import json
import os
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

OUTPUT_FILE = "products.json"
AFFILIATE_TAG = "catchdeal07-21"
TARGET_PRODUCTS = 300
MIN_PRODUCTS = 30
MAX_PRODUCTS_PER_CATEGORY = 24
MIN_PRODUCTS_PER_CATEGORY = 2
RETRIES_PER_CATEGORY = 2

# A wider pool lets the live category mix change from run to run.
# Only categories that return enough valid Best Seller products are published.
CATEGORY_POOL = [
    {"id": "home-kitchen", "label": "Home & Kitchen", "icon": "🏠", "url": "https://www.amazon.in/gp/bestsellers/kitchen"},
    {"id": "beauty", "label": "Beauty", "icon": "✨", "url": "https://www.amazon.in/gp/bestsellers/beauty"},
    {"id": "electronics", "label": "Electronics", "icon": "💻", "url": "https://www.amazon.in/gp/bestsellers/electronics"},
    {"id": "books", "label": "Books", "icon": "📚", "url": "https://www.amazon.in/gp/bestsellers/books"},
    {"id": "toys-games", "label": "Toys & Games", "icon": "🧸", "url": "https://www.amazon.in/gp/bestsellers/toys"},
    {"id": "baby", "label": "Baby", "icon": "👶", "url": "https://www.amazon.in/gp/bestsellers/baby"},
    {"id": "sports-fitness", "label": "Sports, Fitness & Outdoors", "icon": "🏃", "url": "https://www.amazon.in/gp/bestsellers/sports"},
    {"id": "health-personal-care", "label": "Health & Personal Care", "icon": "❤️", "url": "https://www.amazon.in/gp/bestsellers/hpc"},
    {"id": "car-motorbike", "label": "Car & Motorbike", "icon": "🚗", "url": "https://www.amazon.in/gp/bestsellers/automotive"},
    {"id": "clothing-accessories", "label": "Clothing & Accessories", "icon": "👕", "url": "https://www.amazon.in/gp/bestsellers/apparel"},
    {"id": "computers-accessories", "label": "Computers & Accessories", "icon": "🖥️", "url": "https://www.amazon.in/gp/bestsellers/computers"},
    {"id": "office-products", "label": "Office Products", "icon": "🗂️", "url": "https://www.amazon.in/gp/bestsellers/office"},
    {"id": "pet-supplies", "label": "Pet Supplies", "icon": "🐾", "url": "https://www.amazon.in/gp/bestsellers/pet-supplies"},
    {"id": "shoes-handbags", "label": "Shoes & Handbags", "icon": "👟", "url": "https://www.amazon.in/gp/bestsellers/shoes"},
    {"id": "grocery", "label": "Grocery & Gourmet Foods", "icon": "🛒", "url": "https://www.amazon.in/gp/bestsellers/grocery"},
]

IS_CI = os.getenv("CI", "").lower() == "true"


def clean_text(value):
    return " ".join(value.split()) if value else ""


def extract_asin(url):
    if not url:
        return None
    for pattern in (r"/dp/([A-Z0-9]{10})", r"/gp/product/([A-Z0-9]{10})"):
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def extract_visible_rank(container):
    try:
        element = container.locator(".zg-bdg-text").first
        if element.count():
            match = re.search(r"#(\d+)", clean_text(element.inner_text()))
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return None


def extract_product(container, asin, category):
    title = ""
    image = ""
    rating = ""
    rank = extract_visible_rank(container)

    try:
        element = container.locator("div[class*='line-clamp']").first
        if element.count():
            title = clean_text(element.inner_text())
    except Exception:
        pass

    try:
        element = container.locator("img").first
        if element.count():
            image = element.get_attribute("src") or ""
            if not title:
                title = clean_text(element.get_attribute("alt") or "")
    except Exception:
        pass

    try:
        element = container.locator("span.a-icon-alt").first
        if element.count():
            rating = clean_text(element.inner_text())
    except Exception:
        pass

    if not title or not image:
        return None

    product_url = f"https://www.amazon.in/dp/{asin}"
    return {
        "id": asin,
        "asin": asin,
        "title": title,
        "category": category["id"],
        "categoryLabel": category["label"],
        "imageUrl": image,
        "amazonUrl": f"{product_url}?tag={AFFILIATE_TAG}",
        "productUrl": product_url,
        "rating": rating,
        "rank": rank,
    }


def collect_category(page, category, global_asins):
    best = []

    for attempt in range(1, RETRIES_PER_CATEGORY + 1):
        print(f"  Attempt {attempt}/{RETRIES_PER_CATEGORY}")
        try:
            page.goto(category["url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            for _ in range(6):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(600)

            links = page.locator('a[href*="/dp/"]')
            category_asins = set()
            found = []

            for index in range(links.count()):
                if len(found) >= MAX_PRODUCTS_PER_CATEGORY:
                    break

                link = links.nth(index)
                try:
                    asin = extract_asin(link.get_attribute("href") or "")
                    if not asin or asin in category_asins or asin in global_asins:
                        continue

                    container = link.locator(
                        "xpath=ancestor::div[contains(@class,'zg-grid-general-faceout')]"
                    ).first
                    if not container.count():
                        continue

                    product = extract_product(container, asin, category)
                    if not product:
                        continue

                    category_asins.add(asin)
                    found.append(product)
                except Exception as error:
                    print("    Skipping product:", error)

            # Best Seller pages are already ranked; retain visible rank order.
            found.sort(key=lambda p: p["rank"] if p["rank"] is not None else 999999)
            if len(found) > len(best):
                best = found

            if len(best) >= MAX_PRODUCTS_PER_CATEGORY:
                break

            if attempt < RETRIES_PER_CATEGORY:
                page.wait_for_timeout(2500)
        except Exception as error:
            print(f"    Attempt failed: {error}")

    return best


def main():
    print("=" * 60)
    print("CatchDeal Dynamic Amazon Best Seller Collector")
    print("=" * 60)
    print("Browser mode:", "HEADLESS (automation)" if IS_CI else "VISIBLE (local)")

    # Collect from the full candidate pool before choosing the final mix.
    # This prevents the first few categories from consuming all 50 slots.
    category_candidates = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=IS_CI)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()

        for category in CATEGORY_POOL:
            print("\n" + "-" * 60)
            print(f"Checking Best Sellers: {category['label']}")
            products = collect_category(page, category, set())
            if len(products) < MIN_PRODUCTS_PER_CATEGORY:
                print(f"Skipping category: only {len(products)} valid products")
                continue
            category_candidates.append((category, products))
            print(f"Found {len(products)} candidates from {category['label']}")

        if not IS_CI:
            input("\nPress Enter to close Chromium...")
        browser.close()

    # First give every eligible category two unique products. Then add one
    # product per category per round until the catalogue reaches its target.
    # A duplicate ASIN is kept only in the first category that receives it.
    all_products = []
    global_asins = set()
    selected = {category["id"]: [] for category, _ in category_candidates}

    for category, candidates in category_candidates:
        for product in candidates:
            if len(selected[category["id"]]) >= MIN_PRODUCTS_PER_CATEGORY:
                break
            if product["asin"] not in global_asins:
                selected[category["id"]].append(product)
                global_asins.add(product["asin"])

    # Categories with fewer than two unique products do not appear on the site.
    # Release their reserved ASINs before filling the rest of the catalogue.
    eligible = []
    global_asins = set()
    for category, candidates in category_candidates:
        chosen = selected[category["id"]]
        if len(chosen) >= MIN_PRODUCTS_PER_CATEGORY:
            eligible.append((category, candidates))
            global_asins.update(product["asin"] for product in chosen)
        else:
            selected[category["id"]] = []
            print(f"Skipping category: fewer than two unique products ({category['label']})")

    # Keep the first-pass allocation within the target if the pool expands.
    while sum(len(selected[category["id"]]) for category, _ in eligible) > TARGET_PRODUCTS:
        for category, _ in reversed(eligible):
            chosen = selected[category["id"]]
            if len(chosen) > 0:
                removed = chosen.pop()
                global_asins.remove(removed["asin"])
                if sum(len(selected[cat["id"]]) for cat, _ in eligible) <= TARGET_PRODUCTS:
                    break

    while sum(len(selected[category["id"]]) for category, _ in eligible) < TARGET_PRODUCTS:
        added = False
        for category, candidates in eligible:
            chosen = selected[category["id"]]
            if len(chosen) >= MAX_PRODUCTS_PER_CATEGORY:
                continue
            for product in candidates:
                if product["asin"] not in global_asins:
                    chosen.append(product)
                    global_asins.add(product["asin"])
                    added = True
                    break
            if sum(len(selected[cat["id"]]) for cat, _ in eligible) >= TARGET_PRODUCTS:
                break
        if not added:
            break

    active_categories = []
    category_counts = {}
    for category, _ in eligible:
        chosen = selected[category["id"]]
        if len(chosen) < MIN_PRODUCTS_PER_CATEGORY:
            continue
        all_products.extend(chosen)
        active_categories.append({
            "id": category["id"],
            "label": category["label"],
            "icon": category["icon"],
        })
        category_counts[category["label"]] = len(chosen)
        print(f"Selected {len(chosen)} products from {category['label']}")

    catalogue = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "productCount": len(all_products),
        "categories": active_categories,
        "products": all_products,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(catalogue, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Candidate categories checked: {len(CATEGORY_POOL)}")
    print(f"Active categories: {len(active_categories)}")
    print(f"Unique products collected: {len(all_products)} / target {TARGET_PRODUCTS}")
    for label, total in category_counts.items():
        print(f"  {label}: {total}")

    # The workflow performs the final catalogue validation. This warning is
    # useful during local testing too.
    if len(all_products) < MIN_PRODUCTS:
        print(f"WARNING: fewer than {MIN_PRODUCTS} products were collected.")


if __name__ == "__main__":
    main()

