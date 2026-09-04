"use client";

import { useState } from "react";
import type { Conversation } from "../../types/chat.ts";

interface ChatSidebarProps {
  conversations: Conversation[];
  activeConversationId: number | null;
  onSelectConversation: (id: number) => void;
  onNewChat: () => void;
  onRenameConversation: (id: number, newTitle: string) => Promise<{ ok: boolean; error?: string }>;
}

export function ChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onRenameConversation,
}: ChatSidebarProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);

  const startRename = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
    setRenameError(null);
  };

  const handleSaveRename = async (id: number, e: React.FormEvent) => {
    e.preventDefault();
    if (!editTitle.trim()) return;
    const result = await onRenameConversation(id, editTitle.trim());
    if (result.ok) {
      setEditingId(null);
      setRenameError(null);
    } else {
      setRenameError(result.error || "Failed to rename conversation.");
    }
  };

  return (
    <aside className="w-full md:w-72 bg-paper border-r border-rule flex flex-col h-full select-none">
      <div className="p-4 border-b border-rule flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg text-ink font-semibold">Conversations</h2>
          <p className="text-xs text-ink/50">Travel Assistant</p>
        </div>
        <button
          type="button"
          onClick={onNewChat}
          className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-semibold text-white bg-terracotta hover:bg-terracotta-dark rounded-[4px] transition-colors shadow-xs"
        >
          + New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 ? (
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
                onClick={() => onSelectConversation(conv.id)}
                className={`group flex items-center justify-between p-2.5 rounded-[4px] cursor-pointer text-sm transition-colors ${
                  isActive
                    ? "bg-terracotta/10 border border-terracotta/30 text-ink font-medium"
                    : "hover:bg-ink/5 text-ink/80 border border-transparent"
                }`}
              >
                {isEditing ? (
                  <form
                    onSubmit={(e) => handleSaveRename(conv.id, e)}
                    onClick={(e) => e.stopPropagation()}
                    className="flex flex-wrap items-center gap-1 flex-1"
                  >
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => {
                        setEditTitle(e.target.value);
                        setRenameError(null);
                      }}
                      autoFocus
                      className="w-full px-1.5 py-0.5 text-xs bg-paper-surface border border-rule rounded text-ink outline-none"
                    />
                    <button
                      type="submit"
                      className="text-xs text-terracotta font-semibold px-1"
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(null);
                        setRenameError(null);
                      }}
                      className="text-xs text-ink/50 px-1"
                    >
                      ✕
                    </button>
                    {renameError && (
                      <span className="basis-full text-[10px] text-error">
                        {renameError} Edit the title and try Save again.
                      </span>
                    )}
                  </form>
                ) : (
                  <>
                    <div className="flex-1 truncate pr-2">
                      <p className="truncate text-xs font-medium">{conv.title}</p>
                      <span className="text-[10px] text-ink/40">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => startRename(conv, e)}
                      title="Rename conversation"
                      className="opacity-0 group-hover:opacity-100 text-[11px] text-ink/40 hover:text-ink px-1.5 py-0.5 rounded transition-opacity"
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
