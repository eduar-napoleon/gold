import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import psycopg2

DB_URL = "postgresql://neondb_owner:npg_U70SXrAFVTBp@ep-super-pine-aodhk33n-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peta Analisis Outlet Emas</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <!-- FontAwesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: rgba(17, 24, 39, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-green: #10b981;
            --accent-gold: #fbbf24;
            --accent-red: #ef4444;
            --accent-pink: #ec4899;
            --accent-blue: #3b82f6;
            --shadow-premium: 0 10px 30px -10px rgba(0, 0, 0, 0.7);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* Sidebar Container */
        #sidebar {
            width: 420px;
            background: var(--bg-secondary);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            height: 100%;
            z-index: 1000;
            box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }

        /* Header */
        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(10, 15, 30, 0.5);
        }

        .sidebar-header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #fbbf24 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }

        .sidebar-header p {
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        /* Stats Section */
        .stats-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.02);
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            transition: transform 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
        }

        .stat-val {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .stat-val.candidate { color: var(--accent-green); }
        .stat-val.competitor { color: var(--accent-gold); }

        .stat-lbl {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        /* Filter Section */
        .filter-section {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .filter-title {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .filter-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.9rem;
            cursor: pointer;
            padding: 4px 0;
        }

        .filter-checkbox {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .filter-checkbox input {
            accent-color: var(--accent-gold);
            width: 16px;
            height: 16px;
            cursor: pointer;
        }

        .badge {
            font-size: 0.75rem;
            padding: 3px 8px;
            border-radius: 20px;
            font-weight: 600;
        }

        .badge.candidate { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge.raja { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge.ilove { background: rgba(236, 72, 153, 0.15); color: var(--accent-pink); border: 1px solid rgba(236, 72, 153, 0.3); }
        .badge.pandai { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.3); }
        .badge.jual { background: rgba(251, 191, 36, 0.15); color: var(--accent-gold); border: 1px solid rgba(251, 191, 36, 0.3); }

        /* Search & List Section */
        .search-box {
            padding: 16px 24px 8px 24px;
            position: relative;
        }

        .search-input {
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px 10px 40px;
            color: #fff;
            font-size: 0.9rem;
            outline: none;
            transition: all 0.3s;
        }

        .search-input:focus {
            border-color: var(--accent-gold);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.2);
        }

        .search-icon {
            position: absolute;
            left: 38px;
            top: 28px;
            color: var(--text-muted);
        }

        /* List Area */
        .list-container {
            flex: 1;
            overflow-y: auto;
            padding: 12px 24px;
        }

        .list-container::-webkit-scrollbar {
            width: 6px;
        }

        .list-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }

        .list-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .list-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--accent-gold);
            transform: translateY(-2px);
        }

        .list-item.active {
            background: rgba(251, 191, 36, 0.08);
            border-color: var(--accent-gold);
            box-shadow: inset 0 0 10px rgba(251, 191, 36, 0.1);
        }

        .item-title {
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
        }

        .item-details {
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .item-detail-row {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Map styling */
        #map {
            flex: 1;
            height: 100%;
        }

        /* Custom Popup Styling */
        .leaflet-popup-content-wrapper {
            background: var(--bg-primary) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: var(--shadow-premium);
        }

        .leaflet-popup-tip {
            background: var(--bg-primary) !important;
        }

        .popup-card {
            padding: 5px;
            max-width: 250px;
        }

        .popup-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: #fff;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
        }

        .popup-info {
            font-size: 0.85rem;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .popup-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            color: #000;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
            cursor: pointer;
            text-decoration: none;
            margin-top: 10px;
            transition: opacity 0.2s;
        }

        .popup-btn:hover {
            opacity: 0.9;
        }

        /* Overlapping Alert Banner */
        .overlap-banner {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--accent-red);
            border-radius: 8px;
            padding: 8px 12px;
            margin-top: 8px;
            font-size: 0.75rem;
            color: #fca5a5;
            display: flex;
            align-items: center;
            gap: 6px;
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div id="sidebar">
        <div class="sidebar-header">
            <h1><i class="fa-solid fa-map-location-dot"></i> Emas Map Analyzer</h1>
            <p>Visualisasi sebaran calon outlet vs kompetitor retail emas.</p>
        </div>

        <!-- Stats -->
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-val candidate" id="cnt-candidate">0</div>
                <div class="stat-lbl">Calon Outlet</div>
            </div>
            <div class="stat-card">
                <div class="stat-val competitor" id="cnt-competitor">0</div>
                <div class="stat-lbl">Kompetitor</div>
            </div>
        </div>

        <!-- Filters -->
        <div class="filter-section">
            <div class="filter-title"><i class="fa-solid fa-filter"></i> Filter Brand / Tipe</div>
            <div class="filter-group">
                <div class="filter-item">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-candidate" checked onchange="updateFilters()">
                        <span>Calon Outlet</span>
                    </div>
                    <span class="badge candidate" id="cnt-candidate-badge">0</span>
                </div>
                <div class="filter-item">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-raja" checked onchange="updateFilters()">
                        <span>Raja Emas</span>
                    </div>
                    <span class="badge raja" id="cnt-raja-badge">0</span>
                </div>
                <div class="filter-item">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-ilove" checked onchange="updateFilters()">
                        <span>I Love Emas</span>
                    </div>
                    <span class="badge ilove" id="cnt-ilove-badge">0</span>
                </div>
                <div class="filter-item">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-pandai" checked onchange="updateFilters()">
                        <span>Pandai Emas</span>
                    </div>
                    <span class="badge pandai" id="cnt-pandai-badge">0</span>
                </div>
                <div class="filter-item">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-jual" checked onchange="updateFilters()">
                        <span>Jual Emas</span>
                    </div>
                    <span class="badge jual" id="cnt-jual-badge">0</span>
                </div>
            </div>
        </div>

        <!-- Search Bar -->
        <div class="search-box">
            <i class="fa-solid fa-magnifying-glass search-icon"></i>
            <input type="text" class="search-input" id="search-bar" placeholder="Cari nama lokasi atau wilayah..." oninput="handleSearch()">
        </div>

        <!-- List Area -->
        <div class="list-container" id="outlet-list">
            <!-- List items loaded dynamically -->
        </div>
    </div>

    <!-- Map Container -->
    <div id="map"></div>

    <script>
        let map;
        let allOutlets = [];
        let markersGroup;
        let circlesGroup;
        
        // Custom color marker creation using SVG
        function createSvgIcon(color, isCandidate = false) {
            let svg = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
                    <path fill="${color}" stroke="#fff" stroke-width="1.5" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                </svg>
            `;
            if (isCandidate) {
                // Add glowing background ring for candidate pins
                svg = `
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="38" height="38">
                        <circle cx="12" cy="12" r="10" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="3 3">
                            <animate attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="10s" repeatCount="indefinite"/>
                        </circle>
                        <path fill="${color}" stroke="#fff" stroke-width="1.5" d="M12 4C9.13 4 7 6.13 7 10c0 4.25 5 10 5 10s5-5.75 5-10c0-3.87-2.13-6-5-6zm0 7.5c-0.98 0-1.75-0.77-1.75-1.75S11.02 8 12 8s1.75 0.77 1.75 1.75S12.98 11.5 12 11.5z"/>
                    </svg>
                `;
            }
            return L.divIcon({
                html: svg,
                className: 'custom-svg-icon',
                iconSize: isCandidate ? [38, 38] : [32, 32],
                iconAnchor: isCandidate ? [19, 38] : [16, 32],
                popupAnchor: [0, -32]
            });
        }

        // Color mapper
        const BRAND_COLORS = {
            'Candidate': '#10b981',   // Emerald Green
            'Raja Emas': '#ef4444',   // Red
            'I Love Emas': '#ec4899', // Pink
            'Pandai Emas': '#3b82f6', // Blue
            'Jual Emas': '#fbbf24'    // Gold
        };

        // Initialize App
        async function init() {
            // Setup Leaflet map using CartoDB Dark Matter / Positron
            // Positron light style looks cleaner for Google Map style, Dark Matter for premium dark mode
            map = L.map('map', {
                zoomControl: false
            }).setView([-6.2088, 106.8456], 11); // Center in Jakarta

            L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(map);

            L.control.zoom({ position: 'topright' }).addTo(map);

            markersGroup = L.layerGroup().addTo(map);
            circlesGroup = L.layerGroup().addTo(map);

            await loadOutlets();
        }

        // Fetch outlets from API
        async function loadOutlets() {
            try {
                const response = await fetch('/api/outlets');
                allOutlets = await response.json();
                
                // Count and populate UI badges
                updateCounts();
                renderFiltersAndList();
            } catch (err) {
                console.error("Gagal memuat data outlet:", err);
            }
        }

        function updateCounts() {
            const candidates = allOutlets.filter(o => o.type === 'candidate');
            const competitors = allOutlets.filter(o => o.type === 'competitor');
            
            document.getElementById('cnt-candidate').innerText = candidates.length;
            document.getElementById('cnt-competitor').innerText = competitors.length;

            document.getElementById('cnt-candidate-badge').innerText = candidates.length;
            document.getElementById('cnt-raja-badge').innerText = allOutlets.filter(o => o.brand === 'Raja Emas').length;
            document.getElementById('cnt-ilove-badge').innerText = allOutlets.filter(o => o.brand === 'I Love Emas').length;
            document.getElementById('cnt-pandai-badge').innerText = allOutlets.filter(o => o.brand === 'Pandai Emas').length;
            document.getElementById('cnt-jual-badge').innerText = allOutlets.filter(o => o.brand === 'Jual Emas').length;
        }

        // Filter flags
        function getActiveBrands() {
            const brands = [];
            if (document.getElementById('chk-candidate').checked) brands.push('Candidate');
            if (document.getElementById('chk-raja').checked) brands.push('Raja Emas');
            if (document.getElementById('chk-ilove').checked) brands.push('I Love Emas');
            if (document.getElementById('chk-pandai').checked) brands.push('Pandai Emas');
            if (document.getElementById('chk-jual').checked) brands.push('Jual Emas');
            return brands;
        }

        function updateFilters() {
            renderFiltersAndList();
        }

        function handleSearch() {
            renderFiltersAndList();
        }

        // Render List and Map Markers
        function renderFiltersAndList() {
            const activeBrands = getActiveBrands();
            const searchQuery = document.getElementById('search-bar').value.toLowerCase().strip ? 
                                  document.getElementById('search-bar').value.toLowerCase().trim() : 
                                  document.getElementById('search-bar').value.toLowerCase();
            
            // Clear existing map layers
            markersGroup.clearLayers();
            circlesGroup.clearLayers();

            const listContainer = document.getElementById('outlet-list');
            listContainer.innerHTML = '';

            // Filter data
            const filteredOutlets = allOutlets.filter(o => {
                const matchesBrand = activeBrands.includes(o.brand);
                const matchesSearch = o.name.toLowerCase().includes(searchQuery) || 
                                      (o.address && o.address.toLowerCase().includes(searchQuery));
                return matchesBrand && matchesSearch;
            });

            // Populate Map and List
            filteredOutlets.forEach(outlet => {
                if (outlet.latitude && outlet.longitude) {
                    const color = BRAND_COLORS[outlet.brand] || '#6b7280';
                    const isCand = outlet.type === 'candidate';
                    const markerIcon = createSvgIcon(color, isCand);

                    const marker = L.marker([outlet.latitude, outlet.longitude], { icon: markerIcon });
                    
                    // Construct Popup Content
                    let popupContent = `
                        <div class="popup-card">
                            <div class="popup-title">${outlet.name}</div>
                            <div class="popup-info">
                                <div><strong>Brand:</strong> ${outlet.brand}</div>
                    `;

                    if (isCand) {
                        if (outlet.size) popupContent += `<div><strong>Ukuran:</strong> ${outlet.size}</div>`;
                        if (outlet.phone) popupContent += `<div><strong>No Telp:</strong> ${outlet.phone}</div>`;
                        if (outlet.rental_price) popupContent += `<div><strong>Harga Sewa:</strong> ${outlet.rental_price}</div>`;
                        if (outlet.rent_terms) popupContent += `<div><strong>Ketentuan:</strong> ${outlet.rent_terms}</div>`;
                        if (outlet.competitors_nearby) popupContent += `<div><strong>Kompetitor Dekat:</strong> ${outlet.competitors_nearby}</div>`;
                    }

                    popupContent += `
                                <a href="${outlet.google_maps_url}" target="_blank" class="popup-btn">
                                    <i class="fa-solid fa-location-arrow"></i> Buka Google Maps
                                </a>
                            </div>
                        </div>
                    `;

                    marker.bindPopup(popupContent);
                    markersGroup.addLayer(marker);

                    // Add 2km radius circle around candidate locations for overlap analysis
                    if (isCand) {
                        const circle = L.circle([outlet.latitude, outlet.longitude], {
                            color: color,
                            fillColor: color,
                            fillOpacity: 0.08,
                            radius: 2000, // 2km radius
                            weight: 1,
                            dashArray: '4, 4'
                        });
                        circlesGroup.addLayer(circle);
                    }

                    // Map marker click event
                    marker.on('click', () => {
                        highlightListItem(outlet.id);
                    });
                }

                // Add to Sidebar list if it's a Candidate (makes scanning new locations easier)
                if (outlet.type === 'candidate') {
                    const div = document.createElement('div');
                    div.className = 'list-item';
                    div.id = `item-${outlet.id}`;
                    div.onclick = () => focusOnOutlet(outlet);

                    div.innerHTML = `
                        <div class="item-title">
                            <span>${outlet.name}</span>
                            <span class="badge candidate">Calon</span>
                        </div>
                        <div class="item-details">
                            ${outlet.rental_price ? `<div class="item-detail-row"><i class="fa-solid fa-money-bill-wave" style="color: var(--accent-green)"></i> ${outlet.rental_price}</div>` : ''}
                            ${outlet.size ? `<div class="item-detail-row"><i class="fa-solid fa-maximize"></i> Ukuran: ${outlet.size}</div>` : ''}
                            ${outlet.phone ? `<div class="item-detail-row"><i class="fa-solid fa-phone"></i> ${outlet.phone}</div>` : ''}
                            ${outlet.competitors_nearby ? `<div class="overlap-banner"><i class="fa-solid fa-triangle-exclamation"></i> Dekat: ${outlet.competitors_nearby}</div>` : ''}
                        </div>
                    `;
                    listContainer.appendChild(div);
                }
            });

            // If empty
            if (filteredOutlets.length === 0) {
                listContainer.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding-top:20px;">Tidak ada outlet ditemukan.</div>';
            }
        }

        // Map selection and focus
        function focusOnOutlet(outlet) {
            map.flyTo([outlet.latitude, outlet.longitude], 14, {
                duration: 1.5
            });

            // Find and open popup
            markersGroup.eachLayer(marker => {
                const latlng = marker.getLatLng();
                if (latlng.lat === outlet.latitude && latlng.lng === outlet.longitude) {
                    marker.openPopup();
                }
            });

            highlightListItem(outlet.id);
        }

        function highlightListItem(id) {
            // Remove active classes
            document.querySelectorAll('.list-item').forEach(el => el.classList.remove('active'));
            // Add active class
            const activeItem = document.getElementById(`item-${id}`);
            if (activeItem) {
                activeItem.classList.add('active');
                activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        window.onload = init;
    </script>
</body>
</html>
"""

class MapRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
            
        elif parsed_path.path == '/api/outlets':
            # Query Database
            try:
                conn = psycopg2.connect(DB_URL)
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, name, type, brand, address, phone, rental_price, size, 
                           rent_terms, google_maps_url, competitors_nearby, photo_url, latitude, longitude
                    FROM outlets;
                """)
                rows = cur.fetchall()
                outlets = []
                for row in rows:
                    outlets.append({
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'brand': row[3],
                        'address': row[4],
                        'phone': row[5],
                        'rental_price': row[6],
                        'size': row[7],
                        'rent_terms': row[8],
                        'google_maps_url': row[9],
                        'competitors_nearby': row[10],
                        'photo_url': row[11],
                        'latitude': row[12],
                        'longitude': row[13]
                    })
                cur.close()
                conn.close()
                
                # Send JSON response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(outlets).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Database error: {e}".encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=MapRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Web server started at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
