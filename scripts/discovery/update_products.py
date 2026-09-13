import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
OUTPUT = Path("data/products.json")

CATEGORIES = [
    {
        "id": "mobiles",
        "label": "Mobiles",
        "icon": "📱",
        "query": "best smartphones India {year} recommendations review buying guide",
    },
    {
        "id": "audio",
        "label": "Audio",
        "icon": "🎧",
        "query": "best earbuds headphones India {year} recommendations review buying guide",
    },
    {
        "id": "smart-devices",
        "label": "Wearables",
        "icon": "⌚",
        "query": "best smartwatches fitness trackers India {year} recommendations review buying guide",
    },
    {
        "id": "kitchen",
        "label": "Kitchen",
        "icon": "🍳",
        "query": "best kitchen appliances India {year} air fryer mixer grinder recommendations review",
    },
    {
        "id": "home-comfort",
        "label": "Home",
        "icon": "🏠",
        "query": "best useful home products India {year} appliances storage cleaning recommendations review",
    },
    {
        "id": "fitness",
        "label": "Fitness",
        "icon": "💪",
        "query": "best home fitness products India {year} yoga workout accessories recommendations review",
    },
]

# We deliberately exclude major marketplaces. CatchDeal discovers recommendations
# from editorial/public sources and sends the shopper to Amazon only after they click.
EXCLUDED_DOMAINS = [
    "amazon.in",
    "amazon.com",
    "flipkart.com",
    "meesho.com",
    "walmart.com",
    "bestbuy.com",
    "ebay.com",
    "aliexpress.com",
    "temu.com",
]

PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["name"],
            },
        }
    },
    "required": ["products"],
}


def post_json(url, payload, headers=None, retries=3):
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **(headers or {})}

    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Firecrawl HTTP {exc.code}: {text[:500]}") from exc
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Firecrawl request failed: {exc}") from exc


def search_category(category, year, api_key):
    prompt = (
        "Extract up to 6 specific consumer products that this page positively recommends for "
        f"the {category['label']} category. Return exact brand + model/product names where possible. "
        "For each product include a short neutral reason based only on this page. "
        "Do not return article titles, generic product types, stores, prices, ratings, or availability."
    )

    payload = {
        "query": category["query"].format(year=year),
        "limit": 3,
        "excludeDomains": EXCLUDED_DOMAINS,
        "scrapeOptions": {
            "onlyMainContent": True,
            "formats": [
                {
                    "type": "json",
                    "schema": PRODUCT_SCHEMA,
                    "prompt": prompt,
                    "checkPromptInjection": True,
                }
            ],
        },
    }
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    result = post_json(FIRECRAWL_SEARCH_URL, payload, headers=headers)
    if not result.get("success"):
        raise RuntimeError(f"Firecrawl search returned unsuccessful response: {result}")

    web_results = (result.get("data") or {}).get("web") or []
    return web_results


def clean_name(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip(" -–—|:;,.\t\n")
    if len(value) < 4 or len(value) > 120:
        return None
    # Reject obvious generic/article-style outputs.
    lowered = value.casefold()
    bad_fragments = [
        "best products",
        "best smartphone",
        "buying guide",
        "top picks",
        "our picks",
        "recommendations",
    ]
    if lowered in bad_fragments or lowered.startswith("best ") and len(value.split()) < 4:
        return None
    return value


def key_for(name):
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def clean_reason(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if not value:
        return "Appears in a current independent buying guide."
    if len(value) > 180:
        value = value[:177].rsplit(" ", 1)[0] + "…"
    return value


def build_amazon_search_url(product_name, partner_tag):
    query = urllib.parse.urlencode({"k": product_name, "tag": partner_tag})
    return f"https://www.amazon.in/s?{query}"


def collect_category(category, web_results, partner_tag):
    candidates = {}
    source_titles = {}

    for position, result in enumerate(web_results, start=1):
        url = result.get("url") or ""
        title = result.get("title") or "Independent buying guide"
        if not url:
            continue
        source_titles[url] = title
        extracted = result.get("json") or {}
        products = extracted.get("products") or []

        for item in products:
            name = clean_name(item.get("name"))
            if not name:
                continue
            key = key_for(name)
            if not key:
                continue

            entry = candidates.setdefault(
                key,
                {
                    "title": name,
                    "reasons": [],
                    "sources": [],
                    "rankPoints": 0,
                },
            )
            if url not in entry["sources"]:
                entry["sources"].append(url)
                entry["rankPoints"] += max(1, 5 - position)
            reason = clean_reason(item.get("reason"))
            if reason not in entry["reasons"]:
                entry["reasons"].append(reason)

    ranked = []
    for entry in candidates.values():
        source_count = len(entry["sources"])
        score = source_count * 100 + entry["rankPoints"]
        badge = "Widely Recommended" if source_count >= 3 else ("Popular Pick" if source_count == 2 else "Worth a Look")
        ranked.append(
            {
                "title": entry["title"],
                "category": category["id"],
                "categoryLabel": category["label"],
                "icon": category["icon"],
                "reason": entry["reasons"][0] if entry["reasons"] else "Appears in a current independent buying guide.",
                "badge": badge,
                "sourceCount": source_count,
                "sources": [
                    {"url": url, "title": source_titles.get(url, "Independent source")}
                    for url in entry["sources"][:3]
                ],
                "score": score,
                "amazonUrl": build_amazon_search_url(entry["title"], partner_tag),
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["title"].casefold()))
    return ranked[:8]


def write_catalogue(products):
    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated,
        "method": "independent-web-discovery",
        "note": "Product names are discovered from independent public buying guides. Prices, stock, ratings and Amazon product images are intentionally not scraped.",
        "categories": [
            {"id": c["id"], "label": c["label"], "icon": c["icon"]}
            for c in CATEGORIES
        ],
        "products": products,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    partner_tag = os.environ.get("AMAZON_PARTNER_TAG", "").strip()
    if not partner_tag:
        print("ERROR: AMAZON_PARTNER_TAG is missing.", file=sys.stderr)
        return 2

    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    year = datetime.now(timezone.utc).year
    all_products = []
    failures = []

    for category in CATEGORIES:
        try:
            print(f"Discovering {category['label']}…")
            results = search_category(category, year, api_key)
            picks = collect_category(category, results, partner_tag)
            print(f"  {len(picks)} picks from {len(results)} independent pages")
            all_products.extend(picks)
        except Exception as exc:
            failures.append(f"{category['label']}: {exc}")
            print(f"WARNING: {category['label']} discovery failed: {exc}", file=sys.stderr)
        time.sleep(1)

    if len(all_products) < 8:
        print("WARNING: Not enough reliable products were discovered. Existing catalogue is left unchanged.", file=sys.stderr)
        for failure in failures:
            print(" - " + failure, file=sys.stderr)
        return 0

    write_catalogue(all_products)
    print(f"Generated {len(all_products)} CatchDeal picks across {len(CATEGORIES)} categories.")
    if failures:
        print("Some categories were skipped safely:")
        for failure in failures:
            print(" - " + failure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
