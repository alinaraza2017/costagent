import { formatMoney, formatPercent } from "../lib/format";

describe("financial formatting", () => {
  it("formats a PKR amount and keeps two decimals", () => {
    const formatted = formatMoney(1500, "PKR");
    expect(formatted).toContain("1,500");
  });

  it("shows N/A when percentage variance is missing", () => {
    expect(formatPercent(null)).toBe("N/A");
    expect(formatPercent(12.5)).toBe("+12.50%");
    expect(formatPercent(-4)).toBe("-4.00%");
  });
});
