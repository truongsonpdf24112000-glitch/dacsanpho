/**
 * Đặc Sản Phố — Search & Filter Engine v3.0
 * Features: fuzzy search, suggestions dropdown, URL state, keyboard nav
 * Zero dependencies, plain JS
 */
(function () {
  "use strict";

  // ── State ──
  let dishes = [];
  let loaded = false;
  let currentProvince = ""; // scoped search on province pages

  // ── Fuzzy scoring ──
  function fuzzyScore(text, query) {
    if (!text || !query) return 0;
    const t = text.toLowerCase();
    const q = query.toLowerCase();

    // Exact match boost
    if (t === q) return 100;
    if (t.startsWith(q)) return 80;

    // Substring match
    const idx = t.indexOf(q);
    if (idx !== -1) return 70 - idx * 0.1;

    // Fuzzy: all query chars appear in order?
    let qi = 0;
    let score = 0;
    let consecutive = 0;
    for (let i = 0; i < t.length && qi < q.length; i++) {
      if (t[i] === q[qi]) {
        score += 5 + consecutive * 3;
        consecutive++;
        qi++;
      } else {
        consecutive = 0;
        score -= 0.5;
      }
    }
    if (qi !== q.length) return 0; // not all chars matched
    return Math.max(1, score);
  }

  function searchDishes(query, filters) {
    if (!query && !filters) return dishes;

    const q = (query || "").toLowerCase().trim();
    let results = [];

    for (const d of dishes) {
      // Province scope
      if (currentProvince && d.province_slug !== currentProvince) continue;

      // Category filter
      if (filters.cat && filters.cat !== "all" && d.category !== filters.cat) continue;

      // Price filter
      if (filters.price !== undefined && filters.price !== "all") {
        const pLevel = parseInt(filters.price);
        if (pLevel >= 0 && d.price_level !== pLevel) continue;
      }

      // Rating filter
      if (filters.rating !== undefined && filters.rating !== "all") {
        if (d.rating < parseFloat(filters.rating)) continue;
      }

      // Original only
      if (filters.original && !d.is_original) continue;

      if (!q) {
        results.push({ item: d, score: 0 });
        continue;
      }

      // Score across multiple fields
      const scores = [
        fuzzyScore(d.name, q) * 3,
        fuzzyScore(d.vendor, q) * 2.5,
        fuzzyScore(d.display, q) * 2,
        fuzzyScore(d.province, q) * 1.5,
        fuzzyScore(d.district, q) * 1.5,
        fuzzyScore(d.address, q),
        fuzzyScore(d.tags, q) * 2,
        fuzzyScore(d.description, q) * 0.5,
        fuzzyScore(d.category, q),
      ];
      const total = Math.max(...scores);
      if (total > 0) {
        results.push({ item: d, score: total });
      }
    }

    // Sort by score desc, then rating desc
    results.sort((a, b) => {
      if (Math.abs(b.score - a.score) > 1) return b.score - a.score;
      return b.item.rating - a.item.rating;
    });

    // Apply sort filter
    if (filters.sort) {
      const s = filters.sort;
      if (s === "rating-desc") results.sort((a, b) => b.item.rating - a.item.rating);
      else if (s === "reviews-desc") results.sort((a, b) => b.item.reviews - a.item.reviews);
      else if (s === "price-asc") results.sort((a, b) => (a.item.price_level === -1 ? 999 : a.item.price_level) - (b.item.price_level === -1 ? 999 : b.item.price_level));
      else if (s === "price-desc") results.sort((a, b) => (b.item.price_level === -1 ? -1 : b.item.price_level) - (a.item.price_level === -1 ? -1 : a.item.price_level));
    }

    return results;
  }

  // ── URL State Management ──
  function getURLParams() {
    const p = new URLSearchParams(window.location.search);
    return {
      q: p.get("q") || "",
      cat: p.get("cat") || "all",
      price: p.get("price") || "all",
      rating: p.get("rating") || "all",
      sort: p.get("sort") || "default",
      original: p.get("original") === "1",
    };
  }

  function updateURL(params) {
    const url = new URL(window.location);
    for (const [k, v] of Object.entries(params)) {
      if (!v || v === "all" || v === "default" || v === false || v === "") {
        url.searchParams.delete(k);
      } else if (v === true) {
        url.searchParams.set(k, "1");
      } else {
        url.searchParams.set(k, v);
      }
    }
    window.history.replaceState({}, "", url);
  }

  // ── UI: Suggestions Dropdown ──
  let suggestionIdx = -1;
  let currentSuggestions = [];

  function showSuggestions(results) {
    const dropdown = document.getElementById("searchSuggestions");
    const searchInput = document.getElementById("searchInput");
    if (!dropdown || !searchInput) return;

    // Position dropdown relative to search input
    const rect = searchInput.getBoundingClientRect();
    dropdown.style.position = "fixed";
    dropdown.style.top = rect.bottom + 4 + "px";
    dropdown.style.left = rect.left + "px";
    dropdown.style.width = rect.width + "px";
    dropdown.style.maxWidth = "600px";

    const top = results.slice(0, 6);
    currentSuggestions = top;
    suggestionIdx = -1;

    if (top.length === 0) {
      dropdown.style.display = "none";
      return;
    }

    dropdown.innerHTML = top
      .map(
        (r, i) => `
      <div class="suggestion-item" data-idx="${i}" data-url="${r.item.url}">
        <span class="sugg-icon">${getCatIcon(r.item.category)}</span>
        <span class="sugg-text">
          <strong>${highlightMatch(r.item.display, getSearchQuery())}</strong>
          <small>${r.item.province} · ${r.item.category} · ⭐${r.item.rating}</small>
        </span>
      </div>`
      )
      .join("");

    dropdown.style.display = "block";
  }

  function hideSuggestions() {
    const dropdown = document.getElementById("searchSuggestions");
    if (dropdown) dropdown.style.display = "none";
    suggestionIdx = -1;
    currentSuggestions = [];
  }

  function highlightMatch(text, query) {
    if (!query) return escapeHTML(text);
    const escaped = escapeHTML(text);
    const q = escapeHTML(query);
    const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    return escaped.replace(re, "<mark>$1</mark>");
  }

  function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function getCatIcon(cat) {
    const icons = {
      Bánh: "🥖",
      "Phở/Bún/Miến": "🍜",
      "Chè/Tráng miệng": "🍨",
      "Ốc/Hải sản": "🦐",
      "Nem/Chả/Gỏi": "🥢",
      "Đồ nướng": "🔥",
      Cơm: "🍚",
      "Đồ uống": "🥤",
      Lẩu: "🍲",
      "Ăn vặt": "🍿",
      "Đặc sản": "🏆",
      Chay: "🥬",
    };
    return icons[cat] || "🍽️";
  }

  function getSearchQuery() {
    const input = document.getElementById("searchInput");
    return input ? input.value.trim() : "";
  }

  // ── Keyboard Navigation ──
  function navigateSuggestions(e) {
    const dropdown = document.getElementById("searchSuggestions");
    if (!dropdown || dropdown.style.display === "none") return;

    const items = dropdown.querySelectorAll(".suggestion-item");
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      suggestionIdx = Math.min(suggestionIdx + 1, items.length - 1);
      updateSuggestionHighlight(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      suggestionIdx = Math.max(suggestionIdx - 1, -1);
      updateSuggestionHighlight(items);
    } else if (e.key === "Enter") {
      if (suggestionIdx >= 0 && suggestionIdx < items.length) {
        e.preventDefault();
        const url = items[suggestionIdx].dataset.url;
        if (url) window.location = url;
      } else {
        hideSuggestions();
        applySearchFromInput();
      }
    } else if (e.key === "Escape") {
      hideSuggestions();
    }
  }

  function updateSuggestionHighlight(items) {
    items.forEach((item, i) => {
      item.classList.toggle("active", i === suggestionIdx);
    });
  }

  // ── Apply Search & Filter ──
  function applySearchFromInput() {
    const input = document.getElementById("searchInput");
    const q = input ? input.value.trim() : "";

    const filters = {
      cat: document.getElementById("filterCatSelect")?.value || "all",
      price: document.getElementById("filterPrice")?.value || "all",
      rating: document.getElementById("filterRating")?.value || "all",
      sort: document.getElementById("filterSort")?.value || "default",
      original: document.getElementById("toggleOriginal")?.classList.contains("active-filter") || false,
    };

    updateURL({ q, ...filters });

    // If we're on a page with card grids, filter visible cards
    filterCardsOnPage(q, filters);
  }

  function filterCardsOnPage(query, filters) {
    const q = (query || "").toLowerCase().trim();
    const grids = document.querySelectorAll(".card-grid");

    let totalFound = 0;
    grids.forEach((grid) => {
      const cards = grid.querySelectorAll(".card");
      cards.forEach((card) => {
        let visible = true;

        if (q) {
          const text = (card.textContent || "").toLowerCase();
          if (!text.includes(q)) visible = false;
        }

        if (visible && filters.cat && filters.cat !== "all") {
          if (card.dataset.category !== filters.cat) visible = false;
        }

        if (visible && filters.original) {
          if (card.dataset.original !== "true") visible = false;
        }

        if (visible && filters.price && filters.price !== "all") {
          const pLevel = parseInt(filters.price);
          if (pLevel >= 0) {
            const cp = parseInt(card.dataset.price);
            if (cp !== -1 && cp !== pLevel) visible = false;
          }
        }

        if (visible && filters.rating && filters.rating !== "all") {
          const cr = parseFloat(card.dataset.rating) || 0;
          if (cr < parseFloat(filters.rating)) visible = false;
        }

        card.style.display = visible ? "" : "none";
        if (visible) totalFound++;
      });

      // Sort if needed
      if (filters.sort && filters.sort !== "default") {
        sortCardsInGrid(grid, filters.sort);
      }
    });

    // Update result count
    const countEl = document.getElementById("resultCount");
    if (countEl) {
      countEl.textContent = totalFound + " quán";
    }

    // Show/hide no results
    const noResults = document.getElementById("noResults");
    if (noResults) {
      noResults.style.display = totalFound === 0 ? "block" : "none";
      if (grids.length > 0) grids[0].style.display = totalFound === 0 ? "none" : "";
    }
  }

  function sortCardsInGrid(grid, sortVal) {
    const cards = Array.from(grid.querySelectorAll(".card"));
    const getRating = (el) => parseFloat(el.dataset.rating) || 0;
    const getReviews = (el) => parseInt(el.dataset.reviews) || 0;
    const getPrice = (el) => parseInt(el.dataset.price);

    if (sortVal === "rating-desc") cards.sort((a, b) => getRating(b) - getRating(a));
    else if (sortVal === "reviews-desc") cards.sort((a, b) => getReviews(b) - getReviews(a));
    else if (sortVal === "price-asc") cards.sort((a, b) => (getPrice(a) === -1 ? 999 : getPrice(a)) - (getPrice(b) === -1 ? 999 : getPrice(b)));
    else if (sortVal === "price-desc") cards.sort((a, b) => (getPrice(b) === -1 ? -1 : getPrice(b)) - (getPrice(a) === -1 ? -1 : getPrice(a)));

    cards.forEach((c) => grid.appendChild(c));
  }

  // ── Live search with suggestions ──
  let searchDebounce;

  function onSearchInput() {
    clearTimeout(searchDebounce);
    const q = getSearchQuery();

    if (!q) {
      hideSuggestions();
      // Reset filters if search is cleared
      const params = getURLParams();
      params.q = "";
      updateURL(params);
      filterCardsOnPage("", params);
      return;
    }

    searchDebounce = setTimeout(() => {
      if (!loaded) return;

      const filters = getURLParams();
      const results = searchDishes(q, { cat: filters.cat || "all" });

      if (results.length > 0) {
        showSuggestions(results);
      } else {
        hideSuggestions();
      }
    }, 200);
  }

  // ── Init ──
  async function init() {
    // Detect province page
    const provMeta = document.querySelector('meta[name="province-slug"]');
    if (provMeta) {
      currentProvince = provMeta.content;
    }

    // Load data index
    try {
      const resp = await fetch("/data/dishes.json");
      if (resp.ok) {
        dishes = await resp.json();
        loaded = true;
        console.log(`[Search] Loaded ${dishes.length} dishes`);
      }
    } catch (e) {
      console.warn("[Search] Could not load dishes.json, falling back to DOM search");
    }

    // Attach search input events
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
      searchInput.addEventListener("input", onSearchInput);
      searchInput.addEventListener("keydown", navigateSuggestions);
      searchInput.addEventListener("focus", () => {
        const q = getSearchQuery();
        if (q && loaded) {
          const results = searchDishes(q, {});
          showSuggestions(results);
        }
      });
    }

    // Click outside to close suggestions
    document.addEventListener("click", (e) => {
      const dropdown = document.getElementById("searchSuggestions");
      const input = document.getElementById("searchInput");
      if (dropdown && input && !dropdown.contains(e.target) && e.target !== input) {
        hideSuggestions();
      }
    });

    // Click on suggestion
    document.addEventListener("click", (e) => {
      const item = e.target.closest(".suggestion-item");
      if (item && item.dataset.url) {
        window.location = item.dataset.url;
      }
    });

    // Attach filter events
    const filterEls = ["filterPrice", "filterRating", "filterSort", "filterCatSelect"];
    filterEls.forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", applySearchFromInput);
      }
    });

    // Original toggle
    const origBtn = document.getElementById("toggleOriginal");
    if (origBtn) {
      origBtn.addEventListener("click", () => {
        origBtn.classList.toggle("active-filter");
        applySearchFromInput();
      });
    }

    // Restore state from URL
    const params = getURLParams();
    if (params.q) {
      if (searchInput) searchInput.value = params.q;
    }
    if (params.cat && params.cat !== "all") {
      const catSelect = document.getElementById("filterCatSelect");
      if (catSelect) catSelect.value = params.cat;
    }
    if (params.price && params.price !== "all") {
      const priceSelect = document.getElementById("filterPrice");
      if (priceSelect) priceSelect.value = params.price;
    }
    if (params.rating && params.rating !== "all") {
      const ratingSelect = document.getElementById("filterRating");
      if (ratingSelect) ratingSelect.value = params.rating;
    }
    if (params.sort && params.sort !== "default") {
      const sortSelect = document.getElementById("filterSort");
      if (sortSelect) sortSelect.value = params.sort;
    }
    if (params.original) {
      const origToggle = document.getElementById("toggleOriginal");
      if (origToggle) origToggle.classList.add("active-filter");
    }

    // Apply initial filters from URL
    if (params.q || params.cat !== "all" || params.price !== "all" || params.rating !== "all" || params.sort !== "default" || params.original) {
      filterCardsOnPage(params.q, params);
    }
  }

  // ── Expose public API ──
  window.DacSanPho = {
    search: searchDishes,
    init: init,
    applySearch: applySearchFromInput,
    filterCards: filterCardsOnPage,
    updateURL: updateURL,
  };

  // Auto-init
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
