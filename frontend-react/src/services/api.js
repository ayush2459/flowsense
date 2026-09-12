const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const get = async (path, options = {}) => {
  const controller = new AbortController();

  const timeout = setTimeout(() => {
    controller.abort();
  }, options.timeout ?? 8000);

  try {
    const response = await fetch(`${BASE}${path}`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      signal: controller.signal,
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(
        `${response.status} ${response.statusText} ${path}`
      );
    }

    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
};

const encode = (value) =>
  encodeURIComponent(String(value));

export const api = {
  /*
   * Portfolio
   */
  facilities: () =>
    get("/api/facilities"),

  anomalies: (limit = 50) =>
    get(
      `/api/anomalies/recent?limit=${Math.min(
        Number(limit) || 50,
        200
      )}`
    ),

  /*
   * Facility
   */
  summary: (facilityCode) =>
    get(
      `/api/facilities/${encode(
        facilityCode
      )}/summary`
    ),

  energy: (facilityCode, hours = 24) =>
    get(
      `/api/facilities/${encode(
        facilityCode
      )}/energy?hours=${Math.max(
        1,
        Number(hours) || 24
      )}`
    ),

  water: (facilityCode, hours = 24) =>
    get(
      `/api/facilities/${encode(
        facilityCode
      )}/water?hours=${Math.max(
        1,
        Number(hours) || 24
      )}`
    ),

  reconciliation: (
    facilityCode,
    limit = 100
  ) =>
    get(
      `/api/facilities/${encode(
        facilityCode
      )}/reconciliation?limit=${Math.min(
        Number(limit) || 100,
        500
      )}`
    ),

  yearlySummary: (facilityCode) =>
    get(
      `/api/facilities/${encode(
        facilityCode
      )}/yearly-summary`
    ),

  /*
   * Portfolio historical data
   */
  portfolioEnergy: (hours = 24) =>
    get(
      `/api/portfolio/energy?hours=${Math.max(
        1,
        Number(hours) || 24
      )}`
    ),

  portfolioWater: (hours = 24) =>
    get(
      `/api/portfolio/water?hours=${Math.max(
        1,
        Number(hours) || 24
      )}`
    ),

  /*
   * Devices
   */
  devices: () =>
    get("/api/devices"),

  deviceHealth: (deviceCode) =>
    get(
      `/api/devices/${encode(
        deviceCode
      )}/health`
    )
};

/*
 * Backend information.
 */
export const API_BASE_URL = BASE;

/*
 * Lightweight health check.
 * Useful for Settings / Devices without
 * loading portfolio data.
 */
export const health = async () => {
  try {
    return await get("/");
  } catch {
    return {
      status: "offline"
    };
  }
};