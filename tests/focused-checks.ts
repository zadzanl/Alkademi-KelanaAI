import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import { createTrip } from "../frontend/src/app/actions.ts";
import { localErrors, parse422, parseTripId, safeUrl } from "../frontend/src/app/safety.ts";
import { getTrips, getTrip, generateTrip, TripApiError } from "../frontend/src/services/tripService.ts";
import { categoryStyle } from "../frontend/src/lib/categoryStyle.ts";
import { markdownComponents, markdownPlugins, normalizeMarkdownTables } from "../frontend/src/lib/markdownPolicy.ts";
import { invalidateTripsCache } from "../frontend/src/lib/tripCache.ts";
import { months } from "../frontend/src/types/trip.ts";
import { parseAuthMode, parsePublicUser, upstreamSessionCookie, upstreamSessionMaxAge } from "../frontend/src/services/authService.ts";
import { RAG_COMPARE_TIMEOUT_MS } from "../frontend/src/services/knowledgeService.ts";

const values = {
	destination: "Kyoto",
	country: "Japan",
	days: "5",
	budget: "1500",
	currency: "USD" as const,
	travel_month: "December",
};

const form = () => {
	const result = new FormData();

	for (const [key, value] of Object.entries(values)) {
		result.set(key, value);
	}

	return result;
};

const response = (
	body: unknown,
	status = 200,
	headers: Record<string, string> = {},
) =>
	new Response(JSON.stringify(body), {
		status,
		headers: { "content-type": "application/json", ...headers },
	});

const validTrip = {
	id: 7,
	...values,
	days: 5,
	budget: 1500,
	daily_budget: 300,
	travel_season: "Peak Season",
	category: "Standard",
	recommended_places: [],
	recommended_transportation: "Train",
	created_at: "2026-01-01T00:00:00Z",
	ai_recommendation: null,
};

test("RAG comparison uses the dedicated 60 second timeout", () => {
	assert.equal(RAG_COMPARE_TIMEOUT_MS, 60_000);
});

test("citation URLs use the existing safe URL policy", () => {
	assert.equal(safeUrl("javascript:alert(1)"), undefined);
	assert.equal(safeUrl("https://example.com/guide"), "https://example.com/guide");
});

test("normalizes flattened Markdown table rows before rendering", () => {
	const flattened = "| Category | Cost | Notes | |----------|------|-------| | Flights | $350 | Book early | | **Total** | **$350** | Done |";
	const normalized = normalizeMarkdownTables(flattened);
	const markup = renderToStaticMarkup(
		ReactMarkdown({ children: normalized, components: markdownComponents("h3"), remarkPlugins: markdownPlugins }),
	);

	assert.match(normalized, /\| Category \| Cost \| Notes \|\n\|----------/);
	assert.match(markup, /<table>/);
	assert.match(markup, /Flights/);
	assert.match(markup, /Total/);
});

test("maps a successful FastAPI response", async () => {
	process.env.API_URL = "http://api.test";
	globalThis.fetch = async () => response(validTrip);

	const result = await createTrip(null, form());

	assert.equal(result.ok, true);
	if (result.ok) {
		assert.equal(result.trip.id, 7);
	}
});

test("auth cookie bridge keeps only the upstream cookie pair and public identity", () => {

	const upstream = new Response(JSON.stringify({ id: 1, username: "ada", created_at: "2026-01-01" }), {
		status: 200,
		headers: { "set-cookie": "kelana_session=opaque-token; HttpOnly; SameSite=Lax; Path=/" },
	});
	assert.equal(upstreamSessionCookie(upstream), "kelana_session=opaque-token");
	assert.equal(upstreamSessionCookie(new Response(null, { headers: { "set-cookie": "unrelated=x; Path=/" } })), null);
	assert.equal(upstreamSessionCookie(new Response(null, { headers: { "set-cookie": "kelana_session=; Path=/" } })), null);
	assert.deepEqual(parsePublicUser({ id: 1, username: "ada", created_at: "2026-01-01", password_hash: "secret" }), {
		id: 1,
		username: "ada",
		created_at: "2026-01-01",
	});
	assert.equal(parsePublicUser({ id: 1, username: "ada" }), null);
});

test("auth mode accepts only fixed login and registration routes", () => {
	assert.equal(parseAuthMode("login"), "login");
	assert.equal(parseAuthMode("register"), "register");
	assert.equal(parseAuthMode("/api/v1/auth/register"), null);
	assert.equal(parseAuthMode("logout"), null);
	assert.equal(parseAuthMode(null), null);
});

test("auth cookie lifetime comes from the matched session cookie", () => {
	const headers = new Headers();
	headers.append("set-cookie", "unrelated=value; Max-Age=10; Path=/");
	headers.append("set-cookie", "kelana_session=opaque-token; Max-Age=86400; HttpOnly; Path=/");
	const upstream = new Response(null, {
		headers,
	});
	assert.equal(upstreamSessionMaxAge(upstream), 86400);
	assert.equal(upstreamSessionMaxAge(new Response(null, { headers: { "set-cookie": "kelana_session=opaque-token; Path=/" } })), undefined);
	assert.ok((upstreamSessionMaxAge(new Response(null, { headers: { "set-cookie": "kelana_session=opaque-token; Max-Age=-1; Path=/" } })))! < 0);
	assert.ok((upstreamSessionMaxAge(new Response(null, { headers: { "set-cookie": "kelana_session=opaque-token; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/" } })))! < 0);
});

test("rejects invalid input locally without fetching", async () => {
	const invalid = form();
	invalid.set("days", "0");

	assert.equal(
		Object.hasOwn(localErrors({ ...values, days: "0" }), "days"),
		true,
	);

	const result = await createTrip(null, invalid);

	assert.equal(result.ok, false);
	if (!result.ok) {
		assert.equal(result.kind, "validation");
	}
});

test("maps only safe FastAPI 422 body locations", () => {
	const errorBody = {
		detail: [
			{
				loc: ["body", "days"],
				msg: "must be positive",
				input: 0,
				ctx: { secret: "x" },
			},
			{ loc: ["query", "secret"], msg: "no" },
		],
	};

	assert.deepEqual(parse422(errorBody), { days: "must be positive" });
});

test("classifies timeout, network, and retryable statuses", async () => {
	process.env.API_URL = "http://api.test";
	globalThis.fetch = async () => {
		throw Object.assign(new Error("slow"), { name: "TimeoutError" });
	};

	const timeout = await createTrip(null, form());

	assert.equal(timeout.ok, false);
	if (!timeout.ok) {
		assert.equal(timeout.kind, "timeout");
	}

	globalThis.fetch = async () => {
		throw new Error("offline");
	};

	const network = await createTrip(null, form());

	assert.equal(network.ok, false);
	if (!network.ok) {
		assert.equal(network.kind, "network");
	}

	globalThis.fetch = async () => response({}, 503);

	const upstream = await createTrip(null, form());

	assert.equal(upstream.ok, false);
	if (!upstream.ok) {
		assert.equal(upstream.kind, "upstream");
	}
});

test("rejects malformed and oversized upstream responses", async () => {
	globalThis.fetch = async () => new Response("not-json", { status: 200 });

	const malformed = await createTrip(null, form());

	assert.equal(malformed.ok, false);
	if (!malformed.ok) {
		assert.equal(malformed.kind, "malformed");
	}

	globalThis.fetch = async () =>
		new Response("x", {
			status: 200,
			headers: { "content-length": "1000001" },
		});

	const oversized = await createTrip(null, form());

	assert.equal(oversized.ok, false);
	if (!oversized.ok) {
		assert.equal(oversized.kind, "malformed");
	}
});

test("renders hostile Markdown URLs inert by policy", () => {
	// Dangerous schemes
	assert.equal(safeUrl("javascript:alert(1)"), undefined);
	assert.equal(safeUrl("JAVASCRIPT:alert(1)"), undefined);
	assert.equal(safeUrl("   javascript:alert(1)   "), undefined);
	assert.equal(safeUrl("java\tscript:alert(1)"), undefined);
	assert.equal(safeUrl("java\nscript:alert(1)"), undefined);
	assert.equal(safeUrl("vbscript:msgbox(1)"), undefined);
	assert.equal(safeUrl("file:///etc/passwd"), undefined);
	assert.equal(safeUrl("blob:https://example.com/test"), undefined);
	assert.equal(safeUrl("data:text/html,evil", true), undefined);

	// Relative and protocol-relative links
	assert.equal(safeUrl("/trips/1"), undefined);
	assert.equal(safeUrl("//evil.com"), undefined);
	assert.equal(safeUrl("#section"), undefined);

	// Allowed schemes
	assert.equal(safeUrl("https://example.com/image.png", true), "https://example.com/image.png");
	assert.equal(safeUrl("HTTPS://EXAMPLE.COM"), "https://example.com/");
	assert.equal(safeUrl("  https://example.com  "), "https://example.com/");
	assert.equal(safeUrl("mailto:guide@kelana.ai", false), "mailto:guide@kelana.ai");
	assert.equal(safeUrl("mailto:guide@kelana.ai", true), undefined);
});

test("uses field-specific country validation copy", () => {
	assert.equal(localErrors({ ...values, country: "" }).country, "Please enter a country.");
});

test("parseTripId validates positive integers and rejects invalid formats", () => {
	assert.equal(parseTripId("1"), 1);
	assert.equal(parseTripId("42"), 42);
	assert.equal(parseTripId(100), 100);
	assert.equal(parseTripId("2147483647"), 2147483647);

	// Invalid IDs
	assert.equal(parseTripId("0"), null);
	assert.equal(parseTripId("-1"), null);
	assert.equal(parseTripId("1.5"), null);
	assert.equal(parseTripId("01"), null);
	assert.equal(parseTripId("1e5"), null);
	assert.equal(parseTripId("0x10"), null);
	assert.equal(parseTripId("123abc"), null);
	assert.equal(parseTripId("abc"), null);
	assert.equal(parseTripId(""), null);
	assert.equal(parseTripId("   "), null);
	assert.equal(parseTripId(null), null);
	assert.equal(parseTripId(undefined), null);
	assert.equal(parseTripId(2147483648), null); // Exceeds Postgres 32-bit signed int max
	assert.equal(parseTripId("2147483648"), null);
	assert.equal(parseTripId("123456789012345"), null); // Exceeds 10 digits
	assert.equal(parseTripId({}), null);
});

test("tripService getTrips and getTrip fetch and parse responses", async () => {
	process.env.API_URL = "http://api.test";

	// getTrips success
	let requestedUrl = "";
	let requestedInit: RequestInit | undefined;
	let requestedTimeout: number | undefined;
	const originalTimeout = AbortSignal.timeout;
	AbortSignal.timeout = ((milliseconds: number) => {
		requestedTimeout = milliseconds;
		return originalTimeout(milliseconds);
	}) as typeof AbortSignal.timeout;
	globalThis.fetch = async (input, init) => {
		requestedUrl = String(input);
		requestedInit = init;
		return response({ items: [validTrip], total: 6, page: 2, page_size: 5 });
	};
	const trips = await getTrips(2, 5);
	AbortSignal.timeout = originalTimeout;
	assert.equal(requestedUrl, "http://api.test/api/v1/trips?page=2&page_size=5");
	assert.equal(requestedInit?.cache, "no-store");
	assert.equal(requestedTimeout, 8_000);
	assert.equal(trips.items.length, 1);
	assert.equal(trips.items[0].id, 7);
	assert.equal(trips.total, 6);
	assert.equal(trips.page, 2);
	assert.equal(trips.page_size, 5);

	// Defaults are forwarded exactly; FastAPI remains the authoritative range validator.
	globalThis.fetch = async (input) => {
		requestedUrl = String(input);
		return response({ items: [], total: 0, page: 1, page_size: 10 });
	};
	await getTrips();
	assert.equal(requestedUrl, "http://api.test/api/v1/trips?page=1&page_size=10");

	// getTrip success
	globalThis.fetch = async () => response(validTrip);
	const singleTrip = await getTrip(7);
	assert.notEqual(singleTrip, null);
	assert.equal(singleTrip?.id, 7);

	// getTrip 404 returns null
	globalThis.fetch = async () => response({ detail: "Trip not found" }, 404);
	const notFoundTrip = await getTrip(999);
	assert.equal(notFoundTrip, null);

	// getTrip invalid and out-of-bound IDs return null without fetching
	const invalidIdTrip = await getTrip("abc");
	assert.equal(invalidIdTrip, null);
	const negativeIdTrip = await getTrip(-1);
	assert.equal(negativeIdTrip, null);
	const overflowIdTrip = await getTrip(2147483648);
	assert.equal(overflowIdTrip, null);

	// HTML 502/503 proxy responses are classified as upstream
	globalThis.fetch = async () => new Response("<html><body>502 Bad Gateway</body></html>", { status: 502 });
	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "upstream",
	);
});

test("categoryStyle maps categories to consistent visual treatments", () => {
	// Backpacker / Budget → emerald
	const backpacker = categoryStyle("Backpacker");
	assert.ok(backpacker.badge.includes("emerald"));
	assert.ok(backpacker.avatar.includes("emerald"));

	const budget = categoryStyle("budget");
	assert.ok(budget.badge.includes("emerald"));

	// Luxury → amber
	const luxury = categoryStyle("Luxury");
	assert.ok(luxury.badge.includes("amber"));
	assert.ok(luxury.avatar.includes("amber"));

	// Standard / Mediocre / unknown → teal (fallback)
	const standard = categoryStyle("Standard");
	assert.ok(standard.badge.includes("teal"));

	const mediocre = categoryStyle("mediocre");
	assert.ok(mediocre.badge.includes("teal"));

	const unknown = categoryStyle("SomeNewCategory");
	assert.ok(unknown.badge.includes("teal"));

	const empty = categoryStyle("");
	assert.ok(empty.badge.includes("teal"));
});

test("months list is the single source of truth shared by types and safety", () => {
	// types/trip.ts exports the canonical list; lib/safety.ts imports it.
	// This invariant test ensures the two modules cannot drift apart.
	assert.equal(months.length, 12);
	assert.equal(months[0], "January");
	assert.equal(months[11], "December");
	assert.ok(months.includes("June"));
	assert.ok(months.includes("December"));

	// localErrors accepts every month in the canonical list
	for (const month of months) {
		const errors = localErrors({ ...values, travel_month: month });
		assert.equal(errors.travel_month, undefined, `month "${month}" should be valid`);
	}

	// localErrors rejects a month not in the list
	const errors = localErrors({ ...values, travel_month: "Smarch" });
	assert.equal(errors.travel_month, "Choose a valid month.");
});

test("safeUrl serializes backslash-containing http(s) URLs per WHATWG URL standard", () => {
	// The WHATWG URL parser normalizes backslashes to forward slashes in special-scheme
	// URLs (http:, https:). Since safeUrl only allows http:/https:/mailto:, a backslash
	// URL that parses successfully is normalized and safe.
	// Regression test for Changeability finding C-03.
	const result = safeUrl("https:\\\\example.com/path");
	assert.equal(result, "https://example.com/path");
	assert.equal(safeUrl("http:\\\\example.com/path"), "http://example.com/path");

	// Backslash URLs that fail to parse return undefined
	assert.equal(safeUrl("https:\\"), undefined);

	// Non-special schemes with backslashes are still blocked by protocol check
	assert.equal(safeUrl("javascript:alert(1)"), undefined);
});

test("getTrip throws malformed on contract drift (full-shape guard)", async () => {
	process.env.API_URL = "http://api.test";

	// Missing required fields
	globalThis.fetch = async () => response({ id: 1, destination: "Kyoto" });
	await assert.rejects(
		async () => getTrip(1),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);

	// Wrong type for a required field
	globalThis.fetch = async () => response({ ...validTrip, days: "five" });
	await assert.rejects(
		async () => getTrip(1),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);

	// Null ai_recommendation is valid
	globalThis.fetch = async () => response({ ...validTrip, ai_recommendation: null });
	const trip = await getTrip(1);
	assert.equal(trip?.ai_recommendation, null);
});

test("getTrips throws malformed on invalid envelopes and items", async () => {
	process.env.API_URL = "http://api.test";

	// Missing envelope metadata
	globalThis.fetch = async () => response({ items: [validTrip] });
	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);

	// One valid trip + one malformed trip
	globalThis.fetch = async () => response({
		items: [validTrip, { id: 99 }],
		total: 2,
		page: 1,
		page_size: 10,
	});
	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);
});

test("getTrips forwards invalid numbers for authoritative FastAPI validation", async () => {
	process.env.API_URL = "http://api.test";
	const cases = [
		{ page: 0, pageSize: 10 },
		{ page: 1, pageSize: 101 },
		{ page: 1.5, pageSize: 10 },
		{ page: Number.NaN, pageSize: 10 },
		{ page: Number.POSITIVE_INFINITY, pageSize: 10 },
		{ page: 1e21, pageSize: 10 },
	];

	for (const { page, pageSize } of cases) {
		let requestedUrl = "";
		globalThis.fetch = async (input) => {
			requestedUrl = String(input);
			return response({ detail: [] }, 422);
		};

		await assert.rejects(
			async () => getTrips(page, pageSize),
			(err: unknown) => err instanceof TripApiError && err.kind === "validation",
		);
		const parsed = new URL(requestedUrl);
		assert.equal(parsed.searchParams.get("page"), String(page));
		assert.equal(parsed.searchParams.get("page_size"), String(pageSize));
	}
});

test("streaming body cap rejects oversized response without content-length", async () => {
	process.env.API_URL = "http://api.test";

	// Create a ReadableStream that emits more than 1MB without setting content-length
	const encoder = new TextEncoder();
	const chunk = encoder.encode("x".repeat(100_000)); // 100KB per chunk
	let emitted = 0;
	let cancelled = false;

	const stream = new ReadableStream({
		pull(controller) {
			if (emitted < 15) {
				controller.enqueue(chunk);
				emitted++;
			} else {
				controller.close();
			}
		},
		cancel() {
			cancelled = true;
		},
	});

	globalThis.fetch = async () =>
		new Response(stream, {
			status: 200,
			headers: { "content-type": "application/json" },
		});

	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);
	assert.equal(cancelled, true);
	assert.ok(emitted < 15, "reader should reject before consuming the full stream");
});

test("actual ReactMarkdown policy renders hostile URLs inert and remaps headings", () => {
	const markdown = [
		"# Narrative heading",
		"[script](javascript:alert(1))",
		"![data image](data:text/html,evil)",
		"[safe](https://example.com/guide)",
		"<script>alert('raw')</script>",
	].join("\n\n");

	const html = renderToStaticMarkup(
		createElement(
			ReactMarkdown,
			{ components: markdownComponents("h2") },
			markdown,
		),
	);

	assert.equal(html.includes("<h1"), false);
	assert.equal(html.includes("javascript:"), false);
	assert.equal(html.includes("data:text/html"), false);
	assert.equal(html.includes("<script"), false);
	assert.match(html, /<h2[^>]*>Narrative heading<\/h2>/);
	assert.match(html, /href="https:\/\/example\.com\/guide"/);
});

test("trip cache invalidation calls the documented path and propagates runtime failures", async () => {
	let invalidatedPath: string | undefined;
	await invalidateTripsCache(async () => ({
		revalidatePath(path: string) {
			invalidatedPath = path;
		},
	}));
	assert.equal(invalidatedPath, "/trips");

	await assert.rejects(
		() => invalidateTripsCache(async () => ({
			revalidatePath() {
				throw new Error("request async storage failed in production");
			},
		})),
		/request async storage failed in production/,
	);
});

test("tripService maps 401 to unauthorized error kind in getTrips and generateTrip", async () => {
	process.env.API_URL = "http://api.test";

	// getTrips maps 401 to unauthorized
	globalThis.fetch = async () => response({ detail: "Authentication required" }, 401);
	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "unauthorized" && err.status === 401,
	);

	// generateTrip maps 401 to unauthorized
	globalThis.fetch = async () => response({ detail: "Authentication required" }, 401);
	await assert.rejects(
		async () => generateTrip({ destination: "Japan", country: "Japan", days: 5, budget: 1500, currency: "USD", travel_month: "December" }),
		(err: unknown) => err instanceof TripApiError && err.kind === "unauthorized" && err.status === 401,
	);

	// getTrip maps 401 to null (same as not found, hiding existence)
	globalThis.fetch = async () => response({ detail: "Authentication required" }, 401);
	const trip401 = await getTrip(123);
	assert.equal(trip401, null);
});

test("createTrip action maps 401 to unauthorized and preserves submitted form values", async () => {
	process.env.API_URL = "http://api.test";
	globalThis.fetch = async () => response({ detail: "Authentication required" }, 401);

	const result = await createTrip(null, form());

	assert.equal(result.ok, false);
	if (!result.ok) {
		assert.equal(result.kind, "unauthorized");
		assert.equal(result.message, "Please sign in to save your travel itinerary.");
		assert.equal(result.submitted.destination, "Kyoto");
		assert.equal(result.submitted.budget, "1500");
	}
});

test("tripService forwards request headers and preserves 14-field responses", async () => {
	process.env.API_URL = "http://api.test";
	let capturedHeaders: HeadersInit | undefined;

	globalThis.fetch = async (_input, init) => {
		capturedHeaders = init?.headers;
		return response(validTrip);
	};

	const created = await generateTrip({
		destination: "Kyoto",
		country: "Japan",
		days: 5,
		budget: 1500,
		currency: "USD",
		travel_month: "December",
	});

	assert.equal(created.id, 7);
	assert.equal(created.category, "Standard");
	assert.equal(Object.hasOwn(created, "user_id"), false);
	assert.ok(capturedHeaders !== undefined);
});

test("tripService maps non-JSON 401 responses to unauthorized error kind", async () => {
	process.env.API_URL = "http://api.test";

	// HTML or plain-text 401 response from proxy
	globalThis.fetch = async () =>
		new Response("<html><body>401 Unauthorized</body></html>", {
			status: 401,
			headers: { "content-type": "text/html" },
		});

	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "unauthorized" && err.status === 401,
	);
});

