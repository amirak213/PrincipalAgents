import { AUTH_API_BASE } from './config'
import { ApiError } from './errors'

const REQUEST_TIMEOUT_MS = 15_000

async function request(path, init, accessToken) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  const headers = new Headers({ 'Content-Type': 'application/json' })

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  new Headers(init?.headers).forEach((value, key) => headers.set(key, value))

  try {
    const response = await fetch(`${AUTH_API_BASE}${path}`, {
      credentials: 'include',
      ...init,
      signal: controller.signal,
      headers,
    })

    if (response.status === 204) {
      return undefined
    }

    if (!response.ok) {
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }

      const detail =
        typeof payload === 'object' && payload !== null && 'detail' in payload
          ? payload.detail
          : undefined
      let message
      if (response.status === 429) {
        message =
          typeof detail === 'string'
            ? detail
            : 'Trop de tentatives. Réessayez dans quelques instants.'
      } else if (typeof detail === 'string') {
        message = detail
      } else if (response.status === 422 && Array.isArray(detail)) {
        message = 'Données invalides.'
      } else {
        message = `Erreur ${response.status}`
      }
      throw new ApiError(response.status, message)
    }

    return await response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

function jsonBody(value) {
  return { method: 'POST', body: JSON.stringify(value) }
}

export const authApi = {
  register(email, password, fullName) {
    return request(
      '/api/auth/register',
      jsonBody({
        email,
        password,
        ...(fullName !== undefined ? { full_name: fullName } : {}),
      }),
    )
  },

  login(email, password) {
    return request('/api/auth/login', jsonBody({ email, password }))
  },

  refresh() {
    return request('/api/auth/refresh', { method: 'POST' })
  },

  logout() {
    return request('/api/auth/logout', { method: 'POST' })
  },

  me(accessToken) {
    return request('/api/auth/me', { method: 'GET' }, accessToken)
  },
  verifyEmail(token) {
    return request('/api/auth/verify-email', jsonBody({ token }))
  },

  resendVerification(accessToken) {
    return request(
      '/api/auth/resend-verification',
      { method: 'POST' },
      accessToken,
    )
  },

  forgotPassword(email) {
    return request('/api/auth/forgot-password', jsonBody({ email }))
  },

  resetPassword(token, newPassword) {
    return request(
      '/api/auth/reset-password',
      jsonBody({ token, new_password: newPassword }),
    )
  },
}