import type { WizardOption, WizardUI } from "../../../types";
import Card from "../../ui/Card";
import { buildWizardAction } from "./wizardEvents";
import SingleSelectCards from "./SingleSelectCards";
import PlaceMultiSelect from "./PlaceMultiSelect";
import BudgetForm from "./BudgetForm";
import DateForm from "./DateForm";
import ConfirmCard from "./ConfirmCard";

interface WizardRendererProps {
  wizard: WizardUI;
  /** false une fois que cette card n'est plus le dernier message (déjà répondue) */
  interactive: boolean;
  /** action structurée + libellé lisible à afficher comme "message utilisateur" */
  onAnswer: (action: ReturnType<typeof buildWizardAction>, label: string) => void;
}

export default function WizardRenderer({ wizard, interactive, onAnswer }: WizardRendererProps) {
  function submitOption(option: WizardOption) {
    onAnswer(buildWizardAction(wizard.state, option.value), option.label);
  }

  function submitPlaces(options: WizardOption[]) {
    onAnswer(
      buildWizardAction(
        wizard.state,
        options.map((option) => option.value),
      ),
      options.map((option) => option.label).join(", "),
    );
  }

  function submitStructured(value: Record<string, unknown>, label: string) {
    onAnswer(buildWizardAction(wizard.state, value), label);
  }

  return (
    <Card compact className="wizard-card">
      {wizard.input_type === "single_select" && (
        <SingleSelectCards
          options={wizard.options}
          interactive={interactive}
          onSelect={submitOption}
        />
      )}

      {wizard.input_type === "multi_select" && (
        <PlaceMultiSelect
          options={wizard.options}
          hasMore={wizard.has_more}
          interactive={interactive}
          onSubmit={submitPlaces}
        />
      )}

      {wizard.input_type === "budget_form" && (
        <BudgetForm
          options={wizard.options}
          interactive={interactive}
          onSubmit={submitStructured}
        />
      )}

      {wizard.input_type === "date_form" && (
        <DateForm interactive={interactive} onSubmit={submitStructured} />
      )}

      {wizard.input_type === "confirm" && (
        <ConfirmCard
          options={wizard.options}
          budgetOk={wizard.budget_ok}
          budgetWarning={wizard.budget_warning}
          interactive={interactive}
          onSelect={submitOption}
        />
      )}
    </Card>
  );
}
