from __future__ import annotations

from time import perf_counter
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from backend.config.settings import settings
from backend.llm.router import model_router
from backend.models.schemas import AgentIdentity, ErrorCategory
from backend.utils.logging import logger
from backend.utils.validators import parse_model


class AgentExecutionError(RuntimeError):
    def __init__(self, category: ErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


class BaseEngineeringAgent:
    identity: AgentIdentity
    output_model: Type[BaseModel]

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def demo_output(self, observed: dict[str, Any]) -> BaseModel:
        raise NotImplementedError

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        raise NotImplementedError

    def use_tools(self, observed: dict[str, Any], draft: BaseModel | None = None) -> dict[str, Any]:
        return {}

    def run(self, state: dict[str, Any], model_override: str | None = None) -> dict[str, Any]:
        observed = self.observe(state)
        started = perf_counter()
        demo = bool(state.get("demo_mode", settings.demo_mode))
        agent_key = self.identity.name.value
        agent_cfg = model_router.get_config(agent_key)
        usage = {}
        model_used = "demo-deterministic" if demo else (model_override or agent_cfg.primary.model)
        provider_used = "demo" if demo else (model_router.resolve_provider_for_model(model_override) if model_override else agent_cfg.primary.provider)
        attempts = 1
        fallback_used = False
        try:
            if demo:
                output = self.demo_output(observed)
            else:
                system, user = self.build_prompt(observed)
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
                result = model_router.generate(
                    agent_name=agent_key,
                    messages=messages,
                    model_override=model_override,
                    json_mode=True,
                )
                model_used = result.model
                provider_used = result.provider
                attempts = result.attempts
                fallback_used = result.fallback_used
                usage = result.usage
                try:
                    output = parse_model(result.content, self.output_model)
                except (ValidationError, ValueError) as exc:
                    raise AgentExecutionError(ErrorCategory.VALIDATION_ERROR, str(exc)) from exc
            tool_context = self.use_tools(observed, output)
            if tool_context:
                output = self.apply_tools(output, tool_context)
        except AgentExecutionError:
            raise
        except Exception as exc:
            raise AgentExecutionError(ErrorCategory.LLM_ERROR, str(exc)) from exc
        duration = perf_counter() - started
        logger.info(
            "agent completed",
            extra={
                "agent": self.identity.name.value,
                "provider": provider_used,
                "model": model_used,
                "attempts": attempts,
                "fallback_used": fallback_used,
                "duration": duration,
                "status": "COMPLETED",
                "run_id": state.get("run_id"),
            },
        )
        payload = output.model_dump(mode="json")
        payload["_meta"] = {
            "agent": self.identity.name.value,
            "provider": provider_used,
            "model": model_used,
            "attempts": attempts,
            "fallback_used": fallback_used,
            "primary_model": agent_cfg.primary.model,
            "fallbacks": [fb.to_dict() for fb in agent_cfg.fallbacks],
            "duration": duration,
            "usage": usage,
            "demo": demo,
            "tools": self.identity.tools,
        }
        return payload

    def apply_tools(self, output: BaseModel, tool_context: dict[str, Any]) -> BaseModel:
        return output
