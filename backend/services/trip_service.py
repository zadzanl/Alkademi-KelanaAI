"""

Deterministic trip recommendation rules.

"""

RECOMMENDATIONS = {
    "Backpacker": {
        "places": ("Tokyo Tower", "Shibuya", "Mount Fuji"),
        "transportation": "Bus",
    },
    "Standard": {
        "places": ("Tokyo Tower", "Shibuya", "Mount Fuji"),
        "transportation": "Train",
    },
    "Luxury": {
        "places": ("Tokyo Tower", "Shibuya", "Mount Fuji"),
        "transportation": "Flight",
    },
}


def calculate_daily_budget(budget: float, days: int) -> float:
    """Return the entered budget divided by the trip duration."""
    return budget / days


def get_trip_category(budget: float) -> str:
    """Classify an entered budget using the lesson's nominal thresholds."""
    if budget < 1000:
        return "Backpacker"
    if budget < 3000:
        return "Standard"
    return "Luxury"


def get_recommended_places(category: str) -> list[str]:
    """Return a copy of the ordered place recommendations for a category."""
    return list(RECOMMENDATIONS[category]["places"])


def get_recommended_transportation(category: str) -> str:
    """Return the transportation recommendation for a category."""
    return RECOMMENDATIONS[category]["transportation"]