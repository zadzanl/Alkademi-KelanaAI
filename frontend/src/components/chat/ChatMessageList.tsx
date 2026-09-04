"use client";

import { useEffect, useRef } from "react";
import type { Message } from "../../types/chat.ts";
import type { LocalUserMessage } from "../../lib/chatState.ts";
import { ChatMessageItem } from "./ChatMessageItem.tsx";
import { TypingIndicator } from "./TypingIndicator.tsx";

interface ChatMessageListProps {
  messages: Array<Message | LocalUserMessage>;
  isLoading?: boolean;
  onRecoverMessage?: (message: LocalUserMessage) => void;
}

export function ChatMessageList({ messages, isLoading, onRecoverMessage }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
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
            <span className="px-2.5 py-1 bg-ink/5 rounded-full border border-rule">&ldquo;Plan a 4-day trip to Yogyakarta&rdquo;</span>
            <span className="px-2.5 py-1 bg-ink/5 rounded-full border border-rule">&ldquo;What to pack for Mount Bromo?&rdquo;</span>
            <span className="px-2.5 py-1 bg-ink/5 rounded-full border border-rule">&ldquo;Best budget street food in Bandung&rdquo;</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
      <div className="max-w-4xl mx-auto">
        {messages.map((message) => (
          <ChatMessageItem
            key={"kind" in message ? message.localId : `server-${message.id}`}
            message={message}
            onRecover={onRecoverMessage}
          />
        ))}
        {isLoading && (
          <div className="mb-4">
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
