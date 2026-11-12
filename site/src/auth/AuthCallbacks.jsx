import { useLayoutEffect, useState } from 'react'
import { authApi } from './authApi'
import { refreshSession } from './session'
import { consumeAuthTokensOnce } from './urlTokens'
import { useAuth } from './useAuth'


const verificationRequests = new Set()

export function AuthCallbacks() {
  const { openDialog } = useAuth()
  const [notice, setNotice] = useState(null)

  useLayoutEffect(() => {
    const tokens = consumeAuthTokensOnce()

    if (tokens.verifyEmail && !verificationRequests.has(tokens.verifyEmail)) {
      verificationRequests.add(tokens.verifyEmail)
      void authApi
        .verifyEmail(tokens.verifyEmail)
        .then(() => {
          setNotice({ type: 'success', text: 'Adresse email vérifiée.' })
          void refreshSession()
        })
        .catch(() => {
          setNotice({ type: 'error', text: 'Lien invalide ou expiré.' })
        })
    }

    if (tokens.resetPassword) {
      openDialog('reset', { resetToken: tokens.resetPassword })
    }
  }, [openDialog])

  if (!notice) return null

  return (
    <div
      className={`auth-notice auth-notice-${notice.type}`}
      role={notice.type === 'error' ? 'alert' : 'status'}
    >
      <span>{notice.text}</span>
      <button
        type="button"
        aria-label="Fermer"
        onClick={() => setNotice(null)}
      >
        &times;
      </button>
    </div>
  )
}