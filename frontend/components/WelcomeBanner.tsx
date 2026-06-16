export function WelcomeBanner() {
  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 py-8 md:py-12">
      <div className="bg-white border-2 border-primary rounded-xl p-6 md:p-8 shadow-sm">
        <div className="text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-2 text-primary">
            Welcome to Dourbia
          </h2>
          <p className="text-primary-dark text-base md:text-lg mb-8">
            Your guide to discovering the beauty of Tunis
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gradient-to-br from-primary-light/10 to-primary/10 rounded-lg p-5 border-l-4 border-primary hover:shadow-md transition-all">
              <h3 className="font-bold text-primary mb-2 text-lg">🚗 Car Rental</h3>
              <p className="text-sm text-primary-dark">Explore Tunis at your own pace with our car rental service</p>
            </div>
            <div className="bg-gradient-to-br from-accent/10 to-accent-alt/10 rounded-lg p-5 border-l-4 border-accent hover:shadow-md transition-all">
              <h3 className="font-bold text-accent mb-2 text-lg">🌦️ Weather</h3>
              <p className="text-sm text-primary-dark">Get real-time weather updates for your Tunis adventure</p>
            </div>
            <div className="bg-gradient-to-br from-primary-light/10 to-primary/10 rounded-lg p-5 border-l-4 border-primary hover:shadow-md transition-all">
              <h3 className="font-bold text-primary mb-2 text-lg">🏛️ Historical Sites</h3>
              <p className="text-sm text-primary-dark">Learn about ancient monuments and historical landmarks</p>
            </div>
            <div className="bg-gradient-to-br from-accent/10 to-accent-alt/10 rounded-lg p-5 border-l-4 border-accent hover:shadow-md transition-all">
              <h3 className="font-bold text-accent mb-2 text-lg">📍 Personalized Tours</h3>
              <p className="text-sm text-primary-dark">Discover custom circuits tailored to your interests</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
