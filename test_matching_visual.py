"""Visual test to demonstrate the matching algorithm with detailed output."""

from test_matching_algorithm import run_matching_algorithm


def visualize_matching(test_name, shoppers, offers):
    """Run matching and show detailed visualization."""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)
    print()
    
    # Show inputs
    print("📋 SHOPPERS:")
    print(f"   Total: {len(shoppers)} shopper-units")
    
    # Group shoppers by price
    price_groups = {}
    for s in shoppers:
        wtp = s["willing_to_pay"]
        if wtp not in price_groups:
            price_groups[wtp] = []
        price_groups[wtp].append(s["shopper_id"])
    
    for price in sorted(price_groups.keys(), reverse=True):
        count = len(price_groups[price])
        print(f"   ${price:3d}: {count:3d} shoppers")
    print()
    
    print("🏪 SELLERS:")
    total_inventory = 0
    for seller_name, offer in sorted(offers.items(), key=lambda x: x[1]["price"]):
        qty = offer["quantity"]
        price = offer["price"]
        total_inventory += qty
        print(f"   {seller_name:12s}: {qty:3d} units @ ${price:3d}")
    print(f"   {'TOTAL':12s}: {total_inventory:3d} units")
    print()
    
    # Run matching
    result = run_matching_algorithm(shoppers, offers)
    
    # Show results
    print("✅ MATCHES:")
    total_matched = result["total_matched"]
    if total_matched > 0:
        for seller_name in sorted(offers.keys(), key=lambda x: offers[x]["price"]):
            qty = result["quantities_sold"][seller_name]
            if qty > 0:
                price = offers[seller_name]["price"]
                revenue = qty * price
                print(f"   {seller_name:12s}: {qty:3d} units @ ${price:3d} = ${revenue:6d} revenue")
        print(f"   {'TOTAL':12s}: {total_matched:3d} units")
    else:
        print("   (none)")
    print()
    
    print("❌ UNMET DEMAND:")
    total_unmet = result["total_unmet"]
    if total_unmet > 0:
        # Group unmet by price
        unmet_price_groups = {}
        for u in result["unmet_demand"]:
            wtp = u["willing_to_pay"]
            unmet_price_groups[wtp] = unmet_price_groups.get(wtp, 0) + 1
        
        for price in sorted(unmet_price_groups.keys(), reverse=True):
            count = unmet_price_groups[price]
            print(f"   ${price:3d}: {count:3d} shoppers couldn't buy")
        print(f"   {'TOTAL':12s}: {total_unmet:3d} shoppers")
    else:
        print("   (none)")
    print()
    
    # Analysis
    print("📊 ANALYSIS:")
    match_rate = (total_matched / len(shoppers) * 100) if len(shoppers) > 0 else 0
    print(f"   Match Rate: {match_rate:.1f}% ({total_matched}/{len(shoppers)})")
    
    if total_unmet > 0:
        min_seller_price = min(o["price"] for o in offers.values() if o["quantity"] > 0)
        unmet_prices = [u["willing_to_pay"] for u in result["unmet_demand"]]
        max_unmet_price = max(unmet_prices)
        min_unmet_price = min(unmet_prices)
        
        print(f"   Lowest seller price: ${min_seller_price}")
        print(f"   Unmet shoppers WTP range: ${min_unmet_price}-${max_unmet_price}")
        
        if max_unmet_price < min_seller_price:
            print(f"   → All unmet shoppers priced below market (CORRECT)")
        elif total_matched == total_inventory:
            print(f"   → Inventory exhausted before all shoppers satisfied (CORRECT)")
    
    print()


def test_scenario_1_perfect_market():
    """Scenario 1: Perfect market - all shoppers can afford, enough inventory."""
    shoppers = [
        {"shopper_id": "S1", "willing_to_pay": 120, "demand_unit": 1},
        {"shopper_id": "S2", "willing_to_pay": 115, "demand_unit": 1},
        {"shopper_id": "S3", "willing_to_pay": 110, "demand_unit": 1},
        {"shopper_id": "S4", "willing_to_pay": 105, "demand_unit": 1},
        {"shopper_id": "S5", "willing_to_pay": 100, "demand_unit": 1},
    ]
    
    offers = {
        "Seller_1": {"price": 88, "quantity": 3, "inventory_available": 3},
        "Seller_2": {"price": 92, "quantity": 2, "inventory_available": 2},
        "Wholesaler": {"price": 95, "quantity": 0, "inventory_available": 0},
    }
    
    visualize_matching("Perfect Market - All Shoppers Buy", shoppers, offers)


def test_scenario_2_price_too_high():
    """Scenario 2: Sellers price too high - no trades."""
    shoppers = [
        {"shopper_id": "S1", "willing_to_pay": 85, "demand_unit": 1},
        {"shopper_id": "S2", "willing_to_pay": 82, "demand_unit": 1},
        {"shopper_id": "S3", "willing_to_pay": 80, "demand_unit": 1},
        {"shopper_id": "S4", "willing_to_pay": 78, "demand_unit": 1},
        {"shopper_id": "S5", "willing_to_pay": 75, "demand_unit": 1},
    ]
    
    offers = {
        "Seller_1": {"price": 90, "quantity": 10, "inventory_available": 10},
        "Seller_2": {"price": 95, "quantity": 10, "inventory_available": 10},
        "Wholesaler": {"price": 100, "quantity": 10, "inventory_available": 10},
    }
    
    visualize_matching("Price Mismatch - Sellers Too Expensive", shoppers, offers)


def test_scenario_3_inventory_shortage():
    """Scenario 3: Not enough inventory - highest payers win."""
    shoppers = [
        {"shopper_id": "S1", "willing_to_pay": 120, "demand_unit": 1},
        {"shopper_id": "S2", "willing_to_pay": 115, "demand_unit": 1},
        {"shopper_id": "S3", "willing_to_pay": 110, "demand_unit": 1},
        {"shopper_id": "S4", "willing_to_pay": 105, "demand_unit": 1},
        {"shopper_id": "S5", "willing_to_pay": 100, "demand_unit": 1},
        {"shopper_id": "S6", "willing_to_pay": 95, "demand_unit": 1},
        {"shopper_id": "S7", "willing_to_pay": 90, "demand_unit": 1},
        {"shopper_id": "S8", "willing_to_pay": 85, "demand_unit": 1},
    ]
    
    offers = {
        "Seller_1": {"price": 88, "quantity": 2, "inventory_available": 2},
        "Seller_2": {"price": 92, "quantity": 1, "inventory_available": 1},
        "Wholesaler": {"price": 95, "quantity": 0, "inventory_available": 0},
    }
    
    visualize_matching("Inventory Shortage - Only 3 Units Available", shoppers, offers)


def test_scenario_4_mixed_market():
    """Scenario 4: Mixed market - some buy, some don't."""
    shoppers = [
        {"shopper_id": "S1", "willing_to_pay": 120, "demand_unit": 1},
        {"shopper_id": "S2", "willing_to_pay": 115, "demand_unit": 1},
        {"shopper_id": "S3", "willing_to_pay": 110, "demand_unit": 1},
        {"shopper_id": "S4", "willing_to_pay": 85, "demand_unit": 1},  # Too cheap
        {"shopper_id": "S5", "willing_to_pay": 80, "demand_unit": 1},  # Too cheap
        {"shopper_id": "S6", "willing_to_pay": 75, "demand_unit": 1},  # Too cheap
    ]
    
    offers = {
        "Seller_1": {"price": 88, "quantity": 5, "inventory_available": 5},
        "Seller_2": {"price": 92, "quantity": 5, "inventory_available": 5},
        "Wholesaler": {"price": 95, "quantity": 5, "inventory_available": 5},
    }
    
    visualize_matching("Mixed Market - Some Shoppers Too Cheap", shoppers, offers)


def test_scenario_5_realistic_100_shoppers():
    """Scenario 5: Realistic scenario with 100 shoppers."""
    shoppers = []
    
    # 30 high-value shoppers ($110-$139)
    for i in range(30):
        shoppers.append({
            "shopper_id": f"HIGH_{i:02d}",
            "willing_to_pay": 110 + i,
            "demand_unit": 1
        })
    
    # 40 medium-value shoppers ($88-$107)
    for i in range(40):
        shoppers.append({
            "shopper_id": f"MED_{i:02d}",
            "willing_to_pay": 88 + i // 2,
            "demand_unit": 1
        })
    
    # 30 low-value shoppers ($70-$84)
    for i in range(30):
        shoppers.append({
            "shopper_id": f"LOW_{i:02d}",
            "willing_to_pay": 70 + i // 2,
            "demand_unit": 1
        })
    
    offers = {
        "Seller_1": {"price": 88, "quantity": 50, "inventory_available": 100},
        "Seller_2": {"price": 95, "quantity": 30, "inventory_available": 50},
        "Wholesaler": {"price": 92, "quantity": 20, "inventory_available": 50},
    }
    
    visualize_matching("Realistic Market - 100 Shoppers, 3 Sellers", shoppers, offers)


def main():
    """Run all visual tests."""
    print("=" * 80)
    print("MATCHING ALGORITHM VISUAL TESTS")
    print("=" * 80)
    print()
    print("This demonstrates how the matching algorithm works with explicit inputs.")
    print("Each test shows:")
    print("  - Input: Shoppers (by willing_to_pay) and Sellers (by price)")
    print("  - Output: Who matched, who didn't, and why")
    print()
    
    test_scenario_1_perfect_market()
    test_scenario_2_price_too_high()
    test_scenario_3_inventory_shortage()
    test_scenario_4_mixed_market()
    test_scenario_5_realistic_100_shoppers()
    
    print("=" * 80)
    print("KEY TAKEAWAYS:")
    print("=" * 80)
    print()
    print("1. The algorithm DOES match against ALL shoppers and ALL sellers")
    print("2. Shoppers are sorted by willing_to_pay (highest first)")
    print("3. Sellers are sorted by price (lowest first)")
    print("4. Two-pointer algorithm ensures optimal matching")
    print("5. Shoppers don't buy when:")
    print("   - Their willing_to_pay < seller's price")
    print("   - All inventory is exhausted")
    print()
    print("6. 'Number of trades' in logs = aggregated entries (one per seller)")
    print("   'Total volume' = actual units sold")
    print()


if __name__ == "__main__":
    main()

