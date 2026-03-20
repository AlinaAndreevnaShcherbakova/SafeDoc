import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api, setAuthToken, tokenStorageKey } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(tokenStorageKey));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    async function bootstrapAuth() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const { data } = await api.get("/auth/me");
        setUser(data);
      } catch {
        localStorage.removeItem(tokenStorageKey);
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    bootstrapAuth();
  }, [token]);

  useEffect(() => {
    const interceptorId = api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          localStorage.removeItem(tokenStorageKey);
          setToken(null);
          setUser(null);
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(interceptorId);
    };
  }, []);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      async login(loginValue, password) {
        const { data } = await api.post("/auth/login", { login: loginValue, password });
        localStorage.setItem(tokenStorageKey, data.access_token);
        setToken(data.access_token);
        const me = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        setUser(me.data);
      },
      logout() {
        localStorage.removeItem(tokenStorageKey);
        setToken(null);
        setUser(null);
      },
    }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
