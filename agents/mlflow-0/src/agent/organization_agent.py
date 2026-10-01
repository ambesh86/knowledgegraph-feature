import logging

from mlflow.entities.model_registry import PromptVersion

from strands import Agent
from strands.agent.agent_result import AgentResult
from strands.models import BedrockModel

logger = logging.getLogger(__name__)


class OrganizationAgent:

    def __init__(self, agent_model: BedrockModel, prompt: PromptVersion):
        self.agent_model = agent_model
        self.prompt = prompt

    def resolve_organization(self, organization_name: str) -> AgentResult:
        agent = Agent(model=self.agent_model)
        formatted_prompt = self.prompt.format(
            allow_partial=False, organization_name=organization_name
        )
        logger.debug(f"prompt={formatted_prompt}")
        response = agent(formatted_prompt)
        return response
