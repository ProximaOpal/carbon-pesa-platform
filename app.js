'use strict';
// =====================================================================
// CARBON PESA — Landing Page Logic (app.js)
// Wrapped fully in DOMContentLoaded to prevent null-ref errors.
// State sync calls are defensive: always guarded by if (window.patchState).
// =====================================================================

document.addEventListener('DOMContentLoaded', function () {

  // ── DOM REFS (all guarded — this page only) ─────────────────────────
  const heroBg        = document.getElementById('heroBg');
  const searchBtn     = document.getElementById('searchBtn');
  const searchOverlay = document.getElementById('searchOverlay');
  const searchClose   = document.getElementById('searchClose');
  const searchInput   = document.getElementById('searchInput');
  const menuBtn       = document.getElementById('menuBtn');
  const mainNav       = document.getElementById('mainNav');
  const dots          = document.querySelectorAll('.dot');
  const navLinks      = document.querySelectorAll('.nav-link');
  const colRight      = document.getElementById('colRight');
  const dotsNav       = document.getElementById('dotsNav');
  const btnPlant      = document.getElementById('btnPlant');
  const btnWorkflow   = document.getElementById('btnWorkflow');
  const shareBtn      = document.getElementById('shareBtn');
  const featureBlock  = document.getElementById('featureBlock');

  // ── SLIDE DATA ───────────────────────────────────────────────────────
  const slides = [
    {
      number  : '01.',
      heading : 'MISSION',
      body    : 'Carbon Pesa bridges global climate capital with youth-powered tree planting. Every investment funds verified missions executed by university students, high-schoolers and rural communities.',
      body2   : 'From funding to satellite verification to M-Pesa payouts — the full impact cycle in 48-72 hours.',
    },
    {
      number  : '02.',
      heading : 'INVESTORS',
      body    : '94+ institutional investors fund climate missions across Africa and beyond. Each tonne of carbon sequestered is tokenised, satellite-verified, and ESG-grade — no greenwashing, only bankable nature.',
      body2   : 'Spot price today: $24.80 / tCO₂e. Live listings: Mau Forest · Kakamega · Aberdare.',
    },
    {
      number  : '03.',
      heading : 'YOUTH',
      body    : '38,000+ youth activated across 61 countries. University students, high-schoolers and primary pupils earn stipends via M-Pesa while building environmental careers on the ground.',
      body2   : 'Schools receive grants. Youth earn experience. Communities grow a permanent green legacy.',
    },
    {
      number  : '04.',
      heading : 'CARBON',
      body    : 'Real-time agricultural carbon mapping powered by AI satellite audits with an Audit Uncertainty of ±2.9%. Buy or sell verified carbon credits on a transparent marketplace trusted by global institutions.',
      body2   : 'MRV Cost: <$0.40 per hectare per year · Farmer Revenue: 88% · $24.80 / tCO₂e.',
    },
    {
      number  : '05.',
      heading : 'IMPACT',
      body    : '142,000+ trees funded across urban roadsides, school compounds, rural farmlands and watersheds. SDG-aligned outcomes across Goals 1 · 8 · 13 · 15 · 17 — publicly auditable impact.',
      body2   : 'Zero greenwashing. Every mission is geo-tagged, species-logged, and satellite-confirmed.',
    },
  ];

  let currentSlide = 0;
  let isAnimating  = false;
  let autoPlay     = null;
  let navOpen      = false;

  // ── BACKGROUND LOAD ANIMATION ────────────────────────────────────────
  if (heroBg) {
    heroBg.classList.add('loaded');
  }

  // ── ANIMATED STAT COUNTERS ───────────────────────────────────────────
  function animateCounters() {
    const odoCarbon = document.getElementById('odoCarbon');
    const odoPayout = document.getElementById('odoPayout');
    if (!odoCarbon || !odoPayout) return;

    function fetchStats() {
      fetch('https://proxima-opal-platform-1.onrender.com/stats/dashboard')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          odoCarbon.innerHTML = data.total_tco2e_sequestered;
          odoPayout.innerHTML = data.total_usd_flowing;
        })
        .catch(function () {}); // silent fail — backend may be cold
    }
    fetchStats();
    setInterval(fetchStats, 10000);
  }
  animateCounters();

  // ── TOAST ────────────────────────────────────────────────────────────
  function showToast(msg) {
    const el = document.createElement('div');
    el.textContent = msg;
    Object.assign(el.style, {
      position       : 'fixed',
      bottom         : '40px',
      left           : '50%',
      transform      : 'translateX(-50%) translateY(14px)',
      background     : 'rgba(126, 200, 67, 0.12)',
      border         : '1px solid rgba(126, 200, 67, 0.35)',
      backdropFilter : 'blur(14px)',
      color          : '#ffffff',
      padding        : '11px 28px',
      borderRadius   : '4px',
      fontFamily     : 'Outfit, sans-serif',
      fontSize       : '12px',
      letterSpacing  : '1.2px',
      zIndex         : '9999',
      opacity        : '0',
      transition     : 'opacity 0.3s, transform 0.3s',
      pointerEvents  : 'none',
      whiteSpace     : 'nowrap',
    });
    document.body.appendChild(el);
    requestAnimationFrame(function () {
      el.style.opacity   = '1';
      el.style.transform = 'translateX(-50%) translateY(0)';
    });
    setTimeout(function () {
      el.style.opacity   = '0';
      el.style.transform = 'translateX(-50%) translateY(14px)';
      setTimeout(function () { el.remove(); }, 320);
    }, 2800);
  }

  // ── SEARCH OVERLAY ───────────────────────────────────────────────────
  function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.add('open');
    setTimeout(function () { if (searchInput) searchInput.focus(); }, 300);
    if (window.patchState) window.patchState({ searchOpen: true });
  }

  function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.remove('open');
    if (searchInput) searchInput.value = '';
    if (window.patchState) window.patchState({ searchOpen: false });
  }

  if (searchBtn)     searchBtn.addEventListener('click', openSearch);
  if (searchClose)   searchClose.addEventListener('click', closeSearch);
  if (searchOverlay) {
    searchOverlay.addEventListener('click', function (e) {
      if (e.target === searchOverlay) closeSearch();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSearch();
  });

  // ── MOBILE MENU TOGGLE ───────────────────────────────────────────────
  function openNav() {
    if (!mainNav) return;
    navOpen = true;
    Object.assign(mainNav.style, {
      display       : 'flex',
      flexDirection : 'column',
      position      : 'absolute',
      top           : '72px',
      right         : '56px',
      background    : 'rgba(4,14,4,0.95)',
      padding       : '20px 28px',
      gap           : '18px',
      backdropFilter: 'blur(16px)',
      borderLeft    : '1px solid rgba(255,255,255,0.1)',
      zIndex        : '50'
    });
    if (menuBtn) menuBtn.innerHTML = '<i class="fas fa-times"></i>';
    if (window.patchState) window.patchState({ navMenuOpen: true });
  }

  function closeNav() {
    if (!mainNav) return;
    navOpen = false;
    mainNav.removeAttribute('style');
    if (menuBtn) menuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    if (window.patchState) window.patchState({ navMenuOpen: false });
  }

  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      navOpen ? closeNav() : openNav();
    });
  }

  navLinks.forEach(function (link) {
    link.addEventListener('click', function () {
      navLinks.forEach(function (l) { l.classList.remove('active'); });
      link.classList.add('active');
      if (navOpen) closeNav();
    });
  });

  // ── SLIDE TRANSITIONS ────────────────────────────────────────────────
  function goToSlide(index) {
    if (isAnimating || index === currentSlide || !featureBlock) return;
    isAnimating = true;

    if (dots[currentSlide]) dots[currentSlide].classList.remove('active');
    if (dots[index])        dots[index].classList.add('active');
    currentSlide = index;

    // State sync
    if (window.patchState) window.patchState({
      currentSlideIndex  : index,
      currentSlideHeading: slides[index].heading
    });

    // Fade out
    featureBlock.style.transition = 'opacity 0.28s ease, transform 0.28s ease';
    featureBlock.style.opacity    = '0';
    featureBlock.style.transform  = 'translateY(18px)';

    setTimeout(function () {
      const s = slides[index];
      const fn = document.getElementById('featNumber');
      const fh = document.getElementById('featHeading');
      const fb = document.getElementById('featBody');
      const fb2 = document.getElementById('featBody2');
      if (fn)  fn.textContent  = s.number;
      if (fh)  fh.textContent  = s.heading;
      if (fb)  fb.textContent  = s.body;
      if (fb2) fb2.textContent = s.body2;

      // Fade in
      featureBlock.style.transition = 'opacity 0.38s ease, transform 0.38s ease';
      featureBlock.style.opacity    = '1';
      featureBlock.style.transform  = 'translateY(0)';
      setTimeout(function () { isAnimating = false; }, 400);
    }, 290);
  }

  // Dot clicks
  dots.forEach(function (dot, i) {
    dot.addEventListener('click', function () { goToSlide(i); });
  });

  // Auto-advance
  function advanceSlide() {
    goToSlide((currentSlide + 1) % slides.length);
  }
  autoPlay = setInterval(advanceSlide, 5500);

  // Pause on hover
  if (colRight) {
    colRight.addEventListener('mouseenter', function () { clearInterval(autoPlay); });
    colRight.addEventListener('mouseleave', function () { autoPlay = setInterval(advanceSlide, 5500); });
  }
  if (dotsNav) {
    dotsNav.addEventListener('mouseenter', function () { clearInterval(autoPlay); });
    dotsNav.addEventListener('mouseleave', function () { autoPlay = setInterval(advanceSlide, 5500); });
  }

  // ── CTA BUTTONS ──────────────────────────────────────────────────────
  if (btnPlant) {
    btnPlant.addEventListener('click', function () {
      showToast('🌱 Starting your planting journey…');
    });
  }
  if (btnWorkflow) {
    btnWorkflow.addEventListener('click', function () {
      showToast('📋 Loading full workflow…');
    });
  }

  // ── PARALLAX ON MOUSE MOVE ───────────────────────────────────────────
  if (heroBg) {
    document.addEventListener('mousemove', function (e) {
      const xPct = (e.clientX / window.innerWidth  - 0.5) * 1.8;
      const yPct = (e.clientY / window.innerHeight - 0.5) * 1.2;
      heroBg.style.transform = 'scale(1.04) translate(' + xPct + '%, ' + yPct + '%)';
    });
  }

  // ── SHARE BUTTON ─────────────────────────────────────────────────────
  if (shareBtn) {
    shareBtn.addEventListener('click', async function () {
      const data = {
        title : 'Carbon Pesa — Climate Action Platform',
        text  : 'Bridging Climate Investors with Youth Tree Planters across Urban & Rural Communities Worldwide.',
        url   : window.location.href,
      };
      if (navigator.share) {
        try { await navigator.share(data); } catch (_) {}
      } else {
        await navigator.clipboard.writeText(data.url).catch(function () {});
        showToast('🔗 Link copied to clipboard!');
      }
    });
  }

}); // END DOMContentLoaded
