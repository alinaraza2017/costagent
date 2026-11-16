import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { expenseSchema, type ExpenseValues } from "../lib/schemas";
import { CATEGORIES, type Expense } from "../types";
import { FieldError } from "./ui";

function emptyCost(value: unknown) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const amount = typeof value === "number" ? value : Number(value);
  return Number.isNaN(amount) ? null : amount;
}

export function ExpenseForm({
  initial,
  submitLabel,
  busy,
  onSubmit,
}: {
  initial?: Expense;
  submitLabel: string;
  busy: boolean;
  onSubmit: (values: ExpenseValues) => Promise<void>;
}) {
  const form = useForm<ExpenseValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      expense_name: initial?.expense_name ?? "",
      category: initial?.category ?? "Equipment",
      description: initial?.description ?? "",
      estimated_cost: initial?.estimated_cost ?? 0,
      actual_cost: initial?.actual_cost ?? 0,
      optimistic_cost: initial?.optimistic_cost ?? null,
      most_likely_cost: initial?.most_likely_cost ?? null,
      pessimistic_cost: initial?.pessimistic_cost ?? null,
      expense_date: initial?.expense_date ?? "",
      vendor: initial?.vendor ?? "",
    },
  });

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <label>
        <span className="label">Expense name</span>
        <input className="field" {...form.register("expense_name")} />
        <FieldError message={form.formState.errors.expense_name?.message} />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className="label">Category</span>
          <select className="field" {...form.register("category")}>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <FieldError message={form.formState.errors.category?.message} />
        </label>
        <label>
          <span className="label">Expense date</span>
          <input className="field" type="date" {...form.register("expense_date")} />
          <FieldError message={form.formState.errors.expense_date?.message} />
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className="label">Estimated cost</span>
          <input className="field" type="number" min="0" step="0.01" {...form.register("estimated_cost", { valueAsNumber: true })} />
          <FieldError message={form.formState.errors.estimated_cost?.message} />
        </label>
        <label>
          <span className="label">Actual cost</span>
          <input className="field" type="number" min="0" step="0.01" {...form.register("actual_cost", { valueAsNumber: true })} />
          <FieldError message={form.formState.errors.actual_cost?.message} />
        </label>
      </div>
      <fieldset className="space-y-3 rounded-xl border border-line p-3">
        <legend className="px-1 text-sm font-medium">PERT three-point estimate</legend>
        <p className="text-xs text-mist">Optional. Leave all three blank, or enter optimistic, most likely, and pessimistic costs with optimistic at or below most likely, and most likely at or below pessimistic.</p>
        <div className="grid gap-4 sm:grid-cols-3">
          <label>
            <span className="label">Optimistic</span>
            <input className="field" type="number" min="0" step="0.01" {...form.register("optimistic_cost", { setValueAs: emptyCost })} />
            <FieldError message={form.formState.errors.optimistic_cost?.message} />
          </label>
          <label>
            <span className="label">Most likely</span>
            <input className="field" type="number" min="0" step="0.01" {...form.register("most_likely_cost", { setValueAs: emptyCost })} />
            <FieldError message={form.formState.errors.most_likely_cost?.message} />
          </label>
          <label>
            <span className="label">Pessimistic</span>
            <input className="field" type="number" min="0" step="0.01" {...form.register("pessimistic_cost", { setValueAs: emptyCost })} />
            <FieldError message={form.formState.errors.pessimistic_cost?.message} />
          </label>
        </div>
      </fieldset>
      <label>
        <span className="label">Vendor</span>
        <input className="field" {...form.register("vendor")} />
        <FieldError message={form.formState.errors.vendor?.message} />
      </label>
      <label>
        <span className="label">Description</span>
        <textarea className="field min-h-24" {...form.register("description")} />
        <FieldError message={form.formState.errors.description?.message} />
      </label>
      <button className="btn-primary" type="submit" disabled={busy}>
        {busy ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}

export function toExpensePayload(values: ExpenseValues) {
  return {
    ...values,
    vendor: values.vendor.trim() ? values.vendor.trim() : null,
  };
}
