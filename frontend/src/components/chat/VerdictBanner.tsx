const LEGAL_CLINIC_URL = 'https://www.mass.gov/info-details/free-wage-theft-legal-clinic';

interface Props {
  flag: 'high' | 'low' | 'fallback';
}

export function VerdictBanner({ flag }: Props) {
  if (flag === 'high') {
    return (
      <div className="verdict-banner verdict-high">
        This looks like a potential wage violation.
      </div>
    );
  }
  if (flag === 'low') {
    return (
      <div className="verdict-banner verdict-low">
        We found limited matches — consider consulting a professional.
      </div>
    );
  }
  return (
    <div className="verdict-banner verdict-fallback">
      We couldn't find a confident answer.{' '}
      <a href={LEGAL_CLINIC_URL} target="_blank" rel="noreferrer">
        Get free legal help →
      </a>
    </div>
  );
}
