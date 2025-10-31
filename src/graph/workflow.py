"""LangGraph workflow definition."""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from src.models import EconomicState
from src.graph import nodes

# Get logger for workflow routing
logger = logging.getLogger("commodity_market.workflow")


def should_negotiate(state: EconomicState) -> Literal["init_negotiation", "set_market_offers"]:
    """Determine if today is a negotiation day."""
    negotiation_days = state["config"].negotiation_days

    if state["day"] in negotiation_days:
        logger.debug(f"[Day {state['day']}] Router: Negotiation day → init_negotiation")
        return "init_negotiation"
    else:
        logger.debug(f"[Day {state['day']}] Router: Regular day → set_market_offers")
        return "set_market_offers"


def negotiation_router(state: EconomicState) -> Literal["wholesaler_make_offer", "seller_respond", "execute_trade", "update_target_seller1", "update_target_seller2", "set_market_offers"]:
    """Route negotiation flow based on current state."""
    seller_name = state["current_negotiation_target"]
    history = state["negotiation_history"][seller_name]

    if not history:
        # No offers yet, wholesaler starts
        logger.debug(f"[Day {state['day']}] Negotiation Router: Starting negotiation with {seller_name}")
        return "wholesaler_make_offer"

    last_offer = history[-1]
    round_number = len(history) // 2 + 1

    # Check if negotiation ended
    if last_offer["action"] == "accept":
        # Execute trade and move on
        logger.debug(f"[Day {state['day']}] Negotiation Router: Offer accepted → execute_trade")
        return "execute_trade"
    elif last_offer["action"] == "reject":
        # Explicit rejection - no trade, move to next seller
        logger.debug(f"[Day {state['day']}] Negotiation Router: Negotiation rejected")
        if seller_name == "Seller_1":
            logger.debug(f"[Day {state['day']}] → update_target_seller1 (transition to Seller_2)")
            return "update_target_seller1"
        else:
            logger.debug(f"[Day {state['day']}] → update_target_seller2 (complete negotiations)")
            return "update_target_seller2"
    else:
        # Check if max rounds reached
        max_rounds = state["config"].max_negotiation_rounds

        if round_number > max_rounds:
            # Max rounds reached - no trade, move to next seller
            logger.debug(f"[Day {state['day']}] Negotiation Router: Max rounds ({round_number}) reached")
            if seller_name == "Seller_1":
                logger.debug(f"[Day {state['day']}] → update_target_seller1 (transition to Seller_2)")
                return "update_target_seller1"
            else:
                logger.debug(f"[Day {state['day']}] → update_target_seller2 (complete negotiations)")
                return "update_target_seller2"

        # Continue negotiation
        if last_offer["agent"] == "Wholesaler":
            logger.debug(f"[Day {state['day']}] Negotiation Router: Round {round_number} → seller_respond")
            return "seller_respond"
        else:
            logger.debug(f"[Day {state['day']}] Negotiation Router: Round {round_number} → wholesaler_make_offer")
            return "wholesaler_make_offer"


def update_negotiation_target_seller1(state: EconomicState) -> dict:
    """Update negotiation target from Seller_1 to Seller_2."""
    logger.debug(f"[Day {state['day']}] Updating target: Seller_1 → Seller_2")
    return {
        "current_negotiation_target": "Seller_2",
        "negotiation_status": "seller_2_negotiating"
    }


def update_negotiation_target_seller2(state: EconomicState) -> dict:
    """Complete negotiations after Seller_2."""
    logger.debug(f"[Day {state['day']}] Completing negotiations")
    return {
        "current_negotiation_target": None,
        "negotiation_status": "complete"
    }


def create_simulation_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the simulation.
    
    Returns:
        Compiled StateGraph ready to run
    """
    # Create graph
    graph = StateGraph(EconomicState)
    
    # Add nodes
    graph.add_node("setup_day", nodes.setup_day)
    graph.add_node("init_negotiation", nodes.init_negotiation)
    graph.add_node("wholesaler_make_offer", nodes.wholesaler_make_offer)
    graph.add_node("seller_respond", nodes.seller_respond)
    graph.add_node("execute_trade", nodes.execute_trade)
    graph.add_node("update_target_seller1", update_negotiation_target_seller1)
    graph.add_node("update_target_seller2", update_negotiation_target_seller2)
    graph.add_node("set_market_offers", nodes.set_market_offers)
    graph.add_node("run_market_simulation", nodes.run_market_simulation)
    
    # Set entry point
    graph.set_entry_point("setup_day")
    
    # Add edges
    graph.add_conditional_edges(
        "setup_day",
        should_negotiate,
        {
            "init_negotiation": "init_negotiation",
            "set_market_offers": "set_market_offers"
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
            "set_market_offers": "set_market_offers"
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
            "set_market_offers": "set_market_offers"
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

    # After updating target from Seller_1, start Seller_2 negotiation
    graph.add_edge("update_target_seller1", "wholesaler_make_offer")

    # After updating target from Seller_2, go to market
    graph.add_edge("update_target_seller2", "set_market_offers")
    
    graph.add_edge("set_market_offers", "run_market_simulation")
    # End the graph after market simulation - runner will handle day loop
    graph.add_edge("run_market_simulation", END)
    
    return graph.compile()

