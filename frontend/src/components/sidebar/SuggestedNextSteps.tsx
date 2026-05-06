const LEGAL_CLINIC_URL = 'https://www.mass.gov/info-details/free-wage-theft-legal-clinic';

interface Props {
  steps: string[];
  onSelect: (step: string) => void;
}

export function SuggestedNextSteps({ steps, onSelect }: Props) {
  return (
    <div className="sidebar-section">
      <h3 className="sidebar-heading">Next steps</h3>
      {steps.length > 0 ? (
        <ul className="next-steps-list">
          {steps.map((step) => (
            <li key={step}>
              <button className="next-step-btn" onClick={() => onSelect(step)}>
                {step}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="sidebar-empty">Ask me anything about your situation.</p>
      )}

      <div className="sidebar-legal-help">
        <h3 className="sidebar-heading">Free legal help</h3>
        <p className="sidebar-legal-text">
          MA workers can get free legal advice at the{' '}
          <a
            href={LEGAL_CLINIC_URL}
            target="_blank"
            rel="noreferrer"
            className="sidebar-link"
          >
            Wage Theft Legal Clinic
          </a>
          .
        </p>
      </div>
    </div>
  );
}
