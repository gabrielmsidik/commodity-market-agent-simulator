"""Agent tools with different information access levels."""

from typing import Dict, List, Any
from src.models import EconomicState, AgentLedger


class WholesalerTools:
    """
    Tools available to the Wholesaler agent.
    Has access to global market data.
    """
    
    def __init__(self, state: EconomicState, agent_name: str = "Wholesaler"):
        self.state = state
        self.agent_name = agent_name
    
    def get_my_inventory(self) -> Dict[str, Any]:
        """Get current inventory level."""
        ledger = self.state["agent_ledgers"][self.agent_name]
        return {
            "inventory": ledger["inventory"],
            "cash": ledger["cash"]
        }
    
    def get_full_market_history(self, days: int = 20) -> Dict[str, Any]:
        """
        Get comprehensive market statistics.
        Only available to Wholesaler.
        """
        market_log = self.state["market_log"]
        recent_trades = market_log[-days * 100:] if len(market_log) > 0 else []
        
        if not recent_trades:
            return {
                "avg_price": None,
                "total_volume": 0,
                "num_trades": 0,
                "price_trend": "unknown"
            }
        
        prices = [trade["price"] for trade in recent_trades]
        volumes = [trade["quantity"] for trade in recent_trades]
        
        return {
            "avg_price": sum(prices) / len(prices) if prices else None,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "total_volume": sum(volumes),
            "num_trades": len(recent_trades),
            "price_trend": self._calculate_trend(prices)
        }
    
    def get_full_market_demand_stats(self) -> Dict[str, Any]:
        """
        Get demand-side statistics.
        Only available to Wholesaler.
        """
        unmet_demand = self.state["unmet_demand_log"]
        recent_unmet = unmet_demand[-100:] if len(unmet_demand) > 0 else []
        
        total_unmet = sum(entry["quantity"] for entry in recent_unmet)
        
        return {
            "recent_unmet_demand": total_unmet,
            "unmet_demand_entries": len(recent_unmet),
            "market_tightness": "tight" if total_unmet > 100 else "balanced"
        }
    
    def get_profit_maximizing_price(self) -> Dict[str, Any]:
        """
        Calculate estimated profit-maximizing price.
        Only available to Wholesaler.
        """
        market_stats = self.get_full_market_history(20)
        demand_stats = self.get_full_market_demand_stats()
        ledger = self.state["agent_ledgers"][self.agent_name]
        
        # Simple heuristic: if we have inventory and market is tight, price higher
        if ledger["inventory"] > 0:
            base_price = market_stats.get("avg_price", 100)
            if base_price is None:
                base_price = 100
            
            if demand_stats["market_tightness"] == "tight":
                recommended_price = int(base_price * 1.1)
            else:
                recommended_price = int(base_price)
        else:
            recommended_price = None
        
        return {
            "recommended_price": recommended_price,
            "confidence": "medium",
            "reasoning": f"Based on avg market price and {demand_stats['market_tightness']} market"
        }
    
    def _calculate_trend(self, prices: List[float]) -> str:
        """Calculate price trend from recent prices."""
        if len(prices) < 2:
            return "unknown"

        first_half = prices[:len(prices)//2]
        second_half = prices[len(prices)//2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second > avg_first * 1.05:
            return "rising"
        elif avg_second < avg_first * 0.95:
            return "falling"
        else:
            return "stable"

    def get_competitor_activity(self) -> Dict[str, Any]:
        """
        Get public information about the other wholesaler's market activity.
        Enables price transparency for collusion research.
        """
        other_wholesaler = "Wholesaler_2" if self.agent_name == "Wholesaler" else "Wholesaler"

        # Get competitor's recent market offers from market_offers_log
        offers_log = self.state.get("market_offers_log", [])
        competitor_offers = [
            offer for offer in offers_log[-10:]
            if offer.get("agent") == other_wholesaler
        ]

        if not competitor_offers:
            return {
                "competitor_name": other_wholesaler,
                "recent_prices": [],
                "recent_quantities": [],
                "avg_price_last_5_days": None,
                "is_active": False
            }

        prices = [o["price"] for o in competitor_offers]
        quantities = [o["quantity"] for o in competitor_offers]

        return {
            "competitor_name": other_wholesaler,
            "recent_prices": prices,
            "recent_quantities": quantities,
            "avg_price_last_5_days": sum(prices[-5:]) / len(prices[-5:]) if prices[-5:] else None,
            "is_active": len(competitor_offers) > 0
        }

    def get_communication_history(self) -> List[Dict[str, Any]]:
        """
        Get history of communications with the other wholesaler.
        Used to reference previous discussions.
        """
        other_wholesaler = "Wholesaler_2" if self.agent_name == "Wholesaler" else "Wholesaler"
        communications = self.state.get("communications_log", [])

        # Get messages between me and the other wholesaler
        relevant_messages = [
            msg for msg in communications
            if (msg["from_agent"] == self.agent_name and msg["to_agent"] == other_wholesaler) or
               (msg["from_agent"] == other_wholesaler and msg["to_agent"] == self.agent_name)
        ]

        return relevant_messages[-10:]  # Last 10 messages


class SellerTools:
    """
    Tools available to Seller agents.
    Only has access to their own private data.
    """
    
    def __init__(self, state: EconomicState, agent_name: str):
        self.state = state
        self.agent_name = agent_name
    
    def get_my_inventory(self) -> Dict[str, Any]:
        """Get current inventory level."""
        ledger = self.state["agent_ledgers"][self.agent_name]
        return {
            "inventory": ledger["inventory"],
            "cash": ledger["cash"]
        }
    
    def calculate_my_sales_stats(self, days: int = 20) -> Dict[str, Any]:
        """
        Calculate statistics from own sales history.
        Only sees own transactions.
        """
        ledger = self.state["agent_ledgers"][self.agent_name]
        sales_log = ledger["private_sales_log"]
        recent_sales = sales_log[-days:] if len(sales_log) > 0 else []
        
        if not recent_sales:
            return {
                "my_avg_sale_price": None,
                "my_total_volume": 0,
                "my_num_sales": 0
            }
        
        prices = [sale["price"] for sale in recent_sales]
        volumes = [sale["quantity"] for sale in recent_sales]
        
        return {
            "my_avg_sale_price": sum(prices) / len(prices) if prices else None,
            "my_total_volume": sum(volumes),
            "my_num_sales": len(recent_sales),
            "my_revenue": sum(p * q for p, q in zip(prices, volumes))
        }

