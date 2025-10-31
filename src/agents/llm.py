"""LLM wrapper for agents with configurable providers.

This module provides a unified interface for creating LLM clients that work
with multiple providers (OpenAI, OpenRouter, etc.) while maintaining backward
compatibility with existing code.
"""

from typing import Optional, Type
from pydantic import BaseModel
from src.config import AgentConfig
from src.agents.llm_client import LLMClient, create_llm_client


def create_agent_llm(
    agent_config: AgentConfig,
    structured_output_schema: Optional[Type[BaseModel]] = None
) -> LLMClient:
    """
    Create an LLM client for an agent.

    This function automatically selects the appropriate client implementation
    based on the base_url in the agent configuration:
    - OpenRouter (openrouter.ai) → Uses direct HTTP client
    - OpenAI or compatible → Uses langchain_openai.ChatOpenAI

    Args:
        agent_config: Agent configuration with model, base_url, and API key
        structured_output_schema: Optional Pydantic model for structured output

    Returns:
        LLMClient instance (compatible with langchain's .invoke() interface)

    Examples:
        >>> # OpenAI usage (existing code continues to work)
        >>> from src.config import AgentConfig
        >>> config = AgentConfig.from_env("WHOLESALER")
        >>> llm = create_agent_llm(config)
        >>> response = llm.invoke("What is 2+2?")

        >>> # Structured output (existing code continues to work)
        >>> from src.agents.schemas import NegotiationResponse
        >>> llm = create_agent_llm(config, NegotiationResponse)
        >>> response = llm.invoke("Make an offer")  # Returns NegotiationResponse object

    Note:
        The returned object implements the same .invoke() interface as
        langchain_openai.ChatOpenAI, ensuring backward compatibility.
    """
    return create_llm_client(agent_config, structured_output_schema)

