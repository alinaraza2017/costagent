import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { ExpenseForm, toExpensePayload } from "../components/ExpenseForm";
import { Banner, EmptyState, LoadingBlock, Modal, StatCard } from "../components/ui";
import { formatMoney, formatPercent, formatStatus, varianceClass } from "../lib/format";
import type { ExpenseValues } from "../lib/schemas";
import type { Expense, Page, Project } from "../types";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [expenses, setExpenses] = useState<Page<Expense> | null>(null);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Expense | null | "new">(null);
  const [pendingDelete, setPendingDelete] = useState<Expense | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!projectId) return;
    setLoading(true);
    try {
      const [projectResponse, expenseResponse] = await Promise.all([
        api.get<Project>(`/api/projects/${projectId}`),
        api.get<Page<Expense>>(`/api/projects/${projectId}/expenses`, { params: { page, page_size: 8 } }),
      ]);
      setProject(projectResponse.data);
      setExpenses(expenseResponse.data);
      setError("");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId, page]);

  async function save(values: ExpenseValues) {
    if (!projectId) return;
    setBusy(true);
    try {
      if (editing && editing !== "new") {
        await api.put(`/api/expenses/${editing.id}`, toExpensePayload(values));
        setNotice("Cost record updated.");
      } else {
        await api.post(`/api/projects/${projectId}/expenses`, toExpensePayload(values));
        setNotice("Cost record added.");
      }
      setEditing(null);
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function remove(expense: Expense) {
    setBusy(true);
    try {
      await api.delete(`/api/expenses/${expense.id}`);
      setPendingDelete(null);
      setNotice("Cost record deleted.");
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  if (loading && !project) return <LoadingBlock label="Loading project" />;
  if (!project) return <Banner tone="error">{error || "Project not found."}</Banner>;
  const currency = project.currency;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-mist"><Link className="text-primary-700" to="/projects">Projects</Link> / {formatStatus(project.status)}</p>
          <h1 className="mt-1 text-2xl font-semibold">{project.name}</h1>
          <p className="mt-1 max-w-3xl text-sm text-mist">{project.description || "No description"}</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to={`/pert?project=${project.id}`}>PERT</Link>
          <Link className="btn-secondary" to={`/compare?left=${project.id}`}>Compare</Link>
          <Link className="btn-secondary" to={`/import?project=${project.id}`}>Import</Link>
          <button className="btn-primary" type="button" onClick={() => setEditing("new")}>Add cost</button>
        </div>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {notice ? <Banner tone="success">{notice}</Banner> : null}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Estimated" value={formatMoney(project.summary.total_estimated, currency)} />
        <StatCard label="Actual" value={formatMoney(project.summary.total_actual, currency)} />
        <StatCard label="Variance" value={formatMoney(project.summary.total_variance, currency)} hint={project.summary.interpretation} />
        <StatCard label="Percentage variance" value={formatPercent(project.summary.percentage_variance)} hint={`Budget ${formatMoney(project.budget, currency)}`} />
      </section>
      {expenses && expenses.total === 0 ? (
        <EmptyState title="No cost records" body="Add a record or import a CSV or Excel file. Percentage variance shows N/A when the estimate is zero." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <caption className="sr-only">Cost records</caption>
            <thead className="text-mist">
              <tr>
                <th className="py-2 pr-3 font-medium">Expense</th>
                <th className="py-2 pr-3 font-medium">Category</th>
                <th className="py-2 pr-3 font-medium">Estimated</th>
                <th className="py-2 pr-3 font-medium">Actual</th>
                <th className="py-2 pr-3 font-medium">Variance</th>
                <th className="py-2 pr-3 font-medium">Percent</th>
                <th className="py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {expenses?.items.map((expense) => (
                <tr key={expense.id} className="border-t border-line">
                  <td className="py-3 pr-3">
                    <p className="font-medium">{expense.expense_name}</p>
                    <p className="text-xs text-mist">{expense.expense_date}{expense.vendor ? ` · ${expense.vendor}` : ""}</p>
                    {expense.pert_expected !== null && expense.pert_expected !== undefined ? (
                      <p className="text-xs text-mist">PERT expected {formatMoney(expense.pert_expected, currency)}</p>
                    ) : null}
                  </td>
                  <td className="py-3 pr-3">{expense.category}</td>
                  <td className="py-3 pr-3">{formatMoney(expense.estimated_cost, currency)}</td>
                  <td className="py-3 pr-3">{formatMoney(expense.actual_cost, currency)}</td>
                  <td className={`py-3 pr-3 ${varianceClass(expense.variance)}`}>
                    {formatMoney(expense.variance, currency)}
                    <span className="block text-xs">{expense.variance_interpretation}</span>
                  </td>
                  <td className="py-3 pr-3">{formatPercent(expense.percentage_variance)}</td>
                  <td className="py-3">
                    <div className="flex gap-2">
                      <button className="btn-secondary px-3 py-1.5" type="button" onClick={() => setEditing(expense)}>Edit</button>
                      <button className="btn-danger px-3 py-1.5" type="button" onClick={() => setPendingDelete(expense)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {expenses && expenses.total > expenses.page_size ? (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-mist">Page {expenses.page} of {Math.ceil(expenses.total / expenses.page_size)}</p>
              <div className="flex gap-2">
                <button className="btn-secondary" type="button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
                <button className="btn-secondary" type="button" disabled={page * expenses.page_size >= expenses.total} onClick={() => setPage((current) => current + 1)}>Next</button>
              </div>
            </div>
          ) : null}
        </div>
      )}
      {editing ? (
        <Modal title={editing === "new" ? "Add cost record" : "Edit cost record"} onClose={() => setEditing(null)}>
          <ExpenseForm initial={editing === "new" ? undefined : editing} submitLabel="Save record" busy={busy} onSubmit={save} />
        </Modal>
      ) : null}
      {pendingDelete ? (
        <Modal title="Delete cost record" onClose={() => setPendingDelete(null)}>
          <p className="text-sm text-mist">Delete {pendingDelete.expense_name}? This removes the record from the project totals.</p>
          <div className="mt-5 flex gap-2">
            <button className="btn-danger" type="button" disabled={busy} onClick={() => void remove(pendingDelete)}>Delete record</button>
            <button className="btn-secondary" type="button" onClick={() => setPendingDelete(null)}>Keep record</button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
