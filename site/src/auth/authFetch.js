import { AUTH_API_BASE } from './config'
import { getAccessToken, refreshSession } from './session'

function withBearer(headersInit, token) {
  const headers = new Headers(headersInit)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

export async function authFetch(input, init = {}) {
  const url = input.startsWith('/') ? `${AUTH_API_BASE}${input}` : input
  const initialToken = getAccessToken()

  function send(token) {
    return fetch(url, {
      ...init,
      credentials: 'include',
      headers: withBearer(init.headers, token),
    })
  }

  const response = await send(initialToken)
  if (response.status !== 401) {
    return response
  }

  const refreshed = await refreshSession()
  if (!refreshed) {
    return response
  }

  return send(refreshed.access_token)
}