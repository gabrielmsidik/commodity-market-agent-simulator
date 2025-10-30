"""Logging configuration for the simulation."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "commodity_market",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Set up a logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file
        log_dir: Directory for log files
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler (matches logger level - can be DEBUG or INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)  # Use the same level as the logger
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG and above)
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_path / f"simulation_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_file}")
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name (defaults to 'commodity_market')
    
    Returns:
        Logger instance
    """
    if name is None:
        name = "commodity_market"
    
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up
    if not logger.handlers:
        return setup_logger(name)
    
    return logger

