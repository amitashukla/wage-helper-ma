export interface CitationBlock {
  section_id: string;
  section_title: string;
  verbatim_text: string;
}

export interface SessionProfile {
  employer: string | null;
  employer_matches: string[];
  complaint_types: string[];
  employment_type: 'hourly' | 'salary' | 'tipped' | null;
  hours_per_week: number | null;
  violation_categories: string[];
  conversation_history: Array<{ role: string; content: string }>;
  confidence_flag: 'high' | 'low' | 'fallback' | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citationBlocks?: CitationBlock[];
  violationCategory?: string | null;
  employerMatches?: string[];
  confidenceFlag?: 'high' | 'low' | 'fallback';
}

export interface ChatResponse {
  answer: string;
  citation_blocks: CitationBlock[];
  violation_category: string | null;
  employer_matches: string[];
  confidence_flag: 'high' | 'low' | 'fallback';
  session: SessionProfile;
}
