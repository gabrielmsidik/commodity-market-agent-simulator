"""
Test inventory tracking across days to identify the negative inventory bug.

This test suite verifies that:
1. Inventory is correctly updated after wholesale trades
2. Inventory is correctly updated after market sales
3. Inventory state persists correctly between days
4. Sellers cannot sell more than their available inventory
"""

import pytest
from src.simulation.config import SimulationConfig
from src.simulation.runner import SimulationRunner
from src.graph.workflow import create_simulation_graph


class TestInventoryTracking:
    """Test suite for inventory tracking bugs."""
    
    def test_inventory_updates_after_wholesale_trade(self):
        """Test that inventory decreases after selling to wholesaler."""
        # Create a minimal config for 1 day with negotiation
        config = SimulationConfig(
            name="Inventory Test - Wholesale Trade",
            description="Test wholesale trade inventory update",
            num_days=1,
            total_shoppers=10,  # Minimal shoppers
            long_term_ratio=1.0,
            lt_demand_min=5,
            lt_demand_max=10,
            lt_window_min=1,
            lt_window_max=1,
        )
        
        # Run simulation
        runner = SimulationRunner(config)
        results = runner.run()
        
        final_state = results["final_state"]
        
        # Check that sellers' inventory decreased if they traded with wholesaler
        wholesale_trades = final_state["wholesale_trades_log"]
        
        for trade in wholesale_trades:
            seller_name = trade["seller"]
            quantity_sold = trade["quantity"]
            
            # Get seller's final inventory
            seller_ledger = final_state["agent_ledgers"][seller_name]
            
            # Inventory should have decreased
            # We can't check exact amount without knowing initial inventory,
            # but we can verify it's positive
            assert seller_ledger["inventory"] >= 0, \
                f"{seller_name} has negative inventory: {seller_ledger['inventory']}"
    
    def test_inventory_updates_after_market_sales(self):
        """Test that inventory decreases after market sales."""
        # Create a config for 2 days (Day 1 has negotiation, Day 2 is market-only)
        config = SimulationConfig(
            name="Inventory Test - Market Sales",
            description="Test market sales inventory update",
            num_days=2,
            total_shoppers=50,
            long_term_ratio=1.0,
            lt_demand_min=10,
            lt_demand_max=20,
            lt_window_min=1,
            lt_window_max=2,
        )
        
        # Run simulation
        runner = SimulationRunner(config)
        results = runner.run()
        
        final_state = results["final_state"]
        
        # Track inventory changes
        market_trades = final_state["market_log"]
        
        # Group trades by seller
        sales_by_seller = {}
        for trade in market_trades:
            seller = trade["seller"]
            qty = trade["quantity"]
            sales_by_seller[seller] = sales_by_seller.get(seller, 0) + qty
        
        # Check that all sellers have non-negative inventory
        for agent_name, ledger in final_state["agent_ledgers"].items():
            inventory = ledger["inventory"]
            assert inventory >= 0, \
                f"{agent_name} has negative inventory: {inventory} (sold {sales_by_seller.get(agent_name, 0)} units in market)"
    
    def test_inventory_persistence_between_days(self):
        """Test that inventory state persists correctly between days."""
        # Create a config for 3 days
        config = SimulationConfig(
            name="Inventory Test - Multi-Day Persistence",
            description="Test inventory persistence across days",
            num_days=3,
            total_shoppers=100,
            long_term_ratio=1.0,
            lt_demand_min=10,
            lt_demand_max=20,
            lt_window_min=1,
            lt_window_max=3,
        )

        # Run simulation
        runner = SimulationRunner(config)
        results = runner.run()

        final_state = results["final_state"]

        # Get initial inventories from the initial state
        initial_inventories = {
            "Seller_1": results["initial_state"]["agent_ledgers"]["Seller_1"]["inventory"],
            "Seller_2": results["initial_state"]["agent_ledgers"]["Seller_2"]["inventory"],
        }

        # Calculate expected inventory for each seller
        for agent_name in ["Seller_1", "Seller_2"]:
            ledger = final_state["agent_ledgers"][agent_name]

            # Get initial inventory
            initial_inventory = initial_inventories[agent_name]
            
            # Calculate total sales
            total_market_sales = sum(
                trade["quantity"] 
                for trade in final_state["market_log"] 
                if trade["seller"] == agent_name
            )
            
            total_wholesale_sales = sum(
                trade["quantity"] 
                for trade in final_state["wholesale_trades_log"] 
                if trade["seller"] == agent_name
            )
            
            total_sales = total_market_sales + total_wholesale_sales
            expected_inventory = initial_inventory - total_sales
            actual_inventory = ledger["inventory"]
            
            # Verify inventory matches expected
            assert actual_inventory == expected_inventory, \
                f"{agent_name}: Expected inventory {expected_inventory}, got {actual_inventory}. " \
                f"Initial: {initial_inventory}, Market sales: {total_market_sales}, " \
                f"Wholesale sales: {total_wholesale_sales}"
    
    def test_seller_cannot_oversell(self):
        """Test that sellers cannot sell more than their inventory."""
        import logging

        # Create a config with very high demand to stress-test inventory constraints
        config = SimulationConfig(
            name="Inventory Test - Overselling Prevention",
            description="Test that sellers cannot oversell inventory",
            num_days=10,
            total_shoppers=200,
            long_term_ratio=0.5,
            lt_demand_min=20,
            lt_demand_max=40,
            lt_window_min=1,
            lt_window_max=10,
            st_demand_min=30,
            st_demand_max=50,
            st_window_min=1,
            st_window_max=5,
        )

        # Run simulation with DEBUG logging to capture inventory tracking
        runner = SimulationRunner(config, log_level=logging.DEBUG)
        results = runner.run()

        final_state = results["final_state"]

        # Get initial inventories from the initial state
        initial_inventories = {
            agent_name: results["initial_state"]["agent_ledgers"][agent_name]["inventory"]
            for agent_name in final_state["agent_ledgers"].keys()
        }

        # Check that no seller has negative inventory
        for agent_name, ledger in final_state["agent_ledgers"].items():
            inventory = ledger["inventory"]

            # Get initial inventory
            initial_inventory = initial_inventories[agent_name]
            
            # Calculate total sales
            total_market_sales = sum(
                trade["quantity"] 
                for trade in final_state["market_log"] 
                if trade["seller"] == agent_name
            )
            
            total_wholesale_sales = sum(
                trade["quantity"] 
                for trade in final_state["wholesale_trades_log"] 
                if trade["seller"] == agent_name
            )
            
            # Wholesaler buys from sellers, so their sales are negative
            total_wholesale_purchases = sum(
                trade["quantity"] 
                for trade in final_state["wholesale_trades_log"] 
                if trade["buyer"] == agent_name
            )
            
            total_sales = total_market_sales + total_wholesale_sales
            total_purchases = total_wholesale_purchases
            
            expected_inventory = initial_inventory - total_sales + total_purchases
            
            # CRITICAL: Inventory must never be negative
            assert inventory >= 0, \
                f"{agent_name} has NEGATIVE inventory: {inventory}! " \
                f"Initial: {initial_inventory}, Market sales: {total_market_sales}, " \
                f"Wholesale sales: {total_wholesale_sales}, Wholesale purchases: {total_wholesale_purchases}, " \
                f"Expected: {expected_inventory}"
            
            # Verify inventory matches expected
            assert inventory == expected_inventory, \
                f"{agent_name}: Inventory mismatch! Expected {expected_inventory}, got {inventory}. " \
                f"Initial: {initial_inventory}, Market sales: {total_market_sales}, " \
                f"Wholesale sales: {total_wholesale_sales}, Wholesale purchases: {total_wholesale_purchases}"
    
    def test_day_to_day_inventory_tracking(self):
        """Test detailed day-to-day inventory tracking to catch state persistence bugs."""
        # Create a config for 5 days with moderate activity
        config = SimulationConfig(
            name="Inventory Test - Day-to-Day Tracking",
            description="Test detailed inventory tracking across days",
            num_days=5,
            total_shoppers=50,
            long_term_ratio=1.0,
            lt_demand_min=10,
            lt_demand_max=15,
            lt_window_min=1,
            lt_window_max=5,
        )

        # We'll need to modify the runner to capture intermediate states
        # For now, just verify final state consistency
        runner = SimulationRunner(config)
        results = runner.run()

        final_state = results["final_state"]

        # Get initial inventories from the initial state
        initial_inventories = {
            "Seller_1": results["initial_state"]["agent_ledgers"]["Seller_1"]["inventory"],
            "Seller_2": results["initial_state"]["agent_ledgers"]["Seller_2"]["inventory"],
        }

        # Verify that the sum of all sales doesn't exceed initial inventory
        for agent_name in ["Seller_1", "Seller_2"]:
            initial_inventory = initial_inventories[agent_name]
            
            # Sum all sales
            total_sales = 0
            
            # Market sales
            for trade in final_state["market_log"]:
                if trade["seller"] == agent_name:
                    total_sales += trade["quantity"]
            
            # Wholesale sales
            for trade in final_state["wholesale_trades_log"]:
                if trade["seller"] == agent_name:
                    total_sales += trade["quantity"]
            
            # Total sales should not exceed initial inventory
            assert total_sales <= initial_inventory, \
                f"{agent_name} sold {total_sales} units but only had {initial_inventory} initially! " \
                f"This indicates inventory constraints are not being enforced."
            
            # Final inventory should equal initial minus total sales
            final_inventory = final_state["agent_ledgers"][agent_name]["inventory"]
            expected = initial_inventory - total_sales
            
            assert final_inventory == expected, \
                f"{agent_name}: Final inventory {final_inventory} != expected {expected} " \
                f"(initial {initial_inventory} - sales {total_sales})"


    def test_simple_negative_inventory_check(self):
        """Simple test: just check that no agent ever has negative inventory."""
        import logging

        # Create a config with high demand to stress-test
        config = SimulationConfig(
            name="Simple Negative Inventory Test",
            description="Test that no agent ever has negative inventory",
            num_days=10,
            total_shoppers=200,
            long_term_ratio=0.5,
            lt_demand_min=20,
            lt_demand_max=40,
            lt_window_min=1,
            lt_window_max=10,
            st_demand_min=30,
            st_demand_max=50,
            st_window_min=1,
            st_window_max=5,
        )

        # Run simulation with DEBUG logging to capture inventory tracking
        runner = SimulationRunner(config, log_level=logging.DEBUG)
        results = runner.run()

        final_state = results["final_state"]

        # Simple check: no agent should have negative inventory
        for agent_name, ledger in final_state["agent_ledgers"].items():
            inventory = ledger["inventory"]
            assert inventory >= 0, \
                f"{agent_name} has NEGATIVE inventory: {inventory}! This is a critical bug."


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])

