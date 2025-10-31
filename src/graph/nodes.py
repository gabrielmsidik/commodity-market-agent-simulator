"""Graph nodes for the simulation workflow."""

import random
import json
import logging
from typing import Dict, Any
from functools import wraps
from src.models import EconomicState, ShopperPoolEntry
from src.simulation.shoppers import calculate_willing_to_pay
from src.agents import WholesalerTools, SellerTools, create_agent_llm
from src.agents.schemas import NegotiationResponse, MarketOfferResponse
from src.config import get_config

# Get logger for node execution
# Use root logger to ensure debug logs are captured
logger = logging.getLogger()


# ============================================================================
# ECONOMIC PRIORS - Injected into every LLM call for rational decision-making
# ============================================================================

def calculate_current_metrics(ledger: Dict[str, Any], num_days: int, current_day: int) -> Dict[str, Any]:
    """
    Calculate current business metrics for an agent.

    Returns metrics like ROI, cost recovery rate, gross profit, etc.
    """
    initial_investment = ledger.get("initial_inventory_value", 0.0)
    revenue = ledger.get("total_revenue", 0.0)
    total_cost = ledger.get("total_cost_incurred", 0.0)
    inventory = ledger.get("inventory", 0)
    initial_inventory = ledger.get("initial_inventory", 0)
    cost_per_unit = ledger.get("cost_per_unit", 0)
    book_value = ledger.get("book_value_remaining", initial_investment)
    accumulated_depreciation = ledger.get("accumulated_depreciation", 0.0)

    # Units sold
    units_sold = initial_inventory - inventory

    # Gross Profit (margin on sales)
    if units_sold > 0:
        cogs = units_sold * cost_per_unit
        gross_profit = revenue - cogs
    else:
        gross_profit = 0.0

    # Net Position
    net_position = revenue - total_cost

    # Cost Recovery Rate
    cost_recovery_rate = (revenue / initial_investment) if initial_investment > 0 else 0.0

    # ROI
    roi = (net_position / initial_investment) if initial_investment > 0 else 0.0

    # Inventory Turnover
    inventory_turnover = (units_sold / initial_inventory) if initial_inventory > 0 else 0.0

    # Daily depreciation
    daily_depreciation = (initial_investment / num_days) if num_days > 0 else 0.0

    # Days to breakeven (at current revenue rate)
    if current_day > 0:
        daily_revenue_rate = revenue / current_day
        remaining_cost_to_recover = initial_investment - revenue
        if daily_revenue_rate > 0:
            days_to_breakeven = remaining_cost_to_recover / daily_revenue_rate
        else:
            days_to_breakeven = 999  # Impossible to break even
    else:
        days_to_breakeven = 999

    return {
        "initial_investment": initial_investment,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_position": net_position,
        "cost_recovery_rate": cost_recovery_rate,
        "roi": roi,
        "inventory_turnover": inventory_turnover,
        "units_sold": units_sold,
        "inventory_remaining": inventory,
        "book_value": book_value,
        "accumulated_depreciation": accumulated_depreciation,
        "daily_depreciation": daily_depreciation,
        "days_to_breakeven": days_to_breakeven
    }


def get_economic_priors(state: EconomicState, agent_name: str, context: str = "general") -> str:
    """
    Generate economic prior information to inject into LLM prompts.

    This ensures agents make economically rational decisions by providing:
    - Time constraints (days remaining)
    - Negotiation constraints (rounds remaining)
    - Market context (typical prices, negotiation timing)
    - Inventory urgency

    Args:
        state: Current economic state
        agent_name: Name of the agent (Wholesaler, Seller_1, Seller_2)
        context: Context of the call ("negotiation", "pricing", "general")

    Returns:
        Formatted string with economic priors
    """
    current_day = state["day"]
    total_days = state["num_days"]
    days_remaining = total_days - current_day

    # Get agent's current ledger and metrics
    ledger = state["agent_ledgers"].get(agent_name, {})
    metrics = calculate_current_metrics(ledger, total_days, current_day)

    # Build priors string with enhanced business metrics
    priors = f"""
=== BUSINESS PERFORMANCE DASHBOARD ===

YOUR CURRENT FINANCIAL POSITION:
- Initial Investment: ${metrics['initial_investment']:,.0f}
- Current Revenue: ${metrics['revenue']:,.0f}
- Net Position (P&L): ${metrics['net_position']:,.0f}
- Gross Profit: ${metrics['gross_profit']:,.0f}
- ROI: {metrics['roi']:.1%}
- Cost Recovery Rate: {metrics['cost_recovery_rate']:.1%}
- Inventory Turnover: {metrics['inventory_turnover']:.1%}

INVENTORY STATUS:
- Current Inventory: {metrics['inventory_remaining']} units
- Units Sold So Far: {metrics['units_sold']} units
- Book Value (after depreciation): ${metrics['book_value']:,.0f}
- Accumulated Depreciation: ${metrics['accumulated_depreciation']:,.0f}
- Daily Depreciation: ${metrics['daily_depreciation']:,.0f}

TIME & URGENCY:
- Current Day: {current_day} of {total_days}
- Days Remaining: {days_remaining} days
- Est. Days to Breakeven: {metrics['days_to_breakeven']:.0f} days (at current revenue rate)
- ⚠️ CRITICAL: All unsold inventory at day {total_days} EXPIRES (becomes worthless)

MARKET FUNDAMENTALS:
- Typical Market Price Range: $80-$110 per unit (shoppers' willingness to pay)
- Average Market Price: ~$95 per unit
- Sellers' Production Costs: $58-$72 per unit (varies by seller)
"""

    # Add negotiation-specific priors
    if context == "negotiation":
        # Determine which negotiation day this is
        negotiation_days = [1, 21, 41, 61, 81]
        current_negotiation_index = None
        for i, neg_day in enumerate(negotiation_days):
            if current_day == neg_day:
                current_negotiation_index = i
                break

        remaining_negotiations = 0
        if current_negotiation_index is not None:
            remaining_negotiations = len(negotiation_days) - current_negotiation_index - 1

        priors += f"""
NEGOTIATION CONSTRAINTS:
- Maximum Rounds Per Negotiation: 10 rounds
- ⚠️ After 10 rounds, negotiation AUTOMATICALLY FAILS (no deal)
- Negotiation Schedule: Days 1, 21, 41, 61, 81 (every 20 days)
- Current Negotiation: Day {current_day}
- Remaining Future Negotiations: {remaining_negotiations}
- ⚠️ This is negotiation {current_negotiation_index + 1 if current_negotiation_index is not None else '?'} of 5 total

STRATEGIC IMPLICATIONS:
"""

        if current_negotiation_index == 4:  # Last negotiation (day 81)
            priors += f"""- 🚨 THIS IS THE LAST NEGOTIATION! No future opportunities to trade with wholesaler.
- For SELLERS with high inventory: This is your FINAL chance to offload bulk inventory
- Days 82-100 (19 days) are your ONLY remaining time to sell to shoppers
- Failing this negotiation means you MUST sell all {inventory} units to shoppers in 19 days
"""
        elif current_negotiation_index == 3:  # Second-to-last (day 61)
            priors += f"""- Only 1 more negotiation after this (day 81)
- Time is running short - inventory urgency is increasing
- Consider your ability to sell {inventory} units in remaining days
"""
        else:
            priors += f"""- {remaining_negotiations} more negotiation opportunities remain
- Balance current deal vs. future opportunities
- Monitor inventory levels relative to time remaining
"""

    # Add pricing-specific priors
    elif context == "pricing":
        inventory = metrics['inventory_remaining']
        required_daily_rate = inventory / max(days_remaining, 1)

        priors += f"""
PRICING STRATEGY CONSIDERATIONS:
- Inventory to Clear: {inventory} units
- Required Daily Sales Rate: {required_daily_rate:.1f} units/day
- Your Cost Recovery Status: {metrics['cost_recovery_rate']:.1%} (need to reach 100% to break even)
- Current ROI: {metrics['roi']:.1%}
- Shoppers' willingness to pay: $80-$110 (varies by shopper and day)
- Price too high → No sales → Inventory depreciates → Losses compound
- Price too low → Sales but poor margins → Slower cost recovery

DEPRECIATION IMPACT:
- Daily Depreciation Cost: ${metrics['daily_depreciation']:,.0f}
- Book Value Remaining: ${metrics['book_value']:,.0f}
- ⚠️ Holding inventory costs you ${metrics['daily_depreciation']:,.0f} per day in depreciation!

INVENTORY URGENCY:
"""

        # Calculate urgency based on inventory and time
        if days_remaining <= 10:
            priors += f"""- 🚨 CRITICAL: Only {days_remaining} days left! Aggressive pricing essential
- Depreciation accelerating: ${metrics['daily_depreciation'] * days_remaining:,.0f} more value at risk
- Focus on COST RECOVERY first, profit second
"""
        elif days_remaining <= 30:
            priors += f"""- ⚠️ MODERATE URGENCY: {days_remaining} days remaining
- Balance cost recovery with profit margins
- Monitor ROI trend closely
"""
        else:
            priors += f"""- Low urgency: {days_remaining} days remaining
- Can afford to be strategic with pricing
- Focus on maximizing profit margins
"""

    priors += "\n=== END ECONOMIC CONTEXT ===\n"

    return priors


def log_node_execution(func):
    """Decorator to log node execution start and completion."""
    @wraps(func)
    def wrapper(state: EconomicState) -> Dict[str, Any]:
        node_name = func.__name__
        day = state.get("day", "?")
        logger.debug(f"[Day {day}] Node START: {node_name}")
        try:
            result = func(state)
            logger.debug(f"[Day {day}] Node COMPLETE: {node_name}")
            return result
        except Exception as e:
            logger.error(f"[Day {day}] Node FAILED: {node_name} - {str(e)}")
            raise
    return wrapper


@log_node_execution
def setup_day(state: EconomicState) -> Dict[str, Any]:
    """
    Set up the daily shopper pool.

    Filters shoppers whose shopping window includes today,
    calculates their current willingness to pay,
    and creates the daily pool with stable sorting.
    """
    current_day = state["day"]
    shopper_database = state["shopper_database"]

    new_daily_shopper_pool = []

    # Filter active shoppers and create pool entries
    for shopper in shopper_database:
        if (shopper["shopping_window_start"] <= current_day <= shopper["shopping_window_end"]
            and shopper["demand_remaining"] > 0):

            # Calculate current willingness to pay
            willing_to_pay = calculate_willing_to_pay(shopper, current_day)

            # Add one entry per unit of demand (for matching algorithm)
            for _ in range(shopper["demand_remaining"]):
                entry: ShopperPoolEntry = {
                    "shopper_id": shopper["shopper_id"],
                    "willing_to_pay": willing_to_pay,
                    "demand_unit": 1
                }
                new_daily_shopper_pool.append(entry)

    # Shuffle first, then stable sort by price (descending)
    random.shuffle(new_daily_shopper_pool)
    new_daily_shopper_pool.sort(key=lambda x: x["willing_to_pay"], reverse=True)

    logger.debug(f"  → Created daily shopper pool: {len(new_daily_shopper_pool)} demand units")
    return {"daily_shopper_pool": new_daily_shopper_pool}


@log_node_execution
def init_negotiation(state: EconomicState) -> Dict[str, Any]:
    """Initialize negotiation with Seller_1 and Wholesaler."""
    logger.debug(f"  → Initializing negotiation: Seller_1 ↔ Wholesaler")
    return {
        "current_negotiation_target": "Seller_1",
        "current_negotiation_wholesaler": "Wholesaler",
        "negotiation_status": "seller_1_wholesaler_negotiating",
        "negotiation_history": {
            "Seller_1": {"Wholesaler": [], "Wholesaler_2": []},
            "Seller_2": {"Wholesaler": [], "Wholesaler_2": []}
        }
    }


@log_node_execution
def wholesaler_make_offer(state: EconomicState) -> Dict[str, Any]:
    """Current wholesaler makes an offer to the current target seller."""
    config = get_config()

    # Determine which wholesaler is active
    wholesaler_name = state.get("current_negotiation_wholesaler", "Wholesaler")
    wholesaler_config = config.wholesaler if wholesaler_name == "Wholesaler" else config.wholesaler2

    # Create LLM with structured output schema
    llm = create_agent_llm(wholesaler_config, structured_output_schema=NegotiationResponse)
    tools = WholesalerTools(state, agent_name=wholesaler_name)

    target_seller = state["current_negotiation_target"]
    history = state["negotiation_history"][target_seller][wholesaler_name]
    round_number = len(history) // 2 + 1
    scratchpad = state["agent_scratchpads"][wholesaler_name]
    day = state["day"]

    logger.info(f"{wholesaler_name} making offer to {target_seller}")
    logger.debug(f"  → {wholesaler_name} negotiating with {target_seller}, round {round_number}")

    # Get tool data
    stats = tools.get_full_market_history(20)
    inv = tools.get_my_inventory()

    # Log previous offer if exists
    if history:
        last_offer = history[-1]
        logger.info(f"    Previous offer: {last_offer['agent']} offered ${last_offer['price']}/unit for {last_offer['quantity']} units (action: {last_offer['action']})")

    # Get economic priors
    priors = get_economic_priors(state, wholesaler_name, context="negotiation")

    # Build prompt
    prompt = f"""{priors}

--- YOUR PRIVATE DATA ---
Inventory: {inv}
Market Analytics: {stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: {target_seller}
Round: {round_number} of 10
Previous offers in this negotiation: {json.dumps(history, indent=2)}

--- YOUR TASK ---
You are negotiating to BUY inventory from {target_seller}.

STEP 1: Review the ECONOMIC CONTEXT above - consider time constraints, negotiation limits, and market fundamentals
STEP 2: Review your scratchpad and current data. What insights are relevant?
STEP 3: Decide on your negotiation strategy for this round.
STEP 4: Make your offer or respond to their counteroffer.

Provide your response with:
- scratchpad_update: Concise notes to ADD to your scratchpad
- price: Integer price per unit
- quantity: Units to buy
- justification: What you tell the seller about why this price is fair
- action: "offer", "accept", or "reject"

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable information.
Note: "accept" means you accept their last counteroffer. "reject" ends negotiation."""

    # Call LLM with structured output - returns NegotiationResponse object
    response: NegotiationResponse = llm.invoke(prompt)

    # Update scratchpad
    scratchpad_update = f"\n[Day {day}, {target_seller} negotiation]: {response.scratchpad_update}"

    # Create offer
    offer = {
        "agent": wholesaler_name,
        "price": response.price,
        "quantity": response.quantity,
        "justification": response.justification,
        "action": response.action
    }

    # Log the offer
    logger.info(f"    {wholesaler_name}'s offer: ${response.price}/unit for {response.quantity} units (action: {response.action})")
    logger.debug(f"      Justification: {response.justification}")

    # Update history - use nested structure
    new_history = history + [offer]

    return {
        "negotiation_history": {
            **state["negotiation_history"],
            target_seller: {
                **state["negotiation_history"][target_seller],
                wholesaler_name: new_history
            }
        },
        "agent_scratchpads": {
            **state["agent_scratchpads"],
            wholesaler_name: state["agent_scratchpads"][wholesaler_name] + scratchpad_update
        }
    }


@log_node_execution
def seller_respond(state: EconomicState) -> Dict[str, Any]:
    """Seller responds to current Wholesaler's offer."""
    config = get_config()
    seller_name = state["current_negotiation_target"]
    wholesaler_name = state.get("current_negotiation_wholesaler", "Wholesaler")
    logger.debug(f"  → {seller_name} responding to {wholesaler_name}'s offer")

    # Get appropriate config with structured output
    if seller_name == "Seller_1":
        llm = create_agent_llm(config.seller1, structured_output_schema=NegotiationResponse)
    else:
        llm = create_agent_llm(config.seller2, structured_output_schema=NegotiationResponse)

    tools = SellerTools(state, seller_name)

    history = state["negotiation_history"][seller_name][wholesaler_name]
    last_offer = history[-1]
    round_number = len(history) // 2 + 1
    scratchpad = state["agent_scratchpads"][seller_name]
    day = state["day"]

    # Log wholesaler's offer
    logger.info(f"    {wholesaler_name}'s offer to {seller_name}: ${last_offer['price']}/unit for {last_offer['quantity']} units")
    logger.debug(f"      {wholesaler_name}'s justification: {last_offer['justification']}")

    # Get tool data
    inv = tools.get_my_inventory()
    my_stats = tools.calculate_my_sales_stats(20)

    # Get economic priors
    priors = get_economic_priors(state, seller_name, context="negotiation")

    # Build prompt
    prompt = f"""{priors}

--- YOUR PRIVATE DATA ---
Your Inventory: {inv}
Your Recent Sales Stats: {my_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: {wholesaler_name}
Round: {round_number} of 10
{wholesaler_name}'s latest offer: Price ${last_offer['price']} for {last_offer['quantity']} units
Their justification: "{last_offer['justification']}"
Full negotiation history: {json.dumps(history, indent=2)}

--- YOUR TASK ---
{wholesaler_name} wants to BUY from you. They have access to global market data that you don't have.

STEP 1: Review the ECONOMIC CONTEXT above - consider time constraints, inventory urgency, and negotiation timing
STEP 2: Analyze their justification carefully - what market information might they be revealing?
STEP 3: Review your scratchpad - what patterns have you noticed?
STEP 4: Decide whether to accept, reject, or counteroffer.

Provide your response with:
- scratchpad_update: Concise notes to ADD to your scratchpad - what did you learn?
- price: Integer price per unit
- quantity: Units to sell
- justification: What you tell {wholesaler_name} about why this price is fair
- action: "offer", "accept", or "reject"

IMPORTANT: Your scratchpad should be concise. Only add NEW insights you learned.
Note: "accept" means you accept their offer. "reject" ends negotiation.
The wholesaler has superior market data - try to learn from what they reveal!"""

    # Call LLM with structured output - returns NegotiationResponse object
    response: NegotiationResponse = llm.invoke(prompt)

    # Update scratchpad
    scratchpad_update = f"\n[Day {day}, {wholesaler_name} negotiation]: {response.scratchpad_update}"

    # Create response
    offer = {
        "agent": seller_name,
        "price": response.price,
        "quantity": response.quantity,
        "justification": response.justification,
        "action": response.action
    }

    # Log the response
    logger.info(f"    {seller_name}'s response: ${response.price}/unit for {response.quantity} units (action: {response.action})")
    logger.debug(f"      Justification: {response.justification}")

    # Update history - use nested structure
    new_history = history + [offer]

    return {
        "negotiation_history": {
            **state["negotiation_history"],
            seller_name: {
                **state["negotiation_history"][seller_name],
                wholesaler_name: new_history
            }
        },
        "agent_scratchpads": {
            **state["agent_scratchpads"],
            seller_name: state["agent_scratchpads"][seller_name] + scratchpad_update
        }
    }


@log_node_execution
def execute_trade(state: EconomicState) -> Dict[str, Any]:
    """Execute a negotiated trade between Wholesaler and Seller."""
    seller_name = state["current_negotiation_target"]
    history = state["negotiation_history"][seller_name]

    # Get the accepted offer (last one should be accept action)
    last_offer = history[-1]

    # Find the offer that was accepted
    if last_offer["action"] == "accept":
        if last_offer["agent"] == "Wholesaler":
            # Wholesaler accepted seller's offer
            accepted_offer = history[-2]
        else:
            # Seller accepted wholesaler's offer
            accepted_offer = history[-2]
    else:
        # No trade
        return {}

    price = accepted_offer["price"]
    quantity = accepted_offer["quantity"]
    total_value = price * quantity

    logger.info(f"  → TRADE EXECUTED: Wholesaler buys {quantity} units from {seller_name} at ${price}/unit (Total: ${total_value})")
    logger.debug(f"      Accepted offer from: {accepted_offer['agent']}")

    # Update ledgers
    seller_ledger = state["agent_ledgers"][seller_name]
    wholesaler_ledger = state["agent_ledgers"]["Wholesaler"]

    new_seller_ledger = {
        **seller_ledger,
        "inventory": seller_ledger["inventory"] - quantity,
        "cash": seller_ledger["cash"] + (quantity * price),
        "total_revenue": seller_ledger["total_revenue"] + (quantity * price)
    }

    new_wholesaler_ledger = {
        **wholesaler_ledger,
        "inventory": wholesaler_ledger["inventory"] + quantity,
        "cash": wholesaler_ledger["cash"] - (quantity * price),
        "total_cost_incurred": wholesaler_ledger["total_cost_incurred"] + (quantity * price)
    }

    # Log the wholesale trade
    wholesale_trade = {
        "day": state["day"],
        "buyer": "Wholesaler",
        "seller": seller_name,
        "price": price,
        "quantity": quantity,
        "total_value": total_value,
        "status": "completed"
    }

    return {
        "agent_ledgers": {
            **state["agent_ledgers"],
            seller_name: new_seller_ledger,
            "Wholesaler": new_wholesaler_ledger
        },
        "wholesale_trades_log": [wholesale_trade]
    }


@log_node_execution
def set_market_offers(state: EconomicState) -> Dict[str, Any]:
    """All agents set their daily market price and quantity."""
    config = get_config()
    day = state["day"]
    offers = {}

    logger.debug(f"  → Agents setting market offers for day {day}")

    # Wholesaler sets offer
    wholesaler_llm = create_agent_llm(config.wholesaler, structured_output_schema=MarketOfferResponse)
    wholesaler_tools = WholesalerTools(state)

    rec = wholesaler_tools.get_profit_maximizing_price()
    stats = wholesaler_tools.get_full_market_demand_stats()
    inv = wholesaler_tools.get_my_inventory()
    scratchpad = state["agent_scratchpads"]["Wholesaler"]

    # Get economic priors
    wholesaler_priors = get_economic_priors(state, "Wholesaler", context="pricing")

    wholesaler_prompt = f"""{wholesaler_priors}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Current Inventory: {inv['inventory']} units
- Market Analytics: {stats}
- Your Estimated Profit-Maximizing Price: {rec}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review the ECONOMIC CONTEXT above - consider time remaining and inventory urgency
STEP 2: Review your scratchpad - what have you learned from negotiations and past sales?
STEP 3: Analyze current market conditions and your inventory position.
STEP 4: Decide on price and quantity strategy.

Provide your response with:
- scratchpad_update: Concise notes to ADD - any new insights
- price: Integer price per unit
- quantity: Units to offer
- reasoning: Brief explanation of your strategy

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
You may want to hold back inventory for subsequent days."""

    wholesaler_response: MarketOfferResponse = wholesaler_llm.invoke(wholesaler_prompt)

    offers["Wholesaler"] = {
        "agent_name": "Wholesaler",
        "price": wholesaler_response.price,
        "quantity": min(wholesaler_response.quantity, inv["inventory"]),
        "inventory_available": inv["inventory"]
    }

    wholesaler_scratchpad_update = f"\n[Day {day} pricing]: {wholesaler_response.scratchpad_update}"

    # Seller 1 sets offer
    seller1_llm = create_agent_llm(config.seller1, structured_output_schema=MarketOfferResponse)
    seller1_tools = SellerTools(state, "Seller_1")

    s1_inv = seller1_tools.get_my_inventory()
    s1_stats = seller1_tools.calculate_my_sales_stats()
    s1_scratchpad = state["agent_scratchpads"]["Seller_1"]

    # Get economic priors
    seller1_priors = get_economic_priors(state, "Seller_1", context="pricing")

    seller1_prompt = f"""{seller1_priors}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Current Inventory: {s1_inv['inventory']} units
- Your Last 20 Days Sales Stats: {s1_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{s1_scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review the ECONOMIC CONTEXT above - consider time remaining and inventory urgency
STEP 2: Review your scratchpad - what have you learned from negotiations with the Wholesaler?
STEP 3: Analyze your recent sales performance and inventory.
STEP 4: Decide on price and quantity strategy.

Provide your response with:
- scratchpad_update: Concise notes to ADD - any new insights
- price: Integer price per unit
- quantity: Units to offer
- reasoning: Brief explanation of your strategy

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
Remember: The Wholesaler has more market information than you. Use what you learned in negotiations."""

    seller1_response: MarketOfferResponse = seller1_llm.invoke(seller1_prompt)

    offers["Seller_1"] = {
        "agent_name": "Seller_1",
        "price": seller1_response.price,
        "quantity": min(seller1_response.quantity, s1_inv["inventory"]),
        "inventory_available": s1_inv["inventory"]
    }

    seller1_scratchpad_update = f"\n[Day {day} pricing]: {seller1_response.scratchpad_update}"

    # Seller 2 sets offer (similar to Seller 1)
    seller2_llm = create_agent_llm(config.seller2, structured_output_schema=MarketOfferResponse)
    seller2_tools = SellerTools(state, "Seller_2")

    s2_inv = seller2_tools.get_my_inventory()
    s2_stats = seller2_tools.calculate_my_sales_stats()
    s2_scratchpad = state["agent_scratchpads"]["Seller_2"]

    # DEBUG: Log Seller_2 inventory at the start of set_market_offers
    logger.info(f"  [INVENTORY DEBUG] Day {day} - set_market_offers - Seller_2 inventory from state: {s2_inv['inventory']} units")

    # Get economic priors
    seller2_priors = get_economic_priors(state, "Seller_2", context="pricing")

    seller2_prompt = f"""{seller2_priors}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Current Inventory: {s2_inv['inventory']} units
- Your Last 20 Days Sales Stats: {s2_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{s2_scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review the ECONOMIC CONTEXT above - consider time remaining and inventory urgency
STEP 2: Review your scratchpad - what have you learned from negotiations with the Wholesaler?
STEP 3: Analyze your recent sales performance and inventory.
STEP 4: Decide on price and quantity strategy.

Provide your response with:
- scratchpad_update: Concise notes to ADD - any new insights
- price: Integer price per unit
- quantity: Units to offer
- reasoning: Brief explanation of your strategy

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
Remember: The Wholesaler has more market information than you. Use what you learned in negotiations."""

    seller2_response: MarketOfferResponse = seller2_llm.invoke(seller2_prompt)

    offers["Seller_2"] = {
        "agent_name": "Seller_2",
        "price": seller2_response.price,
        "quantity": min(seller2_response.quantity, s2_inv["inventory"]),
        "inventory_available": s2_inv["inventory"]
    }

    seller2_scratchpad_update = f"\n[Day {day} pricing]: {seller2_response.scratchpad_update}"

    return {
        "daily_market_offers": offers,
        "agent_scratchpads": {
            "Wholesaler": state["agent_scratchpads"]["Wholesaler"] + wholesaler_scratchpad_update,
            "Seller_1": state["agent_scratchpads"]["Seller_1"] + seller1_scratchpad_update,
            "Seller_2": state["agent_scratchpads"]["Seller_2"] + seller2_scratchpad_update
        }
    }


@log_node_execution
def run_market_simulation(state: EconomicState) -> Dict[str, Any]:
    """
    Run the priority match algorithm to clear the market.
    Matches highest-paying shoppers with lowest-priced sellers.
    """
    shoppers = state["daily_shopper_pool"].copy()
    offers = state["daily_market_offers"]
    day = state["day"]

    logger.debug(f"  → Running market simulation: {len(shoppers)} shoppers, {len(offers)} sellers")

    # Create flat list of seller offers sorted by price (ascending)
    seller_list = []
    for agent_name, offer in offers.items():
        if offer["quantity"] > 0 and offer["inventory_available"] > 0:
            for _ in range(offer["quantity"]):
                seller_list.append({
                    "agent_name": agent_name,
                    "price": offer["price"],
                    "unit": 1
                })

    seller_list.sort(key=lambda x: x["price"])

    # Two-pointer matching algorithm
    new_unmet_demand_log = []

    # Track quantities sold per agent
    quantities_sold = {agent: 0 for agent in offers.keys()}

    # Track shopper demand fulfillment
    shopper_purchases = {}

    i = 0  # Shopper pointer
    j = 0  # Seller pointer

    while i < len(shoppers) and j < len(seller_list):
        shopper = shoppers[i]
        seller = seller_list[j]

        if shopper["willing_to_pay"] >= seller["price"]:
            # Match!
            quantities_sold[seller["agent_name"]] += 1

            # Track shopper purchase
            if shopper["shopper_id"] not in shopper_purchases:
                shopper_purchases[shopper["shopper_id"]] = 0
            shopper_purchases[shopper["shopper_id"]] += 1

            i += 1
            j += 1
        else:
            # No match - shopper's price too low
            unmet = {
                "day": day,
                "shopper_id": shopper["shopper_id"],
                "willing_to_pay": shopper["willing_to_pay"],
                "quantity": 1
            }
            new_unmet_demand_log.append(unmet)
            i += 1

    # Remaining shoppers are unmet
    while i < len(shoppers):
        shopper = shoppers[i]
        unmet = {
            "day": day,
            "shopper_id": shopper["shopper_id"],
            "willing_to_pay": shopper["willing_to_pay"],
            "quantity": 1
        }
        new_unmet_demand_log.append(unmet)
        i += 1

    # Create aggregated market log entries (one per seller per day)
    new_market_log = []
    for agent_name, qty in quantities_sold.items():
        if qty > 0:
            trade = {
                "day": day,
                "buyer": "Market",  # Aggregate of all shoppers
                "seller": agent_name,
                "quantity": qty,
                "price": offers[agent_name]["price"]
            }
            new_market_log.append(trade)

    # Update agent ledgers
    new_ledgers = {}
    for agent_name, ledger in state["agent_ledgers"].items():
        if agent_name in quantities_sold and quantities_sold[agent_name] > 0:
            qty = quantities_sold[agent_name]
            price = offers[agent_name]["price"]
            revenue = qty * price

            # Log individual agent sales
            logger.info(f"    {agent_name} sold {qty} units at ${price}/unit (Revenue: ${revenue})")

            # DEBUG: Log Seller_2 inventory changes
            if agent_name == "Seller_2":
                old_inventory = ledger["inventory"]
                new_inventory = old_inventory - qty
                logger.info(f"  [INVENTORY DEBUG] Day {day} - run_market_simulation - Seller_2 inventory: {old_inventory} → {new_inventory} (sold {qty} units)")

            new_ledger = {
                **ledger,
                "inventory": ledger["inventory"] - qty,
                "cash": ledger["cash"] + revenue,
                "total_revenue": ledger["total_revenue"] + revenue,
                "private_sales_log": ledger["private_sales_log"] + [{
                    "day": day,
                    "price": price,
                    "quantity": qty
                }]
            }
            new_ledgers[agent_name] = new_ledger
        else:
            new_ledgers[agent_name] = ledger

    # Update shopper database
    new_shopper_database = []
    for shopper in state["shopper_database"]:
        if shopper["shopper_id"] in shopper_purchases:
            purchased = shopper_purchases[shopper["shopper_id"]]
            new_shopper = {
                **shopper,
                "demand_remaining": shopper["demand_remaining"] - purchased
            }
            new_shopper_database.append(new_shopper)
        else:
            new_shopper_database.append(shopper)

    # Log market results
    total_trades = len([t for t in new_market_log if t["day"] == day])
    total_unmet = len([u for u in new_unmet_demand_log if u["day"] == day])
    total_volume = sum(quantities_sold.values())
    total_revenue = sum(quantities_sold[agent] * offers[agent]["price"] for agent in quantities_sold if quantities_sold[agent] > 0)

    logger.info(f"  → Market Summary: {total_trades} trades, {total_volume} units sold, ${total_revenue} total revenue")
    logger.info(f"  → Unmet Demand: {total_unmet} shoppers couldn't find acceptable prices")
    logger.debug(f"      Sales breakdown: {quantities_sold}")

    return {
        "market_log": new_market_log,
        "unmet_demand_log": new_unmet_demand_log,
        "agent_ledgers": new_ledgers,
        "shopper_database": new_shopper_database
    }


@log_node_execution
def apply_daily_depreciation(state: EconomicState) -> Dict[str, Any]:
    """
    Apply daily depreciation to inventory book values.

    Uses linear depreciation: 1% per day over num_days period.
    This reflects the time-value of holding perishable inventory.
    """
    num_days = state["num_days"]
    current_day = state["day"]

    new_ledgers = {}
    for agent_name, ledger in state["agent_ledgers"].items():
        initial_value = ledger.get("initial_inventory_value", 0.0)

        if initial_value > 0:
            # Linear depreciation: depreciate total value evenly over num_days
            daily_depreciation = initial_value / num_days
            new_accumulated_depreciation = ledger["accumulated_depreciation"] + daily_depreciation
            new_book_value = initial_value - new_accumulated_depreciation

            # Ensure book value doesn't go negative
            new_book_value = max(0.0, new_book_value)

            new_ledger = {
                **ledger,
                "accumulated_depreciation": new_accumulated_depreciation,
                "book_value_remaining": new_book_value
            }
            new_ledgers[agent_name] = new_ledger

            logger.debug(f"  [DEPRECIATION] {agent_name}: Daily depreciation ${daily_depreciation:.2f}, "
                        f"Book value: ${new_book_value:.2f} (accumulated: ${new_accumulated_depreciation:.2f})")
        else:
            new_ledgers[agent_name] = ledger

    return {"agent_ledgers": new_ledgers}


@log_node_execution
def increment_day(state: EconomicState) -> Dict[str, Any]:
    """Increment the day counter."""
    return {"day": state["day"] + 1}

