import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./services/api";

const AuthContext = createContext(null);
const STORAGE_KEY = "flowsense_access_token";
const USER_KEY = "flowsense_user";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); }
    catch { return null; }
  });
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    api.me(token).then((result) => {
      setUser(result.user);
      localStorage.setItem(USER_KEY, JSON.stringify(result.user));
    }).catch(() => {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(USER_KEY);
      setToken(null); setUser(null);
    }).finally(() => setLoading(false));
  }, [token]);

  const authenticate = (result) => {
    localStorage.setItem(STORAGE_KEY, result.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(result.user));
    setToken(result.access_token); setUser(result.user);
  };
  const logout = () => {
    localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(USER_KEY);
    setToken(null); setUser(null);
  };
  const value = useMemo(() => ({ token, user, loading, isAuthenticated: Boolean(token && user), authenticate, logout }), [token, user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}