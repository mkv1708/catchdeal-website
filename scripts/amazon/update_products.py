import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

API_BASE="https://creatorsapi.amazon"
TOKEN_ENDPOINTS={"3.1":"https://api.amazon.com/auth/o2/token","3.2":"https://api.amazon.co.uk/auth/o2/token","3.3":"https://api.amazon.co.jp/auth/o2/token"}

def die(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)

def post_json(url, payload, headers=None, retries=4):
    headers={"Content-Type":"application/json", **(headers or {})}
    body=json.dumps(payload).encode()
    for attempt in range(retries):
        req=urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw=e.read().decode(errors="replace")
            if e.code in (429,500,502,503,504) and attempt<retries-1:
                retry_after=e.headers.get("Retry-After")
                delay=float(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt,16)
                time.sleep(delay); continue
            die(f"HTTP {e.code} from {url}: {raw[:800]}")
        except Exception as e:
            if attempt<retries-1:
                time.sleep(min(2**attempt,16)); continue
            die(f"Request failed: {e}")

def token():
    cid=os.environ.get("AMAZON_CLIENT_ID")
    secret=os.environ.get("AMAZON_CLIENT_SECRET")
    version=os.environ.get("AMAZON_CREDENTIAL_VERSION","3.2")
    if not cid or not secret:
        die("Set GitHub Actions secrets AMAZON_CLIENT_ID and AMAZON_CLIENT_SECRET before running this workflow.")
    endpoint=TOKEN_ENDPOINTS.get(version)
    if not endpoint:
        die(f"Unsupported credential version: {version}")
    data=post_json(endpoint,{"grant_type":"client_credentials","client_id":cid,"client_secret":secret,"scope":"creatorsapi::default"})
    access=data.get("access_token")
    if not access: die("Amazon token response did not contain access_token.")
    return access

def api_call(access, operation, payload):
    return post_json(f"{API_BASE}/catalog/v1/{operation}",payload,{
        "Authorization":f"Bearer {access}",
        "x-marketplace":payload["marketplace"]
    })

def nested(obj,*keys):
    for key in keys:
        if not isinstance(obj,dict): return None
        obj=obj.get(key)
    return obj

def first_offer(item):
    listings=nested(item,"offersV2","listings") or []
    return listings[0] if listings else {}

def money(offer):
    p=offer.get("price") or {}
    m=p.get("money") or {}
    return m.get("amount"),m.get("currency"),m.get("displayAmount"),(p.get("savings") or {}).get("percentage")

def image_url(item):
    images=item.get("images") or {}
    primary=images.get("primary") or {}
    for size in ("large","medium","small"):
        value=primary.get(size)
        if isinstance(value,dict) and value.get("url"): return value["url"]
    return None

def title(item):
    return nested(item,"itemInfo","title","displayValue") or "Amazon product"

def brand(item):
    return nested(item,"itemInfo","byLineInfo","brand","displayValue") or nested(item,"itemInfo","byLineInfo","brand") or ""

def sales_rank(item):
    info=item.get("browseNodeInfo") or {}
    rank=info.get("websiteSalesRank") or {}
    if isinstance(rank,dict) and isinstance(rank.get("salesRank"),(int,float)): return rank["salesRank"]
    ranks=[]
    for node in info.get("browseNodes") or []:
        if isinstance(node,dict) and isinstance(node.get("salesRank"),(int,float)): ranks.append(node["salesRank"])
    return min(ranks) if ranks else None

def extract_item(item, category, query, occurrence):
    offer=first_offer(item)
    amount,currency,display,saving=money(offer)
    rank=sales_rank(item)
    rating=nested(item,"customerReviews","starRating","value")
    review_count=nested(item,"customerReviews","count")
    return {
        "asin":item.get("asin"),
        "title":title(item).strip(),
        "brand":brand(item),
        "category":category["id"],
        "categoryLabel":category["label"],
        "image":image_url(item),
        "price":amount,
        "currency":currency or "INR",
        "displayPrice":display,
        "savingPercent":saving,
        "rating":rating,
        "reviewCount":review_count,
        "salesRank":rank,
        "amazonUrl":item.get("detailPageURL"),
        "sourceQueries":[query],
        "searchHits":occurrence,
        "lastUpdated":datetime.now(timezone.utc).isoformat()
    }

def score(p):
    hits=min(p["searchHits"],3)/3*30
    rank_score=0 if not p["salesRank"] else max(0,25*(1/(1+(p["salesRank"]/5000))))
    rating=float(p["rating"] or 0)
    rating_score=(rating/5)*20
    reviews=float(p["reviewCount"] or 0)
    review_score=min(15,5*(reviews**0.5)/10)
    saving=min(10,float(p["savingPercent"] or 0)/5)
    return round(hits+rank_score+rating_score+review_score+saving,2)

def main():
    cfg=json.loads(Path("scripts/amazon/config.json").read_text())
    partner=os.environ.get("AMAZON_PARTNER_TAG")
    if not partner: die("Set GitHub Actions secret AMAZON_PARTNER_TAG before running this workflow.")
    access=token()
    candidates={}
    resources=[
        "images.primary.large","itemInfo.title","itemInfo.byLineInfo",
        "offersV2.listings.price","offersV2.listings.availability",
        "offersV2.listings.dealDetails","browseNodeInfo.websiteSalesRank",
        "browseNodeInfo.browseNodes.salesRank"
    ]
    for category in cfg["categories"]:
        for query in category["queries"][:cfg.get("searchRequestsPerCategory",3)]:
            payload={"keywords":query,"itemCount":10,"sortBy":"Featured","availability":"Available",
                     "marketplace":cfg["marketplace"],"partnerTag":partner,"resources":resources}
            data=api_call(access,"searchItems",payload)
            result=data.get("searchResult") or {}
            for item in result.get("items") or []:
                asin=item.get("asin")
                if not asin: continue
                key=f"{category['id']}:{asin}"
                if key not in candidates:
                    candidates[key]=extract_item(item,category,query,1)
                else:
                    candidates[key]["searchHits"]+=1
                    candidates[key]["sourceQueries"].append(query)
            time.sleep(0.35)

    products=[]
    for p in candidates.values():
        if not p["image"] or not p["amazonUrl"] or not p["asin"]: continue
        p["catchDealScore"]=score(p)
        hits=p.pop("searchHits")
        p["badge"]="Popular" if (p["salesRank"] and p["salesRank"]<=10000) else ("Good Value" if p["savingPercent"] and p["savingPercent"]>=10 else "Smart Pick")
        products.append(p)

    output=[]
    for cat in cfg["categories"]:
        items=[p for p in products if p["category"]==cat["id"]]
        items.sort(key=lambda x:x["catchDealScore"],reverse=True)
        output.extend(items[:cfg.get("maxProductsPerCategory",10)])

    result={"generatedAt":datetime.now(timezone.utc).isoformat(),"marketplace":cfg["marketplace"],
            "partnerTagConfigured":True,"categories":[{"id":c["id"],"label":c["label"],"icon":c["icon"]} for c in cfg["categories"]],
            "products":output}
    Path("data/products.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(f"Generated {len(output)} products across {len(cfg['categories'])} categories.")
    for cat in cfg["categories"]:
        print(f"  {cat['label']}: {sum(1 for p in output if p['category']==cat['id'])}")

if __name__=="__main__":
    main()
