import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { ProjectForm, toProjectPayload } from "../components/ProjectForm";
import { Banner, EmptyState, LoadingBlock, Modal } from "../components/ui";
import { formatMoney, formatPercent, formatStatus } from "../lib/format";
import type { ProjectValues } from "../lib/schemas";
import type { Page, Project } from "../types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState<Project | null | "new">(null);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const response = await api.get<Page<Project>>("/api/projects", { params: { page_size: 100 } });
      setProjects(response.data.items);
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

  async function save(values: ProjectValues) {
    setBusy(true);
    setError("");
    try {
      if (editing && editing !== "new") {
        await api.put(`/api/projects/${editing.id}`, toProjectPayload(values));
        setNotice("Project updated.");
      } else {
        await api.post("/api/projects", toProjectPayload(values));
        setNotice("Project created.");
      }
      setEditing(null);
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function remove(project: Project) {
    setBusy(true);
    try {
      await api.delete(`/api/projects/${project.id}`);
      setNotice("Project deleted.");
      setPendingDelete(null);
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          <p className="mt-1 text-sm text-mist">Each project keeps its own budget, currency, and cost records.</p>
        </div>
        <button className="btn-primary" type="button" onClick={() => setEditing("new")}>New project</button>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {notice ? <Banner tone="success">{notice}</Banner> : null}
      {loading ? <LoadingBlock label="Loading projects" /> : null}
      {!loading && projects.length === 0 ? (
        <EmptyState title="No projects yet" body="Create a project before adding cost records or importing a spreadsheet." />
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {projects.map((project) => (
          <article key={project.id} className="card flex flex-col gap-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{project.name}</h2>
                <p className="mt-1 text-sm text-mist">{project.description || "No description"}</p>
              </div>
              <span className="rounded-full bg-lavender-100 px-3 py-1 text-xs font-semibold text-primary-700">{formatStatus(project.status)}</span>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-mist">Budget</dt>
                <dd className="font-medium">{formatMoney(project.budget, project.currency)}</dd>
              </div>
              <div>
                <dt className="text-mist">Actual</dt>
                <dd className="font-medium">{formatMoney(project.summary.total_actual, project.currency)}</dd>
              </div>
              <div>
                <dt className="text-mist">Variance</dt>
                <dd className="font-medium">{formatMoney(project.summary.total_variance, project.currency)}</dd>
              </div>
              <div>
                <dt className="text-mist">Percentage</dt>
                <dd className="font-medium">{formatPercent(project.summary.percentage_variance)}</dd>
              </div>
            </dl>
            <p className="text-xs text-mist">{project.start_date}{project.end_date ? ` to ${project.end_date}` : ""} · {project.currency}</p>
            <div className="flex flex-wrap gap-2">
              <Link className="btn-primary" to={`/projects/${project.id}`}>Open records</Link>
              <button className="btn-secondary" type="button" onClick={() => setEditing(project)}>Edit</button>
              <button className="btn-danger" type="button" onClick={() => setPendingDelete(project)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
      {editing ? (
        <Modal title={editing === "new" ? "New project" : "Edit project"} onClose={() => setEditing(null)}>
          <ProjectForm
            initial={editing === "new" ? undefined : editing}
            submitLabel={editing === "new" ? "Create project" : "Save changes"}
            busy={busy}
            onSubmit={save}
          />
        </Modal>
      ) : null}
      {pendingDelete ? (
        <Modal title="Delete project" onClose={() => setPendingDelete(null)}>
          <p className="text-sm text-mist">
            Delete {pendingDelete.name}? Its cost records and import previews will be removed. This cannot be undone.
          </p>
          <div className="mt-5 flex gap-2">
            <button className="btn-danger" type="button" disabled={busy} onClick={() => void remove(pendingDelete)}>
              Delete project
            </button>
            <button className="btn-secondary" type="button" onClick={() => setPendingDelete(null)}>Keep project</button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
