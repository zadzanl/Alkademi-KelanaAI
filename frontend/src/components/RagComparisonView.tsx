"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { markdownComponents } from "../lib/markdownPolicy.ts";
import type { CompareRagAction, RagComparisonResponse } from "../types/knowledge.ts";
import type { TripRequest } from "../types/trip.ts";
import { CitationList } from "./CitationList.tsx";

type ComparisonKind = "raw" | "rag";
const labels = { raw: "Base model", rag: "Knowledge-enhanced" } as const;

function RecommendationColumn({ kind, result, activeTab, onRetry }: { kind: ComparisonKind; result: RagComparisonResponse; activeTab: ComparisonKind; onRetry: () => void }) {
  const recommendation = kind === "raw" ? result.raw_recommendation : result.rag_recommendation;
  const status = kind === "raw" ? result.raw_status : result.rag_status;

  return (
    <section className={kind === activeTab ? "block" : "hidden lg:block"} aria-labelledby={`${kind}-comparison-heading`}>
      <h3 id={`${kind}-comparison-heading`} className="font-display text-3xl text-ink">{labels[kind]}</h3>
      {recommendation ? (
        <div className="prose prose-sm mt-5 max-w-none text-ink">
          <ReactMarkdown components={markdownComponents("h4")}>{recommendation}</ReactMarkdown>
        </div>
      ) : (
        <div className="mt-5 rounded-surface border border-error bg-paper p-4 text-sm text-error" role="alert">
          {status === "error_rate_limited" ? "RAG generation was rate limited." : "This column could not be generated."}
          <button type="button" onClick={onRetry} className="mt-3 block font-bold underline focus-visible:outline-focus-ring">Retry {kind === "raw" ? "base" : "RAG"} generation</button>
        </div>
      )}
    </section>
  );
}

export function RagComparisonView({ request, action }: { request: TripRequest; action: CompareRagAction }) {
  const [result, setResult] = useState<RagComparisonResponse | null>(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<ComparisonKind>("rag");
  const [pending, setPending] = useState(false);

  const runComparison = async () => {
    setPending(true);
    setError("");
    const value = await action(request);
    if ("error" in value) setError(value.error);
    else setResult(value);
    setPending(false);
  };

  return (
    <section className="mt-12 border-t border-surface-rule pt-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-terracotta-dark">Evaluation</p>
          <h2 className="font-display text-4xl text-ink">Base model or grounded context?</h2>
        </div>
        <button
          type="button"
          disabled={pending}
          onClick={runComparison}
          className="min-h-12 rounded-surface bg-indigo px-5 font-bold text-white transition-colors hover:bg-ink focus-visible:outline-focus-ring disabled:cursor-wait disabled:opacity-50"
        >
          {pending ? "Comparing approaches…" : "Compare approaches"}
        </button>
      </div>
      {pending && (
        <div
          className="mt-6 rounded-surface border border-surface-rule bg-paper-light p-6 text-center space-y-2 motion-safe:animate-pulse"
          role="status"
          aria-live="polite"
        >
          <p className="font-semibold text-sm text-ink">Comparing base model and knowledge-enhanced recommendations…</p>
          <p className="text-xs text-muted-ink">
            Evaluating prompt retrieval and running dual inference (may take up to 60 seconds).
          </p>
        </div>
      )}
      {error && <p className="mt-4 rounded-surface border border-error bg-paper p-4 text-error" role="alert">{error}</p>}
      {result && (
        <>
          <div className="mt-8 flex gap-2 border-b border-surface-rule lg:hidden">
            {(Object.keys(labels) as ComparisonKind[]).map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => setActiveTab(kind)}
                className={`px-3 py-3 font-bold focus-visible:outline-focus-ring ${activeTab === kind ? "border-b-2 border-terracotta text-ink" : "text-muted-ink hover:text-ink"}`}
              >
                {kind === "raw" ? "Base model" : "Grounded"}
              </button>
            ))}
          </div>
          <div className="mt-8 grid gap-10 lg:grid-cols-2">
            <RecommendationColumn kind="raw" result={result} activeTab={activeTab} onRetry={runComparison} />
            <RecommendationColumn kind="rag" result={result} activeTab={activeTab} onRetry={runComparison} />
          </div>
          <CitationList citations={result.retrieved_citations} />
        </>
      )}
    </section>
  );
}