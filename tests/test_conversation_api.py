"""Tests for conversational assistant API and persistence."""

import os
import unittest
import threading
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import inspect, text
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.migrations import _with_transaction, migrate_conversation_message_requests_schema, verify_conversation_message_requests_schema
from backend.main import AUTH_COOKIE_NAME, app
from backend.models.conversation import Conversation
from backend.models.conversation_message_request import ConversationMessageRequest
from backend.models.message import Message
from backend.models.session import Session
from backend.models.user import User
from backend.services import ai_service


class ConversationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, base_url="https://testserver").__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        self.client.cookies.clear()
        self._clear_db()
        self.addCleanup(self._clear_db)

    @staticmethod
    def _clear_db():
        db = SessionLocal()
        try:
            db.query(ConversationMessageRequest).delete()
            db.query(Message).delete()
            db.query(Conversation).delete()
            db.query(Session).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()

    def _register_user(self, username="user_one", password="password123"):
        res = self.client.post("/api/v1/auth/register", json={"username": username, "password": password})
        self.assertEqual(res.status_code, 201)
        # Login to receive cookie
        login_res = self.client.post("/api/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(login_res.status_code, 200)
        return login_res.cookies.get(AUTH_COOKIE_NAME)

    def test_unauthenticated_endpoints_return_401(self):
        self.assertEqual(self.client.get("/api/v1/conversations").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/conversations", json={}).status_code, 401)
        self.assertEqual(self.client.get("/api/v1/conversations/1/messages").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/conversations/1/messages", json={"content": "hello"}).status_code, 401)
        self.assertEqual(self.client.patch("/api/v1/conversations/1", json={"title": "test"}).status_code, 401)

    def test_create_and_list_conversations(self):
        cookie = self._register_user("alice")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)

        # Create with default title
        res = self.client.post("/api/v1/conversations", json={})
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("conversation_id", data)
        self.assertEqual(data["title"], "New Conversation")
        conv_id = data["conversation_id"]

        # Create with custom title
        res2 = self.client.post("/api/v1/conversations", json={"title": "Bali Vacation"})
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json()["title"], "Bali Vacation")

        # List conversations - newest first
        list_res = self.client.get("/api/v1/conversations")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "Bali Vacation")
        self.assertEqual(items[1]["id"], conv_id)

    def test_conversation_isolation_between_users(self):
        cookie_a = self._register_user("user_a")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie_a)
        res_a = self.client.post("/api/v1/conversations", json={"title": "User A Trip"})
        conv_a_id = res_a.json()["conversation_id"]

        cookie_b = self._register_user("user_b")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie_b)

        # User B should not see user A's conversation
        list_b = self.client.get("/api/v1/conversations").json()
        self.assertEqual(len(list_b), 0)

        # User B should get 404 when attempting to access user A's conversation
        self.assertEqual(self.client.get(f"/api/v1/conversations/{conv_a_id}/messages").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/conversations/{conv_a_id}/messages", json={"content": "hi"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/conversations/{conv_a_id}", json={"title": "Hacked"}).status_code, 404)

    def test_rename_conversation(self):
        cookie = self._register_user("bob")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)

        res = self.client.post("/api/v1/conversations", json={"title": "Old Name"})
        conv_id = res.json()["conversation_id"]

        patch_res = self.client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "New Name"})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["title"], "New Name")

        # Validation checks
        empty_patch = self.client.patch(f"/api/v1/conversations/{conv_id}", json={"title": ""})
        self.assertEqual(empty_patch.status_code, 422)

        extra_field = self.client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "Valid", "extra": "forbidden"})
        self.assertEqual(extra_field.status_code, 422)

    @patch("backend.main.generate_chat_response", return_value="AI Itinerary for Japan: Day 1 Tokyo...")
    def test_send_message_and_multi_turn_flow(self, mock_chat):
        cookie = self._register_user("traveler")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)

        res = self.client.post("/api/v1/conversations", json={})
        conv_id = res.json()["conversation_id"]

        # Send Turn 1
        msg_res1 = self.client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Plan a 5-day trip to Japan"},
        )
        self.assertEqual(msg_res1.status_code, 201)
        data1 = msg_res1.json()
        self.assertEqual(data1["role"], "assistant")
        self.assertEqual(data1["content"], "AI Itinerary for Japan: Day 1 Tokyo...")
        mock_chat.assert_called_once()

        # Check that title was auto-updated from default
        convs = self.client.get("/api/v1/conversations").json()
        self.assertEqual(convs[0]["title"], "Plan a 5-day trip to Japan")

        # Mock Turn 2 reply
        mock_chat.return_value = "On Day 2 in Tokyo, visit Asakusa Senso-ji and Shibuya."
        msg_res2 = self.client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "What should we do on Day 2?"},
        )
        self.assertEqual(msg_res2.status_code, 201)
        data2 = msg_res2.json()
        self.assertEqual(data2["role"], "assistant")
        self.assertEqual(data2["content"], "On Day 2 in Tokyo, visit Asakusa Senso-ji and Shibuya.")

        # Verify full message thread
        thread_res = self.client.get(f"/api/v1/conversations/{conv_id}/messages")
        self.assertEqual(thread_res.status_code, 200)
        messages = thread_res.json()
        self.assertEqual(len(messages), 4)  # user1, assistant1, user2, assistant2
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Plan a 5-day trip to Japan")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(messages[2]["content"], "What should we do on Day 2?")
        self.assertEqual(messages[3]["role"], "assistant")

    @patch("backend.main.generate_chat_response", return_value=None)
    def test_provider_failure_returns_fallback_message_gracefully(self, mock_chat):
        cookie = self._register_user("charlie")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)

        res = self.client.post("/api/v1/conversations", json={})
        conv_id = res.json()["conversation_id"]

        msg_res = self.client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hello AI"},
        )
        self.assertEqual(msg_res.status_code, 201)
        data = msg_res.json()
        self.assertEqual(data["role"], "assistant")
        self.assertIn("unable to generate a response", data["content"])

    def test_cascade_deletion(self):
        cookie = self._register_user("dave")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)

        res = self.client.post("/api/v1/conversations", json={})
        conv_id = res.json()["conversation_id"]

        with patch("backend.main.generate_chat_response", return_value="Reply"):
            self.client.post(f"/api/v1/conversations/{conv_id}/messages", json={"content": "Hi"})

        db = SessionLocal()
        try:
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
            conv = db.get(Conversation, conv_id)
            db.delete(conv)
            db.commit()
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 0)
        finally:
            db.close()

    def test_ledger_migration_is_verified_and_repeatable(self):
        """Exercise the migration seam against the same PostgreSQL test database."""
        db = SessionLocal()
        try:
            bind = db.get_bind()
            with bind.begin() as conn:
                result = migrate_conversation_message_requests_schema(conn)
            self.assertFalse(result["created"])
            self.assertTrue(result["verified"])
            with bind.connect() as conn:
                verified = verify_conversation_message_requests_schema(conn)
            self.assertTrue(verified["verified"])
            self.assertEqual(verified["columns"], 13)
        finally:
            db.close()

    def test_absent_ledger_is_created_and_verified_after_commit(self):
        db = SessionLocal()
        try:
            engine = db.get_bind()
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE conversation_message_requests"))
            with engine.begin() as conn:
                result = migrate_conversation_message_requests_schema(conn)
            self.assertTrue(result["created"])
            self.assertFalse(result["verified"])
            with engine.connect() as conn:
                verified = verify_conversation_message_requests_schema(conn)
            self.assertTrue(verified["verified"])
        finally:
            db.close()

    def test_ledger_migration_rolls_back_injected_ddl(self):
        db = SessionLocal()
        try:
            engine = db.get_bind()
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE conversation_message_requests"))

            def failing_operation(conn):
                conn.execute(text("CREATE TABLE migration_probe (id INTEGER)"))
                raise RuntimeError("injected DDL failure")

            with self.assertRaisesRegex(RuntimeError, "injected DDL failure"):
                _with_transaction(engine, failing_operation)
            with engine.connect() as conn:
                self.assertIsNone(conn.execute(text("SELECT to_regclass('public.migration_probe')")).scalar())
                self.assertIsNone(conn.execute(text("SELECT to_regclass('public.conversation_message_requests')")).scalar())
        finally:
            with engine.begin() as conn:
                migrate_conversation_message_requests_schema(conn)
            db.close()

    def test_partial_ledger_schema_fails_closed_without_mutation(self):
        db = SessionLocal()
        engine = db.get_bind()
        try:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE conversation_message_requests"))
                conn.execute(text("CREATE TABLE conversation_message_requests (id BIGINT PRIMARY KEY)"))
            with engine.connect() as conn:
                before = conn.execute(text("""SELECT column_name FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='conversation_message_requests'
                    ORDER BY ordinal_position""")).scalars().all()
            with self.assertRaisesRegex(RuntimeError, "Incompatible"):
                migrate_conversation_message_requests_schema(engine)
            with engine.connect() as conn:
                after = conn.execute(text("""SELECT column_name FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='conversation_message_requests'
                    ORDER BY ordinal_position""")).scalars().all()
            self.assertEqual(after, before)
        finally:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS conversation_message_requests"))
                migrate_conversation_message_requests_schema(conn)
            db.close()

    def test_ledger_catalog_proves_identity_and_link_cascades(self):
        db = SessionLocal()
        try:
            engine = db.get_bind()
            with engine.connect() as conn:
                identity = conn.execute(text("""SELECT is_identity, identity_generation
                    FROM information_schema.columns WHERE table_schema='public'
                    AND table_name='conversation_message_requests' AND column_name='id'""")).one()
                self.assertEqual(tuple(identity), ("YES", "BY DEFAULT"))
                foreign_keys = inspect(conn).get_foreign_keys("conversation_message_requests")
                self.assertEqual(len(foreign_keys), 4)
                self.assertTrue(all(fk["options"].get("ondelete") == "CASCADE" for fk in foreign_keys))

            user = User(username="cascade_probe", password_hash="hash")
            db.add(user); db.flush()
            conversation = Conversation(user_id=user.id, title="Cascade")
            db.add(conversation); db.flush()
            message = Message(conversation_id=conversation.id, role="user", content="probe")
            db.add(message); db.flush()
            from datetime import datetime, timezone
            ledger = ConversationMessageRequest(
                user_id=user.id, conversation_id=conversation.id, key_digest="a" * 64,
                content_digest="b" * 64, status="processing", user_message_id=message.id,
                claim_token="c" * 64, lease_expires_at=datetime.now(timezone.utc),
            )
            db.add(ledger); db.commit()
            db.delete(user); db.commit()
            # Query the database rather than the non-expiring identity map.
            self.assertEqual(
                db.query(ConversationMessageRequest)
                .filter(ConversationMessageRequest.id == ledger.id)
                .count(),
                0,
            )
        finally:
            db.close()

    def test_failed_session_migration_rolls_back_and_session_remains_usable(self):
        db = SessionLocal()
        try:
            with self.assertRaises(RuntimeError):
                _with_transaction(db, lambda _bind: (_ for _ in ()).throw(RuntimeError("injected DDL failure")))
            # The explicit rollback policy makes a failed PostgreSQL transaction
            # reusable instead of leaving it in the aborted state.
            self.assertEqual(db.execute(__import__("sqlalchemy").text("SELECT 1")).scalar(), 1)
        finally:
            db.close()

    def test_keyless_messages_do_not_create_ledger_rows(self):
        cookie = self._register_user("ledger_keyless")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        with patch("backend.main.generate_chat_response", return_value="Reply"):
            self.client.post(f"/api/v1/conversations/{conv_id}/messages", json={"content": "Keyless"})
        db = SessionLocal()
        try:
            self.assertEqual(db.query(ConversationMessageRequest).count(), 0)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
        finally:
            db.close()

    def test_concurrent_first_keyed_send_is_arbitrated_by_postgres(self):
        cookie = self._register_user("concurrent_keyed")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        barrier = threading.Barrier(2)
        calls = []

        def provider(_history):
            calls.append(1)
            return "one durable reply"

        results = []

        def send():
            client = TestClient(app, base_url="https://testserver")
            client.cookies.set(AUTH_COOKIE_NAME, cookie)
            barrier.wait(timeout=5)
            results.append(client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers={"Idempotency-Key": key}, json={"content": "same request"},
            ))

        with patch("backend.main.generate_chat_response", side_effect=provider):
            threads = [threading.Thread(target=send) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(sorted(result.status_code for result in results), [200, 201])
        self.assertEqual(len(calls), 1)
        db = SessionLocal()
        try:
            self.assertEqual(db.query(ConversationMessageRequest).filter(
                ConversationMessageRequest.conversation_id == conv_id).count(), 1)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
        finally:
            db.close()

    def test_keyed_provider_exception_leaves_one_recoverable_claim(self):
        cookie = self._register_user("keyed_exception")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        with patch("backend.main.generate_chat_response", side_effect=RuntimeError("provider exploded")) as provider:
            result = self.client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers={"Idempotency-Key": key}, json={"content": "retry me"},
            )
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()["detail"]["code"], "chat_generation_unavailable")
        provider.assert_called_once()
        db = SessionLocal()
        try:
            ledger = db.query(ConversationMessageRequest).one()
            self.assertEqual(ledger.status, "processing")
            self.assertIsNotNone(ledger.claim_token)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 1)
        finally:
            db.close()

    @patch("backend.main.generate_chat_response", return_value="Keyed reply")
    def test_keyed_send_replays_without_provider_or_rows(self, mock_chat):
        cookie = self._register_user("keyed_first")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        first = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "Hello keyed"})
        self.assertEqual(first.status_code, 201)
        second = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "Hello keyed"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(second.headers["X-KelanaAI-Chat-Idempotency"], "v1")
        mock_chat.assert_called_once()
        db = SessionLocal()
        try:
            self.assertEqual(db.query(ConversationMessageRequest).count(), 1)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
        finally:
            db.close()

    @patch("backend.main.generate_chat_response", return_value="Keyed reply")
    def test_keyed_conflict_does_not_call_provider(self, mock_chat):
        cookie = self._register_user("keyed_conflict")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "one"})
        conflict = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "two"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "idempotency_key_conflict")
        mock_chat.assert_called_once()

    def test_malformed_key_is_masked_by_owner_lookup(self):
        cookie = self._register_user("keyed_mask")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        self.client.cookies.clear()
        self.assertEqual(self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": "bad"}, json={"content": "x"}).status_code, 401)

    @patch("backend.main.generate_chat_response")
    def test_owned_malformed_key_has_capability_marker_and_no_writes(self, provider):
        cookie = self._register_user("owned_bad_key")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        result = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": "bad"}, json={"content": "x"})
        self.assertEqual(result.status_code, 422)
        self.assertEqual(result.json()["detail"]["code"], "idempotency_key_invalid")
        self.assertEqual(result.headers["X-KelanaAI-Chat-Idempotency"], "v1")
        provider.assert_not_called()
        db = SessionLocal()
        try:
            self.assertEqual(db.query(ConversationMessageRequest).count(), 0)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 0)
        finally:
            db.close()

    @patch("backend.main.generate_chat_response", return_value="unused")
    def test_active_processing_returns_retry_after_and_marker_without_provider(self, provider):
        cookie = self._register_user("active_processing")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        db = SessionLocal()
        try:
            user_id = db.query(User).filter(User.username == "active_processing").one().id
            message = Message(conversation_id=conv_id, role="user", content="wait")
            db.add(message); db.flush()
            db.add(ConversationMessageRequest(user_id=user_id, conversation_id=conv_id, key_digest=__import__("hashlib").sha256(key.encode()).hexdigest(), content_digest=__import__("hashlib").sha256(b"wait").hexdigest(), status="processing", user_message_id=message.id, claim_token="active-token", lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30)))
            db.commit()
        finally:
            db.close()
        result = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "wait"})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()["detail"]["code"], "idempotency_key_in_progress")
        self.assertEqual(result.headers["X-KelanaAI-Chat-Idempotency"], "v1")
        self.assertTrue(1 <= int(result.headers["Retry-After"]) <= 120)
        provider.assert_not_called()

    @patch("backend.main.generate_chat_response", return_value="recovered")
    def test_stale_processing_is_claimed_once_and_completed(self, mock_chat):
        cookie = self._register_user("stale_claim")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        db = SessionLocal()
        try:
            user_id = db.query(User).filter(User.username == "stale_claim").one().id
            message = Message(conversation_id=conv_id, role="user", content="recover me")
            db.add(message); db.flush()
            db.add(ConversationMessageRequest(user_id=user_id, conversation_id=conv_id,
                key_digest=__import__("hashlib").sha256(key.encode()).hexdigest(),
                content_digest=__import__("hashlib").sha256(b"recover me").hexdigest(),
                status="processing", user_message_id=message.id, claim_token="old-token",
                lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()

        result = self.client.post(f"/api/v1/conversations/{conv_id}/messages",
            headers={"Idempotency-Key": key}, json={"content": "recover me"})
        self.assertEqual(result.status_code, 201)
        mock_chat.assert_called_once()
        db = SessionLocal()
        try:
            ledger = db.query(ConversationMessageRequest).one()
            self.assertEqual(ledger.status, "completed")
            self.assertIsNone(ledger.claim_token)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
        finally:
            db.close()

    def test_two_stale_claimants_have_one_provider_and_retryable_loser(self):
        cookie = self._register_user("stale_race")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        db = SessionLocal()
        try:
            user_id = db.query(User).filter(User.username == "stale_race").one().id
            message = Message(conversation_id=conv_id, role="user", content="race me")
            db.add(message); db.flush()
            db.add(ConversationMessageRequest(user_id=user_id, conversation_id=conv_id,
                key_digest=__import__("hashlib").sha256(key.encode()).hexdigest(),
                content_digest=__import__("hashlib").sha256(b"race me").hexdigest(),
                status="processing", user_message_id=message.id, claim_token="old-race-token",
                lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()
        provider_started = threading.Event()
        release_provider = threading.Event()
        calls = []
        calls_lock = threading.Lock()

        def provider(_history):
            with calls_lock:
                calls.append(1)
            provider_started.set()
            self.assertTrue(release_provider.wait(timeout=5))
            return "race reply"

        results = []
        barrier = threading.Barrier(2)

        def send():
            client = TestClient(app, base_url="https://testserver")
            client.cookies.set(AUTH_COOKIE_NAME, cookie)
            barrier.wait(timeout=5)
            results.append(client.post(f"/api/v1/conversations/{conv_id}/messages",
                headers={"Idempotency-Key": key}, json={"content": "race me"}))

        with patch("backend.main.generate_chat_response", side_effect=provider):
            threads = [threading.Thread(target=send) for _ in range(2)]
            for thread in threads: thread.start()
            self.assertTrue(provider_started.wait(timeout=5))
            for _ in range(50):
                if len(results) == 1:
                    break
                threading.Event().wait(0.02)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status_code, 409)
            self.assertEqual(results[0].json()["detail"]["code"], "idempotency_key_in_progress")
            self.assertEqual(results[0].headers["X-KelanaAI-Chat-Idempotency"], "v1")
            self.assertTrue(1 <= int(results[0].headers["Retry-After"]) <= 120)
            release_provider.set()
            for thread in threads: thread.join(timeout=10)
        self.assertEqual(sorted(result.status_code for result in results), [201, 409])
        self.assertEqual(len(calls), 1)
        db = SessionLocal()
        try:
            ledger = db.query(ConversationMessageRequest).one()
            self.assertEqual(ledger.status, "completed")
            self.assertIsNone(ledger.claim_token)
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
        finally:
            db.close()

    def test_late_stale_claim_cannot_commit_after_recovery_wins(self):
        cookie = self._register_user("late_claim")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        db = SessionLocal()
        try:
            user_id = db.query(User).filter(User.username == "late_claim").one().id
            message = Message(conversation_id=conv_id, role="user", content="late me")
            db.add(message); db.flush()
            db.add(ConversationMessageRequest(user_id=user_id, conversation_id=conv_id,
                key_digest=__import__("hashlib").sha256(key.encode()).hexdigest(),
                content_digest=__import__("hashlib").sha256(b"late me").hexdigest(),
                status="processing", user_message_id=message.id, claim_token="old-late-token",
                lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()
        first_started = threading.Event()
        release_first = threading.Event()
        calls = []
        calls_lock = threading.Lock()

        def provider(_history):
            with calls_lock:
                calls.append(len(calls) + 1)
                number = calls[-1]
            if number == 1:
                first_started.set()
                self.assertTrue(release_first.wait(timeout=5))
                return "late reply"
            return "recovery reply"

        first_result = []

        def send_first():
            client = TestClient(app, base_url="https://testserver")
            client.cookies.set(AUTH_COOKIE_NAME, cookie)
            first_result.append(client.post(f"/api/v1/conversations/{conv_id}/messages",
                headers={"Idempotency-Key": key}, json={"content": "late me"}))

        with patch("backend.main.generate_chat_response", side_effect=provider):
            thread = threading.Thread(target=send_first)
            thread.start()
            self.assertTrue(first_started.wait(timeout=5))
            db = SessionLocal()
            try:
                changed = db.query(ConversationMessageRequest).filter(
                    ConversationMessageRequest.conversation_id == conv_id
                ).update({"lease_expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
                self.assertEqual(changed, 1)
                db.commit()
            finally:
                db.close()
            recovery_client = TestClient(app, base_url="https://testserver")
            recovery_client.cookies.set(AUTH_COOKIE_NAME, cookie)
            recovery = recovery_client.post(f"/api/v1/conversations/{conv_id}/messages",
                headers={"Idempotency-Key": key}, json={"content": "late me"})
            self.assertEqual(recovery.status_code, 201, recovery.text)
            release_first.set()
            thread.join(timeout=10)
        self.assertEqual(len(first_result), 1)
        self.assertEqual(first_result[0].status_code, 500)
        self.assertEqual(first_result[0].json()["detail"]["code"], "chat_request_integrity_error")
        self.assertEqual(len(calls), 2)
        db = SessionLocal()
        try:
            ledger = db.query(ConversationMessageRequest).one()
            self.assertEqual(ledger.status, "completed")
            self.assertEqual(db.query(Message).filter(Message.conversation_id == conv_id).count(), 2)
            self.assertEqual(db.get(Message, ledger.assistant_message_id).content, "recovery reply")
        finally:
            db.close()
    @patch("backend.main.generate_chat_response", return_value="must not run")
    def test_corrupt_completed_replay_fails_closed_without_provider(self, mock_chat):
        cookie = self._register_user("corrupt_replay")
        self.client.cookies.set(AUTH_COOKIE_NAME, cookie)
        conv_id = self.client.post("/api/v1/conversations", json={}).json()["conversation_id"]
        key = str(uuid4())
        first = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "original"})
        self.assertEqual(first.status_code, 201)
        db = SessionLocal()
        try:
            ledger = db.query(ConversationMessageRequest).one()
            db.query(Message).filter(Message.id == ledger.assistant_message_id).update({"role": "user"})
            db.commit()
        finally:
            db.close()
        replay = self.client.post(f"/api/v1/conversations/{conv_id}/messages", headers={"Idempotency-Key": key}, json={"content": "original"})
        self.assertEqual(replay.status_code, 500)
        self.assertEqual(replay.json()["detail"]["code"], "chat_request_integrity_error")
        mock_chat.assert_called_once()
