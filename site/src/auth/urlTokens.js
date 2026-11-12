let consumedTokens = null

export function parseAuthTokens(search) {
  const params = new URLSearchParams(
    search.startsWith('?') ? search.slice(1) : search,
  )
  const verifyEmail = params.get('verify_email')
  const resetPassword = params.get('reset_password')
  params.delete('verify_email')
  params.delete('reset_password')
  const remaining = params.toString()

  return {
    verifyEmail: verifyEmail || null,
    resetPassword: resetPassword || null,
    cleanedSearch: remaining ? `?${remaining}` : '',
  }
}

export function consumeAuthTokensOnce() {
  if (consumedTokens) {
    return consumedTokens
  }

  if (typeof window === 'undefined') {
    consumedTokens = {
      verifyEmail: null,
      resetPassword: null,
      cleanedSearch: '',
    }
    return consumedTokens
  }

  consumedTokens = parseAuthTokens(window.location.search)
  if (consumedTokens.cleanedSearch !== window.location.search) {
    window.history.replaceState(
      null,
      '',
      `${window.location.pathname}${consumedTokens.cleanedSearch}${window.location.hash}`,
    )
  }
  return consumedTokens
}