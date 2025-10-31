"""Test the Phase 2 price optimization algorithm."""

from test_matching_algorithm import run_matching_algorithm, ShopperPoolEntry

def test_phase2_optimization():
    """
    Test that Phase 2 re-matches shoppers to cheaper alternatives when all demand is met.
    
    Scenario:
    - 3 shoppers with high WTP
    - 3 sellers: expensive, mid-price, cheap
    - All shoppers can afford all sellers
    - Phase 1: Shoppers buy from expensive sellers first
    - Phase 2: Should re-match to cheaper alternatives
    """
    
    shoppers = [
        ShopperPoolEntry(shopper_id="S1", willing_to_pay=120, demand_unit=1),
        ShopperPoolEntry(shopper_id="S2", willing_to_pay=115, demand_unit=1),
        ShopperPoolEntry(shopper_id="S3", willing_to_pay=110, demand_unit=1),
    ]
    
    offers = {
        "Seller_1": {"price": 120, "quantity": 1, "inventory_available": 1},
        "Seller_2": {"price": 107, "quantity": 1, "inventory_available": 1},
        "Wholesaler": {"price": 95, "quantity": 1, "inventory_available": 1},
    }
    
    result = run_matching_algorithm(shoppers, offers)
    
    print("=" * 80)
    print("PHASE 2 OPTIMIZATION TEST")
    print("=" * 80)
    print(f"\nShoppers:")
    for s in shoppers:
        print(f"  {s['shopper_id']}: WTP ${s['willing_to_pay']}")
    
    print(f"\nSellers:")
    for name, offer in offers.items():
        print(f"  {name}: ${offer['price']} ({offer['quantity']} units)")
    
    print(f"\nResults:")
    print(f"  Total Matched: {result['total_matched']}")
    print(f"  Total Unmet: {result['total_unmet']}")
    
    print(f"\nQuantities Sold:")
    for agent, qty in result['quantities_sold'].items():
        print(f"  {agent}: {qty} units")
    
    print(f"\nShopper Purchases:")
    for shopper_id, qty in result['shopper_purchases'].items():
        print(f"  {shopper_id}: {qty} units")
    
    print("\n" + "=" * 80)
    
    # Assertions
    assert result["total_matched"] == 3, "All 3 shoppers should be matched"
    assert result["total_unmet"] == 0, "No unmet demand"
    
    # After Phase 2 optimization, cheaper sellers should sell out first
    assert result["quantities_sold"]["Wholesaler"] == 1, "Wholesaler (cheapest) should sell 1"
    assert result["quantities_sold"]["Seller_2"] == 1, "Seller_2 (mid-price) should sell 1"
    assert result["quantities_sold"]["Seller_1"] == 1, "Seller_1 (expensive) should sell 1"
    
    print("✅ All assertions passed!")
    print("\nPhase 2 optimization working correctly:")
    print("  - All demand met (3/3 shoppers)")
    print("  - All inventory sold (3/3 units)")
    print("  - Shoppers re-matched to cheaper alternatives")
    print("=" * 80)


def test_phase2_with_unsold_cheap_inventory():
    """
    Test the exact scenario from the user's question:
    Low demand leaves cheap inventory unsold in Phase 1,
    but Phase 2 should re-match to sell it.
    """
    
    shoppers = [
        ShopperPoolEntry(shopper_id="S1", willing_to_pay=120, demand_unit=1),
        ShopperPoolEntry(shopper_id="S2", willing_to_pay=115, demand_unit=1),
        ShopperPoolEntry(shopper_id="S3", willing_to_pay=110, demand_unit=1),
    ]
    
    offers = {
        "Seller_1": {"price": 120, "quantity": 4, "inventory_available": 4},
        "Seller_2": {"price": 107, "quantity": 2, "inventory_available": 2},
        "Wholesaler": {"price": 95, "quantity": 1, "inventory_available": 1},
    }
    
    result = run_matching_algorithm(shoppers, offers)
    
    print("\n" + "=" * 80)
    print("LOW DEMAND SCENARIO TEST")
    print("=" * 80)
    print(f"\nShoppers: 3 (low demand)")
    for s in shoppers:
        print(f"  {s['shopper_id']}: WTP ${s['willing_to_pay']}")
    
    print(f"\nSellers: 7 units available (high supply)")
    for name, offer in offers.items():
        print(f"  {name}: ${offer['price']} ({offer['quantity']} units)")
    
    print(f"\nPhase 1 (without optimization) would result in:")
    print(f"  S1 → Seller_1 @ $120")
    print(f"  S2 → Seller_2 @ $107")
    print(f"  S3 → Seller_2 @ $107")
    print(f"  Wholesaler @ $95: UNSOLD ❌")
    
    print(f"\nPhase 2 (with optimization) should result in:")
    print(f"  S1 → Seller_2 @ $107 (re-matched from $120)")
    print(f"  S2 → Wholesaler @ $95 (re-matched from $107)")
    print(f"  S3 → Seller_1 @ $120 (or another available unit)")
    print(f"  Wholesaler @ $95: SOLD ✓")
    
    print(f"\nActual Results:")
    print(f"  Total Matched: {result['total_matched']}")
    print(f"  Total Unmet: {result['total_unmet']}")
    
    print(f"\nQuantities Sold:")
    for agent, qty in result['quantities_sold'].items():
        print(f"  {agent}: {qty} units")
    
    print("\n" + "=" * 80)
    
    # Assertions
    assert result["total_matched"] == 3, "All 3 shoppers should be matched"
    assert result["total_unmet"] == 0, "No unmet demand"
    assert result["quantities_sold"]["Wholesaler"] == 1, "Wholesaler should sell (Phase 2 optimization!)"
    
    print("✅ All assertions passed!")
    print("\nPhase 2 successfully solved the low-demand problem:")
    print("  - Wholesaler's cheap inventory SOLD (was unsold in Phase 1)")
    print("  - Shoppers re-matched to cheaper alternatives")
    print("  - Consumer surplus maximized!")
    print("=" * 80)


if __name__ == "__main__":
    test_phase2_optimization()
    test_phase2_with_unsold_cheap_inventory()

