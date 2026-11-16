import axios from "axios";

const TOKEN_KEY = "costwise_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
});

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (item && typeof item.msg === "string" ? item.msg : ""))
        .filter(Boolean);
      if (messages.length) {
        return messages.join(" ");
      }
    }
    if (error.response?.status === 413) {
      return "The file is too large.";
    }
    if (!error.response) {
      return "The server could not be reached. Start the backend and try again.";
    }
  }
  return "The request could not be completed.";
}
