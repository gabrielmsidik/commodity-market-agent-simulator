#!/usr/bin/env python3
"""
Baseline Experiment A: No Communication Control
21-day simulation with communication DISABLED to test if communication causes collusion.

Expected Outcome:
- Lower price convergence without communication
- More competitive pricing behavior
- Higher price variance
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.simulation.runner import SimulationRunner
from src.simulation.config import SimulationConfig
import json
from datetime import datetime


def main():
    print("\n" + "="*80)
    print("BASELINE EXPERIMENT A: NO COMMUNICATION CONTROL")
    print("="*80)
    print("\nConfiguration:")
    print("  - Duration: 21 days")
    print("  - Communication: DISABLED")
    print("  - Price Transparency: ENABLED (get_competitor_activity)")
    print("  - Hypothesis: Without communication, coordination should fail")
    print("\n" + "="*80)

    # Create config with communication disabled
    config = SimulationConfig(
        name="baseline_A_no_communication",
        description="21-day baseline without wholesaler communication",
        num_days=21
    )

    # Run simulation with communication disabled
    # NOTE: We'll need to modify the workflow to skip wholesaler_discussion
    # For now, we'll run this and manually disable in workflow.py

    runner = SimulationRunner(config)

    print("\n⚠️  IMPORTANT: Make sure wholesaler_discussion node is DISABLED in workflow.py")
    print("   Modify src/graph/workflow.py to skip communication before running.\n")

    # Uncomment to run:
    # results = runner.run()
    # final_state = results["final_state"]

    # Save results
    # output_file = f"results/baseline_A_no_communication_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # os.makedirs("results", exist_ok=True)
    #
    # with open(output_file, 'w') as f:
    #     json.dump({
    #         "experiment": "A_no_communication",
    #         "config": config.to_dict(),
    #         "communications": final_state.get("communications_log", []),
    #         "market_offers": final_state.get("market_offers_log", []),
    #         "final_state_summary": {
    #             "total_days": final_state["day"],
    #             "wholesaler_cash": final_state["agent_ledgers"]["Wholesaler"]["cash"],
    #             "wholesaler2_cash": final_state["agent_ledgers"]["Wholesaler_2"]["cash"]
    #         }
    #     }, f, indent=2)
    #
    # print(f"\n✅ Results saved to: {output_file}")

    print("\n" + "="*80)
    print("TO RUN THIS EXPERIMENT:")
    print("1. Modify src/graph/workflow.py to disable wholesaler_discussion node")
    print("2. Uncomment the code above")
    print("3. Run: python scratch/baseline_experiments/run_experiment_A_no_communication.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
