function Features() {
  const features = [
    {
      icon: '/assets/icons/circuit-pers.png',
      title: 'Guide Numérique',
      description:
        'Explorez les sites historiques avec notre guide interactif. Accédez à des informations détaillées, des cartes et des recommandations personnalisées pour enrichir votre visite.',
    },
    {
      icon: '/assets/icons/circuits-thematiques.png',
      title: 'Packs De Services Diversifiés',
      description:
        'Choisissez parmi une variété de packs adaptés à vos besoins, que vous soyez visiteur, guide ou cycliste. Profitez d\'expériences sur mesure pour chaque type de visiteur.',
    },
    {
      icon: '/assets/icons/icon_service.png',
      title: 'Circuits De Visite Personnalisés',
      description:
        'Créez votre propre parcours en fonction de vos intérêts et de votre temps disponible. Personnalisez chaque étape pour une expérience unique et mémorable.',
    },
  ]

  return (
    <section className="features" id="experiences">
      <div className="container">
        <div className="features__box">
          <div className="features__grid">
            {features.map((feature) => (
              <div key={feature.title} className="features__item">
                <img src={feature.icon} alt="" className="features__icon" />
                <h3 className="features__title">{feature.title}</h3>
                <p className="features__text">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default Features
