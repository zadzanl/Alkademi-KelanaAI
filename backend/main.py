"""KelanaAI - Trip Summary Generator.

Console-based baseline feature for KelanaAI, a travel planning application
with an integrated AI assistant for users in Indonesia.
"""

try:
    from backend.services.trip_service import (
        calculate_daily_budget,
        get_recommended_places,
        get_recommended_transportation,
        get_travel_season,
        get_trip_category,
    )
except ModuleNotFoundError:
    from services.trip_service import (
        calculate_daily_budget,
        get_recommended_places,
        get_recommended_transportation,
        get_travel_season,
        get_trip_category,
    )

def print_trip_summary(
    destination: str,
    country: str,
    days: int,
    budget: float,
    currency: str,
    travel_month: str,
    travel_season: str,
    hotel_cost: int,
    transport_cost: int,
    food_cost: int,
    misc_cost: int,
    category: str,
    daily_budget: float,
    recommended_places: list[str],
    recommended_transportation: str,
) -> None:
    """Print a formatted summary of the trip details."""
    cost_list = [hotel_cost, transport_cost, food_cost, misc_cost]
    total = sum(cost_list)
    mean = total / len(cost_list)
    stdev = (sum((x - mean) ** 2 for x in cost_list) / (len(cost_list) - 1)) ** 0.5

    print()
    print("========================")
    print("KelanaAI")
    print("========================")
    print()
    print(f"Destination:          {destination}")
    print(f"Country:              {country}")
    print(f"Days:                 {days}")
    print(f"Budget:               {budget} {currency}")
    print(f"Currency:             {currency}")
    print(f"Travel Month:         {travel_month}")
    print(f"Travel Season:        {travel_season}")
    print(f"Hotel Cost:           {hotel_cost} {currency}")
    print(f"Transport Cost:       {transport_cost} {currency}")
    print(f"Food Cost:            {food_cost} {currency}")
    print(f"Misc Cost:            {misc_cost} {currency}")
    print(f"Total Estimated Cost: {total} {currency} +- {stdev:,.2f} {currency}")
    print(f"Category:             {category}")
    print(f"Daily Budget:         {daily_budget} {currency}/Day")
    print("Recommended Places:")
    for place in recommended_places:
        print(f"- {place}")
    print(f"Recommended Transportation: {recommended_transportation}")

def main() -> None:
    """Prompt for trip details and print the trip summary."""
    destination = input("Destination: ")
    country = input("Country: ")
    days = int(input("Days: "))
    budget = float(input("Budget: "))
    currency = input("Currency: ")
    travel_month = input("Travel Month: ")
    hotel_cost = int(input("Hotel Cost: "))
    transport_cost = int(input("Transport Cost: "))
    food_cost = int(input("Food Cost: "))
    misc_cost = int(input("Miscellaneous Cost: "))

    daily_budget = calculate_daily_budget(budget, days)
    travel_season = get_travel_season(travel_month)
    category = get_trip_category(budget)
    recommended_places = get_recommended_places(category)
    recommended_transportation = get_recommended_transportation(category)

    print_trip_summary(
        destination,
        country,
        days,
        budget,
        currency,
        travel_month,
        travel_season,
        hotel_cost,
        transport_cost,
        food_cost,
        misc_cost,
        category,
        daily_budget,
        recommended_places,
        recommended_transportation,
    )

if __name__ == "__main__":
    main()
