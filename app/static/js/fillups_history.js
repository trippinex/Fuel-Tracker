/* Fill-Up History page — edit/delete, filtering, pagination, sticky layout. */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════════════════
     ▌ SECTION 1 — ROW EDIT / DELETE
  ═══════════════════════════════════════════════════════════════════════ */

  function row(id)  { return document.getElementById(`row-${id}`);  }
  function card(id) { return document.getElementById(`card-${id}`); }

  function applyMode(container, mode) {
    if (!container) return;
    container.querySelectorAll('[data-v]').forEach(n => n.classList.toggle('hidden', mode !== 'view'));
    container.querySelectorAll('[data-e]').forEach(n => n.classList.toggle('hidden', mode !== 'edit'));
    container.querySelectorAll('[data-c]').forEach(n => n.classList.toggle('hidden', mode !== 'confirm'));
  }

  function setMode(id, mode) {
    const r = row(id);
    const c = card(id);
    applyMode(r, mode);
    applyMode(c, mode);

    if (r) {
      r.style.backgroundColor =
        mode === 'edit'    ? '#eef2ff' :
        mode === 'confirm' ? '#fff7ed' : '';
    }
    if (c) {
      c.classList.toggle('border-indigo-300', mode === 'edit');
      c.classList.toggle('border-amber-300',  mode === 'confirm');
      c.classList.toggle('border-slate-200',  mode === 'view');
    }

    if (mode === 'edit') {
      wireLiveTotal(id);
      const first = (r || c)?.querySelector('[data-e] input');
      first?.focus();
    }
    clearError(id);
  }

  function wireLiveTotal(id) {
    [[row(id), '[data-total-live]'], [card(id), '[data-mobile-total-edit]']].forEach(([el, sel]) => {
      if (!el) return;
      const g = el.querySelector('[data-field="gallons"]');
      const p = el.querySelector('[data-field="price"]');
      const t = el.querySelector(sel);
      const update = () => {
        const gv = parseFloat(g?.value) || 0;
        const pv = parseFloat(p?.value) || 0;
        if (t) t.textContent = pv > 0 ? `$${(gv * pv).toFixed(2)}` : '—';
      };
      g?.addEventListener('input', update);
      p?.addEventListener('input', update);
      update();
    });
  }

  function showError(id, msg) {
    [row(id), card(id)].filter(Boolean).forEach(el => {
      const e = el.querySelector('[data-error]');
      if (e) { e.textContent = msg; e.classList.remove('hidden'); }
    });
  }

  function clearError(id) {
    [row(id), card(id)].filter(Boolean).forEach(el => {
      const e = el.querySelector('[data-error]');
      if (e) { e.textContent = ''; e.classList.add('hidden'); }
    });
  }

  function getValues(id) {
    const isDesktop = window.matchMedia('(min-width: 640px)').matches;
    const c = isDesktop ? row(id) : card(id);
    return {
      date:             c?.querySelector('[data-field="date"]')?.value     ?? '',
      odometer_reading: c?.querySelector('[data-field="odometer"]')?.value ?? '',
      gallons_pumped:   c?.querySelector('[data-field="gallons"]')?.value  ?? '',
      price_per_gallon: c?.querySelector('[data-field="price"]')?.value    ?? '',
    };
  }

  function applyUpdate(id, f) {
    const r = row(id);
    if (r) {
      r.querySelector('[data-cell="date"] [data-v]').textContent     = f.date_display;
      r.querySelector('[data-cell="odometer"] [data-v]').textContent = f.odometer_display;
      r.querySelector('[data-cell="gallons"] [data-v]').textContent  = f.gallons_display;
      r.querySelector('[data-cell="price"] [data-v]').textContent    = f.price_display;
      r.querySelector('[data-cell="total"] [data-v]').textContent    = f.total_display;
      const mpgSpan = r.querySelector('[data-cell="mpg"] [data-v]');
      mpgSpan.textContent = f.mpg_display;
      mpgSpan.className   = f.mpg ? 'font-medium text-green-600' : 'font-medium text-slate-400';
      r.querySelector('[data-field="date"]').value     = f.date;
      r.querySelector('[data-field="odometer"]').value = f.odometer_reading;
      r.querySelector('[data-field="gallons"]').value  = f.gallons_pumped;
      r.querySelector('[data-field="price"]').value    = f.price_per_gallon > 0 ? f.price_per_gallon : '';
      r.dataset.date = f.date;
    }
    const c = card(id);
    if (c) {
      const tot    = c.querySelector('[data-mobile-total]');
      const detail = c.querySelector('[data-mobile-detail]');
      if (tot)    tot.textContent = f.total_display;
      if (detail) {
        let d = `${f.date_display} · ${f.gallons_display} gal · ${f.odometer_display} mi`;
        if (f.mpg) d += ` · ${f.mpg_display} MPG`;
        detail.innerHTML = d;
      }
      c.querySelector('[data-field="date"]').value     = f.date;
      c.querySelector('[data-field="odometer"]').value = f.odometer_reading;
      c.querySelector('[data-field="gallons"]').value  = f.gallons_pumped;
      c.querySelector('[data-field="price"]').value    = f.price_per_gallon > 0 ? f.price_per_gallon : '';
      c.dataset.date = f.date;
    }
  }

  function flashSuccess(id) {
    const r = row(id);
    if (r) { r.style.backgroundColor = '#f0fdf4'; setTimeout(() => { r.style.backgroundColor = ''; }, 1400); }
    const c = card(id);
    if (c) { c.classList.add('border-green-400'); setTimeout(() => c.classList.remove('border-green-400'), 1400); }
  }

  function animateRemove(id) {
    [row(id), card(id)].filter(Boolean).forEach(el => {
      el.style.transition = 'opacity 0.25s, transform 0.25s';
      el.style.opacity    = '0';
      el.style.transform  = 'translateX(12px)';
    });
    setTimeout(() => {
      [row(id), card(id)].filter(Boolean).forEach(el => el.remove());
      decrementTotal();
      filterRecords();
    }, 270);
  }

  function decrementTotal() {
    const el = document.getElementById('fillup-count');
    if (el) {
      const t = Math.max(0, parseInt(el.dataset.total || '0', 10) - 1);
      el.dataset.total = t;
    }
  }

  function setBtnLoading(id, sel, text) {
    [row(id), card(id)].filter(Boolean).forEach(c => {
      const b = c.querySelector(sel); if (b) { b.disabled = true; b.textContent = text; }
    });
  }

  function resetBtn(id, sel, html) {
    [row(id), card(id)].filter(Boolean).forEach(c => {
      const b = c.querySelector(sel); if (b) { b.disabled = false; b.innerHTML = html; }
    });
  }

  const checkSvg = `<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>`;

  window.handleEditRow      = id => setMode(id, 'edit');
  window.handleCancelRow    = id => setMode(id, 'view');
  window.handleDeleteRow    = id => setMode(id, 'confirm');
  window.handleDeleteCancel = id => setMode(id, 'view');

  window.handleSaveRow = async function (id) {
    setBtnLoading(id, '[data-save-btn]', 'Saving…');
    let result;
    try {
      const resp = await fetch(`/fillups/${id}/edit`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body:    JSON.stringify(getValues(id)),
      });
      result = await resp.json();
    } catch {
      showError(id, 'Network error — please try again.');
      resetBtn(id, '[data-save-btn]', `${checkSvg} Save`);
      return;
    }
    if (!result.success) {
      showError(id, result.error || 'Save failed.');
      resetBtn(id, '[data-save-btn]', `${checkSvg} Save`);
      return;
    }
    applyUpdate(id, result.fillup);
    setMode(id, 'view');
    flashSuccess(id);
    filterRecords();
  };

  window.handleDeleteConfirm = async function (id) {
    setBtnLoading(id, '[data-delete-btn]', 'Deleting…');
    let result;
    try {
      const resp = await fetch(`/fillups/${id}/delete`, {
        method:  'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      result = await resp.json();
    } catch {
      showError(id, 'Network error — please try again.');
      setMode(id, 'view');
      return;
    }
    if (!result.success) {
      showError(id, result.error || 'Delete failed.');
      setMode(id, 'view');
      return;
    }
    animateRemove(id);
  };


  /* ═══════════════════════════════════════════════════════════════════════
     ▌ SECTION 2 — FILTER + PAGINATION
  ═══════════════════════════════════════════════════════════════════════ */

  const fltVehicle   = document.getElementById('flt-vehicle');
  const fltReset     = document.getElementById('flt-reset');
  const dateValWrap  = document.getElementById('date-val-wrap');
  const fdDate       = document.getElementById('fd-date');
  const fdMonth      = document.getElementById('fd-month');
  const fdYear       = document.getElementById('fd-year');
  const countEl      = document.getElementById('fillup-count');
  const countLabelEl = document.getElementById('fillup-count-label');
  const desktopEmpty = document.getElementById('desktop-empty-row');
  const mobileEmpty  = document.getElementById('mobile-empty-state');
  const pgPrev       = document.getElementById('pg-prev');
  const pgNext       = document.getElementById('pg-next');
  const pgIndicator  = document.getElementById('pg-indicator');
  const pgBar        = document.getElementById('pagination-bar');

  let currentDateType = '';
  let currentPage     = 1;
  let rowsPerPage     = 10;

  document.querySelectorAll('.rows-limit-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      rowsPerPage = parseInt(this.dataset.limit, 10);
      currentPage = 1;
      document.querySelectorAll('.rows-limit-btn').forEach(b => {
        const active = b === this;
        b.classList.toggle('bg-fuel-500', active);
        b.classList.toggle('text-white',  active);
        b.classList.toggle('text-slate-500', !active);
      });
      filterRecords();
    });
  });

  const defaultLimitBtn = document.querySelector('.rows-limit-btn[data-limit="10"]');
  if (defaultLimitBtn) {
    defaultLimitBtn.classList.add('bg-fuel-500', 'text-white');
    defaultLimitBtn.classList.remove('text-slate-500');
  }

  document.querySelectorAll('.date-type-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const type     = this.dataset.type;
      const isActive = this.classList.contains('is-active');

      document.querySelectorAll('.date-type-btn').forEach(b => {
        b.classList.remove('is-active', 'bg-fuel-500', 'text-white');
        b.classList.add('text-slate-500');
      });

      if (isActive) {
        currentDateType = '';
      } else {
        this.classList.add('is-active', 'bg-fuel-500', 'text-white');
        this.classList.remove('text-slate-500');
        currentDateType = type;
      }

      currentPage = 1;
      syncDateInput();
      filterRecords();
    });
  });

  function syncDateInput() {
    const show = currentDateType !== '';
    dateValWrap.classList.toggle('hidden', !show);
    fdDate.classList.toggle('hidden',  currentDateType !== 'date');
    fdMonth.classList.toggle('hidden', currentDateType !== 'month');
    fdYear.classList.toggle('hidden',  currentDateType !== 'year');
    if (currentDateType !== 'date')  fdDate.value  = '';
    if (currentDateType !== 'month') fdMonth.value = '';
    if (currentDateType !== 'year')  fdYear.value  = '';
  }

  function getDateValue() {
    if (currentDateType === 'date')  return fdDate.value;
    if (currentDateType === 'month') return fdMonth.value;
    if (currentDateType === 'year')  return fdYear.value;
    return '';
  }

  function filterRecords() {
    const vehicleFilter = fltVehicle?.value || '';
    const dateVal       = getDateValue();
    const isFiltered    = !!(vehicleFilter || (currentDateType && dateVal));

    if (fltReset) {
      fltReset.classList.toggle('hidden', !isFiltered);
      fltReset.style.display = isFiltered ? 'inline-flex' : '';
    }

    const allRows = Array.from(document.querySelectorAll('#desktop-tbody tr[data-id]'));

    const matching = allRows.filter(tr => {
      const vehicleMatch = !vehicleFilter || tr.dataset.vehicle === vehicleFilter;
      let dateMatch = true;
      if (currentDateType && dateVal) {
        const d = tr.dataset.date || '';
        if      (currentDateType === 'date')  dateMatch = d === dateVal;
        else if (currentDateType === 'month') dateMatch = d.slice(0, 7) === dateVal;
        else if (currentDateType === 'year')  dateMatch = d.slice(0, 4) === dateVal;
      }
      return vehicleMatch && dateMatch;
    });

    const totalPages = Math.max(1, Math.ceil(matching.length / rowsPerPage));
    currentPage = Math.min(Math.max(1, currentPage), totalPages);

    const start   = (currentPage - 1) * rowsPerPage;
    const pageIds = new Set(matching.slice(start, start + rowsPerPage).map(tr => tr.dataset.id));

    allRows.forEach(tr => {
      const show = pageIds.has(tr.dataset.id);
      tr.classList.toggle('hidden', !show);
      const c = card(tr.dataset.id);
      if (c) c.classList.toggle('hidden', !show);
    });

    const isEmpty = matching.length === 0;
    if (desktopEmpty) desktopEmpty.classList.toggle('hidden', !isEmpty);
    if (mobileEmpty)  mobileEmpty.classList.toggle('hidden',  !isEmpty);

    updateSubtitle(matching.length, isFiltered);
    updatePagination(matching.length, totalPages);
  }

  function updatePagination(total, totalPages) {
    if (pgIndicator) pgIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
    if (pgPrev) pgPrev.disabled = currentPage <= 1;
    if (pgNext) pgNext.disabled = currentPage >= totalPages;
    if (pgBar) pgBar.classList.toggle('hidden', total === 0);
  }

  function updateSubtitle(visible, isFiltered) {
    if (!countEl || !countLabelEl) return;
    const total = parseInt(countEl.dataset.total || '0', 10);
    if (isFiltered) {
      countEl.textContent      = visible;
      countLabelEl.textContent = ` matching fill-up${visible !== 1 ? 's' : ''} found`;
    } else {
      countEl.textContent      = total;
      countLabelEl.textContent = ` total fill-up${total !== 1 ? 's' : ''} across all vehicles`;
    }
  }

  window.resetFilters = function () {
    if (fltVehicle) fltVehicle.value = '';
    document.querySelectorAll('.date-type-btn').forEach(b => {
      b.classList.remove('is-active', 'bg-fuel-500', 'text-white');
      b.classList.add('text-slate-500');
    });
    currentDateType = '';
    currentPage     = 1;
    syncDateInput();
    filterRecords();
  };

  pgPrev?.addEventListener('click', () => { if (currentPage > 1) { currentPage--; filterRecords(); } });
  pgNext?.addEventListener('click', () => { currentPage++; filterRecords(); });

  fltVehicle?.addEventListener('change', () => { currentPage = 1; filterRecords(); });
  fdDate?.addEventListener('change',     () => { currentPage = 1; filterRecords(); });
  fdMonth?.addEventListener('change',    () => { currentPage = 1; filterRecords(); });
  fdYear?.addEventListener('change',     () => { currentPage = 1; filterRecords(); });

  syncDateInput();
  filterRecords();


  /* ═══════════════════════════════════════════════════════════════════════
     ▌ SECTION 3 — STICKY OFFSET CALCULATION
  ═══════════════════════════════════════════════════════════════════════ */
  const NAV_H       = 56;
  const pgHeaderEl  = document.getElementById('sticky-pg-header');
  const filterEl2   = document.getElementById('sticky-filter');
  const tableWrapEl = document.getElementById('desktop-table-wrapper');

  function updateStickyLayout() {
    if (!pgHeaderEl) return;
    const pgH     = pgHeaderEl.offsetHeight;
    const filterH = filterEl2 ? filterEl2.offsetHeight : 0;
    const pgBarH  = pgBar     ? pgBar.offsetHeight + 8  : 48;

    if (filterEl2) {
      filterEl2.style.top = (NAV_H + pgH) + 'px';
    }

    if (tableWrapEl) {
      const usedPx = NAV_H + pgH + filterH + 8 + pgBarH + 24;
      tableWrapEl.style.maxHeight = 'calc(100vh - ' + usedPx + 'px)';
    }
  }

  [pgHeaderEl, filterEl2, pgBar].forEach(function (el) {
    if (el && window.ResizeObserver) {
      new ResizeObserver(updateStickyLayout).observe(el);
    }
  });
  updateStickyLayout();
  window.addEventListener('resize', updateStickyLayout);

})();
