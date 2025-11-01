#!/usr/bin/env python3
"""Run a single baseline experiment with specified configuration."""

import argparse
import sys
from src.simulation.runner import SimulationRunner
from src.simulation.config import SimulationConfig

def main():
    parser = argparse.ArgumentParser(description="Run baseline experiment")
    parser.add_argument("--experiment", choices=["A", "B", "C", "D"], required=True,
                       help="Experiment: A=NoComm+NoTrans, B=NoComm+Trans, C=Comm+NoTrans, D=Comm+Trans")
    parser.add_argument("--days", type=int, default=21, help="Number of days to simulate")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory")

    args = parser.parse_args()

    # Map experiments to config
    experiments = {
        "A": (False, False),  # No communication, No transparency
        "B": (False, True),   # No communication, With transparency
        "C": (True, False),   # With communication, No transparency
        "D": (True, True)     # With communication, With transparency (full treatment)
    }

    enable_comm, enable_trans = experiments[args.experiment]

    print(f"Running Experiment {args.experiment}:")
    print(f"  - Communication: {enable_comm}")
    print(f"  - Price Transparency: {enable_trans}")
    print(f"  - Days: {args.days}")
    print(f"  - Output: {args.output_dir}")

    # Create config
    config = SimulationConfig(
        name=args.output_dir.replace("outputs/", "").replace("/", "_"),
        num_days=args.days,
        enable_communication=enable_comm,
        enable_price_transparency=enable_trans
    )

    # Run simulation
    runner = SimulationRunner(config)
    runner.run()

    print(f"\nExperiment {args.experiment} completed!")
    print(f"Results saved to: {args.output_dir}")

if __name__ == "__main__":
    main()
