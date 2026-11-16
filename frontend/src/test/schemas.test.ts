import { expenseSchema, projectSchema } from "../lib/schemas";

describe("client validation", () => {
  it("rejects a negative estimated cost", () => {
    const result = expenseSchema.safeParse({
      expense_name: "Cable",
      category: "Equipment",
      description: "",
      estimated_cost: -10,
      actual_cost: 5,
      expense_date: "2026-03-01",
      vendor: "",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a pessimistic cost below the optimistic cost", () => {
    const result = expenseSchema.safeParse({
      expense_name: "Cable",
      category: "Equipment",
      description: "",
      estimated_cost: 100,
      actual_cost: 90,
      optimistic_cost: 120,
      most_likely_cost: 100,
      pessimistic_cost: 80,
      expense_date: "2026-03-01",
      vendor: "",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an end date before the start date", () => {
    const result = projectSchema.safeParse({
      name: "Lab",
      description: "",
      start_date: "2026-05-01",
      end_date: "2026-01-01",
      budget: 100,
      currency: "PKR",
      status: "planning",
    });
    expect(result.success).toBe(false);
  });
});
