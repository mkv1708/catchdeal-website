import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
OUTPUT = Path("data/products.json")
CATEGORIES = [
    {"id":"mobiles","label":"Mobiles","icon":"📱","query":"best smartphones India {year} recommendations review buying guide"},
    {"id":"audio","label":"Audio","icon":"🎧","query":"best earbuds headphones India {year} recommendations review buying guide"},
    {"id":"smart-devices","label":"Wearables","icon":"⌚","query":"best smartwatches fitness trackers India {year} recommendations review buying guide"},
    {"id":"kitchen","label":"Kitchen","icon":"🍳","query":"best kitchen appliances India {year} air fryer mixer grinder recommendations review"},
    {"id":"home-comfort","label":"Home","icon":"🏠","query":"best useful home products India {year} appliances storage cleaning recommendations review"},
    {"id":"fitness","label":"Fitness","icon":"💪","query":"best home fitness products India {year} yoga workout accessories recommendations review"},
]
EXCLUDED_DOMAINS=["amazon.in","amazon.com","flipkart.com","meesho.com","walmart.com","bestbuy.com","ebay.com","aliexpress.com","temu.com"]
PRODUCT_SCHEMA={"type":"object","properties":{"products":{"type":"array","maxItems":6,"items":{"type":"object","properties":{"name":{"type":"string"},"reason":{"type":"string"}},"required":["name"]}}},"required":["products"]}

def post_json(url,payload,headers=None,retries=3):
    body=json.dumps(payload).encode("utf-8"); request_headers={"Content-Type":"application/json",**(headers or {})}
    for attempt in range(retries):
        req=urllib.request.Request(url,data=body,headers=request_headers,method="POST")
        try:
            with urllib.request.urlopen(req,timeout=90) as response:return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text=exc.read().decode("utf-8",errors="replace")
            if exc.code in (429,500,502,503,504) and attempt<retries-1:time.sleep(2**attempt);continue
            raise RuntimeError(f"Firecrawl HTTP {exc.code}: {text[:500]}") from exc

def search_category(category,year,api_key):
    prompt=("Extract up to 6 specific consumer products positively recommended on this page for the "f"{category['label']} category. Return the exact brand + model/product name. Do not return article titles, generic product types, stores, prices, ratings, availability, rumored products, or names you cannot identify precisely.")
    payload={"query":category["query"].format(year=year),"limit":3,"excludeDomains":EXCLUDED_DOMAINS,"scrapeOptions":{"onlyMainContent":True,"formats":[{"type":"json","schema":PRODUCT_SCHEMA,"prompt":prompt,"checkPromptInjection":True}]}}
    headers={"Authorization":f"Bearer {api_key}"} if api_key else {}
    result=post_json(FIRECRAWL_SEARCH_URL,payload,headers=headers)
    if not result.get("success"):raise RuntimeError("Firecrawl search unsuccessful")
    return (result.get("data") or {}).get("web") or []

def clean_name(value):
    value=re.sub(r"\s+"," ",str(value or "")).strip(" -–—|:;,.\t\n"); low=value.casefold()
    if len(value)<5 or len(value)>100 or len(value.split())<2:return None
    if low.startswith(("best ","top ","our picks","buying guide")):return None
    if any(x in low for x in ("iphone","galaxy","pixel","reno","realme","oneplus","redmi","poco")) and not re.search(r"\d",value):return None
    return value

def key_for(name):return re.sub(r"[^a-z0-9]+","",name.casefold())
def clean_reason(v):
    v=re.sub(r"\s+"," ",str(v or "")).strip()
    return (v[:177].rsplit(" ",1)[0]+"…") if len(v)>180 else (v or "Appears in a current independent buying guide.")
def amazon_url(name,tag):return f"https://www.amazon.in/s?{urllib.parse.urlencode({'k':name,'tag':tag})}"

def collect_category(category,web_results,tag):
    candidates={}; source_titles={}
    for position,result in enumerate(web_results,start=1):
        url=result.get("url") or ""; title=result.get("title") or "Independent buying guide"
        if not url:continue
        source_titles[url]=title
        for item in (result.get("json") or {}).get("products") or []:
            name=clean_name(item.get("name")); key=key_for(name) if name else ""
            if not key:continue
            e=candidates.setdefault(key,{"title":name,"reasons":[],"sources":[],"rankPoints":0})
            if url not in e["sources"]:e["sources"].append(url);e["rankPoints"]+=max(1,5-position)
            reason=clean_reason(item.get("reason"))
            if reason not in e["reasons"]:e["reasons"].append(reason)
    ranked=[]
    for e in candidates.values():
        n=len(e["sources"]); score=n*100+e["rankPoints"]; badge="Widely Recommended" if n>=3 else ("Popular Pick" if n==2 else "Worth a Look")
        ranked.append({"title":e["title"],"category":category["id"],"categoryLabel":category["label"],"icon":category["icon"],"reason":e["reasons"][0] if e["reasons"] else "Appears in a current independent buying guide.","badge":badge,"sourceCount":n,"sources":[{"url":u,"title":source_titles.get(u,"Independent source")} for u in e["sources"][:3]],"score":score,"amazonUrl":amazon_url(e["title"],tag)})
    ranked.sort(key=lambda x:(-x["score"],x["title"].casefold()));return ranked[:8]

def write_catalogue(products):
    payload={"generatedAt":datetime.now(timezone.utc).isoformat(),"method":"independent-web-discovery","note":"Product discovery only. Images are assigned later by the strict image-verification step; old image assignments are never carried forward.","categories":[{"id":c["id"],"label":c["label"],"icon":c["icon"]} for c in CATEGORIES],"products":products}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    tag=os.environ.get("AMAZON_PARTNER_TAG","").strip(); api_key=os.environ.get("FIRECRAWL_API_KEY","").strip()
    if not tag:print("ERROR: AMAZON_PARTNER_TAG is missing.",file=sys.stderr);return 2
    year=datetime.now(timezone.utc).year; all_products=[]
    for category in CATEGORIES:
        try:
            print(f"Discovering {category['label']}…"); results=search_category(category,year,api_key); picks=collect_category(category,results,tag);print(f"  {len(picks)} picks from {len(results)} independent pages");all_products.extend(picks)
        except Exception as exc:print(f"WARNING: {category['label']} discovery failed: {exc}",file=sys.stderr)
        time.sleep(1)
    if len(all_products)<8:print("WARNING: Not enough reliable products discovered; existing catalogue left unchanged.",file=sys.stderr);return 0
    write_catalogue(all_products);print(f"Generated {len(all_products)} image-free picks for strict verification.");return 0
if __name__=="__main__":raise SystemExit(main())
