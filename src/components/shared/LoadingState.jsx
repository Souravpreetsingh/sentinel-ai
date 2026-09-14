export default function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-primary animate-pulse"></span>
        <span
          className="h-2 w-2 rounded-full bg-primary animate-pulse"
          style={{ animationDelay: '0.15s' }}
        ></span>
        <span
          className="h-2 w-2 rounded-full bg-primary animate-pulse"
          style={{ animationDelay: '0.3s' }}
        ></span>
      </div>
      <span className="font-label-xs text-outline text-[11px] tracking-widest uppercase">
        {message}
      </span>
    </div>
  );
}
