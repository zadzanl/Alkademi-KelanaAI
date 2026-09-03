import type { TripRequest } from "./trip.ts";

export type ComparisonStatus = "success" | "error_rate_limited" | "error_timeout" | "error_provider";
export type DocumentCitation = {
	source_type: "document"; document_name: string; document_id: string;
	score: number; excerpt: string;
};
export type WebCitation = {
	source_type: "web_search"; title: string; url: string; score: number;
	excerpt: string; published_date: string | null;
};
export type CitationItem = DocumentCitation | WebCitation;
export type RagComparisonMetrics = {
	raw_generation_ms: number; rag_generation_ms: number;
	bedrock_retrieval_ms: number; exa_retrieval_ms: number;
	total_retrieval_ms: number; total_elapsed_ms: number;
	chunks_retrieved_count: number; highlights_retrieved_count: number;
	provider_used: string | null;
};
export type RagComparisonResponse = {
	raw_recommendation: string | null; raw_status: ComparisonStatus;
	rag_recommendation: string | null; rag_status: ComparisonStatus;
	retrieved_citations: CitationItem[]; metrics: RagComparisonMetrics;
};
export type CompareRagAction = (body: TripRequest) =>
	Promise<RagComparisonResponse | { error: string }>;