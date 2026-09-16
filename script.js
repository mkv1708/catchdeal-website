const state={category:"all",query:""};
let catalogue=null;

const container=document.getElementById("products-container");
const tabsWrap=document.getElementById("category-tabs");
const categoryCards=document.getElementById("category-cards");
const featured=document.getElementById("featured-products");
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

function renderHero(){

  const products=[...(catalogue.products||[])];

  const withImages=products
    .filter(p=>p.imageUrl)
    .sort((a,b)=>{
      const rankA=a.rank??999;
      const rankB=b.rank??999;
      return rankA-rankB;
    });


  const picks=(
    withImages.length>=3
      ?withImages
      :products
  ).slice(0,3);


  heroShowcase.innerHTML=picks
    .map(p=>`
      <a
        class="hero-product"
        href="${escapeHtml(p.amazonUrl)}"
        target="_blank"
        rel="nofollow sponsored noopener"
        aria-label="View ${escapeHtml(p.title)} on Amazon"
      >
        ${productImg(p,p.category)}
      </a>
    `)
    .join("");
}


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

function renderFeatured(){

  const products=[
    ...(catalogue.products||[])
  ];


  // Prioritize the best visible Amazon rank.

  const picks=products
    .sort((a,b)=>{

      const imageA=a.imageUrl?1:0;
      const imageB=b.imageUrl?1:0;

      if(imageA!==imageB){
        return imageB-imageA;
      }

      const rankA=a.rank??999;
      const rankB=b.rank??999;

      return rankA-rankB;

    })
    .slice(0,5);


  featured.innerHTML=picks.length
    ?picks.map(p=>`

      <article class="featured-card">

        <div class="featured-visual">
          ${productImg(p,p.category)}
        </div>

        <div class="featured-body">

          <span class="featured-badge ${badgeClass(p)}">
            ${escapeHtml(rankLabel(p))}
          </span>

          <h3>
            ${escapeHtml(p.title)}
          </h3>

          <div class="featured-meta">
            ★ ${escapeHtml(ratingLabel(p))}
          </div>

          <p>
            ${escapeHtml(
              p.categoryLabel||
              "Amazon India Best Seller"
            )}
          </p>

          <a
            class="buy-button"
            href="${escapeHtml(p.amazonUrl)}"
            target="_blank"
            rel="nofollow sponsored noopener"
          >
            Buy Now <span>→</span>
          </a>

        </div>

      </article>

    `).join("")

    :'<div class="empty-state">Top picks are currently unavailable.</div>';
}


// ==========================================================
// ALL PRODUCTS
// ==========================================================

function renderProducts(){

  const products=catalogue.products||[];


  container.innerHTML=(catalogue.categories||[])
    .map(cat=>{

      const items=products
        .filter(p=>p.category===cat.id);


      if(!items.length){
        return "";
      }


      return `

        <section
          class="category-section"
          id="${escapeHtml(cat.id)}"
          data-category="${escapeHtml(cat.id)}"
        >

          <div class="category-header">

            <div class="category-icon-wrap">
              ${escapeHtml(cat.icon||"🛍️")}
            </div>

            <span class="category-name">
              ${escapeHtml(cat.label)}
            </span>

            <span class="category-count">
              ${items.length} products
            </span>

          </div>


          <div class="products-grid">

            ${items.map(p=>`

              <article class="product-card">

                <div class="product-visual">
                  ${productImg(p,cat.id)}
                </div>


                <div class="product-body">

                  <span class="badge ${badgeClass(p)}">
                    ${escapeHtml(rankLabel(p))}
                  </span>


                  <p class="product-name">
                    ${escapeHtml(p.title)}
                  </p>


                  <div class="product-meta">
                    ★ ${escapeHtml(ratingLabel(p))}
                  </div>


                  <p class="product-why">
                    ${escapeHtml(
                      p.categoryLabel||
                      cat.label
                    )}
                  </p>


                  <a
                    class="product-buy"
                    href="${escapeHtml(p.amazonUrl)}"
                    target="_blank"
                    rel="nofollow sponsored noopener"
                  >
                    Buy Now <span>→</span>
                  </a>

                </div>

              </article>

            `).join("")}

          </div>

        </section>
      `;

    })
    .join("")

    ||'<div class="empty-state">No products are available yet.</div>';
}


// ==========================================================
// FILTER PRODUCTS
// ==========================================================

function render(){

  const q=state.query
    .trim()
    .toLowerCase();

  let visible=0;


  document
    .querySelectorAll(".category-section")
    .forEach(section=>{

      const cat=section.dataset.category;

      let matches=0;


      section
        .querySelectorAll(".product-card")
        .forEach(card=>{

          const categoryMatch=
            state.category==="all"||
            state.category===cat;


          const searchMatch=
            !q||
            card.textContent
              .toLowerCase()
              .includes(q);


          const ok=
            categoryMatch&&
            searchMatch;


          card.hidden=!ok;


          if(ok){
            matches++;
            visible++;
          }

        });


      section.hidden=matches===0;

    });


  count.textContent=
    visible
      ?`${visible} products`
      :"No products found";


  mobileCount.textContent=
    `${visible} ${
      visible===1
        ?"product"
        :"products"
    }`;


  reset.style.display=
    (
      state.category!=="all"||
      q
    )
      ?"block"
      :"none";


  clear.style.display=
    q
      ?"block"
      :"none";
}


// ==========================================================
// SEARCH
// ==========================================================

function applySearch(
  value,
  scroll=true
){

  state.query=value;

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


    renderHero();

    renderCategoryNavigation();

    renderFeatured();

    renderProducts();

    setupSearch();

    render();


    const when=
      catalogue.generatedAt
        ?new Date(catalogue.generatedAt)
        :null;


    updated.textContent=
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


    heroShowcase.innerHTML="";


    categoryCards.innerHTML=
      '<div class="empty-state">Categories unavailable.</div>';


    featured.innerHTML=
      '<div class="empty-state">Top picks are temporarily unavailable.</div>';


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