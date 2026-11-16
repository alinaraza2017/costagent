import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { CostCharts } from "../components/Charts";
import { emptyFilters, FilterBar, filterParams, type FilterValues } from "../components/FilterBar";
import { Banner, LoadingBlock } from "../components/ui";
import type { Charts, Page, Project } from "../types";

export default function ChartsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useState<FilterValues>(emptyFilters);
  const [charts, setCharts] = useState<Charts | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => setProjects(response.data.items))
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get<Charts>("/api/analytics/charts", { params: filterParams(filters) })
      .then((response) => {
        if (!active) return;
        setCharts(response.data);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Cost comparison</h1>
        <p className="mt-1 text-sm text-mist">Charts update from the database when the filters change.</p>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      <FilterBar
        projects={projects}
        values={filters}
        currencies={Array.from(new Set(projects.map((project) => project.currency)))}
        onChange={setFilters}
      />
      {loading || !charts ? <LoadingBlock label="Loading charts" /> : <CostCharts data={charts} />}
    </div>
  );
}
