"use client";

import Image from "next/image";
import Link from "next/link";
import { useActionState, useEffect, useState } from "react";
import { createTrip } from "./actions";
import { landmarks } from "./landmarks";
import { TripDetailView } from "../components/TripDetailView";
import {
  initialForm,
  months,
  type ActionState,
  type FormValues,
} from "./types";

const inputClass =
  "mt-2 min-h-12 w-full rounded-[4px] border border-control bg-paper-light px-4 text-base text-ink outline-none transition-colors duration-150 focus-visible:border-indigo focus-visible:outline-indigo disabled:cursor-wait disabled:bg-paper disabled:text-muted-ink";

const sampleFormValues: FormValues = {
  destination: "Kyoto", country: "Japan", days: "5",
  budget: "1500", currency: "USD", travel_month: "December",
};

function PendingSkeleton() {
  return <div aria-hidden="true" className="space-y-5 border-y border-rule py-8 motion-safe:animate-pulse motion-reduce:animate-none"><div className="h-8 w-2/3 bg-rule/50" /><div className="h-4 w-full bg-rule/40" /><div className="h-4 w-5/6 bg-rule/40" /><div className="grid gap-4 sm:grid-cols-3"><div className="h-20 bg-rule/40" /><div className="h-20 bg-rule/40" /><div className="h-20 bg-rule/40" /></div></div>;
}

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
      <label htmlFor={id} className="font-semibold text-ink">
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
          className="mt-2 text-sm font-semibold text-error"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}

function CarouselButton({
  direction,
  onClick,
}: {
  direction: "previous" | "next";
  onClick: () => void;
}) {
  const isPrevious = direction === "previous";
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-10 w-10 items-center justify-center rounded-full border border-white/50 bg-black/35 text-white transition-colors hover:bg-black/65 focus-visible:outline-white"
      aria-label={`${isPrevious ? "Previous" : "Next"} landmark`}
    >
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d={isPrevious ? "m15 19-7-7 7-7" : "m9 5 7 7-7 7"} />
      </svg>
    </button>
  );
}

export default function Home() {
  const [values, setValues] = useState<FormValues>(initialForm);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [slide, setSlide] = useState(0);
  const [isCarouselPaused, setIsCarouselPaused] = useState(false);
  const [state, formAction, pending] = useActionState<
    ActionState | null,
    FormData
  >(createTrip, null);

  useEffect(() => {
    const current = (document.documentElement.getAttribute("data-theme") as "light" | "dark") || "light";
    setTheme(current);
  }, []);

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("kelana_theme", next);
    } catch {}
  };

  useEffect(() => {
    if (state?.submitted) {
      setValues(state.submitted);
    }
  }, [state]);

  const update = (name: keyof FormValues) => (value: string) =>
    setValues((current) => ({ ...current, [name]: value }));
  const errors = state?.ok === false ? state.fieldErrors : undefined;
  const fillExample = () => setValues(sampleFormValues);
  const activeLandmark = landmarks[slide];
  const moveSlide = (direction: 1 | -1) => {
    setSlide((current) => (current + direction + landmarks.length) % landmarks.length);
  };

  useEffect(() => {
    if (isCarouselPaused) return;
    const timer = window.setInterval(() => moveSlide(1), 6000);
    return () => window.clearInterval(timer);
  }, [isCarouselPaused]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-rule bg-paper">
        <nav className="mx-auto flex max-w-[90rem] items-center justify-between px-5 py-5 sm:px-8" aria-label="Primary">
          <a href="#top" className="font-display text-2xl text-ink hover:text-terracotta-dark">
            Kelana<span className="text-terracotta-dark">AI</span>
          </a>
          <div className="flex shrink-0 items-center gap-4 sm:gap-7 text-sm font-semibold">
            <a href="#planner" className="border-b border-terracotta pb-1 text-ink hover:text-terracotta-dark">Plan a trip</a>
            <Link href="/trips" className="text-muted-ink hover:text-ink transition-colors">My Trips</Link>
            <a href="#about" className="hidden text-muted-ink hover:text-ink sm:inline">About</a>
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
              className="flex items-center gap-1.5 rounded-full border border-rule bg-paper-light px-3 py-1.5 text-xs font-semibold text-ink transition-colors hover:border-control hover:text-terracotta-dark"
            >
              {theme === "light" ? (
                <>
                  <svg className="h-3.5 w-3.5 text-terracotta" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                  <span>Dark</span>
                </>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5 text-terracotta-dark" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                  <span>Light</span>
                </>
              )}
            </button>
          </div>
        </nav>
      </header>

      <main id="top">
        <section
          className="journal-reveal relative isolate mx-auto min-h-[42rem] min-w-0 max-w-[90rem] overflow-hidden px-5 py-12 sm:px-8 sm:py-16 lg:min-h-[48rem] lg:py-24"
          onMouseEnter={() => setIsCarouselPaused(true)}
          onMouseLeave={() => setIsCarouselPaused(false)}
          onFocusCapture={() => setIsCarouselPaused(true)}
          onBlurCapture={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) setIsCarouselPaused(false);
          }}
          aria-roledescription="carousel"
          aria-label="Landmark inspiration"
        >
          {landmarks.map((landmark, index) => (
            <Image
              key={landmark.key}
              src={landmark.src}
              alt={index === slide ? landmark.alt : ""}
              fill
              priority={index === 0}
              sizes="(min-width: 1440px) 1440px, 100vw"
              style={{ objectPosition: landmark.objectPosition }}
              className={`-z-20 object-cover transition-opacity duration-1000 motion-reduce:transition-none ${index === slide ? "opacity-100" : "opacity-0"}`}
              aria-hidden={index !== slide}
            />
          ))}
          <div className="absolute inset-0 -z-10 bg-black/60" aria-hidden="true" />
          <div className="relative flex min-h-[36rem] items-center sm:min-h-[38rem] lg:min-h-[40rem]">
            <div className="max-w-2xl bg-indigo px-6 py-10 text-white sm:px-10 sm:py-14 lg:px-12 lg:py-16">
              <h1 className="font-display max-w-[11ch] text-[clamp(3.25rem,7vw,5.5rem)] leading-[0.91] tracking-[-0.03em]">
                Go farther with a plan that feels like you.
              </h1>
              <p className="mt-7 max-w-[55ch] text-lg leading-8 text-slate-200 sm:text-xl">
                Tell KelanaAI where you want to go, and get a grounded trip
                snapshot for your next adventure.
              </p>
              <a href="#planner" className="mt-9 inline-block min-h-12 border-b border-white py-3 font-bold text-white hover:text-slate-200">Plan a trip</a>
            </div>
          </div>
          <p className="absolute inset-x-5 bottom-3 z-10 flex flex-wrap justify-between gap-x-4 gap-y-1 bg-black/80 px-4 py-3 text-xs text-white sm:inset-x-8 lg:bottom-8">
            <span>{activeLandmark.caption}</span>
            <span>
              {activeLandmark.credit}{" · "}
              <a href={activeLandmark.source} className="underline hover:text-white" rel="noreferrer">Source</a>
              {" · "}
              <a href={activeLandmark.licenseUrl} className="underline hover:text-white" rel="noreferrer">{activeLandmark.license}</a>
              {" · "}{activeLandmark.modification}
            </span>
          </p>
          <div className="absolute inset-x-5 bottom-24 z-10 flex items-center justify-between sm:inset-x-8">
            <CarouselButton direction="previous" onClick={() => moveSlide(-1)} />
            <div className="flex items-center gap-2" role="tablist" aria-label="Choose landmark">
              {landmarks.map((landmark, index) => (
                <button key={landmark.key} type="button" role="tab" aria-selected={index === slide} aria-label={`Show ${landmark.label}`} onClick={() => setSlide(index)} className={`h-2 w-2 rounded-full border border-white/80 transition-all ${index === slide ? "scale-125 bg-white" : "bg-white/35 hover:bg-white/70"}`} />
              ))}
            </div>
            <CarouselButton direction="next" onClick={() => moveSlide(1)} />
          </div>
        </section>

        <section
          id="planner"
          aria-labelledby="planner-heading"
          className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.68fr_1.32fr] lg:gap-20 lg:py-24"
        >
          <div>
            <h2 id="planner-heading" className="font-display text-4xl leading-[1.02] text-ink sm:text-5xl">
              Build your trip snapshot
            </h2>
            <p className="mt-6 max-w-[48ch] text-lg leading-8 text-muted-ink">
              A few details are enough to shape a useful first direction. You
              can adjust the plan later.
            </p>
            <button type="button" disabled={pending} onClick={fillExample} className="mt-6 min-h-12 border-b border-terracotta font-bold text-terracotta-dark disabled:opacity-50">Try an example</button>
          </div>

          <div className="border-t border-ink bg-paper-light px-5 py-7 sm:px-8 sm:py-9">
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
                className="min-h-12 w-full rounded-[4px] bg-terracotta px-5 font-bold text-white transition-colors duration-150 hover:bg-terracotta-dark focus-visible:outline-indigo disabled:cursor-wait disabled:bg-control disabled:text-white"
              >
                {pending ? "Generating your itinerary..." : "Plan my trip"}
              </button>

              {pending && (
                <div
                  className="border-y border-control bg-indigo-light p-4 text-center text-sm font-semibold text-indigo"
                  aria-live="polite"
                >
                  Generating your itinerary...
                </div>
              )}

              {state?.ok === false && (
                <div
                  className="border-y border-error bg-paper p-4 text-error"
                  role="alert"
                >
                  <p className="font-bold">{state.message}</p>
                  {state.kind === "unauthorized" ? (
                    <Link
                      href="/auth"
                      className="mt-3 inline-block min-h-12 font-bold underline underline-offset-4"
                    >
                      Sign in to KelanaAI
                    </Link>
                  ) : state.kind !== "validation" && (
                    <button
                      disabled={pending}
                      formAction={formAction}
                      className="mt-3 min-h-12 font-bold underline underline-offset-4"
                    >
                      Try again
                    </button>
                  )}
                </div>
              )}
            </form>
          </div>
        </section>

        <section aria-label="Trip output" className="mx-auto max-w-6xl px-5 pb-24 sm:px-8">
          {state?.ok && !pending ? (
            <TripDetailView
              trip={state.trip}
              headingLevel="h2"
              showBackLink={false}
            />
          ) : (
            pending ? <PendingSkeleton /> : (
              <div className="grid gap-8 border-y border-ink py-10 md:grid-cols-[0.35fr_1fr] md:py-14">
                <p className="tabular text-sm font-semibold text-terracotta-dark" aria-hidden="true">02</p>
                <div>
                <h2 className="font-display text-3xl leading-tight text-ink sm:text-4xl">
                  Your trip snapshot will appear here.
                </h2>
                <p className="mt-5 max-w-[65ch] text-lg leading-8 text-muted-ink">
                  You’ll receive a travel style, daily budget, season, transportation, suggested places, and an AI narrative when available.
                </p>
                </div>
              </div>
            )
          )}
        </section>
      </main>

      <footer
        id="about"
        className="bg-indigo text-slate-300"
      >
        <div className="mx-auto grid max-w-[90rem] gap-8 px-5 py-12 sm:px-8 md:grid-cols-[1fr_auto_auto] md:items-end">
          <div>
            <p className="font-display text-3xl text-white">KelanaAI</p>
            <p className="mt-2 text-sm">
              AI-Powered Indonesian &amp; Global Travel Planner
            </p>
          </div>
          <nav
            className="flex gap-5 text-sm"
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

