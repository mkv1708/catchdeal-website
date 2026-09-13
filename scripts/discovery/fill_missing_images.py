import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CATALOGUE=Path("data/products.json")
SEARCH_URL="https://api.firecrawl.dev/v2/search"
BAD_WORDS=("street","road","building","landscape","cityscape","selfie","portrait","sample photo","camera sample","shot on","wallpaper","screenshot","logo","icon","case","cover","screen protector","poster","advertisement")
BLOCKED=("amazon.in","amazon.com","flipkart.com","meesho.com","ebay.com","walmart.com","aliexpress.com","temu.com")
STOP={"the","and","with","for","edition","wireless","smart","phone","smartphone","black","white","truly","product","official","image"}

def tokens(v): return [x for x in re.findall(r"[a-z0-9]+",str(v).casefold()) if len(x)>1 and x not in STOP]
def clean_name(v):
    v=re.sub(r"\s+"," ",str(v or "")).strip(" -–—|:;,.\t\n"); low=v.casefold()
    if len(v)<5 or len(v)>100 or len(v.split())<2:return None
    if low.startswith(("best ","top ","our picks","buying guide")):return None
    if any(x in low for x in ("iphone","galaxy","pixel","reno","realme","oneplus","redmi","poco","cmf phone")) and not re.search(r"\d",v):return None
    return v

def exact(t,text): return bool(re.search(r"(?<![a-z0-9])"+re.escape(t)+r"(?![a-z0-9])",text.casefold()))
def relevant(name,title):
    wanted=tokens(name); hay=title.casefold()
    if not wanted or any(x in hay for x in BAD_WORDS):return False
    model=[x for x in wanted if any(c.isdigit() for c in x)]
    if model and not all(exact(x,hay) for x in model):return False
    if not exact(wanted[0],hay):return False
    need=max(2,(len(wanted)*2+2)//3)
    return sum(exact(x,hay) for x in wanted)>=min(need,len(wanted))

def post(payload,key,retries=3):
    body=json.dumps(payload).encode(); headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"}
    for n in range(retries):
        try:
            req=urllib.request.Request(SEARCH_URL,data=body,headers=headers,method="POST")
            with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503,504) and n<retries-1:time.sleep(2**n);continue
            raise

def find_image(name,key):
    payload={"query":f'"{name}" product image',"limit":20,"sources":[{"type":"images"}],"country":"IN","excludeDomains":list(BLOCKED)}
    data=post(payload,key)
    results=(data.get("data") or {}).get("images") or []
    best=None; score=-1
    for r in results:
        title=str(r.get("title") or ""); image=str(r.get("imageUrl") or ""); source=str(r.get("url") or "")
        if not image.startswith("https://") or not source.startswith("http"):continue
        host=urllib.parse.urlparse(source).netloc.casefold().removeprefix("www.")
        if any(host==d or host.endswith("."+d) for d in BLOCKED):continue
        w=int(r.get("imageWidth") or 0); h=int(r.get("imageHeight") or 0)
        if w and h and (w<300 or h<300):continue
        if not relevant(name,title):continue
        wanted=tokens(name); s=sum(10 for x in wanted if exact(x,title))
        if s>score: best={"imageUrl":image,"imageSourceUrl":source,"imageSourceTitle":title[:160] or host}; score=s
    return best

def main():
    key=os.environ.get("FIRECRAWL_API_KEY","").strip()
    if not key: print("FIRECRAWL_API_KEY missing; leaving live catalogue unchanged."); CATALOGUE.unlink(missing_ok=True); return 0
    if not CATALOGUE.exists():return 0
    data=json.loads(CATALOGUE.read_text(encoding="utf-8")); products=data.get("products") or []
    publish=[]
    print(f"Firecrawl image search: checking {len(products)} exact product names; Amazon/major retailers excluded.")
    for i,p in enumerate(products,1):
        name=clean_name(p.get("title"))
        if not name: print(f"  rejected name {i}: {p.get('title')}"); continue
        p["title"]=name
        for k in ("imageUrl","imageSourceUrl","imageSourceTitle"):p.pop(k,None)
        try: image=find_image(name,key)
        except Exception as e: print(f"  image search failed {i}/{len(products)}: {name}: {e}"); image=None
        if image: p.update(image); publish.append(p); print(f"  matched {i}/{len(products)}: {name}")
        else: print(f"  no strong match {i}/{len(products)}: {name}")
        time.sleep(.35)
    if len(publish)<8:
        print(f"Only {len(publish)} strong image matches; refusing to replace live catalogue."); CATALOGUE.unlink(missing_ok=True); return 0
    data["products"]=publish
    data["note"]="Product images are discovered with Firecrawl image search using exact brand/model matching. Amazon and major retailer domains are excluded; weak/contextual matches are rejected. Source page metadata is retained for review."
    CATALOGUE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Publishing {len(publish)} products with strong image-search matches.")
    return 0
if __name__=="__main__":raise SystemExit(main())
