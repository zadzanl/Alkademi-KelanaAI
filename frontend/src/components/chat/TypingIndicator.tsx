export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3 max-w-[120px] bg-paper-surface border border-surface-rule rounded-surface shadow-xs text-ink/70">
      <span className="text-xs font-serif italic text-ink/60 mr-1">Thinking</span>
      <span aria-hidden="true" className="w-1.5 h-1.5 bg-terracotta rounded-full animate-bounce [animation-delay:-0.3s] motion-reduce:animate-none" />
      <span aria-hidden="true" className="w-1.5 h-1.5 bg-terracotta rounded-full animate-bounce [animation-delay:-0.15s] motion-reduce:animate-none" />
      <span aria-hidden="true" className="w-1.5 h-1.5 bg-terracotta rounded-full animate-bounce motion-reduce:animate-none" />
    </div>
  );
}
