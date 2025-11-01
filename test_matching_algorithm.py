"""Unit tests for the market matching algorithm."""

import pytest
from typing import List, Dict, Any
from src.models.state import EconomicState, ShopperPoolEntry


def run_matching_algorithm(shoppers: List[ShopperPoolEntry], offers: Dict[str, Dict[str, Any]], day: int = 1) -> Dict[str, Any]:
    """
    Isolated version of the matching algorithm for testing.
    This is the exact same logic as in src/graph/nodes.py:run_market_simulation

    Two-phase algorithm:
    Phase 1: Priority matching - highest WTP shops first, buys most expensive they can afford
    Phase 2: Price optimization - if all demand met, re-match to cheaper alternatives
    """
    # Create flat list of seller offers sorted by price (descending - most expensive first)
    seller_list = []
    for agent_name, offer in offers.items():
        if offer["quantity"] > 0 and offer.get("inventory_available", offer["quantity"]) > 0:
            for i in range(offer["quantity"]):
                seller_list.append({
                    "agent_name": agent_name,
                    "price": offer["price"],
                    "unit": 1,
                    "seller_unit_id": f"{agent_name}_{i}"
                })

    seller_list.sort(key=lambda x: x["price"], reverse=True)

    # PHASE 1: Priority matching
    unmet_demand = []
    shopper_assignments = {}
    available_sellers = list(range(len(seller_list)))

    for shopper in shoppers:
        matched = False

        # Find the most expensive seller this shopper can afford
        for idx in available_sellers:
            seller = seller_list[idx]

            if shopper["willing_to_pay"] >= seller["price"]:
                # Match!
                shopper_assignments[shopper["shopper_id"]] = {
                    "seller_unit_id": seller["seller_unit_id"],
                    "seller_idx": idx,
                    "agent_name": seller["agent_name"],
                    "price": seller["price"],
                    "willing_to_pay": shopper["willing_to_pay"]
                }

                available_sellers.remove(idx)
                matched = True
                break

        if not matched:
            unmet_demand.append({
                "shopper_id": shopper["shopper_id"],
                "willing_to_pay": shopper["willing_to_pay"]
            })

    # PHASE 2: Price optimization - re-match to cheaper alternatives if there are matched shoppers and unsold inventory
    # This runs even if some demand is unmet (e.g., lowball shoppers who can't afford anything)
    if len(shopper_assignments) > 0 and len(available_sellers) > 0:
        # Sort available sellers by price (cheapest first)
        available_sellers_sorted = sorted(available_sellers, key=lambda idx: seller_list[idx]["price"])

        # Sort matched shoppers by current price (most expensive first)
        matched_shoppers = sorted(
            shopper_assignments.items(),
            key=lambda x: x[1]["price"],
            reverse=True
        )

        # Try to re-match shoppers from expensive to cheap sellers
        for shopper_id, current_assignment in matched_shoppers:
            if not available_sellers_sorted:
                break

            cheapest_idx = available_sellers_sorted[0]
            cheapest_seller = seller_list[cheapest_idx]

            # Can afford and is cheaper?
            if (current_assignment["willing_to_pay"] >= cheapest_seller["price"] and
                cheapest_seller["price"] < current_assignment["price"]):

                # Re-match!
                old_seller_idx = current_assignment["seller_idx"]

                shopper_assignments[shopper_id] = {
                    "seller_unit_id": cheapest_seller["seller_unit_id"],
                    "seller_idx": cheapest_idx,
                    "agent_name": cheapest_seller["agent_name"],
                    "price": cheapest_seller["price"],
                    "willing_to_pay": current_assignment["willing_to_pay"]
                }

                # Free up old seller, remove new seller
                available_sellers_sorted.append(old_seller_idx)
                available_sellers_sorted.sort(key=lambda idx: seller_list[idx]["price"])
                available_sellers_sorted.pop(0)

    # Calculate final quantities
    quantities_sold = {agent: 0 for agent in offers.keys()}
    shopper_purchases = {}

    for shopper_id, assignment in shopper_assignments.items():
        quantities_sold[assignment["agent_name"]] += 1

        if shopper_id not in shopper_purchases:
            shopper_purchases[shopper_id] = 0
        shopper_purchases[shopper_id] += 1
    
    return {
        "quantities_sold": quantities_sold,
        "shopper_purchases": shopper_purchases,
        "unmet_demand": unmet_demand,
        "total_matched": sum(quantities_sold.values()),
        "total_unmet": len(unmet_demand)
    }



class TestMatchingAlgorithm:
    """Test suite for the market matching algorithm."""

    def expand_shoppers(self, shoppers: List[Dict[str, Any]]) -> List[ShopperPoolEntry]:
        """Expand shoppers into pool entries with unique IDs and sort by willing_to_pay (descending - highest first)."""
        expanded = []
        for shopper in shoppers:
            for unit_idx in range(shopper["demand_unit"]):
                expanded.append(ShopperPoolEntry(
                    shopper_id=f"{shopper['shopper_id']}_unit{unit_idx}",  # Unique ID per unit
                    original_shopper_id=shopper["shopper_id"],  # Track original
                    willing_to_pay=shopper["willing_to_pay"],
                    demand_unit=1
                ))
        # Sort by willing_to_pay descending (highest shops first)
        expanded.sort(key=lambda x: x["willing_to_pay"], reverse=True)
        return expanded

    def test_matching_algorithm_with_mix(self):
        shoppers = [
            {"shopper_id": "S1", "willing_to_pay": 120, "demand_unit": 2},
            {"shopper_id": "S2", "willing_to_pay": 115, "demand_unit": 2},
            {"shopper_id": "S3", "willing_to_pay": 110, "demand_unit": 2},
            {"shopper_id": "S4", "willing_to_pay": 105, "demand_unit": 2},
            {"shopper_id": "S5", "willing_to_pay": 100, "demand_unit": 2},
        ]

        offers = {
            "Seller_1": {"price": 120, "quantity": 4, "inventory_available": 4},
            "Seller_2": {"price": 107, "quantity": 2, "inventory_available": 2},
            "Wholesaler": {"price": 95, "quantity": 1, "inventory_available": 1},
        }

        result = run_matching_algorithm(self.expand_shoppers(shoppers), offers)
        
        print(result)

        assert result["total_matched"] == 5
        assert result["total_unmet"] == 5
        assert result["quantities_sold"]["Seller_1"] == 2
        assert result["quantities_sold"]["Seller_2"] == 2
        assert result["quantities_sold"]["Wholesaler"] == 1
    
    def test_perfect_match_all_shoppers_buy(self):
        """Test case where all shoppers can afford and all get matched."""
        # Setup: 5 shoppers, 5 units available
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
        
        result = run_matching_algorithm(shoppers, offers)
        
        # All shoppers should buy
        assert result["total_matched"] == 5
        assert result["total_unmet"] == 0
        
        # Seller_1 (cheapest) should sell all 3 units
        assert result["quantities_sold"]["Seller_1"] == 3
        # Seller_2 should sell all 2 units
        assert result["quantities_sold"]["Seller_2"] == 2
        # Wholesaler should sell nothing (no inventory)
        assert result["quantities_sold"]["Wholesaler"] == 0
        
        print("✓ Test 1 passed: Perfect match - all shoppers buy")
    
    
    def test_price_mismatch_no_trades(self):
        """Test case where all shoppers' prices are too low."""
        shoppers = [
            {"shopper_id": "S1", "willing_to_pay": 85, "demand_unit": 1},
            {"shopper_id": "S2", "willing_to_pay": 82, "demand_unit": 1},
            {"shopper_id": "S3", "willing_to_pay": 80, "demand_unit": 1},
        ]
        
        offers = {
            "Seller_1": {"price": 90, "quantity": 5, "inventory_available": 5},
            "Seller_2": {"price": 95, "quantity": 5, "inventory_available": 5},
            "Wholesaler": {"price": 100, "quantity": 5, "inventory_available": 5},
        }
        
        result = run_matching_algorithm(shoppers, offers)
        
        # No shoppers should buy
        assert result["total_matched"] == 0
        assert result["total_unmet"] == 3
        
        # No sellers should sell anything
        assert result["quantities_sold"]["Seller_1"] == 0
        assert result["quantities_sold"]["Seller_2"] == 0
        assert result["quantities_sold"]["Wholesaler"] == 0
        
        print("✓ Test 2 passed: Price mismatch - no trades")
    
    
    def test_partial_match_inventory_shortage(self):
        """Test case where there's not enough inventory for all shoppers."""
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
        
        result = run_matching_algorithm(shoppers, offers)
        
        # Only 3 units available, so only 3 shoppers buy
        assert result["total_matched"] == 3
        assert result["total_unmet"] == 5
        

        # Highest-paying shoppers should get matched first
        assert "S1" in result["shopper_purchases"]
        assert "S2" in result["shopper_purchases"]
        assert "S3" in result["shopper_purchases"]
        
        # Lower-paying shoppers should be unmet
        assert "S6" not in result["shopper_purchases"]
        assert "S7" not in result["shopper_purchases"]
        assert "S8" not in result["shopper_purchases"]
        
        print("Test 3 passed: Partial match - inventory shortage")
    
    
    def test_partial_match_some_shoppers_too_cheap(self):
        """Test case where some shoppers can afford, others can't."""
        shoppers = [
            {"shopper_id": "S1", "willing_to_pay": 120, "demand_unit": 1},
            {"shopper_id": "S2", "willing_to_pay": 115, "demand_unit": 1},
            {"shopper_id": "S3", "willing_to_pay": 110, "demand_unit": 1},
            {"shopper_id": "S4", "willing_to_pay": 85, "demand_unit": 1},  # Too cheap
            {"shopper_id": "S5", "willing_to_pay": 80, "demand_unit": 1},  # Too cheap
        ]
        
        offers = {
            "Seller_1": {"price": 88, "quantity": 5, "inventory_available": 5},
            "Seller_2": {"price": 92, "quantity": 5, "inventory_available": 5},
            "Wholesaler": {"price": 95, "quantity": 5, "inventory_available": 5},
        }
        
        result = run_matching_algorithm(shoppers, offers)
        
        # Only 3 shoppers can afford
        assert result["total_matched"] == 3
        assert result["total_unmet"] == 2
        
        # High-paying shoppers should buy
        assert "S1" in result["shopper_purchases"]
        assert "S2" in result["shopper_purchases"]
        assert "S3" in result["shopper_purchases"]
        
        # Low-paying shoppers should be unmet
        assert "S4" not in result["shopper_purchases"]
        assert "S5" not in result["shopper_purchases"]
        
        print("✓ Test 4 passed: Partial match - some shoppers too cheap")
    
    
    def test_price_priority_cheapest_seller_first(self):
        """Test that cheapest seller sells first."""
        shoppers = [
            {"shopper_id": "S1", "willing_to_pay": 100, "demand_unit": 1},
            {"shopper_id": "S2", "willing_to_pay": 100, "demand_unit": 1},
            {"shopper_id": "S3", "willing_to_pay": 100, "demand_unit": 1},
        ]
        
        offers = {
            "Seller_1": {"price": 70, "quantity": 1, "inventory_available": 1},  # Cheapest
            "Seller_2": {"price": 80, "quantity": 1, "inventory_available": 1},  # Middle
            "Wholesaler": {"price": 90, "quantity": 1, "inventory_available": 1},  # Most expensive
        }
        
        result = run_matching_algorithm(shoppers, offers)
        
        # All should sell
        assert result["total_matched"] == 3
        
        # Each seller should sell exactly 1 unit
        assert result["quantities_sold"]["Seller_1"] == 1
        assert result["quantities_sold"]["Seller_2"] == 1
        assert result["quantities_sold"]["Wholesaler"] == 1
        
        print("✓ Test 5 passed: Cheapest seller sells first")
    
    
    def test_realistic_scenario(self):
        """Test a realistic scenario with mixed prices and quantities.

        With Phase 2 optimization, shoppers are re-matched to cheaper alternatives,
        so the cheapest seller (Seller_1) should sell out first.
        """
        # Create explicit shoppers to know exact expected behavior
        shoppers = []

        # 30 high-value shoppers (all willing to pay >= $110)
        for i in range(30):
            shoppers.append({
                "shopper_id": f"HIGH_{i}",
                "willing_to_pay": 110 + i,  # $110-$139
                "demand_unit": 1
            })

        # 40 medium-value shoppers (willing to pay $88-$107)
        for i in range(40):
            shoppers.append({
                "shopper_id": f"MED_{i}",
                "willing_to_pay": 88 + i // 2,  # $88-$107
                "demand_unit": 1
            })

        # 30 low-value shoppers (willing to pay $70-$87, all below $88)
        for i in range(30):
            shoppers.append({
                "shopper_id": f"LOW_{i}",
                "willing_to_pay": 70 + i // 2,  # $70-$84
                "demand_unit": 1
            })

        # Sellers with realistic pricing
        offers = {
            "Seller_1": {"price": 88, "quantity": 50, "inventory_available": 100},  # Cheapest seller
            "Seller_2": {"price": 95, "quantity": 30, "inventory_available": 50},   # Most expensive seller
            "Wholesaler": {"price": 92, "quantity": 20, "inventory_available": 50}, # Medium price
        }

        result = run_matching_algorithm(shoppers, offers)

        assert result["total_matched"] == 70, f"Expected 70 matches, got {result['total_matched']}"
        assert result["total_unmet"] == 30, f"Expected 30 unmet, got {result['total_unmet']}"

        # With Phase 2 optimization:
        # - Seller_1 (cheapest @ $88) should sell all 50 units (Phase 2 re-matches shoppers here)
        # - Wholesaler (@ $92) should sell all 20 units
        # - Seller_2 (most expensive @ $95) should sell 0 units (shoppers re-matched to cheaper alternatives)
        assert result["quantities_sold"]["Seller_1"] == 50, f"Expected Seller_1 to sell 50, got {result['quantities_sold']['Seller_1']}"
        assert result["quantities_sold"]["Wholesaler"] == 20, f"Expected Wholesaler to sell 20, got {result['quantities_sold']['Wholesaler']}"
        assert result["quantities_sold"]["Seller_2"] == 0, f"Expected Seller_2 to sell 0, got {result['quantities_sold']['Seller_2']}"

        print("✓ Test 6 passed: Realistic scenario with 100 shoppers (Phase 2 optimization)")
        print(f"  - Matched: {result['total_matched']} shoppers")
        print(f"  - Unmet: {result['total_unmet']} shoppers")
        print(f"  - Seller_1 sold: {result['quantities_sold']['Seller_1']} units @ $88 (cheapest - sold out!)")
        print(f"  - Wholesaler sold: {result['quantities_sold']['Wholesaler']} units @ $92")
        print(f"  - Seller_2 sold: {result['quantities_sold']['Seller_2']} units @ $95 (too expensive - unsold)")
    
    
    def test_edge_case_exact_price_match(self):
        """Test edge case where shopper's willing_to_pay exactly equals seller's price."""
        shoppers = [
            {"shopper_id": "S1", "willing_to_pay": 90, "demand_unit": 1},
        ]
        
        offers = {
            "Seller_1": {"price": 90, "quantity": 1, "inventory_available": 1},
            "Seller_2": {"price": 95, "quantity": 1, "inventory_available": 1},
            "Wholesaler": {"price": 100, "quantity": 1, "inventory_available": 1},
        }
        
        result = run_matching_algorithm(shoppers, offers)
        
        # Should match (>= condition)
        assert result["total_matched"] == 1
        assert result["quantities_sold"]["Seller_1"] == 1
        
        print("✓ Test 7 passed: Exact price match works (>= condition)")


def run_all_tests():
    """Run all tests and print results."""
    print("=" * 80)
    print("MATCHING ALGORITHM UNIT TESTS")
    print("=" * 80)
    print()
    
    test_suite = TestMatchingAlgorithm()
    
    tests = [
        ("Perfect Match", test_suite.test_perfect_match_all_shoppers_buy),
        ("Price Mismatch", test_suite.test_price_mismatch_no_trades),
        ("Inventory Shortage", test_suite.test_partial_match_inventory_shortage),
        ("Some Shoppers Too Cheap", test_suite.test_partial_match_some_shoppers_too_cheap),
        ("Price Priority", test_suite.test_price_priority_cheapest_seller_first),
        ("Realistic Scenario", test_suite.test_realistic_scenario),
        ("Exact Price Match", test_suite.test_edge_case_exact_price_match),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test_name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test_name}")
            print(f"  Error: {e}")
            failed += 1
    
    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

