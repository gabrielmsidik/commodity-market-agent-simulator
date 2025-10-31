"""Diagnostic script to analyze the matching algorithm behavior."""

import logging
from src.simulation import SimulationConfig, SimulationRunner

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def analyze_matching():
    """Run a short simulation and analyze matching behavior."""
    
    print("=" * 80)
    print("MATCHING ALGORITHM ANALYSIS")
    print("=" * 80)
    print()
    
    # Run a very short simulation for analysis
    config = SimulationConfig(
        name="Matching Analysis",
        description="Analyzing matching algorithm behavior",
        num_days=5,  # Just 5 days
        total_shoppers=20  # Fewer shoppers for easier analysis
    )
    
    runner = SimulationRunner(config, log_level=logging.INFO)
    results = runner.run()
    
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print()
    
    # Analyze the results
    summary = results['summary']
    final_state = results['final_state']
    market_log = final_state['market_log']
    unmet_demand_log = final_state['unmet_demand_log']
    
    print("📊 OVERALL SUMMARY:")
    print(f"  Total Market Trades (aggregated entries): {summary['total_market_trades']}")
    print(f"  Total Market Volume (units sold): {summary['total_market_volume']}")
    print(f"  Average Market Price: ${summary['average_market_price']:.2f}")
    print(f"  Total Unmet Demand: {summary['total_unmet_demand']} shopper-units")
    print()
    
    print("⚠️  IMPORTANT CLARIFICATION:")
    print("  'Total Market Trades' = Number of aggregated trade entries (one per seller per day)")
    print("  'Total Market Volume' = Actual number of units sold to shoppers")
    print()
    
    # Analyze day by day
    print("📅 DAY-BY-DAY BREAKDOWN:")
    print()
    
    for day in range(1, config.num_days + 1):
        print(f"--- Day {day} ---")
        
        # Get trades for this day
        day_trades = [t for t in market_log if t['day'] == day]
        day_unmet = [u for u in unmet_demand_log if u['day'] == day]
        
        if day_trades:
            total_volume = sum(t['quantity'] for t in day_trades)
            print(f"  ✅ Trades: {len(day_trades)} aggregated entries")
            print(f"  📦 Volume: {total_volume} units sold")
            
            for trade in day_trades:
                print(f"     - {trade['seller']}: {trade['quantity']} units @ ${trade['price']}")
        else:
            print(f"  ❌ No trades")
        
        if day_unmet:
            print(f"  ⚠️  Unmet Demand: {len(day_unmet)} shopper-units couldn't buy")
            
            # Group by willing_to_pay to see price distribution
            price_groups = {}
            for u in day_unmet:
                price = u['willing_to_pay']
                price_groups[price] = price_groups.get(price, 0) + 1
            
            print(f"     Price distribution of unmet shoppers:")
            for price in sorted(price_groups.keys(), reverse=True):
                count = price_groups[price]
                print(f"       ${price}: {count} units")
        
        print()
    
    # Analyze why shoppers didn't buy
    print("🔍 MATCHING ALGORITHM VERIFICATION:")
    print()
    
    # Check if the algorithm is matching correctly
    if unmet_demand_log:
        print("  Checking unmet demand reasons...")
        
        # Sample a few unmet demands
        sample_unmet = unmet_demand_log[:5]
        
        for unmet in sample_unmet:
            day = unmet['day']
            willing_to_pay = unmet['willing_to_pay']
            
            # Find what prices were available that day
            day_trades = [t for t in market_log if t['day'] == day]
            
            if day_trades:
                min_price = min(t['price'] for t in day_trades)
                print(f"  Day {day}: Shopper willing to pay ${willing_to_pay}, "
                      f"lowest seller price was ${min_price}")
                
                if willing_to_pay >= min_price:
                    print(f"    ⚠️  WARNING: Shopper should have matched but didn't!")
                else:
                    print(f"    ✓ Correct: Shopper's price too low")
            else:
                print(f"  Day {day}: Shopper willing to pay ${willing_to_pay}, "
                      f"but no sellers had inventory")
    
    print()
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print()
    print("1. The matching algorithm DOES match against the ENTIRE market")
    print("   - All shoppers in daily_shopper_pool are considered")
    print("   - All sellers with inventory > 0 are considered")
    print()
    print("2. 'Number of trades' in logs = aggregated entries (one per seller)")
    print("   - This is NOT the number of units sold")
    print("   - Check 'Total Volume' for actual units sold")
    print()
    print("3. Shoppers don't buy when:")
    print("   - Their willing_to_pay < lowest seller price")
    print("   - All sellers run out of inventory")
    print()
    print("4. The two-pointer algorithm ensures:")
    print("   - Highest-paying shoppers get matched first")
    print("   - Lowest-priced sellers sell first")
    print("   - Optimal market clearing")
    print()
    
    # Show agent performance
    print("💰 AGENT PERFORMANCE:")
    print()
    for agent_name, perf in summary['agent_performance'].items():
        print(f"  {agent_name}:")
        print(f"    Profit: ${perf['profit']:.2f}")
        print(f"    Revenue: ${perf['revenue']:.2f}")
        print(f"    Final Inventory: {perf['final_inventory']} units")
        print(f"    Final Cash: ${perf['final_cash']:.2f}")
        print()


if __name__ == "__main__":
    analyze_matching()

