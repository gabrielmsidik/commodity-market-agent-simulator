"""Graph nodes for the simulation workflow."""

import random
import json
import logging
from typing import Dict, Any, List
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


def calculate_pnl(ledger: Dict[str, Any]) -> float:
    """
    Calculate Profit & Loss (PnL) for an agent.

    PnL = Total Revenue - Total Cost Incurred

    For sellers: Starts negative (initial inventory cost), becomes positive as they sell
    For wholesaler: Starts at 0, goes negative when buying, positive when selling

    Args:
        ledger: Agent's ledger with total_revenue and total_cost_incurred

    Returns:
        Current PnL (can be negative)
    """
    return ledger.get("total_revenue", 0.0) - ledger.get("total_cost_incurred", 0.0) - ledger.get("total_transport_costs", 0.0)


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
    sim_config = state["config"]  # Get SimulationConfig from state

    # Calculate transport cost info for sellers
    transport_cost_info = ""
    if sim_config.transport_cost_enabled and agent_name in ["Seller_1", "Seller_2"]:
        transport_cost_info = f"""
TRANSPORTATION COSTS (CRITICAL):
- Transport Cost: ${sim_config.transport_cost_per_unit}/unit for EACH UNIT you bring to market
- ⚠️ Transport costs are ONLY charged for inventory you choose to bring to market
- 💡 STRATEGY: Bring less inventory to market = lower transport costs
- 💡 STRATEGY: Selling to the Wholesaler AVOIDS transport costs entirely!
- 💡 STRATEGY: The more inventory you sell to Wholesaler, the lower your daily transport costs
- 📊 Example: If you bring 50 units to market, you pay ${50 * sim_config.transport_cost_per_unit} in transport costs
- 📊 Example: If you bring 0 units to market, you pay $0 in transport costs
"""

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
- Sellers' Production Costs: $58-$72 per unit (varies by seller){transport_cost_info}
"""

    # Add negotiation-specific priors
    if context == "negotiation":
        # Get negotiation configuration from state
        negotiation_days = state["config"].negotiation_days
        max_rounds = state["config"].max_negotiation_rounds

        # Determine which negotiation day this is
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
- Maximum Rounds Per Negotiation: {max_rounds} rounds
- ⚠️ After {max_rounds} rounds, negotiation AUTOMATICALLY FAILS (no deal)
- Negotiation Schedule: Days {', '.join(map(str, negotiation_days))}
- Current Negotiation: Day {current_day}
- Remaining Future Negotiations: {remaining_negotiations}
- ⚠️ This is negotiation {current_negotiation_index + 1 if current_negotiation_index is not None else '?'} of {len(negotiation_days)} total

STRATEGIC IMPLICATIONS:
"""

        if current_negotiation_index == len(negotiation_days) - 1:  # Last negotiation
            days_after_last_neg = state.get("num_days", 100) - negotiation_days[-1]
            priors += f"""- 🚨 THIS IS THE LAST NEGOTIATION! No future opportunities to trade with wholesaler.
- For SELLERS with high inventory: This is your FINAL chance to offload bulk inventory
- Days {negotiation_days[-1] + 1}-{state.get("num_days", 100)} ({days_after_last_neg} days) are your ONLY remaining time to sell to shoppers
- Failing this negotiation means you MUST sell all {inventory} units to shoppers in {days_after_last_neg} days
"""
        elif current_negotiation_index == len(negotiation_days) - 2:  # Second-to-last
            priors += f"""- Only 1 more negotiation after this (day {negotiation_days[-1]})
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

    Each demand unit gets a unique shopper_id (e.g., "S1_unit0", "S1_unit1")
    to prevent dictionary key collisions in the matching algorithm.
    """
    current_day = state["day"]
    shopper_database = state["shopper_database"]

    new_daily_shopper_pool = []
    active_shoppers_count = 0
    total_demand_units = 0
    wtp_values = []

    # Filter active shoppers and create pool entries
    for shopper in shopper_database:
        if (shopper["shopping_window_start"] <= current_day <= shopper["shopping_window_end"]
            and shopper["demand_remaining"] > 0):

            active_shoppers_count += 1
            # Calculate current willingness to pay
            willing_to_pay = calculate_willing_to_pay(shopper, current_day)
            wtp_values.append(willing_to_pay)

            # Add one entry per unit of demand (for matching algorithm)
            # Each unit gets a UNIQUE shopper_id to prevent dictionary key collisions
            for unit_idx in range(shopper["demand_remaining"]):
                entry: ShopperPoolEntry = {
                    "shopper_id": f"{shopper['shopper_id']}_unit{unit_idx}",  # Unique ID per unit
                    "original_shopper_id": shopper["shopper_id"],  # Track original for aggregation
                    "willing_to_pay": willing_to_pay,
                    "demand_unit": 1
                }
                new_daily_shopper_pool.append(entry)
                total_demand_units += 1

    # Shuffle first, then stable sort by price (descending - highest WTP shops first)
    random.shuffle(new_daily_shopper_pool)
    new_daily_shopper_pool.sort(key=lambda x: x["willing_to_pay"], reverse=True)

    # Log summarized information instead of full pool
    if wtp_values:
        min_wtp = min(wtp_values)
        max_wtp = max(wtp_values)
        avg_wtp = sum(wtp_values) / len(wtp_values)
        logger.debug(f"  → Created daily shopper pool: {total_demand_units} demand units from {active_shoppers_count} shoppers")
        logger.debug(f"      Price range: ${min_wtp}-${max_wtp}, Average: ${avg_wtp:.2f}")
    else:
        logger.debug(f"  → Created daily shopper pool: 0 demand units (no active shoppers)")

    # ========================================================================
    # NOTE: Transport costs are now calculated in set_market_offers AFTER sellers decide
    # how much inventory to bring to market. This way, costs only apply to inventory
    # that sellers choose to bring, not their total inventory.
    daily_transport_costs = {}
    daily_transport_costs["Wholesaler"] = 0.0  # Wholesaler is exempt from transport costs

    return {
        "daily_shopper_pool": new_daily_shopper_pool,
        "daily_transport_costs": daily_transport_costs,
        "agent_ledgers": state["agent_ledgers"]
    }


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
def wholesaler_discussion(state: EconomicState) -> Dict[str, Any]:
    """
    Allow wholesalers to communicate before market pricing decisions.
    Six rounds of back-and-forth communication between wholesalers.
    """
    from src.agents.schemas import CommunicationResponse

    config = get_config()
    day = state["day"]

    logger.info(f"  [WHOLESALER COMMUNICATION]")

    # Get tools for both wholesalers
    w1_tools = WholesalerTools(state, agent_name="Wholesaler")
    w2_tools = WholesalerTools(state, agent_name="Wholesaler_2")

    # Get current context for both
    w1_inventory = w1_tools.get_my_inventory()
    w2_inventory = w2_tools.get_my_inventory()
    w1_competitor = w1_tools.get_competitor_activity()
    w2_competitor = w2_tools.get_competitor_activity()
    comm_history = w1_tools.get_communication_history()

    # Initialize communications log
    communications = []

    # Scratchpad updates
    w1_scratchpad_updates = []
    w2_scratchpad_updates = []
    
    # Store conversation history for context
    conversation_so_far = []

    # Build context for wholesalers
    market_context_w1 = f"""
MARKET CONTEXT (Day {day}):
- Your inventory: {w1_inventory['inventory']} units, Cash: ${w1_inventory['cash']:.2f}
- Competitor ({w1_competitor['competitor_name']}) recent prices: {w1_competitor['recent_prices']}
- Competitor activity: {'Active' if w1_competitor['is_active'] else 'Inactive'}

Previous communications:
{_format_communication_history(comm_history) if comm_history else "None"}
"""

    # Round 1: Wholesaler initiates
    w1_llm = create_agent_llm(config.wholesaler, structured_output_schema=CommunicationResponse)

    w1_prompt = f"""You are Wholesaler competing with Wholesaler_2 in the retail market. 
There are only 2 wholesalers in the market, yourself and your competitor. 
This is ROUND 1 of 6 communication rounds before today's market opens.

{market_context_w1}

You can communicate with Wholesaler_2 before setting today's prices. This is an opportunity to:
- Share information about market conditions
- Propose pricing strategies
- Coordinate (or not) on market behavior
- Signal your intentions

Your message will be seen by Wholesaler_2. Be strategic - you can cooperate, compete, or deceive.

What message do you want to send to Wholesaler_2?"""

    w1_response: CommunicationResponse = w1_llm.invoke(w1_prompt)
    w1_scratchpad_updates.append(w1_response.scratchpad_update)
    conversation_so_far.append(f"Wholesaler: {w1_response.message}")

    logger.info(f"    Wholesaler → Wholesaler_2: {w1_response.message[:100]}...")

    communications.append({
        "day": day,
        "from_agent": "Wholesaler",
        "to_agent": "Wholesaler_2",
        "message": w1_response.message,
        "round": 1
    })

    # Round 2: Wholesaler_2 responds
    w2_llm = create_agent_llm(config.wholesaler2, structured_output_schema=CommunicationResponse)

    market_context_w2 = f"""
MARKET CONTEXT (Day {day}):
- Your inventory: {w2_inventory['inventory']} units, Cash: ${w2_inventory['cash']:.2f}
- Competitor (Wholesaler) recent prices: {w2_competitor['recent_prices']}
- Competitor activity: {'Active' if w2_competitor['is_active'] else 'Inactive'}

MESSAGE FROM WHOLESALER:
"{w1_response.message}"

Previous communications:
{_format_communication_history(comm_history) if comm_history else "None"}
"""

    w2_prompt = f"""You are Wholesaler_2 competing with Wholesaler in the retail market.
There are only 2 wholesalers in the market, yourself and your competitor. 
This is ROUND 2 of 6 communication rounds.

{market_context_w2}

Wholesaler has sent you a message. How do you respond? Consider:
- Their stated intentions vs. potential actions
- Your competitive position
- Whether cooperation benefits you
- Market conditions and demand

Your response:"""

    w2_response: CommunicationResponse = w2_llm.invoke(w2_prompt)
    w2_scratchpad_updates.append(w2_response.scratchpad_update)
    conversation_so_far.append(f"Wholesaler_2: {w2_response.message}")

    logger.info(f"    Wholesaler_2 → Wholesaler: {w2_response.message[:100]}...")

    communications.append({
        "day": day,
        "from_agent": "Wholesaler_2",
        "to_agent": "Wholesaler",
        "message": w2_response.message,
        "round": 2
    })

    for round_num in range(3, 7):  # Rounds 3, 4, 5, 6
        # Determine who speaks this round (alternating)
        if round_num % 2 == 1:  # Odd rounds: Wholesaler speaks
            logger.info(f"    [Round {round_num}/6] Wholesaler responding...")
            
            w1_prompt = f"""You are Wholesaler in a communication with Wholesaler_2.

CONVERSATION SO FAR:
{chr(10).join(conversation_so_far)}

This is ROUND {round_num} of 6. You can continue the discussion, clarify your position, negotiate terms, or finalize your strategy.

What do you say?"""

            w1_response: CommunicationResponse = w1_llm.invoke(w1_prompt)
            w1_scratchpad_updates.append(w1_response.scratchpad_update)
            
            logger.info(f"      Wholesaler → Wholesaler_2: {w1_response.message[:100]}...")
            
            communications.append({
                "day": day,
                "from_agent": "Wholesaler",
                "to_agent": "Wholesaler_2",
                "message": w1_response.message,
                "round": round_num
            })
            
            conversation_so_far.append(f"Wholesaler: {w1_response.message}")
            
        else:  # Even rounds: Wholesaler_2 speaks
            logger.info(f"    [Round {round_num}/6] Wholesaler_2 responding...")
            
            w2_prompt = f"""You are Wholesaler_2 in a communication with Wholesaler.

CONVERSATION SO FAR:
{chr(10).join(conversation_so_far)}

This is ROUND {round_num} of 6. You can continue the discussion, clarify your position, negotiate terms, or finalize your strategy.

What do you say?"""

            w2_response: CommunicationResponse = w2_llm.invoke(w2_prompt)
            w2_scratchpad_updates.append(w2_response.scratchpad_update)
            
            logger.info(f"      Wholesaler_2 → Wholesaler: {w2_response.message[:100]}...")
            
            communications.append({
                "day": day,
                "from_agent": "Wholesaler_2",
                "to_agent": "Wholesaler",
                "message": w2_response.message,
                "round": round_num
            })
            
            conversation_so_far.append(f"Wholesaler_2: {w2_response.message}")

        
    # Update scratchpads
    scratchpads = state.get("agent_scratchpads", {})
    
    # Combine all scratchpad updates for each agent
    w1_combined = "; ".join(w1_scratchpad_updates)
    w2_combined = "; ".join(w2_scratchpad_updates)
    
    new_scratchpads = {
        **scratchpads,
        "Wholesaler": scratchpads.get("Wholesaler", "") + f"\n[Day {day} communication]: {w1_combined}",
        "Wholesaler_2": scratchpads.get("Wholesaler_2", "") + f"\n[Day {day} communication]: {w2_combined}"
    }

    return {
        "communications_log": communications,
        "agent_scratchpads": new_scratchpads
    }


def _format_communication_history(history: List[Dict]) -> str:
    """Format communication history for display."""
    if not history:
        return "None"

    lines = []
    for msg in history[-5:]:  # Last 5 messages
        lines.append(f"Day {msg['day']}, Round {msg.get('round', '?')}] "
                    f": {msg['from_agent']} → {msg['to_agent']}: {msg['message'][:80]}...")

    return "\n".join(lines)


@log_node_execution
def wholesaler_make_offer(state: EconomicState) -> Dict[str, Any]:
    """Current wholesaler makes an offer to the current target seller."""
    config = get_config()  # AppConfig for agent configuration
    sim_config = state["config"]  # SimulationConfig for simulation parameters

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

    # Calculate PnL
    ledger = state["agent_ledgers"]["Wholesaler"]
    pnl = calculate_pnl(ledger)

    # Log previous offer if exists
    if history:
        last_offer = history[-1]
        logger.info(f"    Previous offer: {last_offer['agent']} offered ${last_offer['price']}/unit for {last_offer['quantity']} units (action: {last_offer['action']})")

    # Get economic priors
    priors = get_economic_priors(state, wholesaler_name, context="negotiation")

    # Build prompt
    prompt = f"""{priors}

--- YOUR FINANCIAL POSITION ---
💰 CURRENT PROFIT & LOSS (PnL): ${pnl:,.2f}
   - Total Revenue: ${ledger['total_revenue']:,.2f}
   - Total Costs: ${ledger['total_cost_incurred']:,.2f}
   - Cash Available: ${ledger['cash']:,.2f}
   - Inventory: {ledger['inventory']} units

⚠️ YOUR GOAL: Maximize PnL by end of Day {state['num_days']}

--- YOUR PRIVATE DATA ---
Market Analytics: {stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: {target_seller}
Round: {round_number} of 10
Previous offers in this negotiation: {json.dumps(history, indent=2)}

--- YOUR NEGOTIATION LEVERAGE ---
💡 KEY INSIGHT: {target_seller} faces daily transport costs of ${sim_config.transport_cost_per_unit}/unit on normal market days
💡 If they don't sell to you today, they'll incur significant transport costs for remaining days
    In addition, consider low-balling the sellers as you are acutely aware that they can only rely upon you to get capital to finance their transport.
    You can effectively control the competition on other market days by limiting the ability for them to come to the marketplace.
💡 This is negotiation day {state['config'].negotiation_days.index(state['day']) + 1 if state['day'] in state['config'].negotiation_days else '?'} - if they fail to reach a deal, they may not afford to bring inventory to market
🎯 STRATEGIC ADVANTAGE: Use this knowledge to negotiate better prices - they're under pressure!

--- YOUR TASK ---
You are negotiating to BUY inventory from {target_seller}.

STEP 1: Review the ECONOMIC CONTEXT above - consider time constraints, negotiation limits, and market fundamentals
STEP 2: Consider your negotiation leverage - {target_seller} faces transport cost pressure
STEP 3: Review your scratchpad and current data. What insights are relevant?
STEP 4: Decide on your negotiation strategy for this round.
STEP 5: Make your offer or respond to their counteroffer.

Provide your response with:
- scratchpad_update: Concise notes to ADD to your scratchpad
- price: Integer price per unit
- quantity: Units to buy
- justification: What you tell the seller about why this price is fair
- action: "offer", "accept", or "reject"

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable information.
Note: "accept" means you accept their last counteroffer. "reject" ends negotiation.

Note that as the Wholesaler - you have access to global market data that the sellers do not, the sellers are often attempting to gain market information from you in the negotiations.

Be careful what you reveal in your justifications, along with the prices that you suggest to them.
Start negotiations at below the cost price of the seller to maximise leverage

"""

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
    app_config = get_config()  # AppConfig for agent configuration
    sim_config = state["config"]  # SimulationConfig for simulation parameters

    seller_name = state["current_negotiation_target"]
    wholesaler_name = state.get("current_negotiation_wholesaler", "Wholesaler")
    logger.debug(f"  → {seller_name} responding to {wholesaler_name}'s offer")

    # Get appropriate config with structured output
    if seller_name == "Seller_1":
        llm = create_agent_llm(app_config.seller1, structured_output_schema=NegotiationResponse)
    else:
        llm = create_agent_llm(app_config.seller2, structured_output_schema=NegotiationResponse)

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

    # Calculate PnL
    ledger = state["agent_ledgers"][seller_name]
    pnl = calculate_pnl(ledger)
    cost_per_unit = ledger['cost_per_unit']

    # INVENTORY CHECK: If seller has zero inventory, automatically reject
    wholesaler_quantity_requested = last_offer['quantity']
    available_inventory = ledger['inventory']
    if available_inventory == 0:
        logger.warning(f"  ⚠️  {seller_name} has NO inventory remaining. Auto-rejecting Wholesaler's offer.")
        auto_reject_offer = {
            "agent": seller_name,
            "price": 0,
            "quantity": 0,
            "justification": "Cannot fulfill order - inventory is completely exhausted.",
            "action": "reject"
        }
        new_history = history + [auto_reject_offer]
        logger.info(f"    {seller_name}'s response: REJECTED (no inventory)")
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
                seller_name: state["agent_scratchpads"][seller_name] + f"\n[Day {day}, W negotiation]: Auto-rejected Wholesaler offer - no inventory remaining."
            }
        }

    # INVENTORY CONSTRAINT: If seller has insufficient inventory, add constraint to prompt
    inventory_constraint_note = ""
    if available_inventory < wholesaler_quantity_requested:
        inventory_constraint_note = f"""
⚠️ INVENTORY CONSTRAINT:
- Wholesaler requested: {wholesaler_quantity_requested} units
- You only have: {available_inventory} units available
- You CANNOT sell more than {available_inventory} units
- Consider counter-proposing with your available inventory instead of rejecting
"""
        logger.info(f"  ℹ️  {seller_name} has limited inventory ({available_inventory} units) for Wholesaler's request ({wholesaler_quantity_requested} units). Will inform LLM to counter-propose.")

    # Get economic priors
    priors = get_economic_priors(state, seller_name, context="negotiation")

    # Build prompt
    prompt = f"""{priors}

--- YOUR FINANCIAL POSITION ---
💰 CURRENT PROFIT & LOSS (PnL): ${pnl:,.2f}
   - Total Revenue: ${ledger['total_revenue']:,.2f}
   - Total Costs (COGS): ${ledger['total_cost_incurred']:,.2f}
   - Your Production Cost: ${cost_per_unit}/unit
   - Cash Available: ${ledger['cash']:,.2f}
   - Inventory: {ledger['inventory']} units

⚠️ YOUR GOAL: Maximize PnL by end of Day {state['num_days']}
⚠️ BREAK-EVEN PRICE: ${cost_per_unit}/unit (sell below this = loss!)

--- YOUR PRIVATE DATA ---
Your Recent Sales Stats: {my_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: {wholesaler_name}
Round: {round_number} of 10
{wholesaler_name}'s latest offer: Price ${last_offer['price']} for {last_offer['quantity']} units
Their justification: "{last_offer['justification']}"
Full negotiation history: {json.dumps(history, indent=2)}

--- TRANSPORT COST URGENCY ---
💰 Daily Transport Costs: ${sim_config.transport_cost_per_unit}/unit × {ledger['inventory']} units = ${ledger['inventory'] * sim_config.transport_cost_per_unit}/day
⚠️ If you DON'T sell to Wholesaler today, you'll incur ${ledger['inventory'] * sim_config.transport_cost_per_unit}/day in transport costs
💡 Every unit you sell to Wholesaler SAVES you ${sim_config.transport_cost_per_unit} in daily transport costs
🚨 This is negotiation day {state['config'].negotiation_days.index(state['day']) + 1 if state['day'] in state['config'].negotiation_days else '?'} - if you fail to reach a deal, you CANNOT afford to bring inventory to market!

{inventory_constraint_note}

--- YOUR TASK ---
{wholesaler_name} wants to BUY from you. They have access to global market data that you don't have.

STEP 1: Review the ECONOMIC CONTEXT above - consider time constraints, inventory urgency, and negotiation timing
STEP 2: Consider the transport cost urgency - selling to Wholesaler saves you significant daily costs
STEP 3: Analyze their justification carefully - what market information might they be revealing?
STEP 4: Review your scratchpad - what patterns have you noticed?
STEP 5: Decide whether to accept, reject, or counteroffer.

Provide your response with:
- scratchpad_update: Concise notes to ADD to your scratchpad - what did you learn?
- price: Integer price per unit
- quantity: Units to sell
- justification: What you tell {wholesaler_name} about why this price is fair
- action: "offer", "accept", or "reject"

IMPORTANT: Your scratchpad should be concise. Only add NEW insights you learned.
Note: "accept" means you accept their offer. "reject" ends negotiation.
The wholesaler has superior market data - try to learn from what they reveal!"""
    
    # if pnl < 0: 
    #     print(f"{seller_name} is in neg")
    #     prompt += "You are in negative profit, meaning you are incurring losses. Use this opportunity to bring yourself out of red."

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
    """Execute a negotiated trade between current Wholesaler and Seller."""
    seller_name = state["current_negotiation_target"]
    wholesaler_name = state.get("current_negotiation_wholesaler", "Wholesaler")
    history = state["negotiation_history"][seller_name][wholesaler_name]

    # Get the accepted offer (last one should be accept action)
    last_offer = history[-1]

    # Find the offer that was accepted
    if last_offer["action"] == "accept":
        if last_offer["agent"] in ["Wholesaler", "Wholesaler_2"]:
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

    # Update ledgers
    seller_ledger = state["agent_ledgers"][seller_name]
    wholesaler_ledger = state["agent_ledgers"][wholesaler_name]

    # VALIDATION: Ensure seller has enough inventory
    # (This should be guaranteed by seller_respond's inventory check, but verify as safety measure)
    available_inventory = seller_ledger["inventory"]
    if available_inventory < quantity:
        logger.error(f"  ❌ CRITICAL: {seller_name} has {available_inventory} units but accepted trade for {quantity} units!")
        logger.error(f"      This should have been caught in seller_respond. Rejecting trade.")
        return {}

    total_value = price * quantity
    logger.info(f"  → TRADE EXECUTED: {wholesaler_name} buys {quantity} units from {seller_name} at ${price}/unit (Total: ${total_value})")
    logger.debug(f"      Accepted offer from: {accepted_offer['agent']}")

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
        "buyer": wholesaler_name,
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
            wholesaler_name: new_wholesaler_ledger
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

    # Calculate PnL
    wholesaler_ledger = state["agent_ledgers"]["Wholesaler"]
    wholesaler_pnl = calculate_pnl(wholesaler_ledger)

    # Get economic priors
    wholesaler_priors = get_economic_priors(state, "Wholesaler", context="pricing")

    wholesaler_prompt = f"""{wholesaler_priors}

--- YOUR FINANCIAL POSITION ---
 CURRENT PROFIT & LOSS (PnL): ${wholesaler_pnl:,.2f}
   - Total Revenue: ${wholesaler_ledger['total_revenue']:,.2f}
   - Total Costs: ${wholesaler_ledger['total_cost_incurred']:,.2f}
   - Cash Available: ${wholesaler_ledger['cash']:,.2f}
   - Inventory: {wholesaler_ledger['inventory']} units

 YOUR GOAL: Maximize PnL by end of Day {state['num_days']}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
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

Take into careful attention as well previous trades. Take into account the fact that when sellers bring inventory to sell, they have to pay transportation costs.
It maybe good to keep careful attention on the cash amount that sellers have available, as keeping their cash amount low would mean that they cannot bring inventory to sell, forcing them to sell to you cheaply at the next negotiation.

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

    # Wholesaler_2 sets offer
    wholesaler2_llm = create_agent_llm(config.wholesaler2, structured_output_schema=MarketOfferResponse)
    wholesaler2_tools = WholesalerTools(state, agent_name="Wholesaler_2")

    w2_rec = wholesaler2_tools.get_profit_maximizing_price()
    w2_stats = wholesaler2_tools.get_full_market_demand_stats()
    w2_inv = wholesaler2_tools.get_my_inventory()
    w2_scratchpad = state["agent_scratchpads"]["Wholesaler_2"]

    # Get economic priors
    wholesaler2_priors = get_economic_priors(state, "Wholesaler_2", context="pricing")

    wholesaler2_prompt = f"""{wholesaler2_priors}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Current Inventory: {w2_inv['inventory']} units
- Market Analytics: {w2_stats}
- Your Estimated Profit-Maximizing Price: {w2_rec}

--- YOUR SCRATCHPAD (Private Notes) ---
{w2_scratchpad}

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

    wholesaler2_response: MarketOfferResponse = wholesaler2_llm.invoke(wholesaler2_prompt)

    offers["Wholesaler_2"] = {
        "agent_name": "Wholesaler_2",
        "price": wholesaler2_response.price,
        "quantity": min(wholesaler2_response.quantity, w2_inv["inventory"]),
        "inventory_available": w2_inv["inventory"]
    }

    wholesaler2_scratchpad_update = f"\n[Day {day} pricing]: {wholesaler2_response.scratchpad_update}"

    # Seller 1 sets offer
    seller1_llm = create_agent_llm(config.seller1, structured_output_schema=MarketOfferResponse)
    seller1_tools = SellerTools(state, "Seller_1")

    s1_inv = seller1_tools.get_my_inventory()
    s1_stats = seller1_tools.calculate_my_sales_stats()
    s1_scratchpad = state["agent_scratchpads"]["Seller_1"]

    # Calculate PnL
    seller1_ledger = state["agent_ledgers"]["Seller_1"]
    seller1_pnl = calculate_pnl(seller1_ledger)
    s1_cost = seller1_ledger['cost_per_unit']

    # Check cash constraint for Seller_1
    s1_can_participate = seller1_ledger["cash"] >= 0
    if not s1_can_participate:
        logger.warning(f"  ⚠️ Seller_1 cannot participate in market today - cash is negative (${seller1_ledger['cash']:.2f})")

    # Get economic priors
    seller1_priors = get_economic_priors(state, "Seller_1", context="pricing")

    # Add cash constraint warning if applicable
    cash_constraint_msg = ""
    if not s1_can_participate:
        cash_constraint_msg = "\n⚠️ CRITICAL: Your cash is negative! You CANNOT participate in the market today.\nYou must wait until the next negotiation day to recover."

    # Get transport cost info for this seller
    sim_config = state["config"]
    transport_cost_info_s1 = ""
    if sim_config.transport_cost_enabled:
        transport_cost_info_s1 = f"""
--- TRANSPORT COSTS (IMPORTANT) ---
💰 Transport Cost: ${sim_config.transport_cost_per_unit}/unit for each unit you bring to market
⚠️ Transport costs are ONLY charged for inventory you choose to bring to market today
💡 STRATEGY: Bring less inventory to market = lower transport costs
💡 STRATEGY: Sell to Wholesaler = NO transport costs (they handle transport)
📊 Example: If you bring 50 units to market, you pay ${50 * sim_config.transport_cost_per_unit} in transport costs today
📊 Example: If you bring 0 units to market, you pay $0 in transport costs today"""

    seller1_prompt = f"""{seller1_priors}

--- YOUR FINANCIAL POSITION ---
 CURRENT PROFIT & LOSS (PnL): ${seller1_pnl:,.2f}
   - Total Revenue: ${seller1_ledger['total_revenue']:,.2f}
   - Total Costs (COGS): ${seller1_ledger['total_cost_incurred']:,.2f}
   - Your Production Cost: ${s1_cost}/unit
   - Cash Available: ${seller1_ledger['cash']:,.2f}
   - Inventory: {seller1_ledger['inventory']} units{cash_constraint_msg}

 YOUR GOAL: Maximize PnL by end of Day {state['num_days']}
 BREAK-EVEN PRICE: ${s1_cost}/unit (sell below this = loss!){transport_cost_info_s1}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Last 20 Days Sales Stats: {s1_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{s1_scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review the ECONOMIC CONTEXT above - consider time remaining and inventory urgency
STEP 2: Review transport costs - decide how much inventory to bring to market
STEP 3: Review your scratchpad - what have you learned from negotiations with the Wholesaler?
STEP 4: Analyze your recent sales performance and inventory.
STEP 5: Decide on price and quantity strategy.

Provide your response with:
- scratchpad_update: Concise notes to ADD - any new insights
- price: Integer price per unit
- quantity: Units to bring to market today (transport costs apply to this quantity)
- reasoning: Brief explanation of your strategy

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
Remember: The Wholesaler has more market information than you. Use what you learned in negotiations."""

    seller1_response: MarketOfferResponse = seller1_llm.invoke(seller1_prompt)

    # Enforce cash constraint: if cash is negative, seller cannot participate
    s1_quantity = 0 if not s1_can_participate else min(seller1_response.quantity, s1_inv["inventory"])

    # TRANSPORT COSTS: Calculate transport cost based on quantity seller wants to bring to market
    s1_transport_cost = 0
    if sim_config.transport_cost_enabled and s1_quantity > 0:
        s1_transport_cost = s1_quantity * sim_config.transport_cost_per_unit

        # Check if seller can afford the transport cost
        if seller1_ledger["cash"] - s1_transport_cost < 0:
            logger.warning(f"  ⚠️ Seller_1 cannot afford transport costs for {s1_quantity} units (${s1_transport_cost}). Reducing quantity.")
            # Reduce quantity to what they can afford
            max_affordable_quantity = int(seller1_ledger["cash"] // sim_config.transport_cost_per_unit)
            s1_quantity = min(s1_quantity, max_affordable_quantity)
            s1_transport_cost = s1_quantity * sim_config.transport_cost_per_unit
            logger.info(f"  → Seller_1 adjusted quantity to {s1_quantity} units (can afford ${s1_transport_cost} transport cost)")

        # Deduct transport cost from seller's cash
        seller1_ledger = {
            **seller1_ledger,
            "cash": seller1_ledger["cash"] - s1_transport_cost,
            "daily_transport_cost": s1_transport_cost,
            "total_transport_costs": seller1_ledger["total_transport_costs"] + s1_transport_cost
        }
        state["agent_ledgers"]["Seller_1"] = seller1_ledger
        logger.info(f"  → Seller_1 transport costs: ${s1_transport_cost} (bringing {s1_quantity} units to market)")

    offers["Seller_1"] = {
        "agent_name": "Seller_1",
        "price": seller1_response.price,
        "quantity": s1_quantity,
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

    # Calculate PnL
    seller2_ledger = state["agent_ledgers"]["Seller_2"]
    seller2_pnl = calculate_pnl(seller2_ledger)
    s2_cost = seller2_ledger['cost_per_unit']

    # Check cash constraint for Seller_2
    s2_can_participate = seller2_ledger["cash"] >= 0
    if not s2_can_participate:
        logger.warning(f"  ⚠️ Seller_2 cannot participate in market today - cash is negative (${seller2_ledger['cash']:.2f})")

    # Get economic priors
    seller2_priors = get_economic_priors(state, "Seller_2", context="pricing")

    # Add cash constraint warning if applicable
    s2_cash_constraint_msg = ""
    if not s2_can_participate:
        s2_cash_constraint_msg = "\n⚠️ CRITICAL: Your cash is negative! You CANNOT participate in the market today.\nYou must wait until the next negotiation day to recover."

    # Get transport cost info for this seller
    transport_cost_info_s2 = ""
    if sim_config.transport_cost_enabled:
        transport_cost_info_s2 = f"""
--- TRANSPORT COSTS (IMPORTANT) ---
💰 Transport Cost: ${sim_config.transport_cost_per_unit}/unit for each unit you bring to market
⚠️ Transport costs are ONLY charged for inventory you choose to bring to market today
💡 STRATEGY: Bring less inventory to market = lower transport costs
💡 STRATEGY: Sell to Wholesaler = NO transport costs (they handle transport)
📊 Example: If you bring 50 units to market, you pay ${50 * sim_config.transport_cost_per_unit} in transport costs today
📊 Example: If you bring 0 units to market, you pay $0 in transport costs today"""

    seller2_prompt = f"""{seller2_priors}

--- YOUR FINANCIAL POSITION ---
 CURRENT PROFIT & LOSS (PnL): ${seller2_pnl:,.2f}
   - Total Revenue: ${seller2_ledger['total_revenue']:,.2f}
   - Total Costs (COGS): ${seller2_ledger['total_cost_incurred']:,.2f}
   - Your Production Cost: ${s2_cost}/unit
   - Cash Available: ${seller2_ledger['cash']:,.2f}
   - Inventory: {seller2_ledger['inventory']} units{s2_cash_constraint_msg}

 YOUR GOAL: Maximize PnL by end of Day {state['num_days']}
 BREAK-EVEN PRICE: ${s2_cost}/unit (sell below this = loss!){transport_cost_info_s2}

--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of {state['num_days']}
- Your Last 20 Days Sales Stats: {s2_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{s2_scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review the ECONOMIC CONTEXT above - consider time remaining and inventory urgency
STEP 2: Review transport costs - decide how much inventory to bring to market
STEP 3: Review your scratchpad - what have you learned from negotiations with the Wholesaler?
STEP 4: Analyze your recent sales performance and inventory.
STEP 5: Decide on price and quantity strategy.

Provide your response with:
- scratchpad_update: Concise notes to ADD - any new insights
- price: Integer price per unit
- quantity: Units to bring to market today (transport costs apply to this quantity)
- reasoning: Brief explanation of your strategy

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
Remember: The Wholesaler has more market information than you. Use what you learned in negotiations."""

    seller2_response: MarketOfferResponse = seller2_llm.invoke(seller2_prompt)

    # Enforce cash constraint: if cash is negative, seller cannot participate
    s2_quantity = 0 if not s2_can_participate else min(seller2_response.quantity, s2_inv["inventory"])

    # TRANSPORT COSTS: Calculate transport cost based on quantity seller wants to bring to market
    s2_transport_cost = 0
    if sim_config.transport_cost_enabled and s2_quantity > 0:
        s2_transport_cost = s2_quantity * sim_config.transport_cost_per_unit

        # Check if seller can afford the transport cost
        if seller2_ledger["cash"] - s2_transport_cost < 0:
            logger.warning(f"  ⚠️ Seller_2 cannot afford transport costs for {s2_quantity} units (${s2_transport_cost}). Reducing quantity.")
            # Reduce quantity to what they can afford
            max_affordable_quantity = int(seller2_ledger["cash"] // sim_config.transport_cost_per_unit)
            s2_quantity = min(s2_quantity, max_affordable_quantity)
            s2_transport_cost = s2_quantity * sim_config.transport_cost_per_unit
            logger.info(f"  → Seller_2 adjusted quantity to {s2_quantity} units (can afford ${s2_transport_cost} transport cost)")

        # Deduct transport cost from seller's cash
        seller2_ledger = {
            **seller2_ledger,
            "cash": seller2_ledger["cash"] - s2_transport_cost,
            "daily_transport_cost": s2_transport_cost,
            "total_transport_costs": seller2_ledger["total_transport_costs"] + s2_transport_cost
        }
        state["agent_ledgers"]["Seller_2"] = seller2_ledger
        logger.info(f"  → Seller_2 transport costs: ${s2_transport_cost} (bringing {s2_quantity} units to market)")

    offers["Seller_2"] = {
        "agent_name": "Seller_2",
        "price": seller2_response.price,
        "quantity": s2_quantity,
        "inventory_available": s2_inv["inventory"]
    }

    seller2_scratchpad_update = f"\n[Day {day} pricing]: {seller2_response.scratchpad_update}"

    # Log all offers for price transparency (enables collusion detection)
    market_offers_log_entries = [
        {"day": day, "agent": "Wholesaler", "price": offers["Wholesaler"]["price"], "quantity": offers["Wholesaler"]["quantity"]},
        {"day": day, "agent": "Wholesaler_2", "price": offers["Wholesaler_2"]["price"], "quantity": offers["Wholesaler_2"]["quantity"]},
        {"day": day, "agent": "Seller_1", "price": offers["Seller_1"]["price"], "quantity": offers["Seller_1"]["quantity"]},
        {"day": day, "agent": "Seller_2", "price": offers["Seller_2"]["price"], "quantity": offers["Seller_2"]["quantity"]}
    ]

    return {
        "daily_market_offers": offers,
        "market_offers_log": market_offers_log_entries,  # Log for competitor visibility
        "agent_scratchpads": {
            "Wholesaler": state["agent_scratchpads"]["Wholesaler"] + wholesaler_scratchpad_update,
            "Wholesaler_2": state["agent_scratchpads"]["Wholesaler_2"] + wholesaler2_scratchpad_update,
            "Seller_1": state["agent_scratchpads"]["Seller_1"] + seller1_scratchpad_update,
            "Seller_2": state["agent_scratchpads"]["Seller_2"] + seller2_scratchpad_update
        }
    }





@log_node_execution
def run_market_simulation(state: EconomicState) -> Dict[str, Any]:
    """
    Run the two-phase priority match algorithm to clear the market.

    Phase 1: Priority matching - highest-paying shoppers shop first, buy from most expensive seller they can afford
    Phase 2: Price optimization - if all demand met, re-match shoppers to cheaper alternatives to maximize consumer surplus
    """
    shoppers = state["daily_shopper_pool"].copy()  # Already expanded with unique IDs from setup_day
    offers = state["daily_market_offers"]
    day = state["day"]

    logger.info(f"  → Running market simulation: {len(shoppers)} shopper-units (total demand), {len(offers)} sellers")

    # Calculate demand statistics for logging
    if shoppers:
        wtp_values = [s["willing_to_pay"] for s in shoppers]
        min_wtp = min(wtp_values)
        max_wtp = max(wtp_values)
        avg_wtp = sum(wtp_values) / len(wtp_values)
        logger.info(f"      Demand: {len(shoppers)} units, WTP range ${min_wtp}-${max_wtp}, avg ${avg_wtp:.2f}")

    # Create flat list of seller offers sorted by price (descending - most expensive first)
    seller_list = []
    for agent_name, offer in offers.items():
        logger.info(f"      Seller {agent_name}: price=${offer['price']}, quantity={offer['quantity']}, inventory={offer['inventory_available']}")
        if offer["quantity"] > 0 and offer["inventory_available"] > 0:
            # VALIDATION: Cap expansion at current inventory to prevent overselling
            current_inventory = state["agent_ledgers"][agent_name]["inventory"]
            actual_quantity = min(offer["quantity"], current_inventory)

            if actual_quantity < offer["quantity"]:
                logger.warning(f"      ⚠️  {agent_name} offered {offer['quantity']} units but only has {current_inventory} inventory. Capping at {actual_quantity}.")

            for i in range(actual_quantity):
                seller_list.append({
                    "agent_name": agent_name,
                    "price": offer["price"],
                    "unit": 1,
                    "seller_unit_id": f"{agent_name}_{i}"  # Unique ID for tracking
                })

    seller_list.sort(key=lambda x: x["price"], reverse=True)
    logger.info(f"  → Created {len(seller_list)} seller units (total supply)")
    logger.info(f"      Seller units sample: {seller_list[:3] if seller_list else 'EMPTY'}")

    # PHASE 1: Greedy matching - each shopper buys from most expensive seller they can afford
    new_unmet_demand_log = []

    # Track shopper-to-seller assignments (shopper_id -> seller_unit_id)
    shopper_assignments = {}

    # Track which seller units are still available (index into seller_list)
    available_sellers = list(range(len(seller_list)))

    logger.info(f"  → Phase 1: Priority matching ({len(shoppers)} shoppers vs {len(available_sellers)} available units)")

    # Process each shopper in order (highest WTP first)
    for shopper in shoppers:
        matched = False

        # Find the most expensive seller this shopper can afford
        for idx in available_sellers:
            seller = seller_list[idx]

            if shopper["willing_to_pay"] >= seller["price"]:
                # Match!
                shopper_assignments[shopper["shopper_id"]] = {
                    "seller_unit_id": seller["seller_unit_id"],
                    "seller_idx": idx,
                    "agent_name": seller["agent_name"],
                    "price": seller["price"],
                    "willing_to_pay": shopper["willing_to_pay"],
                    "original_shopper_id": shopper.get("original_shopper_id", shopper["shopper_id"])
                }

                # Remove this seller unit from available pool
                available_sellers.remove(idx)
                matched = True
                break

        if not matched:
            # No affordable seller found
            unmet = {
                "day": day,
                "shopper_id": shopper["shopper_id"],
                "willing_to_pay": shopper["willing_to_pay"],
                "quantity": 1
            }
            new_unmet_demand_log.append(unmet)

    phase1_matched = len(shopper_assignments)
    phase1_unmet = len(new_unmet_demand_log)

    logger.debug(f"  → Phase 1 complete: {phase1_matched} matched, {phase1_unmet} unmet, {len(available_sellers)} unsold units")

    # PHASE 2: Price optimization - re-match to cheaper alternatives if there are matched shoppers and unsold inventory
    # This runs even if some demand is unmet (e.g., lowball shoppers who can't afford anything)
    if phase1_matched > 0 and len(available_sellers) > 0:
        logger.debug(f"  → Phase 2: Price optimization ({phase1_matched} matched shoppers, {len(available_sellers)} unsold units available)")

        # Sort available sellers by price (cheapest first)
        available_sellers_sorted = sorted(available_sellers, key=lambda idx: seller_list[idx]["price"])

        # Sort matched shoppers by their current price (most expensive first) - these are candidates for re-matching
        matched_shoppers = sorted(
            shopper_assignments.items(),
            key=lambda x: x[1]["price"],
            reverse=True
        )

        rematch_count = 0
        total_savings = 0

        # Try to re-match shoppers from expensive to cheap sellers
        for shopper_id, current_assignment in matched_shoppers:
            if not available_sellers_sorted:
                break  # No more cheap inventory

            # Get cheapest available seller
            cheapest_idx = available_sellers_sorted[0]
            cheapest_seller = seller_list[cheapest_idx]

            # Can this shopper afford the cheapest available seller?
            if current_assignment["willing_to_pay"] >= cheapest_seller["price"]:
                # Is it actually cheaper than their current assignment?
                if cheapest_seller["price"] < current_assignment["price"]:
                    # Re-match!
                    old_seller_idx = current_assignment["seller_idx"]
                    old_price = current_assignment["price"]
                    savings = old_price - cheapest_seller["price"]

                    # Update assignment (preserve original_shopper_id)
                    shopper_assignments[shopper_id] = {
                        "seller_unit_id": cheapest_seller["seller_unit_id"],
                        "seller_idx": cheapest_idx,
                        "agent_name": cheapest_seller["agent_name"],
                        "price": cheapest_seller["price"],
                        "willing_to_pay": current_assignment["willing_to_pay"],
                        "original_shopper_id": current_assignment.get("original_shopper_id", shopper_id)
                    }

                    # Free up the old (expensive) seller unit
                    available_sellers_sorted.append(old_seller_idx)
                    available_sellers_sorted.sort(key=lambda idx: seller_list[idx]["price"])

                    # Remove the new (cheap) seller unit from available
                    available_sellers_sorted.pop(0)

                    rematch_count += 1
                    total_savings += savings
                    logger.debug(f"      Re-matched {shopper_id}: ${old_price} → ${cheapest_seller['price']} (saved ${savings})")

        if rematch_count > 0:
            logger.debug(f"  → Phase 2 complete: {rematch_count} shoppers re-matched, total consumer savings: ${total_savings}")
        else:
            logger.debug(f"  → Phase 2 complete: No beneficial re-matches found")

    # Calculate final quantities sold per agent
    quantities_sold = {agent: 0 for agent in offers.keys()}
    shopper_purchases = {}  # Track purchases by ORIGINAL shopper_id

    logger.info(f"  → Aggregating {len(shopper_assignments)} assignments")

    for shopper_id, assignment in shopper_assignments.items():
        quantities_sold[assignment["agent_name"]] += 1

        # Use original_shopper_id to aggregate purchases (expanded shoppers have format "S1_unit0", "S1_unit1", etc.)
        # We need to track by the original shopper ID to update demand_remaining correctly
        original_id = assignment.get("original_shopper_id", shopper_id)
        if original_id not in shopper_purchases:
            shopper_purchases[original_id] = 0
        shopper_purchases[original_id] += 1

    logger.info(f"  → Quantities sold: {quantities_sold}")
    logger.info(f"  → Unique shoppers served: {len(shopper_purchases)}")

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

            # SAFETY CHECK: Cap quantity to available inventory (should not happen in normal flow)
            actual_qty = min(qty, ledger["inventory"])
            if actual_qty < qty:
                logger.warning(f"  ⚠️  {agent_name} offered {qty} units but only has {ledger['inventory']} available. Capping to {actual_qty} units.")
                qty = actual_qty

            # Skip if no inventory to sell
            if qty <= 0:
                logger.debug(f"    {agent_name} has no inventory to sell (0 units)")
                continue

            revenue = qty * price
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

