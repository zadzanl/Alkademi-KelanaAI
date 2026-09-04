// Logical send identity is intentionally in-memory only. A persisted browser
// outbox would require a separate privacy and lifecycle design.
export type LogicalSendStatus = "pending" | "failed" | "sent";
export type LogicalSendRecovery = "retry" | "check" | "refresh" | null;

export type LocalUserMessage = {
  kind: "local-user";
  localId: string;
  clientKey: string | null;
  conversation_id: number;
  role: "user";
  content: string;
  created_at: string;
  status: LogicalSendStatus;
  retryable: boolean;
  recovery: LogicalSendRecovery;
  statusText: string;
};

export function createLogicalSend(
  conversationId: number,
  content: string,
  createdAt: string,
  clientKey: string | null,
  localId: string,
): LocalUserMessage {
  return {
    kind: "local-user",
    localId,
    clientKey,
    conversation_id: conversationId,
    role: "user",
    content,
    created_at: createdAt,
    status: "pending",
    retryable: false,
    recovery: null,
    statusText: "Sending…",
  };
}

export function upsertLogicalSend(
  items: LocalUserMessage[],
  item: LocalUserMessage,
): LocalUserMessage[] {
  const index = items.findIndex((candidate) => candidate.localId === item.localId);
  if (index === -1) return [...items, item];
  return items.map((candidate, candidateIndex) => candidateIndex === index ? item : candidate);
}

export function transitionLogicalSend(
  items: LocalUserMessage[],
  localId: string,
  next: Pick<LocalUserMessage, "status" | "retryable" | "recovery" | "statusText">,
): LocalUserMessage[] {
  return items.map((item) => item.localId === localId ? { ...item, ...next } : item);
}

export function beginLogicalRetry(
  items: LocalUserMessage[],
  localId: string,
): LocalUserMessage[] {
  return transitionLogicalSend(items, localId, {
    status: "pending",
    retryable: false,
    recovery: null,
    statusText: "Checking this message with the same request key…",
  });
}

export function canApplySendResult(
  originConversationId: number,
  activeConversationId: number | null,
  originGeneration: number,
  activeGeneration: number,
): boolean {
  return originConversationId === activeConversationId && originGeneration === activeGeneration;
}

export function dedupeServerMessage<T extends { id: number }>(items: T[], message: T): T[] {
  return items.some((candidate) => candidate.id === message.id) ? items : [...items, message];
}