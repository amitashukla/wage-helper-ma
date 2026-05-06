interface Props {
  employerMatches: string[];
}

export function PriorComplaintsCallout({ employerMatches }: Props) {
  if (!employerMatches.length) return null;

  const first = employerMatches[0];
  const extra = employerMatches.length - 1;

  return (
    <div className="complaints-callout">
      <strong>Prior complaints on record:</strong>{' '}
      {first}
      {extra > 0 && ` and ${extra} other employer${extra > 1 ? 's' : ''}`}
      {' '}
      have prior AG complaint records. This may strengthen your case.
    </div>
  );
}
