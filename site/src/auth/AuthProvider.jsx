import { useCallback, useEffect, useMemo, useState } from 'react'
import { authApi } from './authApi'
import { AuthContext } from './context'
import {
  clearSession,
  getAccessToken,
  getUser,
  hasSessionHint,
  refreshSession,
  setSession,
  subscribe,
} from './session'

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading')
  const [user, setUser] = useState(() => getUser())
  const [dialog, setDialog] = useState(null)

  useEffect(() => {
    return subscribe(() => {
      const nextUser = getUser()
      setUser(nextUser)
      setStatus(getAccessToken() && nextUser ? 'authenticated' : 'anonymous')
    })
  }, [])

  useEffect(() => {
    if (!getAccessToken() && !hasSessionHint()) {
      setUser(getUser())
      setStatus('anonymous')
      return
    }

    let active = true
    void refreshSession().then((result) => {
      if (active) {
        setUser(getUser())
        setStatus(result ? 'authenticated' : 'anonymous')
      }
    })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (email, password) => {
    setSession(await authApi.login(email, password))
  }, [])

  const register = useCallback(async (email, password, fullName) => {
    setSession(await authApi.register(email, password, fullName))
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // La déconnexion locale doit aboutir même si le serveur est injoignable.
    } finally {
      clearSession()
    }
  }, [])

  const openDialog = useCallback(
  (view = 'login', extra) =>
    setDialog(
      extra?.resetToken ? { view, resetToken: extra.resetToken } : { view },
    ),
  [],
)
  const closeDialog = useCallback(() => setDialog(null), [])

  const value = useMemo(
    () => ({
      status,
      user,
      isAdmin: user?.role === 'admin',
      isVerified: user?.is_verified ?? false,
      login,
      register,
      logout,
      dialog,
      openDialog,
      closeDialog,
    }),
    [status, user, login, register, logout, dialog, openDialog, closeDialog],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}