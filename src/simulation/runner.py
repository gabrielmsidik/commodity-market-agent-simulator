"""Simulation runner and orchestration."""

import random
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from src.models import EconomicState, AgentLedger
from src.simulation.config import SimulationConfig
from src.simulation.shoppers import generate_shopper_database
from src.graph.workflow import create_simulation_graph
from src.utils import setup_logger, get_logger


class SimulationRunner:
    """Orchestrates a complete simulation run."""

    def __init__(self, config: SimulationConfig, log_level: int = logging.INFO):
        """
        Initialize simulation runner.

        Args:
            config: Simulation configuration
            log_level: Logging level (DEBUG for detailed, INFO for summary)
        """
        self.config = config
        self.graph = create_simulation_graph()
        self.logger = setup_logger(
            name=f"simulation_{config.name}",
            level=log_level,
            log_to_file=True
        )
    
    def create_initial_state(self) -> EconomicState:
        """
        Create the initial state for the simulation.
        
        Returns:
            Initial EconomicState
        """
        # Generate random costs and inventories
        s1_cost = random.randint(self.config.s1_cost_min, self.config.s1_cost_max)
        s1_inv = random.randint(self.config.s1_inv_min, self.config.s1_inv_max)
        s2_cost = random.randint(self.config.s2_cost_min, self.config.s2_cost_max)
        s2_inv = random.randint(self.config.s2_inv_min, self.config.s2_inv_max)
        
        # Generate shopper database
        shopper_database = generate_shopper_database(self.config)
        
        # Create initial state
        initial_state: EconomicState = {
            "num_days": self.config.num_days,
            "day": 1,
            "market_log": [],
            "unmet_demand_log": [],
            "wholesale_trades_log": [],
            "daily_shopper_pool": [],
            "daily_market_offers": {},
            "agent_ledgers": {
                "Seller_1": {
                    "inventory": s1_inv,
                    "cash": self.config.s1_starting_cash,
                    "cost_per_unit": s1_cost,
                    "total_cost_incurred": s1_inv * s1_cost,
                    "total_revenue": 0.0,
                    "private_sales_log": []
                },
                "Seller_2": {
                    "inventory": s2_inv,
                    "cash": self.config.s2_starting_cash,
                    "cost_per_unit": s2_cost,
                    "total_cost_incurred": s2_inv * s2_cost,
                    "total_revenue": 0.0,
                    "private_sales_log": []
                },
                "Wholesaler": {
                    "inventory": 0,
                    "cash": self.config.wholesaler_starting_cash,
                    "cost_per_unit": 0,
                    "total_cost_incurred": 0.0,
                    "total_revenue": 0.0,
                    "private_sales_log": []
                }
            },
            "shopper_database": shopper_database,
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
        
        return initial_state
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete simulation.

        Returns:
            Simulation results including final state and metadata
        """
        start_time = datetime.now()

        self.logger.info("=" * 80)
        self.logger.info(f"Starting Simulation: {self.config.name}")
        self.logger.info(f"Description: {self.config.description}")
        self.logger.info(f"Duration: {self.config.num_days} days")
        self.logger.info("=" * 80)

        # Create initial state
        initial_state = self.create_initial_state()

        self.logger.info(f"Initial Setup:")
        self.logger.info(f"  Seller_1: Cost=${initial_state['agent_ledgers']['Seller_1']['cost_per_unit']}, "
                        f"Inventory={initial_state['agent_ledgers']['Seller_1']['inventory']}")
        self.logger.info(f"  Seller_2: Cost=${initial_state['agent_ledgers']['Seller_2']['cost_per_unit']}, "
                        f"Inventory={initial_state['agent_ledgers']['Seller_2']['inventory']}")
        self.logger.info(f"  Wholesaler: Inventory={initial_state['agent_ledgers']['Wholesaler']['inventory']}")
        self.logger.info(f"  Total Shoppers: {len(initial_state['shopper_database'])}")
        self.logger.info("")

        # Run graph with logging callback
        final_state = self._run_with_logging(initial_state)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info(f"Simulation Complete!")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info("=" * 80)

        # Compile results
        results = {
            "config": self.config.to_dict(),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "initial_state": initial_state,
            "final_state": final_state,
            "summary": self._generate_summary(final_state)
        }

        # Log summary (pass final_state for agent_scratchpads)
        self._log_summary(results["summary"], final_state)

        return results

    def _run_with_logging(self, initial_state: EconomicState) -> EconomicState:
        """
        Run the graph with per-day logging.

        Args:
            initial_state: Initial state

        Returns:
            Final state
        """
        import copy
        # CRITICAL: Create a deep copy to avoid mutating the initial_state
        state = copy.deepcopy(initial_state)

        for day in range(1, self.config.num_days + 1):
            # Update state day
            state["day"] = day

            # Log day header
            self.logger.info(f"--- Day {day} ---")

            # DEBUG: Log all seller inventories at the start of each day
            for agent_name in ["Seller_1", "Seller_2"]:
                inv = state.get("agent_ledgers", {}).get(agent_name, {}).get("inventory", "N/A")
                self.logger.debug(f"  [INVENTORY DEBUG] Day {day} - START OF DAY - {agent_name} inventory: {inv} units")

            # Execute one day with streaming for detailed node-level logging
            try:
                self.logger.debug(f"Starting LangGraph execution for day {day}")

                # Use stream to get node-level events
                events = []
                RECURSION_LIMIT = 1000
                for event in self.graph.stream(state, {"recursion_limit": RECURSION_LIMIT}):
                    events.append(event)
                    # Log each node execution
                    for node_name, node_output in event.items():
                        if node_output:  # Only log if there's output
                            self.logger.debug(f"  Node '{node_name}' executed")

                            # Create a summary output for logging (exclude large arrays)
                            log_output = {}
                            for key, value in node_output.items():
                                if key == "daily_shopper_pool":
                                    # Log summary instead of full array
                                    pool = value
                                    if pool:
                                        prices = [s["willing_to_pay"] for s in pool]
                                        log_output[key] = {
                                            "total_demand": len(pool),
                                            "unique_shoppers": len(set(s["shopper_id"] for s in pool)),
                                            "price_range": f"${min(prices)}-${max(prices)}",
                                            "avg_price": f"${sum(prices)/len(prices):.2f}"
                                        }
                                    else:
                                        log_output[key] = {"total_demand": 0}
                                elif key == "shopper_database":
                                    # Log summary instead of full database
                                    db = value
                                    if db:
                                        total_shoppers = len(db)
                                        active_shoppers = sum(1 for s in db if s["demand_remaining"] > 0)
                                        total_demand_remaining = sum(s["demand_remaining"] for s in db)
                                        log_output[key] = {
                                            "total_shoppers": total_shoppers,
                                            "active_shoppers": active_shoppers,
                                            "total_demand_remaining": total_demand_remaining
                                        }
                                    else:
                                        log_output[key] = {"total_shoppers": 0}
                                elif key == "agent_ledgers":
                                    # Log summary of agent ledgers with private_sales_log summarized
                                    ledgers = value
                                    if ledgers:
                                        summary_ledgers = {}
                                        for agent_name, ledger in ledgers.items():
                                            # Summarize private_sales_log
                                            sales_log = ledger.get("private_sales_log", [])
                                            if sales_log:
                                                total_qty = sum(s["quantity"] for s in sales_log)
                                                total_revenue = sum(s["price"] * s["quantity"] for s in sales_log)
                                                avg_price = total_revenue / total_qty if total_qty > 0 else 0
                                                sales_summary = {
                                                    "total_quantity_sold": total_qty,
                                                    "average_price": f"${avg_price:.2f}"
                                                }
                                            else:
                                                sales_summary = {"total_quantity_sold": 0, "average_price": "$0.00"}

                                            summary_ledgers[agent_name] = {
                                                "inventory": ledger.get("inventory", 0),
                                                "cash": ledger.get("cash", 0),
                                                "cost_per_unit": ledger.get("cost_per_unit", 0),
                                                "total_cost_incurred": ledger.get("total_cost_incurred", 0),
                                                "total_revenue": ledger.get("total_revenue", 0),
                                                "private_sales_summary": sales_summary
                                            }
                                        log_output[key] = summary_ledgers
                                    else:
                                        log_output[key] = {}
                                elif key == "agent_scratchpads":
                                    # Skip logging agent_scratchpads during daily execution
                                    # They will be logged only in the final summary
                                    log_output[key] = "(scratchpads omitted - see final summary)"
                                elif key == "negotiation_history":
                                    # Log summary of negotiation history instead of full history
                                    history = value
                                    if history:
                                        summary = {}
                                        for seller, rounds in history.items():
                                            if rounds:
                                                # Only show the latest round (live negotiation)
                                                latest = rounds[-1]
                                                summary[seller] = {
                                                    "total_rounds": len(rounds),
                                                    "latest_offer": {
                                                        "agent": latest["agent"],
                                                        "price": latest["price"],
                                                        "quantity": latest["quantity"],
                                                        "action": latest["action"]
                                                    }
                                                }
                                            else:
                                                summary[seller] = {"total_rounds": 0}
                                        log_output[key] = summary
                                    else:
                                        log_output[key] = {}
                                elif key == "unmet_demand_log":
                                    # Log summary of unmet demand instead of full log
                                    log = value
                                    if log:
                                        # Get today's unmet demand
                                        today_unmet = [u for u in log if u["day"] == state["day"]]
                                        total_today = len(today_unmet)
                                        log_output[key] = {
                                            "total_entries": len(log),
                                            "today_unmet": total_today,
                                            "cumulative_unmet": len(log)
                                        }
                                    else:
                                        log_output[key] = {"total_entries": 0}
                                elif key == "market_log":
                                    # Log summary of market trades instead of full log
                                    log = value
                                    if log:
                                        # Get today's trades
                                        today_trades = [t for t in log if t["day"] == state["day"]]
                                        total_today_volume = sum(t["quantity"] for t in today_trades)
                                        log_output[key] = {
                                            "total_trade_entries": len(log),
                                            "today_trade_entries": len(today_trades),
                                            "today_volume": total_today_volume
                                        }
                                    else:
                                        log_output[key] = {"total_trade_entries": 0}
                                elif key == "wholesale_trades_log":
                                    # Log summary of wholesale trades instead of full log
                                    log = value
                                    if log:
                                        # Get today's trades
                                        today_trades = [t for t in log if t["day"] == state["day"]]
                                        total_today = len(today_trades)
                                        log_output[key] = {
                                            "total_entries": len(log),
                                            "today_trades": total_today,
                                            "cumulative_trades": len(log)
                                        }
                                    else:
                                        log_output[key] = {"total_entries": 0}
                                else:
                                    log_output[key] = value

                            self.logger.debug(f"    Output: {json.dumps(log_output, indent=2)}")

                            # Log key state changes
                            if "negotiation_status" in node_output:
                                self.logger.debug(f"    → negotiation_status: {node_output['negotiation_status']}")
                            if "current_negotiation_target" in node_output:
                                self.logger.debug(f"    → current_negotiation_target: {node_output['current_negotiation_target']}")
                            if "daily_market_offers" in node_output:
                                offers = node_output["daily_market_offers"]
                                self.logger.debug(f"    → market_offers: {len(offers)} agents set offers")
                            if "daily_shopper_pool" in node_output:
                                pool = node_output["daily_shopper_pool"]
                                self.logger.debug(f"    → daily_shopper_pool: {len(pool)} demand units from {len(set(s['shopper_id'] for s in pool))} shoppers")

                # Merge all node outputs into state
                # IMPORTANT: Use proper reducer logic for append-only fields
                if events:
                    for event in events:
                        for node_name, node_output in event.items():
                            if node_output:
                                # Handle append-only fields (Annotated[List[Dict], operator.add])
                                append_only_fields = ["market_log", "unmet_demand_log", "wholesale_trades_log"]

                                for key, value in node_output.items():
                                    if key in append_only_fields:
                                        # Append to existing list instead of replacing
                                        if key in state:
                                            state[key] = state[key] + value
                                        else:
                                            state[key] = value
                                    else:
                                        # For all other fields, use normal update
                                        # DEBUG: Log when agent_ledgers are updated
                                        if key == "agent_ledgers":
                                            for agent_name in ["Seller_1", "Seller_2"]:
                                                if agent_name in value:
                                                    old_inv = state.get("agent_ledgers", {}).get(agent_name, {}).get("inventory", "N/A")
                                                    new_inv = value.get(agent_name, {}).get("inventory", "N/A")
                                                    self.logger.debug(f"  [INVENTORY DEBUG] Day {day} - State merge from node '{node_name}' - {agent_name} inventory: {old_inv} → {new_inv}")
                                        state[key] = value

                self.logger.debug(f"Completed LangGraph execution for day {day}")

            except Exception as e:
                self.logger.error(f"Error during LangGraph execution on day {day}: {str(e)}")
                self.logger.exception("Full traceback:")
                raise

            # Log day summary
            self._log_day_summary(state, day)

            # Progress indicator every 10 days
            if day % 10 == 0:
                self.logger.info(f"Progress: {day}/{self.config.num_days} days completed")

        return state

    def _log_day_summary(self, state: EconomicState, day: int):
        """Log summary of the day's activities."""
        # Get today's trades
        today_trades = [t for t in state["market_log"] if t["day"] == day]

        # Get today's unmet demand
        today_unmet = [u for u in state["unmet_demand_log"] if u["day"] == day]

        # Get negotiation info if it's a negotiation day
        is_negotiation_day = day in [1, 21, 41, 61, 81]

        if is_negotiation_day:
            self.logger.info(f"  [NEGOTIATION DAY]")
            # Log negotiation outcomes from market log
            negotiation_trades = [t for t in today_trades if t.get("trade_type") == "negotiation"]
            for trade in negotiation_trades:
                self.logger.info(f"    {trade['buyer']} ← {trade['seller']}: "
                               f"{trade['quantity']} units @ ${trade['price']}")

        # Log market activity
        market_trades = [t for t in today_trades if t.get("trade_type") != "negotiation"]
        if market_trades:
            total_volume = sum(t["quantity"] for t in market_trades)
            avg_price = sum(t["price"] * t["quantity"] for t in market_trades) / total_volume if total_volume > 0 else 0

            self.logger.info(f"  Market: {len(market_trades)} trades, "
                           f"{total_volume} units, avg price ${avg_price:.2f}")

            # Log by seller
            for seller in ["Seller_1", "Seller_2", "Wholesaler"]:
                seller_trades = [t for t in market_trades if t["seller"] == seller]
                if seller_trades:
                    volume = sum(t["quantity"] for t in seller_trades)
                    revenue = sum(t["price"] * t["quantity"] for t in seller_trades)
                    self.logger.debug(f"    {seller}: {volume} units sold, ${revenue} revenue")

        # Log unmet demand
        if today_unmet:
            total_unmet = sum(u["quantity"] for u in today_unmet)
            self.logger.info(f"  Unmet Demand: {total_unmet} units")

        # Log inventory levels
        ledgers = state["agent_ledgers"]
        self.logger.debug(f"  Inventory: S1={ledgers['Seller_1']['inventory']}, "
                         f"S2={ledgers['Seller_2']['inventory']}, "
                         f"W={ledgers['Wholesaler']['inventory']}")

    def _log_summary(self, summary: Dict[str, Any], final_state: EconomicState):
        """Log final summary statistics."""
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("FINAL SIMULATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info("")
        self.logger.info("MARKET TRADES (B2C - Sellers to Shoppers):")
        self.logger.info(f"  Total Trades: {summary['total_market_trades']}")
        self.logger.info(f"  Total Volume: {summary['total_market_volume']} units")
        self.logger.info(f"  Average Price: ${summary['average_market_price']:.2f}")
        self.logger.info("")
        self.logger.info("WHOLESALE TRADES (B2B - Sellers to Wholesaler):")
        self.logger.info(f"  Total Trades: {summary['total_wholesale_trades']}")
        self.logger.info(f"  Total Volume: {summary['total_wholesale_volume']} units")
        self.logger.info(f"  Average Price: ${summary['average_wholesale_price']:.2f}")
        self.logger.info("")
        self.logger.info("UNMET DEMAND:")
        self.logger.info(f"  Total Unmet Demand: {summary['total_unmet_demand']} units")
        self.logger.info(f"  (Shoppers who couldn't purchase due to high prices or no inventory)")
        self.logger.info("")
        self.logger.info("AGENT PERFORMANCE:")
        for agent in ["Seller_1", "Seller_2", "Wholesaler"]:
            perf = summary["agent_performance"][agent]
            self.logger.info(f"  {agent}:")
            self.logger.info(f"    Revenue: ${perf['revenue']:.2f}")
            self.logger.info(f"    Costs: ${perf['costs']:.2f}")
            self.logger.info(f"    Profit: ${perf['profit']:.2f}")
            self.logger.info(f"    Market Sales (to shoppers): {perf['market_units_sold']} units")
            self.logger.info(f"    Wholesale Sales (to wholesaler): {perf['wholesale_units_sold']} units")
            self.logger.info(f"    Wholesale Purchases (from sellers): {perf['wholesale_units_bought']} units")
            self.logger.info(f"    Remaining Inventory: {perf['remaining_inventory']} units")
            self.logger.info(f"    Final Cash: ${perf['final_cash']:.2f}")
        self.logger.info("")
        self.logger.info("TRADE HISTORY:")
        self.logger.info("")
        self.logger.info("  Wholesale Trades (B2B):")
        if summary['wholesale_trade_list']:
            for trade in summary['wholesale_trade_list']:
                self.logger.info(f"    Day {trade['day']}: {trade['seller']} → {trade['buyer']}: "
                               f"{trade['quantity']} units @ ${trade['price']}/unit "
                               f"(Total: ${trade['total_value']}) [{trade['status']}]")
        else:
            self.logger.info("    No wholesale trades occurred")
        self.logger.info("")
        self.logger.info("  Market Trades (B2C):")
        if summary['market_trade_list']:
            for trade in summary['market_trade_list']:
                total_value = trade['price'] * trade['quantity']
                self.logger.info(f"    Day {trade['day']}: {trade['seller']} → {trade['buyer']}: "
                               f"{trade['quantity']} units @ ${trade['price']}/unit "
                               f"(Total: ${total_value:.2f})")
        else:
            self.logger.info("    No market trades occurred")
        self.logger.info("")

        # Log agent scratchpads at the end
        self.logger.info("AGENT SCRATCHPADS (Final State):")
        self.logger.info("")
        agent_scratchpads = final_state.get("agent_scratchpads", {})
        for agent in ["Wholesaler", "Seller_1", "Seller_2"]:
            scratchpad = agent_scratchpads.get(agent, "")
            self.logger.info(f"  {agent}:")
            if scratchpad:
                # Split by newlines and indent each line
                lines = scratchpad.strip().split('\n')
                for line in lines:
                    self.logger.info(f"    {line}")
            else:
                self.logger.info("    (empty)")
            self.logger.info("")

        self.logger.info("=" * 80)
    
    def _generate_summary(self, final_state: EconomicState) -> Dict[str, Any]:
        """
        Generate summary statistics from final state.

        Args:
            final_state: Final simulation state

        Returns:
            Summary statistics
        """
        market_log = final_state["market_log"]
        unmet_demand_log = final_state["unmet_demand_log"]
        wholesale_trades_log = final_state["wholesale_trades_log"]
        ledgers = final_state["agent_ledgers"]

        # Calculate market trades (B2C - sellers to shoppers)
        total_market_trades = len(market_log)
        total_market_volume = sum(trade["quantity"] for trade in market_log)

        if total_market_trades > 0:
            avg_market_price = sum(trade["price"] * trade["quantity"] for trade in market_log) / total_market_volume
        else:
            avg_market_price = 0

        # Calculate wholesale trades (B2B - sellers to wholesaler)
        total_wholesale_trades = len(wholesale_trades_log)
        total_wholesale_volume = sum(trade["quantity"] for trade in wholesale_trades_log)

        if total_wholesale_trades > 0:
            avg_wholesale_price = sum(trade["price"] * trade["quantity"] for trade in wholesale_trades_log) / total_wholesale_volume
        else:
            avg_wholesale_price = 0

        # Calculate unmet demand
        total_unmet = sum(entry["quantity"] for entry in unmet_demand_log)

        # Agent profitability
        agent_profits = {}
        for agent_name, ledger in ledgers.items():
            profit = ledger["total_revenue"] - ledger["total_cost_incurred"]

            # Calculate market units sold (to shoppers)
            market_units_sold = sum(sale["quantity"] for sale in ledger["private_sales_log"])

            # Calculate wholesale units sold (seller to wholesaler)
            wholesale_units_sold = sum(
                trade["quantity"] for trade in wholesale_trades_log
                if trade["seller"] == agent_name
            )

            # Calculate wholesale units bought (wholesaler from sellers)
            wholesale_units_bought = sum(
                trade["quantity"] for trade in wholesale_trades_log
                if trade["buyer"] == agent_name
            )

            agent_profits[agent_name] = {
                "revenue": ledger["total_revenue"],
                "costs": ledger["total_cost_incurred"],
                "profit": profit,
                "market_units_sold": market_units_sold,
                "wholesale_units_sold": wholesale_units_sold,
                "wholesale_units_bought": wholesale_units_bought,
                "remaining_inventory": ledger["inventory"],
                "final_cash": ledger["cash"]
            }

        return {
            "total_market_trades": total_market_trades,
            "total_market_volume": total_market_volume,
            "average_market_price": avg_market_price,
            "total_wholesale_trades": total_wholesale_trades,
            "total_wholesale_volume": total_wholesale_volume,
            "average_wholesale_price": avg_wholesale_price,
            "total_unmet_demand": total_unmet,
            "agent_performance": agent_profits,
            "wholesale_trade_list": wholesale_trades_log,
            "market_trade_list": market_log
        }
    
    def save_results(self, results: Dict[str, Any], filepath: str):
        """
        Save simulation results to file.
        
        Args:
            results: Simulation results
            filepath: Path to save file
        """
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

