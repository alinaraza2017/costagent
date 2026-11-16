import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { FieldError } from "../components/ui";
import { loginSchema, type LoginValues } from "../lib/schemas";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [serverError, setServerError] = useState("");
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(values: LoginValues) {
    setServerError("");
    try {
      await login(values.email, values.password);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-primary-700">CostWise AI</p>
          <h1 className="mt-2 text-3xl font-semibold">Sign in</h1>
          <p className="mt-2 text-sm text-mist">Review project estimates, actual costs, and budget variance.</p>
        </div>
        <form className="card space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          {serverError ? (
            <p className="rounded-xl bg-coral-50 px-3 py-2 text-sm text-rose-800" role="alert">
              {serverError}
            </p>
          ) : null}
          <label>
            <span className="label">Email</span>
            <input className="field" type="email" autoComplete="username" {...form.register("email")} />
            <FieldError message={form.formState.errors.email?.message} />
          </label>
          <label>
            <span className="label">Password</span>
            <input className="field" type="password" autoComplete="current-password" {...form.register("password")} />
            <FieldError message={form.formState.errors.password?.message} />
          </label>
          <button className="btn-primary w-full" type="submit" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Signing in..." : "Sign in"}
          </button>
          <p className="text-sm text-mist">
            New here? <Link className="font-semibold text-primary-700" to="/register">Create an account</Link>
          </p>
        </form>
        <p className="mt-4 rounded-2xl bg-lavender-50 px-4 py-3 text-sm text-slate-700">
          A local demo account is created by the seed command. The README lists that sign-in for this machine only.
        </p>
      </div>
    </div>
  );
}
