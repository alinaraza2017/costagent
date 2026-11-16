import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errorMessage } from "../api/client";
import { Banner, EmptyState, LoadingBlock, StatCard } from "../components/ui";
import { formatMoney, formatStatus } from "../lib/format";
import type { Page, PertAnalysis, Project } from "../types";

function plainPercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "N/A";
  }
  return `${value.toFixed(2)}%`;
}

export default function PertPage() {
  const [searchParams] = useSearchParams();
  const requested = searchParams.get("project") ?? "";
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(requested);
  const [analysis, setAnalysis] = useState<PertAnalysis | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        setProjects(response.data.items);
        setProjectId((current) => current || requested || String(response.data.items[0]?.id ?? ""));
      })
      .catch((reason) => setError(errorMessage(reason)));
  }, [requested]);

  useEffect(() => {
    if (!projectId) {
      setAnalysis(null);
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    api.get<PertAnalysis>(`/api/projects/${projectId}/pert`)
      .then((response) => {
        if (!active) return;
        setAnalysis(response.data);
        setError("");
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  async function suggest() {
    if (!projectId) return;
    setBusy(true);
    setNotice("");
    try {
      const response = await api.post<PertAnalysis>(`/api/projects/${projectId}/pert/suggest`);
      setAnalysis(response.data);
      setNotice(
        response.data.suggested_count
          ? `Suggested three-point values were saved for ${response.data.suggested_count} cost records.`
          : "Every cost record already has a three-point estimate.",
      );
      setError("");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const currency = analysis?.currency ?? "PKR";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">PERT analysis</h1>
          <p className="mt-1 max-w-3xl text-sm text-mist">
            Three-point estimates turn an optimistic, most likely, and pessimistic cost into an expected cost and a spread.
          </p>
        </div>
        <label className="min-w-64">
          <span className="label">Project</span>
          <select className="field" value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            {projects.length === 0 ? <option value="">No projects yet</option> : null}
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {notice ? <Banner tone="success">{notice}</Banner> : null}
      {!projectId ? (
        <EmptyState title="Add a project first" body="PERT runs on the cost records saved for one project." />
      ) : loading || !analysis ? (
        <LoadingBlock label="Calculating PERT" />
      ) : (
        <>
          <Banner tone="info">{analysis.assumption}</Banner>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Expected cost" value={formatMoney(analysis.expected_cost, currency)} hint={`${analysis.activity_count} activities included`} />
            <StatCard label="Standard deviation" value={formatMoney(analysis.std_dev, currency)} hint="Square root of the summed activity variances" />
            <StatCard label="Variance" value={analysis.variance === null ? "—" : analysis.variance.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} hint="Sum of activity variances" />
            <StatCard
              label="Chance within budget"
              value={plainPercent(analysis.budget_probability)}
              hint={`Budget ${formatMoney(analysis.budget, currency)} · ${formatStatus(projects.find((project) => String(project.id) === projectId)?.status ?? "")}`}
            />
          </section>
          {analysis.ranges.length ? (
            <section className="grid gap-4 md:grid-cols-3">
              {analysis.ranges.map((range) => (
                <StatCard
                  key={range.label}
                  label={range.label}
                  value={`${formatMoney(range.low, currency)} – ${formatMoney(range.high, currency)}`}
                  hint="Expected cost plus or minus that many standard deviations"
                />
              ))}
            </section>
          ) : null}
          {analysis.missing_count > 0 ? (
            <section className="card space-y-3">
              <h2 className="text-base font-semibold">Records still missing a three-point estimate</h2>
              <p className="text-sm text-mist">{analysis.suggest_note}</p>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {analysis.missing.map((row) => (
                  <li key={row.expense_id}>
                    {row.expense_name} · estimate {formatMoney(row.estimated_cost, currency)}
                  </li>
                ))}
              </ul>
              <button className="btn-primary" type="button" disabled={busy} onClick={() => void suggest()}>
                {busy ? "Saving..." : "Suggest values from the estimates"}
              </button>
            </section>
          ) : null}
          {analysis.activities.length === 0 ? (
            <EmptyState title="No PERT activities yet" body="Enter three costs on a record, or use the suggestion above. Nothing is included in the expected total until all three values are saved." />
          ) : (
            <>
              <section className="card" aria-label="Expected cost by activity">
                <h2 className="text-base font-semibold">Expected cost by activity</h2>
                <div style={{ height: Math.max(280, analysis.activities.length * 36) }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analysis.activities} layout="vertical" margin={{ left: 16, right: 16 }}>
                      <CartesianGrid stroke="#e7ecf7" horizontal={false} />
                      <XAxis type="number" tick={{ fill: "#64748b", fontSize: 12 }} />
                      <YAxis type="category" dataKey="expense_name" width={160} tick={{ fill: "#64748b", fontSize: 12 }} />
                      <Tooltip formatter={(value: number | string) => formatMoney(Number(value), currency)} />
                      <Bar dataKey="expected_cost" name="Expected" fill="#8aa4f8" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
              <div className="card overflow-x-auto">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <caption className="sr-only">PERT activities</caption>
                  <thead className="text-mist">
                    <tr>
                      <th className="py-2 pr-3 font-medium">Activity</th>
                      <th className="py-2 pr-3 font-medium">Optimistic</th>
                      <th className="py-2 pr-3 font-medium">Most likely</th>
                      <th className="py-2 pr-3 font-medium">Pessimistic</th>
                      <th className="py-2 pr-3 font-medium">Expected</th>
                      <th className="py-2 pr-3 font-medium">Std. dev.</th>
                      <th className="py-2 font-medium">Variance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.activities.map((row) => (
                      <tr key={row.expense_id} className="border-t border-line">
                        <td className="py-3 pr-3">
                          <p className="font-medium">{row.expense_name}</p>
                          <p className="text-xs text-mist">{row.category}</p>
                        </td>
                        <td className="py-3 pr-3">{formatMoney(row.optimistic_cost, currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.most_likely_cost, currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.pessimistic_cost, currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.expected_cost, currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.std_dev, currency)}</td>
                        <td className="py-3">{row.variance.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
