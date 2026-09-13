const state={category:"all",query:""};
let catalogue=null;
const container=document.getElementById("products-container");
const tabsWrap=document.getElementById("category-tabs");
const categoryCards=document.getElementById("category-cards");
const featured=document.getElementById("featured-products");
const search=document.getElementById("product-search");
const heroSearch=document.getElementById("hero-search");
const heroSearchButton=document.getElementById("hero-search-button");
const clear=document.getElementById("clear-search");
const reset=document.getElementById("reset-filters");
const count=document.getElementById("results-count");
const mobileCount=document.getElementById("mobile-count");
const updated=document.getElementById("updated-label");
const heroProductCount=document.getElementById("hero-product-count");
const heroCategoryCount=document.getElementById("hero-category-count");

const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const badgeClass=b=>({"Widely Recommended":"badge-bestseller","Popular Pick":"badge-hot","Worth a Look":"badge-deal"})[b]||"badge-deal";
const sourceLabel=p=>p.sourceCount>1?`${p.sourceCount} independent guides`:"Independent guide pick";
const visualForCategory=id=>`assets/visuals/${id}.svg`;
const visualImg=(id,label)=>`<img src="${escapeHtml(visualForCategory(id))}" alt="${escapeHtml(label)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block">`;
const productImg=(p,id,label)=>p.imageUrl?`<img src="${escapeHtml(p.imageUrl)}" alt="${escapeHtml(p.title)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${escapeHtml(visualForCategory(id))}'" style="width:100%;height:100%;object-fit:contain;display:block;background:#fff;padding:10px">`:visualImg(id,label);

function setCategory(category){
 state.category=category;
 document.querySelectorAll(".tab").forEach(el=>el.classList.toggle("active",el.dataset.category===category));
 document.querySelectorAll(".category-card").forEach(el=>el.classList.toggle("active",el.dataset.category===category));
 render();
 document.getElementById("deals")?.scrollIntoView({behavior:"smooth",block:"start"});
}

function renderCategoryNavigation(){
 const categories=catalogue.categories||[];
 tabsWrap.innerHTML=[{id:"all",label:"All",icon:""},...categories].map(c=>
   `<button class="tab ${c.id==="all"?"active":""}" data-category="${escapeHtml(c.id)}" type="button">${escapeHtml(c.icon?c.icon+" ":"")}${escapeHtml(c.label)}</button>`
 ).join("");
 tabsWrap.querySelectorAll(".tab").forEach(tab=>tab.addEventListener("click",()=>setCategory(tab.dataset.category)));

 categoryCards.innerHTML=categories.map(c=>{
   const n=(catalogue.products||[]).filter(p=>p.category===c.id).length;
   return `<button class="category-card" data-category="${escapeHtml(c.id)}" type="button"><span class="category-icon">${escapeHtml(c.icon||"🛍️")}</span><span><strong>${escapeHtml(c.label)}</strong><span>${n} current ${n===1?"pick":"picks"}</span></span></button>`;
 }).join("");
 categoryCards.querySelectorAll(".category-card").forEach(card=>card.addEventListener("click",()=>setCategory(card.dataset.category)));
}

function renderFeatured(){
 const picks=[...(catalogue.products||[])].sort((a,b)=>(b.score||0)-(a.score||0)).slice(0,3);
 featured.innerHTML=picks.length?picks.map(p=>
   `<article class="featured-card"><div style="height:150px;border-radius:16px;overflow:hidden;margin-bottom:14px;background:#fff">${productImg(p,p.category,p.categoryLabel||p.category)}</div><div class="featured-top"><span class="featured-symbol">${escapeHtml(p.icon||"🛍️")}</span><span class="featured-badge">${escapeHtml(p.badge||"Worth a Look")}</span></div><h3>${escapeHtml(p.title)}</h3><p>${escapeHtml(p.reason||"Appears in a current independent buying guide.")}</p><a href="${escapeHtml(p.amazonUrl)}" target="_blank" rel="nofollow sponsored noopener">Check on Amazon <span>→</span></a></article>`
 ).join(""):'<div class="empty-state">Featured picks will appear after the next catalogue refresh.</div>';
}

function renderProducts(){
 const products=catalogue.products||[];
 container.innerHTML=(catalogue.categories||[]).map(cat=>{
   const items=products.filter(p=>p.category===cat.id);
   if(!items.length)return "";
   return `<section class="category-section" id="${escapeHtml(cat.id)}" data-category="${escapeHtml(cat.id)}"><div class="category-header"><div class="category-icon-wrap">${escapeHtml(cat.icon||"🛍️")}</div><span class="category-name">${escapeHtml(cat.label)}</span><span class="category-count">${items.length} picks</span></div><div class="products-grid">${items.map(p=>
     `<article class="product-card"><div class="product-visual">${productImg(p,cat.id,`${p.title} category artwork`)}</div><div class="badge-row"><span class="badge ${badgeClass(p.badge)}">${escapeHtml(p.badge||"Worth a Look")}</span></div><p class="product-name">${escapeHtml(p.title)}</p><div class="product-meta"><span>✓ ${escapeHtml(sourceLabel(p))}</span></div><p class="product-why">${escapeHtml(p.reason||"Appears in a current independent buying guide.")}</p><a class="product-buy" href="${escapeHtml(p.amazonUrl)}" target="_blank" rel="nofollow sponsored noopener">Check on Amazon <span class="buy-arrow">→</span></a></article>`
   ).join("")}</div></section>`;
 }).join("")||'<div class="empty-state">No fresh picks are available yet. Please check back soon.</div>';
}

function render(){
 const q=state.query.trim().toLowerCase();let visible=0;
 document.querySelectorAll(".category-section").forEach(section=>{
   const cat=section.dataset.category;let matches=0;
   section.querySelectorAll(".product-card").forEach(card=>{
     const ok=(state.category==="all"||state.category===cat)&&(!q||card.textContent.toLowerCase().includes(q));
     card.hidden=!ok;if(ok){matches++;visible++}
   });
   section.hidden=matches===0;
 });
 count.textContent=visible?`${visible} curated ${visible===1?"pick":"picks"}`:"No picks found";
 mobileCount.textContent=`${visible} ${visible===1?"pick":"picks"}`;
 reset.style.display=(state.category!=="all"||q)?"block":"none";
 clear.style.display=q?"block":"none";
}

function applySearch(value,scroll=true){state.query=value;search.value=value;heroSearch.value=value;render();if(scroll)document.getElementById("deals")?.scrollIntoView({behavior:"smooth",block:"start"});}
function setupSearch(){
 search.addEventListener("input",e=>{state.query=e.target.value;heroSearch.value=e.target.value;render()});
 heroSearch.addEventListener("input",e=>{state.query=e.target.value;search.value=e.target.value;render()});
 heroSearch.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();applySearch(heroSearch.value)}});
 heroSearchButton.addEventListener("click",e=>{e.preventDefault();applySearch(heroSearch.value)});
 clear.addEventListener("click",()=>{applySearch("",false);search.focus()});
 reset.addEventListener("click",()=>{state.category="all";state.query="";search.value="";heroSearch.value="";document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.category==="all"));document.querySelectorAll(".category-card").forEach(t=>t.classList.remove("active"));render()});
}

async function load(){
 try{
   const r=await fetch("data/products.json?ts="+Date.now(),{cache:"no-store"});
   if(!r.ok)throw new Error("generated catalogue unavailable");
   catalogue=await r.json();
   heroProductCount.textContent=(catalogue.products||[]).length;
   heroCategoryCount.textContent=(catalogue.categories||[]).filter(c=>(catalogue.products||[]).some(p=>p.category===c.id)).length;
   renderCategoryNavigation();renderFeatured();renderProducts();setupSearch();render();
   const when=catalogue.generatedAt?new Date(catalogue.generatedAt):null;
   updated.textContent=when&&!Number.isNaN(when.valueOf())?"Updated "+when.toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Fresh shortlist";
 }catch(err){
   heroProductCount.textContent="—";heroCategoryCount.textContent="—";
   categoryCards.innerHTML='<div class="empty-state">Categories will appear when the catalogue loads.</div>';
   featured.innerHTML='<div class="empty-state">Featured picks are temporarily unavailable.</div>';
   try{
     const fallback=await fetch("data/products.html?ts="+Date.now());
     if(!fallback.ok)throw err;
     container.innerHTML=await fallback.text();setupSearch();render();updated.textContent="Curated shortlist";
   }catch{
     container.innerHTML='<div class="empty-state">We could not load the picks right now. Please refresh and try again.</div>';count.textContent="Picks unavailable";setupSearch();
   }
 }
}

document.getElementById("year").textContent=new Date().getFullYear();
load();
