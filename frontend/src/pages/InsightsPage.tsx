import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Banner, EmptyState, LoadingBlock } from "../components/ui";
import { formatMoney, formatPercent } from "../lib/format";
import type { Analysis, Page, Project } from "../types";

export default function InsightsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        setProjects(response.data.items);
        if (response.data.items[0]) setProjectId(String(response.data.items[0].id));
      })
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setLoadingProjects(false));
  }, []);

  async function analyze() {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.post<Analysis>(`/api/projects/${projectId}/ai/analyze`);
      setAnalysis(response.data);
    } catch (reason) {
      setAnalysis(null);
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">AI cost insights</h1>
        <p className="mt-1 max-w-3xl text-sm text-mist">
          Unusual amounts are flagged with a leave-one-out Tukey fence when a category has at least four other records.
          If no model key is configured, the narrative is rule-based.
        </p>
      </div>
      <Banner tone="info">
        AI-generated explanations may be inaccurate and should be reviewed before financial decisions are made.
        A large amount is not evidence of fraud.
      </Banner>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {loadingProjects ? <LoadingBlock /> : null}
      <section className="card flex flex-wrap items-end gap-3">
        <label className="min-w-64 flex-1">
          <span className="label">Project</span>
          <select className="field" value={projectId} onChange={(event) => { setProjectId(event.target.value); setAnalysis(null); }}>
            <option value="">Select a project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </label>
        <button className="btn-primary" type="button" disabled={!projectId || busy} onClick={() => void analyze()}>
          {busy ? "Analyzing..." : "Analyze costs"}
        </button>
      </section>
      {!analysis && !busy ? (
        <EmptyState title="No analysis yet" body="Choose one of your projects and run the analysis. Only that project's records are used." />
      ) : null}
      {analysis ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-lavender-100 px-3 py-1 text-sm font-semibold text-primary-700">{analysis.mode_label}</span>
            <span className="rounded-full bg-mint-100 px-3 py-1 text-sm font-semibold text-emerald-800">{analysis.budget_health_label}</span>
          </div>
          {analysis.fallback_reason ? <Banner tone="info">{analysis.fallback_reason}</Banner> : null}
          <section className="card">
            <h2 className="text-lg font-semibold">Cost summary</h2>
            <p className="mt-2 text-sm leading-6">{analysis.summary}</p>
            <p className="mt-3 text-sm text-mist">
              Aggregate variance {formatMoney(analysis.summary_metrics.total_variance, analysis.currency)} (
              {formatPercent(analysis.summary_metrics.percentage_variance)}).
            </p>
          </section>
          <section className="card">
            <h2 className="font-semibold">Highest spending categories</h2>
            <ul className="mt-2 space-y-1 text-sm">
              {analysis.highest_spending_categories.map((item) => (
                <li key={item.category}>{item.category}: {formatMoney(item.actual_cost, analysis.currency)} actual</li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h2 className="font-semibold">Expenses over their estimates</h2>
            {analysis.over_budget_expenses.length === 0 ? <p className="mt-2 text-sm text-mist">None in this project.</p> : (
              <ul className="mt-2 space-y-1 text-sm">
                {analysis.over_budget_expenses.map((item) => (
                  <li key={`${item.expense_name}-${item.category}`}>
                    {item.expense_name} ({item.category}): {formatMoney(item.variance, analysis.currency)} over
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="card">
            <h2 className="font-semibold">Unusual expenses for review</h2>
            {analysis.anomalies.length === 0 ? <p className="mt-2 text-sm text-mist">No statistical flags. This can mean the sample is too small or the amounts sit inside the usual range.</p> : (
              <ul className="mt-2 space-y-2 text-sm">
                {analysis.anomalies.map((item) => (
                  <li key={`${item.expense_name}-${item.actual_cost}`}>
                    <span className="font-medium">{item.expense_name}</span> — {item.reason}
                  </li>
                ))}
              </ul>
            )}
            {analysis.insufficient_sample.length ? (
              <ul className="mt-3 space-y-1 text-sm text-mist">
                {analysis.insufficient_sample.map((item) => <li key={item.category}>{item.message}</li>)}
              </ul>
            ) : null}
          </section>
          <section className="card">
            <h2 className="font-semibold">Hypotheses, not facts</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {analysis.hypotheses.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </section>
          <section className="card">
            <h2 className="font-semibold">Recommendations</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {analysis.recommendations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </section>
          <p className="text-sm text-mist">{analysis.disclaimer}</p>
        </div>
      ) : null}
    </div>
  );
}
