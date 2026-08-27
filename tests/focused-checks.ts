import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import { createTrip } from "../frontend/src/app/actions.ts";
import { localErrors, parse422, parseTripId, safeUrl } from "../frontend/src/app/safety.ts";
import { getTrips, getTrip, TripApiError } from "../frontend/src/services/tripService.ts";
import { categoryStyle } from "../frontend/src/lib/categoryStyle.ts";
import { markdownComponents } from "../frontend/src/lib/markdownPolicy.ts";
import { invalidateTripsCache } from "../frontend/src/lib/tripCache.ts";
import { months } from "../frontend/src/types/trip.ts";

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

test("maps a successful FastAPI response", async () => {
	process.env.API_URL = "http://api.test";
	globalThis.fetch = async () => response(validTrip);

	const result = await createTrip(null, form());

	assert.equal(result.ok, true);
	if (result.ok) {
		assert.equal(result.trip.id, 7);
	}
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
	globalThis.fetch = async () => response([validTrip]);
	const trips = await getTrips();
	assert.equal(Array.isArray(trips), true);
	assert.equal(trips.length, 1);
	assert.equal(trips[0].id, 7);

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

test("getTrips throws malformed when any array element fails full-shape guard", async () => {
	process.env.API_URL = "http://api.test";

	// One valid trip + one malformed trip
	globalThis.fetch = async () => response([validTrip, { id: 99 }]);
	await assert.rejects(
		async () => getTrips(),
		(err: unknown) => err instanceof TripApiError && err.kind === "malformed",
	);
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