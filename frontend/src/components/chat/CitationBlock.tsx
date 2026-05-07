import { useState } from 'react';
import type { CitationBlock as CitationBlockType } from '../../types';

interface Props {
  citation: CitationBlockType;
}

function isStatuteSection(id: string): boolean {
  return /^Section\d/i.test(id);
}

export function CitationBlock({ citation }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isStatute = isStatuteSection(citation.section_id);

  return (
    <div className="citation-block">
      <button
        className="citation-toggle"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {isStatute ? (
          <>
            <span className="citation-label">MA General Laws Ch. 149</span>
            <span className="citation-section">{citation.section_id}</span>
          </>
        ) : (
          <>
            <span className="citation-label">AG Publication</span>
            <span className="citation-section">{citation.section_id}</span>
          </>
        )}
        <span className="citation-chevron">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <blockquote className="citation-text">{citation.verbatim_text}</blockquote>
      )}
    </div>
  );
}
