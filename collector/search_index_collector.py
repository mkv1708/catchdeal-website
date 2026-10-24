import json
import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

OUTPUT_FILE = "search_index.json"
AFFILIATE_TAG = "catchdeal07-21"
MAX_RESULTS_PER_TERM = 5

# Search coverage for common shopping intent. These are refreshed automatically.
SEARCH_TERMS = [
    "gaming chair", "office chair", "coffee maker", "air fryer", "mixer grinder",
    "vacuum cleaner", "robot vacuum", "water purifier", "electric kettle", "induction cooktop",
    "ceiling fan", "table fan", "iron box", "hair dryer", "trimmer",
    "electric toothbrush", "power bank", "wireless charger", "mobile charger", "usb c cable",
    "wireless earbuds", "bluetooth headphones", "bluetooth speaker", "smart watch", "fitness band",
    "laptop", "gaming laptop", "laptop stand", "laptop bag", "wireless mouse",
    "keyboard", "gaming keyboard", "gaming mouse", "monitor", "webcam",
    "wifi router", "external hard drive", "ssd", "pen drive", "memory card",
    "phone case", "screen protector", "tripod", "ring light", "security camera",
    "dash cam", "car charger", "car vacuum cleaner", "car phone holder", "tyre inflator",
    "backpack", "travel bag", "wallet", "handbag", "running shoes",
    "sports shoes", "sunglasses", "water bottle", "lunch box", "food container",
    "bedsheet", "pillow", "mattress protector", "curtains", "towel",
    "cookware set", "frying pan", "pressure cooker", "knife set", "chopping board",
    "storage box", "shoe rack", "study table", "desk lamp", "extension board",
    "baby diapers", "baby wipes", "baby stroller", "baby bottle", "baby monitor",
    "dog food", "cat food", "pet bed", "pet grooming kit", "dog leash",
    "yoga mat", "dumbbells", "resistance bands", "badminton racket", "cricket bat",
    "football", "cycle helmet", "massage gun", "weighing scale", "first aid kit",
    "face wash", "sunscreen", "moisturizer", "shampoo", "perfume",
    "toys", "board games", "lego", "remote control car", "kids bicycle",
    "printer", "printer ink", "calculator", "notebook", "office stationery",
    "smart tv", "tv stand", "soundbar", "streaming device", "projector",
    "refrigerator", "washing machine", "microwave oven", "geyser", "room heater",
    "inverter", "ups", "solar light", "emergency light", "rechargeable fan",
    "camera", "action camera", "microphone", "podcast microphone", "phone gimbal",
    "gaming headset", "game controller", "playstation accessories", "xbox accessories", "gaming desk",
    "neck pillow", "packing cubes", "travel adapter", "luggage scale", "umbrella",
    "men watch", "women watch", "men shoes", "women shoes", "slippers",
    "t shirt men", "jeans men", "dress women", "kurti women", "kids clothes",
    "protein shaker", "gym bag", "pull up bar", "skipping rope", "foam roller",
    "garden tools", "plant pots", "water hose", "mosquito racket", "insect killer",
    "door lock", "smart lock", "tool kit", "drill machine", "screwdriver set",
    "cleaning brush", "mop", "laundry basket", "garbage bags", "dish rack",
    "rice cooker", "sandwich maker", "toaster", "juicer", "hand blender",
    "smartphone", "android phone", "iphone accessories", "tablet", "tablet cover",
    "books", "self help books", "children books", "colouring books", "exam preparation books",
    "chocolate", "dry fruits", "coffee", "tea", "snacks"
]

IS_CI = os.getenv("CI", "").lower() == "true"


def clean_text(value):
    return " ".join(value.split()) if value else ""


def collect_term(page, term):
    url = f"https://www.amazon.in/s?k={quote_plus(term)}"
    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1800)

    cards = page.locator('div[data-component-type="s-search-result"]')
    try:
        cards.first.wait_for(state="visible", timeout=5000)
    except Exception:
        print(f"  No result cards: status={response.status if response else 'unknown'}, title={page.title()!r}")
        return []
    results = []
    seen = set()

    for i in range(cards.count()):
        if len(results) >= MAX_RESULTS_PER_TERM:
            break
        card = cards.nth(i)
        asin = clean_text(card.get_attribute("data-asin") or "").upper()
        if not asin or asin in seen:
            continue

        title = ""
        image = ""
        try:
            title = clean_text(card.locator("h2").first.inner_text())
        except Exception:
            pass
        try:
            image = card.locator("img.s-image").first.get_attribute("src") or ""
        except Exception:
            pass
        if not title or not image:
            continue

        seen.add(asin)
        product_url = f"https://www.amazon.in/dp/{asin}"
        results.append({
            "asin": asin,
            "title": title,
            "imageUrl": image,
            "amazonUrl": f"{product_url}?tag={AFFILIATE_TAG}",
            "productUrl": product_url,
        })
    return results


def collect_entries(page, terms):
    entries = {}
    # Retry only empty/failed searches, once, after the first pass. This gives
    # slow result pages another chance without repeatedly fetching successes.
    for attempt in range(2):
        missing = [term for term in terms if term not in entries]
        if not missing:
            break
        for number, term in enumerate(missing, 1):
            print(f"[pass {attempt + 1}, {number}/{len(missing)}] Searching: {term}")
            try:
                results = collect_term(page, term)
                if results:
                    entries[term] = results
                    print(f"  Found {len(results)} products")
                else:
                    print("  No valid products")
            except Exception as error:
                print(f"  Search failed: {error}")
    return entries


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=IS_CI)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        entries = collect_entries(page, SEARCH_TERMS)
        browser.close()

    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "termCount": len(entries),
        "productCount": sum(len(items) for items in entries.values()),
        "terms": entries,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"Search index: {data['termCount']} terms / {data['productCount']} product references")


if __name__ == "__main__":
    main()

