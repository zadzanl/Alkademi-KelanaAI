export type Conversation = {
  id: number;
  title: string;
  created_at: string;
};

export type ConversationCreateResponse = {
  conversation_id: number;
  title: string;
  created_at: string;
};

export type MessageRole = "user" | "assistant";

export type Message = {
  id: number;
  conversation_id: number;
  role: MessageRole;
  content: string;
  created_at: string;
};

export type ChatErrorKind =
  | "validation"
  | "timeout"
  | "network"
  | "upstream"
  | "malformed"
  | "unauthorized"
  | "configuration";

export type ChatActionResult<T> =
  | { ok: true; data: T }
  | {
      ok: false;
      error: string;
      kind: ChatErrorKind;
      status?: number;
      code?: string;
      retryAfterSeconds?: number;
    };
