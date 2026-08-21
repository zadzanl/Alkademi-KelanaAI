"""Regression tests for the KelanaAI REST API.

Status: active | Phase: trip persistence | Last modified: 2026-08-20
Insights: Tests target the real configured local PostgreSQL database; rows
are cleaned before and after each test; IDs are captured from POST
responses and used instead of any fixed sequence value. Phase 1 covers
durable create plus reads. Phase 2 (PUT/DELETE) extends this file.
"""

import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.trip import Trip


class TripApiTests(unittest.TestCase):
    """Verify routes, deterministic composition, and persistence boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        # Entering TestClient as a context manager runs the FastAPI lifespan,
        # which calls init_db() and creates the trips table.
        cls.client = TestClient(app).__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        # Close the lifespan context opened in setUpClass.
        cls.client.__exit__(None, None, None)

    def setUp(self) -> None:
        # Every test starts with an empty table.
        self._truncate_trips()
        # Even if an assertion fails, leave the table empty for the next test.
        self.addCleanup(self._truncate_trips)

    @staticmethod
    def _truncate_trips() -> None:
        session = SessionLocal()
        try:
            session.query(Trip).delete()
            session.commit()
        finally:
            session.close()

    @staticmethod
    def valid_request(**overrides: object) -> dict[str, object]:
        request: dict[str, object] = {
            "destination": "Japan",
            "country": "Japan",
            "days": 5,
            "budget": 1500,
            "currency": "USD",
            "travel_month": "December",
        }
        request.update(overrides)
        return request

    @staticmethod
    def _parse_iso(value: str) -> datetime:
        """Parse a JSON ISO-8601 string, normalizing a trailing Z to +00:00."""
        text = value.replace("Z", "+00:00") if value.endswith("Z") else value
        return datetime.fromisoformat(text)

    def test_application_get_routes(self) -> None:
        expectations = {
            "/": {"message": "Welcome to KelanaAI"},
            "/health": {"status": "OK"},
        }

        for path, expected_json in expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), expected_json)

        self.assertEqual(self.client.get("/docs").status_code, 200)

    def test_recommendations_list(self) -> None:
        response = self.client.get("/api/v1/recommendations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), ["Tokyo Tower", "Shibuya", "Mount Fuji"]
        )

    def test_transportations_list(self) -> None:
        response = self.client.get("/api/v1/transportations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["Bus", "Train", "Flight"])

    def test_standard_december_trip_response(self) -> None:
        response = self.client.post("/api/v1/trips", json=self.valid_request())

        self.assertEqual(response.status_code, 200)
        body = response.json()

        expected_keys = {
            "id",
            "destination",
            "country",
            "days",
            "budget",
            "currency",
            "travel_month",
            "daily_budget",
            "travel_season",
            "category",
            "recommended_places",
            "recommended_transportation",
            "created_at",
        }
        self.assertEqual(set(body.keys()), expected_keys)

        # Dynamic fields: type/format only, no exact value.
        self.assertIsInstance(body["id"], int)
        self.assertGreater(body["id"], 0)
        self.assertIsInstance(self._parse_iso(body["created_at"]), datetime)

        # Eleven deterministically-stable fields.
        self.assertEqual(
            {
                "destination": body["destination"],
                "country": body["country"],
                "days": body["days"],
                "budget": body["budget"],
                "currency": body["currency"],
                "travel_month": body["travel_month"],
                "daily_budget": body["daily_budget"],
                "travel_season": body["travel_season"],
                "category": body["category"],
                "recommended_places": body["recommended_places"],
                "recommended_transportation": body["recommended_transportation"],
            },
            {
                "destination": "Japan",
                "country": "Japan",
                "days": 5,
                "budget": 1500.0,
                "currency": "USD",
                "travel_month": "December",
                "daily_budget": 300.0,
                "travel_season": "Peak Season",
                "category": "Standard",
                "recommended_places": ["Tokyo Tower", "Shibuya", "Mount Fuji"],
                "recommended_transportation": "Train",
            },
        )

        for removed_field in (
            "hotel_cost",
            "transport_cost",
            "food_cost",
            "misc_cost",
            "total",
            "stdev",
        ):
            self.assertNotIn(removed_field, body)

    def test_budget_categories_and_transportation(self) -> None:
        cases = (
            (700, "Backpacker", "Bus"),
            (2000, "Standard", "Train"),
            (5000, "Luxury", "Flight"),
        )

        for budget, category, transportation in cases:
            with self.subTest(budget=budget):
                response = self.client.post(
                    "/api/v1/trips", json=self.valid_request(budget=budget)
                )
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["category"], category)
                self.assertEqual(body["recommended_transportation"], transportation)

    def test_travel_seasons(self) -> None:
        cases = (
            ("December", "Peak Season"),
            ("June", "Holiday Season"),
            ("March", "Regular Season"),
        )

        for month, season in cases:
            with self.subTest(month=month):
                response = self.client.post(
                    "/api/v1/trips",
                    json=self.valid_request(travel_month=month),
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["travel_season"], season)

    def test_compatible_days_value_is_normalized(self) -> None:
        response = self.client.post(
            "/api/v1/trips", json=self.valid_request(days="5")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["days"], 5)
        self.assertIsInstance(response.json()["days"], int)

    def test_missing_required_fields_are_rejected(self) -> None:
        for field in self.valid_request():
            with self.subTest(field=field):
                request = self.valid_request()
                del request[field]
                response = self.client.post("/api/v1/trips", json=request)
                self.assertEqual(response.status_code, 422)

    def test_invalid_days_are_rejected(self) -> None:
        for days in ("five", 0, -1):
            with self.subTest(days=days):
                response = self.client.post(
                    "/api/v1/trips", json=self.valid_request(days=days)
                )
                self.assertEqual(response.status_code, 422)

    def test_empty_list_returns_empty_array(self) -> None:
        response = self.client.get("/api/v1/trips")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_post_detail_round_trip_preserves_id_and_timestamp(self) -> None:
        create_response = self.client.post(
            "/api/v1/trips", json=self.valid_request()
        )
        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()

        detail_response = self.client.get(
            f"/api/v1/trips/{created['id']}"
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()

        self.assertEqual(detail["id"], created["id"])
        self.assertEqual(detail["created_at"], created["created_at"])
        self.assertEqual(detail["destination"], created["destination"])
        self.assertEqual(detail["category"], created["category"])

    def test_two_creates_are_listed_in_ascending_id_order(self) -> None:
        first = self.client.post(
            "/api/v1/trips", json=self.valid_request()
        ).json()
        second_response = self.client.post(
            "/api/v1/trips",
            json=self.valid_request(
                destination="Bali", country="Indonesia", budget=2400
            ),
        )
        self.assertEqual(second_response.status_code, 200)
        second = second_response.json()

        listing = self.client.get("/api/v1/trips").json()
        self.assertEqual(
            [row["id"] for row in listing], [first["id"], second["id"]]
        )

    def test_unknown_detail_returns_404(self) -> None:
        created = self.client.post(
            "/api/v1/trips", json=self.valid_request()
        ).json()
        # Conservative offset: any captured id plus 1000 is absent in a clean
        # table regardless of PostgreSQL identity sequence state.
        unknown_id = created["id"] + 1000
        response = self.client.get(f"/api/v1/trips/{unknown_id}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Trip not found"})

    def test_non_integer_detail_path_returns_422(self) -> None:
        response = self.client.get("/api/v1/trips/not-a-number")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
