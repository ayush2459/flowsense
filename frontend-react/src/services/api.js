const BASE="http://localhost:8000";
const get=async p=>{const r=await fetch(BASE+p);if(!r.ok)throw Error(`${r.status} ${p}`);return r.json()};
export const api={
  facilities:()=>get("/api/facilities"),
  anomalies:(l=50)=>get(`/api/anomalies/recent?limit=${l}`),
  summary:c=>get(`/api/facilities/${c}/summary`),
  energy:(c,h=24)=>get(`/api/facilities/${c}/energy?hours=${h}`),
  water:(c,h=24)=>get(`/api/facilities/${c}/water?hours=${h}`),
  portfolioEnergy:(h=24)=>get(`/api/portfolio/energy?hours=${h}`),
  portfolioWater:(h=24)=>get(`/api/portfolio/water?hours=${h}`),
  reconciliation:(c,l=100)=>get(`/api/facilities/${c}/reconciliation?limit=${l}`)
};
