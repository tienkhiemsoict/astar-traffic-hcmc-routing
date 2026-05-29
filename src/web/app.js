const cfg = {
    MAP: {
        MIN_LAT: 10.7,
        MAX_LAT: 10.85,
        MIN_LON: 106.6,
        MAX_LON: 106.8,
        CENTER: [10.776, 106.7],
        ZOOM: 15,
        MIN_ZOOM: 14,
        MAX_ZOOM: 18
    },
    API: {
        BASE: 'http://127.0.0.1:8000',
        SNAP: '/api/snap-node',
        ROUTE: '/api/route',
        COMPARE: '/api/compare',
        TRAFFIC: '/api/traffic-geojson'
    },
    ICON: {
        S: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        E: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
        SHADOW: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png'
    },
    SLOT: 16
};

const BOUNDS = L.latLngBounds(
    [cfg.MAP.MIN_LAT, cfg.MAP.MIN_LON],
    [cfg.MAP.MAX_LAT, cfg.MAP.MAX_LON]
);

class State {
    constructor() {
        this.map = null;
        this.trafficLayer = null;
        this.trafficAbort = null;
        this.cache = {};
        this.markers = { s: null, e: null };
        this.route = null;
        this.mode = null;
        this.chart = null;
    }

    resetAll() {
        this.clearMarkers();
        this.clearRoute();
        this.mode = null;
    }

    clearMarkers() {
        ['s', 'e'].forEach((k) => {
            if (this.markers[k]) {
                this.map.removeLayer(this.markers[k]);
                this.markers[k] = null;
            }
        });
    }

    clearRoute() {
        if (this.route) {
            this.map.removeLayer(this.route);
            this.route = null;
        }
    }

    hasRoute() {
        return this.markers.s && this.markers.e;
    }
}

const state = new State();

function initMap() {
    state.map = L.map('map', {
        center: cfg.MAP.CENTER,
        zoom: cfg.MAP.ZOOM,
        minZoom: cfg.MAP.MIN_ZOOM,
        maxZoom: cfg.MAP.MAX_ZOOM,
        maxBounds: BOUNDS,
        maxBoundsViscosity: 1,
        renderer: L.canvas()
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(state.map);

    state.trafficLayer = L.geoJSON(null, {
        style: (f) => ({
            color: f.properties.color,
            weight: f.properties.weight,
            opacity: 0.6,
            lineJoin: 'round'
        }),
        interactive: false
    }).addTo(state.map);

    setTimeout(() => state.map.invalidateSize(), 300);
}

function icon(type) {
    return L.icon({
        iconUrl: cfg.ICON[type === 's' ? 'S' : 'E'],
        shadowUrl: cfg.ICON.SHADOW,
        iconSize: [25, 41],
        iconAnchor: [12, 41]
    });
}

function setMode(mode) {
    if (mode === 's') state.resetAll();
    state.mode = mode;
    updateStatus(mode === 's' ? 'Chọn điểm ĐẦU...' : 'Chọn điểm CUỐI...', '#3498db');
}

function resetMap() {
    state.map.setView(cfg.MAP.CENTER, cfg.MAP.ZOOM);
    state.resetAll();
    updateStatus('Sẵn sàng', '#7f8c8d');
}

async function snap(lat, lng) {
    const res = await fetch(`${cfg.API.BASE}${cfg.API.SNAP}?lat=${lat}&lng=${lng}`);
    return await res.json();
}

function placeMarker(type, node) {
    const key = type === 'start' ? 's' : 'e';
    if (state.markers[key]) state.map.removeLayer(state.markers[key]);

    const marker = L.marker([node.lat, node.lng], { icon: icon(key), draggable: true }).addTo(state.map);
    marker.nodeId = node.id;
    state.markers[key] = marker;
}

async function onMapClick(e) {
    if (!state.mode) return;
    if (!BOUNDS.contains(e.latlng)) {
        alert('Vui lòng chọn trong khung đỏ!');
        return;
    }

    const node = await snap(e.latlng.lat, e.latlng.lng);
    placeMarker(state.mode, node);
    state.mode = null;
    updateStatus('Đã chọn điểm', '#2ecc71');
}

async function calculateRoute() {
    if (!state.hasRoute()) {
        alert('Chọn đủ 2 điểm!');
        return;
    }

    state.clearRoute();
    if (state.trafficAbort) state.trafficAbort.abort();

    const slot = +document.getElementById('time-slider').value;
    const res = await fetch(`${cfg.API.BASE}${cfg.API.ROUTE}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_id: state.markers.s.nodeId,
            end_id: state.markers.e.nodeId,
            slot
        })
    });

    const data = await res.json();
    if (!data.path_coords?.length) return;

    state.route = L.polyline(data.path_coords, { color: '#1632cf', weight: 8, opacity: 0.95 }).addTo(state.map);
    state.map.fitBounds(state.route.getBounds(), { padding: [50, 50] });
}

async function compareAlgorithms() {
    if (!state.hasRoute()) {
        alert('Vui lòng chọn đầy đủ điểm ĐẦU và điểm CUỐI trên bản đồ!');
        return;
    }

    updateStatus('Đang so sánh...', '#f39c12');
    const slot = +document.getElementById('time-slider').value;
    const res = await fetch(`${cfg.API.BASE}${cfg.API.COMPARE}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_id: state.markers.s.nodeId,
            end_id: state.markers.e.nodeId,
            slot
        })
    });

    const data = await res.json();
    renderComparison(data);
    updateStatus('Đã hiển thị kết quả', '#2ecc71');
}

function formatTime(slot) {
    const h = Math.floor((slot - 1) / 2);
    return `${String(h).padStart(2, '0')}:${slot % 2 ? '30' : '00'}`;
}

async function updateTraffic(slot) {
    if (state.trafficAbort) state.trafficAbort.abort();
    if (state.cache[slot]) {
        state.trafficLayer.clearLayers();
        state.trafficLayer.addData(state.cache[slot]);
        return;
    }

    try {
        state.trafficAbort = new AbortController();
        const res = await fetch(`${cfg.API.BASE}${cfg.API.TRAFFIC}?slot=${slot}`, { signal: state.trafficAbort.signal });
        const data = await res.json();
        state.cache[slot] = data;
        state.trafficLayer.clearLayers();
        state.trafficLayer.addData(data);
    } catch (err) {
        if (err.name !== 'AbortError') throw err;
    }
}

function updateTimeDisplay(value) {
    document.getElementById('time-val').innerText = formatTime(+value);
    updateTraffic(+value);
}

function renderComparison(data) {
    document.getElementById('comp-body').innerHTML = data
        .map((i) => `<tr><td><b>${i.algo}</b></td><td>${i.dist != null ? (i.dist / 1000).toFixed(2) + ' km' : '-'}</td><td>${i.visited.toLocaleString()}</td><td>${i.time_ms} ms</td></tr>`)
        .join('');

    const ctx = document.getElementById('algoChart').getContext('2d');
    if (state.chart) state.chart.destroy();

    state.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map((i) => i.algo),
            datasets: [
                {
                    label: 'Node duyệt',
                    data: data.map((i) => i.visited),
                    backgroundColor: 'rgba(52,152,219,.7)',
                    borderColor: 'rgba(52,152,219,1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: 'Thời gian (ms)',
                    data: data.map((i) => i.time_ms),
                    backgroundColor: 'rgba(230,126,34,.7)',
                    borderColor: 'rgba(230,126,34,1)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { type: 'linear', position: 'left', title: { display: true, text: 'Node' } },
                y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'ms' } }
            },
            plugins: { legend: { position: 'top' } }
        }
    });

    showModal('compare-modal');
}

function updateStatus(text, color = '#7f8c8d') {
    const el = document.getElementById('status');
    el.innerText = text;
    el.style.color = color;
}

function showModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function closeModal() {
    document.getElementById('compare-modal').style.display = 'none';
}

function setupListeners() {
    state.map.on('click', onMapClick);
    window.onclick = (e) => { if (e.target === document.getElementById('compare-modal')) closeModal(); };
}

async function preloadTraffic() {
    const res = await fetch(`${cfg.API.BASE}${cfg.API.TRAFFIC}?slot=${cfg.SLOT}`);
    const data = await res.json();
    state.cache[cfg.SLOT] = data;
    updateTraffic(cfg.SLOT);
}

function init() {
    initMap();
    setupListeners();
    preloadTraffic();
}

document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();

window.setMode = setMode;
window.resetMap = resetMap;
window.runRouting = calculateRoute;
window.compareAlgos = compareAlgorithms;
window.updateTime = updateTimeDisplay;
window.closeModal = closeModal;