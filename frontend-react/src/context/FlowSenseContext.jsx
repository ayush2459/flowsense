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

const DEFAULT_EXPECTED_ENERGY = 320;
const DEFAULT_EXPECTED_WATER = 30;
const DEFAULT_TREATMENT_RATE = 91.1;
const DEFAULT_REUSE_RATE = 67.3;

function toNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeStatus(value) {
  const status = String(value || "").toLowerCase().trim();

  if (status === "critical") {
    return "critical";
  }

  if (
    status === "attention" ||
    status === "needs attention" ||
    status === "warning"
  ) {
    return "attention";
  }

  return "healthy";
}

function calculateEnergyLoss(data, detection, expectedEnergy) {
  const explicitLoss =
    detection?.estimated_energy_loss_kwh ??
    data?.estimated_energy_loss_kwh;

  if (
    explicitLoss !== undefined &&
    explicitLoss !== null &&
    Number.isFinite(Number(explicitLoss))
  ) {
    return Math.max(0, Number(explicitLoss));
  }

  return Math.max(
    0,
    toNumber(data?.energy_kwh) -
      toNumber(expectedEnergy, DEFAULT_EXPECTED_ENERGY)
  );
}

function calculateWaterLoss(data, detection, expectedWater) {
  // The realtime simulator already sends the actual calculated
  // water loss. Prefer that value over backend detection output,
  // because backend detection may legitimately return 0.
  const dataLoss = data?.estimated_water_loss_kl;

  if (
    dataLoss !== undefined &&
    dataLoss !== null &&
    Number.isFinite(Number(dataLoss))
  ) {
    return Math.max(0, Number(dataLoss));
  }

  // Use backend detection loss only when the realtime telemetry
  // packet does not contain a water-loss value.
  const detectionLoss =
    detection?.estimated_water_loss_kl;

  if (
    detectionLoss !== undefined &&
    detectionLoss !== null &&
    Number.isFinite(Number(detectionLoss))
  ) {
    return Math.max(0, Number(detectionLoss));
  }

  // Final fallback: calculate excess water consumption
  // against the expected baseline.
  const waterConsumption =
    toNumber(data?.water_kl);

  const expectedConsumption =
    toNumber(
      expectedWater,
      DEFAULT_EXPECTED_WATER
    );

  return Math.max(
    0,
    waterConsumption - expectedConsumption
  );
}

function normalizeMessage(message) {
  const data = message?.data || {};
  const detection = message?.detection || {};

  const anomalies = Array.isArray(detection.anomalies)
    ? detection.anomalies
    : [];

  const primaryAnomaly =
    detection.primary_anomaly || null;

  const toNumber = (value, fallback = 0) => {
    const number = Number(value);
    return Number.isFinite(number)
      ? number
      : fallback;
  };

  const firstDefined = (...values) => {
    for (const value of values) {
      if (
        value !== undefined &&
        value !== null &&
        value !== ""
      ) {
        return value;
      }
    }

    return undefined;
  };

  const expectedEnergy = toNumber(
    firstDefined(
      data.expected_energy_kwh,
      detection.expected_energy_kwh,
      320
    )
  );

  const expectedWater = toNumber(
    firstDefined(
      data.expected_water_kl,
      detection.expected_water_kl,
      30
    )
  );

  const energy = toNumber(
    firstDefined(
      data.energy_kwh,
      data.energy,
      data.energy_consumption
    )
  );

  const water = toNumber(
    firstDefined(
      data.water_kl,
      data.water,
      data.water_consumption
    )
  );

  const power = toNumber(
    firstDefined(
      data.power_kw,
      data.power,
      data.demand_kw
    )
  );

  const voltage = toNumber(
    firstDefined(
      data.voltage_v,
      data.voltage,
      data.voltage_volts
    )
  );

  const current = toNumber(
    firstDefined(
      data.current_a,
      data.current,
      data.current_amp,
      data.current_amps
    )
  );

  const waterFlow = toNumber(
    firstDefined(
      data.water_flow_lpm,
      data.flow_lpm,
      data.water_flow
    )
  );

  const waterPressure = toNumber(
    firstDefined(
      data.water_pressure_bar,
      data.pressure_bar,
      data.water_pressure,
      data.pressure
    )
  );

  const temperature = toNumber(
    firstDefined(
      data.temperature_c,
      data.temperature,
      data.temp_c,
      data.temp
    )
  );

  const humidity = toNumber(
    firstDefined(
      data.humidity_percent,
      data.humidity,
      data.humidity_pct
    )
  );

  const vibration = toNumber(
    firstDefined(
      data.vibration_mm_s,
      data.vibration,
      data.vibration_mms
    )
  );

  const treatmentRate = toNumber(
    firstDefined(
      data.treatment_rate,
      data.treatment_percent,
      data.treatment
    ),
    DEFAULT_TREATMENT_RATE
  );

  const reuseRate = toNumber(
    firstDefined(
      data.reuse_rate,
      data.reuse_percent,
      data.reuse
    ),
    DEFAULT_REUSE_RATE
  );

  const rawStatus =
    detection.facility_status ||
    data.status ||
    (
      data.anomaly ||
      anomalies.length ||
      primaryAnomaly
        ? "attention"
        : "healthy"
    );

  const anomalyCount = toNumber(
    detection.anomaly_count ??
      anomalies.length
  );

  const energyLoss =
    detection.estimated_energy_loss_kwh ??
    data.estimated_energy_loss_kwh ??
    Math.max(
      0,
      energy - expectedEnergy
    );

  const waterLoss =
    data.estimated_water_loss_kl ??
    detection.estimated_water_loss_kl ??
    Math.max(
      0,
      water - expectedWater
    );

  return {
    facility_code:
      message?.facility_code ||
      data.facility_code ||
      null,

    timestamp:
      message?.timestamp ||
      data.reading_time ||
      new Date().toISOString(),

    // ------------------------------------------------------
    // ENERGY
    // ------------------------------------------------------

    energy_kwh:
      energy,

    expected_energy_kwh:
      expectedEnergy,

    // ------------------------------------------------------
    // WATER
    // ------------------------------------------------------

    water_kl:
      water,

    expected_water_kl:
      expectedWater,

    // ------------------------------------------------------
    // ELECTRICAL
    // ------------------------------------------------------

    power_kw:
      power,

    voltage_v:
      voltage,

    current_a:
      current,

    // ------------------------------------------------------
    // WATER TELEMETRY
    // ------------------------------------------------------

    water_flow_lpm:
      waterFlow,

    water_pressure_bar:
      waterPressure,

    // ------------------------------------------------------
    // RESOURCE REUSE / TREATMENT
    // ------------------------------------------------------

    treatment_rate:
      treatmentRate,

    reuse_rate:
      reuseRate,

    // ------------------------------------------------------
    // ENVIRONMENT
    // ------------------------------------------------------

    temperature_c:
      temperature,

    humidity_percent:
      humidity,

    vibration_mm_s:
      vibration,

    // ------------------------------------------------------
    // LEAK / DETECTION
    // ------------------------------------------------------

    leak_detected:
      Boolean(data.leak_detected),

    telemetry_anomaly:
      Boolean(data.anomaly),

    telemetry_anomaly_type:
      data.anomaly_type || null,

    telemetry_status:
      normalizeStatus(data.status),

    facility_status:
      normalizeStatus(rawStatus),

    anomaly_count:
      anomalyCount,

    // ------------------------------------------------------
    // LOSSES
    // ------------------------------------------------------

    estimated_energy_loss_kwh:
      Math.max(
        0,
        toNumber(energyLoss)
      ),

    estimated_water_loss_kl:
      Math.max(
        0,
        toNumber(waterLoss)
      ),

    // ------------------------------------------------------
    // ANOMALIES
    // ------------------------------------------------------

    anomalies,

    primary_anomaly:
      primaryAnomaly,

    // ------------------------------------------------------
    // EFFICIENCY
    // ------------------------------------------------------

    energy_score:
      toNumber(
        detection.efficiency?.energy_score
      ),

    water_score:
      toNumber(
        detection.efficiency?.water_score
      ),

    recommendation:
      detection.recommendation ||
      null,

    // ------------------------------------------------------
    // DEBUG / RAW DATA
    // ------------------------------------------------------

    _raw:
      message,

    _receivedAt:
      Date.now()
  };
}


function buildAlert(facility) {
  if (
    !facility ||
    (
      !facility.telemetry_anomaly &&
      !facility.anomaly_count &&
      !facility.primary_anomaly &&
      !facility.anomalies?.length
    )
  ) {
    return null;
  }

  const primary =
    facility.primary_anomaly || {};

  const firstAnomaly =
    facility.anomalies?.[0] || {};

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
        facility.facility_status ||
        ""
    ).toLowerCase() === "critical"
      ? "Critical"
      : "Warning";

  return {
    id: `${facility.facility_code}-${type}`,

    anomaly_id:
      primary.anomaly_id ||
      firstAnomaly.anomaly_id ||
      null,

    facility_code:
      facility.facility_code,

    anomaly_type: type,

    severity,

    description:
      primary.description ||
      firstAnomaly.description ||
      (
        type === "water_leak"
          ? "Possible water leakage detected by realtime IoT telemetry."
          : `Realtime IoT signal indicates ${String(
              type
            ).replaceAll("_", " ")}.`
      ),

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
      toNumber(
        primary.deviation_percent ??
          firstAnomaly.deviation_percent
      ),

    estimated_loss:
      toNumber(
        primary.estimated_loss ??
          firstAnomaly.estimated_loss
      )
  };
}

function mergeFacilityMetadata(
  metadata,
  live
) {
  const map = new Map();

  (
    Array.isArray(metadata)
      ? metadata
      : []
  ).forEach((facility) => {
    if (facility?.facility_code) {
      map.set(
        facility.facility_code,
        {
          ...facility
        }
      );
    }
  });

  Object.entries(live || {}).forEach(
    ([code, telemetry]) => {
      const existing =
        map.get(code) || {};

      map.set(code, {
        ...existing,
        ...telemetry,

        facility_code:
          telemetry.facility_code ||
          existing.facility_code ||
          code,

        facility_name:
          existing.facility_name ||
          telemetry.facility_name ||
          code,

        city:
          existing.city ||
          telemetry.city ||
          "â€”",

        iot_device:
          existing.iot_device ||
          telemetry.iot_device ||
          null
      });
    }
  );

  return Object.fromEntries(
    map.entries()
  );
}

export function FlowSenseProvider({
  children
}) {
  const facilitiesRef =
    useRef({});

  const metadataRef =
    useRef([]);

  const alertsRef =
    useRef({});

  const historyRef =
    useRef({});

  const [facilities, setFacilities] =
    useState({});

  const [metadataLoaded, setMetadataLoaded] =
    useState(false);

  const [alerts, setAlerts] =
    useState([]);

  const [connection, setConnection] =
    useState("connecting");

  const [lastTick, setLastTick] =
    useState(null);

  /*
   * Load static metadata and existing alerts once.
   *
   * REST provides facility information.
   * WebSocket provides realtime telemetry.
   */
  useEffect(() => {
    let alive = true;

    Promise.all([
      api.facilities(),
      api.anomalies(100)
    ])
      .then(
        ([
          facilityRows,
          anomalyRows
        ]) => {
          if (!alive) {
            return;
          }

          metadataRef.current =
            Array.isArray(facilityRows)
              ? facilityRows
              : [];

          if (
            Array.isArray(anomalyRows)
          ) {
            anomalyRows.forEach(
              (anomaly) => {
                const key =
                  anomaly.id ||
                  anomaly.anomaly_id ||
                  `${anomaly.facility_code}:${anomaly.anomaly_type}`;

                alertsRef.current[key] =
                  anomaly;
              }
            );
          }

          setMetadataLoaded(true);

          setFacilities((current) =>
            mergeFacilityMetadata(
              metadataRef.current,
              current
            )
          );

          setAlerts(
            Object.values(
              alertsRef.current
            )
              .sort(
                (a, b) =>
                  new Date(
                    b.detected_at || 0
                  ) -
                  new Date(
                    a.detected_at || 0
                  )
              )
              .slice(0, 100)
          );
        }
      )
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
   * ONE realtime WebSocket for the
   * entire application.
   */
  useEffect(() => {
    const disconnect =
      connectAllFacilities({
        onStatus: setConnection,

        onMessage: (message) => {
          const facility =
            normalizeMessage(message);

          const code =
            facility.facility_code;

          if (!code) {
            return;
          }

          const previous =
            facilitiesRef.current[code] ||
            {};

          facilitiesRef.current[code] = {
            ...previous,
            ...facility,

            expected_energy_kwh:
              toNumber(
                facility.expected_energy_kwh,
                previous.expected_energy_kwh ??
                  DEFAULT_EXPECTED_ENERGY
              ),

            expected_water_kl:
              toNumber(
                facility.expected_water_kl,
                previous.expected_water_kl ??
                  DEFAULT_EXPECTED_WATER
              ),

            treatment_rate:
              toNumber(
                facility.treatment_rate,
                previous.treatment_rate ??
                  DEFAULT_TREATMENT_RATE
              ),

            reuse_rate:
              toNumber(
                facility.reuse_rate,
                previous.reuse_rate ??
                  DEFAULT_REUSE_RATE
              ),

            energy_score:
              toNumber(
                facility.energy_score,
                previous.energy_score ?? 0
              ),

            water_score:
              toNumber(
                facility.water_score,
                previous.water_score ?? 0
              )
          };

          /*
           * Keep the last 120 readings
           * per facility.
           */
          const previousHistory =
            historyRef.current[code] ||
            [];

          historyRef.current[code] = [
            ...previousHistory,

            {
              timestamp:
                facility.timestamp,

              energy_kwh:
                facility.energy_kwh,

              expected_energy_kwh:
                facility.expected_energy_kwh,

              water_kl:
                facility.water_kl,

              expected_water_kl:
                facility.expected_water_kl,

              power_kw:
                facility.power_kw,

              voltage_v:
                facility.voltage_v,

              current_a:
                facility.current_a,

              water_flow_lpm:
                facility.water_flow_lpm,

              water_pressure_bar:
                facility.water_pressure_bar,

              temperature_c:
                facility.temperature_c,

              humidity_percent:
                facility.humidity_percent,

              vibration_mm_s:
                facility.vibration_mm_s,

              treatment_rate:
                facility.treatment_rate,

              reuse_rate:
                facility.reuse_rate,

              leak_detected:
                facility.leak_detected,

              telemetry_anomaly:
                facility.telemetry_anomaly,

              telemetry_anomaly_type:
                facility.telemetry_anomaly_type,

              facility_status:
                facility.facility_status,

              anomaly_count:
                facility.anomaly_count,

              primary_anomaly:
                facility.primary_anomaly,

              energy_score:
                facility.energy_score,

              water_score:
                facility.water_score,

              estimated_energy_loss_kwh:
                facility.estimated_energy_loss_kwh,

              estimated_water_loss_kl:
                facility.estimated_water_loss_kl
            }
          ].slice(-120);

          /*
           * Build/update realtime alert.
           */
          const alert =
            buildAlert(facility);

          if (alert) {
            alertsRef.current[
              alert.id
            ] = {
              ...alertsRef.current[
                alert.id
              ],
              ...alert
            };
          }

          /*
           * Merge live telemetry with
           * static facility metadata.
           */
          const merged =
            mergeFacilityMetadata(
              metadataRef.current,
              facilitiesRef.current
            );

          setFacilities(merged);

          setAlerts(
            Object.values(
              alertsRef.current
            )
              .sort(
                (a, b) =>
                  new Date(
                    b.detected_at || 0
                  ) -
                  new Date(
                    a.detected_at || 0
                  )
              )
              .slice(0, 100)
          );

          setLastTick(
            facility.timestamp
          );
        }
      });

    return disconnect;
  }, []);

  const facilityList = useMemo(
    () =>
      Object.values(facilities),
    [facilities]
  );

  /*
   * Portfolio totals.
   */
  const totals = useMemo(() => {
    let energy = 0;
    let water = 0;
    let power = 0;
    let energyLoss = 0;
    let waterLoss = 0;

    facilityList.forEach(
      (facility) => {
        energy += toNumber(
          facility.energy_kwh
        );

        water += toNumber(
          facility.water_kl
        );

        power += toNumber(
          facility.power_kw
        );

        energyLoss += toNumber(
          facility.estimated_energy_loss_kwh
        );

        waterLoss += toNumber(
          facility.estimated_water_loss_kl
        );
      }
    );

    const energyCost =
      energy * ENERGY_TARIFF;

    const waterCost =
      water * WATER_TARIFF;

    return {
      energy,
      water,
      power,
      energyLoss,
      waterLoss,

      energyCost,
      waterCost,

      totalCost:
        energyCost + waterCost
    };
  }, [facilityList]);

  /*
   * Facility health counts.
   */
  const statusCounts = useMemo(
    () =>
      facilityList.reduce(
        (result, facility) => {
          const status =
            normalizeStatus(
              facility.facility_status ||
                facility.telemetry_status
            );

          if (status === "critical") {
            result.critical += 1;
          } else if (
            status === "attention"
          ) {
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

  /*
   * Average realtime efficiency.
   */
  const averageEfficiency =
    useMemo(() => {
      if (!facilityList.length) {
        return {
          energy: 0,
          water: 0
        };
      }

      const energy =
        facilityList.reduce(
          (sum, facility) =>
            sum +
            toNumber(
              facility.energy_score
            ),
          0
        ) / facilityList.length;

      const water =
        facilityList.reduce(
          (sum, facility) =>
            sum +
            toNumber(
              facility.water_score
            ),
          0
        ) / facilityList.length;

      return {
        energy: Number(
          energy.toFixed(1)
        ),

        water: Number(
          water.toFixed(1)
        )
      };
    }, [facilityList]);

  const getFacility = (code) =>
    facilitiesRef.current[code] ||
    facilities[code] ||
    null;

  const getHistory = (code) =>
    historyRef.current[code] ||
    [];

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

    energyTariff:
      ENERGY_TARIFF,

    waterTariff:
      WATER_TARIFF
  };

  return (
    <FlowSenseContext.Provider
      value={value}
    >
      {children}
    </FlowSenseContext.Provider>
  );
}

export function useFlowSense() {
  const context =
    useContext(FlowSenseContext);

  if (!context) {
    throw new Error(
      "useFlowSense must be used inside FlowSenseProvider"
    );
  }

  return context;
}

