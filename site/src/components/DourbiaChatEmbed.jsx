import {  useCallback, useEffect, useRef, useState } from 'react'

export default function DourbiaChatEmbed({ onClose , pendingCircuit, onCircuitDelivered }) {
  const iframeRef = useRef(null)
  const [wide, setWide] = useState(false)
  let iframeUrl = null
  const readyRef = useRef(false)
  const pendingRef = useRef(pendingCircuit)
  const deliveredRef = useRef(onCircuitDelivered)

  try {
    const configuredUrl = import.meta.env.VITE_DOURBIA_CHAT_URL
    if (configuredUrl) {
      const parsedUrl = new URL(configuredUrl)
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
        throw new Error('Unsupported chat URL protocol')
      }
      parsedUrl.searchParams.set('embed', 'chat')
      iframeUrl = parsedUrl.toString()
    }
  } catch {
    iframeUrl = null
  }
  const expectedOrigin = iframeUrl ? new URL(iframeUrl).origin : null

useEffect(() => {
  pendingRef.current = pendingCircuit
  deliveredRef.current = onCircuitDelivered
})

const flushCircuit = useCallback(() => {
  const pending = pendingRef.current
  const target = iframeRef.current?.contentWindow
  if (!pending || !readyRef.current || !target || !expectedOrigin) return
  target.postMessage(
    {
      source: 'dourbia-site',
      type: 'showCircuit',
      circuit: pending.circuit,
      savedCircuitId: pending.savedCircuitId,
    },
    expectedOrigin,
  )
  deliveredRef.current?.()
}, [expectedOrigin])

  useEffect(() => {
    if (!iframeUrl) return

    
    function handleMessage(event) {
      if (
        event.source !== iframeRef.current?.contentWindow ||
        event.origin !== expectedOrigin ||
        event.data?.source !== 'dourbia-chat' 
        
      ) {
        return
      }

      if (event.data.type === 'layout') {
        setWide(Boolean(event.data.mapOpen))
      } else if (event.data.type === 'ready') {
        readyRef.current = true
        flushCircuit()
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [iframeUrl, expectedOrigin, flushCircuit])

   // Le guide est déjà ouvert et prêt : on envoie le circuit dès qu'il est demandé.
  useEffect(() => {
    if (pendingCircuit) flushCircuit()
  }, [pendingCircuit, flushCircuit])

  return (
    <section
      className={`dourbia-chat-panel${wide ? ' dourbia-chat-panel--wide' : ''}`}
      aria-label="Guide Dourbia"
    >
      <header className="dourbia-chat-header">
        <h2 className="dourbia-chat-title">Guide Dourbia</h2>
        <button
          className="dourbia-chat-close"
          type="button"
          onClick={onClose}
          aria-label="Fermer le guide"
        >
          Fermer
        </button>
      </header>
      {iframeUrl ? (
        <iframe
          className="dourbia-chat-frame"
          title="Guide Dourbia"
          src={iframeUrl}
          ref={iframeRef}
          allow="geolocation"
          referrerPolicy="strict-origin-when-cross-origin"
        />
      ) : (
        <p className="dourbia-chat-error" role="status">
          Le guide est momentanément indisponible.
        </p>
      )}
    </section>
  )
}