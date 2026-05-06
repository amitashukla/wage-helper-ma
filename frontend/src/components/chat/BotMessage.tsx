import type { ChatMessage } from '../../types';
import { VerdictBanner } from './VerdictBanner';
import { ViolationCategoryBadge } from './ViolationCategoryBadge';
import { PriorComplaintsCallout } from './PriorComplaintsCallout';
import { CitationBlock } from './CitationBlock';

interface Props {
  message: ChatMessage;
}

export function BotMessage({ message }: Props) {
  const { content, confidenceFlag, violationCategory, employerMatches, citationBlocks } = message;

  return (
    <div className="bot-message">
      {confidenceFlag && <VerdictBanner flag={confidenceFlag} />}

      <div className="bot-message-text">{content}</div>

      {violationCategory && (
        <div className="violation-badges">
          <ViolationCategoryBadge category={violationCategory} />
        </div>
      )}

      {employerMatches && employerMatches.length > 0 && (
        <PriorComplaintsCallout employerMatches={employerMatches} />
      )}

      {citationBlocks && citationBlocks.length > 0 && (
        <div className="citation-list">
          {citationBlocks.map((c) => (
            <CitationBlock key={c.section_id} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}
