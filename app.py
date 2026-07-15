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
    <title>Peta Analisis Kompetitor Outlet Emas</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <!-- Leaflet Heatmap Plugin -->
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    
    <!-- FontAwesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: rgba(17, 24, 39, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
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
            grid-template-columns: 1fr;
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

        .reviews-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(251, 191, 36, 0.15);
            color: var(--accent-gold);
            padding: 3px 7px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div id="sidebar">
        <div class="sidebar-header">
            <h1><i class="fa-solid fa-map-location-dot"></i> Emas Map Analyzer</h1>
            <p>Visualisasi sebaran & popularitas kompetitor retail emas.</p>
        </div>

        <!-- Stats -->
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-val competitor" id="cnt-competitor">0</div>
                <div class="stat-lbl">Total Outlet Kompetitor</div>
            </div>
        </div>

        <!-- Filters -->
        <div class="filter-section">
            <div class="filter-title"><i class="fa-solid fa-filter"></i> Filter & Mode</div>
            <div class="filter-group">
                <!-- Heatmap Toggle -->
                <div class="filter-item" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
                    <div class="filter-checkbox">
                        <input type="checkbox" id="chk-heatmap" onchange="updateFilters()">
                        <span style="font-weight: 600; color: var(--accent-gold);"><i class="fa-solid fa-fire"></i> Mode Heatmap (Ulasan)</span>
                    </div>
                </div>

                <!-- Review Period Selector -->
                <div class="filter-item" style="border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 8px; display: block; cursor: default;">
                    <div style="font-size: 0.85rem; font-weight: 500; margin-bottom: 6px; color: var(--text-muted);">
                        Filter Waktu Ulasan:
                    </div>
                    <select id="sel-period" onchange="updateFilters()" style="width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px; color: #fff; outline: none; font-size: 0.85rem; cursor: pointer;">
                        <option value="all">Semua Waktu (All Time)</option>
                        <option value="1m">1 Bulan Terakhir</option>
                        <option value="6m">6 Bulan Terakhir</option>
                        <option value="12m">12 Bulan Terakhir</option>
                    </select>
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
        let heatLayer = null;
        
        // Custom color marker creation using SVG
        function createSvgIcon(color) {
            let svg = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
                    <path fill="${color}" stroke="#fff" stroke-width="1.5" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                </svg>
            `;
            return L.divIcon({
                html: svg,
                className: 'custom-svg-icon',
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32]
            });
        }

        // Color mapper
        const BRAND_COLORS = {
            'Raja Emas': '#ef4444',   // Red
            'I Love Emas': '#ec4899', // Pink
            'Pandai Emas': '#3b82f6', // Blue
            'Jual Emas': '#fbbf24'    // Gold
        };

        // Initialize App
        async function init() {
            // Setup Leaflet map
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

            await loadOutlets();
        }

        // Fetch outlets from API
        async function loadOutlets() {
            try {
                const response = await fetch('/api/outlets');
                allOutlets = await response.json();
                
                updateCounts();
                renderFiltersAndList();
            } catch (err) {
                console.error("Gagal memuat data outlet:", err);
            }
        }

        function updateCounts() {
            const competitors = allOutlets.filter(o => o.type === 'competitor');
            document.getElementById('cnt-competitor').innerText = competitors.length;

            document.getElementById('cnt-raja-badge').innerText = allOutlets.filter(o => o.brand === 'Raja Emas').length;
            document.getElementById('cnt-ilove-badge').innerText = allOutlets.filter(o => o.brand === 'I Love Emas').length;
            document.getElementById('cnt-pandai-badge').innerText = allOutlets.filter(o => o.brand === 'Pandai Emas').length;
            document.getElementById('cnt-jual-badge').innerText = allOutlets.filter(o => o.brand === 'Jual Emas').length;
        }

        // Filter flags
        function getActiveBrands() {
            const brands = [];
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
            const searchQuery = document.getElementById('search-bar').value.toLowerCase().trim();
            const showHeatmap = document.getElementById('chk-heatmap').checked;
            const period = document.getElementById('sel-period').value;
            
            // Clear existing map layers
            markersGroup.clearLayers();
            if (heatLayer) {
                map.removeLayer(heatLayer);
                heatLayer = null;
            }

            const listContainer = document.getElementById('outlet-list');
            listContainer.innerHTML = '';

            // Helper to get period-specific review counts
            const getReviewsForPeriod = (o) => {
                if (period === '1m') return o.reviews_1m || 0;
                if (period === '6m') return o.reviews_6m || 0;
                if (period === '12m') return o.reviews_12m || 0;
                return o.reviews_count || 0;
            };

            // Filter and sort outlets by review count descending (dynamic based on selected period)
            const filteredOutlets = allOutlets.filter(o => {
                const matchesBrand = activeBrands.includes(o.brand);
                const matchesSearch = o.name.toLowerCase().includes(searchQuery) || 
                                      (o.address && o.address.toLowerCase().includes(searchQuery));
                return matchesBrand && matchesSearch;
            }).sort((a, b) => getReviewsForPeriod(b) - getReviewsForPeriod(a));

            // Populate Map
            if (showHeatmap) {
                const heatPoints = [];
                let maxReviews = 1;
                
                filteredOutlets.forEach(o => {
                    if (o.latitude && o.longitude) {
                        const reviews = getReviewsForPeriod(o);
                        if (reviews > maxReviews) maxReviews = reviews;
                        heatPoints.push([o.latitude, o.longitude, reviews]);
                    }
                });
                
                if (heatPoints.length > 0) {
                    heatLayer = L.heatLayer(heatPoints, {
                        radius: 35,
                        blur: 20,
                        maxZoom: 15,
                        max: maxReviews
                    }).addTo(map);
                }
            }

            // Always render markers
            filteredOutlets.forEach(outlet => {
                if (outlet.latitude && outlet.longitude) {
                    const color = BRAND_COLORS[outlet.brand] || '#6b7280';
                    const markerIcon = createSvgIcon(color);
                    const marker = L.marker([outlet.latitude, outlet.longitude], { icon: markerIcon });
                    
                    const reviewsVal = getReviewsForPeriod(outlet);
                    const ratingVal = outlet.rating || 0;
                    
                    let reviewsText = '';
                    if (period === 'all') {
                        reviewsText = `${reviewsVal} Ulasan`;
                    } else {
                        const lbl = period === '1m' ? '1 Bulan terakhir' : period === '6m' ? '6 Bulan terakhir' : '12 Bulan terakhir';
                        reviewsText = `${reviewsVal} Ulasan Baru (${lbl})`;
                    }

                    // Format rating display
                    const ratingStars = ratingVal > 0 ? `<span style="color: var(--accent-gold); font-weight: 700; margin-right: 6px;"><i class="fa-solid fa-star"></i> ${ratingVal.toFixed(1)}</span>` : '';

                    // Construct Popup Content
                    let popupContent = `
                        <div class="popup-card">
                            <div class="popup-title">${outlet.name}</div>
                            <div class="popup-info">
                                <div><strong>Brand:</strong> ${outlet.brand}</div>
                                <div><strong>Populer:</strong> <span class="reviews-badge">${ratingStars}${reviewsText}</span></div>
                                <a href="${outlet.google_maps_url}" target="_blank" class="popup-btn">
                                    <i class="fa-solid fa-location-arrow"></i> Buka Google Maps
                                </a>
                            </div>
                        </div>
                    `;

                    marker.bindPopup(popupContent);
                    markersGroup.addLayer(marker);

                    // Map marker click event
                    marker.on('click', () => {
                        highlightListItem(outlet.id);
                    });
                }
            });

            // Populate Sidebar List (sorted by reviews descending)
            filteredOutlets.forEach(outlet => {
                const div = document.createElement('div');
                div.className = 'list-item';
                div.id = `item-${outlet.id}`;
                div.onclick = () => focusOnOutlet(outlet);

                const brandBadgeClass = outlet.brand.toLowerCase().replace(' ', '');
                const reviewsVal = getReviewsForPeriod(outlet);
                const ratingVal = outlet.rating || 0;
                
                let reviewsText = '';
                if (period === 'all') {
                    reviewsText = `${reviewsVal} Ulasan`;
                } else {
                    const lbl = period === '1m' ? '1 Bln' : period === '6m' ? '6 Bln' : '12 Bln';
                    reviewsText = `${reviewsVal} Ulasan Baru (${lbl})`;
                }

                const ratingStars = ratingVal > 0 ? `<span style="color: var(--accent-gold); font-weight: 700; margin-right: 6px;"><i class="fa-solid fa-star"></i> ${ratingVal.toFixed(1)}</span>` : '';

                div.innerHTML = `
                    <div class="item-title">
                        <span>${outlet.name}</span>
                        <span class="badge ${brandBadgeClass}">${outlet.brand}</span>
                    </div>
                    <div class="item-details">
                        <div class="item-detail-row">
                            <span class="reviews-badge">${ratingStars}${reviewsText}</span>
                        </div>
                        ${outlet.google_maps_url ? `<div class="item-detail-row"><i class="fa-solid fa-map-pin"></i> Google Maps Link</div>` : ''}
                    </div>
                `;
                listContainer.appendChild(div);
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

            // Find and open popup if not in heatmap mode
            const showHeatmap = document.getElementById('chk-heatmap').checked;
            if (!showHeatmap) {
                markersGroup.eachLayer(marker => {
                    const latlng = marker.getLatLng();
                    if (latlng.lat === outlet.latitude && latlng.lng === outlet.longitude) {
                        marker.openPopup();
                    }
                });
            }

            highlightListItem(outlet.id);
        }

        function highlightListItem(id) {
            document.querySelectorAll('.list-item').forEach(el => el.classList.remove('active'));
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
                           rent_terms, google_maps_url, competitors_nearby, photo_url, latitude, longitude, 
                           reviews_count, reviews_1m, reviews_6m, reviews_12m, rating
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
                        'longitude': row[13],
                        'reviews_count': row[14],
                        'reviews_1m': row[15],
                        'reviews_6m': row[16],
                        'reviews_12m': row[17],
                        'rating': row[18]
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
