import requests
import json
import os
import time
import random
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/apartments.json")
FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "../data/feedback.json")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "../data/seen_ids.json")

FACEBOOK_GROUPS = os.environ.get("FACEBOOK_GROUPS", "").split(",")

SEARCH_AREAS = {
    "tel_aviv_north": ["צפון תל אביב", "תל אביב צפון", "נורד תל אביב", "הצפון הישן", "הצפון החדש"],
    "tel_aviv_center": ["מרכז תל אביב", "רוטשילד", "נחלת בנימין", "נווה צדק", "לב תל אביב"],
    "givatayim_borochov": ["גבעתיים", "בורוכוב", "בורחוב"],
    "ramat_gan_rishonim": ["רמת גן", "שכונת הראשונים", "הראשונים רמת גן"]
}

FILTERS = {
    "max_price": 5500,
    "min_rooms": 2,
    "max_rooms": 3,
    "min_size": 50,
    "require_parking": True,
    "require_shelter": True,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def random_sleep(a=1.5, b=4.0):
    time.sleep(random.uniform(a, b))

# ── Yad2 ──────────────────────────────────────────────────────────────────────
def scrape_yad2():
    print("🔍 Scraping Yad2...")
    results = []
    area_ids = {
        "tel_aviv": "5000",
        "givatayim": "6700",
        "ramat_gan": "8600",
    }
    for area_name, area_id in area_ids.items():
        try:
            url = (
                f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent"
                f"?city={area_id}&rooms={FILTERS['min_rooms']}-{FILTERS['max_rooms']}"
                f"&price=1000-{FILTERS['max_price']}&forceLdLoad=true"
            )
            r = requests.get(url, headers=HEADERS, timeout=15)
            random_sleep()
            if r.status_code != 200:
                continue
            data = r.json()
            feed = data.get("data", {}).get("feed", {}).get("feed_items", [])
            for item in feed:
                if item.get("type") == "ad":
                    price = item.get("price", 0)
                    if isinstance(price, str):
                        price = int("".join(filter(str.isdigit, price)) or 0)
                    apt = {
                        "id": make_id(str(item.get("id", "")) + "yad2"),
                        "source": "yad2",
                        "title": item.get("title_1", "") + " " + item.get("title_2", ""),
                        "price": price,
                        "rooms": item.get("rooms", ""),
                        "size": item.get("square_meters", ""),
                        "floor": item.get("floor", ""),
                        "address": item.get("address", {}).get("street", {}).get("text", "") + " " +
                                   item.get("address", {}).get("city", {}).get("text", ""),
                        "neighborhood": item.get("address", {}).get("neighborhood", {}).get("text", ""),
                        "description": item.get("meta_data", {}).get("description", ""),
                        "images": [img.get("src", "") for img in item.get("images_urls", [])[:5]],
                        "url": "https://www.yad2.co.il/item/" + str(item.get("token", "")),
                        "date_scraped": datetime.now().isoformat(),
                        "parking": None,
                        "shelter": None,
                        "raw": item,
                    }
                    results.append(apt)
        except Exception as e:
            print(f"Yad2 error ({area_name}): {e}")
    print(f"  ✅ Yad2: {len(results)} listings")
    return results

# ── Facebook Marketplace ───────────────────────────────────────────────────────
def scrape_fb_marketplace():
    print("🔍 Scraping Facebook Marketplace...")
    results = []
    search_queries = [
        "דירה להשכרה תל אביב",
        "דירה להשכרה גבעתיים",
        "דירה להשכרה רמת גן",
    ]
    for query in search_queries:
        try:
            url = f"https://www.facebook.com/marketplace/search/?query={requests.utils.quote(query)}&categoryId=propertyrentals"
            r = requests.get(url, headers=HEADERS, timeout=15)
            random_sleep(2, 5)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            scripts = soup.find_all("script", {"type": "application/json"})
            for script in scripts:
                try:
                    data = json.loads(script.string or "")
                    listings = extract_marketplace_listings(data)
                    results.extend(listings)
                except:
                    pass
        except Exception as e:
            print(f"FB Marketplace error: {e}")
    print(f"  ✅ Facebook Marketplace: {len(results)} listings")
    return results

def extract_marketplace_listings(data):
    results = []
    if not isinstance(data, dict):
        return results
    text = json.dumps(data)
    if "marketplace" not in text.lower():
        return results
    try:
        edges = (data.get("data", {})
                     .get("marketplace_search", {})
                     .get("feed_units", {})
                     .get("edges", []))
        for edge in edges:
            node = edge.get("node", {}).get("listing", {})
            if not node:
                continue
            price_info = node.get("listing_price", {})
            price_str = price_info.get("amount", "0")
            try:
                price = int(float(price_str))
            except:
                price = 0
            apt = {
                "id": make_id(str(node.get("id", "")) + "fbmp"),
                "source": "facebook_marketplace",
                "title": node.get("name", ""),
                "price": price,
                "rooms": "",
                "size": "",
                "floor": "",
                "address": node.get("location", {}).get("reverse_geocode", {}).get("city", ""),
                "neighborhood": "",
                "description": node.get("description", ""),
                "images": [node.get("primary_listing_photo", {}).get("image", {}).get("uri", "")],
                "url": "https://www.facebook.com/marketplace/item/" + str(node.get("id", "")),
                "date_scraped": datetime.now().isoformat(),
                "parking": None,
                "shelter": None,
            }
            if apt["title"] or apt["description"]:
                results.append(apt)
    except:
        pass
    return results

# ── Facebook Public Groups ─────────────────────────────────────────────────────
def scrape_fb_groups():
    print("🔍 Scraping Facebook public groups...")
    results = []
    for group_url in FACEBOOK_GROUPS:
        group_url = group_url.strip()
        if not group_url:
            continue
        try:
            r = requests.get(group_url, headers=HEADERS, timeout=15)
            random_sleep(2, 5)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            posts = soup.find_all("div", {"data-pagelet": True})
            for post in posts[:30]:
                text = post.get_text(" ", strip=True)
                if len(text) < 50:
                    continue
                if not any(kw in text for kw in ["דירה", "להשכרה", "חדרים", "חדר", "שכירות"]):
                    continue
                apt = {
                    "id": make_id(text[:100] + group_url),
                    "source": "facebook_group",
                    "title": text[:80],
                    "price": extract_price_from_text(text),
                    "rooms": extract_rooms_from_text(text),
                    "size": extract_size_from_text(text),
                    "floor": "",
                    "address": "",
                    "neighborhood": "",
                    "description": text[:1000],
                    "images": [img.get("src", "") for img in post.find_all("img") if img.get("src", "").startswith("http")][:3],
                    "url": group_url,
                    "date_scraped": datetime.now().isoformat(),
                    "parking": None,
                    "shelter": None,
                }
                results.append(apt)
        except Exception as e:
            print(f"FB Group error ({group_url}): {e}")
    print(f"  ✅ Facebook Groups: {len(results)} posts")
    return results

def extract_price_from_text(text):
    import re
    patterns = [r'(\d{3,5})\s*₪', r'(\d{3,5})\s*שקל', r'מחיר[:\s]+(\d{3,5})']
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return 0

def extract_rooms_from_text(text):
    import re
    m = re.search(r'(\d+(?:\.\d+)?)\s*חדרים?', text)
    if m:
        return m.group(1)
    return ""

def extract_size_from_text(text):
    import re
    m = re.search(r'(\d+)\s*מ"ר|(\d+)\s*מטר', text)
    if m:
        return m.group(1) or m.group(2)
    return ""

# ── Gemini AI Filter ───────────────────────────────────────────────────────────
def gemini_filter(apartments, feedback_history):
    print(f"🤖 Running Gemini AI filter on {len(apartments)} listings...")
    if not GEMINI_API_KEY:
        print("  ⚠️  No Gemini API key — skipping AI filter")
        return apartments

    feedback_summary = ""
    if feedback_history:
        yes_reasons = [f["reason"] for f in feedback_history if f["decision"] == "yes" and f.get("reason")]
        no_reasons = [f["reason"] for f in feedback_history if f["decision"] == "no" and f.get("reason")]
        if yes_reasons:
            feedback_summary += f"הסיבות שאהב: {'; '.join(yes_reasons[-10:])}\n"
        if no_reasons:
            feedback_summary += f"הסיבות שלא אהב: {'; '.join(no_reasons[-10:])}\n"

    filtered = []
    batch_size = 5
    for i in range(0, len(apartments), batch_size):
        batch = apartments[i:i+batch_size]
        batch_text = json.dumps(batch, ensure_ascii=False, default=str)

        prompt = f"""אתה עוזר לסנן דירות להשכרה עבור מישהו שמחפש בתל אביב.

הפילטרים הנדרשים:
- מחיר: עד 5,500 ₪
- חדרים: 2-3 חדרים
- גודל: מעל 50 מ"ר (אם לא רשום — אל תפסול)
- חניה: חובה (אם לא מצוין — פסול)
- מקלט/ממד: חובה במרחק הליכה (אם לא מצוין — הצג בכל זאת, ציין ספק)
- משופצת: העדפה (אם לא רשום אל תפסול, נסה להבין מהתמונות)
- אזורים מותרים: צפון תל אביב ישן וחדש, מרכז, רוטשילד, נחלת בנימין, נווה צדק, גבעתיים (בורכוב ו-10 דק' הליכה), רמת גן (שכונת הראשונים ו-10 דק' הליכה)
- לא: דרום תל אביב

היסטוריית פידבק של המשתמש:
{feedback_summary if feedback_summary else "אין עדיין היסטוריה"}

עבור כל דירה החלט: SHOW (כדאי להראות) או HIDE (לסנן).
חשוב: אם יש ספק — תמיד SHOW.

ענה אך ורק ב-JSON כזה:
[{{"id": "...", "decision": "SHOW/HIDE", "reason": "...", "confidence": 0.0-1.0, "flags": {{"parking": true/false/null, "shelter": true/false/null, "renovated": true/false/null}}}}]

הדירות:
{batch_text}"""

        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30
            )
            if r.status_code == 200:
                resp = r.json()
                text = resp["candidates"][0]["content"]["parts"][0]["text"]
                text = text.strip().lstrip("```json").rstrip("```").strip()
                decisions = json.loads(text)
                decision_map = {d["id"]: d for d in decisions}
                for apt in batch:
                    decision = decision_map.get(apt["id"], {})
                    if decision.get("decision") != "HIDE":
                        apt["ai_reason"] = decision.get("reason", "")
                        apt["ai_confidence"] = decision.get("confidence", 0.5)
                        flags = decision.get("flags", {})
                        if apt.get("parking") is None:
                            apt["parking"] = flags.get("parking")
                        if apt.get("shelter") is None:
                            apt["shelter"] = flags.get("shelter")
                        apt["renovated"] = flags.get("renovated")
                        filtered.append(apt)
            random_sleep(1, 2)
        except Exception as e:
            print(f"  Gemini error: {e}")
            filtered.extend(batch)

    print(f"  ✅ After AI filter: {len(filtered)} listings")
    return filtered

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f"\n🏠 Apartment Hunter — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)

    existing = load_json(DATA_FILE, {"apartments": [], "last_updated": ""})
    seen_ids = set(load_json(SEEN_FILE, []))
    feedback = load_json(FEEDBACK_FILE, [])

    # Scrape all sources
    all_listings = []
    all_listings.extend(scrape_yad2())
    all_listings.extend(scrape_fb_marketplace())
    if any(FACEBOOK_GROUPS):
        all_listings.extend(scrape_fb_groups())

    # Deduplicate
    new_listings = [a for a in all_listings if a["id"] not in seen_ids]
    print(f"\n📊 New listings (not seen before): {len(new_listings)}")

    if new_listings:
        # AI filter
        filtered = gemini_filter(new_listings, feedback)

        # Mark as seen
        for a in new_listings:
            seen_ids.add(a["id"])

        # Merge with existing
        existing_apts = existing.get("apartments", [])
        # Keep only last 200 apartments to avoid bloat
        merged = filtered + existing_apts
        merged = merged[:200]
    else:
        merged = existing.get("apartments", [])

    save_json(DATA_FILE, {
        "apartments": merged,
        "last_updated": datetime.now().isoformat(),
        "total": len(merged)
    })
    save_json(SEEN_FILE, list(seen_ids))

    print(f"\n✅ Done! Total apartments in dashboard: {len(merged)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
