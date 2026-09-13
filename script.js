const state={category:"all",query:""};let catalogue=null;
const container=document.getElementById("products-container");
const tabsWrap=document.getElementById("category-tabs");
const search=document.getElementById("product-search");
const clear=document.getElementById("clear-search");
const reset=document.getElementById("reset-filters");
const count=document.getElementById("results-count");
const mobileCount=document.getElementById("mobile-count");
const updated=document.getElementById("updated-label");

const badgeClass=b=>({Bestseller:"badge-bestseller","Well Reviewed":"badge-bestseller",Popular:"badge-hot",Trending:"badge-hot","Good Value":"badge-deal","Smart Pick":"badge-deal",New:"badge-new","Wired Pick":"badge-bestseller"})[b]||"badge-deal";
const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money=p=>p.displayPrice||((p.price!=null)?new Intl.NumberFormat("en-IN",{style:"currency",currency:p.currency||"INR",maximumFractionDigits:0}).format(p.price):"");
function reason(p){
 if(p.savingPercent>=10)return "A worthwhile offer with useful savings right now.";
 if(p.salesRank&&p.salesRank<=10000)return "A popular Amazon pick that is worth a closer look.";
 if(p.rating>=4.3)return "A well-rated option selected for everyday value.";
 return "A practical pick selected from current Amazon results.";
}
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
 const groups=new Map((catalogue.categories||[]).map(c=>[c.id,c]));
 container.innerHTML=(catalogue.categories||[]).map(cat=>{
   const items=products.filter(p=>p.category===cat.id);
   if(!items.length)return "";
   return '<section class="category-section" id="'+escapeHtml(cat.id)+'" data-category="'+escapeHtml(cat.id)+'"><div class="category-header"><div class="category-icon-wrap">'+escapeHtml(cat.icon||"🛍️")+'</div><span class="category-name">'+escapeHtml(cat.label)+'</span><span class="category-count">'+items.length+' picks</span></div><div class="products-grid">'+items.map(p=>{
     const badges='<span class="badge '+badgeClass(p.badge)+'">'+escapeHtml(p.badge||"Smart Pick")+'</span>'+(p.savingPercent>=10?'<span class="badge badge-deal">'+Math.round(p.savingPercent)+'% off</span>':"");
     const rating=p.rating?'<span>★ '+Number(p.rating).toFixed(1)+'</span>':"";
     const reviews=p.reviewCount?'<span>· '+Number(p.reviewCount).toLocaleString("en-IN")+' reviews</span>':"";
     const price=p.displayPrice?'<strong class="product-price">'+escapeHtml(p.displayPrice)+'</strong>':"";
     return '<article class="product-card"><div class="product-image-wrap"><img class="product-image" src="'+escapeHtml(p.image)+'" alt="'+escapeHtml(p.title)+'" loading="lazy" referrerpolicy="no-referrer"></div><div class="badge-row">'+badges+'</div><p class="product-name">'+escapeHtml(p.title)+'</p><div class="product-meta">'+rating+reviews+'</div>'+price+'<p class="product-why">'+escapeHtml(reason(p))+'</p><a class="product-buy" href="'+escapeHtml(p.amazonUrl)+'" target="_blank" rel="nofollow sponsored noopener">View deal on Amazon <span class="buy-arrow">→</span></a></article>';
   }).join("")+'</div></section>';
 }).join("")||'<div class="empty-state">No products are available yet. Run the Amazon catalogue workflow from GitHub Actions.</div>';
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
   catalogue=await r.json();
   renderTabs();renderProducts();setupSearch();render();
   const when=catalogue.generatedAt?new Date(catalogue.generatedAt):null;
   updated.textContent=when&&!Number.isNaN(when.valueOf())?"Updated "+when.toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Fresh shortlist";
 }catch(err){
   try{
     const fallback=await fetch("data/products.html?ts="+Date.now());
     if(!fallback.ok)throw err;
     container.innerHTML=await fallback.text();
     setupSearch();render();
     updated.textContent="Curated shortlist";
   }catch{
     container.innerHTML='<div class="empty-state">We could not load the picks right now. Please refresh and try again.</div>';
     count.textContent="Picks unavailable";setupSearch();
   }
 }
}
document.getElementById("year").textContent=new Date().getFullYear();
load();
