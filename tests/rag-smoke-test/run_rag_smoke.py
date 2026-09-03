"""Generate a two-file RAG retrieval and itinerary trace.

Live providers are preferred when configured. Without --strict-live, each failed
or unavailable source falls back to a small local fixture and records that fact.
The script intentionally writes only redacted request/response metadata.
"""
from __future__ import annotations

import argparse
import httpx
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "outputs"
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from backend.services import ai_service
from backend.services.trip_service import (
    get_recommended_transportation,
    get_trip_category,
    get_travel_season,
)

INPUT = {
    "destination": "Kathmandu",
    "country": "Nepal",
    "days": 5,
    "budget": 3500,
    "currency": "USD",
    "travel_month": "July",
}

MOCK_KB = [{"name": "mock-bali-guide.md", "score": 0.98, "id": "mock-kb-1", "text": "Bali dry-season planning: respect temple dress rules, use licensed guides for sacred sites, and allow extra road time around Ubud and southern Bali. Sunrise at Mount Batur requires an early start and local permit arrangements."}]
MOCK_WEB = [{"title": "Mock Bali travel update", "url": "https://example.invalid/bali-update", "score": 0.91, "highlights": ["June is commonly a drier travel period, but local conditions and traffic can change; verify conditions before departure."], "published_date": "2026-06-01"}]


def status_line(name: str, mode: str, started: float, error: str | None = None) -> dict:
    result = {"source": name, "mode": mode, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    if error:
        result["error"] = ai_service._redact_secrets(error)[:500]
    return result


def retrieve(strict: bool):
    query = f"{INPUT['destination']} {INPUT['country']} travel guide highlights activities transport tips {INPUT['travel_month']} {get_trip_category(INPUT['budget'])}"
    timings = []
    kb_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        kb_future = executor.submit(ai_service.retrieve_knowledge_chunks, query)
        web_future = executor.submit(ai_service.retrieve_exa_search_highlights, query)
        kb = kb_future.result(timeout=20)
        web = web_future.result(timeout=20)
    timings.append(status_line("aws_knowledge_base", "live" if kb else "empty_or_failed", kb_started))
    timings.append(status_line("exa", "live" if web else "empty_or_failed", kb_started))
    if not kb:
        if strict and os.getenv("BEDROCK_KNOWLEDGE_BASE_ID"):
            raise RuntimeError("AWS Knowledge Base returned no qualifying chunks")
        kb = MOCK_KB
        timings[0]["mode"] = "mock_fallback"
    if not web:
        if strict and os.getenv("EXA_API_KEY"):
            raise RuntimeError("Exa returned no qualifying results")
        web = MOCK_WEB
        timings[1]["mode"] = "mock_fallback"
    return query, kb, web, timings


def call_llm(prompt: str, strict: bool):
    started = time.perf_counter()
    provider = None
    response_meta = {}
    output = None
    error = None
    try:
        if os.getenv("OPENROUTER_API_KEY", "").strip() and os.getenv("OPENROUTER_MODEL", "").strip():
            provider = "openrouter"
            body = {"model": os.environ["OPENROUTER_MODEL"], "messages": [{"role": "user", "content": prompt}]}
            with httpx.Client(timeout=15) as client:
                response = client.post(ai_service.OPENROUTER_URL, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "X-OpenRouter-Title": "KelanaAI RAG smoke test"}, json=body)
            response.raise_for_status()
            payload = response.json()
            message = payload["choices"][0]["message"]
            output = message["content"].strip()
            response_meta = {k: payload.get(k) for k in ("id", "model", "created", "usage", "system_fingerprint") if k in payload}
            response_meta["finish_reason"] = payload.get("choices", [{}])[0].get("finish_reason")
        elif os.getenv("AWS_REGION", "").strip() and os.getenv("MODEL_ID", "").strip():
            provider = "bedrock"
            response = ai_service._get_boto_client("bedrock-runtime").converse(modelId=os.environ["MODEL_ID"], messages=[{"role": "user", "content": [{"text": prompt}]}])
            output = response["output"]["message"]["content"][0]["text"].strip()
            response_meta = {k: response.get(k) for k in ("metrics", "usage", "stopReason", "ResponseMetadata") if k in response}
        else:
            error = "No LLM provider configured"
    except Exception as exc:
        error = ai_service._redact_secrets(str(exc))
    if not output:
        if strict:
            raise RuntimeError(error or "LLM returned empty output")
        provider = "mock"
        output = """## Bali itinerary\n\n### Overview\nA five-day June trip focused on temples, culture, and a Mount Batur sunrise.\n\n### Day 1 — Arrival and Seminyak\n- Morning: Arrive and settle in.\n- Afternoon: Explore nearby beaches.\n- Evening: Dinner and rest.\n\n### Day 2 — Ubud\n- Morning: Visit Ubud with respectful temple clothing.\n- Afternoon: Rice terraces and a licensed local guide.\n- Evening: Return before peak traffic.\n\n### Day 3 — Mount Batur\n- Morning: Early sunrise trek with permits and a local guide.\n- Afternoon: Recover and visit a hot spring.\n- Evening: Quiet dinner.\n\n### Day 4 — Southern Bali\n- Morning: Visit a coastal temple.\n- Afternoon: Allow extra road time.\n- Evening: Sunset by the coast.\n\n### Day 5 — Departure\n- Morning: Flexible local breakfast.\n- Afternoon: Transfer to the airport.\n- Evening: Departure."""
    return output, {"provider": provider, "duration_ms": round((time.perf_counter() - started) * 1000, 2), "error": error, **response_meta}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-live", action="store_true", help="fail instead of using fixtures")
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    category = get_trip_category(INPUT["budget"])
    query, kb, web, retrieval = retrieve(args.strict_live)
    values = {**INPUT, "category": category, "recommended_places": [], "recommended_transportation": get_recommended_transportation(category), "travel_season": get_travel_season(INPUT["travel_month"]), "_retrieved_kb": kb, "_retrieved_web": web}
    prompt = ai_service._build_prompt(**values)
    output, generation = call_llm(prompt, args.strict_live)
    metadata = {"run_id": run_id, "started_at_utc": started_at.isoformat(), "finished_at_utc": datetime.now(timezone.utc).isoformat(), "mode": "strict-live" if args.strict_live else "live-with-mock-fallback", "input": INPUT, "derived": {"category": category, "travel_season": values["travel_season"]}, "retrieval": retrieval, "generation": generation, "counts": {"knowledge_base_chunks": len(kb), "exa_results": len(web), "prompt_characters": len(prompt), "output_characters": len(output), "output_words": len(output.split())}}
    OUT.mkdir(exist_ok=True)
    header = f"# RAG smoke trace\n\n```json\n{json.dumps(metadata, indent=2, default=str)}\n```\n"
    (OUT / "prompt.md").write_text(header + f"\n## Retrieval query\n\n`{query}`\n\n## Knowledge Base chunks\n\n```json\n{json.dumps(kb, indent=2, ensure_ascii=False)}\n```\n\n## Exa results\n\n```json\n{json.dumps(web, indent=2, ensure_ascii=False)}\n```\n\n## Exact pre-LLM prompt\n\n```text\n{prompt}\n```\n", encoding="utf-8")
    (OUT / "output.md").write_text(header + f"\n## LLM itinerary\n\n{output}\n", encoding="utf-8")
    print(f"Wrote {OUT / 'prompt.md'}")
    print(f"Wrote {OUT / 'output.md'}")
    print(f"LLM provider: {generation['provider']} | KB: {retrieval[0]['mode']} | Exa: {retrieval[1]['mode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
