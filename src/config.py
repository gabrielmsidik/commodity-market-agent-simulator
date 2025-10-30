"""Configuration management for the simulation."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    model_name: str
    base_url: str
    api_key: str
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls, agent_name: str) -> "AgentConfig":
        """Load agent configuration from environment variables."""
        prefix = agent_name.upper().replace(" ", "").replace("_", "")
        
        model_name = os.getenv(f"{prefix}_MODEL_NAME")
        base_url = os.getenv(f"{prefix}_BASE_URL")
        api_key = os.getenv(f"{prefix}_API_KEY")
        
        if not all([model_name, base_url, api_key]):
            raise ValueError(
                f"Missing configuration for {agent_name}. "
                f"Please set {prefix}_MODEL_NAME, {prefix}_BASE_URL, and {prefix}_API_KEY"
            )
        
        return cls(
            name=agent_name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key
        )


@dataclass
class AppConfig:
    """Application-wide configuration."""
    
    # Agent configurations
    wholesaler: AgentConfig
    seller1: AgentConfig
    seller2: AgentConfig
    
    # Database
    database_url: str
    
    # Flask
    flask_secret_key: str
    flask_debug: bool
    flask_port: int
    
    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            wholesaler=AgentConfig.from_env("WHOLESALER"),
            seller1=AgentConfig.from_env("SELLER1"),
            seller2=AgentConfig.from_env("SELLER2"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./simulations.db"),
            flask_secret_key=os.getenv("FLASK_SECRET_KEY", "dev-secret-key"),
            flask_debug=os.getenv("FLASK_DEBUG", "True").lower() == "true",
            flask_port=int(os.getenv("FLASK_PORT", "5000"))
        )


# Global configuration instance
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global config
    if config is None:
        config = AppConfig.load()
    return config

