"use strict";
// Presentation-only navigation. Existing Cockpit management operations stay in app.js.
(function () {
  const tabs = Array.from(document.querySelectorAll('[data-tab]'));
  const sections = Array.from(document.querySelectorAll('[data-view]'));
  function showTab(name) {
    if (!sections.some(section => section.dataset.view === name)) name = 'overview';
    for (const tab of tabs) {
      const current = tab.dataset.tab === name;
      tab.classList.toggle('active', current);
      if (current) tab.setAttribute('aria-current','page');
      else tab.removeAttribute('aria-current');
    }
    for (const section of sections) section.classList.toggle('active', section.dataset.view === name);
    if (name === 'console') { if (typeof logs === 'function') logs(); if (typeof loadPlayerActivity === 'function') loadPlayerActivity(); }
    if (name === 'performance' && typeof loadMetrics === 'function') loadMetrics(false).catch(() => {});
  }
  tabs.forEach(tab => tab.addEventListener('click', () => showTab(tab.dataset.tab)));
  showTab('overview');
})();
