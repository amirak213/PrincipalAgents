import { useState, useEffect, useRef } from 'react'

const SLIDES = [
  { src: '/assets/images/whatsapp-1.png', alt: 'Groupe de touristes à Carthage - selfie' },
  { src: '/assets/images/whatsapp-2.png', alt: 'Groupe de touristes à Carthage' },
  { src: '/assets/images/whatsapp-3.png', alt: 'Visiteurs aux ruines de Carthage' },
  { src: '/assets/images/whatsapp-4.png', alt: 'Touristes explorant le site historique' },
]

const DESTINATIONS = [
  { value: 'carthage', label: 'Carthage', image: '/assets/images/carthage.png' },
  { value: 'la-marsa', label: 'La Marsa', image: '/assets/images/la-marsa.png' },
]

const DUREES = [
  { value: 'demi-journee', label: 'Demi Journée' },
  { value: 'journee-complete', label: 'Journée Complète' },
  { value: 'pack-visiteur', label: 'Pack Visiteur Demi Journée' },
  { value: 'pack-guide', label: 'Pack Guide Demi Journée' },
  { value: 'pack-velo', label: 'Pack Vélo Journée Complète' },
  { value: 'pack-vacance', label: 'Pack Vacance Journée Complète' },
]

function ChevronIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function HeroDropdown({ label, value, options, onChange, withImages = false }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const selected = options.find((o) => o.value === value)
  const displayLabel = selected ? selected.label : label

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className={`hero__dropdown ${open ? 'hero__dropdown--open' : ''}`} ref={ref}>
      <button
        type="button"
        className="hero__search-field"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {withImages && selected?.image && (
          <img src={selected.image} alt="" className="hero__dropdown-thumb" />
        )}
        <span className={selected ? 'hero__dropdown-selected' : 'hero__dropdown-placeholder'}>
          {displayLabel}
        </span>
        <ChevronIcon />
      </button>

      {open && (
        <ul className="hero__dropdown-menu" role="listbox">
          {options.map((option) => (
            <li key={option.value} role="option" aria-selected={value === option.value}>
              <button
                type="button"
                className={`hero__dropdown-item ${value === option.value ? 'hero__dropdown-item--active' : ''}`}
                onClick={() => {
                  onChange(option.value)
                  setOpen(false)
                }}
              >
                {withImages && option.image && (
                  <img src={option.image} alt="" className="hero__dropdown-item-img" />
                )}
                <span>{option.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Hero() {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [destination, setDestination] = useState('')
  const [duree, setDuree] = useState('')

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDES.length)
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  function handleReserve() {
    const destLabel = DESTINATIONS.find((d) => d.value === destination)?.label || '—'
    const dureeLabel = DUREES.find((d) => d.value === duree)?.label || '—'
    alert(`Réservation\nDestination : ${destLabel}\nDurée : ${dureeLabel}`)
  }

  return (
    <section className="hero" id="accueil">
      <div className="hero__image-wrapper">
        {SLIDES.map((slide, index) => (
          <img
            key={slide.src}
            src={slide.src}
            alt={slide.alt}
            className={`hero__image ${index === currentSlide ? 'hero__image--active' : ''}`}
          />
        ))}
        <div className="hero__overlay">
          <p className="hero__brand">DOURBIA</p>
          <h1 className="hero__title">Vos Expériences Culturelles</h1>
          <img
            src="/assets/images/a-la-carte.png"
            alt="À LA CARTE"
            className="hero__badge"
          />
        </div>
      </div>

      <div className="hero__search">
        <div className="hero__search-inner">
          <HeroDropdown
            label="Destination"
            value={destination}
            options={DESTINATIONS}
            onChange={setDestination}
            withImages
          />
          <HeroDropdown
            label="Durée"
            value={duree}
            options={DUREES}
            onChange={setDuree}
          />
          <button className="hero__search-btn" onClick={handleReserve}>
            Réservez Maintenant
          </button>
        </div>
      </div>

      <div className="hero__dots">
        {SLIDES.map((_, i) => (
          <button
            key={i}
            type="button"
            className={`hero__dot ${i === currentSlide ? 'hero__dot--active' : ''}`}
            onClick={() => setCurrentSlide(i)}
            aria-label={`Slide ${i + 1}`}
          />
        ))}
      </div>
    </section>
  )
}

export default Hero
