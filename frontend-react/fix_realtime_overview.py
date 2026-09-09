from pathlib import Path

p = Path("src/RealtimeOverview.jsx")
s = p.read_text(encoding="utf-8")

s = s.replace(
'''  const [historyWater, setHistoryWater] = useState([]);\n  const [lastTick, setLastTick] = useState(null);''',
'''  const [historyWater, setHistoryWater] = useState([]);\n  const [historyRange, setHistoryRange] = useState(24);\n  const [lastTick, setLastTick] = useState(null);''')

old = '''  useEffect(() => {\n    if (!selected) {\n      setHistoryEnergy([]);\n      setHistoryWater([]);\n      return;\n    }\n    let alive = true;\n    api.energy(selected, 24).then(rows => { if (alive) setHistoryEnergy(rows); }).catch(() => {});\n    api.water(selected, 24).then(rows => { if (alive) setHistoryWater(rows); }).catch(() => {});\n    return () => { alive = false; };\n  }, [selected]);'''
new = '''  useEffect(() => {\n    let alive = true;\n    const energyRequest = selected ? api.energy(selected, historyRange) : api.portfolioEnergy(historyRange);\n    const waterRequest = selected ? api.water(selected, historyRange) : api.portfolioWater(historyRange);\n    Promise.all([energyRequest, waterRequest]).then(([energyRows, waterRows]) => {\n      if (!alive) return;\n      setHistoryEnergy(Array.isArray(energyRows) ? energyRows : []);\n      setHistoryWater(Array.isArray(waterRows) ? waterRows : []);\n    }).catch(() => {\n      if (alive) { setHistoryEnergy([]); setHistoryWater([]); }\n    });\n    return () => { alive = false; };\n  }, [selected, historyRange]);'''
if old not in s:
    raise SystemExit("history block not found")
s = s.replace(old, new)

old = '''  const energyScore = selectedLive ? clamp(92 - (selectedLive.anomaly_type === "high_energy" ? 20 : 0) - (selectedLive.status === "critical" ? 8 : 0), 45, 95) : 81;\n  const waterLoss = selectedLive?.leak_detected || selectedLive?.anomaly_type === "water_leak" ? waterTotal * 0.12 : waterTotal * 0.05;\n  const waterUsed = Math.max(0, waterTotal - waterLoss);\n  const waterScore = selectedLive ? clamp(91 - (selectedLive.anomaly_type === "water_leak" ? 25 : 0) - (selectedLive.status === "critical" ? 7 : 0), 40, 95) : 76;'''
new = '''  const energyScoreFor = (x) => clamp(92 - (x?.anomaly_type === "high_energy" ? 20 : 0) - (x?.status === "critical" ? 8 : 0) - (x?.status === "attention" ? 5 : 0), 45, 95);\n  const waterScoreFor = (x) => clamp(91 - (x?.anomaly_type === "water_leak" ? 25 : 0) - (x?.status === "critical" ? 7 : 0) - (x?.status === "attention" ? 4 : 0), 40, 95);\n  const energyScore = selectedLive ? energyScoreFor(selectedLive) : liveValues.length ? liveValues.reduce((sum, x) => sum + energyScoreFor(x), 0) / liveValues.length : 81;\n  const waterLoss = selectedLive?.leak_detected || selectedLive?.anomaly_type === "water_leak" ? waterTotal * 0.12 : waterTotal * 0.05;\n  const waterUsed = Math.max(0, waterTotal - waterLoss);\n  const waterScore = selectedLive ? waterScoreFor(selectedLive) : liveValues.length ? liveValues.reduce((sum, x) => sum + waterScoreFor(x), 0) / liveValues.length : 76;'''
if old not in s:
    raise SystemExit("score block not found")
s = s.replace(old, new)

old = '''<select value={selected || ""} onChange={e => setSelected(e.target.value)}><option value="">All Facilities</option>{facilities.map(f => <option key={f.facility_code} value={f.facility_code}>{f.facility_name}</option>)}</select><button>Today ▾</button><button onClick={onRefresh}><Activity/></button>'''
new = '''<select value={selected || ""} onChange={e => setSelected(e.target.value)}><option value="">All Facilities</option>{facilities.map(f => <option key={f.facility_code} value={f.facility_code}>{f.facility_name}</option>)}</select><select value={historyRange} onChange={e => setHistoryRange(Number(e.target.value))}><option value={24}>Last 24 Hours</option><option value={168}>Last 7 Days</option><option value={720}>Last 30 Days</option></select><button onClick={onRefresh}><Activity/></button>'''
if old not in s:
    raise SystemExit("header block not found")
s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
print("RealtimeOverview.jsx patched successfully")
