const STARTER_PROMPTS = [
  'My employer hasn\'t paid me overtime',
  'I never get a pay stub',
  'My boss pays me less than minimum wage',
  'I was fired for complaining about my pay',
  'I work through lunch but don\'t get paid for it',
];

interface Props {
  onSelect: (prompt: string) => void;
}

export function InputHints({ onSelect }: Props) {
  return (
    <div className="input-hints">
      {STARTER_PROMPTS.map((prompt) => (
        <button
          key={prompt}
          className="hint-chip"
          onClick={() => onSelect(prompt)}
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
