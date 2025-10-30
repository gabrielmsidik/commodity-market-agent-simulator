"""LLM wrapper for agents with configurable providers."""

from typing import Optional, Type
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from src.config import AgentConfig


def create_agent_llm(
    agent_config: AgentConfig,
    structured_output_schema: Optional[Type[BaseModel]] = None
) -> ChatOpenAI:
    """
    Create an LLM instance for an agent.

    Args:
        agent_config: Agent configuration with model, base_url, and API key
        structured_output_schema: Optional Pydantic model for structured output

    Returns:
        ChatOpenAI instance configured for the agent, optionally with structured output
    """
    llm = ChatOpenAI(
        model=agent_config.model_name,
        openai_api_base=agent_config.base_url,
        openai_api_key=agent_config.api_key,
        temperature=agent_config.temperature
    )

    # If structured output schema is provided, configure LLM to use it
    if structured_output_schema is not None:
        llm = llm.with_structured_output(structured_output_schema)

    return llm

