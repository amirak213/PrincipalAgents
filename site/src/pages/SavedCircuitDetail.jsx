const MOBILITY_LABELS = { normale: 'Normale', reduite: 'Réduite', limitee: 'Limitée' }
const TRANSPORT_LABELS = {
  walking: 'À pied',
  bike: 'Vélo',
  car: 'Voiture',
  public_transport: 'Transports en commun',
}
const TARIFF_LABELS = {
  resident: 'Résident',
  etudiant: 'Étudiant',
  etranger: 'Étranger',
  enseignant: 'Enseignant',
  retraite: 'Retraité',
  enfant: 'Enfant',
}

function formatList(values) {
  return values && values.length > 0 ? values.join(', ') : 'Aucune préférence'
}

function formatPrice(price) {
  if (price == null) return 'Prix non renseigné'
  if (price === 0) return 'Gratuit'
  return `${price} DT`
}

function mustVisitNames(detail) {
  const ids = detail.params?.must_visit ?? []
  if (ids.length === 0) return 'Aucun'
  const stops = detail.result?.circuit?.monuments ?? []
  return ids
    .map(
      (id) =>
        stops.find((s) => s.monument_id != null && String(Math.trunc(s.monument_id)) === String(id))
          ?.name ?? `#${id}`,
    )
    .join(', ')
}

function formatTime(detail) {
  const tc = detail.params?.time_constraints
  if (!tc) return 'Non précisé'
  const parts = []
  if (tc.start_time && tc.end_time) parts.push(`${tc.start_time} → ${tc.end_time}`)
  if (typeof tc.duration_minutes === 'number') parts.push(`${tc.duration_minutes} min max`)
  return parts.length > 0 ? parts.join(' · ') : 'Non précisé'
}

function Stat({ label, value, tone }) {
  return (
    <div className={`sc-stat${tone ? ` sc-stat--${tone}` : ''}`}>
      <span className="sc-stat__value">{value}</span>
      <span className="sc-stat__label">{label}</span>
    </div>
  )
}

export default function SavedCircuitDetail({ detail, onBack, onShowOnMap  }) {
  const summary = detail.wizard_summary
  const params = detail.params
  const budget = params?.budget
  const locked = detail.status === 'locked'

  const overBudget =
    summary != null && summary.budget_max != null && summary.total_price > summary.budget_max

  const warnings = []
  if (overBudget) {
    warnings.push(
      `Le coût estimé (${summary.total_price} DT) dépasse le budget maximal (${summary.budget_max} DT).`,
    )
  }
  if (summary && summary.unknown_price_count > 0) {
    warnings.push(
      `${summary.unknown_price_count} prix non renseigné${summary.unknown_price_count > 1 ? 's' : ''} : le coût réel peut être plus élevé.`,
    )
  }

  const criteria = params
    ? [
        [
          'Tarif',
          `${TARIFF_LABELS[budget?.type ?? ''] ?? budget?.type ?? 'Non précisé'}${
            budget?.amount != null ? ` · budget ${budget.amount} DT` : ''
          }`,
        ],
        ['Transport', TRANSPORT_LABELS[params.transport ?? ''] ?? params.transport ?? 'Non précisé'],
        ['Mobilité', MOBILITY_LABELS[params.mobilite ?? ''] ?? params.mobilite ?? 'Non précisé'],
        ['Horaires', formatTime(detail)],
        ['Époques', formatList(params.epoques)],
        ['Fonctions', formatList(params.fonctions)],
        ['Sites imposés', mustVisitNames(detail)],
      ]
    : []

  return (
    <section className="circuits-page sc-page">
      <button type="button" className="circuits-btn sc-back" onClick={onBack}>
        ← Retour à mes circuits
      </button>

      <header className="sc-hero">
        <div>
          <h1>{detail.title}</h1>
          <p className="sc-hero__meta">
            Enregistré le {new Date(detail.created_at).toLocaleDateString('fr-FR')} · lecture seule
          </p>
        </div>
        <span className={`sc-badge${locked ? ' sc-badge--locked' : ''}`}>
          {locked ? 'Verrouillé' : 'Enregistré'}
        </span>
      </header>

      {!summary ? (
        <p className="circuits-error" role="alert">
          Les étapes de ce circuit ne sont pas disponibles{locked ? ' : il est verrouillé.' : '.'}
        </p>
      ) : (
        <>
          <div className="sc-actions">
            <button
              type="button"
              className="circuits-btn circuits-btn--primary"
              onClick={() => onShowOnMap?.(summary, detail.id)}
            >
              🗺 Afficher sur la carte
            </button>
          </div>

          {summary.summary && <p className="sc-summary">{summary.summary}</p>}

          <div className="sc-stats">
            <Stat label="Étapes" value={summary.monuments.length} />
            <Stat label="Durée totale" value={`${Math.round(summary.total_duration_min)} min`} />
            <Stat
              label="Coût estimé"
              value={`${summary.total_price} DT`}
              tone={overBudget ? 'danger' : undefined}
            />
            {summary.budget_max != null && (
              <Stat label="Budget maximal" value={`${summary.budget_max} DT`} />
            )}
          </div>

          {warnings.map((w) => (
            <p key={w} className="circuits-warning" role="alert">
              ⚠️ {w}
            </p>
          ))}

          <h2 className="sc-title">Les étapes</h2>
          <ol className="sc-steps">
            {summary.monuments.map((stop) => (
              <li key={`${stop.order}-${stop.name}`} className="sc-step">
                <span className="sc-step__badge">{stop.order}</span>
                <div className="sc-step__body">
                  <strong>{stop.name}</strong>
                  <div className="sc-step__meta">
                    <span className="sc-chip">⏱ {Math.round(stop.visit_duration_min)} min</span>
                    <span className="sc-chip">{formatPrice(stop.price)}</span>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {criteria.length > 0 && (
        <>
          <h2 className="sc-title">Vos critères</h2>
          <dl className="sc-criteria">
            {criteria.map(([label, value]) => (
              <div key={label} className="sc-criterion">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </section>
  )
}