import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth'

function Header() {
  const { status, user, logout, openDialog } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const userRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) return
    function handlePointerDown(event) {
      if (userRef.current && !userRef.current.contains(event.target)) {
        setMenuOpen(false)
      }
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [menuOpen])

  const authenticated = status === 'authenticated' && user
  const displayName = user?.full_name?.trim() || 'Mon compte'
  const navLinks = [
    { label: 'Accueil', href: '#accueil', active: true },
    { label: 'À Propos', href: '#apropos' },
    { label: 'Destinations', href: '#destinations' },
    { label: 'Expériences', href: '#experiences' },
    { label: 'Contact', href: '#contact' },
    { label: 'Blog', href: '#blog' },
  ]

  return (
    <header className="header">
      <div className="header__container">
        <a href="#accueil" className="header__logo">
          <img
            src="/assets/images/logo-dourbia.png"
            alt="dourbia - guide me !"
            className="header__logo-img"
          />
        </a>

        <nav className="header__nav">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className={`header__nav-link ${link.active ? 'header__nav-link--active' : ''}`}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="header__actions">
          <button className="header__cart" aria-label="Panier">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 6h15l-1.5 9H7.5L6 6zM6 6L5 3H2"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="9" cy="20" r="1.5" fill="currentColor" />
              <circle cx="18" cy="20" r="1.5" fill="currentColor" />
            </svg>
          </button>

          <div className="header__user" ref={userRef}>
          <button
            className="header__dropdown"
            type="button"
            disabled={status === 'loading'}
            aria-haspopup={authenticated ? 'menu' : 'dialog'}
            aria-expanded={authenticated ? menuOpen : undefined}
            onClick={() => (authenticated ? setMenuOpen((open) => !open) : openDialog('login'))}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
              <path d="M4 20c0-4 3.5-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="2" />
            </svg>
            <span>{authenticated ? displayName : 'Connexion'}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
          {authenticated && menuOpen && (
            <div className="auth-user-dropdown" role="menu">
              <span className="auth-user-email">{user.email}</span>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  window.location.hash = 'mes-circuits'
                }}
              >
                Mes circuits
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  void logout()
                }}
              >
                Se déconnecter
              </button>
            </div>
          )}
          </div>

          <button className="header__dropdown">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
              <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke="currentColor" strokeWidth="2" />
            </svg>
            <span>Français</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
