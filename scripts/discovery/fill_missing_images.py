import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

CATALOGUE = Path("data/products.json")
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

ARTICLE_PHRASES = (
    "best ", "top ", "buying guide", "our picks", "you need", "from amazon",
    "recommendations", "gift guide", "deals", "things to buy"
)
BAD_IMAGE_WORDS = (
    "street", "road", "building", "landscape", "cityscape", "selfie", "portrait",
    "sample photo", "camera sample", "shot on", "taken with", "photographed with",
    "wallpaper", "screenshot", "logo", "icon", "store", "shop", "billboard",
    "case", "cover", "screen protector", "advertisement", "poster"
)


def tokens(value):
    stop={"the","and","with","for","edition","wireless","smart","phone","smartphone","black","white","truly"}
    return [x for x in re.findall(r"[a-z0-9]+", str(value).casefold()) if len(x)>1 and x not in stop]


def get_json(params, retries=3):
    url=COMMONS_API_URL+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"CatchDeal/1.0 (https://catchdeal.in/; product image resolver)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req,timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == retries-1: raise
            time.sleep(1.5*(attempt+1))


def clean_product_name(name):
    name=re.sub(r"\s+", " ", str(name or "")).strip(" -–—|:;,.\t\n")
    low=name.casefold()
    if len(name)<5 or len(name)>100 or len(name.split())<2: return None
    if any(low.startswith(x) for x in ARTICLE_PHRASES): return None
    if any(x in low for x in ("best fall decorations", "air fryer toaster ovens", "things you need")): return None
    if any(x in low for x in ("iphone", "galaxy", "pixel", "reno", "realme", "oneplus", "redmi", "poco", "cmf phone")) and not re.search(r"\d", name): return None
    return name


def exact_token_present(token, text):
    return bool(re.search(r"(?<![a-z0-9])"+re.escape(token)+r"(?![a-z0-9])", text.casefold()))


def relevant_image(product_name, title, description=""):
    wanted=tokens(product_name)
    hay=(title+" "+description).casefold()
    if not wanted or any(word in hay for word in BAD_IMAGE_WORDS): return False
    matches=sum(1 for t in wanted if exact_token_present(t,hay))
    required=max(2,(len(wanted)*3+3)//4)
    if matches < min(required,len(wanted)): return False
    model_tokens=[t for t in wanted if any(c.isdigit() for c in t)]
    if model_tokens and not all(exact_token_present(t,hay) for t in model_tokens): return False
    # Brand/first meaningful token must appear too; avoids model-number collisions.
    if wanted and not exact_token_present(wanted[0],hay): return False
    return True


def search_commons(product_name):
    # Search Commons file namespace, then inspect only a small result set with machine-readable metadata.
    data=get_json({
        "action":"query","format":"json","generator":"search","gsrsearch":'"'+product_name+'"',
        "gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo",
        "iiprop":"url|extmetadata|size","iiurlwidth":900,
        "iiextmetadatafilter":"ImageDescription|LicenseShortName|Artist"
    })
    best=None; best_score=-1
    for page in (data.get("query") or {}).get("pages",{}).values():
        title=page.get("title") or ""
        info=(page.get("imageinfo") or [{}])[0]
        image=info.get("thumburl") or info.get("url") or ""
        if not image.startswith("https://"): continue
        width=info.get("thumbwidth") or info.get("width") or 0
        height=info.get("thumbheight") or info.get("height") or 0
        if width and height and (width<300 or height<300): continue
        meta=info.get("extmetadata") or {}
        desc=re.sub("<[^>]+>"," ",((meta.get("ImageDescription") or {}).get("value") or ""))
        if not relevant_image(product_name,title,desc): continue
        wanted=tokens(product_name)
        hay=(title+" "+desc).casefold()
        score=sum(10 for t in wanted if exact_token_present(t,hay))
        # Prefer filenames that look like the actual product, not contextual photos.
        if all(exact_token_present(t,title) for t in wanted if any(c.isdigit() for c in t)): score+=8
        license_name=((meta.get("LicenseShortName") or {}).get("value") or "").strip()
        artist=re.sub("<[^>]+>","",((meta.get("Artist") or {}).get("value") or "")).strip()
        if score>best_score:
            source="https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"),safe=":_/()")
            label="Wikimedia Commons"+(f" · {license_name}" if license_name else "")+(f" · {artist[:80]}" if artist else "")
            best={"imageUrl":image,"imageSourceUrl":source,"imageSourceTitle":label}
            best_score=score
    return best


def main():
    if not CATALOGUE.exists(): return 0
    data=json.loads(CATALOGUE.read_text(encoding="utf-8")); products=data.get("products") or []
    cleaned=[]; rejected=[]
    for p in products:
        name=clean_product_name(p.get("title"))
        if not name:
            rejected.append(p.get("title","(untitled)")); continue
        p["title"]=name
        p.pop("imageUrl",None); p.pop("imageSourceUrl",None); p.pop("imageSourceTitle",None)
        cleaned.append(p)
    products=cleaned
    print(f"Quality filter: kept {len(products)} clean product names; rejected {len(rejected)} questionable entries.")

    print(f"Wikimedia verification: checking {len(products)} products from scratch; no Openverse dependency.")
    found=0
    for i,p in enumerate(products,1):
        try:
            image=search_commons(p["title"])
            if image:
                p.update(image); found+=1; print(f"  verified {i}/{len(products)}: {p['title']}")
            else:
                print(f"  no safe match {i}/{len(products)}: {p['title']}")
        except Exception as exc:
            print(f"  lookup failed {i}/{len(products)}: {p['title']}: {exc}")
        time.sleep(0.25)

    publishable=[p for p in products if p.get("imageUrl")]
    # Never replace a healthy live catalogue with an empty/tiny result because a public image service had an outage.
    if len(publishable)<8:
        print(f"Only {len(publishable)} verified products found; refusing to replace the live catalogue. Remove generated JSON so workflow validation/publish safely skips.")
        CATALOGUE.unlink(missing_ok=True)
        return 0

    print(f"Publishing {len(publishable)} products with strictly matched Wikimedia images; omitting {len(products)-len(publishable)} without a safe match.")
    data["products"]=publishable
    data["note"]="Strict image catalogue: images are resolved from Wikimedia Commons only. Every refresh discards old assignments and publishes only products whose image filename/description closely matches the brand and model. Weak matches and scene/camera-sample images are rejected."
    CATALOGUE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__=="__main__": raise SystemExit(main())
