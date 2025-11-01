"""Test simulation with NO negotiations to debug matching algorithm."""

from src.simulation.config import SimulationConfig
from src.simulation.runner import SimulationRunner
import logging

# Create config with NO negotiations
config = SimulationConfig(
    name='No Negotiations Test',
    description='1-day test with no negotiations to debug matching',
    num_days=1,
    total_shoppers=10,
    long_term_ratio=1.0,
    lt_demand_min=5,
    lt_demand_max=10,
    lt_window_min=1,
    lt_window_max=1,
    negotiation_days=[],  # NO NEGOTIATIONS!
)

print("=" * 80)
print("CONFIGURATION:")
print(f"  Negotiation Days: {config.negotiation_days}")
print(f"  Max Negotiation Rounds: {config.max_negotiation_rounds}")
print("=" * 80)
print()

runner = SimulationRunner(config, log_level=logging.INFO)
results = runner.run()

print('\n' + '=' * 80)
print('FINAL RESULTS:')
print('=' * 80)
for agent, ledger in results['final_state']['agent_ledgers'].items():
    print(f'{agent}:')
    print(f'  Inventory: {ledger["inventory"]} units')
    print(f'  Cash: ${ledger["cash"]:,.2f}')
    print(f'  Revenue: ${ledger["total_revenue"]:,.2f}')
    print(f'  Costs: ${ledger["total_cost_incurred"]:,.2f}')
    pnl = ledger["total_revenue"] - ledger["total_cost_incurred"]
    print(f'  PnL: ${pnl:,.2f}')
    print()

