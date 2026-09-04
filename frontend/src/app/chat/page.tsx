"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createConversationAction, getConversationMessagesAction, listConversationsAction, renameConversationAction, sendConversationMessageAction, sendConversationMessageWithKeyAction } from "../actions.ts";
import type { ChatActionResult, Conversation, Message } from "../../types/chat.ts";
import { beginLogicalRetry, canApplySendResult, createLogicalSend, dedupeServerMessage, transitionLogicalSend, upsertLogicalSend, type LocalUserMessage } from "../../lib/chatState.ts";
import { ChatSidebar } from "../../components/chat/ChatSidebar.tsx";
import { ChatMessageList } from "../../components/chat/ChatMessageList.tsx";
import { ChatInput } from "../../components/chat/ChatInput.tsx";

type ConversationMessages = { server: Message[]; local: LocalUserMessage[] };
type Notice = { message: string; action?: () => void; actionLabel?: string };
const EMPTY_MESSAGES: ConversationMessages = { server: [], local: [] };

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messagesByConversation, setMessagesByConversation] = useState<Record<number, ConversationMessages>>({});
  const [composerContent, setComposerContent] = useState("");
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [, startTransition] = useTransition();
  const activeConversationRef = useRef<number | null>(null);
  const activeGenerationRef = useRef(0);
  const historyGenerationRef = useRef<Record<number, number>>({});
  const sendGuardRef = useRef(false);
  const localSequenceRef = useRef(0);

  const redirectIfUnauthorized = useCallback((result: ChatActionResult<unknown>): boolean => {
    if (!result.ok && (result.kind === "unauthorized" || result.status === 401)) {
      router.push("/auth?mode=login");
      return true;
    }
    return false;
  }, [router]);

  const selectConversation = useCallback((id: number | null) => {
    activeGenerationRef.current += 1;
    activeConversationRef.current = id;
    setActiveConversationId(id);
  }, []);

  const refreshConversations = useCallback(async () => {
    const result = await listConversationsAction();
    if (redirectIfUnauthorized(result)) return false;
    if (!result.ok) {
      setNotice({ message: result.error, action: () => void refreshConversations(), actionLabel: "Try again" });
      return false;
    }
    setConversations(result.data);
    return true;
  }, [redirectIfUnauthorized]);

  const reconcileConversation = useCallback(async (conversationId: number, resolvedLocalId?: string) => {
    const requestGeneration = (historyGenerationRef.current[conversationId] ?? 0) + 1;
    historyGenerationRef.current[conversationId] = requestGeneration;
    const result = await getConversationMessagesAction(conversationId);
    if (historyGenerationRef.current[conversationId] !== requestGeneration) return false;
    if (redirectIfUnauthorized(result)) return false;
    if (!result.ok) return false;
    setMessagesByConversation((previous) => {
      const current = previous[conversationId] ?? EMPTY_MESSAGES;
      return { ...previous, [conversationId]: { server: result.data, local: resolvedLocalId ? current.local.filter((item) => item.localId !== resolvedLocalId) : current.local } };
    });
    return true;
  }, [redirectIfUnauthorized]);

  const refreshConversationTitles = useCallback(async () => {
    const result = await listConversationsAction();
    if (redirectIfUnauthorized(result)) return;
    if (result.ok) setConversations(result.data);
  }, [redirectIfUnauthorized]);

  useEffect(() => {
    let mounted = true;
    startTransition(async () => {
      const result = await listConversationsAction();
      if (!mounted || redirectIfUnauthorized(result)) return;
      if (!result.ok) {
        setNotice({ message: result.error, action: () => void refreshConversations(), actionLabel: "Try again" });
        return;
      }
      setConversations(result.data);
      if (result.data.length > 0) selectConversation(result.data[0].id);
    });
    return () => { mounted = false; };
  }, [redirectIfUnauthorized, refreshConversations, selectConversation]);

  useEffect(() => {
    if (activeConversationId === null) return;
    let mounted = true;
    setIsLoadingMessages(true);
    setNotice(null);
    startTransition(async () => {
      const success = await reconcileConversation(activeConversationId);
      if (!mounted) return;
      setIsLoadingMessages(false);
      if (!success) setNotice({ message: "Failed to load conversation history.", action: () => void reconcileConversation(activeConversationId), actionLabel: "Try again" });
    });
    return () => { mounted = false; };
  }, [activeConversationId, reconcileConversation]);

  const handleNewChat = () => {
    if (sendGuardRef.current) return;
    sendGuardRef.current = true;
    startTransition(async () => {
      try {
        const result = await createConversationAction();
        if (redirectIfUnauthorized(result)) return;
        if (!result.ok) {
          setNotice({ message: `${result.error} The result may be uncertain; refresh the conversation list before creating another chat.`, action: () => void refreshConversations(), actionLabel: "Refresh conversations" });
          return;
        }
        const conversation = { id: result.data.conversation_id, title: result.data.title, created_at: result.data.created_at };
        setConversations((previous) => [conversation, ...previous.filter((item) => item.id !== conversation.id)]);
        selectConversation(conversation.id);
      } finally {
        sendGuardRef.current = false;
      }
    });
  };

  const updateLocal = useCallback((conversationId: number, localId: string, next: Parameters<typeof transitionLogicalSend>[2]) => {
    setMessagesByConversation((previous) => {
      const current = previous[conversationId] ?? EMPTY_MESSAGES;
      return { ...previous, [conversationId]: { ...current, local: transitionLogicalSend(current.local, localId, next) } };
    });
  }, []);

  const executeLogicalSend = useCallback(async (item: LocalUserMessage, originGeneration: number) => {
    const result = item.clientKey
      ? await sendConversationMessageWithKeyAction(item.conversation_id, item.content, item.clientKey)
      : await sendConversationMessageAction(item.conversation_id, item.content);
    if (redirectIfUnauthorized(result)) return;
    if (!result.ok) {
      if (result.code === "idempotency_key_in_progress") {
        updateLocal(item.conversation_id, item.localId, { status: "pending", retryable: true, recovery: "check", statusText: `Still processing. Check again with the same key${result.retryAfterSeconds ? ` after ${result.retryAfterSeconds}s` : ""}.` });
      } else if (result.code === "chat_idempotency_unavailable") {
        updateLocal(item.conversation_id, item.localId, { status: "failed", retryable: false, recovery: "refresh", statusText: "The keyed result is uncertain. Refresh; do not resend this message." });
      } else if (result.code === "idempotency_key_conflict" || result.status === 404) {
        updateLocal(item.conversation_id, item.localId, { status: "failed", retryable: false, recovery: "refresh", statusText: result.status === 404 ? "This conversation is no longer available. Refresh conversations." : "This request key conflicts with another message. Refresh the conversation." });
      } else if (item.clientKey) {
        updateLocal(item.conversation_id, item.localId, { status: "failed", retryable: true, recovery: "retry", statusText: "Message not completed. Retry with the same request key." });
      } else {
        updateLocal(item.conversation_id, item.localId, { status: "failed", retryable: false, recovery: "refresh", statusText: "The result is uncertain because safe retry is unavailable. Refresh before sending again." });
      }
      return;
    }
    setMessagesByConversation((previous) => {
      const current = previous[item.conversation_id] ?? EMPTY_MESSAGES;
      return { ...previous, [item.conversation_id]: { server: dedupeServerMessage(current.server, result.data), local: transitionLogicalSend(current.local, item.localId, { status: "sent", retryable: false, recovery: "refresh", statusText: "Sent. Refreshing conversation history…" }) } };
    });
    const reconciled = await reconcileConversation(item.conversation_id, item.localId);
    if (!reconciled) updateLocal(item.conversation_id, item.localId, { status: "sent", retryable: false, recovery: "refresh", statusText: "Sent, but the conversation could not be refreshed." });
    if (canApplySendResult(item.conversation_id, activeConversationRef.current, originGeneration, activeGenerationRef.current)) setNotice(null);
    void refreshConversationTitles();
  }, [reconcileConversation, redirectIfUnauthorized, refreshConversationTitles, updateLocal]);

  const handleSendMessage = async (content: string) => {
    if (sendGuardRef.current) return;
    sendGuardRef.current = true;
    setIsSending(true);
    setNotice(null);
    try {
      let conversationId = activeConversationRef.current;
      if (conversationId === null) {
        const result = await createConversationAction();
        if (redirectIfUnauthorized(result)) return;
        if (!result.ok) {
          setNotice({ message: `${result.error} Your draft is preserved. Refresh conversations before trying to create another chat.`, action: () => void refreshConversations(), actionLabel: "Refresh conversations" });
          return;
        }
        const conversation = { id: result.data.conversation_id, title: result.data.title, created_at: result.data.created_at };
        conversationId = conversation.id;
        setConversations((previous) => [conversation, ...previous.filter((item) => item.id !== conversation.id)]);
        selectConversation(conversation.id);
      }
      const keyedMode = process.env.NEXT_PUBLIC_CHAT_IDEMPOTENCY_ENABLED?.trim().toLowerCase() === "true";
      const clientKey = keyedMode && typeof globalThis.crypto?.randomUUID === "function" ? globalThis.crypto.randomUUID() : null;
      localSequenceRef.current += 1;
      const item = createLogicalSend(conversationId, content, new Date().toISOString(), clientKey, clientKey ?? `keyless-${localSequenceRef.current}`);
      const originGeneration = activeGenerationRef.current;
      setMessagesByConversation((previous) => {
        const current = previous[conversationId] ?? EMPTY_MESSAGES;
        return { ...previous, [conversationId]: { ...current, local: upsertLogicalSend(current.local, item) } };
      });
      setComposerContent("");
      await executeLogicalSend(item, originGeneration);
    } finally {
      sendGuardRef.current = false;
      setIsSending(false);
    }
  };

  const handleRecoverMessage = async (item: LocalUserMessage) => {
    if (item.recovery === "refresh") {
      const success = await reconcileConversation(item.conversation_id, item.localId);
      if (!success) updateLocal(item.conversation_id, item.localId, { status: item.status, retryable: item.retryable, recovery: item.recovery, statusText: "Refresh failed. Your message is still preserved." });
      return;
    }
    if (!item.clientKey || !item.retryable || sendGuardRef.current) return;
    sendGuardRef.current = true;
    setIsSending(true);
    setMessagesByConversation((previous) => {
      const current = previous[item.conversation_id] ?? EMPTY_MESSAGES;
      return { ...previous, [item.conversation_id]: { ...current, local: beginLogicalRetry(current.local, item.localId) } };
    });
    try {
      await executeLogicalSend(item, activeGenerationRef.current);
    } finally {
      sendGuardRef.current = false;
      setIsSending(false);
    }
  };

  const handleRenameConversation = async (id: number, newTitle: string) => {
    const result = await renameConversationAction(id, newTitle);
    if (redirectIfUnauthorized(result)) return { ok: false, error: "Sign in required." };
    if (!result.ok) return { ok: false, error: result.error };
    setConversations((previous) => previous.map((conversation) => conversation.id === id ? result.data : conversation));
    return { ok: true };
  };

  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId);
  const activeMessages = activeConversationId === null ? EMPTY_MESSAGES : (messagesByConversation[activeConversationId] ?? EMPTY_MESSAGES);
  const visibleMessages = [...activeMessages.server, ...activeMessages.local].sort((left, right) => left.created_at.localeCompare(right.created_at));

  return (
    <div className="flex flex-col h-[calc(100vh-45px)] bg-paper text-ink">
      <header className="border-b border-rule bg-paper px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="font-display text-xl text-ink hover:text-terracotta-dark">Kelana<span className="text-terracotta-dark">AI</span></Link>
          <span className="text-muted-ink text-sm hidden sm:inline">|</span><span className="text-sm font-semibold text-ink/80 hidden sm:inline">Travel Assistant</span>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium"><Link href="/" className="text-muted-ink hover:text-ink transition-colors">Planner</Link><Link href="/trips" className="text-muted-ink hover:text-ink transition-colors">My Trips</Link><span className="text-terracotta font-semibold border-b border-terracotta pb-0.5">Assistant</span></div>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <ChatSidebar conversations={conversations} activeConversationId={activeConversationId} onSelectConversation={selectConversation} onNewChat={handleNewChat} onRenameConversation={handleRenameConversation} />
        <main className="flex-1 flex flex-col bg-paper-light relative">
          <div className="px-6 py-3 border-b border-rule bg-paper-surface flex items-center justify-between shadow-2xs"><h1 className="font-display text-lg text-ink font-semibold truncate">{activeConversation ? activeConversation.title : "New Conversation"}</h1><span className="text-xs text-ink/40 font-mono">{visibleMessages.length} {visibleMessages.length === 1 ? "turn" : "turns"}</span></div>
          {notice && <div className="px-4 py-2 bg-red-50 border-b border-red-200 text-xs text-red-700 flex justify-between items-center gap-3"><span>{notice.message}</span><div className="flex items-center gap-3 shrink-0">{notice.action && <button type="button" onClick={notice.action} className="font-semibold hover:underline">{notice.actionLabel}</button>}<button type="button" onClick={() => setNotice(null)} className="text-red-900 font-bold hover:underline">✕</button></div></div>}
          {isLoadingMessages ? <div className="flex-1 flex items-center justify-center text-ink/50 text-sm italic">Loading conversation history...</div> : <ChatMessageList messages={visibleMessages} isLoading={isSending} onRecoverMessage={handleRecoverMessage} />}
          <ChatInput content={composerContent} onContentChange={setComposerContent} onSendMessage={handleSendMessage} disabled={isSending} />
        </main>
      </div>
    </div>
  );
}
