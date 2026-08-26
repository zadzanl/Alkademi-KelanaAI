import test from "node:test";
import assert from "node:assert/strict";
import { createTrip } from "../frontend/src/app/actions.ts";
import { localErrors, parse422, safeUrl } from "../frontend/src/app/safety.ts";

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
	assert.equal(safeUrl("javascript:alert(1)"), undefined);
	assert.equal(safeUrl("data:text/html,evil", true), undefined);
	assert.equal(
		safeUrl("https://example.com/image.png", true),
		"https://example.com/image.png",
	);
});

test("uses field-specific country validation copy", () => {

	assert.equal(localErrors({ ...values, country: "" }).country, "Please enter a country.");
});