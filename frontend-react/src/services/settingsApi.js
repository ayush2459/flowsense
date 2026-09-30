const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const TOKEN_KEY = "flowsense_access_token";

async function request(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);

  const response = await fetch(`${BASE}${path}`, {
    method: options.method || "GET",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
    },
    cache: "no-store",
    body:
      options.body === undefined
        ? undefined
        : JSON.stringify(options.body),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data?.detail || data?.message || "";
    } catch {
      // Ignore non-JSON error bodies.
    }

    throw new Error(
      `${response.status} ${response.statusText}${
        detail ? ` — ${detail}` : ""
      }`
    );
  }

  return response.json();
}

export const settingsApi = {
  get: () => request("/api/settings"),

  save: (payload) =>
    request("/api/settings", {
      method: "PUT",
      body: payload,
    }),

  profile: (payload) =>
    request("/api/settings/profile", {
      method: "PUT",
      body: payload,
    }),

  password: (payload) =>
    request("/api/settings/password", {
      method: "PUT",
      body: payload,
    }),

  users: () => request("/api/settings/users"),

  updateUser: (userId, payload) =>
    request(`/api/settings/users/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      body: payload,
    }),

  systemStatus: () =>
    request("/api/settings/system-status"),
};
