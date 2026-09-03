import { createElement, type ElementType, type ReactNode } from "react";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { safeUrl } from "./safety.ts";

export const markdownPlugins = [remarkGfm];

/**
 * Repairs tables flattened by upstream text generation. Markdown tables need
 * a newline between rows; this only changes pipe-adjacent boundaries inside a
 * table-shaped block and leaves ordinary prose untouched.
 */
export function normalizeMarkdownTables(markdown: string): string {
  return markdown.replace(
    /(^|\n)(\s*\|[^\n]*\|\s+\|\s*-{3,}[^\n]*)(?=\s*\|)/g,
    (_, prefix: string, table: string) =>
      `${prefix}${table.replace(/\|\s+\|/g, "|\n|")}`,
  );
}

/**
 * Builds the production Markdown render policy. `HeadingTag` must be a heading
 * element subordinate to the page title; Markdown h1/h2 nodes are remapped to
 * preserve one coherent document outline for both embedded and detail views.
 */
export function markdownComponents(HeadingTag: ElementType): Components {
  return {
    h1: ({ children }) =>
      createElement(
        HeadingTag,
        { className: "font-display mt-8 text-2xl leading-tight text-ink" },
        children,
      ),
    h2: ({ children }) =>
      createElement(
        HeadingTag,
        { className: "font-display mt-8 text-2xl leading-tight text-ink" },
        children,
      ),
    a: ({ href, children }) => {
      const safe = href ? safeUrl(href) : undefined;
      return safe
        ? createElement(
            "a",
            {
              href: safe,
              target: "_blank",
              rel: "noopener noreferrer",
              className: "underline hover:text-terracotta-dark",
            },
            children,
          )
        : createElement("span", null, children as ReactNode);
    },
    img: ({ src, alt }) => {
      const safe = typeof src === "string" ? safeUrl(src, true) : undefined;
      return safe
        ? createElement("img", {
            src: safe,
            alt: alt ?? "",
            loading: "lazy",
            className: "rounded-[4px]",
          })
        : null;
    },
  };
}