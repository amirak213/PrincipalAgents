function Testimonials() {
  return (
    <section className="testimonials">
      <div className="container">
        <p className="section-label">TÉMOIGNAGES</p>
        <h2 className="section-title">Ce qu'ils pensent de nous</h2>

        <div className="testimonials__carousel">
          <button
            className="testimonials__arrow testimonials__arrow--left"
            aria-label="Précédent"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>

          <div className="testimonials__phones">
            <img
              src="/assets/images/testimonials.png"
              alt="Témoignages clients sur smartphone"
              className="testimonials__image"
            />
          </div>

          <button
            className="testimonials__arrow testimonials__arrow--right"
            aria-label="Suivant"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  )
}

export default Testimonials
