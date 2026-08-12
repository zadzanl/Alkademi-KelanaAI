"""Regression checks for deterministic trip recommendation rules."""

import unittest

from backend.services.trip_service import (
    calculate_daily_budget,
    get_recommended_places,
    get_recommended_transportation,
    get_trip_category,
)


class TripServiceTests(unittest.TestCase):
    def test_daily_budget(self) -> None:
        self.assertEqual(calculate_daily_budget(1500, 5), 300.0)

    def test_category_boundaries(self) -> None:
        expected = {
            999: "Backpacker",
            1000: "Standard",
            2999: "Standard",
            3000: "Luxury",
        }
        for budget, category in expected.items():
            with self.subTest(budget=budget):
                self.assertEqual(get_trip_category(budget), category)

    def test_ordered_places_for_every_category(self) -> None:
        expected = ["Tokyo Tower", "Shibuya", "Mount Fuji"]
        for category in ("Backpacker", "Standard", "Luxury"):
            with self.subTest(category=category):
                self.assertEqual(get_recommended_places(category), expected)

    def test_transportation_for_every_category(self) -> None:
        expected = {
            "Backpacker": "Bus",
            "Standard": "Train",
            "Luxury": "Flight",
        }
        for category, transportation in expected.items():
            with self.subTest(category=category):
                self.assertEqual(
                    get_recommended_transportation(category), transportation
                )


if __name__ == "__main__":
    unittest.main()