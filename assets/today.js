/* Today page: last run, source status, the four counts, new and removed postings. */
App.boot('today', function (root, data) {
  const el = App.el;
  const rows = data.rows, status = data.status;
  const runDate = status.run_time.slice(0, 10);
  const newRows = rows.filter(function (r) { return r.first_seen === runDate && !r.first_run; });
  const removedRows = rows.filter(function (r) { return r.removed_date === runDate; });
  const employerOf = {};
  rows.forEach(function (r) { employerOf[r.source] = r.employer; });

  const when = new Date(status.run_time);
  root.append(el('header', { class: 'page-head' },
    el('h1', { text: 'Today' }),
    el('p', { class: 'muted' }, 'Last run ',
      el('strong', { text: when.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }),
      ' (' + status.run_time.replace('T', ' ').replace('Z', ' UTC') + ')')));

  const tile = function (label, value) {
    return el('div', { class: 'tile' }, el('div', { class: 'label', text: label }), el('div', { class: 'value', text: App.fmtInt(value) }));
  };
  root.append(el('section', { class: 'tiles', 'aria-label': 'Counts from the latest run' },
    tile('Days with a successful run', status.days_with_success),
    tile('Open postings', status.open),
    tile('New today', status.new_today),
    tile('Removed today', status.removed_today)));

  if (status.days_with_success === 1) {
    root.append(el('p', { class: 'notice' },
      'This is the first run. Postings already open when watching began are the baseline, so nothing counts as new or removed until tomorrow.'));
  }

  // source status: failed sources first so a problem is the first thing you see
  const sources = status.sources.slice().sort(function (a, b) {
    return (a.ok - b.ok) || (a.name < b.name ? -1 : 1);
  });
  const failed = sources.filter(function (s) { return !s.ok; }).length;
  root.append(el('section', { class: 'card' },
    el('h2', { text: 'Sources' }),
    el('p', { class: 'muted', text: failed ? failed + ' of ' + sources.length + ' sources failed in the latest run. Their postings are left unchanged for today.'
      : 'All ' + sources.length + ' sources answered in the latest run.' }),
    el('div', { style: 'overflow-x:auto' }, el('table', null,
      el('thead', null, el('tr', null, el('th', { scope: 'col', text: 'Employer' }), el('th', { scope: 'col', text: 'Source' }),
        el('th', { scope: 'col', text: 'Status' }), el('th', { scope: 'col', class: 'num', text: 'Postings' }))),
      el('tbody', null, sources.map(function (s) {
        return el('tr', null,
          el('td', { text: employerOf[s.name] || s.name }),
          el('td', { class: 'muted', text: s.name }),
          el('td', null, el('span', { class: 'badge ' + (s.ok ? 'ok' : 'fail') }, s.ok ? '✓ Working' : '✕ Failed')),
          el('td', { class: 'num', text: s.ok ? App.fmtInt(s.count) : '-' }));
      }))))));

  function postingList(list) {
    const sorted = list.slice().sort(function (a, b) {
      return (b.in_role - a.in_role) || (a.employer < b.employer ? -1 : a.employer > b.employer ? 1 : 0) || (a.title < b.title ? -1 : 1);
    });
    const item = function (r) {
      return el('li', null,
        el('a', { href: r.url, target: '_blank', rel: 'noopener noreferrer', text: r.title || '(untitled)' }),
        r.in_role ? el('span', { class: 'role-tag', text: 'Your role' }) : null,
        el('span', { class: 'meta', text: r.employer + (r.location ? ' · ' + r.location : '') }));
    };
    const shown = sorted.slice(0, 40), rest = sorted.slice(40);
    const box = el('div', null, el('ul', { class: 'postings' }, shown.map(item)));
    if (rest.length) {
      box.append(el('details', null, el('summary', { text: 'Show the other ' + App.fmtInt(rest.length) }),
        el('ul', { class: 'postings' }, rest.map(item))));
    }
    return box;
  }

  const section = function (title, list, none) {
    return el('section', { class: 'card' },
      el('h2', { text: title + ' (' + App.fmtInt(list.length) + ')' }),
      list.length ? postingList(list) : el('p', { class: 'muted', text: none }));
  };
  root.append(section('New postings', newRows, 'No postings first seen in the latest run.'));
  root.append(section('Removed postings', removedRows, 'No postings removed in the latest run.'));
});
