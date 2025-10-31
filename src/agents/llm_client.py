"""Abstract LLM client interface supporting multiple providers."""

from abc import ABC, abstractmethod
from typing import Optional, Type, Any, Dict, List
import json
import re
import logging
import httpx
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import AgentConfig

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def invoke(self, prompt: str | List[Any]) -> Any:
        """
        Invoke the LLM with a prompt.

        Args:
            prompt: Either a string or a list of messages

        Returns:
            Response from the LLM (format depends on structured output config)
        """
        pass


class OpenAICompatibleClient(LLMClient):
    """
    Client using langchain_openai.ChatOpenAI.

    Works with:
    - OpenAI (https://api.openai.com/v1)
    - Any OpenAI-compatible API
    """

    def __init__(self, agent_config: AgentConfig, structured_output_schema: Optional[Type[BaseModel]] = None):
        """
        Initialize OpenAI-compatible client.

        Args:
            agent_config: Agent configuration
            structured_output_schema: Optional Pydantic model for structured output
        """
        self.agent_config = agent_config
        self.schema = structured_output_schema

        # Create base LLM
        self.llm = ChatOpenAI(
            model=agent_config.model_name,
            base_url=agent_config.base_url,
            api_key=agent_config.api_key,
            temperature=agent_config.temperature
        )

        # Configure structured output if provided
        if structured_output_schema is not None:
            self.llm = self.llm.with_structured_output(structured_output_schema)

    def invoke(self, prompt: str | List[Any]) -> Any:
        """Invoke the LLM using langchain."""
        return self.llm.invoke(prompt)


class OpenRouterClient(LLMClient):
    """
    Client using direct HTTP requests to OpenRouter.

    Bypasses langchain_openai to work around authentication issues.
    """

    def __init__(self, agent_config: AgentConfig, structured_output_schema: Optional[Type[BaseModel]] = None):
        """
        Initialize OpenRouter client.

        Args:
            agent_config: Agent configuration
            structured_output_schema: Optional Pydantic model for structured output
        """
        self.agent_config = agent_config
        self.schema = structured_output_schema
        self.client = httpx.Client(timeout=120.0)  # 2 minute timeout for reasoning models

    def invoke(self, prompt: str | List[Any]) -> Any:
        """
        Invoke OpenRouter API directly using HTTP requests.

        Args:
            prompt: Either a string or list of langchain messages

        Returns:
            Structured Pydantic model if schema provided, else string response
        """
        # Convert langchain messages to OpenAI format
        messages = self._convert_to_messages(prompt)

        # Prepare request payload
        payload = {
            "model": self.agent_config.model_name,
            "messages": messages,
            "temperature": self.agent_config.temperature
        }

        # Add response format for structured output
        if self.schema:
            # Get base schema and add additionalProperties: false recursively
            schema = self.schema.model_json_schema()
            schema = self._add_additional_properties_false(schema)

            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": self.schema.__name__,
                    "strict": True,
                    "schema": schema
                }
            }

        # Make request to OpenRouter
        headers = {
            "Authorization": f"Bearer {self.agent_config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/unused1/commodity-market-agent-simulator",
            "X-Title": "Commodity Market Agent Simulator"
        }

        response = self.client.post(
            f"{self.agent_config.base_url}/chat/completions",
            headers=headers,
            json=payload
        )

        # Check for errors - improved error reporting
        if response.status_code != 200:
            error_body = response.text
            raise httpx.HTTPStatusError(
                f"OpenRouter API error (status {response.status_code}): {error_body}",
                request=response.request,
                response=response
            )

        # Parse response
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse structured output if schema provided
        if self.schema:
            parsed = self._parse_json_content(content)
            return self.schema(**parsed)

        return content

    def _add_additional_properties_false(self, schema: Dict) -> Dict:
        """
        Recursively add 'additionalProperties': false to all object schemas.

        OpenAI's structured output requires this for strict schema validation.

        Args:
            schema: JSON schema dict

        Returns:
            Modified schema with additionalProperties: false added
        """
        if isinstance(schema, dict):
            # Add additionalProperties: false to object types
            if schema.get("type") == "object":
                schema["additionalProperties"] = False

            # Recursively process all nested schemas
            for key, value in schema.items():
                if isinstance(value, dict):
                    schema[key] = self._add_additional_properties_false(value)
                elif isinstance(value, list):
                    schema[key] = [
                        self._add_additional_properties_false(item) if isinstance(item, dict) else item
                        for item in value
                    ]

        return schema

    def _parse_json_content(self, content: str) -> Dict:
        """
        Parse JSON content from LLM response with robust error handling.

        Handles common issues:
        - Markdown code blocks (```json ... ```)
        - Leading/trailing whitespace
        - Escaped quotes and newlines
        - Extra text before/after JSON

        Args:
            content: Raw content from LLM response

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If JSON cannot be parsed after cleanup attempts
        """
        # Try parsing directly first
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {e}. Attempting cleanup...")

        # Clean up the content
        cleaned = content.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```"):
            # Extract content between ``` markers
            lines = cleaned.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Find closing ```
            try:
                end_idx = lines.index("```")
                lines = lines[:end_idx]
            except ValueError:
                # No closing ```, just remove first line
                pass
            cleaned = "\n".join(lines).strip()

        # Try parsing after markdown cleanup
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse after markdown cleanup failed: {e}. Trying regex extraction...")

        # Try to extract JSON object using regex
        # Look for outermost { ... }
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parse after regex extraction failed: {e}")

        # If all else fails, log the content and raise the original error
        logger.error(f"Failed to parse JSON content. Raw content (first 500 chars): {content[:500]}")
        # Try one more time to get a better error message
        return json.loads(content)

    def _convert_to_messages(self, prompt: str | List[Any]) -> List[Dict[str, str]]:
        """
        Convert prompt to OpenAI message format.

        Args:
            prompt: String or list of langchain messages

        Returns:
            List of message dicts in OpenAI format
        """
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]

        messages = []
        for msg in prompt:
            if isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            else:
                # Fallback for other message types
                messages.append({"role": "user", "content": str(msg.content)})

        return messages

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, 'client'):
            self.client.close()


def create_llm_client(
    agent_config: AgentConfig,
    structured_output_schema: Optional[Type[BaseModel]] = None
) -> LLMClient:
    """
    Factory function to create the appropriate LLM client based on configuration.

    Args:
        agent_config: Agent configuration with model, base_url, and API key
        structured_output_schema: Optional Pydantic model for structured output

    Returns:
        LLMClient instance (OpenAICompatibleClient or OpenRouterClient)

    Examples:
        >>> # OpenAI usage (unchanged for upstream developers)
        >>> config = AgentConfig(
        ...     name="test",
        ...     model_name="gpt-4o-mini",
        ...     base_url="https://api.openai.com/v1",
        ...     api_key="sk-..."
        ... )
        >>> client = create_llm_client(config)
        >>> response = client.invoke("Hello!")

        >>> # OpenRouter usage (automatic detection)
        >>> config = AgentConfig(
        ...     name="test",
        ...     model_name="anthropic/claude-3.5-sonnet",
        ...     base_url="https://openrouter.ai/api/v1",
        ...     api_key="sk-or-v1-..."
        ... )
        >>> client = create_llm_client(config)  # Uses OpenRouterClient automatically
        >>> response = client.invoke("Hello!")
    """
    # Detect provider based on base_url
    if "openrouter.ai" in agent_config.base_url:
        return OpenRouterClient(agent_config, structured_output_schema)
    else:
        # Default to OpenAI-compatible client
        return OpenAICompatibleClient(agent_config, structured_output_schema)
