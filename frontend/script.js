const API_BASE = "http://127.0.0.1:5000";

// Map State
let mapInstance = null;
let routeLine    = null;
let startMarker  = null;
let destMarker   = null;

// Feedback State
let currentStart    = "";
let currentDest     = "";
let currentScoreStr = "";
let currentRating   = null;

/* ─────────────────────────────────────
   STEP NAVIGATION
───────────────────────────────────── */
function goToStep(stepNumber) {
  document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
  document.getElementById(`step-${stepNumber}`).classList.add('active');

  if (stepNumber === 2 && mapInstance) {
    setTimeout(() => mapInstance.invalidateSize(), 150);
  }

  if (stepNumber === 1) {
    resetUI();
    currentRating = null;
    document.querySelectorAll('.btn-feedback').forEach(btn => btn.classList.remove('selected'));
    document.getElementById('feedbackComment').value = "";
    document.getElementById('submitFeedbackBtn').disabled = true;
    document.getElementById('start').value = "";
    document.getElementById('destination').value = "";
  }
}

/* ─────────────────────────────────────
   ANALYZE ROUTE
───────────────────────────────────── */
async function analyzeRoute() {
  const start       = document.getElementById("start").value.trim();
  const destination = document.getElementById("destination").value.trim();
  const btn         = document.getElementById("analyzeBtn");
  const loader      = document.getElementById("loader");

  if (!start || !destination) {
    showError("Please enter both an origin and a destination.");
    return;
  }

  resetUI();
  btn.disabled = true;
  goToStep(2);
  loader.classList.add("active");

  try {
    const response = await fetch(`${API_BASE}/predict`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ start_location: start, destination })
    });

    const data = await response.json();

    if (data.error) {
      goToStep(1);
      showError(data.error);
      return;
    }

    renderResult(data, start, destination);

  } catch (err) {
    console.error("Analyze Route Error:", err);
    goToStep(1);
    showError("Could not reach the server. Please check your connection.");
  } finally {
    btn.disabled = false;
    loader.classList.remove("active");
  }
}

/* ─────────────────────────────────────
   RENDER RESULT
───────────────────────────────────── */
function renderResult(data, start, destination) {
  const score = data.safest_route_score; // 1–3

  let label, cls, description;

  if (score >= 2.5) {
    label       = "Safe";
    cls         = "safe";
    description = "This corridor is well-lit and monitored, with low crime density and close police presence.";
  } else if (score >= 1.5) {
    label       = "Moderate";
    cls         = "moderate";
    description = "Exercise normal caution. Some segments have limited surveillance. Prefer daytime travel.";
  } else {
    label       = "Unsafe";
    cls         = "unsafe";
    description = "This route passes through elevated-risk areas. Consider an alternative or travel with company.";
  }

  // Route strip
  document.getElementById("resFrom").textContent = start;
  document.getElementById("resTo").textContent   = destination;

  // Verdict
  const box = document.getElementById("verdictBox");
  box.className = `verdict ${cls}`;
  document.getElementById("verdictTitle").textContent    = label;
  document.getElementById("verdictScoreNum").textContent = score.toFixed(2);
  document.getElementById("verdictMeta").innerHTML =
    `<span>Routes analysed:</span> ${data.routes_checked}&nbsp;&nbsp;·&nbsp;&nbsp;` +
    `<span>Raw score:</span> ${score.toFixed(2)} / 3.00<br>${description}`;

  // Score bar
  const fill = document.getElementById("scoreBarFill");
  fill.className = `score-bar-fill ${cls}`;
  const pct = ((score - 1) / 2) * 100;
  setTimeout(() => { fill.style.width = `${Math.max(4, pct)}%`; }, 100);

  // Save for feedback
  currentStart    = start;
  currentDest     = destination;
  currentScoreStr = score.toFixed(2);

  // Draw map
  drawMap(data.safest_route);

  // Show result
  document.getElementById("result").classList.add("active");
}

/* ─────────────────────────────────────
   DRAW LEAFLET MAP
───────────────────────────────────── */
function drawMap(routeCoords) {
  if (!mapInstance) {
    mapInstance = L.map('map', { zoomControl: true }).setView([8.5241, 76.9366], 13);

    // Soft tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 18
    }).addTo(mapInstance);
  }

  // Clear previous layers
  if (routeLine)   mapInstance.removeLayer(routeLine);
  if (startMarker) mapInstance.removeLayer(startMarker);
  if (destMarker)  mapInstance.removeLayer(destMarker);

  // Draw teal route
  routeLine = L.polyline(routeCoords, {
    color:  '#1ABC9C',
    weight: 5,
    opacity: 0.9,
    lineCap: 'round',
    lineJoin: 'round'
  }).addTo(mapInstance);

  // Custom icons
  const makeIcon = (color) => L.divIcon({
    className: '',
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${color};border:2.5px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.25);
    "></div>`,
    iconSize:   [14, 14],
    iconAnchor: [7, 7]
  });

  startMarker = L.marker(routeCoords[0], { icon: makeIcon('#6C3483') })
    .addTo(mapInstance)
    .bindPopup(`<b style="font-family:DM Sans,sans-serif">Start</b><br>${currentStart}`);

  destMarker = L.marker(routeCoords[routeCoords.length - 1], { icon: makeIcon('#1ABC9C') })
    .addTo(mapInstance)
    .bindPopup(`<b style="font-family:DM Sans,sans-serif">Destination</b><br>${currentDest}`);

  mapInstance.fitBounds(routeLine.getBounds(), { padding: [28, 28] });
  setTimeout(() => mapInstance.invalidateSize(), 60);
}

/* ─────────────────────────────────────
   FEEDBACK
───────────────────────────────────── */
function selectRating(rating) {
  currentRating = rating;
  document.querySelectorAll('.btn-feedback').forEach(btn => btn.classList.remove('selected'));

  if (rating === 'safe') {
    document.getElementById('btnSafe').classList.add('selected');
  } else {
    document.getElementById('btnUnsafe').classList.add('selected');
  }

  document.getElementById('submitFeedbackBtn').disabled = false;
}

async function submitFeedback() {
  if (!currentRating) return;

  const btn     = document.getElementById("submitFeedbackBtn");
  const loader  = document.getElementById("feedbackLoader");
  const comment = document.getElementById("feedbackComment").value.trim();

  btn.style.display = 'none';
  loader.classList.add('active');

  try {
    await fetch(`${API_BASE}/feedback`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start:           currentStart,
        destination:     currentDest,
        predicted_score: currentScoreStr,
        user_rating:     currentRating,
        comment:         comment
      })
    });

    loader.classList.remove('active');
    btn.style.display  = 'flex';
    btn.querySelector('span').textContent = "Feedback Saved — Thank You!";
    btn.disabled = true;

  } catch (err) {
    console.error(err);
    loader.classList.remove('active');
    btn.style.display  = 'flex';
    btn.querySelector('span').textContent = "Error — Please Retry";
  }
}

/* ─────────────────────────────────────
   HELPERS
───────────────────────────────────── */
function showError(msg) {
  const box = document.getElementById("errorBox");
  box.textContent = "⚠  " + msg;
  box.classList.add("active");
}

function resetUI() {
  document.getElementById("result").classList.remove("active");
  document.getElementById("errorBox").classList.remove("active");
  document.getElementById("scoreBarFill").style.width = "0%";
}

// Enter key shortcut
document.addEventListener("keydown", e => {
  if (e.key === "Enter") analyzeRoute();
});