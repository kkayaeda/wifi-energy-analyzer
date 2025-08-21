// Dark Mode + Toggle Icon
  (function() {
    const body = document.body;
    const toggle = document.getElementById("darkModeToggle");

    const svgOn = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
      class="bi bi-toggle-on toggle-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M5 3a5 5 0 0 0 0 10h6a5 5 0 0 0 0-10zm6 9a4 4 0 1 1 0-8 4 4 0 0 1 0 8"></path></svg>`;
    const svgOff = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
      class="bi bi-toggle-off toggle-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M11 4a4 4 0 0 1 0 8H8a5 5 0 0 0 2-4 5 5 0 0 0-2-4zm-6 8a4 4 0 1 1 0-8 4 4 0 0 1 0 8M0 8a5 5 0 0 0 5 5h6a5 5 0 0 0 0-10H5a5 5 0 0 0-5 5"></path></svg>`;

    function setIcon(isDark) {
      toggle.innerHTML = isDark ? svgOn : svgOff;
    }

    const savedDark = localStorage.getItem("darkMode") === "enabled";
    body.classList.toggle("dark-mode", savedDark);
    setIcon(savedDark);

    toggle.addEventListener("click", function () {
      const makeDark = !body.classList.contains("dark-mode");
      body.classList.toggle("dark-mode", makeDark);
      localStorage.setItem("darkMode", makeDark ? "enabled" : "disabled");
      setIcon(makeDark);
    });
  })();

  // API & Table Logic
  const API_BASE = 'http://127.0.0.1:5000';
  const deviceBody = document.getElementById('deviceBody');
  const statusEl = document.getElementById('status');
  const scanBtn = document.getElementById('scanBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const deviceCountEl = document.getElementById('deviceCount');
  const lastUpdatedEl = document.getElementById('lastUpdated');

  const totalEnergyEl = document.getElementById('totalEnergy');
  const totalCostEl = document.getElementById('totalCost');
  const totalCarbonEl = document.getElementById('totalCarbon');

  const COST_PER_KWH = 2.6;
  const CO2_PER_KWH = 0.475;

  function setStatus(text){ statusEl.textContent = text; }

  function updateSummary(list){
    let totalEnergy = 0;
    list.forEach(d => {
      const val = parseFloat(d.energy);
      if(!isNaN(val)) totalEnergy += val;
    });

    if(totalEnergy > 0){
      totalEnergyEl.textContent = totalEnergy.toFixed(2);
      totalCostEl.textContent = (totalEnergy * COST_PER_KWH).toFixed(2);
      totalCarbonEl.textContent = (totalEnergy * CO2_PER_KWH).toFixed(2);
    } else {
      totalEnergyEl.textContent = "-";
      totalCostEl.textContent = "-";
      totalCarbonEl.textContent = "-";
    }
  }

  function renderRows(list, last_updated){
    deviceBody.innerHTML = '';
    if(!list || list.length === 0){
      deviceBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No devices found</td></tr>';
      deviceCountEl.textContent = "Devices connected: 0";
      lastUpdatedEl.textContent = "Last updated: -";
      updateSummary([]);
      return;
    }

    list.forEach((d, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${i+1}</td>
        <td>${d.ip || '-'}</td>
        <td>${d.mac || '-'}</td>
        <td>${d.hostname || '-'}</td>
        <td>${d.vendor || '-'}</td>
        <td>${d.connectiontime || '-'}</td>
        <td>${d.energy || '-'}</td>
      `;
      deviceBody.appendChild(tr);
    });

    deviceCountEl.textContent = `Devices connected: ${list.length}`;
    lastUpdatedEl.textContent = `Last updated: ${last_updated || "-"}`;
    updateSummary(list);
  }

  async function fetchDevices(){
    setStatus('Loading...');
    try {
      const res = await fetch(`${API_BASE}/devices`);
      const data = await res.json();
      renderRows(data.devices, data.last_updated);
      setStatus('Updated');
    } catch (err) {
      setStatus('Connection Error');
    }
  }

  async function startScan(){
    setStatus('Scanning...');
    scanBtn.disabled = true;
    try {
      await fetch(`${API_BASE}/scan`, { method: 'POST' });
      await fetchDevices();
    } catch (err) {
      setStatus('Scanning failed to start');
    } finally {
      scanBtn.disabled = false;
    }
  }

  scanBtn.addEventListener('click', startScan);
  refreshBtn.addEventListener('click', fetchDevices);
  setInterval(fetchDevices, 10000);
  setInterval(startScan, 30000);