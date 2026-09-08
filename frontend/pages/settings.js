let settingsTab = 'General';
const settingsToggles = { email: true, inapp: true, sms: true, daily: false };

async function renderSettingsPage(main) {
  const tabs = ['General', 'Facilities', 'Sensors', 'Alerts', 'Users', 'Integrations'];

  main.innerHTML = `
    ${pageHeader('Settings', 'Manage system preferences, alerts and integrations', '')}

    <div class="tab-row">
      ${tabs.map(t => `<div class="tab ${t === settingsTab ? 'active' : ''}" data-tab="${t}">${t}</div>`).join('')}
    </div>

    ${settingsTab === 'General' ? `
      <div class="grid grid-2">
        <div class="card">
          <div class="card-title">General Settings</div>
          <div class="field-group">
            <label class="field-label">Time Zone</label>
            <select class="select" style="width:100%;"><option>(UTC+05:30) Asia/Kolkata</option></select>
          </div>
          <div class="field-group">
            <label class="field-label">Date Format</label>
            <select class="select" style="width:100%;"><option>DD-MM-YYYY</option></select>
          </div>
          <div class="field-group">
            <label class="field-label">Currency</label>
            <select class="select" style="width:100%;"><option>INR (\u20B9)</option></select>
          </div>
          <div class="field-group">
            <label class="field-label">Units</label>
            <select class="select" style="width:100%;"><option>Metric (kWh, L, °C, etc.)</option></select>
          </div>
        </div>
        <div class="card">
          <div class="card-title">Notification Preferences</div>
          ${toggleRow('Email Notifications', 'email')}
          ${toggleRow('In-app Notifications', 'inapp')}
          ${toggleRow('Critical Alerts (SMS)', 'sms')}
          ${toggleRow('Daily Summary Email', 'daily')}
        </div>
      </div>
      <div style="display:flex; justify-content:flex-end; margin-top:16px;">
        <button style="background:var(--accent-blue); color:white; border:none; padding:10px 22px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer;">Save Changes</button>
      </div>
    ` : `<div class="card"><div class="empty-state">${settingsTab} settings — coming soon in this prototype.</div></div>`}
  `;

  main.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => { settingsTab = t.dataset.tab; renderSettingsPage(main); });
  });

  main.querySelectorAll('.switch').forEach(sw => {
    sw.addEventListener('click', () => {
      const key = sw.dataset.key;
      settingsToggles[key] = !settingsToggles[key];
      renderSettingsPage(main);
    });
  });
}

function toggleRow(label, key) {
  const on = settingsToggles[key];
  return `
    <div class="toggle-row">
      <span>${label}</span>
      <div class="switch ${on ? 'on' : ''}" data-key="${key}"><div class="switch-knob"></div></div>
    </div>`;
}
