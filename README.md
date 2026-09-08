# FlowSense

### IoT-Based Energy & Water Monitoring, Loss Detection and Intelligent Insights Platform

FlowSense is an IoT-powered resource monitoring platform designed to help facilities monitor **energy and water consumption**, identify **unaccounted losses and anomalies**, and provide actionable insights through a centralized dashboard.

The system combines **IoT sensing, real-time telemetry, PostgreSQL analytics, FastAPI backend services, React visualization, and AI-assisted recommendations** into a single platform.

---

## 🚀 What is FlowSense?

Facilities often know how much energy and water enters a building, but identifying **where abnormal consumption or losses are occurring** can be difficult.

FlowSense addresses this problem by:

- Monitoring energy and water consumption
- Collecting data through IoT devices
- Comparing main meter readings with observed resource usage
- Detecting abnormal consumption patterns
- Identifying potential losses and anomalies
- Generating alerts based on detected conditions
- Providing facility-level performance insights
- Displaying everything through a centralized dashboard
- Providing AI-assisted recommendations for corrective action

The goal is to turn raw meter and sensor data into **clear, actionable information for facility operators**.

---

## 🎯 Key Objectives

- Reduce energy and water wastage
- Detect abnormal resource consumption
- Identify potential unaccounted losses
- Monitor facility performance from one dashboard
- Provide real-time operational visibility
- Support preventive maintenance
- Help facility teams make data-driven decisions

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │   Energy Main Meter  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │                      │
                    │   FlowSense IoT      │
                    │       Device         │
                    │                      │
                    │ Multiple Sensor      │
                    │ Channels             │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
                    ▼                      ▼
             Energy Telemetry       Water Telemetry
                    │                      │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │    FastAPI Backend   │
                    │                      │
                    │ REST APIs            │
                    │ Business Logic       │
                    │ Anomaly Detection    │
                    │ Reconciliation       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     PostgreSQL       │
                    │                      │
                    │ Facilities           │
                    │ Meters               │
                    │ IoT Devices          │
                    │ IoT Sensors          │
                    │ Meter Readings       │
                    │ Sensor Readings      │
                    │ Baselines            │
                    │ Anomalies            │
                    │ Alerts               │
                    │ Reconciliation       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   React Dashboard    │
                    │                      │
                    │ Energy               │
                    │ Water                │
                    │ Alerts               │
                    │ Facilities           │
                    │ Analytics            │
                    │ AI Insights          │
                    └──────────────────────┘
```

---

## 🔌 IoT Architecture

FlowSense is designed around a practical facility-level IoT architecture.

Each facility can have:

* **1 main energy meter**
* **1 main water meter**
* **1 FlowSense IoT device**
* Multiple sensor channels within the IoT device

The IoT device can collect multiple parameters without requiring a separate complete IoT gateway for every individual component.

### Energy Monitoring

The system can monitor parameters such as:

* Energy consumption
* Power
* Voltage
* Current

### Water Monitoring

The system can monitor:

* Water consumption
* Water flow
* Water pressure
* Leak conditions

### Environmental / Equipment Monitoring

Additional sensor channels can provide:

* Temperature
* Humidity
* Vibration

This allows FlowSense to correlate resource consumption with operational conditions.

---

## 📊 Dashboard

FlowSense uses a centralized dashboard designed to provide important information without forcing users to navigate through multiple screens.

The main dashboard provides visibility into:

* Total energy consumption
* Total water consumption
* Energy efficiency
* Water efficiency
* Detected losses
* Critical alerts
* Facility performance
* Resource trends
* Anomalies
* Savings opportunities
* AI recommendations
* Live operational information

The dashboard also provides navigation to detailed pages when deeper analysis is required.

---

## 🧠 Loss Detection

One of the main purposes of FlowSense is to identify **unaccounted resource usage**.

The platform compares:

```text
Main Meter Reading
        ↓
Expected / Baseline Usage
        ↓
Observed IoT Usage
        ↓
Difference
        ↓
Potential Loss / Anomaly
```

For example:

```text
Main Water Meter
       │
       ▼
    1000 L
       │
       ├───────────────┐
       │               │
       ▼               ▼
Expected Usage     Observed Usage
   900 L              760 L
       │               │
       └───────┬───────┘
               ▼
        140 L Unaccounted
               │
               ▼
          Possible Loss
```

This allows facility teams to investigate abnormal resource consumption instead of simply seeing a high consumption number.

---

## 🚨 Anomaly Detection

FlowSense stores and analyzes abnormal readings using factors such as:

* Expected values
* Actual values
* Deviation percentage
* Resource type
* Sensor source
* Severity
* Detection timestamp
* Estimated loss

Anomalies can be classified and surfaced through the Alerts section of the platform.

---

## 💧 Water Monitoring

The water monitoring system provides visibility into:

* Water consumption
* Flow rate
* Pressure
* Leak detection
* Abnormal usage
* Estimated water losses
* Facility-level water performance

This can help identify conditions such as unexpected flow or consumption during periods where usage should normally be low.

---

## ⚡ Energy Monitoring

The energy monitoring system provides:

* Energy consumption
* Power monitoring
* Voltage monitoring
* Current monitoring
* Consumption trends
* Abnormal energy usage
* Estimated energy losses
* Facility-level energy performance

---

## 🏢 Multi-Facility Monitoring

FlowSense is designed to support multiple facilities from a centralized system.

Each facility can have:

```text
Facility
 ├── Energy Meter
 ├── Water Meter
 └── FlowSense IoT Device
      ├── Energy Sensors
      ├── Water Sensors
      ├── Environmental Sensors
      └── Equipment Sensors
```

This allows facility managers to compare performance and identify locations requiring attention.

---

## 🤖 AI Insights

The platform is designed to provide AI-assisted recommendations based on detected conditions.

Examples include:

* Investigate abnormal water consumption
* Check equipment operating conditions
* Inspect potential leakage
* Review unusual energy consumption
* Prioritize facilities with higher losses
* Recommend operational improvements

The objective is to move from:

**"Something is wrong."**

to:

**"This facility is showing abnormal consumption, the deviation is significant, and this is what should be investigated."**

---

## 🗄️ Database

FlowSense uses PostgreSQL for storing operational and analytical data.

The database includes entities for:

* Facilities
* Meters
* IoT devices
* IoT sensors
* Meter readings
* Sensor readings
* Baselines
* Anomalies
* Alerts
* Resource reconciliation
* Monthly summaries

The project also includes database views for dashboard-oriented queries.

### Important Views

```text
v_facility_dashboard
v_recent_anomalies
v_resource_reconciliation
v_yearly_facility_summary
```

These views simplify access to processed information required by the dashboard.

---

## 🔗 Backend API

The backend is implemented using **FastAPI**.

Main API capabilities include:

```text
GET /api/facilities

GET /api/facilities/{facility_code}/summary

GET /api/facilities/{facility_code}/anomalies

GET /api/anomalies/recent

GET /api/facilities/{facility_code}/reconciliation

GET /api/facilities/{facility_code}/yearly-summary

GET /api/facilities/{facility_code}/energy

GET /api/facilities/{facility_code}/water

GET /api/devices/{device_code}/health
```

The API acts as the communication layer between PostgreSQL and the React frontend.

---

## 🛠️ Technology Stack

### Frontend

* React
* Vite
* JavaScript
* React Router
* Recharts
* Lucide React
* CSS

### Backend

* Python
* FastAPI
* SQLAlchemy
* Uvicorn

### Database

* PostgreSQL

### IoT / Data Simulation

* Python
* Sensor telemetry simulation
* Meter reading simulation

### Development Tools

* Git
* GitHub
* REST APIs
* JSON

---

## 📁 Project Structure

```text
flowsense/
│
├── backend/
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── requirements.txt
│
├── db/
│   ├── schema.sql
│   ├── schema_3h.sql
│   └── schema_3h_month.sql
│
├── frontend-react/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── frontend/
│   ├── pages/
│   ├── api.js
│   ├── app.js
│   ├── components.js
│   ├── index.html
│   └── styles.css
│
└── simulator/
    ├── live_feed.py
    └── requirements.txt
```

---

## 🖥️ Application Pages

The React application currently provides routes for:

| Page             | Purpose                          |
| ---------------- | -------------------------------- |
| Overview         | Centralized FlowSense dashboard  |
| Facilities       | Facility listing and performance |
| Facility Details | Detailed facility monitoring     |
| Energy           | Energy trends and analysis       |
| Water            | Water trends and analysis        |
| Alerts           | Detected anomalies and alerts    |
| Reports          | Reporting workspace              |
| Analytics        | Analytical workspace             |
| AI Insights      | AI recommendation workspace      |
| Devices          | IoT device monitoring            |
| Settings         | Application settings             |

---

## ⚙️ Local Setup

### 1. Clone the Repository

```bash
git clone [https://github.com/ayush2459/flowsense.git](https://github.com/ayush2459/flowsense.git)
cd flowsense
```

---

### 2. Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```cmd
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=your_postgresql_connection_string
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Backend:

```text
[http://127.0.0.1:8000](http://127.0.0.1:8000)
```

Interactive API documentation:

```text
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
```

---

### 3. Frontend Setup

Open another terminal and navigate to:

```bash
cd frontend-react
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The Vite development server will display the local frontend URL in the terminal.

---

## 🧪 Data Simulation

The project includes a Python-based telemetry simulator.

Navigate to:

```bash
cd simulator
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python live_feed.py
```

The simulator can be used during development to generate resource telemetry and test the monitoring pipeline.

---

## 🔐 Environment Variables

Sensitive credentials should **never be committed to GitHub**.

The backend `.env` file is excluded through `.gitignore`.

Example:

```env
DATABASE_URL=your_database_url
```

Never place real database passwords, API keys, tokens, or other secrets directly inside source code.

---

## 📈 Data Flow

The complete application flow is:

```text
Meters + Sensors
       ↓
IoT Device
       ↓
Telemetry
       ↓
FastAPI Backend
       ↓
PostgreSQL
       ↓
Data Processing
       ↓
Anomaly Detection
       ↓
Resource Reconciliation
       ↓
REST API
       ↓
React Dashboard
       ↓
Alerts + Analytics + AI Insights
```

---

## 🔍 Resource Reconciliation

FlowSense uses reconciliation to compare different measurements of a resource.

Conceptually:

```text
Unaccounted Resource
=
Main Meter
-
Observed / Expected Usage
```

The system stores:

* Main meter value
* Observed IoT value
* Expected value
* Unaccounted value
* Unaccounted percentage
* Estimated loss
* Status

This provides a structured way to investigate resource discrepancies.

---

## 📊 Development Dataset

The development database has been populated with multi-facility telemetry and analytical data to support dashboard development and testing.

Current development data includes:

* 100 facilities
* 200 meters
* 100 IoT devices
* 1,300 IoT sensors
* Meter readings
* Sensor readings
* Baseline records
* Reconciliation records
* Anomaly records
* Alert records
* Monthly summaries

This dataset is intended for development and demonstration purposes.

---

## 🔮 Future Improvements

Potential future enhancements include:

* Live IoT hardware integration
* MQTT-based telemetry ingestion
* Real-time WebSocket updates
* Advanced anomaly detection models
* Predictive maintenance
* More detailed facility-level localization of losses
* Automated report generation
* Advanced AI recommendations
* Role-based access control
* Cloud deployment
* Mobile-friendly monitoring
* Historical trend forecasting
* Automated notifications

---

## 🎯 Why FlowSense?

Traditional monitoring systems often answer:

**"How much did we consume?"**

FlowSense aims to answer a more useful question:

**"Where is abnormal consumption happening, how significant is it, and what should we investigate?"**

By combining IoT telemetry, meter data, analytics, anomaly detection, reconciliation, and intelligent recommendations, FlowSense provides a foundation for smarter facility resource management.

---

## 👨‍💻 Project

**FlowSense**

IoT-Based Energy & Water Monitoring and Loss Detection Platform

GitHub: [https://github.com/ayush2459/flowsense](https://github.com/ayush2459/flowsense)

---

## 📜 License

This project is currently intended for development, demonstration, and educational purposes.
