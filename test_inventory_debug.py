"""Quick test script to debug inventory tracking."""

from src.simulation.config import SimulationConfig
from src.simulation.runner import SimulationRunner
import logging

config = SimulationConfig(
    name='Inventory Debug Test',
    description='3-day test with debug logging',
    num_days=3,
    total_shoppers=50,
    long_term_ratio=1.0,
    lt_demand_min=10,
    lt_demand_max=20,
    lt_window_min=1,
    lt_window_max=3,
)

runner = SimulationRunner(config, log_level=logging.DEBUG)
results = runner.run()

print('\n=== FINAL INVENTORY ===')
for agent, ledger in results['final_state']['agent_ledgers'].items():
    print(f'{agent}: {ledger["inventory"]} units')

