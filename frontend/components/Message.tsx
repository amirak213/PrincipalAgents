interface MessageProps {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export function Message({ text, isUser, timestamp }: MessageProps) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-gradient-to-r from-primary to-primary-light text-background font-medium'
            : 'bg-surface border border-primary-dark text-text'
        }`}
      >
        <p className="text-sm md:text-base break-words">{text}</p>
        <span className={`text-xs mt-1 block ${isUser ? 'text-background opacity-75' : 'text-primary opacity-75'}`}>
          {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}
