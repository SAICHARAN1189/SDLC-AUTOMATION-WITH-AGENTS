from __future__ import annotations

import json
from typing import Any

from backend.agents import AGENT_REGISTRY
from backend.models.schemas import DeveloperMode, EventType, utc_now
from backend.orchestration.events import emit
from backend.orchestration.state import ProjectState, update_live_state
from backend.persistence import repositories
from backend.tools.artifact_tools import artifact_storage_path, files_to_zip_bytes, maybe_upload_bytes


def _message(sender: str, receiver: str, message_type: str, content: str, recommended_action: str | None = None, severity: str | None = None, affected_files: list[str] | None = None) -> dict[str, Any]:
    return {
        "sender": sender,
        "receiver": receiver,
        "message_type": message_type,
        "content": content,
        "recommended_action": recommended_action,
        "severity": severity,
        "affected_files": affected_files or [],
        "timestamp": utc_now().isoformat(),
    }


def _run_agent(state: ProjectState, agent_key: str, stage: str) -> dict[str, Any]:
    agent = AGENT_REGISTRY[agent_key]
    run_id = state["run_id"]
    mapped_stage = "DEVELOPMENT" if stage in ("DEVELOPER", "DEVELOPMENT") else stage
    repositories.update_run(run_id, current_stage=mapped_stage, status="RUNNING")
    emit(run_id, EventType.AGENT_STARTED.value, f"{agent.identity.display_name} started", mapped_stage, agent_key, "RUNNING")
    
    raw_override = state.get("primary_model")
    model_override = raw_override if raw_override and str(raw_override).lower() not in ("auto", "router", "default", "none") else None

    execution_id = repositories.add_agent_execution(
        {
            "run_id": run_id,
            "agent_name": agent_key,
            "model": model_override,
            "status": "RUNNING",
            "retry_number": (state.get("retry_counts") or {}).get(stage.lower(), 0),
        }
    )
    try:
        payload = agent.run(dict(state), model_override=model_override)
        meta = payload.pop("_meta", {})
        repositories.complete_agent_execution(execution_id, "COMPLETED", float(meta.get("duration") or 0), meta.get("usage"))
        emit(
            run_id,
            EventType.AGENT_COMPLETED.value,
            f"{agent.identity.display_name} completed",
            stage,
            agent_key,
            "COMPLETED",
            {
                "demo": meta.get("demo"),
                "model": meta.get("model"),
                "provider": meta.get("provider"),
                "attempts": meta.get("attempts"),
                "fallback_used": meta.get("fallback_used"),
                "primary_model": meta.get("primary_model"),
                "fallbacks": meta.get("fallbacks"),
            },
        )
        return payload, meta
    except Exception as exc:
        repositories.complete_agent_execution(execution_id, "FAILED", 0)
        emit(run_id, EventType.AGENT_FAILED.value, str(exc), stage, agent_key, "FAILED")
        raise


def requirements_node(state: ProjectState) -> dict[str, Any]:
    output, _ = _run_agent(state, "requirements_agent", "REQUIREMENTS")
    artifact_id = repositories.add_artifact(state["run_id"], "requirements", "Requirements package", json.dumps(output, indent=2))
    message = _message(
        "requirements_agent",
        "architecture_agent",
        "REQUIREMENTS_PACKAGE",
        "Requirements package completed.",
        "CONTINUE",
    )
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, message["content"], "REQUIREMENTS", "requirements_agent", metadata=message)
    update_live_state(state["run_id"], {"requirements": output, "current_stage": "REQUIREMENTS"})
    return {
        "requirements": output,
        "current_stage": "REQUIREMENTS",
        "current_agent": "requirements_agent",
        "messages": [message],
        "artifact_ids": [artifact_id],
        "timestamps": {**(state.get("timestamps") or {}), "requirements": utc_now().isoformat()},
    }


def architecture_node(state: ProjectState) -> dict[str, Any]:
    output, _ = _run_agent(state, "architecture_agent", "ARCHITECTURE")
    artifact_id = repositories.add_artifact(state["run_id"], "architecture", "Architecture specification", json.dumps(output, indent=2))
    message = _message(
        "architecture_agent",
        "developer_agent",
        "ARCHITECTURE_SPEC",
        "Architecture specification available.",
        "CONTINUE",
    )
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, message["content"], "ARCHITECTURE", "architecture_agent", metadata=message)
    update_live_state(state["run_id"], {"architecture": output, "current_stage": "ARCHITECTURE"})
    return {
        "architecture": output,
        "current_stage": "ARCHITECTURE",
        "current_agent": "architecture_agent",
        "messages": [message],
        "artifact_ids": [artifact_id],
    }


def visual_architecture_node(state: ProjectState) -> dict[str, Any]:
    output, _ = _run_agent(state, "visual_architecture_agent", "VISUAL_ARCHITECTURE")
    artifact_id = repositories.add_artifact(state["run_id"], "diagrams", "Visual architecture", json.dumps(output, indent=2))
    update_live_state(state["run_id"], {"visual_architecture": output, "current_stage": "VISUAL_ARCHITECTURE"})
    return {
        "visual_architecture": output,
        "current_stage": "VISUAL_ARCHITECTURE",
        "current_agent": "visual_architecture_agent",
        "artifact_ids": [artifact_id],
        "messages": [
            _message("visual_architecture_agent", "developer_agent", "DIAGRAMS_READY", "Validated diagrams stored in state.")
        ],
    }


def developer_node(state: ProjectState) -> dict[str, Any]:
    mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
    if mode != DeveloperMode.INITIAL_IMPLEMENTATION.value:
        emit(state["run_id"], EventType.REWORK_STARTED.value, f"Developer rework: {mode}", "DEVELOPER", "developer_agent", "REWORKING")
    output, _ = _run_agent(state, "developer_agent", "DEVELOPER")
    
    # Guarantee that rework maintains all existing project files
    existing_files = (state.get("code") or {}).get("files") or []
    files = output.get("files") or []
    if mode != DeveloperMode.INITIAL_IMPLEMENTATION.value and existing_files:
        current_paths = {
            f.get("path") if isinstance(f, dict) else getattr(f, "path", "")
            for f in files
        }
        for ef in existing_files:
            ef_path = ef.get("path") if isinstance(ef, dict) else getattr(ef, "path", "")
            ef_content = ef.get("content") if isinstance(ef, dict) else getattr(ef, "content", "")
            if ef_path and ef_path not in current_paths:
                files.append({"path": ef_path, "content": ef_content})
                current_paths.add(ef_path)
        output["files"] = files
        output["project_structure"] = sorted(list(current_paths))

    # Always ensure complete_project_files reflects all project files
    output["complete_project_files"] = list(files)
    if not output.get("changed_files"):
        output["changed_files"] = [
            f.get("path") if isinstance(f, dict) else getattr(f, "path", "")
            for f in files
        ]

    # Pre-QA Implementation Validation Gate
    from backend.tools.implementation_validator import validate_implementation
    val_result = validate_implementation(
        files=files,
        architecture=state.get("architecture"),
        requirements=state.get("requirements"),
        setup_instructions=output.get("setup_instructions") or [],
        existing_files=existing_files,
        mode=mode,
    )

    # Bounded single self-repair attempt if validator finds blocking issues and not in demo mode
    if not val_result.passed and not state.get("demo_mode", True) and not state.get("validation_retry_attempted"):
        logger.warning(f"Developer implementation failed validation: {val_result.summary}. Attempting bounded repair.")
        retry_state = dict(state)
        retry_state["validation_retry_attempted"] = True
        retry_state["validation_issues"] = [i.to_dict() for i in val_result.blocking_issues]
        retry_state["code"] = output
        retry_state["developer_mode"] = DeveloperMode.QA_REWORK.value
        repaired_output, _ = _run_agent(retry_state, "developer_agent", "DEVELOPER")
        
        # Merge repaired output
        repaired_files = repaired_output.get("files") or []
        repaired_paths = {f.get("path") if isinstance(f, dict) else getattr(f, "path", "") for f in repaired_files}
        for orig_f in files:
            orig_path = orig_f.get("path") if isinstance(orig_f, dict) else getattr(orig_f, "path", "")
            if orig_path and orig_path not in repaired_paths:
                repaired_files.append(orig_f)
        output = repaired_output
        output["files"] = repaired_files
        output["complete_project_files"] = list(repaired_files)
        files = repaired_files

        # Re-validate
        val_result = validate_implementation(
            files=files,
            architecture=state.get("architecture"),
            requirements=state.get("requirements"),
            setup_instructions=output.get("setup_instructions") or [],
            existing_files=existing_files,
            mode=mode,
        )

    output["validation_passed"] = val_result.passed
    output["validation_issues"] = [i.to_dict() for i in val_result.issues]

    developer_status = "COMPLETED" if val_result.passed else "FAILED_VALIDATION"

    zip_bytes = files_to_zip_bytes(files)
    storage_path = maybe_upload_bytes(artifact_storage_path(state["run_id"], "source.zip"), zip_bytes)
    artifact_id = repositories.add_artifact(
        state["run_id"],
        "code",
        "Generated source",
        json.dumps(output, indent=2),
        storage_path=storage_path,
    )

    receiver = "security_agent"
    if val_result.passed:
        if mode != DeveloperMode.INITIAL_IMPLEMENTATION.value:
            emit(state["run_id"], EventType.REWORK_COMPLETED.value, "Updated implementation submitted", "DEVELOPER", "developer_agent", "COMPLETED")
            content = "Updated implementation submitted for re-scan."
        else:
            emit(state["run_id"], EventType.FEEDBACK_CREATED.value, "Initial implementation validated and complete", "DEVELOPER", "developer_agent", "COMPLETED")
            content = "Initial implementation available for security analysis."
        message_type = "CODE_UPDATED"
    else:
        emit(
            state["run_id"],
            EventType.FEEDBACK_CREATED.value,
            f"Implementation failed sanity checks: {val_result.summary}",
            "DEVELOPER",
            "developer_agent",
            "FAILED_VALIDATION",
            metadata={"validation_issues": output["validation_issues"]},
        )
        content = f"Implementation completed with validation warnings: {val_result.summary}"
        message_type = "VALIDATION_WARNING"

    message = _message(
        "developer_agent",
        receiver,
        message_type,
        content,
        "CONTINUE",
        affected_files=output.get("changed_files") or [],
    )
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, content, "DEVELOPER", "developer_agent", metadata=message)
    update_live_state(state["run_id"], {
        "code": output,
        "current_stage": "DEVELOPMENT",
        "developer_status": developer_status,
        "validation_issues": output["validation_issues"],
    })
    return {
        "code": output,
        "current_stage": "DEVELOPMENT",
        "current_agent": "developer_agent",
        "developer_status": developer_status,
        "validation_issues": output["validation_issues"],
        "messages": [message],
        "artifact_ids": [artifact_id],
        "developer_mode": mode,
    }


def security_node(state: ProjectState) -> dict[str, Any]:
    output, _ = _run_agent(state, "security_agent", "SECURITY")
    repositories.replace_security_findings(state["run_id"], output.get("vulnerabilities") or [])
    repositories.add_artifact(state["run_id"], "security", "Security report", json.dumps(output, indent=2))
    retries = dict(state.get("retry_counts") or {})
    blocking = bool(output.get("blocking"))
    if blocking:
        retries["security"] = int(retries.get("security") or 0) + 1
        emit(
            state["run_id"],
            EventType.SECURITY_FINDINGS_FOUND.value,
            f"{len(output.get('vulnerabilities') or [])} findings require remediation.",
            "SECURITY",
            "security_agent",
            "FAILED",
            {"blocking": True},
        )
        message = _message(
            "security_agent",
            "developer_agent",
            "SECURITY_FEEDBACK",
            f"{sum(1 for v in output.get('vulnerabilities') or [] if v.get('severity') in ('HIGH','CRITICAL'))} high-severity findings require remediation.",
            "REWORK",
            "HIGH",
            output.get("affected_files") or [],
        )
        max_retries = int(state.get("security_max_retries") or 2)
        decision = "MANUAL_INTERVENTION_REQUIRED" if retries["security"] >= max_retries else "SECURITY_REWORK"
        developer_mode = DeveloperMode.SECURITY_REWORK.value
        status = "MANUAL_INTERVENTION_REQUIRED" if decision == "MANUAL_INTERVENTION_REQUIRED" else "REWORK"
        if decision == "MANUAL_INTERVENTION_REQUIRED":
            emit(state["run_id"], EventType.MANUAL_INTERVENTION_REQUIRED.value, "Security retry limit reached", "SECURITY", "security_agent", "BLOCKED")
    else:
        emit(state["run_id"], EventType.SECURITY_PASSED.value, "Security validation passed.", "SECURITY", "security_agent", "COMPLETED")
        message = _message("security_agent", "qa_agent", "SECURITY_CLEARED", "Security validation passed.", "CONTINUE")
        decision = "CONTINUE"
        developer_mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        status = "PASS"
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, message["content"], "SECURITY", "security_agent", metadata=message)
    update_live_state(state["run_id"], {"security_report": output, "security_status": status, "current_stage": "SECURITY"})
    return {
        "security_report": output,
        "security_status": status,
        "retry_counts": retries,
        "developer_mode": developer_mode,
        "last_decision": decision,
        "current_stage": "SECURITY",
        "current_agent": "security_agent",
        "messages": [message],
        "final_status": "MANUAL_INTERVENTION_REQUIRED" if decision == "MANUAL_INTERVENTION_REQUIRED" else state.get("final_status") or "PENDING",
    }


def qa_node(state: ProjectState) -> dict[str, Any]:
    emit(state["run_id"], EventType.TESTS_STARTED.value, "QA execution started", "QA", "qa_agent", "RUNNING")
    output, _ = _run_agent(state, "qa_agent", "QA")
    repositories.add_test_result(state["run_id"], output)
    repositories.add_artifact(state["run_id"], "tests", "QA report", json.dumps(output, indent=2))
    retries = dict(state.get("retry_counts") or {})
    failed = output.get("overall_status") == "FAIL" or int(output.get("failed") or 0) > 0
    if failed:
        retries["qa"] = int(retries.get("qa") or 0) + 1
        emit(state["run_id"], EventType.TESTS_FAILED.value, "Important test failures exist", "QA", "qa_agent", "FAILED")
        
        failure_affected: list[str] = []
        for f in output.get("failures") or []:
            for af in (f.get("affected_files") or []):
                if af not in failure_affected:
                    failure_affected.append(af)

        message = _message(
            "qa_agent",
            "developer_agent",
            "QA_FEEDBACK",
            "Test failures require implementation fixes.",
            "REWORK",
            "HIGH",
            failure_affected,
        )
        max_retries = int(state.get("qa_max_retries") or 2)
        decision = "MANUAL_INTERVENTION_REQUIRED" if retries["qa"] >= max_retries else "QA_REWORK"
        developer_mode = DeveloperMode.QA_REWORK.value
        status = "FAIL"
        if decision == "MANUAL_INTERVENTION_REQUIRED":
            emit(state["run_id"], EventType.MANUAL_INTERVENTION_REQUIRED.value, "QA retry limit reached", "QA", "qa_agent", "BLOCKED")
    else:
        emit(state["run_id"], EventType.TESTS_PASSED.value, "Tests passed", "QA", "qa_agent", "COMPLETED")
        emit(state["run_id"], EventType.TESTS_COMPLETED.value, "QA completed", "QA", "qa_agent", "COMPLETED")
        message = _message("qa_agent", "review_agent", "QA_CLEARED", "Tests passed.", "CONTINUE")
        decision = "CONTINUE"
        developer_mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        status = "PASS"
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, message["content"], "QA", "qa_agent", metadata=message)
    update_live_state(state["run_id"], {"test_report": output, "testing_status": status, "current_stage": "QA"})
    return {
        "test_report": output,
        "testing_status": status,
        "retry_counts": retries,
        "developer_mode": developer_mode,
        "last_decision": decision,
        "current_stage": "QA",
        "current_agent": "qa_agent",
        "messages": [message],
        "final_status": "MANUAL_INTERVENTION_REQUIRED" if decision == "MANUAL_INTERVENTION_REQUIRED" else state.get("final_status") or "PENDING",
    }


def review_node(state: ProjectState) -> dict[str, Any]:
    emit(state["run_id"], EventType.REVIEW_STARTED.value, "Review started", "REVIEW", "review_agent", "RUNNING")
    output, _ = _run_agent(state, "review_agent", "REVIEW")
    repositories.add_review_result(state["run_id"], output)
    repositories.add_artifact(state["run_id"], "review", "Review report", json.dumps(output, indent=2))
    retries = dict(state.get("retry_counts") or {})
    rework = bool(output.get("rework_required"))
    if rework:
        retries["review"] = int(retries.get("review") or 0) + 1
        message = _message("review_agent", "developer_agent", "REVIEW_FEEDBACK", "Blocking review issues require rework.", "REWORK", "HIGH")
        max_retries = int(state.get("review_max_retries") or 2)
        decision = "MANUAL_INTERVENTION_REQUIRED" if retries["review"] >= max_retries else "REVIEW_REWORK"
        developer_mode = DeveloperMode.REVIEW_REWORK.value
        status = "FAIL"
        if decision == "MANUAL_INTERVENTION_REQUIRED":
            emit(state["run_id"], EventType.MANUAL_INTERVENTION_REQUIRED.value, "Review retry limit reached", "REVIEW", "review_agent", "BLOCKED")
    else:
        message = _message("review_agent", "finalizer", "REVIEW_CLEARED", "Review passed.", "CONTINUE")
        decision = "CONTINUE"
        developer_mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        status = "PASS"
    emit(state["run_id"], EventType.REVIEW_COMPLETED.value, message["content"], "REVIEW", "review_agent", "COMPLETED" if not rework else "FAILED")
    emit(state["run_id"], EventType.FEEDBACK_CREATED.value, message["content"], "REVIEW", "review_agent", metadata=message)
    update_live_state(state["run_id"], {"review_report": output, "review_status": status, "current_stage": "REVIEW"})
    return {
        "review_report": output,
        "review_status": status,
        "retry_counts": retries,
        "developer_mode": developer_mode,
        "last_decision": decision,
        "current_stage": "REVIEW",
        "current_agent": "review_agent",
        "messages": [message],
        "final_status": "MANUAL_INTERVENTION_REQUIRED" if decision == "MANUAL_INTERVENTION_REQUIRED" else ("COMPLETED" if decision == "CONTINUE" else "PENDING"),
    }


def model_comparison_node(state: ProjectState) -> dict[str, Any]:
    output, _ = _run_agent(state, "multi_model_agent", "MODEL_COMPARISON")
    repositories.add_model_comparisons(state["run_id"], output.get("results") or [])
    repositories.add_artifact(state["run_id"], "model_comparison", "Model comparison", json.dumps(output, indent=2))
    update_live_state(state["run_id"], {"model_comparison": output, "current_stage": "MODEL_COMPARISON"})
    return {
        "model_comparison": output,
        "current_stage": "MODEL_COMPARISON",
        "current_agent": "multi_model_agent",
    }


def finalization_node(state: ProjectState) -> dict[str, Any]:
    intervention = state.get("final_status") == "MANUAL_INTERVENTION_REQUIRED" or state.get("last_decision") == "MANUAL_INTERVENTION_REQUIRED"
    status = "MANUAL_INTERVENTION_REQUIRED" if intervention else "COMPLETED"
    repositories.update_run(state["run_id"], status=status, current_stage="FINALIZATION", completed_at=utc_now())
    if intervention:
        emit(state["run_id"], EventType.MANUAL_INTERVENTION_REQUIRED.value, "Workflow stopped for manual intervention", "FINALIZATION", None, status)
        emit(state["run_id"], EventType.PIPELINE_FAILED.value, "Pipeline requires manual intervention", "FINALIZATION", None, status)
    else:
        emit(state["run_id"], EventType.PIPELINE_COMPLETED.value, "Pipeline completed", "FINALIZATION", None, "COMPLETED")
    return {
        "current_stage": "FINALIZATION",
        "current_agent": "finalizer",
        "final_status": status,
    }
