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
const navSearch=document.getElementById("nav-search");
const clear=document.getElementById("clear-search");
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
    ?`<div class="empty-state">
        <h3>Explore more options on Amazon</h3>
        <p>Continue your search for “${escapeHtml(state.query.trim())}” on Amazon India.</p>
        <a class="product-buy" href="https://www.amazon.in/s?k=${encodeURIComponent(state.query.trim()).replace(/'/g,"%27")}&amp;tag=facebook011b-21" target="_blank" rel="nofollow sponsored noopener">See results on Amazon <span>↗</span></a>
        <small>Affiliate link · Opens Amazon India</small>
      </div>`
    :'<div class="empty-state">Explore more products by choosing another category.</div>';
  count.textContent=filtered.length
    ?`Showing ${offset+1}–${offset+shown.length} of ${filtered.length} products`
    :q?"Explore more options on Amazon":"Explore other categories";
  mobileCount.textContent=filtered.length
    ?`${filtered.length} ${filtered.length===1?"product":"products"}`
    :q?"Explore on Amazon":"Explore categories";
  reset.style.display=(state.category!=="all"||q)?"block":"none";
  clear.style.display=q?"block":"none";
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

function applySearch(
  value,
  scroll=true
){

  state.query=value;
  state.page=1;

  search.value=value;

  if(navSearch){
    navSearch.value=value;
  }

  render();


  if(scroll){

    document
      .getElementById("deals")
      ?.scrollIntoView({
        behavior:"smooth",
        block:"start"
      });

  }
}


function setupSearch(){

  search.addEventListener(
    "input",
    e=>{

      state.query=e.target.value;
      state.page=1;

      if(navSearch){
        navSearch.value=e.target.value;
      }

      render();

    }
  );


  if(navSearch){

    navSearch.addEventListener(
      "input",
      e=>{

        state.query=e.target.value;
      state.page=1;

        search.value=e.target.value;

        render();

      }
    );


    navSearch.addEventListener(
      "keydown",
      e=>{

        if(e.key==="Enter"){

          e.preventDefault();

          applySearch(
            navSearch.value
          );

        }

      }
    );

  }


  clear.addEventListener(
    "click",
    ()=>{

      applySearch(
        "",
        false
      );

      search.focus();

    }
  );


  reset.addEventListener(
    "click",
    ()=>{

      state.category="all";
      state.page=1;
      state.query="";

      search.value="";

      if(navSearch){
        navSearch.value="";
      }


      document
        .querySelectorAll(".tab")
        .forEach(t=>
          t.classList.toggle(
            "active",
            t.dataset.category==="all"
          )
        );


      document
        .querySelectorAll(".category-card")
        .forEach(t=>
          t.classList.remove("active")
        );


      render();

    }
  );
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