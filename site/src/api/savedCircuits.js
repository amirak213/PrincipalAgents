import { authFetch } from '../auth'

async function errorMessage(response, fallback) {
  try {
    const payload = await response.json()
    if (payload && typeof payload.detail === 'string') {
      return payload.detail
    }
  } catch {
    // corps non JSON : message par défaut
  }
  return fallback
}

export async function listSavedCircuits(signal) {
  const response = await authFetch('/api/saved-circuits', { signal })
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Impossible de charger vos circuits.'))
  }
  return response.json()
}

export async function getSavedCircuit(id, signal) {
  const response = await authFetch(`/api/saved-circuits/${encodeURIComponent(id)}`, { signal })
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Impossible de charger ce circuit.'))
  }
  return response.json()
}

export async function deleteSavedCircuit(id) {
  const response = await authFetch(`/api/saved-circuits/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Suppression impossible.'))
  }
}