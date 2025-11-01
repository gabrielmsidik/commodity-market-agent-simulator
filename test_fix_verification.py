"""Verify the fix for the market allocation bug."""

from src.graph.nodes import setup_day
from src.models import EconomicState, Shopper

# Create a test state with Day 19 scenario
state = {
    'day': 19,
    'shopper_database': [
        {
            'shopper_id': 'S1',
            'shopping_window_start': 1,
            'shopping_window_end': 30,
            'demand_remaining': 7,
            'base_willing_to_pay': 110.0,
            'max_willing_to_pay': 120.0,
            'urgency_factor': 1.0,
            'shopper_type': 'long_term',
            'total_demand': 7
        },
        {
            'shopper_id': 'S2',
            'shopping_window_start': 1,
            'shopping_window_end': 30,
            'demand_remaining': 5,
            'base_willing_to_pay': 100.0,
            'max_willing_to_pay': 110.0,
            'urgency_factor': 1.0,
            'shopper_type': 'long_term',
            'total_demand': 5
        },
        {
            'shopper_id': 'S3',
            'shopping_window_start': 1,
            'shopping_window_end': 30,
            'demand_remaining': 10,
            'base_willing_to_pay': 95.0,
            'max_willing_to_pay': 105.0,
            'urgency_factor': 1.0,
            'shopper_type': 'long_term',
            'total_demand': 10
        }
    ]
}

result = setup_day(state)
pool = result['daily_shopper_pool']

print("=" * 80)
print("VERIFICATION OF FIX FOR MARKET ALLOCATION BUG")
print("=" * 80)
print()

print(f"Total demand units created: {len(pool)}")
print(f"Expected: 22 (7 + 5 + 10)")
print()

# Check for unique IDs
shopper_ids = [s["shopper_id"] for s in pool]
unique_ids = set(shopper_ids)

print(f"Unique shopper IDs: {len(unique_ids)}")
print(f"Expected: 22 (all should be unique)")
print()

# Check if IDs follow the pattern
print("Sample entries (first 10):")
for i, entry in enumerate(pool[:10]):
    print(f"  {i}: shopper_id={entry['shopper_id']}, wtp={entry['willing_to_pay']}")
print()

# Verify the fix
if len(unique_ids) == len(pool):
    print("✅ FIX VERIFIED: All shopper IDs are unique!")
    print("   This means no dictionary key collisions will occur in the matching algorithm.")
else:
    print("❌ FIX FAILED: Duplicate IDs detected!")
    print(f"   Total entries: {len(pool)}, Unique IDs: {len(unique_ids)}")
    print(f"   Duplicates: {len(pool) - len(unique_ids)}")

print()
print("=" * 80)

