import { useState } from 'react';
import type { ChatMessage, ChatResponse } from './types';
import { useSession } from './hooks/useSession';
import { ChatWindow } from './components/layout/ChatWindow';
import { Sidebar } from './components/layout/Sidebar';
import { InputBar } from './components/input/InputBar';
import { InputHints } from './components/input/InputHints';
import { SessionPill } from './components/session/SessionPill';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

function buildSessionTags(session: ReturnType<typeof useSession>['sessionProfile']): string[] {
  const tags: string[] = [];
  if (session.employer) tags.push(session.employer);
  if (session.employment_type) tags.push(session.employment_type);
  if (session.violation_categories.length) tags.push(...session.violation_categories.slice(0, 2));
  return tags;
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingInput, setPendingInput] = useState('');
  const [suggestedSteps, setSuggestedSteps] = useState<string[]>([]);
  const { sessionProfile, updateSessionProfile } = useSession();

  const hasSentMessage = messages.length > 0;

  async function sendMessage(text: string) {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session: sessionProfile }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: ChatResponse = await res.json();

      const botMsg: ChatMessage = {
        role: 'assistant',
        content: data.answer,
        citationBlocks: data.citation_blocks,
        violationCategory: data.violation_category,
        employerMatches: data.employer_matches,
        confidenceFlag: data.confidence_flag,
      };

      setMessages((prev) => [...prev, botMsg]);
      updateSessionProfile(data.session);

      // Derive suggested follow-up questions from violation category
      if (data.violation_category && data.violation_category !== 'unknown') {
        setSuggestedSteps([
          `What evidence should I gather for a ${data.violation_category}?`,
          `How do I file a complaint about ${data.violation_category}?`,
          'What are the deadlines for filing a wage claim in Massachusetts?',
        ]);
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content:
          'Something went wrong. Please try again, or visit the free ' +
          'MA Wage Theft Legal Clinic for direct help.',
        confidenceFlag: 'fallback',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }

  const sessionTags = buildSessionTags(sessionProfile);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <span className="header-logo">⚖️</span>
          <h1 className="header-title">MA Wage Rights Helper</h1>
          <span className="header-badge">Massachusetts workers only</span>
        </div>
      </header>

      {sessionTags.length > 0 && <SessionPill tags={sessionTags} />}

      <div className="app-body">
        <main className="main-panel">
          <ChatWindow messages={messages} isLoading={isLoading} />

          {!hasSentMessage && (
            <InputHints onSelect={(p) => { setPendingInput(p); }} />
          )}

          <InputBar
            onSend={sendMessage}
            isLoading={isLoading}
            pendingMessage={pendingInput}
            onPendingChange={setPendingInput}
          />
        </main>

        <Sidebar suggestedSteps={suggestedSteps} onStepSelect={sendMessage} />
      </div>
    </div>
  );
}
