export type AiMode = "rule_based" | "external_llm";

export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
  ai_mode: AiMode;
}

export interface Summary {
  total_estimated: number;
  total_actual: number;
  total_variance: number;
  percentage_variance: number | null;
  expense_count: number;
  over_budget_count: number;
  under_budget_count: number;
  on_budget_count: number;
  interpretation: string;
  currency: string;
  mixed_currencies: boolean;
  currencies_present: string[];
}

export interface Project {
  id: number;
  name: string;
  description: string;
  start_date: string;
  end_date: string | null;
  budget: number;
  currency: string;
  status: string;
  created_at: string;
  updated_at: string;
  summary: Summary;
}

export interface Expense {
  id: number;
  project_id: number;
  expense_name: string;
  category: string;
  description: string;
  estimated_cost: number;
  actual_cost: number;
  optimistic_cost: number | null;
  most_likely_cost: number | null;
  pessimistic_cost: number | null;
  pert_expected: number | null;
  pert_std_dev: number | null;
  variance: number;
  percentage_variance: number | null;
  variance_interpretation: string;
  expense_date: string;
  vendor: string | null;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChartPoint {
  label: string;
  estimated: number;
  actual: number;
  variance: number;
}

export interface TimePoint {
  label: string;
  estimated: number;
  actual: number;
  cumulative_actual: number;
}

export interface Charts {
  by_category: ChartPoint[];
  by_project: ChartPoint[];
  variance_by_category: ChartPoint[];
  spending_over_time: TimePoint[];
  category_distribution: { label: string; actual: number }[];
  currency: string;
}

export interface RowIssue {
  row_number: number;
  field: string | null;
  message: string;
}

export interface ImportPreview {
  import_id: number | null;
  needs_mapping: boolean;
  detected_columns: string[];
  missing_fields: string[];
  suggested_mapping: Record<string, string>;
  valid_rows: Array<{
    source_row: number;
    expense_name: string;
    category: string;
    description: string;
    estimated_cost: number;
    actual_cost: number;
    variance: number;
    percentage_variance: number | null;
    expense_date: string;
    vendor: string | null;
  }>;
  errors: RowIssue[];
  duplicates: RowIssue[];
  duplicate_policy: string;
  accepted_count: number;
  rejected_count: number;
  duplicate_count: number;
  message: string;
}

export interface Analysis {
  project_id: number;
  project_name: string;
  currency: string;
  mode: AiMode;
  mode_label: string;
  fallback_reason: string | null;
  summary_metrics: Summary;
  highest_spending_categories: Array<{ category: string; actual_cost: number; estimated_cost: number; variance: number }>;
  over_budget_expenses: Array<{
    expense_name: string;
    category: string;
    estimated_cost: number;
    actual_cost: number;
    variance: number;
    percentage_variance: number | null;
  }>;
  anomalies: Array<{
    expense_name: string;
    category: string;
    actual_cost: number;
    peer_count: number;
    upper_fence: number;
    reason: string;
  }>;
  insufficient_sample: Array<{ category: string; peer_count: number; message: string }>;
  hypotheses: string[];
  recommendations: string[];
  budget_health: string;
  budget_health_label: string;
  summary: string;
  disclaimer: string;
}

export interface Threat {
  id: string;
  name: string;
  scenario: string;
  impact: string;
  mitigation: string;
  status: string;
  test_case: string;
  future_improvement: string;
}

export interface ChecklistItem {
  key: string;
  title: string;
  guidance: string;
  completed: boolean;
  updated_at: string | null;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  detail: string;
  created_at: string;
}

export const CATEGORIES = [
  "Personnel",
  "Equipment",
  "Software",
  "Software & Tools",
  "AI / Cloud API",
  "Travel",
  "Marketing",
  "Infrastructure",
  "Hardware & Infrastructure",
  "Operations",
  "Testing",
  "Documentation & Handover",
  "Other",
] as const;

export const CURRENCIES = ["PKR", "USD", "EUR", "GBP", "AED", "SAR", "INR"] as const;

export const STATUSES = [
  { value: "planning", label: "Planning" },
  { value: "active", label: "Active" },
  { value: "on_hold", label: "On hold" },
  { value: "completed", label: "Completed" },
] as const;

export const IMPORT_FIELDS = [
  { key: "expense_name", label: "Expense name", required: true },
  { key: "category", label: "Category", required: true },
  { key: "estimated_cost", label: "Estimated cost", required: true },
  { key: "actual_cost", label: "Actual cost", required: true },
  { key: "expense_date", label: "Expense date", required: true },
  { key: "description", label: "Description", required: false },
  { key: "vendor", label: "Vendor", required: false },
] as const;

export interface PertActivity {
  expense_id: number;
  expense_name: string;
  category: string;
  optimistic_cost: number;
  most_likely_cost: number;
  pessimistic_cost: number;
  expected_cost: number;
  std_dev: number;
  variance: number;
}

export interface PertAnalysis {
  project_id: number;
  project_name: string;
  currency: string;
  budget: number;
  activity_count: number;
  missing_count: number;
  expected_cost: number | null;
  std_dev: number | null;
  variance: number | null;
  budget_probability: number | null;
  ranges: { label: string; low: number; high: number }[];
  activities: PertActivity[];
  missing: { expense_id: number; expense_name: string; estimated_cost: number }[];
  assumption: string;
  suggest_note: string;
  suggested_count: number;
}

export interface CompareSide {
  id: number;
  name: string;
  status: string;
  currency: string;
  start_date: string;
  end_date: string | null;
  budget: number;
  expense_count: number;
  total_estimated: number;
  total_actual: number;
  total_variance: number;
  percentage_variance: number | null;
  pert_expected: number | null;
  pert_std_dev: number | null;
  pert_activity_count: number;
  pert_missing_count: number;
}

export interface ProjectComparison {
  same_currency: boolean;
  left: CompareSide;
  right: CompareSide;
  deltas: {
    budget: number;
    total_estimated: number;
    total_actual: number;
    total_variance: number;
    pert_expected: number | null;
  } | null;
  category_rows: {
    category: string;
    left_estimated: number;
    left_actual: number;
    right_estimated: number;
    right_actual: number;
  }[];
  notes: string[];
}
