"use client";
/* eslint-disable @next/next/no-img-element -- react-markdown supplies an already URL-scheme-validated image source. */

import { useActionState, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { createTrip } from "./actions";
import { safeUrl } from "./safety";
import {
  initialForm,
  months,
  type ActionState,
  type FormValues,
  type TripResponse,
} from "./types";

const inputClass =
  "mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-slate-900 shadow-sm outline-none transition focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:bg-slate-100";

type FieldProps = {
  label: string;
  name: keyof FormValues;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  type?: string;
  children?: React.ReactNode;
  disabled?: boolean;
  [key: string]: unknown;
};

function Field({
  label,
  name,
  value,
  onChange,
  error,
  type = "text",
  children,
  disabled,
  ...props
}: FieldProps) {
  const id = `trip-${name}`;

  return (
    <div>
      <label htmlFor={id} className="font-semibold text-slate-800">
        {label}
      </label>
      {children ? (
        <select
          disabled={disabled}
          id={id}
          name={name}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={inputClass}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          {...props}
        >
          {children}
        </select>
      ) : (
        <input
          disabled={disabled}
          id={id}
          name={name}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={inputClass}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          {...props}
        />
      )}
      {error && (
        <p
          id={`${id}-error`}
          className="mt-2 text-sm font-medium text-rose-700"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}

function Results({ trip }: { trip: TripResponse }) {
  const metrics = [
    ["Total budget", `${trip.currency} ${trip.budget.toLocaleString()}`],
    [
      "Daily budget",
      `${trip.currency} ${trip.daily_budget.toLocaleString()}`,
    ],
    ["Season", trip.travel_season],
    ["Getting around", trip.recommended_transportation],
  ];

  return (
    <section aria-labelledby="results-heading" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-teal-700">
            Your route, mapped
          </p>
          <h2
            id="results-heading"
            className="mt-2 text-3xl font-bold tracking-[-0.02em] text-slate-950"
          >
            {trip.destination}
          </h2>
          <p className="mt-2 text-slate-600">
            {trip.days} days · {trip.travel_month} · {trip.country}
          </p>
        </div>
        <span className="rounded-full bg-emerald-100 px-4 py-2 text-sm font-bold text-emerald-900">
          {trip.category}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 font-bold text-slate-950">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-bold text-slate-950">
            Places to keep close
          </h3>
          <ul className="mt-4 space-y-3">
            {trip.recommended_places.map((place) => (
              <li key={place} className="flex gap-3 text-slate-700">
                <span className="text-teal-600" aria-hidden="true">
                  ●
                </span>
                {place}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-teal-100 bg-teal-50/60 p-6 shadow-sm">
          <h3 className="text-xl font-bold text-slate-950">AI itinerary</h3>
          {trip.ai_recommendation ? (
            <div className="prose prose-teal mt-4 max-w-none">
              <ReactMarkdown
                components={{
                  a: ({ href, children }) => {
                    const safe = href ? safeUrl(href) : undefined;
                    return safe ? (
                      <a href={safe} rel="noreferrer">
                        {children}
                      </a>
                    ) : (
                      <span>{children}</span>
                    );
                  },
                  img: ({ src, alt }) => {
                    const safe =
                      typeof src === "string" ? safeUrl(src, true) : undefined;
                    return safe ? <img src={safe} alt={alt ?? ""} /> : null;
                  },
                }}
              >
                {trip.ai_recommendation}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="mt-4 rounded-xl bg-white/70 p-4 text-slate-700">
              AI itinerary unavailable for this trip — deterministic summary
              shown above.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [values, setValues] = useState<FormValues>(initialForm);
  const [state, formAction, pending] = useActionState<
    ActionState | null,
    FormData
  >(createTrip, null);

  useEffect(() => {
    if (state?.submitted) {
      setValues(state.submitted);
    }
  }, [state]);

  const update = (name: keyof FormValues) => (value: string) =>
    setValues((current) => ({ ...current, [name]: value }));
  const errors = state?.ok === false ? state.fieldErrors : undefined;

  return (
    <div className="min-h-screen bg-[#f5f8f7] text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav
          className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5"
          aria-label="Primary"
        >
          <a
            href="#top"
            className="text-xl font-black tracking-[-0.03em] text-teal-800"
          >
            Kelana<span className="text-emerald-600">AI</span>
          </a>
          <div className="hidden gap-7 text-sm font-semibold text-slate-600 sm:flex">
            <a href="#planner" className="hover:text-teal-700">
              Plan a trip
            </a>
            <a href="#about" className="hover:text-teal-700">
              About
            </a>
          </div>
        </nav>
      </header>

      <main id="top">
        <section className="relative isolate overflow-hidden bg-slate-950">
          <div
            className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,#0f766e_0%,transparent_38%),linear-gradient(125deg,#082f49,#0f766e_65%,#064e3b)]"
            aria-hidden="true"
          />
          <div className="relative mx-auto max-w-6xl px-5 py-20 sm:py-28">
            <div className="max-w-2xl rounded-3xl bg-slate-950/70 p-7 shadow-2xl ring-1 ring-white/10 sm:p-10">
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-300">
                Travel, considered
              </p>
              <h1 className="mt-4 text-4xl font-bold leading-tight tracking-[-0.03em] text-white sm:text-6xl">
                Go farther with a plan that feels like you.
              </h1>
              <p className="mt-6 max-w-[65ch] text-lg leading-8 text-slate-200">
                Tell KelanaAI where you want to go, and get a grounded trip
                snapshot for your next adventure.
              </p>
              <div className="mt-8 flex flex-wrap gap-2 text-sm font-semibold text-white">
                <span className="rounded-full bg-white/15 px-4 py-2">
                  Bali
                </span>
                <span className="rounded-full bg-white/15 px-4 py-2">
                  Labuan Bajo
                </span>
                <span className="rounded-full bg-white/15 px-4 py-2">
                  Tokyo
                </span>
              </div>
            </div>
          </div>
        </section>

        <section
          id="planner"
          className="mx-auto grid max-w-6xl gap-10 px-5 py-14 lg:grid-cols-[0.8fr_1.2fr] lg:py-20"
        >
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-teal-700">
              Start with the essentials
            </p>
            <h2 className="mt-3 text-3xl font-bold tracking-[-0.02em] text-slate-950">
              Build your trip snapshot
            </h2>
            <p className="mt-4 max-w-[65ch] leading-7 text-slate-700">
              A few details are enough to shape a useful first direction. You
              can adjust the plan later.
            </p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md sm:p-8">
            <form action={formAction} className="space-y-6">
              <div className="grid gap-5 md:grid-cols-2">
                <Field
                  disabled={pending}
                  label="Destination"
                  name="destination"
                  value={values.destination}
                  onChange={update("destination")}
                  error={errors?.destination}
                  required
                  maxLength={100}
                  placeholder="e.g. Kyoto"
                />
                <Field
                  disabled={pending}
                  label="Country"
                  name="country"
                  value={values.country}
                  onChange={update("country")}
                  error={errors?.country}
                  required
                  maxLength={100}
                  placeholder="e.g. Japan"
                />
                <Field
                  disabled={pending}
                  label="Days"
                  name="days"
                  type="number"
                  value={values.days}
                  onChange={update("days")}
                  error={errors?.days}
                  required
                  min="1"
                  max="365"
                />
                <Field
                  disabled={pending}
                  label="Budget"
                  name="budget"
                  type="number"
                  value={values.budget}
                  onChange={update("budget")}
                  error={errors?.budget}
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="1500"
                />
                <Field
                  disabled={pending}
                  label="Currency"
                  name="currency"
                  value={values.currency}
                  onChange={update("currency")}
                  error={errors?.currency}
                >
                  {["IDR", "USD"].map((currency) => (
                    <option key={currency}>{currency}</option>
                  ))}
                </Field>
                <Field
                  disabled={pending}
                  label="Travel month"
                  name="travel_month"
                  value={values.travel_month}
                  onChange={update("travel_month")}
                  error={errors?.travel_month}
                >
                  {months.map((month) => (
                    <option key={month}>{month}</option>
                  ))}
                </Field>
              </div>

              <button
                disabled={pending}
                className="min-h-12 w-full rounded-xl bg-teal-700 px-5 font-bold text-white shadow-sm transition hover:bg-teal-800 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60"
              >
                {pending
                  ? "Generating your itinerary..."
                  : "✨ Generate AI Itinerary"}
              </button>

              {pending && (
                <div
                  className="motion-safe:animate-pulse rounded-xl bg-slate-100 p-4 text-center text-sm font-semibold text-slate-700 motion-reduce:animate-none"
                  aria-live="polite"
                >
                  Generating your itinerary...
                </div>
              )}

              {state?.ok === false && (
                <div
                  className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900"
                  role="alert"
                >
                  <p className="font-bold">{state.message}</p>
                  {state.kind !== "validation" && (
                    <button
                      disabled={pending}
                      formAction={formAction}
                      className="mt-3 font-bold underline underline-offset-4"
                    >
                      Try again
                    </button>
                  )}
                </div>
              )}
            </form>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-20">
          {state?.ok ? (
            <Results trip={state.trip} />
          ) : (
            !pending && (
              <div className="rounded-3xl border border-dashed border-slate-300 bg-white/60 px-6 py-12 text-center">
                <h2 className="text-2xl font-bold text-slate-950">
                  Your next good idea starts here.
                </h2>
                <p className="mx-auto mt-3 max-w-[65ch] text-slate-600">
                  Complete the form above and your trip summary will appear in
                  this space.
                </p>
              </div>
            )
          )}
        </section>
      </main>

      <footer
        id="about"
        className="border-t border-slate-200 bg-slate-950 text-slate-300"
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-5 px-5 py-10 text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
          <div>
            <p className="font-bold text-white">KelanaAI</p>
            <p className="mt-1 text-sm">
              AI-Powered Indonesian &amp; Global Travel Planner
            </p>
          </div>
          <nav
            className="flex justify-center gap-5 text-sm"
            aria-label="Footer"
          >
            <a href="#planner" className="hover:text-white">
              Plan a trip
            </a>
            <a href="#top" className="hover:text-white">
              Back to top
            </a>
          </nav>
          <p className="text-sm">© 2026 KelanaAI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

