interface ChatHeaderProps {
  onClear: () => void;
}

export function ChatHeader({ onClear }: ChatHeaderProps) {
  return (
    <div className="bg-white border-b-2 border-primary">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-4 md:py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-primary-light flex items-center justify-center">
              <span className="text-xl font-bold text-white">🏛️</span>
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-primary">
                Dourbia
              </h1>
              <p className="text-xs md:text-sm text-primary-dark opacity-80">
                Explore Tunis • Discover History
              </p>
            </div>
          </div>
          <button
            onClick={onClear}
            className="px-3 md:px-4 py-2 rounded-lg bg-accent hover:bg-accent-alt text-white font-semibold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-accent/40"
          >
            Clear Chat
          </button>
        </div>
      </div>
    </div>
  );
}
