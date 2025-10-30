"""Shopper database generation."""

import random
from typing import List
from src.models import Shopper
from src.simulation.config import SimulationConfig


def generate_shopper_database(config: SimulationConfig) -> List[Shopper]:
    """
    Generate a database of shoppers based on configuration.

    Args:
        config: Simulation configuration

    Returns:
        List of Shopper objects
    """
    shoppers = []
    num_long_term = int(config.total_shoppers * config.long_term_ratio)
    num_short_term = config.total_shoppers - num_long_term

    # Generate long-term shoppers
    for i in range(num_long_term):
        total_demand = random.randint(config.lt_demand_min, config.lt_demand_max)
        # Ensure window_length doesn't exceed num_days - 1
        max_window = min(config.lt_window_max, config.num_days - 1)
        min_window = min(config.lt_window_min, max_window)
        window_length = random.randint(min_window, max_window)
        # Ensure we have a valid range for window_start
        max_start = max(1, config.num_days - window_length)
        window_start = random.randint(1, max_start)
        window_end = window_start + window_length
        
        base_price = random.uniform(config.lt_base_price_min, config.lt_base_price_max)
        max_price = random.uniform(config.lt_max_price_min, config.lt_max_price_max)
        urgency_factor = random.uniform(config.lt_urgency_min, config.lt_urgency_max)
        
        shopper: Shopper = {
            "shopper_id": f"LT_{i+1:04d}",
            "shopper_type": "long_term",
            "total_demand": total_demand,
            "demand_remaining": total_demand,
            "shopping_window_start": window_start,
            "shopping_window_end": window_end,
            "base_willing_to_pay": base_price,
            "max_willing_to_pay": max_price,
            "urgency_factor": urgency_factor
        }
        shoppers.append(shopper)
    
    # Generate short-term shoppers
    for i in range(num_short_term):
        total_demand = random.randint(config.st_demand_min, config.st_demand_max)
        # Ensure window_length doesn't exceed num_days - 1
        max_window = min(config.st_window_max, config.num_days - 1)
        min_window = min(config.st_window_min, max_window)
        window_length = random.randint(min_window, max_window)
        # Ensure we have a valid range for window_start
        max_start = max(1, config.num_days - window_length)
        window_start = random.randint(1, max_start)
        window_end = window_start + window_length
        
        base_price = random.uniform(config.st_base_price_min, config.st_base_price_max)
        max_price = random.uniform(config.st_max_price_min, config.st_max_price_max)
        urgency_factor = random.uniform(config.st_urgency_min, config.st_urgency_max)
        
        shopper: Shopper = {
            "shopper_id": f"ST_{i+1:04d}",
            "shopper_type": "short_term",
            "total_demand": total_demand,
            "demand_remaining": total_demand,
            "shopping_window_start": window_start,
            "shopping_window_end": window_end,
            "base_willing_to_pay": base_price,
            "max_willing_to_pay": max_price,
            "urgency_factor": urgency_factor
        }
        shoppers.append(shopper)
    
    return shoppers


def calculate_willing_to_pay(shopper: Shopper, current_day: int) -> int:
    """
    Calculate a shopper's current willingness to pay based on urgency curve.
    
    Args:
        shopper: The shopper
        current_day: Current simulation day
        
    Returns:
        Integer price the shopper is willing to pay
    """
    # Calculate time progress through shopping window
    window_length = shopper["shopping_window_end"] - shopper["shopping_window_start"]

    # Handle edge case: if window_length is 0 (instant purchase), use maximum urgency
    if window_length == 0:
        time_progress = 1.0  # Maximum urgency
    else:
        days_elapsed = current_day - shopper["shopping_window_start"]
        time_progress = days_elapsed / window_length

    # Apply urgency curve
    price_range = shopper["max_willing_to_pay"] - shopper["base_willing_to_pay"]
    urgency_curve = time_progress ** shopper["urgency_factor"]
    current_price_float = shopper["base_willing_to_pay"] + (price_range * urgency_curve)
    
    # Round to integer
    return round(current_price_float)

