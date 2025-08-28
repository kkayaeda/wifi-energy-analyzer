// =====================
// Dark Mode + Toggle Icon
// =====================
document.addEventListener("DOMContentLoaded", function() {
    const body = document.body;
    const toggle = document.getElementById("darkModeToggle");

    const svgOn = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
        class="bi bi-toggle-on toggle-icon" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M5 3a5 5 0 0 0 0 10h6a5 5 0 0 0 0-10zm6 9a4 4 0 1 1 0-8 4 4 0 0 1 0 8"></path>
    </svg>`;
    const svgOff = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
        class="bi bi-toggle-off toggle-icon" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M11 4a4 4 0 0 1 0 8H8a5 5 0 0 0 2-4 5 5 0 0 0-2-4zm-6 8a4 4 0 1 1 0-8 4 4 0 0 1 0 8M0 8a5 5 0 0 0 5 5h6a5 5 0 0 0 0-10H5a5 5 0 0 0-5 5"></path>
    </svg>`;

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

        // Chart renklerini dark/light moda göre ayarla
        if (window.energyChart) {
            const color = makeDark ? '#f1f1f1' : '#212529';
            window.energyChart.options.plugins.legend.labels.color = color;
            window.energyChart.options.scales.x.title.color = color;
            window.energyChart.options.scales.x.ticks.color = color;
            window.energyChart.options.scales.y.title.color = color;
            window.energyChart.options.scales.y.ticks.color = color;
            window.energyChart.update();
        }
    });
});

// =====================
// API & Table Logic
// =====================
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

function setStatus(text){ if(statusEl) statusEl.textContent = text; }

function updateSummary(list){
  let totalEnergy = 0;
  list.forEach(d => {
    const val = parseFloat(d.energy);
    if(!isNaN(val)) totalEnergy += val;
  });

  if(totalEnergyEl) totalEnergyEl.textContent = totalEnergy > 0 ? totalEnergy.toFixed(2) : "-";
  if(totalCostEl) totalCostEl.textContent = totalEnergy > 0 ? (totalEnergy*COST_PER_KWH).toFixed(2) : "-";
  if(totalCarbonEl) totalCarbonEl.textContent = totalEnergy > 0 ? (totalEnergy*CO2_PER_KWH).toFixed(2) : "-";
}

function renderRows(list, last_updated){
  if(!deviceBody) return;
  deviceBody.innerHTML = '';
  if(!list || list.length===0){
    deviceBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No devices found</td></tr>';
    if(deviceCountEl) deviceCountEl.textContent = "Devices connected: 0";
    if(lastUpdatedEl) lastUpdatedEl.textContent = "Last updated: -";
    updateSummary([]);
    return;
  }

  list.forEach((d,i)=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${i+1}</td>
      <td>${d.ip||'-'}</td>
      <td>${d.mac||'-'}</td>
      <td>${d.hostname||'-'}</td>
      <td>${d.vendor||'-'}</td>
      <td>${d.connectiontime||'-'}</td>
      <td>${d.energy||'-'}</td>
    `;
    deviceBody.appendChild(tr);
  });

  if(deviceCountEl) deviceCountEl.textContent = `Devices connected: ${list.length}`;
  if(lastUpdatedEl) lastUpdatedEl.textContent = `Last updated: ${last_updated||"-"}`;
  updateSummary(list);
}

async function fetchDevices(){
  setStatus('Loading...');
  try {
    const res = await fetch(`${API_BASE}/devices`);
    const data = await res.json();
    renderRows(data.devices||[], data.last_updated);
    setStatus('Updated');
  } catch(err){
    setStatus('Connection Error');
  }
}

async function startScan(){
  if(!scanBtn) return;
  setStatus('Scanning...');
  scanBtn.disabled = true;
  try{
    const scanRes = await fetch(`${API_BASE}/scan`, {method:'POST'});
    if(!scanRes.ok) throw new Error('Scan failed');
    const data = await scanRes.json();
    renderRows(data.devices||[], data.last_updated);
    await fetchDevices();
    setStatus('Scan Completed');
  } catch(err){
    setStatus('Scanning failed');
  } finally{
    scanBtn.disabled = false;
  }
}

document.getElementById('downloadBtn')?.addEventListener('click', async () => {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF('p', 'pt', 'a4');

  const table = document.getElementById('myTable');
  if(!table) return;
  const canvas = await html2canvas(table, { scale: 2 });
  const imgData = canvas.toDataURL('image/png');

  const imgProps = doc.getImageProperties(imgData);
  const pdfWidth = doc.internal.pageSize.getWidth();
  const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

  doc.addImage(imgData, 'PNG', 0, 20, pdfWidth, pdfHeight);
  doc.save('table.pdf');
});

// =====================
// Chart.js Energy Chart
// =====================
document.addEventListener("DOMContentLoaded", async () => {
    const ctx = document.getElementById('energyChart')?.getContext('2d');
    if(!ctx) return;

    window.energyChart = new Chart(ctx, {
        type:'line',
        data:{
            labels:[],
            datasets:[
                {label:'Total Energy (kWh)', data:[], borderColor:'rgba(75,192,192,1)', backgroundColor:'rgba(75,192,192,0.2)', tension:0.3, fill:true},
                {label:'Cost (₺)', data:[], borderColor:'rgba(255,99,132,1)', backgroundColor:'rgba(255,99,132,0.2)', tension:0.3, fill:true},
                {label:'CO2 Emissions (kg)', data:[], borderColor:'rgba(255,206,86,1)', backgroundColor:'rgba(255,206,86,0.2)', tension:0.3, fill:true}
            ]
        },
        options:{
            responsive:false,
            maintainAspectRatio:false,
            plugins:{legend:{position:'top', labels:{color:'#212529'}}, tooltip:{mode:'index', intersect:false}},
            scales:{
                x:{title:{display:true, text:'Time (min)', color:'#212529'}, ticks:{color:'#212529'}},
                y:{title:{display:true, text:'Value', color:'#212529'}, beginAtZero:true, ticks:{color:'#212529'}}
            }
        }
    });

    async function updateEnergyChart(){
        try{
            const res = await fetch(`${API_BASE}/energy_data`);
            const data = await res.json();

            window.energyChart.data.labels = data.labels||[];
            window.energyChart.data.datasets[0].data = data.energy||[];
            window.energyChart.data.datasets[1].data = data.cost||[];
            window.energyChart.data.datasets[2].data = data.co2||[];
            window.energyChart.update();
        } catch(err){
            console.error('Chart update error:', err);
        }
    }


    updateEnergyChart();
    setInterval(updateEnergyChart, 60000);
});

const shareBtn = document.getElementById('shareBtn');
shareBtn.addEventListener('click', () => {
  shareBtn.classList.toggle('active');
});


// =====================
// Intervals & Event Listeners
// =====================
if(scanBtn) scanBtn.addEventListener('click', startScan);
if(refreshBtn) refreshBtn.addEventListener('click', fetchDevices);

setInterval(fetchDevices, 10000);
setInterval(startScan, 30000);
