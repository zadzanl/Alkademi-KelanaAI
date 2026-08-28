"""Regression tests for the KelanaAI REST API.

Tests target the real configured local PostgreSQL database; rows are cleaned 
before and after each test; IDs are captured from POST responses. Tests verify
owner-scoped trip CRUD operations, cross-user isolation, anonymous rejection,
restart durability, legacy migration, and database cleanup.
"""

from datetime import datetime
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.database import SessionLocal
from backend.main import AUTH_COOKIE_NAME, app
from backend.migrations import (
    backfill_legacy_trips,
    enforce_trips_user_id_non_null,
    migrate_trips_schema,
    rollback_trips_user_id_migration,
    verify_trips_ownership,
)
from backend.models.session import Session as AuthSession
from backend.models.trip import Trip
from backend.models.user import User


class TripApiTests(unittest.TestCase):
    """Verify routes, deterministic composition, and persistence boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        # Entering TestClient as a context manager runs the FastAPI lifespan,
        # which calls init_db() and creates the trips table.
        cls.client = TestClient(app, base_url="https://testserver").__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        # Final cleanup and close lifespan context.
        cls._truncate_all()
        cls.client.__exit__(None, None, None)

    def setUp(self) -> None:
        self.ai_patch = patch("backend.main.get_ai_recommendation", return_value="## Trip plan")
        self.ai_mock = self.ai_patch.start()
        self.addCleanup(self.ai_patch.stop)
        self.client.cookies.clear()
        # Every test starts with clean tables.
        self._truncate_all()
        # Even if an assertion fails, leave the tables empty for the next test.
        self.addCleanup(self._truncate_all)
        # Register and authenticate default user for standard tests.
        self._register_and_login("default_user", "password123")

    @staticmethod
    def _truncate_all() -> None:
        session = SessionLocal()
        try:
            session.query(AuthSession).delete()
            session.query(Trip).delete()
            session.query(User).delete()
            session.commit()
        finally:
            session.close()

    def _register_and_login(
        self, username: str = "default_user", password: str = "password123"
    ) -> tuple[dict, str]:
        self.client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        token = login_resp.cookies.get(AUTH_COOKIE_NAME, "")
        return login_resp.json(), token

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
            "ai_recommendation",
        }
        self.assertEqual(set(body.keys()), expected_keys)

        # Dynamic fields: type/format only, no exact value.
        self.assertIsInstance(body["id"], int)
        self.assertTrue(body["ai_recommendation"] is None or isinstance(body["ai_recommendation"], str))
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
            "user_id",
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

    def test_empty_list_returns_paginated_envelope(self) -> None:
        response = self.client.get("/api/v1/trips")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"items": [], "total": 0, "page": 1, "page_size": 10},
        )

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

    def test_two_creates_are_listed_in_descending_id_order(self) -> None:
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
            [row["id"] for row in listing["items"]],
            [second["id"], first["id"]],
        )
        self.assertEqual(listing["total"], 2)

    def test_default_page_returns_ten_newest_with_full_total(self) -> None:
        created_ids = [
            self.client.post(
                "/api/v1/trips",
                json=self.valid_request(destination=f"Trip {index}"),
            ).json()["id"]
            for index in range(11)
        ]

        response = self.client.get("/api/v1/trips")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 11)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 10)
        self.assertEqual(
            [row["id"] for row in body["items"]],
            list(reversed(created_ids))[:10],
        )

    def test_page_and_page_size_slice_newest_first(self) -> None:
        created_ids = [
            self.client.post(
                "/api/v1/trips",
                json=self.valid_request(destination=f"Trip {index}"),
            ).json()["id"]
            for index in range(7)
        ]

        response = self.client.get("/api/v1/trips?page=2&page_size=3")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 7)
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 3)
        self.assertEqual(
            [row["id"] for row in body["items"]],
            list(reversed(created_ids))[3:6],
        )

    def test_invalid_pagination_query_returns_422(self) -> None:
        for query in (
            "page=0",
            "page=-1",
            "page=abc",
            "page_size=0",
            "page_size=-1",
            "page_size=101",
            "page_size=abc",
        ):
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/trips?{query}")
                self.assertEqual(response.status_code, 422)

    def test_out_of_range_page_returns_empty_items_with_total(self) -> None:
        created = self.client.post(
            "/api/v1/trips", json=self.valid_request()
        ).json()

        response = self.client.get("/api/v1/trips?page=999")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"items": [], "total": 1, "page": 999, "page_size": 10},
        )
        self.assertGreater(created["id"], 0)

    def test_huge_out_of_range_page_does_not_overflow_database(self) -> None:
        self.client.post("/api/v1/trips", json=self.valid_request())
        huge_page = 999999999999999999999

        response = self.client.get(f"/api/v1/trips?page={huge_page}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "items": [],
                "total": 1,
                "page": huge_page,
                "page_size": 10,
            },
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

    def test_put_budget_recomputes_derived_fields(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request(budget=1500)).json()

        response = self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 700})
        self.assertEqual(response.status_code, 200)
        updated = response.json()

        self.assertEqual(updated["budget"], 700.0)
        self.assertEqual(updated["category"], "Backpacker")
        self.assertEqual(updated["recommended_transportation"], "Bus")
        self.assertEqual(updated["daily_budget"], 140.0)

    def test_put_preserves_non_budget_fields(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()

        updated = self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 700}).json()

        for field in ("id", "destination", "country", "days", "currency", "travel_month", "travel_season", "created_at", "ai_recommendation"):
            self.assertEqual(updated[field], created[field])

    def test_ai_failure_still_creates_trip_with_null(self) -> None:
        self.ai_mock.return_value = None
        response = self.client.post("/api/v1/trips", json=self.valid_request())
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["ai_recommendation"])

    def test_put_preserves_ai_recommendation_without_invocation(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.ai_mock.reset_mock()
        updated = self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 700})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["ai_recommendation"], created["ai_recommendation"])
        self.ai_mock.assert_not_called()

    def test_put_preserves_null_ai_recommendation_without_invocation(self) -> None:
        self.ai_mock.return_value = None
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.assertIsNone(created["ai_recommendation"])
        self.ai_mock.reset_mock()
        updated = self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 700})
        self.assertEqual(updated.status_code, 200)
        self.assertIsNone(updated.json()["ai_recommendation"])
        self.ai_mock.assert_not_called()

    def test_string_max_lengths_are_rejected(self) -> None:
        for field, value in (("destination", "x" * 101), ("country", "x" * 101),
                             ("currency", "x" * 11), ("travel_month", "x" * 21)):
            with self.subTest(field=field):
                response = self.client.post("/api/v1/trips", json=self.valid_request(**{field: value}))
                self.assertEqual(response.status_code, 422)

    def test_openapi_exposes_ai_field_and_lengths(self) -> None:
        schema = self.client.get("/openapi.json").json()
        components = schema["components"]["schemas"]
        response_schema = components["TripResponse"]
        self.assertIn("ai_recommendation", response_schema["properties"])
        self.assertNotIn("user_id", response_schema["properties"])
        ai_schema = response_schema["properties"]["ai_recommendation"]
        self.assertTrue(ai_schema.get("nullable") or "anyOf" in ai_schema)
        request_schema = components["TripRequest"]["properties"]
        self.assertNotIn("user_id", request_schema)
        for field, length in (("destination", 100), ("country", 100), ("currency", 10), ("travel_month", 20)):
            self.assertEqual(request_schema[field]["maxLength"], length)

    def test_put_missing_budget_returns_422(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()

        response = self.client.put(f"/api/v1/trips/{created['id']}", json={})
        self.assertEqual(response.status_code, 422)

    def test_put_extra_fields_returns_422(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()

        response = self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 700, "days": 3})
        self.assertEqual(response.status_code, 422)

    def test_put_unknown_id_returns_404(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        unknown_id = created["id"] + 1000

        response = self.client.put(f"/api/v1/trips/{unknown_id}", json={"budget": 700})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Trip not found"})

    def test_put_non_integer_id_returns_422(self) -> None:
        response = self.client.put("/api/v1/trips/abc", json={"budget": 700})
        self.assertEqual(response.status_code, 422)

    def test_delete_returns_204_empty_body(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()

        response = self.client.delete(f"/api/v1/trips/{created['id']}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_get_after_delete_returns_404(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.client.delete(f"/api/v1/trips/{created['id']}")

        response = self.client.get(f"/api/v1/trips/{created['id']}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Trip not found"})

    def test_list_after_delete_excludes_deleted(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.client.delete(f"/api/v1/trips/{created['id']}")

        listing = self.client.get("/api/v1/trips").json()
        self.assertNotIn(
            created["id"], [row["id"] for row in listing["items"]]
        )

    def test_delete_unknown_id_returns_404(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        unknown_id = created["id"] + 1000

        response = self.client.delete(f"/api/v1/trips/{unknown_id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Trip not found"})

    def test_repeated_delete_returns_404(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.client.delete(f"/api/v1/trips/{created['id']}")

        response = self.client.delete(f"/api/v1/trips/{created['id']}")
        self.assertEqual(response.status_code, 404)

    def test_delete_non_integer_id_returns_422(self) -> None:
        response = self.client.delete("/api/v1/trips/abc")
        self.assertEqual(response.status_code, 422)

    def test_anonymous_rejection_for_all_trip_routes(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        self.client.cookies.clear()

        self.assertEqual(self.client.post("/api/v1/trips", json=self.valid_request()).status_code, 401)
        self.assertEqual(self.client.get("/api/v1/trips").status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/trips/{created['id']}").status_code, 401)
        self.assertEqual(self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 500}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/v1/trips/{created['id']}").status_code, 401)

    def test_user_isolation_for_all_crud_operations(self) -> None:
        # User A creates a trip
        trip_a = self.client.post(
            "/api/v1/trips",
            json=self.valid_request(destination="Tokyo", budget=1500),
        ).json()

        # Register and switch to User B
        self._register_and_login("user_b", "password123")

        # User B creates their own trip
        trip_b = self.client.post(
            "/api/v1/trips",
            json=self.valid_request(destination="Kyoto", budget=2000),
        ).json()

        # User B list only shows trip B
        list_b = self.client.get("/api/v1/trips").json()
        self.assertEqual(list_b["total"], 1)
        self.assertEqual([t["id"] for t in list_b["items"]], [trip_b["id"]])

        # User B cannot get User A's trip (404)
        get_other = self.client.get(f"/api/v1/trips/{trip_a['id']}")
        self.assertEqual(get_other.status_code, 404)
        self.assertEqual(get_other.json(), {"detail": "Trip not found"})

        # User B cannot update User A's trip (404)
        put_other = self.client.put(f"/api/v1/trips/{trip_a['id']}", json={"budget": 5000})
        self.assertEqual(put_other.status_code, 404)
        self.assertEqual(put_other.json(), {"detail": "Trip not found"})

        # User B cannot delete User A's trip (404)
        del_other = self.client.delete(f"/api/v1/trips/{trip_a['id']}")
        self.assertEqual(del_other.status_code, 404)
        self.assertEqual(del_other.json(), {"detail": "Trip not found"})

        # Switch back to User A
        self.client.post("/api/v1/auth/login", json={"username": "default_user", "password": "password123"})

        # User A list only shows trip A
        list_a = self.client.get("/api/v1/trips").json()
        self.assertEqual(list_a["total"], 1)
        self.assertEqual([t["id"] for t in list_a["items"]], [trip_a["id"]])

        # User A verifies trip A was unchanged by User B's rejected update
        get_a = self.client.get(f"/api/v1/trips/{trip_a['id']}").json()
        self.assertEqual(get_a["budget"], 1500.0)
        self.assertEqual(get_a["category"], "Standard")

        # User A can delete their own trip
        self.assertEqual(self.client.delete(f"/api/v1/trips/{trip_a['id']}").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/trips").json()["total"], 0)

    def test_client_cannot_inject_user_id_in_trip_creation(self) -> None:
        req = self.valid_request(user_id=9999, owner="other_user")
        resp = self.client.post("/api/v1/trips", json=req)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertNotIn("user_id", body)
        self.assertNotIn("owner", body)

        # Check in DB that user_id matches authenticated user
        db = SessionLocal()
        try:
            row = db.query(Trip).filter(Trip.id == body["id"]).first()
            user = db.query(User).filter(User.username == "default_user").first()
            self.assertIsNotNone(row)
            self.assertEqual(row.user_id, user.id)
            self.assertNotEqual(row.user_id, 9999)
        finally:
            db.close()

    def test_restart_durability_across_test_client_contexts(self) -> None:
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        token = self.client.cookies.get(AUTH_COOKIE_NAME)
        self.assertIsNotNone(token)

        with TestClient(app, base_url="https://testserver") as new_client:
            new_client.cookies.set(AUTH_COOKIE_NAME, token)
            detail_resp = new_client.get(f"/api/v1/trips/{created['id']}")
            self.assertEqual(detail_resp.status_code, 200)
            detail = detail_resp.json()
            self.assertEqual(detail["id"], created["id"])
            self.assertEqual(detail["created_at"], created["created_at"])
            self.assertEqual(detail["destination"], created["destination"])
            self.assertEqual(detail["ai_recommendation"], created["ai_recommendation"])
            self.assertNotIn("user_id", detail)

            list_resp = new_client.get("/api/v1/trips")
            self.assertEqual(list_resp.status_code, 200)
            self.assertEqual(list_resp.json()["total"], 1)

    def test_legacy_backfill_and_migration_lifecycle(self) -> None:
        db = SessionLocal()
        try:
            # Get current user ID
            user = db.query(User).filter(User.username == "default_user").first()

            # Temporarily drop NOT NULL constraint for the test scenario
            db.execute(text("ALTER TABLE trips ALTER COLUMN user_id DROP NOT NULL;"))
            db.commit()

            # Insert a legacy unowned trip with user_id = NULL
            db.execute(text("""
                INSERT INTO trips (
                    destination, country, days, budget, currency, travel_month,
                    daily_budget, travel_season, category, recommended_places,
                    recommended_transportation, ai_recommendation, created_at, user_id
                ) VALUES (
                    'Legacy Bali', 'Indonesia', 4, 1000, 'USD', 'June',
                    250, 'Holiday Season', 'Standard', '["Ubud", "Kuta"]',
                    'Train', '## Legacy AI Snapshot', NOW(), NULL
                );
            """))
            db.commit()

            # 1. Verify unowned stats
            stats = verify_trips_ownership(db)
            self.assertGreaterEqual(stats["unowned"], 1)

            # 2. Enforcing NOT NULL fails when unowned > 0
            with self.assertRaises(RuntimeError):
                enforce_trips_user_id_non_null(db)

            # 3. Backfill fails with non-existent target user
            with self.assertRaises(ValueError):
                backfill_legacy_trips(db, target_user_id=999999)

            # 4. Backfill succeeds with valid target user
            backfilled_count = backfill_legacy_trips(db, target_user_id=user.id)
            self.assertGreaterEqual(backfilled_count, 1)

            # 5. Verify stats show zero unowned
            post_stats = verify_trips_ownership(db)
            self.assertEqual(post_stats["unowned"], 0)

            # 6. Enforce NOT NULL succeeds
            enforce_trips_user_id_non_null(db)

            # 7. Verify legacy trip retains all snapshot fields and AI narrative
            legacy_row = db.query(Trip).filter(Trip.destination == "Legacy Bali").first()
            self.assertIsNotNone(legacy_row)
            self.assertEqual(legacy_row.user_id, user.id)
            self.assertEqual(legacy_row.category, "Standard")
            self.assertEqual(legacy_row.ai_recommendation, "## Legacy AI Snapshot")
        finally:
            try:
                db.execute(text("ALTER TABLE trips ALTER COLUMN user_id SET NOT NULL;"))
                db.commit()
            except Exception:
                pass
            db.close()

    def test_schema_migration_and_rollback_idempotency(self) -> None:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "default_user").first()

            # 1. Roll back user_id column completely to simulate legacy DB
            rollback_trips_user_id_migration(db)

            # 2. Insert legacy 13-column trip row without user_id
            db.execute(text("""
                INSERT INTO trips (
                    destination, country, days, budget, currency, travel_month,
                    daily_budget, travel_season, category, recommended_places,
                    recommended_transportation, ai_recommendation, created_at
                ) VALUES (
                    'Legacy Bandung', 'Indonesia', 3, 500, 'USD', 'December',
                    166.67, 'Peak Season', 'Backpacker', '["Tangkuban Perahu"]',
                    'Bus', '## Legacy Bandung Plan', NOW()
                );
            """))
            db.commit()

            # 3. Run migrate_trips_schema twice to verify idempotency
            migrate_trips_schema(db)
            migrate_trips_schema(db)

            # 4. Verify unowned stats
            stats = verify_trips_ownership(db)
            self.assertEqual(stats["unowned"], 1)

            # 5. Backfill and enforce constraint
            backfilled = backfill_legacy_trips(db, target_user_id=user.id)
            self.assertEqual(backfilled, 1)
            enforce_trips_user_id_non_null(db)

            # 6. Verify backfilled trip row
            row = db.query(Trip).filter(Trip.destination == "Legacy Bandung").first()
            self.assertIsNotNone(row)
            self.assertEqual(row.user_id, user.id)
            self.assertEqual(row.category, "Backpacker")
        finally:
            try:
                migrate_trips_schema(db)
                enforce_trips_user_id_non_null(db)
            except Exception:
                pass
            db.close()

    def test_session_revocation_and_expiration_rejection(self) -> None:
        import hashlib
        created = self.client.post("/api/v1/trips", json=self.valid_request()).json()
        token = self.client.cookies.get(AUTH_COOKIE_NAME)

        # 1. Revoke session explicitly in DB
        db = SessionLocal()
        try:
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            db.execute(text("UPDATE sessions SET revoked_at = NOW() WHERE token_digest = :digest"), {"digest": digest})
            db.commit()
        finally:
            db.close()

        # All trip endpoints reject revoked session with 401
        self.assertEqual(self.client.get("/api/v1/trips").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/trips", json=self.valid_request()).status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/trips/{created['id']}").status_code, 401)
        self.assertEqual(self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 500}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/v1/trips/{created['id']}").status_code, 401)

        # 2. Re-login and expire session
        self.client.post("/api/v1/auth/login", json={"username": "default_user", "password": "password123"})
        token2 = self.client.cookies.get(AUTH_COOKIE_NAME)
        db = SessionLocal()
        try:
            digest2 = hashlib.sha256(token2.encode("ascii")).hexdigest()
            db.execute(text("UPDATE sessions SET expires_at = NOW() - INTERVAL '1 day' WHERE token_digest = :digest"), {"digest": digest2})
            db.commit()
        finally:
            db.close()

        # All trip endpoints reject expired session with 401
        self.assertEqual(self.client.get("/api/v1/trips").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/trips", json=self.valid_request()).status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/trips/{created['id']}").status_code, 401)
        self.assertEqual(self.client.put(f"/api/v1/trips/{created['id']}", json={"budget": 500}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/v1/trips/{created['id']}").status_code, 401)

    def test_database_cleanup_leaves_no_records_behind(self) -> None:
        self.client.post("/api/v1/trips", json=self.valid_request())
        self._truncate_all()
        db = SessionLocal()
        try:
            self.assertEqual(db.query(Trip).count(), 0)
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
