import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { FieldError } from "../components/ui";
import { registerSchema, type RegisterValues } from "../lib/schemas";

export default function RegisterPage() {
  const { user, register: registerAccount } = useAuth();
  const [serverError, setServerError] = useState("");
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(values: RegisterValues) {
    setServerError("");
    try {
      await registerAccount(values.full_name, values.email, values.password);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-primary-700">CostWise AI</p>
          <h1 className="mt-2 text-3xl font-semibold">Create an account</h1>
        </div>
        <form className="card space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          {serverError ? (
            <p className="rounded-xl bg-coral-50 px-3 py-2 text-sm text-rose-800" role="alert">
              {serverError}
            </p>
          ) : null}
          <label>
            <span className="label">Full name</span>
            <input className="field" autoComplete="name" {...form.register("full_name")} />
            <FieldError message={form.formState.errors.full_name?.message} />
          </label>
          <label>
            <span className="label">Email</span>
            <input className="field" type="email" autoComplete="email" {...form.register("email")} />
            <FieldError message={form.formState.errors.email?.message} />
          </label>
          <label>
            <span className="label">Password</span>
            <input className="field" type="password" autoComplete="new-password" {...form.register("password")} />
            <FieldError message={form.formState.errors.password?.message} />
            <p className="mt-1 text-xs text-mist">Use at least 8 characters, including a letter and a number.</p>
          </label>
          <button className="btn-primary w-full" type="submit" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Creating account..." : "Create account"}
          </button>
          <p className="text-sm text-mist">
            Already registered? <Link className="font-semibold text-primary-700" to="/login">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
