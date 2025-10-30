"""Database operations for simulations."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from src.database.models import Base, Simulation
from src.config import get_config


# Create engine and session
def get_engine():
    """Get database engine."""
    config = get_config()
    return create_engine(config.database_url)


def get_session() -> Session:
    """Get database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def save_simulation(results: Dict[str, Any]) -> int:
    """
    Save simulation results to database.
    
    Args:
        results: Simulation results dictionary
        
    Returns:
        Simulation ID
    """
    session = get_session()
    
    try:
        config = results["config"]
        summary = results["summary"]
        
        simulation = Simulation(
            name=config.get("name"),
            description=config.get("description"),
            start_time=datetime.fromisoformat(results["start_time"]),
            end_time=datetime.fromisoformat(results["end_time"]),
            duration_seconds=results["duration_seconds"],
            config_json=json.dumps(config),
            final_state_json=json.dumps(results["final_state"], default=str),
            summary_json=json.dumps(summary),
            total_trades=summary.get("total_trades"),
            total_volume=summary.get("total_volume"),
            average_price=summary.get("average_price"),
            total_unmet_demand=summary.get("total_unmet_demand"),
            wholesaler_profit=summary["agent_performance"]["Wholesaler"]["profit"],
            seller1_profit=summary["agent_performance"]["Seller_1"]["profit"],
            seller2_profit=summary["agent_performance"]["Seller_2"]["profit"]
        )
        
        session.add(simulation)
        session.commit()
        
        sim_id = simulation.id
        session.close()
        
        return sim_id
    
    except Exception as e:
        session.rollback()
        session.close()
        raise e


def get_simulation(simulation_id: int) -> Optional[Dict[str, Any]]:
    """
    Get simulation by ID.
    
    Args:
        simulation_id: Simulation ID
        
    Returns:
        Simulation data or None if not found
    """
    session = get_session()
    
    try:
        simulation = session.query(Simulation).filter(Simulation.id == simulation_id).first()
        
        if not simulation:
            return None
        
        result = {
            "id": simulation.id,
            "name": simulation.name,
            "description": simulation.description,
            "created_at": simulation.created_at.isoformat(),
            "start_time": simulation.start_time.isoformat(),
            "end_time": simulation.end_time.isoformat(),
            "duration_seconds": simulation.duration_seconds,
            "config": json.loads(simulation.config_json),
            "final_state": json.loads(simulation.final_state_json),
            "summary": json.loads(simulation.summary_json)
        }
        
        session.close()
        return result
    
    except Exception as e:
        session.close()
        raise e


def list_simulations(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List simulations with pagination.
    
    Args:
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of simulation summaries
    """
    session = get_session()
    
    try:
        simulations = (
            session.query(Simulation)
            .order_by(desc(Simulation.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        results = []
        for sim in simulations:
            config = json.loads(sim.config_json)
            results.append({
                "id": sim.id,
                "name": sim.name,
                "description": sim.description,
                "created_at": sim.created_at.isoformat(),
                "num_days": config.get("num_days", "N/A"),
                "duration_seconds": sim.duration_seconds,
                "total_trades": sim.total_trades,
                "total_volume": sim.total_volume,
                "average_price": sim.average_price,
                "total_unmet_demand": sim.total_unmet_demand,
                "wholesaler_profit": sim.wholesaler_profit,
                "seller1_profit": sim.seller1_profit,
                "seller2_profit": sim.seller2_profit
            })
        
        session.close()
        return results
    
    except Exception as e:
        session.close()
        raise e

