import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errorMessage } from "../api/client";
import { Banner, EmptyState, LoadingBlock, StatCard } from "../components/ui";
import { formatMoney, formatPercent, formatStatus } from "../lib/format";
import type { Page, Project, ProjectComparison } from "../types";

function signedMoney(value: number | null | undefined, currency: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  const text = formatMoney(Math.abs(value), currency);
  if (value > 0) return `+${text}`;
  if (value < 0) return `−${text}`;
  return text;
}

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.toString();
  const [projects, setProjects] = useState<Project[]>([]);
  const [leftId, setLeftId] = useState(searchParams.get("left") ?? "");
  const [rightId, setRightId] = useState(searchParams.get("right") ?? "");
  const [comparison, setComparison] = useState<ProjectComparison | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        const items = response.data.items;
        setProjects(items);
        setLeftId((current) => current || searchParams.get("left") || String(items[0]?.id ?? ""));
        setRightId((current) => {
          if (current) return current;
          const requested = searchParams.get("right");
          if (requested) return requested;
          const first = String(items[0]?.id ?? "");
          const second = items.find((project) => String(project.id) !== (searchParams.get("left") || first));
          return second ? String(second.id) : "";
        });
      })
      .catch((reason) => setError(errorMessage(reason)));
  }, [query, searchParams]);

  useEffect(() => {
    if (!leftId || !rightId || leftId === rightId) {
      setComparison(null);
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    api.get<ProjectComparison>("/api/analytics/compare", { params: { left_id: leftId, right_id: rightId } })
      .then((response) => {
        if (!active) return;
        setComparison(response.data);
        setError("");
      })
      .catch((reason) => {
        if (active) {
          setComparison(null);
          setError(errorMessage(reason));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [leftId, rightId]);

  const chartRows = comparison
    ? [
        { metric: "Budget", left: comparison.left.budget, right: comparison.right.budget },
        { metric: "Estimated", left: comparison.left.total_estimated, right: comparison.right.total_estimated },
        { metric: "Actual", left: comparison.left.total_actual, right: comparison.right.total_actual },
        { metric: "PERT expected", left: comparison.left.pert_expected ?? 0, right: comparison.right.pert_expected ?? 0 },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Compare projects</h1>
        <p className="mt-1 max-w-3xl text-sm text-mist">
          Pick two projects you own. The difference is the second project minus the first.
        </p>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {projects.length < 2 ? (
        <EmptyState title="Two projects are needed" body="Create another project, then come back to compare budget, estimates, actual cost, and PERT expected cost." />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <label>
              <span className="label">First project</span>
              <select className="field" value={leftId} onChange={(event) => setLeftId(event.target.value)}>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span className="label">Second project</span>
              <select className="field" value={rightId} onChange={(event) => setRightId(event.target.value)}>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </label>
          </div>
          {leftId === rightId ? (
            <Banner tone="info">Choose two different projects.</Banner>
          ) : loading || !comparison ? (
            <LoadingBlock label="Comparing projects" />
          ) : (
            <>
              {comparison.notes.map((note) => (
                <Banner key={note} tone="info">{note}</Banner>
              ))}
              <div className="grid gap-4 lg:grid-cols-2">
                {[comparison.left, comparison.right].map((side) => (
                  <section key={side.id} className="card space-y-3">
                    <div>
                      <h2 className="text-lg font-semibold">{side.name}</h2>
                      <p className="text-sm text-mist">{formatStatus(side.status)} · {side.expense_count} cost records · {side.start_date}{side.end_date ? ` to ${side.end_date}` : ""}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <StatCard label="Budget" value={formatMoney(side.budget, side.currency)} />
                      <StatCard label="Estimated" value={formatMoney(side.total_estimated, side.currency)} />
                      <StatCard label="Actual" value={formatMoney(side.total_actual, side.currency)} />
                      <StatCard label="Variance" value={formatMoney(side.total_variance, side.currency)} hint={formatPercent(side.percentage_variance)} />
                      <StatCard label="PERT expected" value={formatMoney(side.pert_expected, side.currency)} hint={`${side.pert_activity_count} activities · ${side.pert_missing_count} missing`} />
                      <StatCard label="PERT std. dev." value={formatMoney(side.pert_std_dev, side.currency)} />
                    </div>
                  </section>
                ))}
              </div>
              {comparison.same_currency && comparison.deltas ? (
                <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <StatCard label="Budget difference" value={signedMoney(comparison.deltas.budget, comparison.left.currency)} />
                  <StatCard label="Estimated difference" value={signedMoney(comparison.deltas.total_estimated, comparison.left.currency)} />
                  <StatCard label="Actual difference" value={signedMoney(comparison.deltas.total_actual, comparison.left.currency)} />
                  <StatCard label="Variance difference" value={signedMoney(comparison.deltas.total_variance, comparison.left.currency)} />
                  <StatCard label="PERT difference" value={signedMoney(comparison.deltas.pert_expected, comparison.left.currency)} />
                </section>
              ) : null}
              {comparison.same_currency ? (
                <section className="card" aria-label="Project totals compared">
                  <h2 className="text-base font-semibold">Totals</h2>
                  <p className="mb-4 text-sm text-mist">{comparison.left.name} and {comparison.right.name} in {comparison.left.currency}.</p>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartRows}>
                        <CartesianGrid stroke="#e7ecf7" vertical={false} />
                        <XAxis dataKey="metric" tick={{ fill: "#64748b", fontSize: 12 }} />
                        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
                        <Tooltip formatter={(value: number | string) => formatMoney(Number(value), comparison.left.currency)} />
                        <Legend />
                        <Bar dataKey="left" name={comparison.left.name} fill="#8aa4f8" radius={[6, 6, 0, 0]} />
                        <Bar dataKey="right" name={comparison.right.name} fill="#7dcec0" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              ) : null}
              <div className="card overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <caption className="sr-only">Category comparison</caption>
                  <thead className="text-mist">
                    <tr>
                      <th className="py-2 pr-3 font-medium">Category</th>
                      <th className="py-2 pr-3 font-medium">{comparison.left.name} estimated</th>
                      <th className="py-2 pr-3 font-medium">{comparison.left.name} actual</th>
                      <th className="py-2 pr-3 font-medium">{comparison.right.name} estimated</th>
                      <th className="py-2 font-medium">{comparison.right.name} actual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.category_rows.length === 0 ? (
                      <tr>
                        <td className="py-3 text-mist" colSpan={5}>Neither project has cost records yet.</td>
                      </tr>
                    ) : comparison.category_rows.map((row) => (
                      <tr key={row.category} className="border-t border-line">
                        <td className="py-3 pr-3 font-medium">{row.category}</td>
                        <td className="py-3 pr-3">{formatMoney(row.left_estimated, comparison.left.currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.left_actual, comparison.left.currency)}</td>
                        <td className="py-3 pr-3">{formatMoney(row.right_estimated, comparison.right.currency)}</td>
                        <td className="py-3">{formatMoney(row.right_actual, comparison.right.currency)}</td>
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
