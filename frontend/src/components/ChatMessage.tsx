import type { ChatEvent } from "../types/request";

export function ChatMessage({ event }: { event: ChatEvent }) {
  const isUser = event.role === "USER";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] whitespace-pre-line rounded-2xl px-4 py-3 leading-relaxed ${
          isUser
            ? "rounded-br-md bg-pine text-white"
            : "rounded-bl-md bg-pine-soft text-ink"
        }`}
      >
        {event.content}
      </div>
    </div>
  );
}
