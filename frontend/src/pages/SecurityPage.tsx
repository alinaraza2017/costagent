import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Banner, LoadingBlock } from "../components/ui";
import type { AuditEvent, ChecklistItem, Page, Threat } from "../types";

export default function SecurityPage() {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [threatResponse, checklistResponse, auditResponse] = await Promise.all([
        api.get<Threat[]>("/api/security/threats"),
        api.get<ChecklistItem[]>("/api/security/checklist"),
        api.get<Page<AuditEvent>>("/api/security/audit"),
      ]);
      setThreats(threatResponse.data);
      setChecklist(checklistResponse.data);
      setAudit(auditResponse.data.items);
      setError("");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function toggle(item: ChecklistItem) {
    try {
      await api.put(`/api/security/checklist/${item.key}`, { completed: !item.completed });
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Security Center</h1>
        <p className="mt-1 max-w-3xl text-sm text-mist">
          Implemented protections are the controls present in this application and covered by automated tests.
          Future improvements are additional work for a production deployment. Checklist items stay incomplete until you mark them during a deployment review.
        </p>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {loading ? <LoadingBlock label="Loading security center" /> : null}
      <div className="space-y-4">
        {threats.map((threat) => (
          <article key={threat.id} className="card space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">{threat.name}</h2>
              <span className="rounded-full bg-mint-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-800">{threat.status.replaceAll("_", " ")}</span>
            </div>
            <p><span className="font-medium">Scenario. </span>{threat.scenario}</p>
            <p><span className="font-medium">Impact. </span>{threat.impact}</p>
            <p><span className="font-medium">Current mitigation. </span>{threat.mitigation}</p>
            <p><span className="font-medium">Test. </span><code className="text-sm">{threat.test_case}</code></p>
            <p className="text-sm text-mist"><span className="font-medium text-ink">Future improvement. </span>{threat.future_improvement}</p>
          </article>
        ))}
      </div>
      <section className="card">
        <h2 className="text-lg font-semibold">Deployment security checklist</h2>
        <p className="mt-1 text-sm text-mist">Mark an item only after you have reviewed it for the environment you are deploying. The application does not check these boxes for you.</p>
        <ul className="mt-4 space-y-3">
          {checklist.map((item) => (
            <li key={item.key} className="rounded-xl border border-line p-3">
              <label className="flex items-start gap-3">
                <input
                  className="mt-1 h-4 w-4"
                  type="checkbox"
                  checked={item.completed}
                  onChange={() => void toggle(item)}
                />
                <span>
                  <span className="font-medium">{item.title}</span>
                  <span className="mt-1 block text-sm text-mist">{item.guidance}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </section>
      <section className="card">
        <h2 className="text-lg font-semibold">Recent security events</h2>
        {audit.length === 0 ? <p className="mt-2 text-sm text-mist">No events for this account yet.</p> : (
          <ul className="mt-3 space-y-2 text-sm">
            {audit.map((event) => (
              <li key={event.id} className="flex flex-wrap justify-between gap-2 border-b border-line py-2">
                <span><span className="font-medium">{event.event_type}</span> — {event.detail}</span>
                <span className="text-mist">{new Date(event.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
