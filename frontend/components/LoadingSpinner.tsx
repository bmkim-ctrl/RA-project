export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return <div style={{ color: 'var(--muted)', fontSize: 14 }}>{message}</div>;
}
