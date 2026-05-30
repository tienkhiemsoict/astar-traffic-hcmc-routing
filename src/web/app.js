const CONFIG = {
    MAP: {
        MIN_LAT: 10.70,
        MAX_LAT: 10.85,
        MIN_LON: 106.60,
        MAX_LON: 106.80,
        CENTER: [10.776, 106.700],
        INITIAL_ZOOM: 15,
        MIN_ZOOM: 14,
        MAX_ZOOM: 18
    },
    API: {
        BASE_URL: 'http://127.0.0.1:8000',
        ENDPOINTS: {
            SNAP_NODE: '/api/snap-node',
            ROUTE: '/api/route',
            COMPARE: '/api/compare',
            TRAFFIC: '/api/traffic-geojson'
        }
    },
    ICONS: {
        START: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        END: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
        SHADOW: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png'
    },
    TIMING: {
        TRAFFIC_UPDATE_DEBOUNCE: 500,
        DEFAULT_SLOT: 16
    }
};

// ========================================
// APPLICATION STATE
// ========================================
class AppState {
    constructor() {
        this.map = null;
        this.trafficLayer = null;
        this.trafficTimer = null;
        this.trafficAbortController = null;
        this.trafficCache = {};
        this.markers = {
            start: null,
            end: null
        };
        this.routeLine = null;
        this.selectingMode = null;
        this.chart = null;
    }

    reset() {
        this.clearMarkers();
        this.clearRoute();
        this.selectingMode = null;
    }

    clearMarkers() {
        if (this.markers.start) {
            this.map.removeLayer(this.markers.start);
            this.markers.start = null;
        }
        if (this.markers.end) {
            this.map.removeLayer(this.markers.end);
            this.markers.end = null;
        }
    }

    clearRoute() {
        if (this.routeLine) {
            this.map.removeLayer(this.routeLine);
            this.routeLine = null;
        }
    }

    hasValidRoute() {
        return this.markers.start && this.markers.end;
    }
}

const appState = new AppState();

// ========================================
// MAP INITIALIZATION
// ========================================
function initializeMap() {
    const bounds = L.latLngBounds(
        [CONFIG.MAP.MIN_LAT, CONFIG.MAP.MIN_LON],
        [CONFIG.MAP.MAX_LAT, CONFIG.MAP.MAX_LON]
    );

    appState.map = L.map('map', {
        center: CONFIG.MAP.CENTER,
        zoom: CONFIG.MAP.INITIAL_ZOOM,
        minZoom: CONFIG.MAP.MIN_ZOOM,
        maxZoom: CONFIG.MAP.MAX_ZOOM,
        maxBounds: bounds,
        maxBoundsViscosity: 1.0,
        renderer: L.canvas()
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(appState.map);

    setupTrafficLayer();
    
    setTimeout(() => appState.map.invalidateSize(), 300);
}

function setupTrafficLayer() {
    appState.trafficLayer = L.geoJSON(null, {
        style: (feature) => ({
            color: feature.properties.color,
            weight: feature.properties.weight,
            opacity: 0.6,
            lineJoin: 'round'
        }),
        interactive: false
    }).addTo(appState.map);
}

// ========================================
// MARKER MANAGEMENT
// ========================================
function createMarkerIcon(type) {
    return L.icon({
        iconUrl: CONFIG.ICONS[type.toUpperCase()],
        shadowUrl: CONFIG.ICONS.SHADOW,
        iconSize: [25, 41],
        iconAnchor: [12, 41]
    });
}

function setSelectionMode(mode) {
    if (mode === 'start') {
        appState.reset();
        updateStatus('Đang chọn điểm ĐẦU...', '#3498db');
    } else {
        updateStatus('Đang chọn điểm CUỐI...', '#3498db');
    }
    appState.selectingMode = mode;
}

function resetMap() {
    appState.map.setView(CONFIG.MAP.CENTER, CONFIG.MAP.INITIAL_ZOOM);
    appState.reset();
    updateStatus('Trạng thái: Sẵn sàng', '#7f8c8d');
}


async function handleMapClick(event) {
    if (!appState.selectingMode) return;

    const bounds = L.latLngBounds(
        [CONFIG.MAP.MIN_LAT, CONFIG.MAP.MIN_LON],
        [CONFIG.MAP.MAX_LAT, CONFIG.MAP.MAX_LON]
    );

    if (!bounds.contains(event.latlng)) {
        alert('Vui lòng chọn trong khung đỏ!');
        return;
    }

    try {
        const node = await snapToNode(event.latlng.lat, event.latlng.lng);
        placeMarker(appState.selectingMode, node);
        appState.selectingMode = null;
        updateStatus('Đã ghim vị trí.');
    } catch (error) {
        console.error('Snap node error:', error);
        alert('Lỗi kết nối Server!');
    }
}

function placeMarker(type, node) {
    const markerType = type === 'start' ? 'start' : 'end';
    
    if (appState.markers[markerType]) {
        appState.map.removeLayer(appState.markers[markerType]);
    }

    const marker = L.marker([node.lat, node.lng], {
        icon: createMarkerIcon(markerType),
        draggable: true
    }).addTo(appState.map);

    marker.nodeId = node.id;
    appState.markers[markerType] = marker;
}

// ========================================
// API CALLS
// ========================================
async function snapToNode(lat, lng) {
    const url = `${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.SNAP_NODE}?lat=${lat}&lng=${lng}`;
    const response = await fetch(url);
    
    if (!response.ok) {
        throw new Error('Failed to snap to node');
    }
    
    return await response.json();
}

async function calculateRoute() {
    if (!appState.hasValidRoute()) {
        alert('Chọn đủ 2 điểm!');
        return;
    }

    appState.clearRoute();

    try {
        const slot = parseInt(document.getElementById('time-slider').value);
        const response = await fetch(`${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.ROUTE}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_id: appState.markers.start.nodeId,
                end_id: appState.markers.end.nodeId,
                slot: slot
            })
        });

        const data = await response.json();

        if (data.path_coords && data.path_coords.length > 0) {
            appState.routeLine = L.polyline(data.path_coords, {
                color: '#1632cf',
                weight: 8,
                opacity: 0.95
            }).addTo(appState.map);

            appState.map.fitBounds(appState.routeLine.getBounds(), {
                padding: [50, 50]
            });
        }
    } catch (error) {
        console.error('Route calculation error:', error);
        alert('Lỗi tính toán đường đi!');
    }
}

async function compareAlgorithms() {
    if (!appState.hasValidRoute()) {
        alert('Vui lòng chọn đầy đủ điểm ĐẦU và điểm CUỐI trên bản đồ!');
        return;
    }

    updateStatus(' Đang phân tích và vẽ biểu đồ...', '#f39c12');

    try {
        const slot = parseInt(document.getElementById('time-slider').value);
        const response = await fetch(`${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.COMPARE}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_id: appState.markers.start.nodeId,
                end_id: appState.markers.end.nodeId,
                slot: slot
            })
        });

        if (!response.ok) {
            throw new Error('Server connection failed');
        }

        const data = await response.json();
        displayComparisonResults(data);
        updateStatus(' Đã hiển thị kết quả phân tích.', '#2ecc71');
    } catch (error) {
        console.error('Comparison error:', error);
        updateStatus(` Lỗi: ${error.message}`, '#e74c3c');
    }
}

// ========================================
// TRAFFIC LAYER
// ========================================
function updateTime(slotValue) {
    const slot = parseInt(slotValue);
    const hours = Math.floor((slot - 1) * 0.5);
    const minutes = (slot % 2 === 0) ? '30' : '00';
    
    document.getElementById('time-val').innerText = 
        `${String(hours).padStart(2, '0')}:${minutes}`;

    clearTimeout(appState.trafficTimer);
    appState.trafficTimer = setTimeout(() => {
        updateTrafficLayer(slot);
    }, CONFIG.TIMING.TRAFFIC_UPDATE_DEBOUNCE);
}

async function updateTrafficLayer(slot) {
    try {
        if (appState.trafficAbortController) {
            appState.trafficAbortController.abort();
        }
        
        if (appState.trafficCache[slot]) {
            appState.trafficLayer.clearLayers();
            appState.trafficLayer.addData(appState.trafficCache[slot]);
            return;
        }
        
        appState.trafficAbortController = new AbortController();
        const url = `${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.TRAFFIC}?slot=${slot}`;
        const response = await fetch(url, {
            signal: appState.trafficAbortController.signal
        });
        
        if (!response.ok) return;

        const data = await response.json();
        appState.trafficCache[slot] = data;
        appState.trafficLayer.clearLayers();
        appState.trafficLayer.addData(data);
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Traffic layer update error:', error);
        }
    }
}

// ========================================
// COMPARISON RESULTS
// ========================================
function displayComparisonResults(data) {
    updateComparisonTable(data);
    renderComparisonChart(data);
    showModal('compare-modal');
}

function updateComparisonTable(data) {
    const tbody = document.getElementById('comp-body');
    tbody.innerHTML = data.map(item => `
        <tr>
            <td><b>${item.algo}</b></td>
            <td>${(item.dist / 1000).toFixed(2)} km</td>
            <td>${item.visited.toLocaleString()}</td>
            <td>${item.time_ms} ms</td>
        </tr>
    `).join('');
}

function renderComparisonChart(data) {
    const ctx = document.getElementById('algoChart').getContext('2d');

    if (appState.chart) {
        appState.chart.destroy();
    }

    appState.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.algo),
            datasets: [
                {
                    label: 'Số Node duyệt',
                    data: data.map(item => item.visited),
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: 'Thời gian (ms)',
                    data: data.map(item => item.time_ms),
                    backgroundColor: 'rgba(230, 126, 34, 0.7)',
                    borderColor: 'rgba(230, 126, 34, 1)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Số lượng Node' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Thời gian thực thi (ms)' }
                }
            },
            plugins: {
                legend: { position: 'top' },
                title: { display: false }
            }
        }
    });
}

// ========================================
// UI HELPERS
// ========================================
function updateStatus(message, color = '#7f8c8d') {
    const statusEl = document.getElementById('status');
    statusEl.innerText = message;
    statusEl.style.color = color;
}

function showModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal() {
    document.getElementById('compare-modal').style.display = 'none';
}

// ========================================
// EVENT LISTENERS
// ========================================
function setupEventListeners() {
    appState.map.on('click', handleMapClick);

    window.onclick = (event) => {
        const modal = document.getElementById('compare-modal');
        if (event.target === modal) {
            closeModal();
        }
    };
}

// ========================================
// INITIALIZATION
// ========================================
async function preloadTrafficCache() {
    try {
        const url = `${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.TRAFFIC}?slot=${CONFIG.TIMING.DEFAULT_SLOT}`;
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            appState.trafficCache[CONFIG.TIMING.DEFAULT_SLOT] = data;
            updateTrafficLayer(CONFIG.TIMING.DEFAULT_SLOT);
        }
    } catch (error) {
        console.log(`Failed to preload traffic for default slot`);
    }
}

function init() {
    initializeMap();
    setupEventListeners();
    preloadTrafficCache();
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export functions for HTML onclick handlers
window.setMode = setSelectionMode;
window.resetMap = resetMap;
window.runRouting = calculateRoute;
window.compareAlgos = compareAlgorithms;
window.updateTime = updateTime;
window.closeModal = closeModal;