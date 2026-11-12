function AppDemo() {
  return (
    <section className="app-demo">
      <div className="container">
        <div className="app-demo__grid">
          <div className="app-demo__left">
            <h2 className="app-demo__title">
              Fonctionnalités Révolutionnaires Pour Une Expérience Inégalée
            </h2>
            <div className="app-demo__buttons">
              <button className="app-demo__btn">Devenir Partenaire</button>
              <button className="app-demo__btn">Devenir Expert</button>
            </div>
          </div>

          <div className="app-demo__center">
            <img
              src="/assets/images/phone-mockup.png"
              alt="Application Dourbia sur smartphone"
              className="app-demo__phone"
            />
            <span className="app-demo__label">DÉMO</span>
          </div>

          <div className="app-demo__right">
            <img
              src="/assets/images/logo-qp.png"
              alt="dourbia - guide me !"
              className="app-demo__logo"
            />
            <img
              src="/assets/images/app-download.png"
              alt="Télécharger l'application - Google Play, App Store et QR Code"
              className="app-demo__download"
            />
          </div>
        </div>
      </div>
    </section>
  )
}

export default AppDemo
