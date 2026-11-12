import { useEffect,useRef, useState } from 'react'
import { useAuth } from '../auth'
import { deleteSavedCircuit, getSavedCircuit, listSavedCircuits } from '../api/savedCircuits'
import SavedCircuitDetail from './SavedCircuitDetail'
import './circuits.css'

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function formatDetails(circuit) {
  const parts = [`${circuit.stops_count} étape${circuit.stops_count > 1 ? 's' : ''}`]
  if (typeof circuit.total_duration_min === 'number') {
    parts.push(`${Math.round(circuit.total_duration_min)} min`)
  }
  if (typeof circuit.total_price === 'number') {
    parts.push(`${circuit.total_price} DT`)
  }
  return parts.join(' · ')
}

export default function CircuitsPage({ onBack , onShowOnMap}) {
  const { status, openDialog } = useAuth()
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [detail, setDetail] = useState(null)
  const [openingId, setOpeningId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [actionError, setActionError] = useState(null)
  const previousStatus = useRef(status)

  // Déconnexion ou session expirée : on efface le circuit ouvert et on quitte la page.
  useEffect(() => {
    if (previousStatus.current === 'authenticated' && status === 'anonymous') {
      setDetail(null)
      onBack()
    }
    previousStatus.current = status
  }, [status, onBack])
  useEffect(() => {
    if (status !== 'authenticated') return
    const controller = new AbortController()
    listSavedCircuits(controller.signal)
      .then(setItems)
      .catch((err) => {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Impossible de charger vos circuits.')
      })
    return () => {
      controller.abort()
      setItems(null)
      setError(null)
    }
  }, [status, reloadKey])

  async function handleOpen(circuit) {
    setActionError(null)
    setOpeningId(circuit.id)
    try {
      setDetail(await getSavedCircuit(circuit.id))
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Impossible de charger ce circuit.')
    } finally {
      setOpeningId(null)
    }
  }

  async function handleDelete(circuit) {
    if (!window.confirm(`Supprimer « ${circuit.title} » ? Cette action est définitive.`)) {
      return
    }
    setActionError(null)
    setDeletingId(circuit.id)
    try {
      await deleteSavedCircuit(circuit.id)
      setItems((current) => current?.filter((item) => item.id !== circuit.id) ?? current)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Suppression impossible.')
    } finally {
      setDeletingId(null)
    }
  }

  if (detail) {
     return (
      <SavedCircuitDetail
        detail={detail}
        onBack={() => setDetail(null)}
        onShowOnMap={onShowOnMap}
      />
    )
  }

  let body
  if (status === 'loading') {
    body = <p>Chargement…</p>
  } else if (status === 'anonymous') {
    body = (
      <div className="circuits-empty">
        <p>Connectez-vous pour retrouver vos circuits enregistrés.</p>
        <button type="button" className="circuits-btn circuits-btn--primary" onClick={() => openDialog('login')}>
          Se connecter
        </button>
      </div>
    )
  } else if (error) {
    body = (
      <div className="circuits-empty">
        <p>{error}</p>
        <button type="button" className="circuits-btn" onClick={() => setReloadKey((key) => key + 1)}>
          Réessayer
        </button>
      </div>
    )
  } else if (items === null) {
    body = <p>Chargement de vos circuits…</p>
  } else if (items.length === 0) {
    body = (
      <div className="circuits-empty">
        <p>Vous n'avez pas encore de circuit enregistré. Créez-en un avec le guide Dourbia.</p>
      </div>
    )
  } else {
    body = (
      <div className="circuits-grid">
        {items.map((circuit) => (
          <article key={circuit.id} className="circuits-card">
            <h3>{circuit.title}</h3>
            <p>{formatDetails(circuit)}</p>
            <p>
              <small>
                Créé le {formatDate(circuit.created_at)}
                {circuit.status === 'locked' ? ' · Verrouillé' : ''}
              </small>
            </p>
            <div className="circuits-actions">
              <button
                type="button"
                className="circuits-btn circuits-btn--primary"
                disabled={openingId === circuit.id}
                onClick={() => void handleOpen(circuit)}
              >
                {openingId === circuit.id ? 'Ouverture…' : 'Consulter'}
              </button>
              <button
                type="button"
                className="circuits-btn"
                disabled={deletingId === circuit.id}
                onClick={() => void handleDelete(circuit)}
              >
                {deletingId === circuit.id ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </article>
        ))}
      </div>
    )
  }

  return (
    <section className="circuits-page">
      <header className="circuits-header">
        <h1>Mes circuits</h1>
        <p>Retrouvez les circuits que vous avez enregistrés avec le guide.</p>
        <button type="button" className="circuits-btn" onClick={onBack}>
          ← Retour à l'accueil
        </button>
      </header>
      {actionError && <p className="circuits-error" role="alert">{actionError}</p>}
      {body}
    </section>
  )
}