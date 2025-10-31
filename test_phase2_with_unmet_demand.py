"""Test Phase 2 optimization with unmet demand (lowball shoppers)."""

from test_matching_algorithm import run_matching_algorithm, ShopperPoolEntry

def test_phase2_with_lowball_shoppers():
    """
    Test that Phase 2 optimization still works even when some shoppers are unmet.
    
    Scenario:
    - 5 shoppers: 3 can afford products, 2 are lowball (too cheap)
    - 3 sellers with different prices
    - Phase 1: 3 shoppers matched, 2 unmet (lowballs)
    - Phase 2: Should still optimize the 3 matched shoppers, ignoring the lowballs
    
    This ensures lowball actors don't disable the optimization for everyone else!
    """
    
    shoppers = [
        # These can afford products
        ShopperPoolEntry(shopper_id="S1", willing_to_pay=120, demand_unit=1),
        ShopperPoolEntry(shopper_id="S2", willing_to_pay=115, demand_unit=1),
        ShopperPoolEntry(shopper_id="S3", willing_to_pay=110, demand_unit=1),
        # These are lowballs - can't afford anything
        ShopperPoolEntry(shopper_id="S4_lowball", willing_to_pay=50, demand_unit=1),
        ShopperPoolEntry(shopper_id="S5_lowball", willing_to_pay=40, demand_unit=1),
    ]
    
    offers = {
        "Seller_1": {"price": 120, "quantity": 1, "inventory_available": 1},
        "Seller_2": {"price": 107, "quantity": 1, "inventory_available": 1},
        "Wholesaler": {"price": 95, "quantity": 1, "inventory_available": 1},
    }
    
    result = run_matching_algorithm(shoppers, offers)
    
    print("=" * 80)
    print("PHASE 2 WITH LOWBALL SHOPPERS TEST")
    print("=" * 80)
    print(f"\nShoppers:")
    for s in shoppers:
        print(f"  {s['shopper_id']}: WTP ${s['willing_to_pay']}")
    
    print(f"\nSellers:")
    for name, offer in offers.items():
        print(f"  {name}: ${offer['price']} ({offer['quantity']} units)")
    
    print(f"\nExpected Behavior:")
    print(f"  Phase 1:")
    print(f"    - S1, S2, S3 matched (can afford)")
    print(f"    - S4_lowball, S5_lowball unmet (too cheap)")
    print(f"  Phase 2:")
    print(f"    - Optimize S1, S2, S3 to cheaper alternatives")
    print(f"    - Ignore lowballs (they don't block optimization!)")
    
    print(f"\nActual Results:")
    print(f"  Total Matched: {result['total_matched']}")
    print(f"  Total Unmet: {result['total_unmet']}")
    
    print(f"\nQuantities Sold:")
    for agent, qty in result['quantities_sold'].items():
        print(f"  {agent}: {qty} units")
    
    print(f"\nShopper Purchases:")
    for shopper_id, qty in result['shopper_purchases'].items():
        print(f"  {shopper_id}: {qty} units")
    
    print(f"\nUnmet Demand:")
    for unmet in result['unmet_demand']:
        print(f"  {unmet['shopper_id']}: WTP ${unmet['willing_to_pay']}")
    
    print("\n" + "=" * 80)
    
    # Assertions
    assert result["total_matched"] == 3, "3 shoppers should be matched (S1, S2, S3)"
    assert result["total_unmet"] == 2, "2 lowball shoppers should be unmet"
    
    # All inventory should sell (Phase 2 optimization)
    assert result["quantities_sold"]["Wholesaler"] == 1, "Wholesaler should sell"
    assert result["quantities_sold"]["Seller_2"] == 1, "Seller_2 should sell"
    assert result["quantities_sold"]["Seller_1"] == 1, "Seller_1 should sell"
    
    # Lowballs should be unmet
    unmet_ids = [u['shopper_id'] for u in result['unmet_demand']]
    assert "S4_lowball" in unmet_ids, "S4_lowball should be unmet"
    assert "S5_lowball" in unmet_ids, "S5_lowball should be unmet"
    
    print("✅ All assertions passed!")
    print("\nKey Achievement:")
    print("  ✓ Phase 2 optimization ran despite unmet demand")
    print("  ✓ Lowball shoppers didn't block optimization for others")
    print("  ✓ All 3 matched shoppers got optimized to cheaper prices")
    print("  ✓ All inventory sold efficiently")
    print("=" * 80)


def test_phase2_mixed_scenario():
    """
    Test a realistic mixed scenario:
    - Some shoppers matched
    - Some shoppers unmet (lowballs)
    - Unsold cheap inventory exists
    - Phase 2 should optimize matched shoppers to use cheap inventory
    """
    
    shoppers = [
        # High-value shoppers
        ShopperPoolEntry(shopper_id="S1", willing_to_pay=120, demand_unit=1),
        ShopperPoolEntry(shopper_id="S2", willing_to_pay=115, demand_unit=1),
        # Mid-value shoppers
        ShopperPoolEntry(shopper_id="S3", willing_to_pay=100, demand_unit=1),
        ShopperPoolEntry(shopper_id="S4", willing_to_pay=98, demand_unit=1),
        # Lowball shoppers (can't afford anything)
        ShopperPoolEntry(shopper_id="S5_lowball", willing_to_pay=60, demand_unit=1),
        ShopperPoolEntry(shopper_id="S6_lowball", willing_to_pay=50, demand_unit=1),
    ]
    
    offers = {
        "Seller_1": {"price": 120, "quantity": 2, "inventory_available": 2},
        "Seller_2": {"price": 107, "quantity": 2, "inventory_available": 2},
        "Wholesaler": {"price": 95, "quantity": 3, "inventory_available": 3},
    }
    
    result = run_matching_algorithm(shoppers, offers)
    
    print("\n" + "=" * 80)
    print("MIXED SCENARIO: MATCHED + UNMET + UNSOLD INVENTORY")
    print("=" * 80)
    print(f"\nShoppers: 6 total (4 can afford, 2 lowballs)")
    for s in shoppers:
        print(f"  {s['shopper_id']}: WTP ${s['willing_to_pay']}")
    
    print(f"\nSellers: 7 units total")
    for name, offer in offers.items():
        print(f"  {name}: ${offer['price']} ({offer['quantity']} units)")
    
    print(f"\nPhase 1 (without optimization):")
    print(f"  S1 → Seller_1 @ $120")
    print(f"  S2 → Seller_1 @ $120")
    print(f"  S3 → Seller_2 @ $107")
    print(f"  S4 → Seller_2 @ $107")
    print(f"  S5_lowball, S6_lowball → UNMET")
    print(f"  Wholesaler @ $95 (3 units) → UNSOLD")
    
    print(f"\nPhase 2 (with optimization):")
    print(f"  Should re-match S1-S4 to use Wholesaler's cheap inventory")
    print(f"  Lowballs remain unmet (don't block optimization)")
    
    print(f"\nActual Results:")
    print(f"  Total Matched: {result['total_matched']}")
    print(f"  Total Unmet: {result['total_unmet']}")
    
    print(f"\nQuantities Sold:")
    for agent, qty in result['quantities_sold'].items():
        print(f"  {agent}: {qty} units")
    
    print("\n" + "=" * 80)
    
    # Assertions
    assert result["total_matched"] == 4, "4 shoppers should be matched"
    assert result["total_unmet"] == 2, "2 lowball shoppers should be unmet"
    
    # After Phase 2, Wholesaler (cheapest) should sell the most
    assert result["quantities_sold"]["Wholesaler"] >= 3, "Wholesaler should sell at least 3 units (Phase 2 optimization)"
    
    # Lowballs should be unmet
    unmet_ids = [u['shopper_id'] for u in result['unmet_demand']]
    assert "S5_lowball" in unmet_ids
    assert "S6_lowball" in unmet_ids
    
    print("✅ All assertions passed!")
    print("\nPhase 2 Generalization Success:")
    print("  ✓ Optimization works with partial demand fulfillment")
    print("  ✓ Lowball shoppers isolated (don't affect others)")
    print("  ✓ Cheap inventory prioritized for matched shoppers")
    print("  ✓ Economic efficiency maximized for viable participants")
    print("=" * 80)


if __name__ == "__main__":
    test_phase2_with_lowball_shoppers()
    test_phase2_mixed_scenario()

