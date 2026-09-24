import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "./authApi";

const AuthContext = createContext(null);

const TOKEN_KEY = "flowsense_access_token";
const USER_KEY = "flowsense_user";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() =>
    localStorage.getItem(TOKEN_KEY)
  );

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem(USER_KEY);

    if (!savedUser) {
      return null;
    }

    try {
      return JSON.parse(savedUser);
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      const savedToken = localStorage.getItem(TOKEN_KEY);

      if (!savedToken) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser(savedToken);

        setToken(savedToken);
        setUser(currentUser);

        localStorage.setItem(
          USER_KEY,
          JSON.stringify(currentUser)
        );
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);

        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    restoreSession();
  }, []);

  const saveSession = (data) => {
    localStorage.setItem(
      TOKEN_KEY,
      data.access_token
    );

    localStorage.setItem(
      USER_KEY,
      JSON.stringify(data.user)
    );

    setToken(data.access_token);
    setUser(data.user);
  };

  const login = async (credentials) => {
    const data = await loginUser(credentials);

    saveSession(data);

    return data.user;
  };

  const register = async (credentials) => {
    const data = await registerUser(credentials);

    saveSession(data);

    return data.user;
  };

  const logout = async () => {
    const currentToken = token;

    try {
      if (currentToken) {
        await logoutUser(currentToken);
      }
    } catch {
      // Local session is still cleared even if the API
      // logout request fails.
    }

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      register,
      logout,
    }),
    [token, user, loading]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}