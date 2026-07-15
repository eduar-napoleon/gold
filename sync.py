import os
import re
import csv
import urllib.parse
import psycopg2
import requests
from bs4 import BeautifulSoup
import time

DB_URL = "postgresql://neondb_owner:npg_U70SXrAFVTBp@ep-super-pine-aodhk33n-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

def init_db():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS outlets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            brand VARCHAR(100) NOT NULL,
            address TEXT,
            phone VARCHAR(50),
            rental_price VARCHAR(100),
            size VARCHAR(100),
            rent_terms TEXT,
            google_maps_url TEXT UNIQUE,
            competitors_nearby TEXT,
            photo_url TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            reviews_count INT DEFAULT 0,
            reviews_1m INT DEFAULT 0,
            reviews_6m INT DEFAULT 0,
            reviews_12m INT DEFAULT 0,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("ALTER TABLE outlets ADD COLUMN IF NOT EXISTS reviews_count INT DEFAULT 0;")
    cur.execute("ALTER TABLE outlets ADD COLUMN IF NOT EXISTS reviews_1m INT DEFAULT 0;")
    cur.execute("ALTER TABLE outlets ADD COLUMN IF NOT EXISTS reviews_6m INT DEFAULT 0;")
    cur.execute("ALTER TABLE outlets ADD COLUMN IF NOT EXISTS reviews_12m INT DEFAULT 0;")
    cur.execute("DELETE FROM outlets WHERE type = 'candidate';")
    conn.commit()
    cur.close()
    conn.close()
    print("Database tables initialized and candidates deleted successfully.")

def resolve_coords_and_name(url):
    """
    Follows redirects and parses Google Maps URL for coordinates and place name.
    """
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        return None, None, None

    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
        final_url = r.url

        if 'google.com/maps' not in final_url and 'google.co.id/maps' not in final_url:
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
            final_url = r.url

        lat, lng = None, None
        place_name = None

        place_match = re.search(r'/place/([^/]+)/', final_url)
        if place_match:
            place_name = urllib.parse.unquote(place_match.group(1).replace('+', ' '))
        else:
            search_match = re.search(r'/search/([^/?]+)', final_url)
            if search_match:
                place_name = urllib.parse.unquote(search_match.group(1).replace('+', ' '))

        # Pattern 1: /search/lat,+lng
        match = re.search(r'/search/(-?\d+\.\d+),\+?(-?\d+\.\d+)', final_url)
        if match:
            lat, lng = float(match.group(1)), float(match.group(2))
        else:
            # Pattern 2: !3d(-?\d+\.\d+)!4d(-?\d+\.\d+) (Exact place coordinates - prioritize over map camera center!)
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', final_url)
            if match:
                lat, lng = float(match.group(1)), float(match.group(2))
            else:
                # Pattern 3: @lat,lng (Fallback map camera center)
                match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
                if match:
                    lat, lng = float(match.group(1)), float(match.group(2))
                else:
                    # Pattern 4: center=lat%2Clng or center=lat,lng
                    match = re.search(r'center=(-?\d+\.\d+)(?:%2C|,)(-?\d+\.\d+)', final_url)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))

        if lat is None or lng is None:
            r_get = requests.get(url, headers=HEADERS, timeout=10)
            meta_match = re.search(r'meta content=\"https://maps.google.com/maps/api/staticmap\?center=(-?\d+\.\d+)%2C(-?\d+\.\d+)', r_get.text)
            if meta_match:
                lat, lng = float(meta_match.group(1)), float(meta_match.group(2))

        return lat, lng, place_name
    except Exception as e:
        print(f"Error resolving coordinates for {url}: {e}")
        return None, None, None

def geocode_address(address):
    """
    Fallback geocoding using Nominatim (OpenStreetMap)
    """
    if not address:
        return None, None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'gold-outlet-scraper-app'}, timeout=10)
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Nominatim geocoding error for {address}: {e}")
    return None, None

def fetch_reviews_count(name, brand, resolved_name=None):
    """
    Scrapes the Google Maps Embed API using different query variations.
    Returns: (reviews_count, latitude, longitude)
    """
    queries = []
    
    # 1. Canonical resolved name from redirect (best match)
    if resolved_name:
        clean_resolved = re.sub(r'\s+@\s*[-+]?\d+\.\d+,\s*[-+]?\d+\.\d+', '', resolved_name)
        queries.append(clean_resolved)
        
    # Clean the raw name
    clean_name = name
    if name.startswith(f"{brand} - "):
        clean_name = name.replace(f"{brand} - ", "", 1)
    if name.startswith(f"{brand} Indonesia - "):
        clean_name = name.replace(f"{brand} Indonesia - ", "", 1)
        
    # 2. Brand + Clean Name
    if brand.lower() not in clean_name.lower():
        queries.append(f"{brand} Indonesia - {clean_name}")
        queries.append(f"{brand} {clean_name}")
    else:
        queries.append(clean_name)
        
    # 3. Add country or city to force single match
    if len(clean_name) < 30:
        queries.append(f"{brand} {clean_name}, Indonesia")
        
    # Query sequentially until we find a match
    for q in queries:
        url = f"https://maps.google.com/maps?q={urllib.parse.quote(q)}&output=embed"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            # Match reviews with thousand separators (like 1.087 or 1,087)
            match = re.search(r'\"([0-9\.,]+)\s+(?:reviews|ulasan)\"', r.text)
            if match:
                raw_val = match.group(1)
                val = int(raw_val.replace('.', '').replace(',', ''))
                
                # Match coordinates from the [[[zoom, longitude, latitude] array in Embed JS
                lat, lng = None, None
                coord_match = re.search(r'\[\[\[\d+\.?\d*,\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)\]', r.text)
                if coord_match:
                    lng, lat = float(coord_match.group(1)), float(coord_match.group(2))
                    
                print(f"  Scraped reviews for {name} ({q}): {val} (Coords: {lat}, {lng})")
                return val, lat, lng
        except Exception as e:
            print(f"  Error fetching reviews for {q}: {e}")
        time.sleep(0.5)
        
    return 0, None, None

def upsert_outlet(data):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("SELECT reviews_count, reviews_1m, reviews_6m, reviews_12m FROM outlets WHERE google_maps_url = %s;", (data['google_maps_url'],))
        row = cur.fetchone()
        
        new_count = data.get('reviews_count', 0)
        if row:
            old_count, r1m, r6m, r12m = row
            if old_count is None: old_count = 0
            if r1m is None: r1m = 0
            if r6m is None: r6m = 0
            if r12m is None: r12m = 0
            
            diff = new_count - old_count
            if diff > 0:
                r1m += diff
                r6m += diff
                r12m += diff
            elif diff < 0:
                r1m = max(0, r1m + diff)
                r6m = max(0, r6m + diff)
                r12m = max(0, r12m + diff)
                
            r12m = min(r12m, new_count)
            r6m = min(r6m, r12m)
            r1m = min(r1m, r6m)
        else:
            r1m = int(new_count * 0.06) + 1 if new_count > 5 else 0
            r6m = int(new_count * 0.32) + 2 if new_count > 5 else 0
            r12m = int(new_count * 0.60) + 3 if new_count > 5 else 0
            
            r12m = min(r12m, new_count)
            r6m = min(r6m, r12m)
            r1m = min(r1m, r6m)
            
        cur.execute("""
            INSERT INTO outlets (
                name, type, brand, address, phone, rental_price, size, rent_terms, 
                google_maps_url, competitors_nearby, photo_url, latitude, longitude, reviews_count, 
                reviews_1m, reviews_6m, reviews_12m, last_synced
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (google_maps_url) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                brand = EXCLUDED.brand,
                address = COALESCE(EXCLUDED.address, outlets.address),
                phone = COALESCE(EXCLUDED.phone, outlets.phone),
                rental_price = COALESCE(EXCLUDED.rental_price, outlets.rental_price),
                size = COALESCE(EXCLUDED.size, outlets.size),
                rent_terms = COALESCE(EXCLUDED.rent_terms, outlets.rent_terms),
                competitors_nearby = COALESCE(EXCLUDED.competitors_nearby, outlets.competitors_nearby),
                photo_url = COALESCE(EXCLUDED.photo_url, outlets.photo_url),
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                reviews_count = EXCLUDED.reviews_count,
                reviews_1m = EXCLUDED.reviews_1m,
                reviews_6m = EXCLUDED.reviews_6m,
                reviews_12m = EXCLUDED.reviews_12m,
                last_synced = CURRENT_TIMESTAMP;
        """, (
            data['name'], data['type'], data['brand'], data.get('address'), data.get('phone'),
            data.get('rental_price'), data.get('size'), data.get('rent_terms'), data['google_maps_url'],
            data.get('competitors_nearby'), data.get('photo_url'), data.get('latitude'), data.get('longitude'),
            new_count, r1m, r6m, r12m
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error upserting {data['name']}: {e}")
    finally:
        cur.close()
        conn.close()

def scrape_raja_emas():
    print("Scraping Raja Emas...")
    url = "https://rajaemasindonesia.co.id"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        processed_urls = set()
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            if 'maps.app.goo.gl' in href or 'google.com/maps' in href or 'share.google' in href:
                if href in processed_urls:
                    continue
                processed_urls.add(href)
                
                # Find specific branch heading by traversing up to column element
                branch_title = ''
                parent_col = None
                curr = a
                while curr:
                    curr = curr.parent
                    if curr and curr.name == 'div' and curr.get('class') and any('bde-column' in c for c in curr.get('class')):
                        parent_col = curr
                        break
                
                if parent_col:
                    headers = parent_col.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', 'span'])
                    for h in headers:
                        txt = h.text.strip()
                        if txt and re.search(r'^\d+[A-Za-z]', txt):
                            branch_title = txt
                            break
                    if not branch_title:
                        for h in headers:
                            txt = h.text.strip()
                            if txt and len(txt) < 40 and not any(kw in txt.lower() for kw in ['lokasi', 'buka', 'whatsapp', 'catatan']):
                                branch_title = txt
                                break
                                
                branch_title = re.sub(r'^\d+', '', branch_title).strip() # strip leading numbers
                if not branch_title:
                    branch_title = "Raja Emas Outlet"
                
                print(f"Resolving Raja Emas: {branch_title} ({href})")
                lat, lng, resolved_name = resolve_coords_and_name(href)
                
                name = branch_title
                if not name.lower().startswith("raja emas"):
                    name = f"Raja Emas Indonesia - {name}"
                
                if lat and lng:
                    reviews_count, embed_lat, embed_lng = fetch_reviews_count(name, 'Raja Emas', resolved_name)
                    final_lat = embed_lat if embed_lat is not None else lat
                    final_lng = embed_lng if embed_lng is not None else lng
                    
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'Raja Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': final_lat,
                        'longitude': final_lng,
                        'reviews_count': reviews_count
                    })
                    print(f"Saved Raja Emas: {name} -> {final_lat}, {final_lng} (Reviews: {reviews_count})")
    except Exception as e:
        print(f"Error scraping Raja Emas: {e}")

def scrape_i_love_emas():
    print("Scraping I Love Emas...")
    url = "https://iloveemas.co.id/outlet/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        processed_urls = set()
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            if 'maps.app.goo.gl' in href or 'google.com/maps' in href or 'share.google' in href:
                if href in processed_urls:
                    continue
                processed_urls.add(href)
                
                text = a.text.strip()
                if not text:
                    parent = a.find_parent()
                    text = parent.text.strip() if parent else "I Love Emas Branch"
                
                text = re.sub(r'\s+', ' ', text).strip()
                if not text or len(text) < 3 or 'lokasi' in text.lower():
                    text = "I Love Emas Outlet"
                
                print(f"Resolving I Love Emas: {text} ({href})")
                lat, lng, resolved_name = resolve_coords_and_name(href)
                
                name = resolved_name if resolved_name else text
                if not name.lower().startswith("i love emas"):
                    name = f"I Love Emas - {name}"
                
                if lat and lng:
                    reviews_count, embed_lat, embed_lng = fetch_reviews_count(name, 'I Love Emas', resolved_name)
                    final_lat = embed_lat if embed_lat is not None else lat
                    final_lng = embed_lng if embed_lng is not None else lng
                    
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'I Love Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': final_lat,
                        'longitude': final_lng,
                        'reviews_count': reviews_count
                    })
                    print(f"Saved I Love Emas: {name} -> {final_lat}, {final_lng} (Reviews: {reviews_count})")
    except Exception as e:
        print(f"Error scraping I Love Emas: {e}")

def scrape_pandai_emas():
    print("Scraping Pandai Emas...")
    url = "https://www.pandaiemas.id/lokasi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        processed_urls = set()
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            if 'maps.google.com' in href or 'maps.app.goo.gl' in href or 'google.com/maps' in href:
                if href in processed_urls:
                    continue
                processed_urls.add(href)
                
                text = a.text.strip()
                if not text:
                    parent = a.find_parent()
                    text = parent.text.strip() if parent else "Pandai Emas Branch"
                
                text = re.sub(r'\s+', ' ', text).strip()
                if not text or len(text) < 3 or 'lokasi' in text.lower() or 'maps' in text.lower():
                    text = "Pandai Emas Outlet"
                
                lat, lng = None, None
                resolved_name = None
                if 'maps.google.com/?q=' in href or 'maps.google.com/maps?q=' in href:
                    query = urllib.parse.unquote(href.split('q=')[1].split('&')[0])
                    resolved_name = query
                    lat, lng = geocode_address(query + ", Indonesia")
                else:
                    lat, lng, resolved_name = resolve_coords_and_name(href)
                
                name = resolved_name if resolved_name else text
                if not name.lower().startswith("pandai emas"):
                    name = f"Pandai Emas - {name}"
                
                if lat and lng:
                    reviews_count, embed_lat, embed_lng = fetch_reviews_count(name, 'Pandai Emas', resolved_name)
                    final_lat = embed_lat if embed_lat is not None else lat
                    final_lng = embed_lng if embed_lng is not None else lng
                    
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'Pandai Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': final_lat,
                        'longitude': final_lng,
                        'reviews_count': reviews_count
                    })
                    print(f"Saved Pandai Emas: {name} -> {final_lat}, {final_lng} (Reviews: {reviews_count})")
    except Exception as e:
        print(f"Error scraping Pandai Emas: {e}")

def scrape_jual_emas():
    print("Scraping Jual Emas...")
    url = "https://jualemas.id"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        branch_pages = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/cabang/' in href:
                branch_pages.add(urllib.parse.urljoin(url, href))
        
        processed_urls = set()
        maps_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'maps.app.goo.gl' in href or 'google.com/maps' in href or 'share.google' in href:
                maps_links.add((href, a.text.strip()))
                
        for b_url in branch_pages:
            try:
                br = requests.get(b_url, headers=HEADERS, timeout=10)
                bsoup = BeautifulSoup(br.text, 'html.parser')
                b_title = bsoup.title.string.strip() if bsoup.title else "Jual Emas Branch"
                for ba in bsoup.find_all('a', href=True):
                    bhref = ba['href']
                    if 'maps.app.goo.gl' in bhref or 'google.com/maps' in bhref or 'share.google' in bhref:
                        maps_links.add((bhref, b_title))
            except Exception as e:
                print(f"Error scraping branch page {b_url}: {e}")
                
        for href, text in maps_links:
            if href in processed_urls:
                continue
            processed_urls.add(href)
            
            text = re.sub(r'\s+', ' ', text).strip()
            if not text or len(text) < 3 or 'lokasi' in text.lower() or 'cek' in text.lower():
                text = "Jual Emas Outlet"
                
            print(f"Resolving Jual Emas: {text} ({href})")
            lat, lng, resolved_name = resolve_coords_and_name(href)
            
            name = resolved_name if resolved_name else text
            name = name.split('|')[0].strip()
            if not name.lower().startswith("jual emas"):
                name = f"Jual Emas - {name}"
                
            if lat and lng:
                reviews_count, embed_lat, embed_lng = fetch_reviews_count(name, 'Jual Emas', resolved_name)
                final_lat = embed_lat if embed_lat is not None else lat
                final_lng = embed_lng if embed_lng is not None else lng
                
                upsert_outlet({
                    'name': name,
                    'type': 'competitor',
                    'brand': 'Jual Emas',
                    'address': name,
                    'google_maps_url': href,
                    'latitude': final_lat,
                    'longitude': final_lng,
                    'reviews_count': reviews_count
                })
                print(f"Saved Jual Emas: {name} -> {final_lat}, {final_lng} (Reviews: {reviews_count})")
    except Exception as e:
        print(f"Error scraping Jual Emas: {e}")

def run_all():
    init_db()
    scrape_raja_emas()
    scrape_i_love_emas()
    scrape_pandai_emas()
    scrape_jual_emas()
    print("All scraping and sync activities completed.")

if __name__ == "__main__":
    run_all()
