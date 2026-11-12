function TopDestinations() {
  const destinations = [
    { name: 'Carthage', image: '/assets/images/carthage.png' },
    { name: 'La Marsa', image: '/assets/images/la-marsa.png' },
  ]

  return (
    <section className="destinations" id="destinations">
      <div className="container">
        <p className="section-label">DÉCOUVREZ NOS EXPÉRIENCES</p>
        <h2 className="section-title">TOP Destinations</h2>

        <div className="destinations__grid">
          {destinations.map((dest) => (
            <div key={dest.name} className="destinations__card">
              <img src={dest.image} alt={dest.name} className="destinations__card-image" />
              <span className="destinations__card-label">{dest.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default TopDestinations
