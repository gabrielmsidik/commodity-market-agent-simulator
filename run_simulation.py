"""Example script to run a simulation programmatically."""

import logging
from src.simulation import SimulationConfig, SimulationRunner

def main():
    """Run a simple simulation."""
    # Create configuration
    config = SimulationConfig(
        name="100 Day - Full Simulation - final technical update",
        description="Updated PnL information and added that to prompts",
        num_days=100,  # Default simulation for testing
        s1_cost_min=58,
        s1_cost_max=62,
        s1_inv_min=7800,
        s1_inv_max=8200,
        s2_cost_min=68,
        s2_cost_max=72,
        s2_inv_min=1900,
        s2_inv_max=2100,
        total_shoppers=300,
        long_term_ratio=0.7
    )
    
    print("=" * 80)
    print(f"Running simulation: {config.name}")
    print(f"Description: {config.description}")
    print(f"Duration: {config.num_days} days")
    print("=" * 80)
    
    # Run simulation with INFO level logging
    runner = SimulationRunner(config, log_level=logging.DEBUG)
    results = runner.run()
    
    # Print summary
    print("\n" + "=" * 80)
    print("SIMULATION RESULTS")
    print("=" * 80)
    
    summary = results['summary']
    
    print(f"\nMarket Trades:")
    print(f"  Total Trades: {summary['total_market_trades']}")
    print(f"  Total Volume: {summary['total_market_volume']}")
    print(f"  Average Price: ${summary['average_market_price']:.2f}")
    print(f"  Unmet Demand: {summary['total_unmet_demand']}")
    
    print(f"\nWholesale Trades:")
    print(f"  Total Trades: {summary['total_wholesale_trades']}")
    print(f"  Total Volume: {summary['total_wholesale_volume']}")
    print(f"  Average Price: ${summary['average_wholesale_price']:.2f}")
    
    print(f"\nAgent Performance:")
    for agent_name, perf in summary['agent_performance'].items():
        print(f"  {agent_name}:")
        print(f"    Profit: ${perf['profit']:.2f}")
        print(f"    Final Inventory: {perf['remaining_inventory']}")
        print(f"    Final Cash: ${perf['final_cash']:.2f}")
    
    print("\n" + "=" * 80)
    print(f"Detailed logs saved to: logs/simulation_*.log")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    main()

