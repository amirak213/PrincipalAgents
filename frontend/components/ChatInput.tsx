import { useState, useRef } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  loading: boolean;
}

export function ChatInput({ onSend, loading }: ChatInputProps) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSend(input);
      setInput('');
      inputRef.current?.focus();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-primary-dark bg-background">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-4">
        <div className="flex gap-2 md:gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about history, culture, or technology..."
            disabled={loading}
            className="flex-1 px-4 py-3 rounded-lg bg-surface border border-primary-dark text-text placeholder-opacity-60 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary focus:ring-opacity-50 disabled:opacity-50 transition-all duration-200"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 md:px-6 py-3 rounded-lg bg-gradient-to-r from-primary to-primary-light text-background font-semibold hover:shadow-lg hover:shadow-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="inline-block animate-spin">⏳</span>
                <span className="hidden sm:inline">Thinking...</span>
              </>
            ) : (
              <>
                <span>Send</span>
                <span>→</span>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
