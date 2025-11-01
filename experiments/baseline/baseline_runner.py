#!/usr/bin/env python3
"""
Baseline Experiment Runner - Automated 21-Day Comparison Study

Runs 4 experimental conditions to test causality of collusion:
- Experiment A: No Communication (transparency only)
- Experiment B: No Transparency (communication only)
- Experiment C: Full Baseline (neither)
- Experiment D: Treatment (both - current setup)

This framework modifies the workflow dynamically without manual code edits.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.simulation.config import SimulationConfig
from src.graph.workflow import create_workflow
from src.graph import nodes
from src.models.state import EconomicState
from langgraph.graph import StateGraph
from typing import Literal, Dict, Any
import json
from datetime import datetime
import logging


def create_baseline_workflow(enable_communication: bool, enable_transparency: bool) -> StateGraph:
    """
    Create a workflow with configurable communication and transparency features.

    Args:
        enable_communication: If False, skip wholesaler_discussion node
        enable_transparency: If False, remove competitor_activity tool access

    Returns:
        Configured StateGraph
    """
    # Create base graph
    graph = StateGraph(EconomicState)

    # Add core nodes (always present)
    graph.add_node("setup_day", nodes.setup_day)
    graph.add_node("init_negotiation", nodes.init_negotiation)
    graph.add_node("wholesaler_make_offer", nodes.wholesaler_make_offer)
    graph.add_node("seller_make_offer", nodes.seller_make_offer)
    graph.add_node("finalize_negotiation", nodes.finalize_negotiation)
    graph.add_node("update_target_seller1", nodes.update_target_seller1)
    graph.add_node("update_target_seller2", nodes.update_target_seller2)
    graph.add_node("set_market_offers", nodes.set_market_offers)
    graph.add_node("market_clearing", nodes.market_clearing)
    graph.add_node("end_day", nodes.end_day)

    # Conditionally add communication node
    if enable_communication:
        graph.add_node("wholesaler_discussion", nodes.wholesaler_discussion)

    # Set entry point
    graph.set_entry_point("setup_day")

    # Router function
    def should_negotiate(state: EconomicState) -> Literal["init_negotiation", "set_market_offers", "wholesaler_discussion"]:
        negotiation_days = [1, 21, 41, 61, 81]
        if state["day"] in negotiation_days:
            return "init_negotiation"
        else:
            if enable_communication:
                return "wholesaler_discussion"
            else:
                return "set_market_offers"

    # Add edges
    graph.add_conditional_edges(
        "setup_day",
        should_negotiate,
        {
            "init_negotiation": "init_negotiation",
            "set_market_offers": "set_market_offers",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers"
        }
    )

    # Negotiation cycle
    graph.add_edge("init_negotiation", "wholesaler_make_offer")
    graph.add_conditional_edges(
        "wholesaler_make_offer",
        lambda s: "seller_make_offer" if s["current_round"] < s["max_rounds"] else "finalize_negotiation",
        {
            "seller_make_offer": "seller_make_offer",
            "finalize_negotiation": "finalize_negotiation"
        }
    )
    graph.add_conditional_edges(
        "seller_make_offer",
        lambda s: "wholesaler_make_offer" if s["current_round"] < s["max_rounds"] else "finalize_negotiation",
        {
            "wholesaler_make_offer": "wholesaler_make_offer",
            "finalize_negotiation": "finalize_negotiation"
        }
    )

    # After negotiation, route to next seller or communication
    def after_negotiation(state: EconomicState) -> Literal["update_target_seller1", "update_target_seller2", "wholesaler_discussion", "set_market_offers"]:
        if state["current_negotiation_seller"] == "Seller_1" and state["current_negotiation_wholesaler"] == "Wholesaler":
            return "update_target_seller1"
        elif state["current_negotiation_seller"] == "Seller_1" and state["current_negotiation_wholesaler"] == "Wholesaler_2":
            return "update_target_seller2"
        elif state["current_negotiation_seller"] == "Seller_2" and state["current_negotiation_wholesaler"] == "Wholesaler":
            return "update_target_seller2"
        else:  # All negotiations complete
            if enable_communication:
                return "wholesaler_discussion"
            else:
                return "set_market_offers"

    graph.add_conditional_edges(
        "finalize_negotiation",
        after_negotiation,
        {
            "update_target_seller1": "update_target_seller1",
            "update_target_seller2": "update_target_seller2",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers",
            "set_market_offers": "set_market_offers"
        }
    )

    # Continue negotiation routing
    graph.add_conditional_edges(
        "update_target_seller1",
        lambda s: "wholesaler_make_offer" if s["negotiation_status"] != "complete" else ("wholesaler_discussion" if enable_communication else "set_market_offers"),
        {
            "wholesaler_make_offer": "wholesaler_make_offer",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers",
            "set_market_offers": "set_market_offers"
        }
    )

    graph.add_conditional_edges(
        "update_target_seller2",
        lambda s: "wholesaler_make_offer" if s["negotiation_status"] != "complete" else ("wholesaler_discussion" if enable_communication else "set_market_offers"),
        {
            "wholesaler_make_offer": "wholesaler_make_offer",
            "wholesaler_discussion": "wholesaler_discussion" if enable_communication else "set_market_offers",
            "set_market_offers": "set_market_offers"
        }
    )

    # After communication (if enabled), go to market offers
    if enable_communication:
        graph.add_edge("wholesaler_discussion", "set_market_offers")

    # Market clearing sequence
    graph.add_edge("set_market_offers", "market_clearing")

    # Day completion
    def should_continue(state: EconomicState) -> Literal["setup_day", "end"]:
        return "setup_day" if state["day"] < state["total_days"] else "end"

    graph.add_conditional_edges(
        "market_clearing",
        should_continue,
        {
            "setup_day": "setup_day",
            "end": "end_day"
        }
    )

    graph.add_edge("end_day", "__end__")

    return graph.compile()


def run_baseline_experiment(
    experiment_name: str,
    enable_communication: bool,
    enable_transparency: bool,
    num_days: int = 21
) -> Dict[str, Any]:
    """
    Run a single baseline experiment configuration.

    Args:
        experiment_name: Identifier for this experiment
        enable_communication: Enable wholesaler communication
        enable_transparency: Enable competitor price visibility
        num_days: Simulation duration

    Returns:
        Results dictionary
    """
    print(f"\n{'='*80}")
    print(f"RUNNING: {experiment_name}")
    print(f"{'='*80}")
    print(f"Configuration:")
    print(f"  - Communication: {'ENABLED' if enable_communication else 'DISABLED'}")
    print(f"  - Price Transparency: {'ENABLED' if enable_transparency else 'DISABLED'}")
    print(f"  - Duration: {num_days} days")
    print(f"{'='*80}\n")

    # Create config
    config = SimulationConfig(
        name=experiment_name,
        description=f"Baseline experiment: comm={enable_communication}, trans={enable_transparency}",
        num_days=num_days
    )

    # Create custom workflow
    workflow = create_baseline_workflow(enable_communication, enable_transparency)

    # NOTE: For transparency control, we'd need to modify WholesalerTools.get_competitor_activity()
    # For now, we'll document this limitation
    if not enable_transparency:
        print("⚠️  NOTE: Price transparency control not yet implemented in tools.py")
        print("    Agents still have access to get_competitor_activity() tool")
        print("    This will be addressed in future iteration\n")

    # Initialize state (similar to SimulationRunner)
    from src.simulation.runner import SimulationRunner
    from src.config import get_config

    runner = SimulationRunner(config)

    # Run using custom workflow (this requires modifying SimulationRunner to accept custom workflow)
    print("⚠️  NOTE: Custom workflow integration requires SimulationRunner modification")
    print("    For now, run standard SimulationRunner with manual feature toggles\n")

    # For MVP, we'll just run standard simulation and document the approach
    # results = runner.run()  # Would use custom workflow

    return {
        "experiment": experiment_name,
        "communication_enabled": enable_communication,
        "transparency_enabled": enable_transparency,
        "status": "framework_ready_needs_integration"
    }


def main():
    """Run all baseline experiments."""
    print("\n" + "="*80)
    print("BASELINE EXPERIMENT SUITE - 21-DAY COMPARISON STUDY")
    print("="*80)
    print("\nThis suite tests the causal impact of:")
    print("  1. Communication on collusion")
    print("  2. Price transparency on collusion")
    print("\n" + "="*80)

    experiments = [
        ("Experiment_A_NoComm", False, True),   # No communication, has transparency
        ("Experiment_B_NoTrans", True, False),  # Has communication, no transparency
        ("Experiment_C_FullBaseline", False, False),  # Neither
        ("Experiment_D_Treatment", True, True)  # Both (current setup)
    ]

    results_summary = []

    for exp_name, enable_comm, enable_trans in experiments:
        result = run_baseline_experiment(exp_name, enable_comm, enable_trans, num_days=21)
        results_summary.append(result)

    # Save framework summary
    output_file = f"scratch/baseline_experiments/framework_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "experiments": results_summary,
            "notes": [
                "Framework created for configurable baseline experiments",
                "Next steps:",
                "1. Integrate custom workflow into SimulationRunner",
                "2. Implement transparency control in WholesalerTools",
                "3. Run all 4 experiments",
                "4. Statistical comparison analysis"
            ]
        }, f, indent=2)

    print(f"\n✅ Framework summary saved to: {output_file}")
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("1. Review the configurable workflow approach above")
    print("2. Integrate into SimulationRunner (accept custom workflow parameter)")
    print("3. Add transparency toggle to WholesalerTools")
    print("4. Run all 4 experiments and collect data")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
