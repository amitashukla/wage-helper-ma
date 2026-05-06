import type { ChatMessage } from '../../types';
import { BotMessage } from './BotMessage';

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="message-row message-row-user">
        <div className="bubble bubble-user">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="message-row message-row-bot">
      <div className="bot-avatar" aria-hidden="true">⚖️</div>
      <div className="bubble bubble-bot">
        <BotMessage message={message} />
      </div>
    </div>
  );
}
