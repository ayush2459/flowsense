import React, { useEffect, useMemo, useState } from "react";
import {
  Wrench,
  CalendarDays,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Search,
  RefreshCw,
  Plus,
  X,
  Cpu,
  UserRound,
  Building2,
  CircleDollarSign,
  ShieldCheck,
  ClipboardList,
} from "lucide-react";

import { api } from "../services/api";
import "./MaintenancePage.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleDateString([], {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}


function getMaintenanceStatus(service) {
  if (!service.next_service_date) {
    return "completed";
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const nextDate = new Date(service.next_service_date);
  nextDate.setHours(0, 0, 0, 0);

  const diffDays = Math.ceil(
    (nextDate.getTime() - today.getTime()) /
      (1000 * 60 * 60 * 24)
  );

  if (diffDays < 0) return "overdue";
  if (diffDays <= 30) return "upcoming";

  return "scheduled";
}


function statusLabel(status) {
  const labels = {
    completed: "Completed",
    overdue: "Overdue",
    upcoming: "Due Soon",
    scheduled: "Scheduled",
  };

  return labels[status] || "Recorded";
}


function normalizeDevice(device) {
  return {
    ...device,
    id: device.iot_device_id || device.device_id || device.id,
    code: device.device_code || device.code,
    name:
      device.device_name ||
      device.device_code ||
      device.code ||
      "Unnamed Device",
    facility:
      device.facility_id ||
      device.facility_code ||
      "—",
  };
}


function MaintenancePage() {
  const [devices, setDevices] = useState([]);
  const [services, setServices] = useState([]);
  const [summary, setSummary] = useState({
    total_services: 0,
    upcoming: 0,
    overdue: 0,
    repairs_required: 0,
    warranty_services: 0,
    total_service_cost: 0,
  });

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const [showForm, setShowForm] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    service_date: "",
    service_type: "maintenance",
    description: "",
    technician_name: "",
    service_vendor: "",
    repair_required: false,
    warranty_applicable: false,
    warranty_claim_reference: "",
    service_cost: "",
    next_service_date: "",
  });


  // ============================================================
  // LOAD DEVICES
  // ============================================================

  const loadDevices = async () => {
  try {
    const response = await fetch(
      `${API_BASE}/api/devices`
    );

    if (!response.ok) {
      throw new Error(
        `Device request failed: HTTP ${response.status}`
      );
    }

    const data = await response.json();

    const rawDevices = Array.isArray(data)
      ? data
      : data?.devices ||
        data?.items ||
        data?.data ||
        [];

    const normalized = rawDevices.map(
      normalizeDevice
    );

    setDevices(normalized);

    return normalized;
  } catch (err) {
    console.error(
      "Device loading failed:",
      err
    );

    setError(
      err.message ||
        "Unable to load IoT devices."
    );

    return [];
  }
};


  // ============================================================
  // LOAD MAINTENANCE SUMMARY + RECORDS
  // ============================================================

  const loadMaintenance = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const [summaryResponse, recordsResponse] =
        await Promise.all([
          fetch(`${API_BASE}/api/maintenance/summary`),
          fetch(`${API_BASE}/api/maintenance/records`),
        ]);

      if (!summaryResponse.ok) {
        throw new Error(
          `Maintenance summary request failed: ${summaryResponse.status}`
        );
      }

      if (!recordsResponse.ok) {
        throw new Error(
          `Maintenance records request failed: ${recordsResponse.status}`
        );
      }

      const summaryData = await summaryResponse.json();
      const recordsData = await recordsResponse.json();

      setSummary({
        total_services:
          Number(summaryData.total_services) || 0,

        upcoming:
          Number(summaryData.upcoming) || 0,

        overdue:
          Number(summaryData.overdue) || 0,

        repairs_required:
          Number(summaryData.repairs_required) || 0,

        warranty_services:
          Number(summaryData.warranty_services) || 0,

        total_service_cost:
          Number(summaryData.total_service_cost) || 0,
      });

      const records = Array.isArray(recordsData.records)
        ? recordsData.records
        : [];

      setServices(records);
    } catch (err) {
      console.error("Maintenance load failed:", err);

      setError(
        err.message ||
          "Unable to load maintenance information from the FlowSense backend."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };


  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    const initialize = async () => {
      await Promise.all([
        loadDevices(),
        loadMaintenance(),
      ]);
    };

    initialize();
  }, []);


  // ============================================================
  // ENRICH RECORDS
  // ============================================================

  const enrichedServices = useMemo(() => {
    return services.map((service) => ({
      ...service,

      maintenance_status:
        service.maintenance_status ||
        getMaintenanceStatus(service),
    }));
  }, [services]);


  // ============================================================
  // SERVICE TYPES
  // ============================================================

  const serviceTypes = useMemo(() => {
    return [
      ...new Set(
        services
          .map((service) => service.service_type)
          .filter(Boolean)
      ),
    ].sort();
  }, [services]);


  // ============================================================
  // FILTERED RECORDS
  // ============================================================

  const filteredServices = useMemo(() => {
    const query = search.trim().toLowerCase();

    return enrichedServices.filter((service) => {
      const matchesSearch =
        !query ||
        [
          service.device_code,
          service.device_name,
          service.facility_id,
          service.service_type,
          service.description,
          service.technician_name,
          service.service_vendor,
        ]
          .filter(Boolean)
          .some((value) =>
            String(value)
              .toLowerCase()
              .includes(query)
          );

      const matchesStatus =
        statusFilter === "all" ||
        service.maintenance_status === statusFilter;

      const matchesType =
        typeFilter === "all" ||
        service.service_type === typeFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesType
      );
    });
  }, [
    enrichedServices,
    search,
    statusFilter,
    typeFilter,
  ]);


  // ============================================================
  // FORM
  // ============================================================

  const openNewMaintenance = () => {
    setSelectedDevice(
      devices.length ? devices[0] : null
    );

    setForm({
      service_date: new Date()
        .toISOString()
        .slice(0, 16),

      service_type: "maintenance",
      description: "",
      technician_name: "",
      service_vendor: "",
      repair_required: false,
      warranty_applicable: false,
      warranty_claim_reference: "",
      service_cost: "",
      next_service_date: "",
    });

    setError("");
    setShowForm(true);
  };


  const submitMaintenance = async (event) => {
    event.preventDefault();

    if (!selectedDevice?.id) {
      setError("Please select a device.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const payload = {
        device_id: selectedDevice.id,

        service_date:
          form.service_date || null,

        service_type:
          form.service_type || "maintenance",

        description:
          form.description || null,

        technician_name:
          form.technician_name || null,

        service_vendor:
          form.service_vendor || null,

        repair_required:
          Boolean(form.repair_required),

        warranty_applicable:
          Boolean(form.warranty_applicable),

        warranty_claim_reference:
          form.warranty_applicable
            ? form.warranty_claim_reference || null
            : null,

        service_cost:
          form.service_cost === ""
            ? null
            : Number(form.service_cost),

        next_service_date:
          form.next_service_date || null,
      };

      const response = await fetch(
        `${API_BASE}/api/maintenance/records`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify(payload),
        }
      );

      const responseText = await response.text();

      if (!response.ok) {
        throw new Error(
          responseText ||
            `Failed to create maintenance record. HTTP ${response.status}`
        );
      }

      setShowForm(false);

      await loadMaintenance(true);
    } catch (err) {
      console.error(
        "Maintenance creation failed:",
        err
      );

      setError(
        err.message ||
          "Unable to save the maintenance record."
      );
    } finally {
      setSaving(false);
    }
  };


  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="maintenance-page">

      {/* HEADER */}
      <div className="maintenance-header">

        <div>
          <div className="maintenance-eyebrow">
            <Wrench size={15} />
            ASSET MAINTENANCE
          </div>

          <h1>Maintenance</h1>

          <p>
            Manage real maintenance records, service
            schedules, repairs, warranty activity and
            service history across FlowSense IoT assets.
          </p>
        </div>

        <div className="maintenance-header-actions">

          <button
            className="maintenance-secondary-btn"
            onClick={() => loadMaintenance(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? "maintenance-spin"
                  : ""
              }
            />

            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>

          <button
            className="maintenance-primary-btn"
            onClick={openNewMaintenance}
            disabled={!devices.length}
          >
            <Plus size={17} />
            Record Maintenance
          </button>

        </div>
      </div>


      {/* ERROR */}
      {error && (
        <div className="maintenance-error">
          <AlertTriangle size={18} />

          <span>{error}</span>

          <button
            type="button"
            onClick={() => setError("")}
          >
            <X size={15} />
          </button>
        </div>
      )}


      {/* KPI GRID */}
      <div className="maintenance-kpi-grid">

        <div className="maintenance-kpi">
          <div className="maintenance-kpi-icon">
            <ClipboardList size={20} />
          </div>

          <span>Total Services</span>

          <strong>
            {summary.total_services}
          </strong>

          <small>
            Recorded service history
          </small>
        </div>


        <div className="maintenance-kpi">
          <div className="maintenance-kpi-icon upcoming">
            <Clock3 size={20} />
          </div>

          <span>Due Soon</span>

          <strong>
            {summary.upcoming}
          </strong>

          <small>
            Scheduled maintenance
          </small>
        </div>


        <div className="maintenance-kpi">
          <div className="maintenance-kpi-icon overdue">
            <AlertTriangle size={20} />
          </div>

          <span>Overdue</span>

          <strong>
            {summary.overdue}
          </strong>

          <small>
            Past next-service date
          </small>
        </div>


        <div className="maintenance-kpi">
          <div className="maintenance-kpi-icon repair">
            <Wrench size={20} />
          </div>

          <span>Repairs Required</span>

          <strong>
            {summary.repairs_required}
          </strong>

          <small>
            Records requiring repair
          </small>
        </div>


        <div className="maintenance-kpi">
          <div className="maintenance-kpi-icon cost">
            <CircleDollarSign size={20} />
          </div>

          <span>Total Service Cost</span>

          <strong>
            ₹
            {summary.total_service_cost.toLocaleString(
              "en-IN"
            )}
          </strong>

          <small>
            Recorded maintenance cost
          </small>
        </div>

      </div>


      {/* SECONDARY METRICS */}
      <div className="maintenance-secondary-metrics">

        <div className="maintenance-mini-card">
          <ShieldCheck size={17} />

          <div>
            <span>Warranty Services</span>

            <strong>
              {summary.warranty_services}
            </strong>
          </div>
        </div>


        <div className="maintenance-mini-card">
          <CalendarDays size={17} />

          <div>
            <span>Maintenance Records</span>

            <strong>
              {services.length}
            </strong>
          </div>
        </div>


        <div className="maintenance-mini-card">
          <Cpu size={17} />

          <div>
            <span>Registered Devices</span>

            <strong>
              {devices.length}
            </strong>
          </div>
        </div>

      </div>


      {/* DATABASE INFO */}
      <div className="maintenance-info">
        <ShieldCheck size={19} />

        <div>
          <strong>
            Real maintenance records only
          </strong>

          <span>
            This workspace reads maintenance activity
            directly from the FlowSense service-history
            database. No synthetic maintenance activity
            is generated.
          </span>
        </div>
      </div>


      {/* RECORDS */}
      <section className="maintenance-card">

        <div className="maintenance-card-head">

          <div>
            <h2>Maintenance Records</h2>

            <p>
              {filteredServices.length} of{" "}
              {services.length} records shown
            </p>
          </div>


          <div className="maintenance-filters">

            <div className="maintenance-search">
              <Search size={16} />

              <input
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search device, technician, vendor..."
              />

              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                >
                  <X size={14} />
                </button>
              )}
            </div>


            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(
                  event.target.value
                )
              }
            >
              <option value="all">
                All Status
              </option>

              <option value="upcoming">
                Due Soon
              </option>

              <option value="overdue">
                Overdue
              </option>

              <option value="scheduled">
                Scheduled
              </option>

              <option value="completed">
                Completed
              </option>
            </select>


            <select
              value={typeFilter}
              onChange={(event) =>
                setTypeFilter(
                  event.target.value
                )
              }
            >
              <option value="all">
                All Types
              </option>

              {serviceTypes.map((type) => (
                <option
                  key={type}
                  value={type}
                >
                  {type}
                </option>
              ))}
            </select>

          </div>
        </div>


        {/* LOADING */}
        {loading ? (
          <div className="maintenance-empty">
            <RefreshCw
              className="maintenance-spin"
              size={25}
            />

            <strong>
              Loading maintenance records...
            </strong>

            <span>
              Reading the FlowSense maintenance database.
            </span>
          </div>


        ) : filteredServices.length === 0 ? (

          <div className="maintenance-empty">

            <Wrench size={34} />

            <strong>
              No maintenance records found
            </strong>

            <span>
              {services.length === 0
                ? "There are currently no recorded maintenance services in the database."
                : "No records match the selected filters."}
            </span>

            {services.length === 0 && (
              <button
                className="maintenance-primary-btn"
                onClick={openNewMaintenance}
                disabled={!devices.length}
              >
                <Plus size={16} />
                Record First Maintenance
              </button>
            )}

          </div>


        ) : (

          <div className="maintenance-table-wrap">

            <table className="maintenance-table">

              <thead>
                <tr>
                  <th>Device</th>
                  <th>Service</th>
                  <th>Service Date</th>
                  <th>Technician / Vendor</th>
                  <th>Repair</th>
                  <th>Warranty</th>
                  <th>Next Service</th>
                  <th>Status</th>
                  <th>Cost</th>
                </tr>
              </thead>


              <tbody>

                {filteredServices.map(
                  (service) => (

                    <tr
                      key={
                        service.service_id ||
                        `${service.device_id}-${service.service_date}`
                      }
                    >

                      <td>
                        <div className="maintenance-device">

                          <div className="maintenance-device-icon">
                            <Cpu size={16} />
                          </div>

                          <div>
                            <strong>
                              {service.device_code ||
                                "Unknown Device"}
                            </strong>

                            <span>
                              {service.device_name ||
                                "—"}
                            </span>
                          </div>

                        </div>
                      </td>


                      <td>
                        <div className="maintenance-service">

                          <strong>
                            {service.service_type ||
                              "Maintenance"}
                          </strong>

                          <span>
                            {service.description ||
                              "No description"}
                          </span>

                        </div>
                      </td>


                      <td>
                        {formatDate(
                          service.service_date
                        )}
                      </td>


                      <td>
                        <div className="maintenance-person">

                          {service.technician_name && (
                            <span>
                              <UserRound size={13} />
                              {service.technician_name}
                            </span>
                          )}

                          {service.service_vendor && (
                            <span>
                              <Building2 size={13} />
                              {service.service_vendor}
                            </span>
                          )}

                          {!service.technician_name &&
                            !service.service_vendor &&
                            "—"}

                        </div>
                      </td>


                      <td>
                        <span
                          className={
                            service.repair_required
                              ? "maintenance-badge warning"
                              : "maintenance-badge neutral"
                          }
                        >
                          {service.repair_required
                            ? "Required"
                            : "No"}
                        </span>
                      </td>


                      <td>
                        <span
                          className={
                            service.warranty_applicable
                              ? "maintenance-badge success"
                              : "maintenance-badge neutral"
                          }
                        >
                          {service.warranty_applicable
                            ? "Applicable"
                            : "No"}
                        </span>
                      </td>


                      <td>
                        {formatDate(
                          service.next_service_date
                        )}
                      </td>


                      <td>
                        <span
                          className={`maintenance-status ${service.maintenance_status}`}
                        >
                          {statusLabel(
                            service.maintenance_status
                          )}
                        </span>
                      </td>


                      <td>
                        {service.service_cost != null
                          ? `₹${Number(
                              service.service_cost
                            ).toLocaleString(
                              "en-IN"
                            )}`
                          : "—"}
                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {/* MODAL */}
      {showForm && (

        <div
          className="maintenance-modal-backdrop"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowForm(false);
            }
          }}
        >

          <div className="maintenance-modal">

            <div className="maintenance-modal-head">

              <div>
                <h2>
                  Record Maintenance
                </h2>

                <p>
                  Add a real service record to
                  the FlowSense maintenance database.
                </p>
              </div>

              <button
                type="button"
                onClick={() =>
                  setShowForm(false)
                }
              >
                <X size={19} />
              </button>

            </div>


            <form
              onSubmit={submitMaintenance}
              className="maintenance-form"
            >

              <label>
                Device

                <select
                  value={
                    selectedDevice?.id || ""
                  }
                  onChange={(event) => {
                    const device =
                      devices.find(
                        (item) =>
                          item.id ===
                          event.target.value
                      );

                    setSelectedDevice(device);
                  }}
                  required
                >

                  <option value="">
                    Select device
                  </option>

                  {devices.map((device) => (
                    <option
                      key={device.id}
                      value={device.id}
                    >
                      {device.code} —{" "}
                      {device.name}
                    </option>
                  ))}

                </select>

              </label>


              <div className="maintenance-form-grid">

                <label>
                  Service Date

                  <input
                    type="datetime-local"
                    value={
                      form.service_date
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        service_date:
                          event.target.value,
                      })
                    }
                    required
                  />
                </label>


                <label>
                  Service Type

                  <select
                    value={
                      form.service_type
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        service_type:
                          event.target.value,
                      })
                    }
                  >
                    <option value="maintenance">
                      Maintenance
                    </option>

                    <option value="inspection">
                      Inspection
                    </option>

                    <option value="repair">
                      Repair
                    </option>

                    <option value="preventive">
                      Preventive
                    </option>

                    <option value="replacement">
                      Replacement
                    </option>

                    <option value="calibration">
                      Calibration
                    </option>
                  </select>
                </label>


                <label>
                  Technician

                  <input
                    value={
                      form.technician_name
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        technician_name:
                          event.target.value,
                      })
                    }
                    placeholder="Technician name"
                  />
                </label>


                <label>
                  Service Vendor

                  <input
                    value={
                      form.service_vendor
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        service_vendor:
                          event.target.value,
                      })
                    }
                    placeholder="Vendor / company"
                  />
                </label>


                <label>
                  Service Cost

                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={
                      form.service_cost
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        service_cost:
                          event.target.value,
                      })
                    }
                    placeholder="0.00"
                  />
                </label>


                <label>
                  Next Service Date

                  <input
                    type="date"
                    value={
                      form.next_service_date
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        next_service_date:
                          event.target.value,
                      })
                    }
                  />
                </label>

              </div>


              <label>
                Description

                <textarea
                  value={
                    form.description
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      description:
                        event.target.value,
                    })
                  }
                  placeholder="Describe the maintenance/service performed..."
                  rows={4}
                />

              </label>


              <div className="maintenance-checkbox-row">

                <label className="maintenance-check">

                  <input
                    type="checkbox"
                    checked={
                      form.repair_required
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        repair_required:
                          event.target.checked,
                      })
                    }
                  />

                  Repair required

                </label>


                <label className="maintenance-check">

                  <input
                    type="checkbox"
                    checked={
                      form.warranty_applicable
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        warranty_applicable:
                          event.target.checked,
                      })
                    }
                  />

                  Warranty applicable

                </label>

              </div>


              {form.warranty_applicable && (

                <label>
                  Warranty Claim Reference

                  <input
                    value={
                      form.warranty_claim_reference
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        warranty_claim_reference:
                          event.target.value,
                      })
                    }
                    placeholder="Warranty claim reference"
                  />
                </label>

              )}


              <div className="maintenance-form-actions">

                <button
                  type="button"
                  className="maintenance-secondary-btn"
                  onClick={() =>
                    setShowForm(false)
                  }
                >
                  Cancel
                </button>


                <button
                  type="submit"
                  className="maintenance-primary-btn"
                  disabled={
                    saving ||
                    !selectedDevice?.id
                  }
                >
                  {saving
                    ? "Saving..."
                    : "Save Maintenance Record"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}


export default MaintenancePage;