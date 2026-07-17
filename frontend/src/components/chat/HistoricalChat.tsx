import { useEffect, useRef } from "react";
import type { ChatSession, SourceRef } from "../../types";
import ChatCore from "./ChatCore";

interface HistoricalChatProps {
  variant: "floating" | "docked";
  chat: ChatSession | null;
  chats: ChatSession[];
  activeChatId: string | null;
  onClose: () => void;
  onNewChat: () => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  onEnsureChat: () => string;
  onAppendMessage: (
    chatId: string,
    message: {
      role: "user" | "assistant";
      content: string;
      sources?: ChatSession["messages"][number]["sources"];
      memory?: ChatSession["messages"][number]["memory"];
      actions?: string[];
      wizard?: ChatSession["messages"][number]["wizard"];
      elapsedMs?: number;
      latencyMs?: number;
      latencyDebug?: ChatSession["messages"][number]["latencyDebug"];
    },
  ) => void;
  onSourcesReceived?: (sources: SourceRef[]) => void;
}

export default function HistoricalChat({
  variant,
  chat,
  chats,
  activeChatId,
  onClose,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onEnsureChat,
  onAppendMessage,
  onSourcesReceived,
}: HistoricalChatProps) {
  const widgetRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (variant !== "floating") return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [variant, onClose]);

  if (variant === "docked") {
    return (
      <div className="historical-chat-docked">
        <header className="historical-chat-docked-header">
          <div>
            <h2>Guide historique</h2>
            <p>Réponses sourcées sur le patrimoine de Carthage</p>
          </div>
        </header>
        <ChatCore
          chat={chat}
          chats={chats}
          activeChatId={activeChatId}
          onNewChat={onNewChat}
          onSelectChat={onSelectChat}
          onDeleteChat={onDeleteChat}
          onEnsureChat={onEnsureChat}
          onAppendMessage={onAppendMessage}
          onSourcesReceived={onSourcesReceived}
        />
      </div>
    );
  }

  return (
    <section
      ref={widgetRef}
      className="chat-widget"
      role="dialog"
      aria-modal="true"
      aria-label="Dourbia Guide"
    >
      <header className="chat-widget-header">
        <img src="/dourbia-icon.png" alt="" className="chat-header-icon" />
        <div className="chat-widget-header-text">
          <h2>Dourbia Guide</h2>
          <p>Guide historique intelligent</p>
        </div>
        <button
          type="button"
          className="chat-widget-close"
          onClick={onClose}
          aria-label="Fermer le guide"
        >
          ×
        </button>
      </header>
      <ChatCore
        chat={chat}
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={onNewChat}
        onSelectChat={onSelectChat}
        onDeleteChat={onDeleteChat}
        onEnsureChat={onEnsureChat}
        onAppendMessage={onAppendMessage}
        onSourcesReceived={onSourcesReceived}
      />
    </section>
  );
}
