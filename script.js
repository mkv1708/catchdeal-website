const state={category:"all",query:"",page:1};
const PAGE_SIZE=15;
let catalogue=null;

const container=document.getElementById("products-container");
const tabsWrap=document.getElementById("category-tabs");
const categoryCards=document.getElementById("category-cards");
const featured=document.getElementById("featured-products");
const pagination=document.getElementById("pagination");
const heroShowcase=document.getElementById("hero-showcase");
const search=document.getElementById("product-search");
const searchForm=document.getElementById("search-form");

const reset=document.getElementById("reset-filters");
const count=document.getElementById("results-count");
const mobileCount=document.getElementById("mobile-count");
const updated=document.getElementById("updated-label");


const escapeHtml=s=>String(s??"").replace(
  /[&<>"']/g,
  c=>({
    "&":"&amp;",
    "<":"&lt;",
    ">":"&gt;",
    '"':"&quot;",
    "'":"&#39;"
  }[c])
);


const visualForCategory=id=>`assets/visuals/${id}.svg`;


const productImg=(p,id)=>p.imageUrl
 ?`<img src="${escapeHtml(p.imageUrl)}"
        alt="${escapeHtml(p.title)}"
        loading="lazy"
        referrerpolicy="no-referrer"
        onerror="this.onerror=null;this.src='${escapeHtml(visualForCategory(id))}'">`
 :`<img src="${escapeHtml(visualForCategory(id))}"
        alt="${escapeHtml(p.title)}"
        loading="lazy">`;


// ==========================================================
// COLLECTOR DATA HELPERS
// ==========================================================

const rankLabel=p=>{
  if(p.rank){
    return `#${p.rank} Best Seller`;
  }

  return "Amazon Best Seller";
};


const ratingLabel=p=>{
  if(p.rating && p.rating!=="N/A"){
    return p.rating;
  }

  return "Rating unavailable";
};


const badgeClass=p=>{
  if(p.rank===1){
    return "badge-bestseller";
  }

  if(p.rank && p.rank<=3){
    return "badge-hot";
  }

  return "badge-deal";
};


// ==========================================================
// CATEGORY SELECTION
// ==========================================================

function setCategory(category){

  state.category=category;
  state.page=1;

  document
    .querySelectorAll(".tab")
    .forEach(el=>
      el.classList.toggle(
        "active",
        el.dataset.category===category
      )
    );

  document
    .querySelectorAll(".category-card")
    .forEach(el=>
      el.classList.toggle(
        "active",
        el.dataset.category===category
      )
    );

  render();

  document
    .getElementById("deals")
    ?.scrollIntoView({
      behavior:"smooth",
      block:"start"
    });
}


// ==========================================================
// HERO PRODUCTS
// ==========================================================

// ==========================================================
// CATEGORY NAVIGATION
// ==========================================================

function renderCategoryNavigation(){

  const categories=(catalogue.categories||[])
    .filter(c=>
      (catalogue.products||[])
        .some(p=>p.category===c.id)
    );


  tabsWrap.innerHTML=[
    {
      id:"all",
      label:"All",
      icon:""
    },
    ...categories
  ]
    .map(c=>`
      <button
        class="tab ${c.id==="all"?"active":""}"
        data-category="${escapeHtml(c.id)}"
        type="button"
      >
        ${escapeHtml(c.icon?c.icon+" ":"")}
        ${escapeHtml(c.label)}
      </button>
    `)
    .join("");


  tabsWrap
    .querySelectorAll(".tab")
    .forEach(tab=>
      tab.addEventListener(
        "click",
        ()=>setCategory(tab.dataset.category)
      )
    );


  categoryCards.innerHTML=categories
    .map(c=>{

      const items=(catalogue.products||[])
        .filter(p=>p.category===c.id);

      const sample=
        items.find(p=>p.imageUrl)||
        items[0];


      return `
        <button
          class="category-card"
          data-category="${escapeHtml(c.id)}"
          type="button"
        >

          <span class="category-thumb">
            ${
              sample
                ?productImg(sample,c.id)
                :escapeHtml(c.icon||"🛍️")
            }
          </span>

          <strong>
            ${escapeHtml(c.label)}
          </strong>

          <small>
            ${items.length} products
          </small>

        </button>
      `;
    })
    .join("");


  categoryCards
    .querySelectorAll(".category-card")
    .forEach(card=>
      card.addEventListener(
        "click",
        ()=>setCategory(card.dataset.category)
      )
    );
}


// ==========================================================
// FEATURED / TOP PICKS
// ==========================================================

// Look up a representative picture only for searches without catalogue matches.
// Commons pictures are illustrations, not Amazon product listings.
let pictureRequest=0;
let pictureTimer=null;
const pictureCache=new Map();

function loadSearchPicture(term){
  const request=++pictureRequest;
  clearTimeout(pictureTimer);
  const slot=document.getElementById("search-picture");
  if(!slot||!term.trim())return;
  const key=term.trim().toLowerCase();
  const show=picture=>{
    if(request!==pictureRequest||!document.getElementById("search-picture"))return;
    if(!picture){slot.innerHTML='<span class="search-picture-placeholder" aria-hidden="true">🛍️</span>';return;}
    slot.innerHTML=`<img src="${escapeHtml(picture.url)}" alt="Illustration related to ${escapeHtml(term)}" loading="lazy" referrerpolicy="no-referrer"><a href="${escapeHtml(picture.page)}" target="_blank" rel="noopener noreferrer">Image source and credits ↗</a>`;
    slot.querySelector("img").addEventListener("error",()=>{if(request===pictureRequest)slot.innerHTML='<span class="search-picture-placeholder" aria-hidden="true">🛍️</span>';},{once:true});
  };
  if(pictureCache.has(key)){show(pictureCache.get(key));return;}
  pictureTimer=setTimeout(async()=>{
    try{
      const url=new URL("https://commons.wikimedia.org/w/api.php");
      url.search=new URLSearchParams({
        action:"query",format:"json",origin:"*",generator:"search",
        gsrsearch:term.trim(),gsrnamespace:"6",gsrlimit:"12",
        prop:"imageinfo",iiprop:"url|extmetadata",iiurlwidth:"480"
      }).toString();
      const response=await fetch(url.toString());
      if(!response.ok)throw new Error("Picture search unavailable");
      const data=await response.json();
      const words=key.match(/[a-z0-9]+/g)?.filter(word=>word.length>2)||[];
      const pictures=Object.values(data.query?.pages||{}).filter(page=>{
        const name=page.title?.replace(/^File:/i,"").replace(/[_-]/g," ").toLowerCase()||"";
        const info=page.imageinfo?.[0];
        const license=info?.extmetadata?.LicenseShortName?.value||"";
        return words.length>0&&words.every(word=>name.includes(word))&&
          /^(cc0|public domain|pd)/i.test(license)&&
          /^https:\/\//.test(info?.thumburl||"")&&
          /^https:\/\//.test(info?.descriptionurl||"");
      });
      const found=pictures[0]?.imageinfo?.[0];
      const picture=found?{url:found.thumburl,page:found.descriptionurl}:null;
      pictureCache.set(key,picture);
      show(picture);
    }catch(error){show(null);}
  },450);
}

// ==========================================================
// ALL PRODUCTS
// ==========================================================

function render(){
  if(!catalogue)return;
  const q=state.query.trim().toLowerCase();
  const filtered=catalogue.products.filter(p=>
    (state.category==="all"||p.category===state.category)&&
    (!q||[p.title,p.categoryLabel,p.category].some(v=>String(v||"").toLowerCase().includes(q)))
  );
  const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
  state.page=Math.min(Math.max(1,state.page),pages);
  const offset=(state.page-1)*PAGE_SIZE;
  const shown=filtered.slice(offset,offset+PAGE_SIZE);
  const categories=new Map(catalogue.categories.map(c=>[c.id,c]));
  container.innerHTML=shown.length?'<div class="products-grid">'+shown.map(p=>{
    const cat=categories.get(p.category)||{label:p.categoryLabel||"Products",icon:"🛍️"};
    return `<article class="product-card">
      <div class="product-visual">${productImg(p,p.category)}</div>
      <div class="product-body">
        <span class="badge ${badgeClass(p)}">${escapeHtml(rankLabel(p))}</span>
        <p class="product-name">${escapeHtml(p.title)}</p>
        <div class="product-meta">★ ${escapeHtml(ratingLabel(p))}</div>
        <p class="product-why">${escapeHtml(cat.label)}</p>
        <a class="product-buy" href="${escapeHtml(p.amazonUrl)}" target="_blank" rel="nofollow sponsored noopener">Buy Now <span>→</span></a>
      </div>
    </article>`;
  }).join("")+'</div>':q
    ?`<div class="empty-state search-fallback">
        <div id="search-picture" class="search-picture" aria-label="Related product illustration"><span class="search-picture-placeholder" aria-hidden="true">🛍️</span></div>
        <div class="search-fallback-copy">
        <h3>Explore more options on Amazon</h3>
        <p>Continue your search for “${escapeHtml(state.query.trim())}” on Amazon India.</p>
        <a class="product-buy" href="https://www.amazon.in/s?k=${encodeURIComponent(state.query.trim()).replace(/'/g,"%27")}&amp;tag=catchdeal07-21" target="_blank" rel="nofollow sponsored noopener">See results on Amazon <span>↗</span></a>
        </div>
      </div>`
    :'<div class="empty-state">Explore more products by choosing another category.</div>';
  if(!shown.length&&q)loadSearchPicture(state.query.trim());
  else{++pictureRequest;clearTimeout(pictureTimer);}
  count.textContent=filtered.length
    ?`Showing ${offset+1}–${offset+shown.length} of ${filtered.length} products`
    :q?"Explore more options on Amazon":"Explore other categories";
  mobileCount.textContent=filtered.length
    ?`${filtered.length} ${filtered.length===1?"product":"products"}`
    :q?"Explore on Amazon":"Explore categories";
  reset.style.display=(state.category!=="all"||q)?"block":"none";
  pagination.innerHTML=filtered.length>PAGE_SIZE
    ?`<button type="button" data-page="${state.page-1}" ${state.page===1?"disabled":""}>← Previous</button>
      <span>Page ${state.page} of ${pages}</span>
      <button type="button" data-page="${state.page+1}" ${state.page===pages?"disabled":""}>Next →</button>`:"";
  pagination.querySelectorAll("button[data-page]").forEach(button=>
    button.addEventListener("click",()=>{
      state.page=Number(button.dataset.page);
      render();
      document.getElementById("deals").scrollIntoView({behavior:"smooth",block:"start"});
    })
  );
}


// ==========================================================
// SEARCH
// ==========================================================

function applySearch(value,scroll=true){
  state.query=value;
  state.category="all";
  state.page=1;
  search.value=value;
  document.querySelectorAll(".tab").forEach(tab=>
    tab.classList.toggle("active",tab.dataset.category==="all")
  );
  document.querySelectorAll(".category-card").forEach(card=>card.classList.remove("active"));
  render();
  if(scroll)document.getElementById("deals")?.scrollIntoView({behavior:"smooth",block:"start"});
}

function setupSearch(){
  search.addEventListener("input",event=>applySearch(event.target.value,false));
  searchForm.addEventListener("submit",event=>{
    event.preventDefault();
    applySearch(search.value);
  });
  document.querySelectorAll("[data-search-term]").forEach(button=>
    button.addEventListener("click",()=>applySearch(button.dataset.searchTerm))
  );
  reset.addEventListener("click",()=>applySearch(""));
}


// ==========================================================
// LOAD COLLECTOR DATA
// ==========================================================

async function load(){

  try{

    const r=await fetch(
      "data/products.json?ts="+
      Date.now(),
      {
        cache:"no-store"
      }
    );


    if(!r.ok){

      throw new Error(
        "Product catalogue unavailable"
      );

    }


    catalogue=await r.json();


    if(
      !Array.isArray(catalogue.products)||
      !Array.isArray(catalogue.categories)
    ){

      throw new Error(
        "Invalid product catalogue"
      );

    }



    renderCategoryNavigation();



    setupSearch();

    render();


    const when=
      catalogue.generatedAt
        ?new Date(catalogue.generatedAt)
        :null;


    if(updated) updated.textContent=
      when&&!Number.isNaN(when.valueOf())
        ?"Updated "+
          when.toLocaleDateString(
            "en-IN",
            {
              day:"numeric",
              month:"short"
            }
          )
        :"Fresh products";


    console.log(
      `CatchDeal loaded ${catalogue.products.length} products`
    );

  }
  catch(err){

    console.error(
      "Unable to load CatchDeal products:",
      err
    );




    categoryCards.innerHTML=
      '<div class="empty-state">Categories unavailable.</div>';




    container.innerHTML=
      '<div class="empty-state">We could not load products right now.</div>';


    count.textContent=
      "Products unavailable";

  }

}


// ==========================================================
// START
// ==========================================================

document.getElementById(
  "year"
).textContent=
  new Date().getFullYear();


load();