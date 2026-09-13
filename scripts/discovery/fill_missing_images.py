import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

CATALOGUE = Path("data/products.json")
OPENVERSE_URL = "https://api.openverse.org/v1/images/"

ARTICLE_PHRASES = (
    "best ", "top ", "buying guide", "our picks", "you need", "from amazon",
    "recommendations", "gift guide", "deals", "things to buy"
)


def tokens(value):
    stop={"the","and","with","for","edition","wireless","smart","phone","smartphone","black","white"}
    return [x for x in re.findall(r"[a-z0-9]+", str(value).casefold()) if len(x)>1 and x not in stop]


def get_json(url, params):
    req=urllib.request.Request(url+"?"+urllib.parse.urlencode(params), headers={"User-Agent":"CatchDeal/1.0 (https://catchdeal.in/)"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_product_name(name):
    name=re.sub(r"\s+", " ", str(name or "")).strip(" -–—|:;,.\t\n")
    low=name.casefold()
    if len(name)<5 or len(name)>100 or len(name.split())<2: return None
    if any(low.startswith(x) for x in ARTICLE_PHRASES): return None
    if any(x in low for x in ("best fall decorations", "air fryer toaster ovens", "things you need")): return None
    # Phone/watch model names should contain a model identifier; this removes vague extractions such as "TATA Phone" or "iPhone Duo".
    if any(x in low for x in ("iphone", "galaxy", "pixel", "reno", "realme", "oneplus", "redmi", "poco", "cmf phone")):
        if not re.search(r"\d", name): return None
    return name


def choose(product_name, results):
    wanted=tokens(product_name)
    best=None; best_score=-1
    for item in results:
        image=item.get("url") or item.get("thumbnail") or ""
        if not image.startswith("https://"): continue
        title=item.get("title") or ""
        tags=" ".join((t.get("name") or "") for t in (item.get("tags") or []) if isinstance(t,dict))
        hay=(title+" "+tags).casefold()
        matches=sum(1 for t in wanted if t in hay)
        required=max(1, min(2, len(wanted)))
        if matches < required: continue
        width=item.get("width") or 0; height=item.get("height") or 0
        if width and height and (width < 250 or height < 250): continue
        score=matches*10
        if "logo" in hay or "icon" in hay: score-=8
        if score > best_score:
            source=item.get("foreign_landing_url") or item.get("detail_url") or "https://openverse.org/"
            license_name=(item.get("license") or "").upper(); creator=item.get("creator") or ""
            label="Openverse"+(f" · {license_name}" if license_name else "")+(f" · {creator[:80]}" if creator else "")
            best={"imageUrl":image,"imageSourceUrl":source,"imageSourceTitle":label}; best_score=score
    return best


def search_openverse(product_name):
    data=get_json(OPENVERSE_URL,{"q":product_name,"page_size":20,"mature":"false"})
    return choose(product_name,data.get("results") or [])


def main():
    if not CATALOGUE.exists(): return 0
    data=json.loads(CATALOGUE.read_text(encoding="utf-8")); products=data.get("products") or []

    cleaned=[]; rejected=[]
    for p in products:
        name=clean_product_name(p.get("title"))
        if not name:
            rejected.append(p.get("title","(untitled)")); continue
        p["title"]=name; cleaned.append(p)
    products=cleaned
    print(f"Quality filter: kept {len(products)} clean product names; rejected {len(rejected)} questionable entries.")
    for name in rejected: print(f"  rejected name: {name}")

    missing=[p for p in products if not p.get("imageUrl")]
    print(f"Openverse fallback: {len(missing)} clean products still need images.")
    found=0
    for i,p in enumerate(missing,1):
        try:
            image=search_openverse(p["title"])
            if image:
                p.update(image); found+=1; print(f"  openverse {i}/{len(missing)}: {p['title']}")
            else: print(f"  no licensed web match: {p['title']}")
        except Exception as exc: print(f"  lookup failed: {p['title']}: {exc}")
        time.sleep(0.3)

    publishable=[p for p in products if p.get("imageUrl")]
    removed=len(products)-len(publishable)
    print(f"Publishing {len(publishable)} products with real images; omitting {removed} products without images.")
    data["products"]=publishable
    data["note"]="Quality-first catalogue: only specific product names with a real sourced image are published. Images retain existing verified sources, then use Wikimedia Commons and Openverse openly licensed media. Prices, stock and ratings are not scraped from Amazon."
    CATALOGUE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__=="__main__": raise SystemExit(main())
