export function WelcomeBanner() {
  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 py-8 md:py-12">
      <div className="bg-gradient-to-r from-surface via-surface to-surface border border-primary rounded-xl p-6 md:p-8">
        <div className="text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">
            <span className="bg-gradient-to-r from-primary-light via-primary to-accent-alt bg-clip-text text-transparent">
              Welcome to Principal Agent
            </span>
          </h2>
          <p className="text-primary-dark text-sm md:text-base mb-6">
            Explore the intersection of history, culture, and technology
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-background rounded-lg p-4 border border-primary-dark hover:border-primary transition-colors">
              <div className="text-2xl mb-2">📚</div>
              <h3 className="font-semibold text-primary mb-1">Historical</h3>
              <p className="text-xs text-primary-dark">Discover key events and figures</p>
            </div>
            <div className="bg-background rounded-lg p-4 border border-primary-dark hover:border-primary transition-colors">
              <div className="text-2xl mb-2">🌍</div>
              <h3 className="font-semibold text-accent mb-1">Cultural</h3>
              <p className="text-xs text-primary-dark">Understand diverse traditions</p>
            </div>
            <div className="bg-background rounded-lg p-4 border border-primary-dark hover:border-primary transition-colors">
              <div className="text-2xl mb-2">⚙️</div>
              <h3 className="font-semibold text-primary-light mb-1">Technical</h3>
              <p className="text-xs text-primary-dark">Learn cutting-edge innovations</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
