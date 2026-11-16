import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { projectSchema, type ProjectValues } from "../lib/schemas";
import { CURRENCIES, STATUSES, type Project } from "../types";
import { FieldError } from "./ui";

export function ProjectForm({
  initial,
  submitLabel,
  busy,
  onSubmit,
}: {
  initial?: Project;
  submitLabel: string;
  busy: boolean;
  onSubmit: (values: ProjectValues) => Promise<void>;
}) {
  const form = useForm<ProjectValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: initial?.name ?? "",
      description: initial?.description ?? "",
      start_date: initial?.start_date ?? "",
      end_date: initial?.end_date ?? "",
      budget: initial?.budget ?? 0,
      currency: initial?.currency ?? "PKR",
      status: (initial?.status as ProjectValues["status"]) ?? "planning",
    },
  });

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <label>
        <span className="label">Project name</span>
        <input className="field" aria-invalid={Boolean(form.formState.errors.name)} {...form.register("name")} />
        <FieldError message={form.formState.errors.name?.message} />
      </label>
      <label>
        <span className="label">Description</span>
        <textarea className="field min-h-24" {...form.register("description")} />
        <FieldError message={form.formState.errors.description?.message} />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className="label">Start date</span>
          <input className="field" type="date" {...form.register("start_date")} />
          <FieldError message={form.formState.errors.start_date?.message} />
        </label>
        <label>
          <span className="label">End date</span>
          <input className="field" type="date" {...form.register("end_date")} />
          <FieldError message={form.formState.errors.end_date?.message} />
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <label>
          <span className="label">Budget</span>
          <input className="field" type="number" min="0" step="0.01" {...form.register("budget", { valueAsNumber: true })} />
          <FieldError message={form.formState.errors.budget?.message} />
        </label>
        <label>
          <span className="label">Currency</span>
          <select className="field" {...form.register("currency")}>
            {CURRENCIES.map((currency) => (
              <option key={currency} value={currency}>
                {currency}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">Status</span>
          <select className="field" {...form.register("status")}>
            {STATUSES.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <button className="btn-primary" type="submit" disabled={busy}>
        {busy ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}

export function toProjectPayload(values: ProjectValues) {
  return {
    ...values,
    end_date: values.end_date || null,
  };
}
