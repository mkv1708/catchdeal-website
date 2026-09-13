const state={category:"all",query:""};let catalogue=null;
const container=document.getElementById("products-container");
const tabsWrap=document.getElementById("category-tabs");
const search=document.getElementById("product-search");
const clear=document.getElementById("clear-search");
const reset=document.getElementById("reset-filters");
const count=document.getElementById("results-count");
const mobileCount=document.getElementById("mobile-count");
const updated=document.getElementById("updated-label");

const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const badgeClass=b=>({"Widely Recommended":"badge-bestseller","Popular Pick":"badge-hot","Worth a Look":"badge-deal"})[b]||"badge-deal";

function renderTabs(){
 const cats=[{id:"all",label:"All",icon:""}].concat(catalogue.categories||[]);
 tabsWrap.innerHTML=cats.map(c=>'<button class="tab '+(c.id==="all"?"active":"")+'" data-category="'+escapeHtml(c.id)+'" type="button">'+escapeHtml(c.icon?c.icon+" ":"")+escapeHtml(c.label)+'</button>').join("");
 tabsWrap.querySelectorAll(".tab").forEach(tab=>tab.addEventListener("click",()=>{
   tabsWrap.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
   tab.classList.add("active");state.category=tab.dataset.category;render();
 }));
}

function renderProducts(){
 const products=catalogue.products||[];
 container.innerHTML=(catalogue.categories||[]).map(cat=>{
   const items=products.filter(p=>p.category===cat.id);
   if(!items.length)return "";
   return '<section class="category-section" id="'+escapeHtml(cat.id)+'" data-category="'+escapeHtml(cat.id)+'"><div class="category-header"><div class="category-icon-wrap">'+escapeHtml(cat.icon||"🛍️")+'</div><span class="category-name">'+escapeHtml(cat.label)+'</span><span class="category-count">'+items.length+' picks</span></div><div class="products-grid">'+items.map(p=>{
     const sourceText=p.sourceCount>1?p.sourceCount+' independent guides':'Independent guide pick';
     return '<article class="product-card"><div class="product-visual" aria-hidden="true"><span>'+escapeHtml(p.icon||cat.icon||"🛍️")+'</span></div><div class="badge-row"><span class="badge '+badgeClass(p.badge)+'">'+escapeHtml(p.badge||"Worth a Look")+'</span></div><p class="product-name">'+escapeHtml(p.title)+'</p><div class="product-meta"><span>✓ '+escapeHtml(sourceText)+'</span></div><p class="product-why">'+escapeHtml(p.reason||"Appears in a current independent buying guide.")+'</p><a class="product-buy" href="'+escapeHtml(p.amazonUrl)+'" target="_blank" rel="nofollow sponsored noopener">Search on Amazon <span class="buy-arrow">→</span></a></article>';
   }).join("")+'</div></section>';
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
 count.textContent=visible?visible+" curated picks":"No picks found";
 mobileCount.textContent=visible+" "+(visible===1?"pick":"picks");
 reset.style.display=(state.category!=="all"||q)?"block":"none";
 clear.style.display=q?"block":"none";
}

function setupSearch(){
 search.addEventListener("input",e=>{state.query=e.target.value;render()});
 clear.addEventListener("click",()=>{search.value="";state.query="";search.focus();render()});
 reset.addEventListener("click",()=>{state.category="all";state.query="";search.value="";tabsWrap.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.category==="all"));render()});
}

async function load(){
 try{
   const r=await fetch("data/products.json?ts="+Date.now(),{cache:"no-store"});
   if(!r.ok)throw new Error("generated catalogue unavailable");
   catalogue=await r.json();renderTabs();renderProducts();setupSearch();render();
   const when=catalogue.generatedAt?new Date(catalogue.generatedAt):null;
   updated.textContent=when&&!Number.isNaN(when.valueOf())?"Updated "+when.toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Fresh shortlist";
 }catch(err){
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
