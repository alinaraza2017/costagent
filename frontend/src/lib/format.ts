export function formatMoney(value: number | null | undefined, currency = "PKR"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  try {
    return new Intl.NumberFormat("en-PK", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

export function formatStatus(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function varianceClass(value: number): string {
  if (value > 0) return "text-rose-700";
  if (value < 0) return "text-emerald-700";
  return "text-mist";
}
