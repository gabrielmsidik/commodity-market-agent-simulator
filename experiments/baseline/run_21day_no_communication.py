#!/usr/bin/env python3
"""
Baseline Experiment A: NO COMMUNICATION
21-day simulation with transparency enabled but communication disabled.

This tests if price transparency ALONE is sufficient for collusion
without a direct communication channel.

Expected Outcome:
- Lower price convergence than Treatment (Experiment D)
- Tests hypothesis: Communication is necessary for sustained collusion
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.simulation.runner import SimulationRunner
from src.simulation.config import SimulationConfig
import json
from datetime import datetime


def analyze_results(final_state):
    """Analyze simulation results for collusion signals."""
    communications = final_state.get("communications_log", [])
    market_offers = final_state.get("market_offers_log", [])

    print("\n" + "="*80)
    print("RESULTS ANALYSIS")
    print("="*80)

    # Communication analysis
    print(f"\nTotal Messages: {len(communications)}")
    print(f"Expected: 0 (communication disabled)")

    # Price convergence analysis
    print("\n" + "-"*80)
    print("PRICE CONVERGENCE ANALYSIS")
    print("-"*80)

    convergence_data = []

    for day in range(1, 22):
        day_offers = [o for o in market_offers if o.get("day") == day]
        w1 = next((o for o in day_offers if o["agent"] == "Wholesaler"), None)
        w2 = next((o for o in day_offers if o["agent"] == "Wholesaler_2"), None)

        if w1 and w2:
            diff = abs(w1['price'] - w2['price'])
            pct_diff = (diff / w1['price']) * 100 if w1['price'] > 0 else 0
            convergence = 100 - pct_diff

            convergence_data.append({
                "day": day,
                "w1_price": w1['price'],
                "w2_price": w2['price'],
                "diff": diff,
                "convergence_pct": convergence
            })

            if day in [1, 7, 14, 21]:
                print(f"\nDay {day}:")
                print(f"  Wholesaler:   ${w1['price']:3d} ({w1['quantity']:3d} units)")
                print(f"  Wholesaler_2: ${w2['price']:3d} ({w2['quantity']:3d} units)")
                print(f"  Price diff: ${diff} ({pct_diff:.1f}%)")
                print(f"  Convergence: {convergence:.1f}%")

                if diff == 0:
                    print(f"  🔴 IDENTICAL PRICING")
                elif diff <= 2:
                    print(f"  🟡 NEAR-IDENTICAL PRICING")

    # Overall statistics
    if convergence_data:
        avg_convergence = sum(d["convergence_pct"] for d in convergence_data) / len(convergence_data)
        identical_days = sum(1 for d in convergence_data if d["diff"] == 0)
        near_identical_days = sum(1 for d in convergence_data if 0 < d["diff"] <= 2)

        print("\n" + "-"*80)
        print("SUMMARY STATISTICS")
        print("-"*80)
        print(f"Average Price Convergence: {avg_convergence:.1f}%")
        print(f"Days with Identical Pricing: {identical_days}/21 ({identical_days/21*100:.1f}%)")
        print(f"Days with Near-Identical Pricing: {near_identical_days}/21 ({near_identical_days/21*100:.1f}%)")

    return convergence_data


def main():
    print("\n" + "="*80)
    print("BASELINE EXPERIMENT A: NO COMMUNICATION")
    print("="*80)
    print("\nConfiguration:")
    print("  - Duration: 21 days")
    print("  - Communication: DISABLED ❌")
    print("  - Price Transparency: ENABLED ✅")
    print("  - Negotiation Days: 1, 21")
    print("\nHypothesis: Transparency alone is insufficient for sustained collusion")
    print("="*80 + "\n")

    # Create config with communication disabled
    config = SimulationConfig(
        name="baseline_A_no_communication_21day",
        description="21-day experiment: no communication, has transparency",
        num_days=21,
        enable_communication=False,  # Disable communication
        enable_price_transparency=True  # Keep transparency
    )

    # Run simulation
    print("🚀 Starting simulation...")
    print("⏱️  Expected runtime: 20-30 minutes (faster without communication)")
    print("")

    runner = SimulationRunner(config)
    results = runner.run()
    final_state = results["final_state"]

    print("\n✅ Simulation complete!")

    # Analyze results
    convergence_data = analyze_results(final_state)

    # Save results
    os.makedirs("experiments/baseline/results", exist_ok=True)
    output_file = f"experiments/baseline/results/experiment_A_no_communication_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w') as f:
        json.dump({
            "experiment": "A_no_communication",
            "configuration": {
                "communication_enabled": False,
                "transparency_enabled": True,
                "num_days": 21
            },
            "config": config.to_dict(),
            "communications": final_state.get("communications_log", []),
            "market_offers": final_state.get("market_offers_log", []),
            "convergence_analysis": convergence_data,
            "final_state_summary": {
                "total_days": final_state["day"],
                "wholesaler_cash": final_state["agent_ledgers"]["Wholesaler"]["cash"],
                "wholesaler2_cash": final_state["agent_ledgers"]["Wholesaler_2"]["cash"],
                "seller1_cash": final_state["agent_ledgers"]["Seller_1"]["cash"],
                "seller2_cash": final_state["agent_ledgers"]["Seller_2"]["cash"]
            }
        }, f, indent=2)

    print(f"\n📊 Results saved to: {output_file}")
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("1. Compare convergence with Experiment D (treatment)")
    print("2. Run statistical significance tests")
    print("3. Analyze if transparency alone enables tacit coordination")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
