import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your name").max(120),
  email: z.string().trim().email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(72, "Password is too long")
    .regex(/[A-Za-z]/, "Include a letter")
    .regex(/\d/, "Include a number"),
});

export const projectSchema = z
  .object({
    name: z.string().trim().min(1, "Project name is required").max(200),
    description: z.string().max(2000, "Description is too long"),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string(),
    budget: z.number({ invalid_type_error: "Enter a budget" }).min(0, "Budget cannot be negative"),
    currency: z.string().min(3, "Select a currency"),
    status: z.enum(["planning", "active", "on_hold", "completed"]),
  })
  .refine((value) => !value.end_date || value.end_date >= value.start_date, {
    message: "End date cannot be earlier than the start date",
    path: ["end_date"],
  });

const optionalCost = z.preprocess(
  (value) => {
    if (value === "" || value === undefined || value === null || (typeof value === "number" && Number.isNaN(value))) {
      return null;
    }
    return value;
  },
  z.number({ invalid_type_error: "Enter a cost" }).min(0, "Cost cannot be negative").nullable(),
);

export const expenseSchema = z
  .object({
    expense_name: z.string().trim().min(1, "Expense name is required").max(200),
    category: z.string().min(1, "Select a category"),
    description: z.string().max(2000, "Description is too long"),
    estimated_cost: z.number({ invalid_type_error: "Enter an estimated cost" }).min(0, "Cost cannot be negative"),
    actual_cost: z.number({ invalid_type_error: "Enter an actual cost" }).min(0, "Cost cannot be negative"),
    optimistic_cost: optionalCost,
    most_likely_cost: optionalCost,
    pessimistic_cost: optionalCost,
    expense_date: z.string().min(1, "Expense date is required"),
    vendor: z.string().max(200, "Vendor is too long"),
  })
  .superRefine((value, context) => {
    const points = [value.optimistic_cost, value.most_likely_cost, value.pessimistic_cost];
    const filled = points.filter((point) => point !== null);
    if (filled.length === 0) {
      return;
    }
    if (filled.length !== 3) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Enter all three PERT costs, or leave them all blank",
        path: ["optimistic_cost"],
      });
      return;
    }
    if (
      value.optimistic_cost !== null &&
      value.most_likely_cost !== null &&
      value.pessimistic_cost !== null &&
      (value.optimistic_cost > value.most_likely_cost || value.most_likely_cost > value.pessimistic_cost)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Optimistic cannot exceed most likely, and most likely cannot exceed pessimistic",
        path: ["pessimistic_cost"],
      });
    }
  });

export const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your name").max(120),
});

export const passwordSchema = z.object({
  current_password: z.string().min(1, "Enter your current password"),
  new_password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(72, "Password is too long")
    .regex(/[A-Za-z]/, "Include a letter")
    .regex(/\d/, "Include a number"),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ProjectValues = z.infer<typeof projectSchema>;
export type ExpenseValues = z.infer<typeof expenseSchema>;
