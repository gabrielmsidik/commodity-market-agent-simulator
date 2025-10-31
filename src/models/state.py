"""State models for the economic simulation."""

from typing import TypedDict, List, Dict, Optional, Annotated, Any
import operator


class Shopper(TypedDict):
    """Represents a shopper in the simulation."""
    shopper_id: str
    shopper_type: str  # "long_term" or "short_term"
    total_demand: int
    demand_remaining: int
    shopping_window_start: int
    shopping_window_end: int
    base_willing_to_pay: float
    max_willing_to_pay: float
    urgency_factor: float  # Controls price acceleration curve


class AgentLedger(TypedDict):
    """Tracks an agent's financial state."""
    inventory: int
    cash: float
    cost_per_unit: int  # Production/acquisition cost per unit (for sellers)
    total_cost_incurred: float
    total_revenue: float
    private_sales_log: List[Dict]
    total_transport_costs: float  # Cumulative transport costs incurred
    daily_transport_cost: float  # Transport cost for current day (informational)


class MarketOffer(TypedDict):
    """An agent's daily market offer."""
    agent_name: str
    price: int  # Must be an integer
    quantity: int
    inventory_available: int


class NegotiationOffer(TypedDict):
    """An offer made during negotiation."""
    agent: str  # Who made this offer
    price: int  # Integer price per unit
    quantity: int  # Number of units
    justification: str  # Reasoning for this offer
    action: str  # "offer", "counteroffer", "accept", or "reject"


class ShopperPoolEntry(TypedDict, total=False):
    """Entry in the daily shopper pool."""
    shopper_id: str  # Unique ID per demand unit (e.g., "S1_unit0", "S1_unit1")
    original_shopper_id: str  # Original shopper ID for aggregation (optional)
    willing_to_pay: int  # Integer price
    demand_unit: int  # Always 1 (for matching algorithm)


class EconomicState(TypedDict):
    """The complete state of the economic simulation."""

    # Simulation configuration
    num_days: int  # Total number of days in the simulation

    # Day counter
    day: int

    # Market history (append-only logs)
    market_log: Annotated[List[Dict], operator.add]  # B2C trades (sellers to shoppers)
    unmet_demand_log: Annotated[List[Dict], operator.add]
    wholesale_trades_log: Annotated[List[Dict], operator.add]  # B2B trades (sellers to wholesaler)

    # Daily state (reset each day)
    daily_shopper_pool: List[ShopperPoolEntry]
    daily_market_offers: Dict[str, MarketOffer]
    daily_transport_costs: Dict[str, float]  # Transport costs by agent for current day

    # Agent state (persistent)
    agent_ledgers: Dict[str, AgentLedger]

    # Shopper database (persistent)
    shopper_database: List[Shopper]

    # Negotiation state (used on negotiation days)
    negotiation_status: str  # "pending", "seller_1_negotiating", "seller_2_negotiating", "complete"
    current_negotiation_target: Optional[str]  # "Seller_1" or "Seller_2" or None
    negotiation_history: Dict[str, List[NegotiationOffer]]

    # Agent memory (persistent across all days)
    agent_scratchpads: Dict[str, str]  # Free-form text notes

    # Simulation configuration (immutable)
    config: Any  # SimulationConfig (using Any to avoid circular import)

