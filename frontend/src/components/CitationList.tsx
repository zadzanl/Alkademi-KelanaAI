import type { CitationItem } from "../types/knowledge.ts";
import { safeUrl } from "../lib/safety.ts";

export function CitationList({ citations }: { citations: CitationItem[] }) {
  if (!citations.length) return null;
  return (
    <section aria-labelledby="citation-heading" className="mt-10 border-t border-ink pt-5">
      <h3 id="citation-heading" className="font-display text-3xl text-ink">Sources behind the comparison</h3>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {citations.map((citation, index) => (
          <CitationCard key={`${citation.source_type}-${index}`} citation={citation} />
        ))}
      </div>
    </section>
  );
}

function CitationCard({ citation }: { citation: CitationItem }) {
  const relevance = `Relevance ${(citation.score * 100).toFixed(0)}%`;
  if (citation.source_type === "document") {
    return <article className="border border-indigo/30 bg-indigo-light p-5"><p className="text-xs font-bold uppercase tracking-wide text-indigo">Verified guidebook</p><h4 className="mt-2 font-bold text-ink">{citation.document_name}</h4><p className="mt-2 text-xs text-muted-ink">{relevance}</p><blockquote className="mt-3 border-l-2 border-indigo pl-3 text-sm text-muted-ink">{citation.excerpt}</blockquote></article>;
  }

  const sourceUrl = safeUrl(citation.url);
  return <article className="border border-terracotta/30 bg-paper-light p-5"><p className="text-xs font-bold uppercase tracking-wide text-terracotta-dark">Live web search</p><h4 className="mt-2 font-bold text-ink">{citation.title}</h4>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm underline hover:text-terracotta-dark">Open source ↗</a>}<p className="mt-2 text-xs text-muted-ink">{relevance}{citation.published_date ? ` · ${citation.published_date}` : ""}</p><blockquote className="mt-3 border-l-2 border-terracotta pl-3 text-sm text-muted-ink">{citation.excerpt}</blockquote></article>;
}