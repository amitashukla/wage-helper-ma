import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../../types';
import { MessageBubble } from '../chat/MessageBubble';
import { TypingIndicator } from '../chat/TypingIndicator';

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function ChatWindow({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-window" role="log" aria-live="polite">
      {messages.length === 0 && (
        <div className="chat-empty">
          <p>Describe your situation and I'll help you understand your rights under MA wage law.</p>
        </div>
      )}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {isLoading && (
        <div className="message-row message-row-bot">
          <div className="bot-avatar" aria-hidden="true">⚖️</div>
          <div className="bubble bubble-bot">
            <TypingIndicator />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
