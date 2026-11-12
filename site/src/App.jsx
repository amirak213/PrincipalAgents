import { lazy, Suspense, useEffect, useState } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import TopDestinations from './components/TopDestinations'
import Features from './components/Features'
import AppDemo from './components/AppDemo'
import Packages from './components/Packages'
import Testimonials from './components/Testimonials'
import Footer from './components/Footer'
import { AuthDialog } from './auth'
import { AuthCallbacks } from './auth/AuthCallbacks'
import CircuitsPage from './pages/CircuitsPage'
import './App.css'

const DourbiaChatEmbed = lazy(() => import('./components/DourbiaChatEmbed'))

function routeFromHash() {
  return window.location.hash === '#mes-circuits' ? 'circuits' : 'home'
}

function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [route, setRoute] = useState(routeFromHash)
  const [pendingCircuit, setPendingCircuit] = useState(null)

  function handleShowCircuitOnMap(circuit, savedCircuitId) {
    // Le compteur permet de renvoyer le même circuit si l'utilisateur reclique.
    setPendingCircuit({ circuit, savedCircuitId, nonce: Date.now() })
    setChatOpen(true)}

  useEffect(() => {
    function handleHashChange() {
      setRoute(routeFromHash())
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Retour à la landing : l'ancre n'existait pas encore au moment du clic, on défile après le rendu.
  useEffect(() => {
    if (route !== 'home') return
    const id = window.location.hash.slice(1)
    if (id) document.getElementById(id)?.scrollIntoView()
  }, [route])

  return (
    <div className="app">
      <Header />
      <main>
        {route === 'circuits' ? (
          <CircuitsPage
            onBack={() => { window.location.hash = 'accueil' }}
            onShowOnMap={handleShowCircuitOnMap}
          />
        ) : (
          <>
            <Hero />
            <TopDestinations />
            <Features />
            <AppDemo />
            <Packages />
            <Testimonials />
          </>
        )}
      </main>
      <Footer />
      <AuthDialog />
      <AuthCallbacks />
      <button
        className="dourbia-chat-launcher"
        type="button"
        aria-label="Ouvrir le guide Dourbia"
        aria-expanded={chatOpen}
        onClick={() => setChatOpen(true)}
      >
        <img src="/assets/images/dourbia-icon.png" alt="" />
      </button>
      {chatOpen && (
        <Suspense fallback={null}>
          <DourbiaChatEmbed
            onClose={() => setChatOpen(false)}
            pendingCircuit={pendingCircuit}
            onCircuitDelivered={() => setPendingCircuit(null)}
          />
        </Suspense>
      )}
    </div>
  )
}

export default App
