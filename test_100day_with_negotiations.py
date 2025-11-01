"""Test 100-day simulation with negotiations on days 1, 21, 41, 61, 81."""

from src.simulation.config import SimulationConfig
from src.simulation.runner import SimulationRunner
import logging

# Create config with negotiations on specific days
config = SimulationConfig(
    name='100-Day Simulation with Negotiations',
    description='100-day simulation with negotiations on days 1, 21, 41, 61, 81',
    num_days=100,
    
    # Seller 1 configuration - lower cost, higher inventory
    s1_cost_min=58,
    s1_cost_max=62,
    s1_inv_min=8000,
    s1_inv_max=8500,
    s1_starting_cash=0,
    
    # Seller 2 configuration - higher cost, lower inventory
    s2_cost_min=68,
    s2_cost_max=72,
    s2_inv_min=1800,
    s2_inv_max=2200,
    s2_starting_cash=0,
    
    # Wholesaler configuration
    wholesaler_starting_cash=50000,
    
    # Shopper configuration - moderate demand
    total_shoppers=400,
    long_term_ratio=0.7,  # 70% long-term, 30% short-term
    
    # Long-term shoppers (more patient, lower urgency)
    lt_demand_min=5,
    lt_demand_max=15,
    lt_window_min=5,
    lt_window_max=10,
    lt_base_price_min=80.0,
    lt_base_price_max=100.0,
    lt_max_price_min=110.0,
    lt_max_price_max=130.0,
    lt_urgency_min=0.7,
    lt_urgency_max=1.2,
    
    # Short-term shoppers (less patient, higher urgency)
    st_demand_min=3,
    st_demand_max=10,
    st_window_min=1,
    st_window_max=3,
    st_base_price_min=100.0,
    st_base_price_max=120.0,
    st_max_price_min=120.0,
    st_max_price_max=150.0,
    st_urgency_min=1.5,
    st_urgency_max=2.5,
    
    # Negotiation configuration
    negotiation_days=[1, 21, 41, 61, 81],
    max_negotiation_rounds=10,
)

print("=" * 80)
print("SIMULATION CONFIGURATION:")
print("=" * 80)
print(f"  Name: {config.name}")
print(f"  Days: {config.num_days}")
print(f"  Negotiation Days: {config.negotiation_days}")
print(f"  Max Negotiation Rounds: {config.max_negotiation_rounds}")
print(f"  Total Shoppers: {config.total_shoppers}")
print(f"  Long-term Ratio: {config.long_term_ratio * 100:.0f}%")
print()
print(f"  Seller 1:")
print(f"    - Cost: ${config.s1_cost_min}-${config.s1_cost_max}")
print(f"    - Inventory: {config.s1_inv_min:,}-{config.s1_inv_max:,} units")
print(f"    - Starting Cash: ${config.s1_starting_cash:,}")
print()
print(f"  Seller 2:")
print(f"    - Cost: ${config.s2_cost_min}-${config.s2_cost_max}")
print(f"    - Inventory: {config.s2_inv_min:,}-{config.s2_inv_max:,} units")
print(f"    - Starting Cash: ${config.s2_starting_cash:,}")
print()
print(f"  Wholesaler:")
print(f"    - Starting Cash: ${config.wholesaler_starting_cash:,}")
print("=" * 80)
print()

# Run simulation
runner = SimulationRunner(config, log_level=logging.debug)
results = runner.run()

print('\n' + '=' * 80)
print('FINAL RESULTS:')
print('=' * 80)

# Agent performance
for agent, ledger in results['final_state']['agent_ledgers'].items():
    pnl = ledger["total_revenue"] - ledger["total_cost_incurred"]
    print(f'\n{agent}:')
    print(f'  Inventory: {ledger["inventory"]:,} units')
    print(f'  Cash: ${ledger["cash"]:,.2f}')
    print(f'  Revenue: ${ledger["total_revenue"]:,.2f}')
    print(f'  Costs: ${ledger["total_cost_incurred"]:,.2f}')
    print(f'  PnL: ${pnl:,.2f}')

# Market summary
summary = results['summary']
print('\n' + '=' * 80)
print('MARKET SUMMARY:')
print('=' * 80)
print(f'  Total Market Trades (B2C): {summary["total_market_trades"]}')
print(f'  Total Market Volume: {summary["total_market_volume"]:,} units')
print(f'  Average Market Price: ${summary["average_market_price"]:.2f}')
print()
print(f'  Total Wholesale Trades (B2B): {summary["total_wholesale_trades"]}')
print(f'  Total Wholesale Volume: {summary["total_wholesale_volume"]:,} units')
print(f'  Average Wholesale Price: ${summary["average_wholesale_price"]:.2f}')
print()
print(f'  Total Unmet Demand: {summary["total_unmet_demand"]:,} units')
print()

# Negotiation summary
wholesale_log = results['final_state']['wholesale_trades_log']
if wholesale_log:
    print('=' * 80)
    print('WHOLESALE NEGOTIATION RESULTS:')
    print('=' * 80)
    for day in config.negotiation_days:
        day_trades = [t for t in wholesale_log if t['day'] == day]
        if day_trades:
            print(f'\nDay {day}:')
            for trade in day_trades:
                print(f'  {trade["buyer"]} ← {trade["seller"]}: {trade["quantity"]:,} units @ ${trade["price"]}/unit (Total: ${trade["price"] * trade["quantity"]:,.2f})')
        else:
            print(f'\nDay {day}: No wholesale trades')

# Daily market activity summary (every 10 days)
print('\n' + '=' * 80)
print('MARKET ACTIVITY SUMMARY (Every 10 Days):')
print('=' * 80)
market_log = results['final_state']['market_log']
for day in range(10, config.num_days + 1, 10):
    # Get trades for this 10-day period
    period_start = day - 9
    period_trades = [t for t in market_log if period_start <= t['day'] <= day]
    
    if period_trades:
        period_volume = sum(t['quantity'] for t in period_trades)
        period_revenue = sum(t['price'] * t['quantity'] for t in period_trades)
        avg_price = period_revenue / period_volume if period_volume > 0 else 0
        
        # Breakdown by seller
        seller_breakdown = {}
        for trade in period_trades:
            seller = trade['seller']
            if seller not in seller_breakdown:
                seller_breakdown[seller] = {'volume': 0, 'revenue': 0}
            seller_breakdown[seller]['volume'] += trade['quantity']
            seller_breakdown[seller]['revenue'] += trade['price'] * trade['quantity']
        
        print(f'\nDays {period_start}-{day}:')
        print(f'  Total: {len(period_trades)} trades, {period_volume:,} units, ${avg_price:.2f} avg price')
        for seller, data in seller_breakdown.items():
            seller_avg = data['revenue'] / data['volume'] if data['volume'] > 0 else 0
            print(f'    {seller}: {data["volume"]:,} units @ ${seller_avg:.2f} avg (${data["revenue"]:,.2f} revenue)')
    else:
        print(f'\nDays {period_start}-{day}: No trades')

# Unmet demand summary (every 10 days)
print('\n' + '=' * 80)
print('UNMET DEMAND SUMMARY (Every 10 Days):')
print('=' * 80)
unmet_log = results['final_state']['unmet_demand_log']
for day in range(10, config.num_days + 1, 10):
    period_start = day - 9
    period_unmet = [u for u in unmet_log if period_start <= u['day'] <= day]
    
    if period_unmet:
        total_unmet = sum(u['quantity'] for u in period_unmet)
        print(f'  Days {period_start}-{day}: {total_unmet:,} units unmet')
    else:
        print(f'  Days {period_start}-{day}: 0 units unmet')

print('\n' + '=' * 80)
print('SIMULATION COMPLETE!')
print('=' * 80)
print(f'Log file: {results["log_file"]}')
print('=' * 80)

