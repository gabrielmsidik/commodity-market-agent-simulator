"""Database models for storing simulation results."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Simulation(Base):
    """Stores simulation run data."""
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    # Configuration (JSON)
    config_json = Column(Text, nullable=False)
    
    # Results (JSON)
    final_state_json = Column(Text, nullable=False)
    summary_json = Column(Text, nullable=False)
    
    # Summary statistics (for quick querying)
    total_trades = Column(Integer, nullable=True)
    total_volume = Column(Integer, nullable=True)
    average_price = Column(Float, nullable=True)
    total_unmet_demand = Column(Integer, nullable=True)
    
    wholesaler_profit = Column(Float, nullable=True)
    seller1_profit = Column(Float, nullable=True)
    seller2_profit = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<Simulation(id={self.id}, name='{self.name}', created_at='{self.created_at}')>"

