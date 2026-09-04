"use client";

import ReactMarkdown from "react-markdown";
import { markdownComponents, markdownPlugins, normalizeMarkdownTables } from "../../lib/markdownPolicy.ts";
import type { Message } from "../../types/chat.ts";
import type { LocalUserMessage } from "../../lib/chatState.ts";

interface ChatMessageItemProps {
  message: Message | LocalUserMessage;
  onRecover?: (message: LocalUserMessage) => void;
}

export function ChatMessageItem({ message, onRecover }: ChatMessageItemProps) {
  const isUser = message.role === "user";
  const isLocal = "kind" in message;
  const formattedTime = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} mb-4`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] px-4 py-3 rounded-[6px] text-sm leading-relaxed border ${
          isUser
            ? "bg-terracotta/10 border-terracotta/30 text-ink"
            : "bg-paper-surface border-rule text-ink shadow-xs"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="journal-prose prose prose-sm max-w-none prose-headings:font-display prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5">
            <ReactMarkdown
              remarkPlugins={markdownPlugins}
              components={markdownComponents("h4")}
            >
              {normalizeMarkdownTables(message.content)}
            </ReactMarkdown>
          </div>
        )}
      </div>
      <span className="text-[11px] text-ink/40 mt-1 px-1 font-mono">{formattedTime}</span>
      {isLocal && (
        <div className={`mt-1 px-1 text-xs ${message.status === "failed" ? "text-error" : "text-muted-ink"}`}>
          <span>{message.statusText}</span>
          {message.recovery && onRecover && (
            <button
              type="button"
              onClick={() => onRecover(message)}
              className="ml-2 font-semibold text-terracotta-dark hover:underline"
            >
              {message.recovery === "retry" ? "Retry" : message.recovery === "check" ? "Check again" : "Refresh"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
