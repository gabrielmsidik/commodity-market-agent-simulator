"""Test 10-day simulation with NO negotiations."""

from src.simulation.config import SimulationConfig
from src.simulation.runner import SimulationRunner
import logging

# Create config with NO negotiations
config = SimulationConfig(
    name='10-Day No Negotiations Test',
    description='10-day simulation with no negotiations to test market dynamics',
    num_days=10,
    
    # Seller configurations
    s1_cost_min=58,
    s1_cost_max=62,
    s1_inv_min=500,
    s1_inv_max=600,
    
    s2_cost_min=68,
    s2_cost_max=72,
    s2_inv_min=300,
    s2_inv_max=400,
    
    # Shopper configuration - moderate demand
    total_shoppers=50,
    long_term_ratio=0.7,  # 70% long-term, 30% short-term
    
    # Long-term shoppers
    lt_demand_min=5,
    lt_demand_max=15,
    lt_window_min=3,
    lt_window_max=8,
    lt_base_price_min=80.0,
    lt_base_price_max=100.0,
    lt_max_price_min=110.0,
    lt_max_price_max=130.0,
    lt_urgency_min=0.7,
    lt_urgency_max=1.2,
    
    # Short-term shoppers
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
    
    # NO NEGOTIATIONS!
    negotiation_days=[],
    max_negotiation_rounds=10,
)

print("=" * 80)
print("SIMULATION CONFIGURATION:")
print("=" * 80)
print(f"  Name: {config.name}")
print(f"  Days: {config.num_days}")
print(f"  Negotiation Days: {config.negotiation_days}")
print(f"  Total Shoppers: {config.total_shoppers}")
print(f"  Seller 1: Cost ${config.s1_cost_min}-${config.s1_cost_max}, Inventory {config.s1_inv_min}-{config.s1_inv_max}")
print(f"  Seller 2: Cost ${config.s2_cost_min}-${config.s2_cost_max}, Inventory {config.s2_inv_min}-{config.s2_inv_max}")
print("=" * 80)
print()

# Run simulation
runner = SimulationRunner(config, log_level=logging.INFO)
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
print(f'  Total Market Trades: {summary["total_market_trades"]}')
print(f'  Total Volume Sold: {summary["total_market_volume"]:,} units')
print(f'  Average Price: ${summary["average_market_price"]:.2f}')
print(f'  Total Unmet Demand: {summary["total_unmet_demand"]:,} units')
print()

# Daily breakdown
print('=' * 80)
print('DAILY BREAKDOWN:')
print('=' * 80)
market_log = results['final_state']['market_log']
for day in range(1, config.num_days + 1):
    day_trades = [t for t in market_log if t['day'] == day]
    if day_trades:
        day_volume = sum(t['quantity'] for t in day_trades)
        day_revenue = sum(t['price'] * t['quantity'] for t in day_trades)
        avg_price = day_revenue / day_volume if day_volume > 0 else 0
        
        # Breakdown by seller
        seller_breakdown = {}
        for trade in day_trades:
            seller = trade['seller']
            if seller not in seller_breakdown:
                seller_breakdown[seller] = {'volume': 0, 'revenue': 0}
            seller_breakdown[seller]['volume'] += trade['quantity']
            seller_breakdown[seller]['revenue'] += trade['price'] * trade['quantity']
        
        print(f'\nDay {day}:')
        print(f'  Total: {len(day_trades)} trades, {day_volume:,} units, ${avg_price:.2f} avg price')
        for seller, data in seller_breakdown.items():
            print(f'    {seller}: {data["volume"]:,} units, ${data["revenue"]:,.2f} revenue')
    else:
        print(f'\nDay {day}: No trades')

print('\n' + '=' * 80)

