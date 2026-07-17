import type { WizardOption } from "../../../types";
import Button from "../../ui/Button";

interface ConfirmCardProps {
  options: WizardOption[];
  budgetOk?: boolean | null;
  budgetWarning?: string | null;
  interactive: boolean;
  onSelect: (option: WizardOption) => void;
}

export default function ConfirmCard({
  options,
  budgetOk,
  budgetWarning,
  interactive,
  onSelect,
}: ConfirmCardProps) {
  return (
    <div className={`wizard-form${interactive ? "" : " wizard-disabled"}`}>
      {budgetOk === false && budgetWarning && (
        <p className="wizard-warning" role="alert">
          ⚠️ {budgetWarning}
        </p>
      )}
      <div className="wizard-chip-row" role="group">
        {options.map((option) => (
          <Button
            key={option.value}
            variant={option.value === "confirm_circuit" ? "primary" : "secondary"}
            compact
            disabled={!interactive}
            onClick={interactive ? () => onSelect(option) : undefined}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
