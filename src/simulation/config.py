"""Simulation configuration parameters."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimulationConfig:
    """Configuration for a single simulation run."""
    
    # Simulation metadata
    name: Optional[str] = None
    description: Optional[str] = None
    num_days: int = 100
    
    # Seller 1 configuration

    # cost range
    s1_cost_min: int = 58 
    s1_cost_max: int = 62
    
    # inventory range
    s1_inv_min: int = 7800
    s1_inv_max: int = 8200

    s1_starting_cash: float = 0.0  # Sellers start with $0 (in debt for initial inventory)

    # Seller 2 configuration
    
    s2_cost_min: int = 68
    s2_cost_max: int = 72
    
    s2_inv_min: int = 1900
    s2_inv_max: int = 2100
    
    s2_starting_cash: float = 0.0  # Sellers start with $0 (in debt for initial inventory)

    # Wholesaler configuration
    wholesaler_starting_cash: float = 50000.0  # Wholesaler starts with working capital
    
    # Shopper configuration
    total_shoppers: int = 400  # Increased by 4x to create more demand
    long_term_ratio: float = 0.7  # 70% long-term, 30% short-term

    # Long-term shopper parameters
    # shopper demand
    lt_demand_min: int = 20
    lt_demand_max: int = 50
    lt_window_min: int = 50  # Extended from 30 to spread across 100 days
    lt_window_max: int = 90  # Extended from 60 to spread across 100 days
    
    # initial starting shopping price
    lt_base_price_min: float = 80.0
    lt_base_price_max: float = 100.0

    # final shopping price range
    lt_max_price_min: float = 110.0
    lt_max_price_max: float = 130.0
    
    lt_urgency_min: float = 0.7
    lt_urgency_max: float = 1.2

    # Short-term shopper parameters
    st_demand_min: int = 30
    st_demand_max: int = 50
    st_window_min: int = 10  # Extended from 5 to create more overlap
    st_window_max: int = 20  # Extended from 10 to create more overlap

    st_base_price_min: float = 100.0
    st_base_price_max: float = 120.0
    st_max_price_min: float = 120.0
    st_max_price_max: float = 150.0
    
    st_urgency_min: float = 1.5
    st_urgency_max: float = 2.5
    
    # Negotiation configuration
    negotiation_days: list = field(default_factory=lambda: [1, 21, 41, 61, 81])
    max_negotiation_rounds: int = 10

    # Baseline experiment toggles (collusion research)
    enable_communication: bool = True  # Enable wholesaler daily communication
    enable_price_transparency: bool = True  # Enable competitor price visibility

    # Transportation costs configuration
    transport_cost_per_unit: int = 1  # Daily transport cost per unit brought to market
    transport_cost_enabled: bool = True  # Toggle feature on/off

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure num_days is at least 1
        if self.num_days < 1:
            raise ValueError(f"num_days must be at least 1, got {self.num_days}")

        # Warn if window lengths might be problematic
        if self.lt_window_max >= self.num_days:
            import warnings
            warnings.warn(
                f"Long-term window_max ({self.lt_window_max}) is >= num_days ({self.num_days}). "
                f"This will be automatically capped to {self.num_days - 1}."
            )

        if self.st_window_max >= self.num_days:
            import warnings
            warnings.warn(
                f"Short-term window_max ({self.st_window_max}) is >= num_days ({self.num_days}). "
                f"This will be automatically capped to {self.num_days - 1}."
            )

        # Ensure min <= max for all ranges
        if self.s1_cost_min > self.s1_cost_max:
            raise ValueError(f"s1_cost_min ({self.s1_cost_min}) > s1_cost_max ({self.s1_cost_max})")
        if self.s1_inv_min > self.s1_inv_max:
            raise ValueError(f"s1_inv_min ({self.s1_inv_min}) > s1_inv_max ({self.s1_inv_max})")
        if self.s2_cost_min > self.s2_cost_max:
            raise ValueError(f"s2_cost_min ({self.s2_cost_min}) > s2_cost_max ({self.s2_cost_max})")
        if self.s2_inv_min > self.s2_inv_max:
            raise ValueError(f"s2_inv_min ({self.s2_inv_min}) > s2_inv_max ({self.s2_inv_max})")

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "num_days": self.num_days,
            "s1_cost_min": self.s1_cost_min,
            "s1_cost_max": self.s1_cost_max,
            "s1_inv_min": self.s1_inv_min,
            "s1_inv_max": self.s1_inv_max,
            "s1_starting_cash": self.s1_starting_cash,
            "s2_cost_min": self.s2_cost_min,
            "s2_cost_max": self.s2_cost_max,
            "s2_inv_min": self.s2_inv_min,
            "s2_inv_max": self.s2_inv_max,
            "s2_starting_cash": self.s2_starting_cash,
            "wholesaler_starting_cash": self.wholesaler_starting_cash,
            "total_shoppers": self.total_shoppers,
            "long_term_ratio": self.long_term_ratio,
            "lt_demand_min": self.lt_demand_min,
            "lt_demand_max": self.lt_demand_max,
            "lt_window_min": self.lt_window_min,
            "lt_window_max": self.lt_window_max,
            "lt_base_price_min": self.lt_base_price_min,
            "lt_base_price_max": self.lt_base_price_max,
            "lt_max_price_min": self.lt_max_price_min,
            "lt_max_price_max": self.lt_max_price_max,
            "lt_urgency_min": self.lt_urgency_min,
            "lt_urgency_max": self.lt_urgency_max,
            "st_demand_min": self.st_demand_min,
            "st_demand_max": self.st_demand_max,
            "st_window_min": self.st_window_min,
            "st_window_max": self.st_window_max,
            "st_base_price_min": self.st_base_price_min,
            "st_base_price_max": self.st_base_price_max,
            "st_max_price_min": self.st_max_price_min,
            "st_max_price_max": self.st_max_price_max,
            "st_urgency_min": self.st_urgency_min,
            "st_urgency_max": self.st_urgency_max,
            "negotiation_days": self.negotiation_days,
            "max_negotiation_rounds": self.max_negotiation_rounds,
            "enable_communication": self.enable_communication,
            "enable_price_transparency": self.enable_price_transparency,
            "transport_cost_per_unit": self.transport_cost_per_unit,
            "transport_cost_enabled": self.transport_cost_enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SimulationConfig":
        """Create configuration from dictionary."""
        return cls(**data)

