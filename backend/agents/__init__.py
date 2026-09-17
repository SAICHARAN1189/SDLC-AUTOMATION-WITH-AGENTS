from backend.agents.requirements_agent import RequirementsAgent
from backend.agents.architecture_agent import ArchitectureAgent
from backend.agents.visual_architecture_agent import VisualArchitectureAgent
from backend.agents.developer_agent import DeveloperAgent
from backend.agents.security_agent import SecurityAgent
from backend.agents.qa_agent import QAAgent
from backend.agents.review_agent import ReviewAgent
from backend.agents.multi_model_agent import MultiModelAgent

AGENT_REGISTRY = {
    "requirements_agent": RequirementsAgent(),
    "architecture_agent": ArchitectureAgent(),
    "visual_architecture_agent": VisualArchitectureAgent(),
    "developer_agent": DeveloperAgent(),
    "security_agent": SecurityAgent(),
    "qa_agent": QAAgent(),
    "review_agent": ReviewAgent(),
    "multi_model_agent": MultiModelAgent(),
}


def serialize_agents() -> list[dict]:
    items = []
    for agent in AGENT_REGISTRY.values():
        items.append(agent.identity.model_dump(mode="json"))
    return items
