/* Pure calculations on data/history.csv. No DOM access, so the same code runs in the
   browser and under Node (tests/test_market_calc.py checks it against Python).
   Dates are UTC 'YYYY-MM-DD' strings. */
(function (root) {
  'use strict';

  // ------------------------------------------------------------------ parsing
  function parseCSV(text) {
    const rows = [];
    let row = [], field = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; } else { quoted = false; }
        } else { field += c; }
      } else if (c === '"') { quoted = true; }
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c !== '\r') { field += c; }
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }
    return rows;
  }

  function parseHistory(text) {
    const table = parseCSV(text);
    if (!table.length) return [];
    const head = table[0];
    return table.slice(1).filter(function (r) { return r.length === head.length; }).map(function (r) {
      const o = {};
      head.forEach(function (h, i) { o[h] = r[i]; });
      o.in_role = o.in_role === 'true';
      o.first_run = o.first_run === 'true';
      return o;
    });
  }

  // -------------------------------------------------------------------- dates
  function dayNum(s) {
    const p = s.split('-');
    return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 864e5;
  }
  function addDays(s, n) { return new Date((dayNum(s) + n) * 864e5).toISOString().slice(0, 10); }
  function diffDays(a, b) { return dayNum(b) - dayNum(a); }
  function eachDay(a, b) {
    const out = [];
    for (let d = a; d <= b; d = addDays(d, 1)) out.push(d);
    return out;
  }

  /* The last run is the latest day any posting was listed, removed or first seen. */
  function lastRunDate(rows) {
    let last = '';
    rows.forEach(function (r) {
      [r.last_seen, r.first_seen, r.removed_date].forEach(function (d) { if (d > last) last = d; });
    });
    return last;
  }
  function firstDate(rows) {
    let first = '';
    rows.forEach(function (r) { if (r.first_seen && (!first || r.first_seen < first)) first = r.first_seen; });
    return first;
  }

  function median(values) {
    if (!values.length) return null;
    const s = values.slice().sort(function (a, b) { return a - b; });
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  // ---------------------------------------------------------------- regions
  const REGIONS = {
    dfw: /\b(dallas|fort worth|ft\.? worth|plano|irving|frisco|addison|richardson|southlake|las colinas|carrollton|denton|mckinney|lewisville|grapevine|westlake|coppell|garland|mesquite|euless|colleyville|flower mound|the colony|rockwall|prosper|dfw)\b|\barlington,\s*(tx|texas)\b|\ballen,\s*(tx|texas)\b|\bbedford,\s*(tx|texas)\b/i,
    nwa: /\b(bentonville|rogers|springdale|fayetteville|lowell|bella vista|siloam springs|centerton|cave springs|northwest arkansas|nwa)\b/i,
    ar: /\b(arkansas|little rock|bentonville|rogers|springdale|fayetteville|lowell|bella vista|siloam springs|centerton|cave springs|north little rock|conway|fort smith|jonesboro)\b|,\s*ar\b/i
  };
  // ---- is a location in the United States? ----
  // Order matters: an explicit "United States" wins; a country name rules a place out;
  // a US state (abbreviation or name) makes it US even for towns that share a foreign
  // name ("London, KY"); then well-known foreign cities; then well-known US cities written
  // without a state. Anything left is unknown and counts as not US.
  const US_ABBR = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR'.split(' ');
  // String.raw keeps the backslashes; case-sensitive on purpose ("In" is not Indiana)
  const US_ABBR_RE = new RegExp(String.raw`(?:^|[\s,/(-])(` + US_ABBR.join('|') + String.raw`)(?=$|[\s,/)-])`);
  const US_STATE_RE = /\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|puerto rico|district of columbia|georgia)\b/i;
  const US_WORD_RE = /\b(united states|usa|u\.s\.a?\.?)(?!\w)/i;
  const COUNTRY_RE = /\b(united kingdom|uk|england|scotland|wales|ireland|india|china|hong kong|japan|singapore|philippines|poland|germany|france|netherlands|spain|switzerland|luxembourg|canada|quebec|british columbia|alberta|brazil|argentina|colombia|chile|peru|australia|new zealand|israel|emirates|uae|korea|taiwan|malaysia|thailand|vietnam|indonesia|italy|belgium|sweden|norway|denmark|finland|austria|czech|romania|hungary|portugal|greece|turkey(?! plant)|egypt|south africa|nigeria|kenya|saudi arabia|qatar|bahrain|costa rica|panama|prince edward island|nova scotia|new brunswick|manitoba|saskatchewan|newfoundland)\b|(?<!new )\bmexico\b|\bontario\b(?!,?\s*CA\b)/i;
  const FOREIGN_CITY_RE = /\b(london|mumbai|bangalore|bengaluru|hyderabad|gurugram|gurgaon|chennai|pune|noida|tokyo|manila|cluj|edinburgh|glasgow|krakow|warsaw|warszawa|gdansk|toronto|nottingham|bournemouth|dublin|kilkenny|sydney|melbourne|frankfurt|paris|geneve|geneva|zurich|shanghai|beijing|shenzhen|hangzhou|seoul|taipei|kuala lumpur|buenos aires|sao paulo|alabang|tbilisi|eng)\b/i;
  const US_CITY_RE = /\b(arlington|pnc plaza|tysons corner|boston|dallas|fort worth|new york|nyc|chicago|tempe|charlotte|fort mill(?:charlotte)?|san francisco|houston|austin|atlanta|denver|seattle|los angeles|philadelphia|pittsburgh|minneapolis|miami|phoenix|irving|plano|columbus|cleveland|princeton|wilmington|jersey city|newark|mclean|richmond|nashville|san antonio|san diego|san jose|baltimore|washington|detroit|st\.? louis|kansas city|salt lake city|las vegas|portland|raleigh|tampa|orlando|jacksonville|indianapolis|cincinnati|milwaukee|omaha|little rock|bentonville|springdale|rogers|fayetteville)\b/i;

  // Canadian provinces written as abbreviations ("Markham, ON", "ON; BC")
  const CA_PROVINCE_RE = new RegExp(String.raw`(?:^|[\s,;/(-])(ON|BC|QC|AB|NS|NB|MB|SK|PE|NL)(?=$|[\s,;/)-])`);

  function isUS(location) {
    const t = (location || '').replace(/\(\+\d+ more\)/, '').trim();
    if (!t) return false;
    if (US_WORD_RE.test(t)) return true;
    if (/\btbilisi\b/i.test(t)) return false;                 // Georgia the country
    if (COUNTRY_RE.test(t) || CA_PROVINCE_RE.test(t)) return false;
    if (US_ABBR_RE.test(t) || US_STATE_RE.test(t)) return true;
    if (FOREIGN_CITY_RE.test(t)) return false;
    return US_CITY_RE.test(t);
  }

  // a posting whose board gave no usable place (empty or just "Multiple locations")
  function isUnclearLocation(location) {
    const t = (location || '').trim().toLowerCase();
    return t === '' || t === 'multiple locations' || t === 'remote - national';
  }

  function inRegion(location, region) {
    if (!region || region === 'all') return true;
    if (region === 'us') return isUS(location);
    return REGIONS[region].test(location || '');
  }

  // ------------------------------------------------------------ market numbers
  function countBy(rows, key) {
    const m = new Map();
    rows.forEach(function (r) { const k = key(r); m.set(k, (m.get(k) || 0) + 1); });
    return m;
  }
  /* Every series spans the whole history, first run to last run, so charts line up. */
  function series(allRows, rows, dateOf, last) {
    const first = firstDate(allRows);
    const days = first ? eachDay(first, last) : [];
    const m = countBy(rows.filter(function (r) { return dateOf(r); }), dateOf);
    return { days: days, counts: days.map(function (d) { return m.get(d) || 0; }) };
  }

  /* 1. Postings first seen each day, leaving out first-run postings. */
  function newPerDay(rows, last, roleOnly) {
    return series(rows, rows.filter(function (r) { return !r.first_run && (!roleOnly || r.in_role); }),
      function (r) { return r.first_seen; }, last);
  }

  /* 2. Postings with a removed date on each day. */
  function removedPerDay(rows, last) {
    return series(rows, rows.filter(function (r) { return r.removed_date; }),
      function (r) { return r.removed_date; }, last);
  }

  /* 3. Open postings per employer as of the last run. */
  function openByEmployer(rows, roleOnly, region) {
    const m = countBy(rows.filter(function (r) { return r.status === 'open' && (!roleOnly || r.in_role) && inRegion(r.location, region); }),
      function (r) { return r.employer; });
    return Array.from(m, function (e) { return { name: e[0], count: e[1] }; })
      .sort(function (a, b) { return b.count - a.count || (a.name < b.name ? -1 : 1); });
  }

  /* 4. Days open: removed, not first-run postings; removed date minus first-seen date. */
  function daysOpen(rows) {
    return rows.filter(function (r) { return r.status === 'removed' && r.removed_date && !r.first_run; })
      .map(function (r) { return diffDays(r.first_seen, r.removed_date); });
  }

  /* 5. Of postings that are not first-run and were first seen at least seven days before
        the last run, the share whose removed date minus first-seen date is seven days or less. */
  function removedWithinSeven(rows, last) {
    const eligible = rows.filter(function (r) { return !r.first_run && diffDays(r.first_seen, last) >= 7; });
    const quick = function (r) { return r.status === 'removed' && r.removed_date && diffDays(r.first_seen, r.removed_date) <= 7; };
    const removed = eligible.filter(quick).length;
    const by = new Map();
    eligible.forEach(function (r) {
      const e = by.get(r.employer) || { name: r.employer, eligible: 0, removed: 0 };
      e.eligible++;
      if (quick(r)) e.removed++;
      by.set(r.employer, e);
    });
    const byEmployer = Array.from(by.values()).map(function (e) { e.share = e.removed / e.eligible; return e; })
      .sort(function (a, b) { return b.share - a.share || b.eligible - a.eligible || (a.name < b.name ? -1 : 1); });
    return { eligible: eligible.length, removed: removed, share: eligible.length ? removed / eligible.length : null, byEmployer: byEmployer };
  }

  /* 6. Top locations among open postings (optionally within a region or only my role). */
  function topLocations(rows, opts) {
    opts = opts || {};
    // "McLean VA (+3 more)", "McLean, VA" and "McLean, VA, United States" are one place: group on
    // letters and digits, drop a trailing country, and write a trailing state name as its abbreviation
    const STATES = { alabama: 'al', alaska: 'ak', arizona: 'az', arkansas: 'ar', california: 'ca', colorado: 'co', connecticut: 'ct', delaware: 'de', florida: 'fl', georgia: 'ga', hawaii: 'hi', idaho: 'id', illinois: 'il', indiana: 'in', iowa: 'ia', kansas: 'ks', kentucky: 'ky', louisiana: 'la', maine: 'me', maryland: 'md', massachusetts: 'ma', michigan: 'mi', minnesota: 'mn', mississippi: 'ms', missouri: 'mo', montana: 'mt', nebraska: 'ne', nevada: 'nv', 'new hampshire': 'nh', 'new jersey': 'nj', 'new mexico': 'nm', 'new york': 'ny', 'north carolina': 'nc', 'north dakota': 'nd', ohio: 'oh', oklahoma: 'ok', oregon: 'or', pennsylvania: 'pa', 'rhode island': 'ri', 'south carolina': 'sc', 'south dakota': 'sd', tennessee: 'tn', texas: 'tx', utah: 'ut', vermont: 'vt', virginia: 'va', washington: 'wa', 'west virginia': 'wv', wisconsin: 'wi', wyoming: 'wy' };
    const key = function (l) {
      let k = l.replace(/\(\+\d+ more\)/, '').toLowerCase().replace(/\b(united states|usa)\b/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
      Object.keys(STATES).forEach(function (n) {
        if (k.length > n.length + 1 && k.slice(-(n.length + 1)) === ' ' + n) k = k.slice(0, -n.length) + STATES[n];
      });
      return k;
    };
    // prefer the tidy "City, ST" spelling as the label
    const tidy = function (l) { return /^[^,]+, [A-Z]{2}$/.test(l) ? 2 : l.indexOf(',') >= 0 ? 1 : 0; };
    const places = new Map();
    rows.forEach(function (r) {
      if (r.status !== 'open' || (opts.roleOnly && !r.in_role) || !r.location || !inRegion(r.location, opts.region)) return;
      const k = key(r.location);
      const label = r.location.replace(/\s*\(\+\d+ more\)/, '');
      const p = places.get(k) || { name: label, count: 0, score: -1 };
      p.count++;
      if (tidy(label) > p.score) { p.name = label; p.score = tidy(label); }
      places.set(k, p);
    });
    return Array.from(places.values(), function (p) { return { name: p.name, count: p.count }; })
      .sort(function (a, b) { return b.count - a.count || (a.name < b.name ? -1 : 1); })
      .slice(0, opts.n || 10);
  }

  const api = {
    parseCSV: parseCSV, parseHistory: parseHistory, dayNum: dayNum, addDays: addDays,
    diffDays: diffDays, eachDay: eachDay, lastRunDate: lastRunDate, firstDate: firstDate,
    median: median, inRegion: inRegion, isUS: isUS, isUnclearLocation: isUnclearLocation, REGIONS: REGIONS, newPerDay: newPerDay,
    removedPerDay: removedPerDay, openByEmployer: openByEmployer, daysOpen: daysOpen,
    removedWithinSeven: removedWithinSeven, topLocations: topLocations
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Calc = api;
})(typeof self !== 'undefined' ? self : this);
