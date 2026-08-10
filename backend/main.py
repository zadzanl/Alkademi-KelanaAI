"""KelanaAI - Trip Summary Generator.

Console-based baseline feature for KelanaAI, a travel planning application
with an integrated AI assistant for users in Indonesia.

Known ceiling: numeric prompts crash on non-numeric input (ValueError from
int()/float()). Upgrade path: wrap conversions in a retry loop with
user-friendly validation messages.
"""


def print_trip_summary(
    destination: str,
    country: str,
    days: int,
    budget: float,
    currency: str,
    travel_month: str,
) -> None:
    """Print a formatted summary of the trip details."""
    print()
    print("========================")
    print("KelanaAI")
    print("========================")
    print()
    print(f"Destination: {destination}")
    print(f"Country: {country}")
    print(f"Days: {days}")
    print(f"Budget: {budget} {currency}")
    print(f"Currency: {currency}")
    print(f"Travel Month: {travel_month}")


def main() -> None:
    """Prompt for trip details and print the trip summary."""
    destination = input("Destination: ")
    country = input("Country: ")
    days = int(input("Days: "))
    budget = float(input("Budget: "))
    currency = input("Currency: ")
    travel_month = input("Travel Month: ")

    print_trip_summary(destination, country, days, budget, currency, travel_month)


if __name__ == "__main__":
    main()
