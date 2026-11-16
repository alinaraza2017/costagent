import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { CostCharts } from "../components/Charts";
import { emptyFilters, FilterBar, filterParams, type FilterValues } from "../components/FilterBar";
import { Banner, EmptyState, LoadingBlock, StatCard } from "../components/ui";
import { formatMoney, formatPercent } from "../lib/format";
import type { Charts, Page, Project, Summary } from "../types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useState<FilterValues>(emptyFilters);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [charts, setCharts] = useState<Charts | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        setProjects(response.data.items);
        const currencies = Array.from(new Set(response.data.items.map((project) => project.currency)));
        if (currencies.length) {
          setFilters((current) => ({ ...current, currency: current.currency || (currencies.includes("PKR") ? "PKR" : currencies[0]) }));
        }
      })
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const params = filterParams(filters);
    Promise.all([
      api.get<Summary>("/api/analytics/summary", { params }),
      api.get<Charts>("/api/analytics/charts", { params }),
    ])
      .then(([summaryResponse, chartResponse]) => {
        if (!active) return;
        setSummary(summaryResponse.data);
        setCharts(chartResponse.data);
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
  }, [filters]);

  const currency = summary?.currency || "PKR";
  const currencies = summary?.currencies_present || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-mist">Totals are calculated from your saved cost records.</p>
        </div>
        <Link className="btn-primary" to="/projects">Manage projects</Link>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      <FilterBar projects={projects} values={filters} currencies={currencies} onChange={setFilters} />
      {summary?.mixed_currencies ? (
        <Banner tone="info">Projects use more than one currency. Totals below include only {currency} so amounts are not added across currencies.</Banner>
      ) : null}
      {loading || !summary ? (
        <LoadingBlock label="Loading dashboard" />
      ) : summary.expense_count === 0 && projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          body="Create a project and add estimated and actual costs. You can also import the sample CSV."
          action={<Link className="btn-primary" to="/projects">Create a project</Link>}
        />
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total estimated" value={formatMoney(summary.total_estimated, currency)} />
            <StatCard label="Total actual" value={formatMoney(summary.total_actual, currency)} />
            <StatCard label="Total variance" value={formatMoney(summary.total_variance, currency)} hint={summary.interpretation} />
            <StatCard
              label="Percentage variance"
              value={formatPercent(summary.percentage_variance)}
              hint={`${summary.expense_count} expenses · ${summary.over_budget_count} over · ${summary.under_budget_count} under`}
            />
          </section>
          {charts ? <CostCharts data={charts} /> : null}
        </>
      )}
    </div>
  );
}
