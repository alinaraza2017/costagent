import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatMoney } from "../lib/format";
import type { Charts as ChartData } from "../types";
import { EmptyState } from "./ui";

const estimatedColor = "#8aa4f8";
const actualColor = "#7dcec0";
const pieColors = ["#8aa4f8", "#7dcec0", "#c4b5fd", "#f3c6a5", "#9ec5e8", "#e7b1c9", "#b7d7c5", "#d9d6f5"];

function moneyTooltip(currency: string) {
  return (value: number | string) => formatMoney(Number(value), currency);
}

export function CostCharts({ data }: { data: ChartData }) {
  const hasCategory = data.by_category.length > 0;
  const hasTime = data.spending_over_time.length > 0;
  if (!hasCategory && !hasTime) {
    return (
      <EmptyState
        title="No chart data for this filter"
        body="Add cost records, import a spreadsheet, or widen the filters. Charts use saved records only."
      />
    );
  }

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <section className="card" aria-label="Estimated versus actual costs">
        <h2 className="text-base font-semibold">Estimated vs actual costs</h2>
        <p className="mb-4 text-sm text-mist">Grouped bars compare the two amounts by category.</p>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.by_category}>
              <CartesianGrid stroke="#e7ecf7" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip formatter={moneyTooltip(data.currency)} />
              <Legend />
              <Bar dataKey="estimated" name="Estimated" fill={estimatedColor} radius={[6, 6, 0, 0]} />
              <Bar dataKey="actual" name="Actual" fill={actualColor} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card" aria-label="Cost variance by category">
        <h2 className="text-base font-semibold">Cost variance analysis</h2>
        <p className="mb-4 text-sm text-mist">Coral bars are over the estimate. Mint bars are under it.</p>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.variance_by_category}>
              <CartesianGrid stroke="#e7ecf7" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip formatter={moneyTooltip(data.currency)} />
              <Legend />
              <Bar dataKey="variance" name="Variance">
                {data.variance_by_category.map((entry) => (
                  <Cell
                    key={entry.label}
                    fill={entry.variance > 0 ? "#e7a3a3" : entry.variance < 0 ? "#7dcec0" : "#c4b5fd"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card" aria-label="Spending over time">
        <h2 className="text-base font-semibold">Monthly and cumulative spending</h2>
        <p className="mb-4 text-sm text-mist">Actual spend by month, with a running total.</p>
        <div className="h-80">
          {hasTime ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.spending_over_time}>
                <CartesianGrid stroke="#e7ecf7" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 12 }} />
                <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
                <Tooltip formatter={moneyTooltip(data.currency)} />
                <Legend />
                <Line type="monotone" dataKey="actual" name="Monthly actual" stroke="#5f7ef0" strokeWidth={2} dot />
                <Line type="monotone" dataKey="cumulative_actual" name="Cumulative actual" stroke="#3cb89f" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-mist">No dated expenses in this filter.</p>
          )}
        </div>
      </section>

      <section className="card" aria-label="Spending distribution">
        <h2 className="text-base font-semibold">Spending distribution</h2>
        <p className="mb-4 text-sm text-mist">Share of actual cost by category.</p>
        <div className="h-80">
          {data.category_distribution.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.category_distribution} dataKey="actual" nameKey="label" innerRadius={60} outerRadius={95} paddingAngle={2}>
                  {data.category_distribution.map((entry, index) => (
                    <Cell key={entry.label} fill={pieColors[index % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={moneyTooltip(data.currency)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-mist">No actual spending to distribute.</p>
          )}
        </div>
      </section>
    </div>
  );
}
