import os
import re
import csv
import urllib.parse
import psycopg2
import requests
from bs4 import BeautifulSoup

DB_URL = "postgresql://neondb_owner:npg_U70SXrAFVTBp@ep-super-pine-aodhk33n-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1XIvzlgr-sg0scyMaxmIZgwOQk41wJLE1zmfbnq69V20/export?format=csv"

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
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database tables initialized successfully.")

def resolve_coords_and_name(url):
    """
    Follows redirects and parses Google Maps URL for coordinates and place name.
    """
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        return None, None, None

    try:
        # Do not download the full page if it's too big, but follow redirect
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
        final_url = r.url

        # If head requests don't redirect or fail to give maps search, try GET
        if 'google.com/maps' not in final_url and 'google.co.id/maps' not in final_url:
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
            final_url = r.url

        lat, lng = None, None
        place_name = None

        # Extract place name
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
            # Pattern 2: @lat,lng
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
            if match:
                lat, lng = float(match.group(1)), float(match.group(2))
            else:
                # Pattern 3: !3d(-?\d+\.\d+)!4d(-?\d+\.\d+)
                match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', final_url)
                if match:
                    lat, lng = float(match.group(1)), float(match.group(2))
                else:
                    # Pattern 4: center=lat%2Clng or center=lat,lng
                    match = re.search(r'center=(-?\d+\.\d+)(?:%2C|,)(-?\d+\.\d+)', final_url)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))

        # Pattern 5: if not found in URL, search within HTML body
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

def upsert_outlet(data):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO outlets (
                name, type, brand, address, phone, rental_price, size, rent_terms, 
                google_maps_url, competitors_nearby, photo_url, latitude, longitude, last_synced
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
                latitude = COALESCE(EXCLUDED.latitude, outlets.latitude),
                longitude = COALESCE(EXCLUDED.longitude, outlets.longitude),
                last_synced = CURRENT_TIMESTAMP;
        """, (
            data['name'], data['type'], data['brand'], data.get('address'), data.get('phone'),
            data.get('rental_price'), data.get('size'), data.get('rent_terms'), data['google_maps_url'],
            data.get('competitors_nearby'), data.get('photo_url'), data.get('latitude'), data.get('longitude')
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error upserting {data['name']}: {e}")
    finally:
        cur.close()
        conn.close()

def scrape_candidates():
    print("Scraping candidate outlets from Google Sheet...")
    try:
        r = requests.get(SHEET_URL, timeout=15)
        decoded_content = r.content.decode('utf-8')
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        rows = list(cr)
        
        # Check header
        if not rows:
            return
        
        for row in rows[1:]:
            if len(row) < 7 or not row[1].strip() or not row[6].strip():
                continue
            
            name = row[1].strip()
            size = row[2].strip()
            phone = row[3].strip()
            rental_price = row[4].strip()
            rent_terms = row[5].strip()
            maps_url = row[6].strip()
            competitors_nearby = row[7].strip() if len(row) > 7 else ""
            photo_url = row[8].strip() if len(row) > 8 else ""
            
            print(f"Resolving candidate: {name} ({maps_url})")
            lat, lng, _ = resolve_coords_and_name(maps_url)
            
            if lat is None or lng is None:
                # Try geocoding city or location name
                lat, lng = geocode_address(f"{name}, Jakarta, Indonesia")
            
            outlet_data = {
                'name': name,
                'type': 'candidate',
                'brand': 'Candidate',
                'address': name,
                'phone': phone,
                'rental_price': rental_price,
                'size': size,
                'rent_terms': rent_terms,
                'google_maps_url': maps_url,
                'competitors_nearby': competitors_nearby,
                'photo_url': photo_url,
                'latitude': lat,
                'longitude': lng
            }
            upsert_outlet(outlet_data)
            print(f"Saved Candidate: {name} -> {lat}, {lng}")
    except Exception as e:
        print(f"Error scraping candidates sheet: {e}")

def scrape_raja_emas():
    print("Scraping Raja Emas...")
    url = "https://rajaemasindonesia.co.id"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find all google maps links
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            # Look for google maps pattern
            if 'maps.app.goo.gl' in href or 'google.com/maps' in href or 'share.google' in href:
                text = a.text.strip()
                # If the anchor has no text, try nearby parent texts
                if not text:
                    parent = a.find_parent()
                    text = parent.text.strip() if parent else "Raja Emas Branch"
                
                # Clean text to remove newlines and extra spaces
                text = re.sub(r'\s+', ' ', text).strip()
                if not text or len(text) < 3 or 'lokasi' in text.lower():
                    # Set a default name
                    text = "Raja Emas Outlet"
                
                print(f"Resolving Raja Emas: {text} ({href})")
                lat, lng, resolved_name = resolve_coords_and_name(href)
                
                # Use resolved name if found in URL path
                name = resolved_name if resolved_name else text
                if not name.lower().startswith("raja emas"):
                    name = f"Raja Emas - {name}"
                
                if lat and lng:
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'Raja Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': lat,
                        'longitude': lng
                    })
                    print(f"Saved Raja Emas: {name} -> {lat}, {lng}")
    except Exception as e:
        print(f"Error scraping Raja Emas: {e}")

def scrape_i_love_emas():
    print("Scraping I Love Emas...")
    url = "https://iloveemas.co.id/outlet/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            if 'maps.app.goo.gl' in href or 'google.com/maps' in href or 'share.google' in href:
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
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'I Love Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': lat,
                        'longitude': lng
                    })
                    print(f"Saved I Love Emas: {name} -> {lat}, {lng}")
    except Exception as e:
        print(f"Error scraping I Love Emas: {e}")

def scrape_pandai_emas():
    print("Scraping Pandai Emas...")
    url = "https://www.pandaiemas.id/lokasi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            if 'maps.google.com' in href or 'maps.app.goo.gl' in href or 'google.com/maps' in href:
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
                    upsert_outlet({
                        'name': name,
                        'type': 'competitor',
                        'brand': 'Pandai Emas',
                        'address': name,
                        'google_maps_url': href,
                        'latitude': lat,
                        'longitude': lng
                    })
                    print(f"Saved Pandai Emas: {name} -> {lat}, {lng}")
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
                upsert_outlet({
                    'name': name,
                    'type': 'competitor',
                    'brand': 'Jual Emas',
                    'address': name,
                    'google_maps_url': href,
                    'latitude': lat,
                    'longitude': lng
                })
                print(f"Saved Jual Emas: {name} -> {lat}, {lng}")
    except Exception as e:
        print(f"Error scraping Jual Emas: {e}")

def run_all():
    init_db()
    scrape_candidates()
    scrape_raja_emas()
    scrape_i_love_emas()
    scrape_pandai_emas()
    scrape_jual_emas()
    print("All scraping and sync activities completed.")

if __name__ == "__main__":
    run_all()
