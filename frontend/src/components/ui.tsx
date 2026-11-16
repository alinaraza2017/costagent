import { useEffect, type ReactNode } from "react";

export function Spinner() {
  return (
    <span
      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent"
      aria-hidden="true"
    />
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-mist" role="status">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}

export function Banner({
  tone,
  children,
}: {
  tone: "error" | "success" | "info";
  children: ReactNode;
}) {
  const styles = {
    error: "border-coral-100 bg-coral-50 text-rose-800",
    success: "border-mint-100 bg-mint-50 text-emerald-800",
    info: "border-lavender-100 bg-lavender-50 text-slate-700",
  }[tone];
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${styles}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-white px-6 py-12 text-center">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm text-mist">{body}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/30 p-4 sm:items-center" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white p-6 shadow-card"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="dialog-title" className="text-lg font-semibold">
            {title}
          </h2>
          <button type="button" className="btn-ghost px-2 py-1" onClick={onClose} aria-label="Close dialog">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="field-error">{message}</p>;
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <article className="card">
      <p className="text-sm text-mist">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-2 text-sm text-mist">{hint}</p> : null}
    </article>
  );
}
