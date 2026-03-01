/**
 * Data Story — main orchestrator.
 * Loads data, computes stats, renders all sections except the heat matrix.
 */

DataLoader.basePath = '../data/';

const CRISIS_EVENTS = [
  {
    month: '2013-09',
    iso3: 'SYR',
    headline: 'Syria\'s Chemical Weapons Crisis',
    context: 'Reports of the Assad regime\'s sarin attacks trigger a wave of congressional resolutions. Syria vaults from obscurity to the top of the legislative agenda in a single month.',
  },
  {
    month: '2015-07',
    iso3: 'IRN',
    headline: 'The Iran Nuclear Deal',
    context: 'The Joint Comprehensive Plan of Action (JCPOA) dominates congressional debate across the entire 114th Congress. Iran holds the #1 spot for more months in this era than any other country in the dataset.',
  },
  {
    month: '2021-08',
    iso3: 'AFG',
    headline: 'The Fall of Kabul',
    context: 'The U.S. withdrawal and the Taliban\'s rapid seizure of Kabul drives the highest single-month Afghanistan mention count in the dataset — a twenty-year war closing in a matter of days.',
  },
  {
    month: '2022-02',
    iso3: 'UKR',
    headline: 'Russia Invades Ukraine',
    context: 'The most dramatic surge in the dataset. Ukraine goes from absent to #1 in a single month as Congress responds to the full-scale invasion with sanctions, aid packages, and resolutions.',
  },
  {
    month: '2023-10',
    iso3: 'ISR',
    headline: 'Hamas Attacks Israel',
    context: 'The October 7 attacks and the ensuing Gaza war send both Israel and Palestine to the top of the congressional agenda simultaneously — an unusual co-surge of two entangled countries.',
  },
  {
    month: '2024-08',
    iso3: 'VEN',
    headline: 'Venezuela\'s Stolen Election',
    context: 'Nicolás Maduro\'s disputed reelection and the regime\'s violent crackdown on protesters push Venezuela into the spotlight, producing one of the sharpest out-of-nowhere surges in the record.',
  },
];

const ERA_EVENTS = {
  113: 'Syria chemical weapons, Russia annexes Crimea',
  114: 'Iran nuclear deal, Cuba trade normalization',
  115: 'Russia-Trump sanctions, U.S.–China trade war begins',
  116: 'COVID-19 emerges, China competition intensifies',
  117: 'Afghanistan withdrawal, Russia invades Ukraine',
  118: 'Israel-Hamas war, China competition bill',
  119: 'China tariffs, Ukraine aid debate',
};

async function init() {
  const { monthlyTop, monthlyAll, metadata } = await DataLoader.loadAll();

  const months = Object.keys(monthlyAll).sort();
  const countryMeta = buildCountryMeta(monthlyAll);
  const totals = computeTotals(monthlyAll);

  renderStatCards(metadata, months, totals, countryMeta);
  renderBarChart(totals, countryMeta);
  renderEraGrid(monthlyAll, countryMeta, months);
  renderCrisisTimeline(monthlyAll, countryMeta);
  renderHeatMatrix(monthlyAll, totals, countryMeta, months);

  const updated = metadata.last_run ? metadata.last_run.slice(0, 10) : '';
  if (updated) document.getElementById('last-update').textContent = `Data last updated ${updated}`;
}

// ── Utility ───────────────────────────────────────────────────────────────────

function buildCountryMeta(allData) {
  const meta = {};
  for (const entry of Object.values(allData)) {
    for (const c of (entry.countries || [])) {
      if (!meta[c.iso3]) meta[c.iso3] = { iso2: c.iso2, name: c.name };
    }
  }
  return meta;
}

function computeTotals(allData) {
  const totals = {};
  for (const entry of Object.values(allData)) {
    for (const c of (entry.countries || [])) {
      totals[c.iso3] = (totals[c.iso3] || 0) + c.count;
    }
  }
  return totals;
}

function flagSrc(iso2) {
  return `../flags/${(iso2 || 'xx').toLowerCase()}.svg`;
}

// ── Stat Cards ────────────────────────────────────────────────────────────────

function renderStatCards(metadata, months, totals, countryMeta) {
  document.getElementById('stat-months').textContent = months.length;
  document.getElementById('stat-mentions').textContent =
    (metadata.total_mentions_detected || 0).toLocaleString();
  document.getElementById('stat-countries').textContent =
    Object.keys(totals).length;

  const top = Object.entries(totals).sort((a, b) => b[1] - a[1])[0];
  if (top) {
    const name = countryMeta[top[0]]?.name || top[0];
    document.getElementById('stat-leader').textContent = name;
  }
}

// ── Bar Chart ─────────────────────────────────────────────────────────────────

function renderBarChart(totals, countryMeta) {
  const sorted = Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  const max = sorted[0][1];
  const container = document.getElementById('bar-chart');

  for (const [iso3, count] of sorted) {
    const meta = countryMeta[iso3] || {};
    const pct = (count / max * 100).toFixed(1);

    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <img class="bar-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || iso3}" />
      <span class="bar-country">${meta.name || iso3}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      <span class="bar-count">${count}</span>
    `;
    container.appendChild(row);
  }
}

// ── Era Grid ──────────────────────────────────────────────────────────────────

function renderEraGrid(allData, countryMeta, months) {
  const ERAS = [
    { congress: 113, start: '2013-01', end: '2015-01' },
    { congress: 114, start: '2015-01', end: '2017-01' },
    { congress: 115, start: '2017-01', end: '2019-01' },
    { congress: 116, start: '2019-01', end: '2021-01' },
    { congress: 117, start: '2021-01', end: '2023-01' },
    { congress: 118, start: '2023-01', end: '2025-01' },
    { congress: 119, start: '2025-01', end: '2027-01' },
  ];

  const grid = document.getElementById('era-grid');

  for (const era of ERAS) {
    const eraMonths = months.filter(m => m >= era.start && m < era.end);
    if (eraMonths.length === 0) continue;

    const eraTotals = {};
    for (const m of eraMonths) {
      for (const c of (allData[m]?.countries || [])) {
        eraTotals[c.iso3] = (eraTotals[c.iso3] || 0) + c.count;
      }
    }
    const topThree = Object.entries(eraTotals)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);

    const startYear = era.start.slice(0, 4);
    const endYear = String(parseInt(era.end.slice(0, 4)) - 1);

    const flagsHtml = topThree.map(([iso3]) => {
      const meta = countryMeta[iso3] || {};
      return `<img class="era-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || iso3}" title="${meta.name || iso3}" />`;
    }).join('');

    const leaderMeta = countryMeta[topThree[0]?.[0]] || {};
    const ordinals = { 113:'113th', 114:'114th', 115:'115th', 116:'116th', 117:'117th', 118:'118th', 119:'119th' };

    const card = document.createElement('div');
    card.className = 'era-card';
    card.innerHTML = `
      <div>
        <div class="era-congress">${ordinals[era.congress]}</div>
        <div class="era-years">${startYear}&ndash;${endYear}</div>
      </div>
      <div class="era-flags">${flagsHtml}</div>
      <div class="era-leader">${leaderMeta.name || ''} led</div>
      <div class="era-event">${ERA_EVENTS[era.congress] || ''}</div>
    `;
    grid.appendChild(card);
  }
}

// ── Crisis Timeline ───────────────────────────────────────────────────────────

function renderCrisisTimeline(allData, countryMeta) {
  const container = document.getElementById('crisis-timeline');

  for (const event of CRISIS_EVENTS) {
    const entry = allData[event.month];
    if (!entry) continue;

    const countryEntry = (entry.countries || []).find(c => c.iso3 === event.iso3);
    const rank = countryEntry
      ? (entry.countries || []).indexOf(countryEntry) + 1
      : null;
    const count = countryEntry?.count || 0;
    const titles = countryEntry?.sample_titles || [];
    const meta = countryMeta[event.iso3] || {};
    const rankLabel = rank === 1 ? '#1 that month' : rank ? `#${rank} that month` : 'mentioned';

    const titlesHtml = titles.slice(0, 3).map(t =>
      `<li>${t.length > 110 ? t.slice(0, 109) + '&hellip;' : t}</li>`
    ).join('');

    const card = document.createElement('article');
    card.className = 'crisis-card';
    card.innerHTML = `
      <div class="crisis-dateline">${DataLoader.formatMonthLong(event.month)}</div>
      <div class="crisis-header">
        <img class="crisis-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || event.iso3}" />
        <h3 class="crisis-headline">${event.headline}</h3>
      </div>
      <p class="crisis-context">${event.context}</p>
      <div class="crisis-stats">
        <span class="crisis-stat"><strong>${count}</strong> mentions</span>
        <span class="crisis-stat">${rankLabel}</span>
      </div>
      ${titles.length > 0 ? `<hr class="crisis-divider" /><ul class="crisis-samples">${titlesHtml}</ul>` : ''}
    `;
    container.appendChild(card);
  }
}

// ── Heat Matrix ───────────────────────────────────────────────────────────────

function renderHeatMatrix(allData, totals, countryMeta, months) {
  const top25 = Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 25)
    .map(([iso3]) => ({ iso3, ...countryMeta[iso3] }));

  HeatMatrix.render(
    allData,
    top25,
    months,
    document.getElementById('heat-matrix-container')
  );
}

// ── Boot ──────────────────────────────────────────────────────────────────────

init().catch(err => {
  console.error('Data story failed to load:', err);
  document.body.innerHTML += `<p style="color:red;padding:2rem">Failed to load data: ${err.message}</p>`;
});
