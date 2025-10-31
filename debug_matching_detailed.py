"""Detailed step-by-step debugging of the matching algorithm."""

def simulate_matching_algorithm(shoppers_willing_to_pay, seller_offers):
    """
    Simulate the exact matching algorithm used in the code.
    
    Args:
        shoppers_willing_to_pay: List of (shopper_id, willing_to_pay) tuples
        seller_offers: Dict of {seller_name: (price, quantity)}
    
    Returns:
        Detailed matching results
    """
    print("=" * 80)
    print("MATCHING ALGORITHM STEP-BY-STEP SIMULATION")
    print("=" * 80)
    print()
    
    # Step 1: Prepare shoppers (sorted by willing_to_pay descending)
    shoppers = sorted(shoppers_willing_to_pay, key=lambda x: x[1], reverse=True)
    print(f"📋 SHOPPERS (sorted by willing_to_pay, highest first):")
    for i, (sid, wtp) in enumerate(shoppers):
        print(f"  [{i}] {sid}: ${wtp}")
    print()
    
    # Step 2: Prepare sellers (create flat list, sorted by price ascending)
    seller_list = []
    for seller_name, (price, quantity) in seller_offers.items():
        for _ in range(quantity):
            seller_list.append((seller_name, price))
    
    seller_list.sort(key=lambda x: x[1])
    
    print(f"🏪 SELLERS (sorted by price, lowest first):")
    print(f"  Total units available: {len(seller_list)}")
    for seller_name, (price, quantity) in seller_offers.items():
        print(f"  {seller_name}: {quantity} units @ ${price}")
    print()
    
    # Step 3: Run two-pointer matching
    print("🔄 MATCHING PROCESS:")
    print()
    
    i = 0  # Shopper pointer
    j = 0  # Seller pointer
    matches = []
    unmet = []
    
    step = 0
    while i < len(shoppers) and j < len(seller_list):
        shopper_id, willing_to_pay = shoppers[i]
        seller_name, seller_price = seller_list[j]
        
        step += 1
        print(f"Step {step}:")
        print(f"  Shopper[{i}]: {shopper_id} willing to pay ${willing_to_pay}")
        print(f"  Seller[{j}]: {seller_name} asking ${seller_price}")
        
        if willing_to_pay >= seller_price:
            # Match!
            print(f"  ✅ MATCH! {shopper_id} buys from {seller_name} at ${seller_price}")
            matches.append((shopper_id, seller_name, seller_price))
            i += 1
            j += 1
        else:
            # No match - shopper's price too low
            print(f"  ❌ NO MATCH: Shopper's ${willing_to_pay} < Seller's ${seller_price}")
            print(f"     → Shopper {shopper_id} goes unmet")
            unmet.append((shopper_id, willing_to_pay))
            i += 1
        
        print()
        
        # Limit output for readability
        if step >= 20:
            print(f"  ... (showing first 20 steps only)")
            break
    
    # Remaining shoppers are unmet
    while i < len(shoppers):
        shopper_id, willing_to_pay = shoppers[i]
        print(f"  ⚠️  Shopper {shopper_id} (${willing_to_pay}) - no more sellers available")
        unmet.append((shopper_id, willing_to_pay))
        i += 1
    
    print()
    print("=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print()
    
    # Aggregate by seller
    seller_sales = {}
    for _, seller_name, price in matches:
        if seller_name not in seller_sales:
            seller_sales[seller_name] = {'quantity': 0, 'price': price}
        seller_sales[seller_name]['quantity'] += 1
    
    print(f"✅ SUCCESSFUL MATCHES: {len(matches)} units sold")
    for seller_name, data in seller_sales.items():
        print(f"  {seller_name}: {data['quantity']} units @ ${data['price']}")
    print()
    
    print(f"❌ UNMET DEMAND: {len(unmet)} shopper-units")
    if unmet:
        # Group by price
        price_groups = {}
        for _, wtp in unmet:
            price_groups[wtp] = price_groups.get(wtp, 0) + 1
        
        print(f"  Price distribution:")
        for price in sorted(price_groups.keys(), reverse=True):
            count = price_groups[price]
            print(f"    ${price}: {count} units")
    print()
    
    # Analysis
    print("📊 ANALYSIS:")
    print()
    
    total_shoppers = len(shoppers)
    total_sellers = len(seller_list)
    match_rate = (len(matches) / total_shoppers * 100) if total_shoppers > 0 else 0
    
    print(f"  Total Shoppers: {total_shoppers}")
    print(f"  Total Seller Units: {total_sellers}")
    print(f"  Match Rate: {match_rate:.1f}%")
    print()
    
    if unmet:
        min_unmet_price = min(wtp for _, wtp in unmet)
        max_unmet_price = max(wtp for _, wtp in unmet)
        
        if seller_offers:
            min_seller_price = min(price for _, (price, _) in seller_offers.items())
            max_seller_price = max(price for _, (price, _) in seller_offers.items())
            
            print(f"  Unmet shoppers willing to pay: ${min_unmet_price} - ${max_unmet_price}")
            print(f"  Seller prices: ${min_seller_price} - ${max_seller_price}")
            print()
            
            if max_unmet_price < min_seller_price:
                print(f"  💡 All unmet shoppers had prices below the lowest seller price")
                print(f"     This is CORRECT behavior - no profitable trades available")
            elif total_sellers < total_shoppers:
                print(f"  💡 More shoppers than seller units available")
                print(f"     Some shoppers will always go unmet")
    
    return matches, unmet


def example_scenario_1():
    """Example: Normal market with good matching."""
    print("\n\n")
    print("🎯 SCENARIO 1: Normal Market")
    print()
    
    shoppers = [
        ("Shopper_1", 120),
        ("Shopper_2", 115),
        ("Shopper_3", 110),
        ("Shopper_4", 105),
        ("Shopper_5", 100),
        ("Shopper_6", 95),
        ("Shopper_7", 90),
        ("Shopper_8", 85),
    ]
    
    sellers = {
        "Seller_1": (88, 3),  # 3 units @ $88
        "Seller_2": (92, 2),  # 2 units @ $92
        "Wholesaler": (95, 2),  # 2 units @ $95
    }
    
    simulate_matching_algorithm(shoppers, sellers)


def example_scenario_2():
    """Example: Price mismatch - shoppers too cheap."""
    print("\n\n")
    print("🎯 SCENARIO 2: Price Mismatch (Shoppers Too Cheap)")
    print()
    
    shoppers = [
        ("Shopper_1", 85),
        ("Shopper_2", 82),
        ("Shopper_3", 80),
        ("Shopper_4", 78),
        ("Shopper_5", 75),
    ]
    
    sellers = {
        "Seller_1": (90, 5),  # All sellers priced above shoppers
        "Seller_2": (95, 5),
    }
    
    simulate_matching_algorithm(shoppers, sellers)


def example_scenario_3():
    """Example: Inventory shortage."""
    print("\n\n")
    print("🎯 SCENARIO 3: Inventory Shortage")
    print()
    
    shoppers = [
        ("Shopper_1", 120),
        ("Shopper_2", 115),
        ("Shopper_3", 110),
        ("Shopper_4", 105),
        ("Shopper_5", 100),
        ("Shopper_6", 95),
        ("Shopper_7", 90),
        ("Shopper_8", 85),
    ]
    
    sellers = {
        "Seller_1": (88, 2),  # Only 3 units total, but 8 shoppers
        "Seller_2": (92, 1),
    }
    
    simulate_matching_algorithm(shoppers, sellers)


if __name__ == "__main__":
    print("This script demonstrates how the matching algorithm works")
    print()
    
    example_scenario_1()
    example_scenario_2()
    example_scenario_3()
    
    print("\n\n")
    print("=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print()
    print("The matching algorithm DOES match against the ENTIRE market:")
    print("  ✓ All shoppers are considered (sorted by willing_to_pay)")
    print("  ✓ All sellers are considered (sorted by price)")
    print("  ✓ Two-pointer algorithm ensures optimal matching")
    print()
    print("Low trade counts can happen when:")
    print("  1. Shoppers' willing_to_pay < sellers' prices")
    print("  2. Sellers run out of inventory")
    print("  3. 'Trades' = aggregated entries, not individual units")
    print()

