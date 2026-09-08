"use client";

import { useState } from "react";
import type { Conversation } from "../../types/chat.ts";

interface ChatSidebarProps {
  conversations: Conversation[];
  activeConversationId: number | null;
  onSelectConversation: (id: number) => void;
  onNewChat: () => void;
  onRenameConversation: (id: number, newTitle: string) => Promise<{ ok: boolean; error?: string }>;
  mobileOpen?: boolean;
  onClose?: () => void;
  isLoadingHistory?: boolean;
  isCreatingChat?: boolean;
}

export function ChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onRenameConversation,
  mobileOpen = false,
  onClose,
  isLoadingHistory = false,
  isCreatingChat = false,
}: ChatSidebarProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isSavingRename, setIsSavingRename] = useState(false);

  const startRename = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
    setRenameError(null);
  };

  const handleSaveRename = async (id: number, e: React.FormEvent) => {
    e.preventDefault();
    if (!editTitle.trim() || isSavingRename) return;
    setIsSavingRename(true);
    try {
      const result = await onRenameConversation(id, editTitle.trim());
      if (result.ok) {
        setEditingId(null);
        setRenameError(null);
      } else {
        setRenameError(result.error || "Failed to rename conversation.");
      }
    } finally {
      setIsSavingRename(false);
    }
  };

  return (
    <aside aria-label="Conversation history" className={`${mobileOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-40 w-[min(88vw,18rem)] bg-paper border-r border-surface-rule flex flex-col h-full select-none transition-transform md:static md:z-auto md:w-72 md:translate-x-0`}>
      <div className="p-4 border-b border-surface-rule flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg text-ink font-semibold">Conversations</h2>
          <p className="text-xs text-ink/50">Travel Assistant</p>
        </div>
        <button
          type="button"
          disabled={isCreatingChat}
          aria-busy={isCreatingChat}
          onClick={() => { onNewChat(); onClose?.(); }}
          aria-label="Start a new chat"
          className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-semibold text-white bg-terracotta hover:bg-terracotta-dark rounded-surface transition-colors shadow-xs disabled:cursor-wait disabled:opacity-60 focus-visible:outline-focus-ring"
        >
          {isCreatingChat ? "Creating…" : "+ New Chat"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoadingHistory ? (
          <div className="p-4 text-center text-xs text-muted-ink" role="status">Loading conversations…</div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-xs text-ink/40 italic">
            No conversations yet. Start a new chat!
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const isEditing = conv.id === editingId;

            return (
              <div
                key={conv.id}
                className={`group flex items-center justify-between p-2.5 rounded-surface cursor-pointer text-sm transition-colors ${
                  isActive
                    ? "bg-terracotta/10 border border-terracotta/30 text-ink font-medium"
                    : "hover:bg-ink/5 text-ink/80 border border-transparent"
                }`}
              >
                {isEditing ? (
                  <form
                    onSubmit={(e) => handleSaveRename(conv.id, e)}
                    onClick={(e) => e.stopPropagation()}
                    className="flex flex-wrap items-center gap-1 flex-1 min-w-0"
                  >
                    <input
                      aria-label={`Conversation title for ${conv.title}`}
                      type="text"
                      value={editTitle}
                      onChange={(e) => {
                        setEditTitle(e.target.value);
                        setRenameError(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Escape") {
                          setEditingId(null);
                          setRenameError(null);
                        }
                      }}
                      disabled={isSavingRename}
                      autoFocus
                      className="w-full px-1.5 py-0.5 text-xs bg-paper-surface border border-surface-rule rounded-surface text-ink outline-none focus-visible:outline-focus-ring disabled:opacity-60"
                    />
                    <button
                      type="submit"
                      disabled={isSavingRename}
                      aria-busy={isSavingRename}
                      aria-label={isSavingRename ? "Saving conversation title" : "Save conversation title"}
                      className="text-xs text-terracotta font-semibold px-1 focus-visible:outline-focus-ring disabled:opacity-50"
                    >
                      {isSavingRename ? "…" : "✓"}
                    </button>
                    <button
                      type="button"
                      disabled={isSavingRename}
                      onClick={() => {
                        setEditingId(null);
                        setRenameError(null);
                      }}
                      aria-label="Cancel renaming"
                      className="text-xs text-ink/50 px-1 focus-visible:outline-focus-ring disabled:opacity-50"
                    >
                      ✕
                    </button>
                    {isSavingRename && (
                      <span className="sr-only" role="status">Saving conversation title…</span>
                    )}
                    {renameError && (
                      <span className="basis-full text-[10px] text-error">
                        {renameError} Edit the title and try Save again.
                      </span>
                    )}
                  </form>
                ) : (
                  <>
                    <button type="button" onClick={() => { onSelectConversation(conv.id); onClose?.(); }} aria-current={isActive ? "page" : undefined} className="flex-1 min-w-0 text-left truncate pr-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus-ring">
                      <p className="truncate text-xs font-medium">{conv.title}</p>
                      <span className="text-[10px] text-ink/40">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => startRename(conv, e)}
                      aria-label={`Rename ${conv.title}`}
                      title={`Rename ${conv.title}`}
                      className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-[11px] text-ink/40 hover:text-ink px-2 py-2 rounded-surface transition-opacity focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus-ring"
                    >
                      ✎
                    </button>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
