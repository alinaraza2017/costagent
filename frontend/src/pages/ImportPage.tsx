import Papa from "papaparse";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { Banner, LoadingBlock } from "../components/ui";
import { formatMoney, formatPercent } from "../lib/format";
import { IMPORT_FIELDS, type ImportPreview, type Page, type Project } from "../types";

export default function ImportPage() {
  const [params] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(params.get("project") || "");
  const [file, setFile] = useState<File | null>(null);
  const [clientNote, setClientNote] = useState("");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } })
      .then((response) => {
        setProjects(response.data.items);
        if (!projectId && response.data.items[0]) {
          setProjectId(String(response.data.items[0].id));
        }
      })
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setLoading(false));
  }, []);

  async function downloadTemplate() {
    const response = await api.get("/api/imports/sample-template", { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "costwise-import-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function onFile(selected: File | null) {
    setFile(selected);
    setPreview(null);
    setSummary("");
    setClientNote("");
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setClientNote("Excel files are checked on the server. The table below appears after the server preview.");
      return;
    }
    Papa.parse<Record<string, string>>(selected, {
      header: true,
      skipEmptyLines: true,
      preview: 5,
      complete: (result) => {
        const columns = result.meta.fields?.filter(Boolean) ?? [];
        setClientNote(
          columns.length
            ? `Client preview saw columns: ${columns.join(", ")}. The server preview below is the one that can be saved.`
            : "The client parser did not find a header row. The server will validate the file.",
        );
      },
      error: () => setClientNote("The client parser could not read this CSV. The server will still validate it."),
    });
  }

  async function previewFile(nextMapping = mapping) {
    if (!file || !projectId) {
      setError("Choose a project and a .csv or .xlsx file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("This file is larger than 5 MB.");
      return;
    }
    setBusy(true);
    setError("");
    setSummary("");
    try {
      const form = new FormData();
      form.append("file", file);
      if (Object.keys(nextMapping).length) {
        form.append("column_map", JSON.stringify(nextMapping));
      }
      const response = await api.post<ImportPreview>(`/api/projects/${projectId}/imports/preview`, form);
      setPreview(response.data);
      setMapping(response.data.suggested_mapping || {});
    } catch (reason) {
      setPreview(null);
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirmImport() {
    if (!preview?.import_id || !projectId) return;
    setBusy(true);
    try {
      const response = await api.post(`/api/projects/${projectId}/imports/confirm`, { import_id: preview.import_id });
      setSummary(response.data.message);
      setPreview(null);
      setFile(null);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function cancelImport() {
    if (!preview?.import_id || !projectId) {
      setPreview(null);
      setFile(null);
      return;
    }
    setBusy(true);
    try {
      const response = await api.post(`/api/projects/${projectId}/imports/${preview.import_id}/cancel`);
      setSummary(response.data.message);
      setPreview(null);
      setFile(null);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const project = projects.find((item) => String(item.id) === projectId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Import data</h1>
          <p className="mt-1 max-w-3xl text-sm text-mist">
            Upload a CSV or XLSX file, review the server preview, then confirm. Cancelling writes nothing.
            Negative costs, invalid dates, and spreadsheet formulas are rejected.
          </p>
        </div>
        <button className="btn-secondary" type="button" onClick={() => void downloadTemplate()}>Download sample CSV</button>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {summary ? <Banner tone="success">{summary}</Banner> : null}
      {loading ? <LoadingBlock label="Loading projects" /> : null}
      <section className="card grid gap-4 md:grid-cols-2">
        <label>
          <span className="label">Project</span>
          <select className="field" value={projectId} onChange={(event) => { setProjectId(event.target.value); setPreview(null); }}>
            <option value="">Select a project</option>
            {projects.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">Spreadsheet</span>
          <input
            className="field"
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => onFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <div className="md:col-span-2 flex flex-wrap gap-2">
          <button className="btn-primary" type="button" disabled={busy || !file} onClick={() => void previewFile()}>
            {busy ? "Checking..." : "Preview and validate"}
          </button>
        </div>
        {clientNote ? <p className="md:col-span-2 text-sm text-mist">{clientNote}</p> : null}
      </section>
      {preview?.needs_mapping ? (
        <section className="card space-y-4">
          <h2 className="text-lg font-semibold">Map columns</h2>
          <p className="text-sm text-mist">Detected columns: {preview.detected_columns.join(", ") || "none"}.</p>
          <div className="grid gap-4 md:grid-cols-2">
            {IMPORT_FIELDS.map((field) => (
              <label key={field.key}>
                <span className="label">{field.label}{field.required ? " (required)" : " (optional)"}</span>
                <select
                  className="field"
                  value={mapping[field.key] || ""}
                  onChange={(event) => setMapping((current) => ({ ...current, [field.key]: event.target.value }))}
                >
                  <option value="">Not mapped</option>
                  {preview.detected_columns.map((column) => (
                    <option key={column} value={column}>{column}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <button className="btn-primary" type="button" disabled={busy} onClick={() => void previewFile(mapping)}>
            Preview mapped file
          </button>
        </section>
      ) : null}
      {preview && !preview.needs_mapping ? (
        <section className="space-y-4">
          <Banner tone="info">{preview.message}</Banner>
          <div className="grid gap-4 md:grid-cols-3">
            <article className="card"><p className="text-sm text-mist">Valid rows</p><p className="text-2xl font-semibold">{preview.accepted_count}</p></article>
            <article className="card"><p className="text-sm text-mist">Rejected rows</p><p className="text-2xl font-semibold">{preview.rejected_count}</p></article>
            <article className="card"><p className="text-sm text-mist">Duplicates skipped</p><p className="text-2xl font-semibold">{preview.duplicate_count}</p></article>
          </div>
          <p className="text-sm text-mist">{preview.duplicate_policy}</p>
          {preview.errors.length ? (
            <div className="card">
              <h2 className="font-semibold">Row errors</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {preview.errors.map((issue) => (
                  <li key={`${issue.row_number}-${issue.message}`}>Row {issue.row_number}: {issue.message}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {preview.duplicates.length ? (
            <div className="card">
              <h2 className="font-semibold">Duplicates</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {preview.duplicates.map((issue) => (
                  <li key={`${issue.row_number}-${issue.message}`}>Row {issue.row_number}: {issue.message}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {preview.valid_rows.length ? (
            <div className="card overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <caption className="sr-only">Valid rows that will be saved if you confirm</caption>
                <thead className="text-mist">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Row</th>
                    <th className="py-2 pr-3 font-medium">Expense</th>
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 pr-3 font-medium">Estimated</th>
                    <th className="py-2 pr-3 font-medium">Actual</th>
                    <th className="py-2 font-medium">Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.valid_rows.map((row) => (
                    <tr key={row.source_row} className="border-t border-line">
                      <td className="py-2 pr-3">{row.source_row}</td>
                      <td className="py-2 pr-3">{row.expense_name}</td>
                      <td className="py-2 pr-3">{row.category}</td>
                      <td className="py-2 pr-3">{formatMoney(row.estimated_cost, project?.currency || "PKR")}</td>
                      <td className="py-2 pr-3">{formatMoney(row.actual_cost, project?.currency || "PKR")}</td>
                      <td className="py-2">{formatMoney(row.variance, project?.currency || "PKR")} ({formatPercent(row.percentage_variance)})</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" type="button" disabled={busy || preview.accepted_count === 0} onClick={() => void confirmImport()}>
              Confirm import
            </button>
            <button className="btn-secondary" type="button" disabled={busy} onClick={() => void cancelImport()}>
              Cancel import
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
