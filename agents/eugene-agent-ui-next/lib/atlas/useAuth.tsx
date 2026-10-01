"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiPath } from "@/lib/basePath";

export interface AtlasUser {
  id: string;
  email: string;
  name: string;
  role: string;
  focusArea: string;
}

interface AuthState {
  user: AtlasUser | null;
  greeting: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
    focusArea: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

async function postJson(url: string, body: unknown) {
  const res = await fetch(apiPath(url), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

export function AtlasAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AtlasUser | null>(null);
  const [greeting, setGreeting] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(apiPath("/api/atlas/auth/me"), { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
        setGreeting(data.greeting ?? null);
      } else {
        setUser(null);
        setGreeting(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await postJson("/api/atlas/auth/login", { email, password });
    setUser(data.user);
    setGreeting(data.greeting ?? null);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string, focusArea: string) => {
      const data = await postJson("/api/atlas/auth/register", {
        name,
        email,
        password,
        focusArea,
      });
      setUser(data.user);
      setGreeting(data.greeting ?? null);
    },
    []
  );

  const logout = useCallback(async () => {
    await postJson("/api/atlas/auth/logout", {});
    setUser(null);
    setGreeting(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, greeting, loading, login, register, logout, refresh }),
    [user, greeting, loading, login, register, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AtlasAuthProvider");
  return ctx;
}
