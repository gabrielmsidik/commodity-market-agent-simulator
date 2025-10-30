# 100-Day Economic Simulation - Architecture Documentation

This document provides the complete, consolidated specification for a 100-day, turn-based economic simulation. It details the demand-side logic, the agent-side (supply) logic, the core state, all agent toolkits, and the market-clearing "physics engine".

## Overview

The goal is to test a hypothesis on information asymmetry, where a Wholesaler agent with superior market data competes and negotiates with two Seller agents with limited private data.

## 1. Pre-Simulation Shopper Generation (Demand Side)

Before the 100-day loop begins, a global `shopper_database` must be created. This list is NOT part of the `EconomicState` and is NEVER shown to the agents.

### Shopper Data Structure

Each object in the `shopper_database` list will have this structure:

```python
class Shopper:
    shopper_id: str
    shopper_type: str # "long_term" or "short_term"
    total_demand: int # Total units they want over their window
    demand_remaining: int # Starts at total_demand

    # Shopping Window
    shopping_window_start: int
    shopping_window_end: int

    # Price Function
    base_willing_to_pay: float
    max_willing_to_pay: float # Price on their *last* day
    urgency_factor: float # Controls price acceleration curve (default: 1.0 = linear)
                          # < 1.0 = decelerating (willing to pay more early)
                          # > 1.0 = accelerating (panic increases near deadline)
                          # Recommended: 0.5-3.0
```

### Urgency Factor Explanation

The `urgency_factor` controls how a shopper's willingness to pay increases over their shopping window using a power curve:

**Formula:** `current_price = base_price + (max_price - base_price) * (time_progress ^ urgency_factor)`

Where `time_progress` is normalized between 0 (first day) and 1 (last day).

**Behavior:**
- `urgency_factor = 1.0`: Linear increase (constant rate)
- `urgency_factor < 1.0`: Decelerating curve (willing to pay more early, e.g., 0.5 = square root)
- `urgency_factor > 1.0`: Accelerating curve (panic near deadline, e.g., 2.0 = quadratic)

**Examples:**
- Long-term shoppers (0.7-1.2): More patient, gradual price increase
- Short-term shoppers (1.5-2.5): Urgent, rapid price increase near deadline

### Price Rounding Convention

**All prices used in market matching are integers.** While internal parameters (`base_willing_to_pay`, `max_willing_to_pay`, etc.) can be floats for calculation precision, the final `willing_to_pay` price calculated by the urgency function **must be rounded to the nearest integer** before being added to the `daily_shopper_pool`.

Similarly, all agent price offers (`daily_market_offers`) must be integers.

**Implementation:** Use `round()` function after calculating the urgency-adjusted price.

### Example Generation (Programmatic Logic)

You will write a Python script to generate this database:

```python
shopper_database = {} # Use a dict for O(1) lookup by shopper_id

# 1. Generate Long-Term Shoppers
for i in range(50): # e.g., 50 long-term shoppers
    start_day = random.randint(1, 80)
    window_days = random.randint(15, 25) # Long window
    base_price = random.uniform(80, 95) # Lower base price
    shopper_id = f"long_{i}"

    shopper_database[shopper_id] = Shopper(
        shopper_id=shopper_id,
        shopper_type="long_term",
        total_demand=random.randint(5, 10),
        demand_remaining=self.total_demand,
        shopping_window_start=start_day,
        shopping_window_end=start_day + window_days,
        base_willing_to_pay=base_price,
        max_willing_to_pay=base_price * random.uniform(1.2, 1.4), # 20-40% desperation increase
        urgency_factor=random.uniform(0.7, 1.2) # Moderate urgency curve
    )

# 2. Generate Short-Term Shoppers
for i in range(200): # e.g., 200 short-term (urgent) shoppers
    start_day = random.randint(1, 97)
    window_days = random.randint(2, 4) # Short window
    base_price = random.uniform(105.0, 120.0) # Higher base price
    shopper_id = f"short_{i}"

    shopper_database[shopper_id] = Shopper(
        shopper_id=shopper_id,
        shopper_type="short_term",
        total_demand=random.randint(1, 3),
        demand_remaining=self.total_demand,
        shopping_window_start=start_day,
        shopping_window_end=start_day + window_days,
        base_willing_to_pay=base_price,
        max_willing_to_pay=base_price * random.uniform(1.05, 1.15), # 5-15% desperation increase
        urgency_factor=random.uniform(1.5, 2.5) # Higher urgency (panic near deadline)
    )

```

## 2. The Core EconomicState (The "World Ledger")

This is the central state object managed by LangGraph. It contains all information that is passed between nodes.

```python
from typing import TypedDict, Annotated, List, Dict, Optional
import operator

class AgentLedger(TypedDict):
    """Holds the private financial state of a single agent."""
    inventory: int
    cash: float 
    total_cost_incurred: float # (COGS) Sum of (unit * cost_price)
    total_revenue: float
    private_sales_log: List[Dict] # Only logs sales this agent made

class MarketOffer(TypedDict):
    """A single agent's public offer for one day."""
    price: int # Must be an integer (rounded if calculated from float)
    quantity: int # The MAX number of units this agent will sell today

class EconomicState(TypedDict):
    """The entire state of the simulation for one day."""
    day: int
    
    # --- Public Logs (Wholesaler access only) ---
    market_log: Annotated[List[Dict], operator.add] 
    unmet_demand_log: Annotated[List[Dict], operator.add] 
    
    # --- Daily State (Reset each day) ---
    daily_shopper_pool: List[Dict] 
    daily_market_offers: Dict[str, MarketOffer] 
    
    # --- Agent-Specific State ---
    agent_ledgers: Dict[str, AgentLedger] 
    
    # --- Negotiation State (Used on days 1, 21, 41...) ---
    negotiation_status: str # "pending", "seller_1_negotiating", "seller_2_negotiating", "complete"
    current_negotiation_target: Optional[str] # "Seller_1" or "Seller_2" or None
    negotiation_history: Dict[str, List[Dict]] # Tracks all offers/counteroffers per seller

    # --- Agent Memory (Persistent across all days) ---
    agent_scratchpads: Dict[str, str] # Free-form text notes for each agent
                                       # Key: agent_name, Value: plain text string

```

## 3. Initial State, Cost Assumptions & Shared Context

### Initial World State (Stochastic Initialization)

This is the `initial_state` object fed into the graph on Day 1.

- **Shared Belief:** Cost price is ~60 for Seller 1 and ~70 for Seller 2.
- **Shared Belief:** Inventory is ~8000 for Seller 1 and ~2000 for Seller 2.
- **Actual (Hidden) Values:** We use these beliefs as a mean for randomization.

```python
# Example initialization script

S1_ACTUAL_COST = random.randint(58, 62)  # Integer cost
S1_ACTUAL_INV = random.randint(7800, 8200)
S2_ACTUAL_COST = random.randint(68, 72)  # Integer cost
S2_ACTUAL_INV = random.randint(1900, 2100)

initial_world_state = {
    "day": 1,
    "market_log": [],
    "unmet_demand_log": [],
    "daily_shopper_pool": [],
    "daily_market_offers": {},
    "agent_ledgers": {
        "Seller_1": {
            "inventory": S1_ACTUAL_INV,
            "cash": 10000.0, # Starting cash
            "total_cost_incurred": S1_ACTUAL_INV * S1_ACTUAL_COST,
            "total_revenue": 0.0,
            "private_sales_log": []
        },
        "Seller_2": {
            "inventory": S2_ACTUAL_INV,
            "cash": 5000.0,
            "total_cost_incurred": S2_ACTUAL_INV * S2_ACTUAL_COST,
            "total_revenue": 0.0,
            "private_sales_log": []
        },
        "Wholesaler": {
            "inventory": 0, # Starts with no inventory
            "cash": 50000.0, # High starting cash for purchases
            "total_cost_incurred": 0.0, # COGS is added *when* it buys
            "total_revenue": 0.0,
            "private_sales_log": []
        }
    },
    "negotiation_status": "pending",
    "current_negotiation_target": None,
    "negotiation_history": {
        "Seller_1": [],
        "Seller_2": []
    },
    "agent_scratchpads": {
        "Wholesaler": "",
        "Seller_1": "",
        "Seller_2": ""
    }
}
```

### Shared Context (Agent System Prompts)

This text is included in the system prompt of ALL agents (Wholesaler and Sellers) to establish baseline "market beliefs."

```
--- SHARED MARKET CONTEXT ---
You are an economic agent in a 100-day simulation.
- The historical market price for this product is around $100.
- There are two producers:
  1. Seller 1 (Large): Produces ~8000 units. Cost price is ~_60.
  2. Seller 2 (Small): Produces ~2000 units. Cost price is ~_70.
- A Wholesaler also participates in the market.
- Shoppers arrive at the market each day. Not all shoppers are present every day.
- Your goal is to maximize your own profit (PnL) by the end of Day 100.
```

## 4. Agent Analytical Toolkits (Information Asymmetry)

These are the Python functions provided to the agent nodes.

### Toolkit 1: Wholesaler (Sophisticated Tools)

**Access:** Global `market_log`, global `unmet_demand_log`, own `AgentLedger`.

**Available Functions:**

- `get_my_inventory()`: Returns `agent_ledgers["Wholesaler"]["inventory"]`.

- `get_full_market_history(last_n_days: int)`:
  - Reads the _entire_ `market_log` and `unmet_demand_log`.
  - Returns a full summary: `{"total_units_sold": X, "avg_sale_price": Y, "total_unmet_shoppers": Z, "highest_rejected_price": Q}`

- `get_demand_price_elasticity()`: Reads the `market_log` (price, units sold).
  - Runs a `scipy.stats.linregress` on `log(price)` vs `log(quantity_sold)`.
  - Returns: `{"elasticity": float, "confidence": "high/medium/low"}`.
  - (Becomes more accurate as more data is logged)

- `get_profit_maximizing_price()`:
  - Uses the `get_demand_price_elasticity()` output.
  - Calculates the theoretical profit-maximizing price.
  - Returns: `{"recommended_price": float}`.

### Toolkit 2: Sellers (Simple Tools)

**Access:** Own `AgentLedger` only.

**Available Functions:**

- `get_my_inventory()`: Returns `agent_ledgers["Seller_X"]["inventory"]`.

- `calculate_my_sales_stats(last_n_days: int)`: Reads only its own `private_sales_log`.
  - Returns: `{"my_units_sold": X, "my_avg_sale_price": Y}`.

- `how_much_did_i_sell_yesterday()`: Checks if its `private_sales_log` from `day - 1` has entries and the number size.
  - Returns: number of units sold yesterday.

## 5. The Daily Graph: Node Logic

### Node 1: setup_day

**Purpose:** To query the global `shopper_database` and create the `daily_shopper_pool` for the current day, applying the desperation function.

**Logic:**

1. Get `current_day` from `state['day']`.
2. Initialize `new_daily_shopper_pool = []`.
3. Loop through every shopper in the global `shopper_database`:
   - **Check 1 (Still needs to buy?):** `if shopper.demand_remaining <= 0: continue`
   - **Check 2 (Is active today?):** `if not (shopper.shopping_window_start <= current_day <= shopper.shopping_window_end): continue`
   - **If active, calculate today's price using the urgency-adjusted desperation function:**
     - `days_in_window = shopper.shopping_window_end - shopper.shopping_window_start`
     - `days_elapsed = current_day - shopper.shopping_window_start`
     - `time_progress = days_elapsed / days_in_window`  # Normalized time [0, 1]
     - `urgency_curve = time_progress ** shopper.urgency_factor`  # Apply power curve
     - `price_range = shopper.max_willing_to_pay - shopper.base_willing_to_pay`
     - `current_willing_to_pay_float = shopper.base_willing_to_pay + (price_range * urgency_curve)`
     - `current_willing_to_pay = round(current_willing_to_pay_float)`  # **Round to integer**
   - Add to pool: For each unit of `shopper.demand_remaining`:
     - `new_daily_shopper_pool.append({ "shopper_id": shopper.shopper_id, "demand_unit": 1, "willing_to_pay": current_willing_to_pay })`
4. **Shuffle and Sort:**
   - `random.shuffle(new_daily_shopper_pool)`  # Randomize order first
   - `new_daily_shopper_pool.sort(key=lambda x: x["willing_to_pay"], reverse=True, stable=True)`  # Stable sort by price (descending)
   - This ensures: (1) highest prices are matched first, (2) within the same price, order is randomized for fairness

**Returns:** `{"daily_shopper_pool": new_daily_shopper_pool, "day": current_day + 1}`

### Router 1: master_day_router

**Purpose:** To decide if negotiations should occur today.

**Logic:**

1. `day = state['day']`
2. `if (day - 1) % 20 == 0:` (i.e., Day 1, 21, 41, 61, 81)
   - `return "run_negotiation"`
3. `else:`
   - `return "set_market_offers"`

### The Negotiation Loop (Sub-Graph)

The negotiation system allows up to 10 rounds of offers/counteroffers between the Wholesaler and each Seller. This creates opportunities for information exchange and strategic positioning.

**Key Features:**
- **Multi-round bargaining**: Up to 10 offer/counteroffer exchanges per seller
- **Information asymmetry exploitation**: Wholesaler has market data; Sellers can learn from justifications
- **Thinking scratchpads**: Each agent maintains private notes across negotiation rounds
- **Strategic communication**: Agents must justify their offers, potentially revealing information
- **Sequential negotiations**: Wholesaler negotiates with Seller_1 first, then Seller_2

**Flow:**
1. Wholesaler → Seller_1 (up to 10 rounds) → Trade or No Deal
2. Wholesaler → Seller_2 (up to 10 rounds) → Trade or No Deal
3. Proceed to market phase

**Example Negotiation Round:**
```
Round 1:
  Wholesaler → Seller_1: "I'll buy 1000 units at $55. Market data shows oversupply."
  Seller_1 → Wholesaler: "I'll sell 800 units at $62. My costs are high and demand is strong."

Round 2:
  Wholesaler → Seller_1: "I'll meet you at $58 for 900 units. That's fair given the risk."
  Seller_1 → Wholesaler: "Accept." ✓

[Trade executed: 900 units at $58]
[Seller_1's scratchpad updated: "Day 21: W claimed oversupply. Sold 900@58. Watch if prices drop."]
```

#### Scratchpad Guidelines

**Purpose:** Each agent maintains a free-form text scratchpad to track insights, patterns, and strategic notes across the 100-day simulation.

**Format:** Plain text string (not structured data). Agents append new observations with automatic timestamping.

**Update Pattern:**
```python
# System automatically adds context prefix when updating:
agent_scratchpads[agent_name] += f"\n[Day {day}, {context}]: {llm_response['scratchpad_update']}"

# Example scratchpad content:
"""
[Day 1, Seller_1 negotiation]: W offered $55, claimed oversupply. Countered $62. Final: $58 for 900 units.
[Day 1 pricing]: Set price $100. Inventory: 7200 remaining.
[Day 5 pricing]: Sales slow at $100. Only 50 units/day. Market weaker than expected?
[Day 21, Seller_1 negotiation]: W more aggressive, offered $52. Mentioned "demand dropping". Rejected.
[Day 21 pricing]: Lowered to $95 based on W's signals. Inventory: 6800.
"""
```

**Best Practices (included in agent prompts):**
- **Concise**: One-line updates only. No redundant information.
- **Actionable**: Focus on insights that affect future decisions (price trends, competitor signals, inventory strategy)
- **Non-redundant**: Don't repeat what's already in the scratchpad
- **Strategic**: For Sellers - track what Wholesaler reveals in negotiations
- **Pattern-focused**: Note trends, not individual transactions

**When to Update:**
- After negotiations (what did you learn from their justification?)
- After setting daily prices (what's your strategy? any new patterns?)
- NOT after every single sale (too verbose)

#### Negotiation Offer Structure

Each offer in the negotiation contains:

```python
{
    "agent": str,  # Who made this offer ("Wholesaler" or "Seller_X")
    "price": int,  # Integer price per unit
    "quantity": int,  # Number of units
    "justification": str,  # Reasoning for this offer
    "action": str  # "offer", "counteroffer", "accept", or "reject"
}
```

#### Entry Node: init_negotiation

**Purpose:** Initialize negotiation with Seller_1 first.

**Logic:**

1. Set `current_negotiation_target = "Seller_1"`
2. Set `negotiation_status = "seller_1_negotiating"`
3. Clear negotiation history for both sellers: `negotiation_history = {"Seller_1": [], "Seller_2": []}`

**Returns:** `{"current_negotiation_target": "Seller_1", "negotiation_status": "seller_1_negotiating"}`

#### Node: wholesaler_make_offer

**Purpose:** Wholesaler initiates or responds in the negotiation with the current target seller.

**Logic:**

1. Get context:
   - `target_seller = state['current_negotiation_target']`
   - `history = state['negotiation_history'][target_seller]`
   - `round_number = len(history) // 2 + 1`  # Each round = 1 offer + 1 counteroffer
   - `scratchpad = state['agent_scratchpads']['Wholesaler']`

2. Call Tools:
   - `stats = self.tools.get_full_market_history(20)`
   - `inv = self.tools.get_my_inventory()`

3. Call LLM (with Shared Context):

**Prompt:**
```
--- YOUR PRIVATE DATA ---
Inventory: {inv}
Market Analytics: {stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: {target_seller}
Round: {round_number} of 10
Previous offers in this negotiation: {history}

--- YOUR TASK ---
You are negotiating to BUY inventory from {target_seller}.

STEP 1: Review your scratchpad and current data. What insights are relevant?
STEP 2: Decide on your negotiation strategy for this round.
STEP 3: Make your offer or respond to their counteroffer.

You MUST respond in JSON format:
{
    "scratchpad_update": "<concise notes to ADD to your scratchpad - focus on new insights, patterns, or strategic observations. Keep it brief and non-redundant.>",
    "price": <integer_price_per_unit>,
    "quantity": <units_to_buy>,
    "justification": "<what you tell the seller about why this price is fair - be strategic about what you reveal>",
    "action": "offer" or "accept" or "reject"
}

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable information.
Note: "accept" means you accept their last counteroffer. "reject" ends negotiation.
```

4. Action:
   - Update scratchpad: `agent_scratchpads['Wholesaler'] += "\n[Day {day}, {target_seller} negotiation]: " + llm_response['scratchpad_update']`
   - Add to history: `negotiation_history[target_seller].append({...})`
   - If action is "accept": Execute trade and move to next seller
   - If action is "reject": Move to next seller with no trade
   - Otherwise: Pass turn to seller

**Returns:** Updated state with new offer in history

#### Node: seller_respond

**Purpose:** The target seller responds to the Wholesaler's offer with a counteroffer, acceptance, or rejection.

**Logic:**

1. Get context:
   - `seller_name = state['current_negotiation_target']`
   - `history = state['negotiation_history'][seller_name]`
   - `last_offer = history[-1]`  # Wholesaler's most recent offer
   - `round_number = len(history) // 2 + 1`
   - `scratchpad = state['agent_scratchpads'][seller_name]`

2. Call Tools:
   - `inv = self.tools.get_my_inventory()`
   - `my_stats = self.tools.calculate_my_sales_stats(20)`

3. Call LLM (with Shared Context):

**Prompt:**
```
--- YOUR PRIVATE DATA ---
Your Inventory: {inv}
Your Recent Sales Stats: {my_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- NEGOTIATION CONTEXT ---
Negotiating with: Wholesaler
Round: {round_number} of 10
Wholesaler's latest offer: Price ${last_offer['price']} for {last_offer['quantity']} units
Their justification: "{last_offer['justification']}"
Full negotiation history: {history}

--- YOUR TASK ---
The Wholesaler wants to BUY from you. They have access to global market data that you don't have.

STEP 1: Analyze their justification carefully - what market information might they be revealing?
STEP 2: Review your scratchpad - what patterns have you noticed?
STEP 3: Decide whether to accept, reject, or counteroffer.

You MUST respond in JSON format:
{
    "scratchpad_update": "<concise notes to ADD to your scratchpad - what did you learn from their justification? Any patterns? Keep it brief and actionable.>",
    "price": <integer_price_per_unit>,
    "quantity": <units_to_sell>,
    "justification": "<what you tell the wholesaler about why this price is fair>",
    "action": "counteroffer" or "accept" or "reject"
}

IMPORTANT: Your scratchpad should be concise. Only add NEW insights you learned.
Note: "accept" means you accept their offer. "reject" ends negotiation.
The Wholesaler has superior market data - try to learn from what they reveal!
```

4. Action:
   - Update scratchpad: `agent_scratchpads[seller_name] += "\n[Day {day}, W negotiation]: " + llm_response['scratchpad_update']`
   - Add to history: `negotiation_history[seller_name].append({...})`
   - If action is "accept": Execute trade at Wholesaler's offered terms
   - If action is "reject": End this negotiation, no trade
   - If round >= 10: Force end negotiation, no trade
   - Otherwise: Return to wholesaler_make_offer

**Returns:** Updated state with seller's response in history

#### Node: execute_trade

**Purpose:** Execute the agreed-upon trade between Wholesaler and Seller.

**Logic:**

1. Get the accepted offer details (price, quantity)
2. Update ledgers:
   - `agent_ledgers[seller_name]["inventory"] -= quantity`
   - `agent_ledgers[seller_name]["cash"] += quantity * price`
   - `agent_ledgers[seller_name]["total_revenue"] += quantity * price`
   - `agent_ledgers["Wholesaler"]["inventory"] += quantity`
   - `agent_ledgers["Wholesaler"]["cash"] -= quantity * price`
   - `agent_ledgers["Wholesaler"]["total_cost_incurred"] += quantity * price`

**Returns:** Updated ledgers

#### Router: negotiation_router

**Purpose:** Route the negotiation flow based on current state.

**Logic:**

1. Check if current negotiation ended (accept/reject or round >= 10):
   - If `current_negotiation_target == "Seller_1"`:
     - Set `current_negotiation_target = "Seller_2"`
     - Set `negotiation_status = "seller_2_negotiating"`
     - Return `"wholesaler_make_offer"` (start negotiation with Seller_2)
   - If `current_negotiation_target == "Seller_2"`:
     - Set `negotiation_status = "complete"`
     - Return `"set_market_offers"` (move to market phase)

2. Check whose turn it is:
   - If last entry in history is from Wholesaler: Return `"seller_respond"`
   - If last entry in history is from Seller: Return `"wholesaler_make_offer"`


### The Market Phase

#### Node: set_market_offers (Formerly set_market_prices)

**Purpose:** All agents use their tools and beliefs to set both their daily price and their daily quantity to offer.

**Wholesaler Price/Quantity Logic:**

1. Get context:
   - `scratchpad = state['agent_scratchpads']['Wholesaler']`
   - `day = state['day']`

2. Call Tools:
   - `rec = self.tools.get_profit_maximizing_price()`
   - `stats = self.tools.get_full_market_demand_stats()`
   - `inv = self.tools.get_my_inventory()`

3. Call LLM:

```
--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of 100
- Your Current Inventory: {inv['inventory']} units
- Market Analytics: {stats}
- Your Estimated Profit-Maximizing Price: {rec}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review your scratchpad - what have you learned from negotiations and past sales?
STEP 2: Analyze current market conditions and your inventory position.
STEP 3: Decide on price and quantity strategy.

You MUST respond in JSON format:
{
    "scratchpad_update": "<concise notes to ADD - any new insights about market conditions, inventory strategy, or pricing patterns. Keep it brief.>",
    "price": <integer_price>,
    "quantity": <units_to_offer>
}

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
You may want to hold back inventory for subsequent days.
```

4. Action:
   - Update scratchpad: `agent_scratchpads['Wholesaler'] += "\n[Day {day} pricing]: " + llm_response['scratchpad_update']`
   - Parse JSON: `price = int(round(llm_price))`, `quantity = min(llm_quantity, actual_inventory)`

**Seller Price/Quantity Logic:**

1. Get context:
   - `seller_name = "Seller_1"` or `"Seller_2"`
   - `scratchpad = state['agent_scratchpads'][seller_name]`
   - `day = state['day']`

2. Call Tools:
   - `my_stats = self.tools.calculate_my_sales_stats()`
   - `inv = self.tools.get_my_inventory()`

3. Call LLM (with Shared Context):

```
--- YOUR PRIVATE DATA (From Tools) ---
- Current Day: {day} of 100
- Your Current Inventory: {inv['inventory']} units
- Your Last 20 Days Sales Stats: {my_stats}

--- YOUR SCRATCHPAD (Private Notes) ---
{scratchpad}

--- YOUR TASK ---
Set your daily market price and quantity for today.

STEP 1: Review your scratchpad - what have you learned from negotiations with the Wholesaler?
STEP 2: Analyze your recent sales performance and inventory.
STEP 3: Decide on price and quantity strategy.

You MUST respond in JSON format:
{
    "scratchpad_update": "<concise notes to ADD - any new insights from sales patterns, what you learned from Wholesaler, or pricing strategy. Keep it brief.>",
    "price": <integer_price>,
    "quantity": <units_to_offer>
}

IMPORTANT: Your scratchpad should be concise. Only add NEW, actionable insights.
Remember: The Wholesaler has more market information than you. Use what you learned in negotiations.
```

4. Action:
   - Update scratchpad: `agent_scratchpads[seller_name] += "\n[Day {day} pricing]: " + llm_response['scratchpad_update']`
   - Parse JSON: `price = int(round(llm_price))`, `quantity = min(llm_quantity, actual_inventory)`

**Returns:** `{"daily_market_offers": {"Wholesaler": {...}, "Seller_1": {...}, "Seller_2": {...}}}`

#### Node: run_market_simulation

**Purpose:** The "physics engine." Runs the Priority Match Algorithm to clear the market.

**Logic:**

1. **Prepare Shoppers:** Sort the `daily_shopper_pool` in DESCENDING order by `willing_to_pay`.

2. **Prepare Sellers:** Create a flat list of all offers from `daily_market_offers` (that have `quantity > 0` and `inventory > 0`) and sort it in ASCENDING order by `price`.

3. **Initialize Logs:** `new_market_log = []`, `new_unmet_demand_log = []`.

4. **Run Two-Pointer Loop:** Use two index pointers, `i` for shoppers and `j` for sellers.

```python
while i < len(shoppers) and j < len(sellers):
    shopper = shoppers[i]
    seller = sellers[j]
    seller_name = seller["name"]

    # Check 1 (Seller Valid?)
    if seller["quantity"] <= 0 or state.agent_ledgers[seller_name]["inventory"] <= 0:
        j += 1  # Move to next seller
        continue

    # Check 2 (Match?)
    if shopper["willing_to_pay"] >= seller["price"]:
        # --- SALE! ---
        sale_price = seller["price"]
        new_market_log.append(...)
        seller["quantity"] -= 1

        # Update state.agent_ledgers[seller_name]
        # inventory -= 1, cash += sale_price, total_revenue += sale_price
        # Update state.agent_ledgers[seller_name]["private_sales_log"]
        # Update shopper_database[shopper["shopper_id"]].demand_remaining -= 1

        i += 1  # Move to next shopper
    else:
        # --- NO SALE ---
        new_unmet_demand_log.append({
            "day": ...,
            "shopper_id": ...,
            "rejected_price": seller["price"]
        })
        i += 1  # This shopper is done for the day

# Log any remaining shoppers who didn't buy as unmet demand
```

**Returns:** `{"market_log": new_market_log, "unmet_demand_log": new_unmet_demand_log}`

## 6. The 100-Day Simulation Loop (External Python)

A simple for loop outside of LangGraph that calls the compiled graph 100 times.

```python
# 1. Compile the graph
app = workflow.compile()

# 2. Get the initial state
current_state = initial_world_state
all_states = []  # To log history

# 3. Run the simulation
for day in range(1, 101):
    print(f"--- Day {day} ---")

    # Run one full day (which includes setup, route, negotiate, market, etc.)
    current_state = app.invoke(current_state)
    all_states.append(current_state)

print("--- Simulation Complete ---")
final_state = all_states[-1]
```

## 7. Analyzing Key Metrics (Post-Simulation)

After the 100-day loop, you analyze `final_state` to get your results.

```python
final_state = all_states[-1]
ledgers = final_state["agent_ledgers"]

print("--- FINAL RESULTS ---")

# 1. Total Met/Unmet Demand
total_met_demand = len(final_state["market_log"])
total_unmet_demand = len(final_state["unmet_demand_log"])
print(f"Total Met Demand: {total_met_demand} units")
print(f"Total Unmet Demand: {total_unmet_demand} shopper-days")

# 2. PnL and Value Capture of each Agent
for agent_name, ledger in ledgers.items():
    # PnL = Total Revenue - Total Cost of Goods Sold
    # Note: For Sellers, COGS is pre-calculated. For Wholesaler, it's accumulated.
    pnl = ledger["total_revenue"] - ledger["total_cost_incurred"]

    # Value Capture = Total Revenue
    value_capture = ledger["total_revenue"]

    print(f"\n--- {agent_name} ---")
    print(f"  Final PnL: ${pnl:,.2f}")
    print(f"  Value Capture (Total Revenue): ${value_capture:,.2f}")
    print(f"  Final Inventory: {ledger['inventory']} units")
    print(f"  Final Cash: ${ledger['cash']:,.2f}")
```

