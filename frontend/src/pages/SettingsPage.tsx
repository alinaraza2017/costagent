import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { api, errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Banner, FieldError } from "../components/ui";
import { passwordSchema, profileSchema } from "../lib/schemas";
import { z } from "zod";

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const profile = useForm<{ full_name: string }>({
    resolver: zodResolver(profileSchema),
    values: { full_name: user?.full_name ?? "" },
  });
  const password = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "" },
  });

  async function saveProfile(values: { full_name: string }) {
    setError("");
    try {
      await api.put("/api/auth/me", values);
      await refresh();
      setNotice("Profile updated.");
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  async function savePassword(values: z.infer<typeof passwordSchema>) {
    setError("");
    try {
      await api.post("/api/auth/change-password", values);
      password.reset();
      setNotice("Password updated.");
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings and profile</h1>
        <p className="mt-1 text-sm text-mist">Currency is chosen on each project and defaults to PKR. It is shown on that project's costs, charts, and reports.</p>
      </div>
      {error ? <Banner tone="error">{error}</Banner> : null}
      {notice ? <Banner tone="success">{notice}</Banner> : null}
      <section className="card space-y-3">
        <h2 className="font-semibold">Account</h2>
        <p className="text-sm text-mist">Email: {user?.email}</p>
        <p className="text-sm text-mist">
          Analysis mode: {user?.ai_mode === "external_llm" ? "External model configured on the server" : "Rule-based. No model API key is configured."}
        </p>
        <form className="space-y-3" onSubmit={profile.handleSubmit(saveProfile)}>
          <label>
            <span className="label">Full name</span>
            <input className="field" {...profile.register("full_name")} />
            <FieldError message={profile.formState.errors.full_name?.message} />
          </label>
          <button className="btn-primary" type="submit" disabled={profile.formState.isSubmitting}>Save profile</button>
        </form>
      </section>
      <section className="card space-y-3">
        <h2 className="font-semibold">Change password</h2>
        <form className="space-y-3" onSubmit={password.handleSubmit(savePassword)}>
          <label>
            <span className="label">Current password</span>
            <input className="field" type="password" autoComplete="current-password" {...password.register("current_password")} />
            <FieldError message={password.formState.errors.current_password?.message} />
          </label>
          <label>
            <span className="label">New password</span>
            <input className="field" type="password" autoComplete="new-password" {...password.register("new_password")} />
            <FieldError message={password.formState.errors.new_password?.message} />
          </label>
          <button className="btn-secondary" type="submit" disabled={password.formState.isSubmitting}>Update password</button>
        </form>
      </section>
    </div>
  );
}
