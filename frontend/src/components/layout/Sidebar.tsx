import { SuggestedNextSteps } from '../sidebar/SuggestedNextSteps';

interface Props {
  suggestedSteps: string[];
  onStepSelect: (step: string) => void;
}

export function Sidebar({ suggestedSteps, onStepSelect }: Props) {
  return (
    <aside className="sidebar">
      <SuggestedNextSteps steps={suggestedSteps} onSelect={onStepSelect} />
    </aside>
  );
}
