import { authApi } from './authApi'
import { ApiError } from './errors'

const HINT_KEY = 'dourbia_auth_hint'

let accessToken = null
let user = null
const listeners = new Set()
let refreshInFlight = null

function writeHint(on) {
  try {
    if (on) {
      localStorage.setItem(HINT_KEY, '1')
    } else {
      localStorage.removeItem(HINT_KEY)
    }
  } catch {
    // Stockage indisponible (navigation privée) : on continue sans indice.
  }
}

function notify() {
  listeners.forEach((listener) => listener())
}

export function hasSessionHint() {
  try {
    return localStorage.getItem(HINT_KEY) === '1'
  } catch {
    return false
  }
}

export function getAccessToken() {
  return accessToken
}

export function getUser() {
  return user
}

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function setSession(tokenResponse) {
  accessToken = tokenResponse.access_token
  user = tokenResponse.user
  writeHint(true)
  notify()
}

export function updateSessionUser(nextUser) {
  user = nextUser
  notify()
}

export function clearSession() {
  accessToken = null
  user = null
  writeHint(false)
  notify()
}

export function refreshSession() {
  if (refreshInFlight) {
    return refreshInFlight
  }
  if (!accessToken && !hasSessionHint()) {
    return Promise.resolve(null)
  }

  const inFlight = authApi
    .refresh()
    .then((tokenResponse) => {
      setSession(tokenResponse)
      return tokenResponse
    })
    .catch((error) => {
      if (error instanceof ApiError && error.status === 401) {
        clearSession()
      }
      return null
    })
    .finally(() => {
      if (refreshInFlight === inFlight) {
        refreshInFlight = null
      }
    })

  refreshInFlight = inFlight
  return inFlight
}