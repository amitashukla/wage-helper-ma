interface Props {
  tags: string[];
}

export function SessionPill({ tags }: Props) {
  if (!tags.length) return null;

  return (
    <div className="session-pill-bar">
      <span className="session-pill-label">What I know:</span>
      {tags.map((tag) => (
        <span key={tag} className="session-tag">{tag}</span>
      ))}
    </div>
  );
}
