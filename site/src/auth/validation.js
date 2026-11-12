export function isValidEmail(value) {
  const email = value.trim()
  return email.length <= 320 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)
}

export function validatePassword(value) {
  if (value.length < 10) {
    return 'Le mot de passe doit contenir au moins 10 caractères.'
  }
  if (value.length > 128) {
    return 'Le mot de passe ne doit pas dépasser 128 caractères.'
  }
  return null
}