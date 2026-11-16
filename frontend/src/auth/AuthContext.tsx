import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, errorMessage, setToken } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  async function refresh() {
    const response = await api.get<User>("/api/auth/me");
    setUser(response.data);
  }

  useEffect(() => {
    const token = sessionStorage.getItem("costwise_token");
    if (!token) {
      setReady(true);
      return;
    }
    refresh()
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      ready,
      refresh,
      async login(email, password) {
        const response = await api.post<{ access_token: string }>("/api/auth/login", { email, password });
        setToken(response.data.access_token);
        await refresh();
      },
      async register(fullName, email, password) {
        await api.post("/api/auth/register", { full_name: fullName, email, password });
        const response = await api.post<{ access_token: string }>("/api/auth/login", { email, password });
        setToken(response.data.access_token);
        await refresh();
      },
      async logout() {
        try {
          await api.post("/api/auth/logout");
        } catch (error) {
          if (errorMessage(error)) {
            setToken(null);
            setUser(null);
            return;
          }
        }
        setToken(null);
        setUser(null);
      },
    }),
    [user, ready],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
