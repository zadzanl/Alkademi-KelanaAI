"""KelanaAI FastAPI application.

Status: active | Phase: REST API cut-over | Last modified: 2026-08-18
Known ceiling: Recommendations remain static and nominal-budget based; replace the
service rules through a future approved change when destination-aware data exists.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.services.trip_service import (
    calculate_daily_budget,
    get_recommended_places,
    get_recommended_transportation,
    get_travel_season,
    get_trip_category,
)


app = FastAPI()

# Mirrors RECOMMENDATIONS transportation order: Backpacker, Standard, Luxury.
TRANSPORTATIONS = ["Bus", "Train", "Flight"]


class TripRequest(BaseModel):
    """Validated trip input accepted by the REST API."""

    destination: str
    country: str
    days: int = Field(gt=0)
    budget: float
    currency: str
    travel_month: str


class TripResponse(BaseModel):
    """Trip details and deterministic recommendations returned by the API."""

    destination: str
    country: str
    days: int
    budget: float
    currency: str
    travel_month: str
    daily_budget: float
    travel_season: str
    category: str
    recommended_places: list[str]
    recommended_transportation: str


@app.get("/")
def welcome() -> dict[str, str]:
    """Return the application welcome message."""
    return {"message": "Welcome to KelanaAI"}


@app.get("/health")
def health() -> dict[str, str]:
    """Return the application health status."""
    return {"status": "OK"}


@app.get("/api/v1/recommendations")
def list_recommendations() -> list[str]:
    """Return the service-backed ordered place recommendations."""
    return get_recommended_places(get_trip_category(1500))


@app.get("/api/v1/transportations")
def list_transportations() -> list[str]:
    """Return the ordered transportation options."""
    return TRANSPORTATIONS


@app.post("/api/v1/trips", response_model=TripResponse)
def create_trip(trip: TripRequest) -> TripResponse:
    """Create a deterministic trip recommendation from validated input."""
    category = get_trip_category(trip.budget)

    return TripResponse(
        destination=trip.destination,
        country=trip.country,
        days=trip.days,
        budget=trip.budget,
        currency=trip.currency,
        travel_month=trip.travel_month,
        daily_budget=calculate_daily_budget(trip.budget, trip.days),
        travel_season=get_travel_season(trip.travel_month),
        category=category,
        recommended_places=get_recommended_places(category),
        recommended_transportation=get_recommended_transportation(category),
    )
