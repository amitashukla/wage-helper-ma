import { useState, useRef } from 'react';

const LEGAL_CLINIC_URL = 'https://www.mass.gov/info-details/free-wage-theft-legal-clinic';

interface Props {
  onSend: (message: string) => void;
  isLoading: boolean;
  pendingMessage?: string;
  onPendingChange?: (value: string) => void;
}

export function InputBar({ onSend, isLoading, pendingMessage, onPendingChange }: Props) {
  const [localValue, setLocalValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const value = pendingMessage !== undefined ? pendingMessage : localValue;
  const setValue = onPendingChange ?? setLocalValue;

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue('');
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="input-bar-wrapper">
      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your situation…"
          disabled={isLoading}
          rows={2}
          aria-label="Your message"
        />
        <button
          className="send-button"
          onClick={handleSubmit}
          disabled={isLoading || !value.trim()}
          aria-label="Send message"
        >
          {isLoading ? '…' : '→'}
        </button>
      </div>
      <p className="input-disclaimer">
        This tool provides legal information, not legal advice. For free help,{' '}
        <a href={LEGAL_CLINIC_URL} target="_blank" rel="noreferrer">
          visit the MA Wage Theft Legal Clinic
        </a>
        . Always consult a lawyer for your specific situation.
      </p>
    </div>
  );
}
