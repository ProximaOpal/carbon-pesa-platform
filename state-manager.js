// =====================================================================
// CARBON PESA — Global State Registry (state-manager.js)
// v2 — Non-breaking, lazy, fully defensive
// =====================================================================
// DESIGN RULES:
//   1. This file NEVER throws. All operations are try-catch wrapped.
//   2. All DOM interactions are deferred to DOMContentLoaded.
//   3. patchState / syncGlobalState are safe to call from ANY file
//      regardless of load order.
//   4. State sync is debounced (500ms) to avoid flooding the API
//      during map panning.
// =====================================================================

(function () {
  'use strict';

  const STATE_SYNC_URL     = 'https://carbon-pesa-platform-1.onrender.com/api/update-state';
  const DEBOUNCE_MS        = 500;
  let   _syncTimer         = null;

  // ── Page detection ─────────────────────────────────────────────────
  function _detectPage() {
    try {
      const file = window.location.pathname.split('/').pop() || 'index.html';
      return {
        'index.html'          : 'Home',
        'map.html'            : 'AuditMaps',
        'carbon-credits.html' : 'CarbonCredits',
        'education.html'      : 'Education',
        'partners.html'       : 'Partners'
      }[file] || 'Unknown';
    } catch (_) { return 'Unknown'; }
  }

  // ── State object ───────────────────────────────────────────────────
  window.CarbonPesaState = {
    currentPage        : _detectPage(),
    currentSlideIndex  : 0,
    currentSlideHeading: 'MISSION',
    searchOpen         : false,
    navMenuOpen        : false,
    activeView         : 'audit',
    activeFarmId       : 1,
    mapContext         : { lat: -0.5023, lng: 35.4156, zoom: 15 },
    activeLayers       : ['satellite', 'NDVI'],
    lastAgentIntent    : null,
    lastAgentPayload   : null,
    updatedAt          : new Date().toISOString()
  };

  // ── Sync function (debounced POST) ─────────────────────────────────
  window.syncGlobalState = function () {
    clearTimeout(_syncTimer);
    _syncTimer = setTimeout(function () {
      try {
        window.CarbonPesaState.updatedAt = new Date().toISOString();
        fetch(STATE_SYNC_URL, {
          method  : 'POST',
          headers : { 'Content-Type': 'application/json' },
          body    : JSON.stringify(window.CarbonPesaState)
        }).catch(function () { /* silent — backend may be offline */ });
      } catch (_) { /* never throw */ }
    }, DEBOUNCE_MS);
  };

  // ── patchState — safe merge helper ────────────────────────────────
  // Usage: window.patchState({ activeView: 'field' })
  // Safe to call before or after DOMContentLoaded from any file.
  window.patchState = function (partial) {
    try {
      Object.assign(window.CarbonPesaState, partial);
      window.syncGlobalState();
    } catch (_) { /* never throw */ }
  };

  // ── Initial sync after DOM ready ───────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      window.syncGlobalState();
    });
  } else {
    // Already loaded (script placed at bottom of body)
    window.syncGlobalState();
  }

  console.log('[CarbonPesa] State registry ready. Page:', window.CarbonPesaState.currentPage);
}());
