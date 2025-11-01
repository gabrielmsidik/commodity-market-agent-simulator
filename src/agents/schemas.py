"""Pydantic schemas for structured LLM outputs."""

from pydantic import BaseModel, Field
from typing import Literal


class NegotiationResponse(BaseModel):
    """Structured response for negotiation offers."""
    
    scratchpad_update: str = Field(
        description="Concise notes to ADD to your scratchpad - focus on new insights, patterns, or strategic observations. Keep it brief and non-redundant."
    )
    price: int = Field(
        description="Integer price per unit for the offer",
        ge=0
    )
    quantity: int = Field(
        description="Number of units to trade",
        ge=0
    )
    justification: str = Field(
        description="What you tell the other party about why this price is fair - be strategic about what you reveal"
    )
    action: Literal["offer", "accept", "reject"] = Field(
        description="Action to take: 'offer' to make/counter an offer, 'accept' to accept their last offer, 'reject' to end negotiation"
    )


class MarketOfferResponse(BaseModel):
    """Structured response for daily market offers."""

    scratchpad_update: str = Field(
        description="Concise notes to ADD to your scratchpad - focus on new insights about market conditions, pricing strategy, or inventory management. Keep it brief."
    )
    price: int = Field(
        description="Integer price per unit to offer on the market today",
        ge=0
    )
    quantity: int = Field(
        description="Maximum number of units willing to sell today",
        ge=0
    )
    reasoning: str = Field(
        description="Brief explanation of your pricing and quantity strategy for today"
    )


class CommunicationResponse(BaseModel):
    """Structured response for inter-agent communication."""

    scratchpad_update: str = Field(
        description="Concise notes to ADD to your scratchpad about this communication - insights gained, strategy adjustments, or collusion considerations. Keep it brief."
    )
    message: str = Field(
        description="Your message to the other wholesaler. Be strategic - you can propose coordination, share information, or compete. This is free-form text."
    )

