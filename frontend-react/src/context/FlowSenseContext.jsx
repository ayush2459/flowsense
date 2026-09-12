import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { connectAllFacilities } from "../realtime";
import { api } from "../services/api";

const FlowSenseContext = createContext(null);

const ENERGY_TARIFF = 8.5;
const WATER_TARIFF = 35;

function normalizeStatus(value) {
  const status = String(value || "").toLowerCase();

  if (status === "critical") return "critical";
  if (status === "attention" || status === "needs attention") {
    return "attention";
  }

  return "healthy";
}

function normalizeMessage(message) {
  const data = message?.data || {};
  const detection = message?.detection || {};

  const anomalies = Array.isArray(detection.anomalies)
    ? detection.anomalies
    : [];

  const primaryAnomaly = detection.primary_anomaly || null;

  const rawStatus =
    detection.facility_status ||
    data.status ||
    (anomalies.length || primaryAnomaly ? "attention" : "healthy");

  return {
    facility_code: message?.facility_code || null,
    timestamp:
      message?.timestamp ||
      data.reading_time ||
      new Date().toISOString(),

    energy_kwh: Number(data.energy_kwh ?? 0),
    water_kl: Number(data.water_kl ?? 0),
    power_kw: Number(data.power_kw ?? 0),
    voltage_v: Number(data.voltage_v ?? 0),
    current_a: Number(data.current_a ?? 0),

    water_flow_lpm: Number(data.water_flow_lpm ?? 0),
    water_pressure_bar: Number(data.water_pressure_bar ?? 0),

    temperature_c: Number(data.temperature_c ?? 0),
    humidity_percent: Number(data.humidity_percent ?? 0),
    vibration_mm_s: Number(data.vibration_mm_s ?? 0),

    leak_detected: Boolean(data.leak_detected),

    telemetry_anomaly: Boolean(data.anomaly),
    telemetry_anomaly_type: data.anomaly_type || null,
    telemetry_status: normalizeStatus(data.status),

    facility_status: normalizeStatus(rawStatus),

    anomaly_count: Number(
      detection.anomaly_count ?? anomalies.length
    ),

    estimated_energy_loss_kwh: Number(
      detection.estimated_energy_loss_kwh ?? 0
    ),

    estimated_water_loss_kl: Number(
      detection.estimated_water_loss_kl ?? 0
    ),

    anomalies,
    primary_anomaly: primaryAnomaly,

    energy_score: Number(
      detection.efficiency?.energy_score ?? 0
    ),

    water_score: Number(
      detection.efficiency?.water_score ?? 0
    ),

    recommendation: detection.recommendation || null,

    _raw: message,
    _receivedAt: Date.now()
  };
}

function buildAlert(facility) {
  if (
    !facility ||
    (!facility.telemetry_anomaly &&
      !facility.anomaly_count &&
      !facility.primary_anomaly &&
      !facility.anomalies?.length)
  ) {
    return null;
  }

  const primary = facility.primary_anomaly || {};
  const firstAnomaly = facility.anomalies?.[0] || {};

  const type =
    facility.telemetry_anomaly_type ||
    primary.anomaly_type ||
    firstAnomaly.anomaly_type ||
    firstAnomaly.type ||
    "realtime_anomaly";

  const severity =
    String(
      primary.severity ||
        firstAnomaly.severity ||
        facility.facility_status
    ).toLowerCase() === "critical"
      ? "Critical"
      : "Warning";

  return {
    id: `${facility.facility_code}-${type}`,
    anomaly_id:
      primary.anomaly_id ||
      firstAnomaly.anomaly_id ||
      null,

    facility_code: facility.facility_code,
    anomaly_type: type,
    severity,

    description:
      primary.description ||
      firstAnomaly.description ||
      (type === "water_leak"
        ? "Possible water leakage detected by realtime IoT telemetry."
        : `Realtime IoT signal indicates ${String(type).replaceAll(
            "_",
            " "
          )}.`),

    detected_at:
      primary.detected_at ||
      firstAnomaly.detected_at ||
      facility.timestamp,

    source_name:
      primary.likely_source ||
      primary.source_name ||
      firstAnomaly.likely_source ||
      firstAnomaly.source_name ||
      "Realtime IoT",

    deviation_percent:
      Number(primary.deviation_percent) ||
      Number(firstAnomaly.deviation_percent) ||
      0,

    estimated_loss:
      Number(primary.estimated_loss) ||
      Number(firstAnomaly.estimated_loss) ||
      0
  };
}

function mergeFacilityMetadata(metadata, live) {
  const map = new Map();

  (Array.isArray(metadata) ? metadata : []).forEach((facility) => {
    if (facility?.facility_code) {
      map.set(facility.facility_code, {
        ...facility
      });
    }
  });

  Object.entries(live || {}).forEach(([code, telemetry]) => {
    map.set(code, {
      ...(map.get(code) || {}),
      ...telemetry,

      // Preserve metadata if the websocket payload doesn't contain it.
      facility_code:
        telemetry.facility_code ||
        map.get(code)?.facility_code ||
        code,

      facility_name:
        map.get(code)?.facility_name ||
        telemetry.facility_name ||
        code,

      city:
        map.get(code)?.city ||
        telemetry.city ||
        "—",

      iot_device:
        map.get(code)?.iot_device ||
        telemetry.iot_device ||
        null
    });
  });

  return Object.fromEntries(map.entries());
}

export function FlowSenseProvider({ children }) {
  const facilitiesRef = useRef({});
  const metadataRef = useRef([]);
  const alertsRef = useRef({});
  const historyRef = useRef({});

  const [facilities, setFacilities] = useState({});
  const [metadataLoaded, setMetadataLoaded] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [connection, setConnection] = useState("connecting");
  const [lastTick, setLastTick] = useState(null);

  /*
   * Load static facility metadata once.
   *
   * WebSocket telemetry is responsible for live values.
   * REST is only used here to supply names, cities and device metadata.
   */
  useEffect(() => {
    let alive = true;

    Promise.all([
      api.facilities(),
      api.anomalies(100)
    ])
      .then(([facilityRows, anomalyRows]) => {
        if (!alive) return;

        metadataRef.current = Array.isArray(facilityRows)
          ? facilityRows
          : [];

        if (Array.isArray(anomalyRows)) {
          anomalyRows.forEach((anomaly) => {
            const key =
              anomaly.id ||
              anomaly.anomaly_id ||
              `${anomaly.facility_code}:${anomaly.anomaly_type}`;

            alertsRef.current[key] = anomaly;
          });
        }

        setMetadataLoaded(true);

        setFacilities((current) =>
          mergeFacilityMetadata(
            metadataRef.current,
            current
          )
        );

        setAlerts(
          Object.values(alertsRef.current)
            .sort(
              (a, b) =>
                new Date(b.detected_at || 0) -
                new Date(a.detected_at || 0)
            )
            .slice(0, 100)
        );
      })
      .catch(() => {
        if (alive) {
          metadataRef.current = [];
          setMetadataLoaded(true);
        }
      });

    return () => {
      alive = false;
    };
  }, []);

  /*
   * ONE realtime WebSocket for the entire application.
   *
   * Every page consumes this provider instead of creating its
   * own WebSocket connection.
   */
  useEffect(() => {
    const disconnect = connectAllFacilities({
      onStatus: setConnection,

      onMessage: (message) => {
        const facility = normalizeMessage(message);
        const code = facility.facility_code;

        if (!code) return;

        facilitiesRef.current[code] = facility;

        const previousHistory =
          historyRef.current[code] || [];

        historyRef.current[code] = [
          ...previousHistory,
          {
            timestamp: facility.timestamp,
            energy_kwh: facility.energy_kwh,
            water_kl: facility.water_kl,
            power_kw: facility.power_kw,
            water_flow_lpm: facility.water_flow_lpm,
            water_pressure_bar:
              facility.water_pressure_bar
          }
        ].slice(-120);

        const alert = buildAlert(facility);

        if (alert) {
          alertsRef.current[alert.id] = {
            ...alertsRef.current[alert.id],
            ...alert
          };
        }

        const merged = mergeFacilityMetadata(
          metadataRef.current,
          facilitiesRef.current
        );

        setFacilities(merged);

        setAlerts(
          Object.values(alertsRef.current)
            .sort(
              (a, b) =>
                new Date(b.detected_at || 0) -
                new Date(a.detected_at || 0)
            )
            .slice(0, 100)
        );

        setLastTick(facility.timestamp);
      }
    });

    return disconnect;
  }, []);

  const facilityList = useMemo(
    () => Object.values(facilities),
    [facilities]
  );

  const totals = useMemo(() => {
    let energy = 0;
    let water = 0;
    let power = 0;
    let energyLoss = 0;
    let waterLoss = 0;

    facilityList.forEach((facility) => {
      energy += Number(facility.energy_kwh) || 0;
      water += Number(facility.water_kl) || 0;
      power += Number(facility.power_kw) || 0;
      energyLoss +=
        Number(facility.estimated_energy_loss_kwh) || 0;
      waterLoss +=
        Number(facility.estimated_water_loss_kl) || 0;
    });

    const energyCost = energy * ENERGY_TARIFF;
    const waterCost = water * WATER_TARIFF;

    return {
      energy,
      water,
      power,
      energyLoss,
      waterLoss,
      energyCost,
      waterCost,
      totalCost: energyCost + waterCost
    };
  }, [facilityList]);

  const statusCounts = useMemo(
    () =>
      facilityList.reduce(
        (result, facility) => {
          const status = normalizeStatus(
            facility.facility_status ||
              facility.telemetry_status
          );

          if (status === "critical") {
            result.critical += 1;
          } else if (status === "attention") {
            result.attention += 1;
          } else {
            result.healthy += 1;
          }

          return result;
        },
        {
          healthy: 0,
          attention: 0,
          critical: 0
        }
      ),
    [facilityList]
  );

  const averageEfficiency = useMemo(() => {
    if (!facilityList.length) {
      return {
        energy: 0,
        water: 0
      };
    }

    const energy =
      facilityList.reduce(
        (sum, facility) =>
          sum + (Number(facility.energy_score) || 0),
        0
      ) / facilityList.length;

    const water =
      facilityList.reduce(
        (sum, facility) =>
          sum + (Number(facility.water_score) || 0),
        0
      ) / facilityList.length;

    return {
      energy: Number(energy.toFixed(1)),
      water: Number(water.toFixed(1))
    };
  }, [facilityList]);

  const getFacility = (code) =>
    facilitiesRef.current[code] ||
    facilities[code] ||
    null;

  const getHistory = (code) =>
    historyRef.current[code] || [];

  const value = {
    facilities,
    facilityList,
    metadataLoaded,

    alerts,
    connection,
    lastTick,

    totals,
    statusCounts,
    averageEfficiency,

    getFacility,
    getHistory,

    energyTariff: ENERGY_TARIFF,
    waterTariff: WATER_TARIFF
  };

  return (
    <FlowSenseContext.Provider value={value}>
      {children}
    </FlowSenseContext.Provider>
  );
}

export function useFlowSense() {
  const context = useContext(FlowSenseContext);

  if (!context) {
    throw new Error(
      "useFlowSense must be used inside FlowSenseProvider"
    );
  }

  return context;
}
