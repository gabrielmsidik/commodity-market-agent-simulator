"""LangGraph workflow definition."""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from src.models import EconomicState
from src.graph import nodes

# Get logger for workflow routing
logger = logging.getLogger("commodity_market.workflow")


def create_should_negotiate(enable_communication: bool):
    """Create a should_negotiate router function based on config."""
    def should_negotiate(state: EconomicState) -> Literal["init_negotiation", "wholesaler_discussion", "set_market_offers"]:
        """Determine if today is a negotiation day."""
        # Get negotiation days from config (upstream improvement)
        negotiation_days = state["config"].negotiation_days

        if state["day"] in negotiation_days:
            logger.debug(f"[Day {state['day']}] Router: Negotiation day → init_negotiation")
            return "init_negotiation"
        else:
            if enable_communication:
                logger.debug(f"[Day {state['day']}] Router: Regular day → wholesaler_discussion")
                return "wholesaler_discussion"
            else:
                logger.debug(f"[Day {state['day']}] Router: Regular day (no comm) → set_market_offers")
                return "set_market_offers"
    return should_negotiate


def create_negotiation_router(enable_communication: bool):
    """Create negotiation router that respects communication config."""
    def negotiation_router(state: EconomicState) -> Literal["wholesaler_make_offer", "seller_respond", "execute_trade", "update_target_seller1", "update_target_seller2", "set_market_offers", "wholesaler_discussion"]:
        """Route negotiation flow based on current state."""
        seller_name = state["current_negotiation_target"]
        wholesaler_name = state.get("current_negotiation_wholesaler", "Wholesaler")
        history = state["negotiation_history"][seller_name][wholesaler_name]

        if not history:
            # No offers yet, wholesaler starts
            logger.debug(f"[Day {state['day']}] Negotiation Router: Starting negotiation {seller_name} ↔ {wholesaler_name}")
            return "wholesaler_make_offer"

        last_offer = history[-1]
        round_number = len(history) // 2 + 1

        # Check if negotiation ended
        if last_offer["action"] == "accept":
            # Execute trade and move on
            logger.debug(f"[Day {state['day']}] Negotiation Router: Offer accepted → execute_trade")
            return "execute_trade"
        elif last_offer["action"] == "reject":
            # Explicit rejection - no trade, move to next wholesaler or seller
            logger.debug(f"[Day {state['day']}] Negotiation Router: Negotiation rejected")
            if seller_name == "Seller_1":
                logger.debug(f"[Day {state['day']}] → update_target_seller1")
                return "update_target_seller1"
            else:
                logger.debug(f"[Day {state['day']}] → update_target_seller2")
                return "update_target_seller2"
        else:
            # Check if max rounds reached (use config - upstream improvement)
            max_rounds = state["config"].max_negotiation_rounds

            if round_number > max_rounds:
                # Max rounds reached - no trade, move to next wholesaler or seller
                logger.debug(f"[Day {state['day']}] Negotiation Router: Max rounds ({round_number}) reached")
                if seller_name == "Seller_1":
                    logger.debug(f"[Day {state['day']}] → update_target_seller1")
                    return "update_target_seller1"
                else:
                    logger.debug(f"[Day {state['day']}] → update_target_seller2")
                    return "update_target_seller2"

            # Continue negotiation
            if last_offer["agent"] in ["Wholesaler", "Wholesaler_2"]:
                logger.debug(f"[Day {state['day']}] Negotiation Router: Round {round_number} → seller_respond")
                return "seller_respond"
            else:
                logger.debug(f"[Day {state['day']}] Negotiation Router: Round {round_number} → wholesaler_make_offer")
                return "wholesaler_make_offer"
    return negotiation_router


def create_update_target_seller1(enable_communication: bool):
    """Create update_target_seller1 function that respects communication config."""
    def update_negotiation_target_seller1(state: EconomicState) -> dict:
        """Update negotiation: Seller_1 moves to next wholesaler or advances to Seller_2."""
        current_wholesaler = state.get("current_negotiation_wholesaler")
        print(f"[DEBUG] update_target_seller1: current_wholesaler={current_wholesaler}")
        logger.debug(f"[Day {state['day']}] update_target_seller1: current_wholesaler={current_wholesaler}")

        if current_wholesaler == "Wholesaler":
            # Move to Wholesaler_2
            logger.debug(f"[Day {state['day']}] Seller_1 → Wholesaler_2")
            return {
                "current_negotiation_target": "Seller_1",
                "current_negotiation_wholesaler": "Wholesaler_2",
                "negotiation_status": "seller_1_wholesaler_2_negotiating"
            }
        else:
            # Done with Seller_1, move to Seller_2
            logger.debug(f"[Day {state['day']}] Seller_1 complete → Seller_2 with Wholesaler")
            return {
                "current_negotiation_target": "Seller_2",
                "current_negotiation_wholesaler": "Wholesaler",
                "negotiation_status": "seller_2_wholesaler_negotiating"
            }
    return update_negotiation_target_seller1


def create_update_target_seller2(enable_communication: bool):
    """Create update_target_seller2 function that respects communication config."""
    def update_negotiation_target_seller2(state: EconomicState) -> dict:
        """Update negotiation: Seller_2 moves to next wholesaler or completes."""
        current_wholesaler = state.get("current_negotiation_wholesaler")
        logger.debug(f"[Day {state['day']}] update_target_seller2: current_wholesaler={current_wholesaler}")

        if current_wholesaler == "Wholesaler":
            # Move to Wholesaler_2
            logger.debug(f"[Day {state['day']}] Seller_2 → Wholesaler_2")
            return {
                "current_negotiation_target": "Seller_2",
                "current_negotiation_wholesaler": "Wholesaler_2",
                "negotiation_status": "seller_2_wholesaler_2_negotiating"
            }
        else:
            # All negotiations complete
            logger.debug(f"[Day {state['day']}] All negotiations complete")
            return {
                "current_negotiation_target": None,
                "current_negotiation_wholesaler": None,
                "negotiation_status": "complete"
            }
    return update_negotiation_target_seller2


def create_simulation_graph(enable_communication: bool = True, enable_price_transparency: bool = True) -> StateGraph:
    """
    Create the LangGraph workflow for the simulation with configurable features.

    Args:
        enable_communication: If True, add wholesaler_discussion node
        enable_price_transparency: If True, agents can see competitor prices (handled in tools)

    Returns:
        Compiled StateGraph ready to run
    """
    # Create graph
    graph = StateGraph(EconomicState)

    # Create routers based on configuration
    should_negotiate = create_should_negotiate(enable_communication)
    negotiation_router = create_negotiation_router(enable_communication)
    update_target_seller1 = create_update_target_seller1(enable_communication)
    update_target_seller2 = create_update_target_seller2(enable_communication)

    # Add nodes
    graph.add_node("setup_day", nodes.setup_day)
    graph.add_node("init_negotiation", nodes.init_negotiation)
    graph.add_node("wholesaler_make_offer", nodes.wholesaler_make_offer)
    graph.add_node("seller_respond", nodes.seller_respond)
    graph.add_node("execute_trade", nodes.execute_trade)
    graph.add_node("update_target_seller1", update_target_seller1)
    graph.add_node("update_target_seller2", update_target_seller2)

    # Conditionally add communication node
    if enable_communication:
        graph.add_node("wholesaler_discussion", nodes.wholesaler_discussion)

    graph.add_node("set_market_offers", nodes.set_market_offers)
    graph.add_node("run_market_simulation", nodes.run_market_simulation)
    graph.add_node("apply_daily_depreciation", nodes.apply_daily_depreciation)

    # Set entry point
    graph.set_entry_point("setup_day")

    # Add edges - routing depends on whether communication is enabled
    if enable_communication:
        graph.add_conditional_edges(
            "setup_day",
            should_negotiate,
            {
                "init_negotiation": "init_negotiation",
                "wholesaler_discussion": "wholesaler_discussion",  # Communication on non-negotiation days
                "set_market_offers": "set_market_offers"  # Fallback (shouldn't happen)
            }
        )
    else:
        graph.add_conditional_edges(
            "setup_day",
            should_negotiate,
            {
                "init_negotiation": "init_negotiation",
                "set_market_offers": "set_market_offers"  # Skip communication entirely
            }
        )

    graph.add_conditional_edges(
        "init_negotiation",
        lambda _: "wholesaler_make_offer",
        {"wholesaler_make_offer": "wholesaler_make_offer"}
    )

    graph.add_conditional_edges(
        "wholesaler_make_offer",
        negotiation_router,
        {
            "seller_respond": "seller_respond",
            "execute_trade": "execute_trade",
            "update_target_seller1": "update_target_seller1",
            "update_target_seller2": "update_target_seller2",
            "set_market_offers": "set_market_offers",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers"
        }
    )

    graph.add_conditional_edges(
        "seller_respond",
        negotiation_router,
        {
            "wholesaler_make_offer": "wholesaler_make_offer",
            "execute_trade": "execute_trade",
            "update_target_seller1": "update_target_seller1",
            "update_target_seller2": "update_target_seller2",
            "set_market_offers": "set_market_offers",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers"
        }
    )

    graph.add_conditional_edges(
        "execute_trade",
        lambda state: "update_target_seller1" if state["current_negotiation_target"] == "Seller_1" else "update_target_seller2",
        {
            "update_target_seller1": "update_target_seller1",
            "update_target_seller2": "update_target_seller2"
        }
    )

    # After updating target from Seller_1, continue negotiating
    graph.add_edge("update_target_seller1", "wholesaler_make_offer")

    # After updating target from Seller_2, route based on communication setting
    if enable_communication:
        graph.add_conditional_edges(
            "update_target_seller2",
            lambda state: "wholesaler_make_offer" if state["negotiation_status"] != "complete" else "wholesaler_discussion",
            {
                "wholesaler_make_offer": "wholesaler_make_offer",
                "wholesaler_discussion": "wholesaler_discussion"  # Communication after negotiations complete
            }
        )
        # After communication, proceed to market offers
        graph.add_edge("wholesaler_discussion", "set_market_offers")
    else:
        graph.add_conditional_edges(
            "update_target_seller2",
            lambda state: "wholesaler_make_offer" if state["negotiation_status"] != "complete" else "set_market_offers",
            {
                "wholesaler_make_offer": "wholesaler_make_offer",
                "set_market_offers": "set_market_offers"  # Skip communication, go straight to market
            }
        )

    graph.add_edge("set_market_offers", "run_market_simulation")
    # Apply daily depreciation after market clears
    graph.add_edge("run_market_simulation", "apply_daily_depreciation")
    # End the graph after depreciation - runner will handle day loop
    graph.add_edge("apply_daily_depreciation", END)

    return graph.compile()

