import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Banner, StatCard } from "../components/ui";
import { formatMoney, formatPercent } from "../lib/format";
import { CATEGORIES, type Page, type Project, type Summary } from "../types";

export default function ReportsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [category, setCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        setProjects(response.data.items);
        if (response.data.items[0]) setProjectId(String(response.data.items[0].id));
      })
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    const params: Record<string, string> = {};
    if (category) params.category = category;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    api.get<Summary>(`/api/projects/${projectId}/analytics`, { params })
      .then((response) => setSummary(response.data))
      .catch((reason) => setError(errorMessage(reason)));
  }, [projectId, category, dateFrom, dateTo]);

  async function download(kind: "pdf" | "csv") {
    if (!projectId) return;
    setBusy(kind);
    setError("");
    try {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const response = await api.get(`/api/projects/${projectId}/reports/${kind}`, { params, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `costwise-project-${projectId}.${kind}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  const project = projects.find((item) => String(item.id) === projectId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="mt-1 text-sm text-mist">PDF findings use the rule-based analysis so a download does not send project data to an external model.</p>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      <section className="card grid gap-4 md:grid-cols-4">
        <label className="md:col-span-2">
          <span className="label">Project</span>
          <select className="field" value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">Select a project</option>
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label>
          <span className="label">Category</span>
          <select className="field" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">All categories</option>
            {CATEGORIES.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label>
            <span className="label">From</span>
            <input className="field" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label>
            <span className="label">To</span>
            <input className="field" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
        </div>
      </section>
      {summary && project ? (
        <section className="grid gap-4 md:grid-cols-4">
          <StatCard label="Estimated" value={formatMoney(summary.total_estimated, project.currency)} />
          <StatCard label="Actual" value={formatMoney(summary.total_actual, project.currency)} />
          <StatCard label="Variance" value={formatMoney(summary.total_variance, project.currency)} />
          <StatCard label="Percentage variance" value={formatPercent(summary.percentage_variance)} />
        </section>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" type="button" disabled={!projectId || busy !== ""} onClick={() => void download("pdf")}>
          {busy === "pdf" ? "Preparing PDF..." : "Export PDF"}
        </button>
        <button className="btn-secondary" type="button" disabled={!projectId || busy !== ""} onClick={() => void download("csv")}>
          {busy === "csv" ? "Preparing CSV..." : "Export CSV"}
        </button>
      </div>
    </div>
  );
}
