/* Market page: a report on the history file. Every number is computed here, in the
   browser, from data/history.csv, so the page changes as the history grows.
   First-run postings were already open when watching began, so their start date is
   unknown and they are left out where the definitions below say so. */
App.boot('market', function (root, data) {
  const el = App.el, fmt = App.fmtInt;
  const rows = data.rows;
  const last = Calc.lastRunDate(rows);
  const first = Calc.firstDate(rows);
  if (!rows.length) { root.append(el('p', { class: 'notice', text: 'The history file is empty. Come back after the first run.' })); return; }
  const span = Calc.diffDays(first, last);
  const sum = function (a) { return a.reduce(function (s, x) { return s + x; }, 0); };
  const plural = function (n, w) { return fmt(n) + ' ' + w + (n === 1 ? '' : 's'); };

  root.append(el('header', { class: 'page-head' }, el('h1', { text: 'Market' }),
    el('p', { class: 'muted', text: 'Built from ' + fmt(rows.length) + ' postings seen from ' + first + ' to ' + last + ' (' + plural(span + 1, 'day') + ' of history). "Your role" means entry-level FP&A and wealth management titles. Only jobs located in the United States are tracked.' })));

  function section(heading, paragraph, content) {
    root.append(el('section', { class: 'market-section' }, el('h2', { text: heading }), el('p', { text: paragraph }), content));
  }

  // 1. New postings per day --------------------------------------------------
  (function () {
    const all = Calc.newPerDay(rows, last, false), mine = Calc.newPerDay(rows, last, true);
    const totalAll = sum(all.counts), totalMine = sum(mine.counts);
    const heading = totalAll === 0
      ? 'No new postings yet: the first run only set the baseline'
      : fmt(totalAll) + ' new postings in ' + plural(span, 'day') + ', ' + fmt(totalMine) + ' of them in your role';
    section(heading,
      'New postings are those first seen on each day. Postings that were already open on the first run are left out, because their real start date is unknown. ' +
      (span < 1 ? 'There is only one day of history so far, so every posting counts as baseline; new postings appear from tomorrow.' :
        'On average that is ' + (totalAll / span).toFixed(1) + ' a day across all postings and ' + (totalMine / span).toFixed(1) + ' a day in your role.'),
      el('div', { class: 'charts-2' },
        Charts.columns({ title: 'All postings', subtitle: 'New per day', days: all.days, counts: all.counts, color: 'all' }),
        Charts.columns({ title: 'Your role', subtitle: 'New per day', days: mine.days, counts: mine.counts, color: 'role' })));
  })();

  // 2. Removed postings per day ----------------------------------------------
  (function () {
    const s = Calc.removedPerDay(rows, last);
    const total = sum(s.counts);
    let peak = 0;
    s.counts.forEach(function (c, i) { if (c > s.counts[peak]) peak = i; });
    section(total === 0 ? 'No postings have been removed yet' : fmt(total) + ' postings were removed, most on ' + App.fmtShortDate(s.days[peak]) + ' (' + fmt(s.counts[peak]) + ')',
      'A posting is removed on the first day its employer\'s board has a file and no longer lists it. A posting that comes back is open again and drops out of this count. ' +
      'Removed postings include ones that were open before watching began, since the removal date is known either way.',
      Charts.columns({ title: 'All postings', subtitle: 'Removed per day', days: s.days, counts: s.counts, color: 'all' }));
  })();

  // 3. Open postings per employer --------------------------------------------
  (function () {
    const holder = el('div');
    const note = el('p');
    const wrap = el('section', { class: 'market-section' });
    const h = el('h2');
    let role = 'all';
    function draw() {
      const items = Calc.openByEmployer(rows, role === 'mine');
      const total = sum(items.map(function (i) { return i.count; }));
      h.textContent = items.length
        ? items[0].name + ' has the most open postings (' + fmt(items[0].count) + ' of ' + fmt(total) + ')'
        : 'No open postings match';
      note.textContent = 'Open postings per employer as of the last run (' + last + ')' + ', counting every US-based posting the employer\'s board returns' + (role === 'mine' ? ', and only titles in your role.' : '.');
      holder.replaceChildren(Charts.bars({ title: role === 'mine' ? 'Your role' : 'All postings', subtitle: 'Open per employer', items: items, color: role === 'mine' ? 'role' : 'all', valueHeader: 'Open postings', emptyText: 'No open postings in your role yet.' }));
    }
    wrap.append(h, note, el('div', { class: 'scope' }, App.switcher([{ value: 'all', label: 'All postings' }, { value: 'mine', label: 'My role' }], role, function (v) { role = v; draw(); }, 'Which postings')), holder);
    root.append(wrap);
    draw();
  })();

  // 4. Days open ---------------------------------------------------------------
  (function () {
    const days = Calc.daysOpen(rows);
    const med = Calc.median(days);
    const bands = [['0-1 days', 0, 1], ['2-3', 2, 3], ['4-7', 4, 7], ['8-14', 8, 14], ['15-30', 15, 30], ['31+', 31, Infinity]];
    const items = bands.map(function (b) { return { name: b[0] + (b[0].indexOf('days') < 0 ? ' days' : ''), count: days.filter(function (d) { return d >= b[1] && d <= b[2]; }).length }; });
    section(med === null ? 'No removed postings yet, so days open cannot be measured' : 'Removed postings were open a median of ' + (med % 1 ? med.toFixed(1) : med) + ' days',
      'Days open is the removed date minus the first-seen date, for removed postings that are not first-run postings (those have an unknown start). The median is the middle value, so a few long-lived postings do not skew it. ' +
      (med === null ? '' : 'It is based on ' + plural(days.length, 'posting') + '.'),
      Charts.bars({ title: 'Removed postings', subtitle: 'How long they were open', items: items, color: 'all', valueHeader: 'Postings', emptyText: 'Nothing removed yet.' }));
  })();

  // 5. Share removed within seven days ------------------------------------------
  (function () {
    const r = Calc.removedWithinSeven(rows, last);
    const pct = r.share === null ? null : App.fmtPct(r.share);
    section(r.share === null ? 'Too early to say how many postings disappear within a week' : pct + ' of postings were removed within seven days',
      'Among postings that are not first-run postings and were first seen at least seven days before the last run, this is the share whose removed date minus first-seen date is seven days or less. ' +
      (r.share === null ? 'Seven days of history are needed before any posting qualifies.' : fmt(r.removed) + ' of ' + fmt(r.eligible) + ' qualifying postings were gone within a week.'),
      el('div', { class: 'charts-2' },
        Charts.segmented({ title: 'All employers', subtitle: 'Qualifying postings', emptyText: 'No posting is old enough yet.',
          parts: [{ name: 'Removed within 7 days', value: r.removed, cls: 'hit' }, { name: 'Still open or open longer', value: r.eligible - r.removed, cls: 'rest' }] }),
        Charts.bars({ title: 'By employer', subtitle: 'Share removed within 7 days (employers with 5+ qualifying postings)',
          items: r.byEmployer.filter(function (e) { return e.eligible >= 5; }).slice(0, 12).map(function (e) { return { name: e.name, count: e.share, removed: e.removed, eligible: e.eligible }; }),
          format: function (x) { return App.fmtPct(x); }, valueHeader: 'Share', color: 'all', emptyText: 'No employer has 5 qualifying postings yet.',
          tipText: function (it) { return it.name + ': ' + fmt(it.removed) + ' of ' + fmt(it.eligible) + ' (' + App.fmtPct(it.count) + ')'; } })));
  })();

  // 6. Top locations ----------------------------------------------------------------
  (function () {
    const holder = el('div'), h = el('h2'), note = el('p');
    const wrap = el('section', { class: 'market-section' });
    let region = 'all', role = 'all';
    const names = { all: 'the United States', dfw: 'the Dallas-Fort Worth area', nwa: 'Northwest Arkansas', ar: 'Arkansas' };
    function draw() {
      const items = Calc.topLocations(rows, { region: region, roleOnly: role === 'mine', n: 10 });
      h.textContent = items.length ? items[0].name + ' leads with ' + fmt(items[0].count) + ' open postings' : 'No open postings in ' + names[region];
      note.textContent = 'The ten locations with the most open postings in ' + names[region] + (role === 'mine' ? ', counting only titles in your role' : '') +
        '. Locations are shown as each employer\'s board writes them; a posting listed in several places is counted under its first location.';
      holder.replaceChildren(Charts.bars({ title: role === 'mine' ? 'Your role' : 'All postings', subtitle: 'Top locations among open postings', items: items,
        color: role === 'mine' ? 'role' : 'all', valueHeader: 'Open postings', emptyText: 'Nothing open here yet.' }));
    }
    wrap.append(h, note,
      el('div', { class: 'scope' },
        App.switcher([{ value: 'all', label: 'All US' }, { value: 'dfw', label: 'DFW' }, { value: 'nwa', label: 'NW Arkansas' }, { value: 'ar', label: 'All Arkansas' }], region, function (v) { region = v; draw(); }, 'Region'),
        App.switcher([{ value: 'all', label: 'All postings' }, { value: 'mine', label: 'My role' }], role, function (v) { role = v; draw(); }, 'Which postings')),
      holder);
    root.append(wrap);
    draw();
  })();
});
