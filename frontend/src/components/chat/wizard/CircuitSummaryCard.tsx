import type { WizardCircuitSummary } from "../../../types";

interface CircuitSummaryCardProps {
  circuit: WizardCircuitSummary;
}

export default function CircuitSummaryCard({ circuit }: CircuitSummaryCardProps) {
  return (
    <div className="wizard-circuit-summary">
      <h4>{circuit.title}</h4>
      {circuit.summary && <p className="wizard-circuit-tagline">{circuit.summary}</p>}
      <ol className="wizard-circuit-stops">
        {circuit.monuments.map((stop) => (
          <li key={stop.order} className="wizard-circuit-stop">
            <span className="wizard-circuit-stop-order">{stop.order}</span>
            <span className="wizard-circuit-stop-name">{stop.name}</span>
            <span className="wizard-circuit-stop-meta">
              {stop.visit_duration_min} min · {stop.price} DT
            </span>
          </li>
        ))}
      </ol>
      <p className="wizard-circuit-totals">
        Total : {circuit.total_duration_min} min · {circuit.total_price} DT
      </p>
    </div>
  );
}
