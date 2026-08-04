import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="glass-panel mx-auto max-w-lg p-10 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="mt-2 font-display text-2xl font-semibold">Page not found</h1>
      <p className="mt-2 text-ink-muted">That page does not exist. Check the URL or return home.</p>
      <Link to="/" className="btn-primary mt-6">
        Back home
      </Link>
    </div>
  );
}
