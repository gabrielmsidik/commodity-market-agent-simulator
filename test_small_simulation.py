"""Small test simulation to debug negative sales and validate performance attributes."""

import logging
from src.simulation import SimulationConfig, SimulationRunner

def main():
    """Run a small simulation for debugging."""
    # Create a SMALL configuration for quick testing
    config = SimulationConfig(
        name="Small Test - Debug Negative Sales",
        description="Small 3-day test to debug negative sales and validate performance attributes",
        num_days=3,  # Only 3 days for quick testing
        s1_cost_min=58,
        s1_cost_max=62,
        s1_inv_min=100,  # Small inventory
        s1_inv_max=150,
        s2_cost_min=68,
        s2_cost_max=72,
        s2_inv_min=50,   # Small inventory
        s2_inv_max=100,
        total_shoppers=20,  # Only 20 shoppers
        long_term_ratio=0.7
    )
    
    print("=" * 80)
    print(f"Running simulation: {config.name}")
    print(f"Description: {config.description}")
    print(f"Duration: {config.num_days} days")
    print("=" * 80)
    
    # Run simulation with DEBUG level logging
    runner = SimulationRunner(config, log_level=logging.INFO)
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
        print(f"\n  {agent_name}:")
        print(f"    Profit: ${perf['profit']:.2f}")
        print(f"    Revenue: ${perf['revenue']:.2f}")
        print(f"    Costs: ${perf['costs']:.2f}")
        print(f"    Market Units Sold: {perf['market_units_sold']}")
        print(f"    Wholesale Units Sold: {perf['wholesale_units_sold']}")
        print(f"    Wholesale Units Bought: {perf['wholesale_units_bought']}")
        print(f"    Remaining Inventory: {perf['remaining_inventory']}")
        print(f"    Final Cash: ${perf['final_cash']:.2f}")
        
        # Check for negative sales
        if perf['revenue'] < 0:
            print(f"    ⚠️  WARNING: Negative revenue detected!")
        if perf['costs'] < 0:
            print(f"    ⚠️  WARNING: Negative costs detected!")
    
    print("\n" + "=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)
    
    # Validate attributes exist
    print("\nChecking agent_performance attributes:")
    expected_attrs = [
        'profit', 'revenue', 'costs', 'market_units_sold',
        'wholesale_units_sold', 'wholesale_units_bought',
        'remaining_inventory', 'final_cash'
    ]
    
    for agent_name, perf in summary['agent_performance'].items():
        print(f"\n  {agent_name}:")
        for attr in expected_attrs:
            if attr in perf:
                print(f"    ✓ {attr}: {perf[attr]}")
            else:
                print(f"    ✗ {attr}: MISSING!")
    
    print("\n" + "=" * 80)
    print(f"Detailed logs saved to: logs/simulation_*.log")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    main()

