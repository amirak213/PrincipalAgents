import { useState } from "react";
import Button from "../../ui/Button";

interface DateFormProps {
  interactive: boolean;
  onSubmit: (value: { date: string; start_time: string; end_time: string }, label: string) => void;
}

const today = new Date().toISOString().slice(0, 10);

export default function DateForm({ interactive, onSubmit }: DateFormProps) {
  const [date, setDate] = useState(today);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("12:00");

  const canSubmit = Boolean(date) && Boolean(startTime) && Boolean(endTime) && startTime < endTime;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit(
      { date, start_time: startTime, end_time: endTime },
      `${date} · ${startTime} - ${endTime}`,
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
          <span>Début</span>
          <input
            type="time"
            className="wizard-input"
            value={startTime}
            disabled={!interactive}
            onChange={(event) => setStartTime(event.target.value)}
          />
        </label>
        <label className="wizard-field">
          <span>Fin</span>
          <input
            type="time"
            className="wizard-input"
            value={endTime}
            disabled={!interactive}
            onChange={(event) => setEndTime(event.target.value)}
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
