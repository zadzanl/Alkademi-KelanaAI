"use client";

import Image from "next/image";
import Link from "next/link";
import { useActionState, useEffect, useRef, useState } from "react";
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
  "mt-2 min-h-12 w-full rounded-surface border border-control bg-paper-light px-4 text-base text-ink outline-none transition-colors duration-150 focus-visible:border-terracotta focus-visible:outline-focus-ring disabled:cursor-wait disabled:bg-paper disabled:text-muted-ink";

const sampleFormValues: FormValues = {
  destination: "Yogyakarta", country: "Indonesia", days: "5",
  budget: "2500", currency: "IDR", travel_month: "December",
};

function PendingSkeleton() {
  return <div aria-hidden="true" className="space-y-5 border-y border-surface-rule py-8 motion-safe:animate-pulse motion-reduce:animate-none"><div className="h-8 w-2/3 bg-rule/50 rounded-surface" /><div className="h-4 w-full bg-rule/40 rounded-surface" /><div className="h-4 w-5/6 bg-rule/40 rounded-surface" /><div className="grid gap-4 sm:grid-cols-3"><div className="h-20 bg-rule/40 rounded-surface" /><div className="h-20 bg-rule/40 rounded-surface" /><div className="h-20 bg-rule/40 rounded-surface" /></div></div>;
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
  const [slide, setSlide] = useState(0);
  const [isCarouselPaused, setIsCarouselPaused] = useState(false);
  const [isWaitingCancelled, setIsWaitingCancelled] = useState(false);
  const [waitStage, setWaitStage] = useState(0);
  const resultRef = useRef<HTMLDivElement>(null);
  const stopWaitingRef = useRef<HTMLButtonElement>(null);
  const wasCancelledRef = useRef(false);
  const [state, formAction, pending] = useActionState<
    ActionState | null,
    FormData
  >(createTrip, null);

  useEffect(() => {
    if (!pending) {
      setIsWaitingCancelled(false);
      setWaitStage(0);
    }
  }, [pending]);

  useEffect(() => {
    if (!pending || isWaitingCancelled) return;
    const timer = window.setInterval(() => setWaitStage((stage) => Math.min(stage + 1, 3)), 6000);
    return () => window.clearInterval(timer);
  }, [pending, isWaitingCancelled]);

  useEffect(() => {
    if (wasCancelledRef.current && !isWaitingCancelled && pending) {
      stopWaitingRef.current?.focus();
    }
    wasCancelledRef.current = isWaitingCancelled;
  }, [isWaitingCancelled, pending]);

  useEffect(() => {
    if (state?.ok && !pending) {
      if (!wasCancelledRef.current) {
        const prefersReducedMotion =
          typeof window !== "undefined" &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        resultRef.current?.scrollIntoView(
          prefersReducedMotion ? undefined : { behavior: "smooth" }
        );
      }
    }
  }, [state, pending]);

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
      <main id="main-content">
        <div id="top" />
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

          <div className="rounded-surface border border-surface-rule bg-paper-light px-5 py-7 sm:px-8 sm:py-9">
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
                className="min-h-12 w-full rounded-surface bg-terracotta px-5 font-bold text-white transition-colors duration-150 hover:bg-terracotta-dark focus-visible:outline-focus-ring disabled:cursor-wait disabled:bg-control disabled:text-white"
              >
                {pending
                  ? isWaitingCancelled
                    ? "Generating in background…"
                    : "Generating your itinerary…"
                  : "Plan my trip"}
              </button>

              {pending && !isWaitingCancelled && (
                <div
                  className="rounded-surface border border-surface-rule bg-indigo-light p-4 text-center text-sm font-semibold text-indigo space-y-2"
                  role="status"
                  aria-live="polite"
                >
                  <div
                    className="h-2 overflow-hidden rounded-full bg-paper/70"
                    role="progressbar"
                    aria-label="Trip generation progress"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.min(92, (waitStage + 1) * 23)}
                  >
                    <div
                      className="h-full rounded-full bg-terracotta transition-[width] duration-500 motion-reduce:transition-none"
                      style={{ width: `${Math.min(92, (waitStage + 1) * 23)}%` }}
                    />
                  </div>
                  <p>{[
                    `Reading your ${values.days}-day ${values.destination || "trip"} brief…`,
                    `Considering ${values.travel_month} season and your ${values.currency} budget…`,
                    "Checking useful travel knowledge when available…",
                    "Writing your trip snapshot…",
                  ][waitStage]}</p>
                  <p className="text-xs font-normal text-muted-ink">
                    Stage {waitStage + 1} of 4 · This is a progress estimate, may not reflect real progress.
                  </p>
                  <button
                    ref={stopWaitingRef}
                    type="button"
                    onClick={() => setIsWaitingCancelled(true)}
                    className="mt-2 inline-flex items-center text-xs font-medium text-muted-ink hover:text-ink underline focus-visible:outline-focus-ring"
                  >
                    Stop showing progress
                  </button>
                </div>
              )}

              {pending && isWaitingCancelled && (
                <div
                  className="rounded-surface border border-surface-rule bg-paper-light p-4 text-center text-sm text-muted-ink space-y-2"
                  role="status"
                  aria-live="polite"
                >
                  <p className="font-semibold text-ink">Stopped waiting for this response.</p>
                  <p className="text-xs">If the server request finishes in the background, your itinerary may still be saved under My Trips.</p>
                  <button
                    type="button"
                    autoFocus
                    onClick={() => setIsWaitingCancelled(false)}
                    className="mt-1 text-xs font-semibold text-terracotta-dark hover:underline focus-visible:outline-focus-ring"
                  >
                    Resume waiting
                  </button>
                </div>
              )}

              {state?.ok === false && (
                <div
                  className="rounded-surface border border-error bg-paper p-4 text-error"
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

        <section aria-label="Trip output" className="mx-auto max-w-6xl px-5 pb-24 sm:px-8" ref={resultRef}>
          {state?.ok && !pending ? (
            <div>
              <div
                role="status"
                aria-live="polite"
                className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-surface border border-emerald-600/30 bg-emerald-50/80 p-4 text-sm font-semibold text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
              >
                <div className="flex items-center gap-2">
                  <span aria-hidden="true" className="text-base font-bold text-emerald-600 dark:text-emerald-400">✓</span>
                  <span>Itinerary created and saved to My Trips</span>
                </div>
                <Link
                  href="/trips"
                  className="inline-flex min-h-[44px] items-center text-xs font-bold text-emerald-800 underline transition-colors hover:text-ink dark:text-emerald-300"
                >
                  View saved trips →
                </Link>
              </div>
              <TripDetailView
                trip={state.trip}
                headingLevel="h2"
                showBackLink={false}
              />
            </div>
          ) : (
            pending ? <PendingSkeleton /> : (
              <div className="grid gap-8 border-y border-surface-rule py-10 md:grid-cols-[0.35fr_1fr] md:py-14">
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

