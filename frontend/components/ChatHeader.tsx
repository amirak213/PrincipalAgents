interface ChatHeaderProps {
  onClear: () => void;
}

export function ChatHeader({ onClear }: ChatHeaderProps) {
  return (
    <div className="bg-gradient-to-r from-background via-surface to-background border-b border-primary-dark">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-4 md:py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-accent-alt flex items-center justify-center">
              <span className="text-xl font-bold text-background">🔬</span>
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-primary-light to-primary bg-clip-text text-transparent">
                Principal Agent
              </h1>
              <p className="text-xs md:text-sm text-primary opacity-90">
                Historical • Cultural • Technical Intelligence
              </p>
            </div>
          </div>
          <button
            onClick={onClear}
            className="px-3 md:px-4 py-2 rounded-lg bg-accent hover:bg-accent-alt text-background font-semibold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-accent"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
