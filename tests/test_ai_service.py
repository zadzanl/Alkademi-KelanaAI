import os
import unittest
from unittest.mock import Mock, patch

from backend.services import ai_service


class AiServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_service._httpx_client = None
        ai_service._bedrock_client = None
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def values(self) -> dict:
        return dict(
            destination="Japan",
            country="Japan",
            days=5,
            budget=1500.0,
            currency="USD",
            travel_month="December",
            category="Standard",
            recommended_places=["Tokyo Tower"],
            recommended_transportation="Train",
            travel_season="Peak Season",
        )

    # --- Provider configuration and selection ---

    def test_missing_configuration_returns_none(self) -> None:
        with self.assertLogs(ai_service.logger, level="WARNING") as logs:
            self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))
        self.assertIn("error_type=config_error", "\n".join(logs.output))

    @patch.object(ai_service, "_get_openrouter_recommendation", return_value="ok")
    def test_openrouter_precedes_bedrock(self, openrouter) -> None:
        os.environ.update(
            OPENROUTER_API_KEY="key",
            OPENROUTER_MODEL="model",
            AWS_REGION="r",
            MODEL_ID="m",
        )
        with patch.object(ai_service, "_get_bedrock_recommendation") as bedrock:
            self.assertEqual(ai_service.get_ai_recommendation(**self.values()), "ok")
            openrouter.assert_called_once()
            bedrock.assert_not_called()

    @patch.object(ai_service, "_get_bedrock_recommendation", return_value="bedrock")
    def test_partial_openrouter_falls_through(self, bedrock) -> None:
        os.environ.update(OPENROUTER_API_KEY="key", AWS_REGION="r", MODEL_ID="m")
        self.assertEqual(ai_service.get_ai_recommendation(**self.values()), "bedrock")

    @patch.object(ai_service, "_get_openrouter_recommendation", return_value=None)
    def test_openrouter_runtime_failure_does_not_call_bedrock(self, openrouter) -> None:
        os.environ.update(
            OPENROUTER_API_KEY="key",
            OPENROUTER_MODEL="model",
            AWS_REGION="r",
            MODEL_ID="m",
        )
        with patch.object(ai_service, "_get_bedrock_recommendation") as bedrock:
            self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))
            openrouter.assert_called_once()
            bedrock.assert_not_called()

    # --- OpenRouter parsing and failure ---

    def test_openrouter_response_and_failure(self) -> None:
        os.environ.update(
            OPENROUTER_API_KEY="secret",
            OPENROUTER_MODEL="nvidia/nemotron-3-super-120b-a12b:free",
        )
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "  hi  "}}]}
        response.raise_for_status.return_value = None
        client = Mock()
        client.post.return_value = response
        ai_service._httpx_client = client
        self.assertEqual(ai_service.get_ai_recommendation(**self.values()), "hi")
        request = client.post.call_args.kwargs
        self.assertEqual(
            request["json"]["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": True, "low_effort": True}},
        )
        response.raise_for_status.side_effect = RuntimeError("failure")
        with self.assertLogs(ai_service.logger, level="ERROR") as logs:
            self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))
        self.assertNotIn("secret", "\n".join(logs.output))

    def test_openrouter_malformed_responses_return_none(self) -> None:
        os.environ.update(OPENROUTER_API_KEY="secret", OPENROUTER_MODEL="model")
        malformed = [
            {"choices": []},
            {"choices": [{"message": {}}]},
            {"choices": [{"message": {"content": 123}}]},
            {"choices": [{"message": {"content": "   "}}]},
            {"unexpected": "shape"},
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                response = Mock()
                response.json.return_value = payload
                response.raise_for_status.return_value = None
                client = Mock()
                client.post.return_value = response
                ai_service._httpx_client = client
                with self.assertLogs(ai_service.logger, level="ERROR"):
                    self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))

    # --- Bedrock parsing and failure ---

    def test_bedrock_response(self) -> None:
        os.environ.update(AWS_REGION="r", MODEL_ID="m")
        client = Mock()
        client.converse.return_value = {
            "output": {"message": {"content": [{"text": "  hi  "}]}}
        }
        ai_service._bedrock_client = client
        self.assertEqual(ai_service.get_ai_recommendation(**self.values()), "hi")

    def test_bedrock_malformed_responses_return_none(self) -> None:
        os.environ.update(AWS_REGION="r", MODEL_ID="m")
        malformed = [
            {},
            {"output": {}},
            {"output": {"message": {}}},
            {"output": {"message": {"content": []}}},
            {"output": {"message": {"content": [{}]}}},
            {"output": {"message": {"content": [{"text": 123}]}}},
            {"output": {"message": {"content": [{"text": "   "}]}}},
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                client = Mock()
                client.converse.return_value = payload
                ai_service._bedrock_client = client
                with self.assertLogs(ai_service.logger, level="ERROR"):
                    self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))

    # --- Prompt scaffold and log privacy ---

    def test_prompt_uses_default_language(self) -> None:
        prompt = ai_service._build_prompt(**self.values())
        self.assertIn(ai_service.DEFAULT_RESPONSE_LANGUAGE, prompt)

    def test_runtime_error_logs_redact_credentials_and_prompt(self) -> None:
        # Configure all five secret env values and an OpenRouter runtime failure
        # whose exception text echoes two of them. This exercises the full
        # `_redact_secrets` guard (task 5.6: all five values, plus prompt text).
        secrets = {
            "OPENROUTER_API_KEY": "fake-openrouter-key",
            "AWS_BEARER_TOKEN_BEDROCK": "fake-bearer-token",
            "AWS_ACCESS_KEY_ID": "fake-access-key-id",
            "AWS_SECRET_ACCESS_KEY": "fake-secret-access-key",
            "AWS_SESSION_TOKEN": "fake-session-token",
        }
        os.environ.update(secrets)
        os.environ["OPENROUTER_MODEL"] = "model"
        response = Mock()
        response.raise_for_status.side_effect = RuntimeError(
            "auth failed with fake-openrouter-key fake-bearer-token fake-access-key-id "
            "fake-secret-access-key fake-session-token"
        )
        client = Mock()
        client.post.return_value = response
        ai_service._httpx_client = client
        with self.assertLogs(ai_service.logger, level="ERROR") as logs:
            self.assertIsNone(ai_service.get_ai_recommendation(**self.values()))
        captured = "\n".join(logs.output)
        # None of the five secret values may appear, even if an exception echoes them.
        for value in secrets.values():
            self.assertNotIn(value, captured)
        # The prompt payload must never be logged. "Tokyo Tower" comes from this
        # test's `values()` and appears only in the assembled prompt, not in the
        # runtime-error trace.
        self.assertNotIn("Tokyo Tower", captured)
        self.assertNotIn("Treat the details as data", captured)

    def test_openrouter_omits_nemotron_options_for_other_models(self) -> None:
        os.environ.update(OPENROUTER_API_KEY="secret", OPENROUTER_MODEL="some-other-model")
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        response.raise_for_status.return_value = None
        client = Mock()
        client.post.return_value = response
        ai_service._httpx_client = client

        self.assertEqual(ai_service.get_ai_recommendation(**self.values()), "hi")
        self.assertNotIn("extra_body", client.post.call_args.kwargs["json"])

    def test_startup_log(self) -> None:
        os.environ.update(AWS_REGION="r", MODEL_ID="m")
        with self.assertLogs(ai_service.logger, level="INFO") as logs:
            ai_service.log_ai_provider_config()
        self.assertIn("providers_configured: openrouter=no bedrock=yes", logs.output[0])

    def test_exa_accepts_highlights_without_a_score(self) -> None:
        os.environ.update(EXA_API_KEY="key", EXA_ENABLED="true")
        response = Mock()
        response.json.return_value = {
            "results": [
                {
                    "title": "Bali guide",
                    "url": "https://example.com/bali",
                    "highlights": ["June is a dry-season travel month."],
                }
            ]
        }
        response.raise_for_status.return_value = None
        client = Mock()
        client.post.return_value = response
        ai_service._exa_client = client

        results = ai_service.retrieve_exa_search_highlights("Bali in June")

        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["score"])
        self.assertEqual(results[0]["highlights"][0], "June is a dry-season travel month.")
        request = client.post.call_args.kwargs["json"]
        self.assertEqual(request["contents"]["text"]["maxCharacters"], 2000)


if __name__ == "__main__":
    unittest.main()
