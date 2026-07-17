import { useState } from "react";
import Button from "../../ui/Button";

interface DateFormProps {
  interactive: boolean;
  onSubmit: (value: { date: string; duration_hours: number }, label: string) => void;
}

const today = new Date().toISOString().slice(0, 10);

export default function DateForm({ interactive, onSubmit }: DateFormProps) {
  const [date, setDate] = useState(today);
  const [durationHours, setDurationHours] = useState("3");

  const durationNumber = Number(durationHours);
  const canSubmit = Boolean(date) && durationNumber > 0;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit(
      { date, duration_hours: durationNumber },
      `${date} · ${durationNumber}h`,
    );
  }

  return (
    <div className={`wizard-form${interactive ? "" : " wizard-disabled"}`}>
      <div className="wizard-form-row">
        <label className="wizard-field">
          <span>Date</span>
          <input
            type="date"
            className="wizard-input"
            value={date}
            min={today}
            disabled={!interactive}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
        <label className="wizard-field">
          <span>Durée (heures)</span>
          <input
            type="number"
            min={1}
            max={12}
            className="wizard-input"
            value={durationHours}
            disabled={!interactive}
            onChange={(event) => setDurationHours(event.target.value)}
          />
        </label>
      </div>
      {interactive && (
        <Button variant="primary" compact onClick={handleSubmit} disabled={!canSubmit}>
          Valider
        </Button>
      )}
    </div>
  );
}
