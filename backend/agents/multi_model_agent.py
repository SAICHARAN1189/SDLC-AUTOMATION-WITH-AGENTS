from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_model_comparison
from backend.config.settings import settings
from backend.llm.provider import provider
from backend.models.schemas import AgentIdentity, AgentName, ModelComparisonOutput, ModelComparisonResult


def heuristic_scores(text: str, prompt: str) -> dict[str, float]:
    lowered = text.lower()
    req_terms = ["requirement", "user", "api", "auth", "database"]
    coverage = sum(1 for term in req_terms if term in lowered) / len(req_terms)
    structure = 1.0 if ("{" in text and "}" in text) or text.count("\n") > 3 else 0.4
    depth = min(1.0, len(text) / 1200)
    security = sum(1 for term in ("auth", "secret", "injection", "encrypt", "rbac") if term in lowered) / 5
    return {
        "requirement_coverage": round(coverage, 3),
        "structure_adherence": round(structure, 3),
        "technical_depth": round(depth, 3),
        "security_awareness": round(security, 3),
    }


class MultiModelAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.MULTI_MODEL,
        display_name="Multi-Model Comparison Agent",
        role="Run the same benchmark prompt across configured Groq models",
        goal="Record actual latency and heuristic scores without inventing a universal winner",
        instructions="Call each configured model with the same prompt. Store raw outputs and measured latency.",
        tools=["llm_timer"],
        default_model_slot="fast",
    )
    output_model = ModelComparisonOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        prompt = state.get("benchmark_prompt") or (
            "Produce a short architecture sketch for: " + (state.get("user_idea") or "a software system")
        )
        models = state.get("comparison_models") or settings.comparison_model_list
        return {"prompt": prompt, "models": models, "demo_mode": state.get("demo_mode", settings.demo_mode)}

    def demo_output(self, observed: dict[str, Any]) -> ModelComparisonOutput:
        return demo_model_comparison(observed["prompt"], observed["models"])

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        return "Return JSON later", json.dumps(observed)

    def run(self, state: dict[str, Any], model_override: str | None = None) -> dict[str, Any]:
        observed = self.observe(state)
        if observed.get("demo_mode", settings.demo_mode) or not provider.available:
            payload = self.demo_output(observed).model_dump(mode="json")
            payload["_meta"] = {"agent": self.identity.name.value, "demo": True, "model": "demo-deterministic"}
            return payload
        results: list[ModelComparisonResult] = []
        for model in observed["models"]:
            started = perf_counter()
            try:
                completion = provider.complete(
                    system="You are comparing engineering quality. Respond with a structured architecture sketch.",
                    user=observed["prompt"],
                    model=model,
                    json_mode=False,
                    max_completion_tokens=800,
                )
                text = completion.content
                latency = completion.latency_ms
            except Exception as exc:
                text = ""
                latency = (perf_counter() - started) * 1000
                results.append(
                    ModelComparisonResult(
                        model=model,
                        latency_ms=latency,
                        output="",
                        output_length=0,
                        error=str(exc),
                    )
                )
                continue
            scores = heuristic_scores(text, observed["prompt"])
            results.append(
                ModelComparisonResult(
                    model=model,
                    latency_ms=latency,
                    output=text,
                    output_length=len(text),
                    **scores,
                )
            )
        output = ModelComparisonOutput(prompt=observed["prompt"], results=results)
        payload = output.model_dump(mode="json")
        payload["_meta"] = {"agent": self.identity.name.value, "demo": False}
        return payload
