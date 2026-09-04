"use client";

import { useRef, KeyboardEvent } from "react";

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  content: string;
  onContentChange: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, content, onContentChange, disabled }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = content.trim();
    if (!trimmed || disabled) return;
    onSendMessage(trimmed);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onContentChange(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="border-t border-stone-200 bg-paper-surface p-4">
      <div className="max-w-4xl mx-auto flex items-end gap-2 bg-paper-surface border border-rule rounded-[6px] p-2 focus-within:border-terracotta transition-colors shadow-xs">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask KelanaAI travel assistant... (Shift + Enter for new line)"
          disabled={disabled}
          rows={1}
          className="flex-1 max-h-40 resize-none bg-transparent px-2 py-1.5 text-sm text-ink outline-none placeholder:text-ink/40 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || !content.trim()}
          className="inline-flex items-center justify-center px-4 py-2 text-xs font-semibold text-white bg-terracotta hover:bg-terracotta-dark disabled:opacity-40 disabled:cursor-not-allowed rounded-[4px] transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
