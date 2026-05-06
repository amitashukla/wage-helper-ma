import { useState } from 'react';
import type { SessionProfile } from '../types';

const DEFAULT_SESSION: SessionProfile = {
  employer: null,
  employer_matches: [],
  complaint_types: [],
  employment_type: null,
  hours_per_week: null,
  violation_categories: [],
  conversation_history: [],
  confidence_flag: null,
};

export function useSession() {
  const [sessionProfile, setSessionProfile] = useState<SessionProfile>(DEFAULT_SESSION);
  return { sessionProfile, updateSessionProfile: setSessionProfile };
}
