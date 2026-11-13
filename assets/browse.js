/* Browse page: open postings with a role switch, filters, title search, sort,
   apply links and a starred shortlist kept in the browser (localStorage). */
App.boot('browse', function (root, data) {
  const el = App.el;
  const lastRun = Calc.lastRunDate(data.rows);
  const open = data.rows.filter(function (r) { return r.status === 'open'; });
  const byId = {};
  data.rows.forEach(function (r) { byId[r.posting_id] = r; r.days_open = lastRun ? Calc.diffDays(r.first_seen, lastRun) : 0; });

  // ---- shortlist, stored in the browser and still there after a reload ----
  const KEY = 'jobwatcher.shortlist';
  let shortlist = new Set();
  try { shortlist = new Set(JSON.parse(localStorage.getItem(KEY) || '[]')); } catch (e) { /* storage blocked: stars last for this visit */ }
  function saveShortlist() {
    try { localStorage.setItem(KEY, JSON.stringify(Array.from(shortlist))); } catch (e) { /* ignore */ }
  }

  const state = { role: 'mine', region: 'us', employer: '', location: '', days: '', q: '', sort: 'new', starred: false, limit: 100 };
  const DAY_BANDS = { '': null, '0-1': [0, 1], '2-7': [2, 7], '8-14': [8, 14], '15-30': [15, 30], '31+': [31, Infinity] };

  function matches(r, ignoreRegion) {
    if (state.role === 'mine' && !r.in_role) return false;
    if (!ignoreRegion && !Calc.inRegion(r.location, state.region)) return false;
    if (state.employer && r.employer !== state.employer) return false;
    if (state.location && r.location.toLowerCase().indexOf(state.location.toLowerCase()) < 0) return false;
    const band = DAY_BANDS[state.days];
    if (band && (r.days_open < band[0] || r.days_open > band[1])) return false;
    if (state.q && r.title.toLowerCase().indexOf(state.q.toLowerCase()) < 0) return false;
    return true;
  }

  function visible() {
    let list;
    if (state.starred) {
      list = Array.from(shortlist).map(function (id) { return byId[id]; }).filter(Boolean)
        .filter(function (r) { return !state.q || r.title.toLowerCase().indexOf(state.q.toLowerCase()) >= 0; });
    } else {
      list = open.filter(matches);
    }
    const dir = state.sort === 'new' ? -1 : 1;
    return list.sort(function (a, b) {
      return dir * (a.first_seen < b.first_seen ? -1 : a.first_seen > b.first_seen ? 1 : 0) ||
        (a.employer < b.employer ? -1 : a.employer > b.employer ? 1 : 0) || (a.title < b.title ? -1 : a.title > b.title ? 1 : 0) ||
        (a.posting_id < b.posting_id ? -1 : 1);
    });
  }

  // ---- controls ----
  const employers = Array.from(new Set(open.map(function (r) { return r.employer; }))).sort();
  const topPlaces = Calc.topLocations(open, { n: 60 }).map(function (l) { return l.name; });
  const results = el('div', { class: 'card', 'aria-live': 'polite' });
  const count = el('p', { class: 'result-count' });
  const note = el('p', { class: 'muted', style: 'margin:-4px 0 8px;font-size:.875rem' });

  function render() {
    const list = visible();
    const shown = list.slice(0, state.limit);
    count.textContent = state.starred
      ? App.fmtInt(list.length) + ' on your shortlist (all filters except search are ignored here)'
      : App.fmtInt(list.length) + ' open posting' + (list.length === 1 ? '' : 's') + (state.role === 'mine' ? ' in your role' : '') + (state.region === 'us' ? ' in the United States' : '');
    // postings whose board gives no usable location are not shown as US; say how many are left out
    const unclear = state.region === 'us' && !state.starred ? open.filter(function (r) { return matches(r, true) && !Calc.isUS(r.location) && Calc.isUnclearLocation(r.location); }).length : 0;
    note.textContent = unclear ? App.fmtInt(unclear) + ' more ' + (unclear === 1 ? 'posting has' : 'postings have') + ' no clear location and ' + (unclear === 1 ? 'is' : 'are') + ' left out. Choose Worldwide to see ' + (unclear === 1 ? 'it' : 'them') + '.' : '';
    results.replaceChildren();
    if (!list.length) {
      results.append(el('p', { class: 'empty', text: state.starred ? 'Star a posting to save it here.' : 'No postings match. Try switching to All postings or clearing a filter.' }));
      return;
    }
    shown.forEach(function (r) { results.append(jobRow(r)); });
    if (list.length > shown.length) {
      results.append(el('button', { class: 'link-btn', type: 'button', onclick: function () { state.limit += 100; render(); } },
        'Show 100 more (' + App.fmtInt(list.length - shown.length) + ' left)'));
    }
  }

  function jobRow(r) {
    const star = el('button', { class: 'star', type: 'button', 'aria-pressed': String(shortlist.has(r.posting_id)),
      'aria-label': 'Shortlist: ' + r.title, title: 'Save to shortlist' }, shortlist.has(r.posting_id) ? '★' : '☆');
    star.addEventListener('click', function () {
      if (shortlist.has(r.posting_id)) shortlist.delete(r.posting_id); else shortlist.add(r.posting_id);
      saveShortlist();
      starCount.textContent = shortlist.size;
      if (state.starred) render();
      else { star.setAttribute('aria-pressed', String(shortlist.has(r.posting_id))); star.textContent = shortlist.has(r.posting_id) ? '★' : '☆'; }
    });
    // first-run postings were already open when watching began, so only a minimum is known
    const days = r.status === 'removed' ? 'removed ' + r.removed_date
      : r.first_run ? 'open before tracking began'
      : 'open ' + r.days_open + ' day' + (r.days_open === 1 ? '' : 's');
    return el('div', { class: 'job' },
      el('div', { class: 'title' }, r.title || '(untitled)', r.in_role ? el('span', { class: 'role-tag', text: 'Your role' }) : null),
      el('div', { class: 'actions' }, star,
        r.status === 'open' ? el('a', { class: 'apply', href: r.url, target: '_blank', rel: 'noopener noreferrer' }, 'Apply') : el('span', { class: 'muted', text: 'Closed' })),
      el('div', { class: 'meta', text: [r.employer, r.location, 'first seen ' + r.first_seen, days].filter(Boolean).join(' · ') }));
  }

  const changed = function () { state.limit = 100; render(); };
  const select = function (label, options, key) {
    const s = el('select', null, options.map(function (o) { return el('option', { value: o[0], text: o[1] }); }));
    s.addEventListener('change', function () { state[key] = s.value; changed(); });
    return el('label', null, label, s);
  };
  let timer;
  const text = function (label, key, attrs) {
    const i = el('input', Object.assign({ type: 'search', autocomplete: 'off' }, attrs));
    i.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state[key] = i.value.trim(); changed(); }, 150); });
    return el('label', null, label, i);
  };

  const starCount = el('span', { text: shortlist.size });
  const starBtn = el('button', { class: 'seg-switch', type: 'button', 'aria-pressed': 'false',
    style: 'font:inherit;padding:8px 14px;background:var(--surface);color:var(--ink);cursor:pointer;min-height:40px' }, '★ Shortlist (', starCount, ')');
  starBtn.addEventListener('click', function () {
    state.starred = !state.starred;
    starBtn.setAttribute('aria-pressed', String(state.starred));
    starBtn.style.background = state.starred ? 'var(--accent)' : 'var(--surface)';
    starBtn.style.color = state.starred ? 'var(--accent-ink)' : 'var(--ink)';
    changed();
  });

  const locList = el('datalist', { id: 'places' }, topPlaces.map(function (p) { return el('option', { value: p }); }));
  root.append(
    el('header', { class: 'page-head' }, el('h1', { text: 'Browse' }),
      el('p', { class: 'muted', text: 'Open postings as of ' + lastRun + '. Your role means entry-level FP&A and wealth management titles. Jobs are limited to the United States unless you choose Worldwide.' })),
    el('section', { class: 'card' },
      el('div', { class: 'chips' },
        App.switcher([{ value: 'mine', label: 'My role' }, { value: 'all', label: 'All postings' }], state.role, function (v) { state.role = v; changed(); }, 'Which postings'),
        App.switcher([{ value: 'us', label: 'United States' }, { value: 'dfw', label: 'DFW' }, { value: 'nwa', label: 'NW Arkansas' }, { value: 'ar', label: 'All Arkansas' }, { value: 'all', label: 'Worldwide' }],
          state.region, function (v) { state.region = v; changed(); }, 'Region'),
        starBtn),
      el('div', { class: 'controls' },
        text('Search titles', 'q', { placeholder: 'e.g. FP&A, wealth, analyst', 'aria-label': 'Search titles' }),
        select('Employer', [['', 'All employers']].concat(employers.map(function (e) { return [e, e]; })), 'employer'),
        el('label', null, 'Location', (function () {
          const i = el('input', { type: 'search', list: 'places', placeholder: 'City or state', autocomplete: 'off' });
          i.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state.location = i.value.trim(); changed(); }, 150); });
          return i;
        })(), locList),
        select('Days open', [['', 'Any'], ['0-1', '0 to 1 day'], ['2-7', '2 to 7 days'], ['8-14', '8 to 14 days'], ['15-30', '15 to 30 days'], ['31+', '31 days or more']], 'days'),
        select('Sort by first seen', [['new', 'Newest first'], ['old', 'Oldest first']], 'sort'))),
    count, note, results);
  render();
});
