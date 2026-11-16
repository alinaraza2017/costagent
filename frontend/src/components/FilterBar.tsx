import { CATEGORIES, type Project } from "../types";

export interface FilterValues {
  projectId: string;
  category: string;
  dateFrom: string;
  dateTo: string;
  currency: string;
}

export const emptyFilters: FilterValues = {
  projectId: "",
  category: "",
  dateFrom: "",
  dateTo: "",
  currency: "",
};

export function FilterBar({
  projects,
  values,
  onChange,
  showProject = true,
  currencies = [],
}: {
  projects: Project[];
  values: FilterValues;
  onChange: (values: FilterValues) => void;
  showProject?: boolean;
  currencies?: string[];
}) {
  function update(partial: Partial<FilterValues>) {
    onChange({ ...values, ...partial });
  }

  return (
    <form className="card grid gap-4 md:grid-cols-2 xl:grid-cols-5" aria-label="Cost filters" onSubmit={(event) => event.preventDefault()}>
      {showProject ? (
        <label>
          <span className="label">Project</span>
          <select className="field" value={values.projectId} onChange={(event) => update({ projectId: event.target.value })}>
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label>
        <span className="label">Category</span>
        <select className="field" value={values.category} onChange={(event) => update({ category: event.target.value })}>
          <option value="">All categories</option>
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">From</span>
        <input className="field" type="date" value={values.dateFrom} onChange={(event) => update({ dateFrom: event.target.value })} />
      </label>
      <label>
        <span className="label">To</span>
        <input className="field" type="date" value={values.dateTo} onChange={(event) => update({ dateTo: event.target.value })} />
      </label>
      {currencies.length > 1 ? (
        <label>
          <span className="label">Currency</span>
          <select className="field" value={values.currency} onChange={(event) => update({ currency: event.target.value })}>
            {currencies.map((currency) => (
              <option key={currency} value={currency}>
                {currency}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </form>
  );
}

export function filterParams(values: FilterValues): Record<string, string> {
  const params: Record<string, string> = {};
  if (values.projectId) params.project_id = values.projectId;
  if (values.category) params.category = values.category;
  if (values.dateFrom) params.date_from = values.dateFrom;
  if (values.dateTo) params.date_to = values.dateTo;
  if (values.currency) params.currency = values.currency;
  return params;
}
