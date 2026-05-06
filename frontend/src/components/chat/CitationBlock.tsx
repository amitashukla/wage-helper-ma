import { useState } from 'react';
import type { CitationBlock as CitationBlockType } from '../../types';

interface Props {
  citation: CitationBlockType;
}

export function CitationBlock({ citation }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="citation-block">
      <button
        className="citation-toggle"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="citation-label">From MA General Laws Chapter 149</span>
        <span className="citation-section">§ {citation.section_id}</span>
        {citation.section_title && (
          <span className="citation-title"> — {citation.section_title}</span>
        )}
        <span className="citation-chevron">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <blockquote className="citation-text">{citation.verbatim_text}</blockquote>
      )}
    </div>
  );
}
