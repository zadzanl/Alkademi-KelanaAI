"use client";

import { useEffect, useRef } from "react";
import type { Message } from "../../types/chat.ts";
import type { LocalUserMessage } from "../../lib/chatState.ts";
import { ChatMessageItem } from "./ChatMessageItem.tsx";
import { TypingIndicator } from "./TypingIndicator.tsx";

const suggestions = [
  "Plan a 4-day trip to Yogyakarta",
  "What to pack for Mount Bromo?",
  "Best budget street food in Bandung",
];

interface ChatMessageListProps {
  messages: Array<Message | LocalUserMessage>;
  isLoading?: boolean;
  onRecoverMessage?: (message: LocalUserMessage) => void;
  onSelectSuggestion?: (content: string) => void;
}

export function ChatMessageList({ messages, isLoading, onRecoverMessage, onSelectSuggestion }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = listRef.current;
    const nearBottom = !list || list.scrollHeight - list.scrollTop - list.clientHeight < 160;
    if (!nearBottom) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) bottomRef.current?.scrollIntoView();
    else bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-ink/60">
        <div className="max-w-md">
          <h3 className="font-display text-2xl text-ink mb-2">Welcome to KelanaAI Assistant</h3>
          <p className="text-sm text-ink/70 leading-relaxed mb-4">
            I can help you build custom itineraries, answer questions about destinations, suggest transport routes, and recommend authentic local experiences.
          </p>
          <div className="flex flex-wrap justify-center gap-2 text-xs">
            {suggestions.map((text) => (
              <button
                key={text}
                type="button"
                disabled={isLoading}
                onClick={() => onSelectSuggestion?.(text)}
                className="px-2.5 py-1 bg-ink/5 hover:bg-ink/10 text-ink rounded-full border border-surface-rule transition-colors cursor-pointer text-xs focus-visible:outline-focus-ring disabled:opacity-50 disabled:cursor-not-allowed"
              >
                &ldquo;{text}&rdquo;
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={listRef} role="log" aria-label="Conversation messages" aria-live="off" className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
      <div className="max-w-4xl mx-auto">
        {messages.map((message) => (
          <ChatMessageItem
            key={"kind" in message ? message.localId : `server-${message.id}`}
            message={message}
            onRecover={onRecoverMessage}
          />
        ))}
        {isLoading && (
          <div className="mb-4" role="status" aria-label="Assistant is thinking">
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
