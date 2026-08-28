"""Phase-one authentication regressions against the configured PostgreSQL database."""

import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import AUTH_COOKIE_NAME, app
from backend.models.session import Session
from backend.models.user import User


class AuthApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, base_url="https://testserver").__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        self.client.cookies.clear()
        self._clear_auth()
        self.addCleanup(self._clear_auth)

    @staticmethod
    def _clear_auth():
        db = SessionLocal()
        try:
            db.query(Session).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()

    def test_register_normalizes_and_never_returns_password_material(self):
        response = self.client.post("/api/v1/auth/register", json={"username": "  Ada_1 ", "password": "correct horse"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "ada_1")
        self.assertNotIn("password", response.text)
        self.assertNotIn("password_hash", response.text)
        db = SessionLocal()
        try:
            user = db.query(User).one()
            self.assertEqual(user.username, "ada_1")
            self.assertNotEqual(user.password_hash, "correct horse")
            self.assertTrue(user.password_hash.startswith("$argon2id$"))
        finally:
            db.close()

    def test_duplicates_invalid_input_and_generic_login_failure(self):
        body = {"username": "Ada", "password": "correct horse"}
        self.assertEqual(self.client.post("/api/v1/auth/register", json=body).status_code, 201)
        self.assertEqual(self.client.post("/api/v1/auth/register", json={**body, "username": " ada "}).status_code, 409)
        recognizable_password = "recognizable-secret" * 10
        invalid = self.client.post("/api/v1/auth/register", json={"username": "valid_user", "password": recognizable_password})
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn(recognizable_password, invalid.text)
        wrong = self.client.post("/api/v1/auth/login", json={"username": "Ada", "password": "wrong pass"})
        missing = self.client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong pass"})
        self.assertEqual(wrong.status_code, missing.status_code)
        self.assertEqual(wrong.json(), missing.json())

    def test_session_lifecycle_expiry_and_logout(self):
        self.client.post("/api/v1/auth/register", json={"username": "ada", "password": "correct horse"})
        login = self.client.post("/api/v1/auth/login", json={"username": "ada", "password": "correct horse"})
        self.assertEqual(login.status_code, 200)
        self.assertIn(AUTH_COOKIE_NAME, login.cookies)
        set_cookie = login.headers["set-cookie"].lower()
        self.assertIn("httponly", set_cookie)
        self.assertIn("samesite=lax", set_cookie)
        self.assertIn("path=/", set_cookie)
        self.assertIn("max-age=", set_cookie)
        token = login.cookies[AUTH_COOKIE_NAME]
        self.assertNotIn(token, login.text)
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["username"], "ada")
        with TestClient(app, base_url="https://testserver") as restarted_client:
            restarted_client.cookies.set(AUTH_COOKIE_NAME, token)
            self.assertEqual(restarted_client.get("/api/v1/auth/me").json()["username"], "ada")
        logout = self.client.post("/api/v1/auth/logout")
        self.assertEqual(logout.status_code, 204)
        self.assertIn("max-age=0", logout.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        db = SessionLocal()
        try:
            self.assertIsNotNone(db.query(Session).one().revoked_at)
            db.query(Session).one().expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()
        self.client.cookies.set(AUTH_COOKIE_NAME, token)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)

    def test_anonymous_me_is_unauthorized(self):
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)


if __name__ == "__main__":
    unittest.main()
