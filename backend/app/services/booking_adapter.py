"""Third-party booking API adapter (Adapter Pattern).

MockEZTableAdapter simulates EZTable responses so the reservation flow
can be built and demoed without real API credentials. Swap
`get_booking_adapter()` for a real HTTP-calling implementation later —
no other code needs to change.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from . import restaurant_catalog


class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    NO_AVAILABILITY = "NO_AVAILABILITY"
    ERROR = "ERROR"


@dataclass
class BookingResult:
    status: BookingStatus
    booking_id: str | None = None
    share_reservation_url: str | None = None
    message: str | None = None


@dataclass
class AvailabilityResult:
    available: bool
    alternative_slots: list[str] = field(default_factory=list)


class BookingAdapter:
    """Base interface for third-party booking adapters."""

    async def create_booking(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        people: int,
        contact_name: str,
        phone: str,
    ) -> BookingResult:
        raise NotImplementedError

    async def check_availability(
        self,
        restaurant_id: str,
        date: str,
        time_slot: str,
    ) -> AvailabilityResult:
        raise NotImplementedError


class MockEZTableAdapter(BookingAdapter):
    """Simulated EZTable responses, keyed off restaurant seed flags."""

    TIMEOUT_SECONDS = 10  # Requirement 9.1

    async def create_booking(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        people: int,
        contact_name: str,
        phone: str,
    ) -> BookingResult:
        restaurant = restaurant_catalog.get_restaurant(restaurant_id)
        if not restaurant:
            return BookingResult(status=BookingStatus.ERROR, message="Restaurant not found.")

        if restaurant["verification_enabled"]:
            booking_id = f"EZ-MOCK-{uuid.uuid4().hex[:8].upper()}"
            return BookingResult(
                status=BookingStatus.CONFIRMED,
                booking_id=booking_id,
                share_reservation_url=f"https://eztable.example.com/booking/{booking_id}",
            )

        return BookingResult(status=BookingStatus.ERROR, message="Simulated third-party API failure.")

    async def check_availability(
        self,
        restaurant_id: str,
        date: str,
        time_slot: str,
    ) -> AvailabilityResult:
        return AvailabilityResult(available=True)


def get_booking_adapter() -> BookingAdapter:
    return MockEZTableAdapter()
