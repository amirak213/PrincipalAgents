import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useAuth } from './useAuth'
import { authApi } from './authApi'
import { ApiError } from './errors'
import { isValidEmail, validatePassword } from './validation'
import './auth.css'

const TITLES = {
  login: 'Se connecter',
  register: 'Créer un compte',
  forgot: 'Mot de passe oublié',
  reset: 'Choisir un nouveau mot de passe',
}

function messageOf(error) {
  if (error instanceof Error && error.message) return error.message
  return 'Une erreur est survenue. Veuillez réessayer.'
}

export function AuthDialog() {
  const { dialog, closeDialog, openDialog, login, register } = useAuth()
  const dialogRef = useRef(null)
  const previousFocusRef = useRef(null)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [pending, setPending] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)
  const [responseMessage, setResponseMessage] = useState(null)
  const [invalidResetToken, setInvalidResetToken] = useState(false)
  const open = Boolean(dialog)

  useEffect(() => {
    if (!open) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeDialog()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return

      const focusable = dialogRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocusRef.current?.focus()
    }
  }, [open, closeDialog])

  useEffect(() => {
    if (!open) {
      setEmail('')
      setFullName('')
      setPassword('')
      setConfirmation('')
      setPending(false)
      setErrorMessage(null)
      setResponseMessage(null)
      setInvalidResetToken(false)
      return
    }
    setErrorMessage(null)
    setInvalidResetToken(false)
    dialogRef.current?.querySelector('input')?.focus()
  }, [open, dialog?.view, dialog?.resetToken])

  if (!dialog || typeof document === 'undefined') return null

  async function handleSubmit(event) {
    event.preventDefault()
    if (pending) return
    setErrorMessage(null)
    setResponseMessage(null)

    const view = dialog.view
    const normalizedEmail = email.trim()
    if (view !== 'reset' && !isValidEmail(normalizedEmail)) {
      setErrorMessage('Veuillez saisir une adresse email valide.')
      return
    }
    if (view === 'register' || view === 'reset') {
      const passwordError = validatePassword(password)
      if (passwordError) {
        setErrorMessage(passwordError)
        return
      }
    }

    if (view === 'reset') {
      if (password !== confirmation) {
        setErrorMessage('Les mots de passe ne correspondent pas.')
        return
      }
      if (!dialog.resetToken) {
        setErrorMessage('Le lien de réinitialisation est invalide.')
        setInvalidResetToken(true)
        return
      }
    }

    setPending(true)
    try {
      if (view === 'login') {
        await login(normalizedEmail, password)
        closeDialog()
      } else if (view === 'register') {  
        await register(normalizedEmail, password, fullName.trim() || undefined)
        closeDialog()
      } else if (view === 'forgot') {
        const result = await authApi.forgotPassword(normalizedEmail)
        setResponseMessage(result.message)
      } else {
        await authApi.resetPassword(dialog.resetToken, password)
        setPassword('')
        setConfirmation('')
        openDialog('login')
        setResponseMessage('Mot de passe mis à jour. Connectez-vous.')
      }
    } catch (error) {
      setErrorMessage(messageOf(error))
      setInvalidResetToken(
        view === 'reset' &&
          error instanceof ApiError &&
          [400, 401, 404, 410, 422].includes(error.status),
      )
    } finally {
      setPending(false)
    }
  }

  function changeView(view) {
    setErrorMessage(null)
    setResponseMessage(null)
    openDialog(view)
  }

  const isLogin = dialog.view === 'login'
  const hasEmail = ['login', 'register', 'forgot'].includes(dialog.view)
  const hasPassword = ['login', 'register', 'reset'].includes(dialog.view)
  const isNewPassword = dialog.view === 'register' || dialog.view === 'reset'

  return createPortal(
    <div
      className="auth-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeDialog()
      }}
    >
      <section
        ref={dialogRef}
        className="auth-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-dialog-title"
      >
        <button
          type="button"
          className="auth-dialog-close"
          onClick={closeDialog}
          aria-label="Fermer"
        >
          ×
        </button>
        <h2 id="auth-dialog-title">{TITLES[dialog.view]}</h2>
        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          {dialog.view === 'register' && (
            <div className="auth-field">
              <label htmlFor="auth-full-name">Nom (facultatif)</label>
              <input
                id="auth-full-name"
                name="name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </div>
          )}

          {hasEmail && (
            <div className="auth-field">
              <label htmlFor="auth-email">Adresse email</label>
              <input
                id="auth-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
          )}

          {hasPassword && (
            <div className="auth-field">
              <label htmlFor="auth-password">
                {isLogin ? 'Mot de passe' : 'Nouveau mot de passe'}
              </label>
              {isNewPassword && (
                <span className="auth-field-help">10 caractères minimum</span>
              )}
              <input
                id="auth-password"
                name="password"
                type="password"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
          )}

          {dialog.view === 'reset' && (
            <div className="auth-field">
              <label htmlFor="auth-password-confirmation">
                Confirmer le nouveau mot de passe
              </label>
              <input
                id="auth-password-confirmation"
                name="password-confirmation"
                type="password"
                autoComplete="new-password"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                required
              />
            </div>
          )}

          {errorMessage && (
            <p className="auth-form-error" role="alert">
              {errorMessage}
            </p>
          )}
          {responseMessage && (
            <p className="auth-form-message" role="status">
              {responseMessage}
            </p>
          )}

          <button className="auth-primary-button" type="submit" disabled={pending}>
            {pending
              ? 'Veuillez patienter…'
              : dialog.view === 'login'
                ? 'Se connecter'
                : dialog.view === 'register'
                  ? 'Créer mon compte'
                  : dialog.view === 'forgot'
                    ? 'Envoyer le lien'
                    : 'Mettre à jour le mot de passe'}
          </button>
        </form>

        <div className="auth-dialog-links">
          {dialog.view === 'login' && (
            <>
              <button type="button" onClick={() => changeView('forgot')}>
                Mot de passe oublié ?
              </button>
              <button type="button" onClick={() => changeView('register')}>
                Créer un compte
              </button>
            </>
          )}
          {(dialog.view === 'register' || dialog.view === 'forgot') && (
            <button type="button" onClick={() => changeView('login')}>
              Retour à la connexion
            </button>
          )}
          {dialog.view === 'reset' && invalidResetToken && (
            <button type="button" onClick={() => changeView('forgot')}>
              Demander un nouveau lien
            </button>
          )}
        </div>
      </section>
    </div>,
    document.body,
  )
}