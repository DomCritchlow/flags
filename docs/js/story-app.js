/**
 * Congressional World View — Unified data story orchestrator.
 * Handles the interactive flag grid AND renders all data story sections below.
 */

(async function() {
  'use strict';

  // ── Crisis events for the timeline ──────────────────────────────────────────

  const CRISIS_EVENTS = [
    {
      month: '1979-11', iso3: 'IRN',
      headline: 'The Iran Hostage Crisis',
      context: 'When Iranian students storm the U.S. Embassy and take 52 Americans hostage, Iran becomes the dominant subject of the congressional record overnight. The crisis stretched 444 days, reshaping American foreign policy and dominating the late Carter and early Reagan years.',
    },
    {
      month: '1990-08', iso3: 'IRQ',
      headline: 'Iraq Invades Kuwait',
      context: 'Saddam Hussein\'s seizure of Kuwait forces a massive congressional reckoning. In the months leading to Operation Desert Storm, Congress holds the most consequential war debate since Vietnam, with Iraq and Kuwait both surging simultaneously in the legislative record.',
    },
    {
      month: '1999-03', iso3: 'SRB',
      headline: 'NATO Bombs Yugoslavia',
      context: 'The first time NATO attacked a sovereign European nation without U.N. authorization. Congress debates the legality of the air campaign over Kosovo, with sharp divisions over whether the President needs congressional approval to wage war.',
    },
    {
      month: '2001-09', iso3: 'AFG',
      headline: 'September 11 and the Afghanistan War',
      context: 'The most consequential single month in the modern congressional record. Within weeks of the attacks, Congress authorizes the use of military force, producing an instant surge in Afghanistan mentions that reshapes the legislative agenda for the next decade.',
    },
    {
      month: '2003-03', iso3: 'IRQ',
      headline: 'The Iraq War Begins',
      context: 'After months of debate over weapons of mass destruction and U.N. inspections, Congress and the country are consumed by the invasion. Iraq dominates the congressional record throughout the 108th Congress, from the shock of the initial assault through the emergence of the insurgency.',
    },
    {
      month: '2013-09', iso3: 'SYR',
      headline: 'Syria\'s Chemical Weapons Crisis',
      context: 'Reports of the Assad regime\'s sarin attacks trigger a wave of congressional resolutions. Syria vaults from obscurity to the top of the legislative agenda in a single month.',
    },
    {
      month: '2015-07', iso3: 'IRN',
      headline: 'The Iran Nuclear Deal',
      context: 'The Joint Comprehensive Plan of Action (JCPOA) dominates congressional debate across the entire 114th Congress. Iran holds the #1 spot for more months in this era than any other country on record.',
    },
    {
      month: '2021-08', iso3: 'AFG',
      headline: 'The Fall of Kabul',
      context: 'The U.S. withdrawal and the Taliban\'s rapid seizure of Kabul drives the highest single-month Afghanistan mention count on record, a twenty-year war closing in a matter of days.',
    },
    {
      month: '2022-02', iso3: 'UKR',
      headline: 'Russia Invades Ukraine',
      context: 'One of the most dramatic surges on record. Ukraine goes from absent to #1 in a single month as Congress responds to the full-scale invasion with sanctions, aid packages, and resolutions.',
    },
    {
      month: '2023-10', iso3: 'ISR',
      headline: 'Hamas Attacks Israel',
      context: 'The October 7 attacks and the ensuing Gaza war send both Israel and Palestine to the top of the congressional agenda simultaneously, an unusual co-surge of two entangled countries.',
    },
    {
      month: '2024-08', iso3: 'VEN',
      headline: 'Venezuela\'s Stolen Election',
      context: 'Maduro\'s disputed reelection and the regime\'s violent crackdown on protesters push Venezuela into the spotlight, producing one of the sharpest out-of-nowhere surges on record.',
    },
  ];

  // ── Political control by Congress number ────────────────────────────────────

  const POLITICAL = {
    93:  { prez: 'R', senate: 'D', house: 'D', name: 'Nixon / Ford' },
    94:  { prez: 'R', senate: 'D', house: 'D', name: 'Ford' },
    95:  { prez: 'D', senate: 'D', house: 'D', name: 'Carter' },
    96:  { prez: 'D', senate: 'D', house: 'D', name: 'Carter' },
    97:  { prez: 'R', senate: 'R', house: 'D', name: 'Reagan' },
    98:  { prez: 'R', senate: 'R', house: 'D', name: 'Reagan' },
    99:  { prez: 'R', senate: 'R', house: 'D', name: 'Reagan' },
    100: { prez: 'R', senate: 'D', house: 'D', name: 'Reagan' },
    101: { prez: 'R', senate: 'D', house: 'D', name: 'Bush' },
    102: { prez: 'R', senate: 'D', house: 'D', name: 'Bush' },
    103: { prez: 'D', senate: 'D', house: 'D', name: 'Clinton' },
    104: { prez: 'D', senate: 'R', house: 'R', name: 'Clinton' },
    105: { prez: 'D', senate: 'R', house: 'R', name: 'Clinton' },
    106: { prez: 'D', senate: 'R', house: 'R', name: 'Clinton' },
    107: { prez: 'R', senate: 'S', house: 'R', name: 'G.W. Bush' },
    108: { prez: 'R', senate: 'R', house: 'R', name: 'G.W. Bush' },
    109: { prez: 'R', senate: 'R', house: 'R', name: 'G.W. Bush' },
    110: { prez: 'R', senate: 'D', house: 'D', name: 'G.W. Bush' },
    111: { prez: 'D', senate: 'D', house: 'D', name: 'Obama' },
    112: { prez: 'D', senate: 'D', house: 'R', name: 'Obama' },
    113: { prez: 'D', senate: 'D', house: 'R', name: 'Obama' },
    114: { prez: 'D', senate: 'R', house: 'R', name: 'Obama' },
    115: { prez: 'R', senate: 'R', house: 'R', name: 'Trump' },
    116: { prez: 'R', senate: 'R', house: 'D', name: 'Trump' },
    117: { prez: 'D', senate: 'D', house: 'D', name: 'Biden' },
    118: { prez: 'D', senate: 'D', house: 'R', name: 'Biden' },
    119: { prez: 'R', senate: 'R', house: 'R', name: 'Trump' },
  };

  const ERA_EVENTS = {
    93:  'Yom Kippur War, Vietnam ceasefire',
    94:  'Fall of Saigon, Mayaguez incident',
    95:  'Camp David Accords, Panama Canal treaties',
    96:  'Iran hostage crisis, Soviet invasion of Afghanistan',
    97:  'Cold War escalation, martial law in Poland',
    98:  'Lebanon intervention, Grenada invasion',
    99:  'Iran-Contra affair, Libya bombing',
    100: 'Iran-Contra hearings, INF Treaty signed',
    101: 'Fall of Berlin Wall, Panama invasion',
    102: 'Gulf War, Soviet Union dissolves',
    103: 'Somalia, Bosnia, NAFTA',
    104: 'Dayton Accords, Bosnia peacekeeping',
    105: 'Kosovo crisis, Asian financial contagion',
    106: 'Kosovo War, China trade normalization',
    107: 'September 11, Afghanistan War begins',
    108: 'Iraq War, Abu Ghraib',
    109: 'Iraq insurgency, Iran nuclear standoff',
    110: 'Iraq surge, Afghanistan escalation',
    111: 'Iraq drawdown, Afghanistan surge',
    112: 'Arab Spring, Libya intervention',
    113: 'Syria chemical weapons, Russia annexes Crimea',
    114: 'Iran nuclear deal, Cuba trade normalization',
    115: 'Russia-Trump sanctions, U.S.-China trade war begins',
    116: 'COVID-19 emerges, China competition intensifies',
    117: 'Afghanistan withdrawal, Russia invades Ukraine',
    118: 'Israel-Hamas war, China competition bill',
    119: 'China tariffs, Ukraine aid debate',
  };

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function partyColor(p) {
    return p === 'R' ? '#c95c5c' : p === 'D' ? '#4e7cc9' : '#a0a0a0';
  }

  function partyLabel(p) {
    return p === 'R' ? 'R' : p === 'D' ? 'D' : 'Split';
  }

  function congressOrdinal(n) {
    if (n % 100 >= 11 && n % 100 <= 13) return n + 'th';
    switch (n % 10) {
      case 1: return n + 'st';
      case 2: return n + 'nd';
      case 3: return n + 'rd';
      default: return n + 'th';
    }
  }

  function flagSrc(iso2) {
    return DataLoader.flagPath(iso2);
  }

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

  function computeStreak(monthlyTop) {
    const sorted = [...monthlyTop].sort((a, b) => a.month.localeCompare(b.month));
    let maxStreak = 0, maxCountry = '';
    let curStreak = 0, curName = '';
    for (const d of sorted) {
      if (d.country_name === curName) {
        curStreak++;
      } else {
        curName = d.country_name;
        curStreak = 1;
      }
      if (curStreak > maxStreak) {
        maxStreak = curStreak;
        maxCountry = curName;
      }
    }
    return { country: maxCountry, months: maxStreak };
  }

  // ── Main init ───────────────────────────────────────────────────────────────

  try {
    // Load congressional + executive data in parallel
    const [congData, exData] = await Promise.all([
      DataLoader.loadAll(),
      DataLoader.loadExecutive().catch(() => null),
    ]);

    const { monthlyTop, monthlyAll, metadata } = congData;

    if (!monthlyTop || monthlyTop.length === 0) {
      document.querySelector('.grid-section').innerHTML =
        '<p style="text-align:center;padding:3rem;color:var(--text-muted);">No data yet. Run the pipeline to generate data.</p>';
      return;
    }

    // ── Masthead edition line ─────────────────────────────────────────────────

    const first = monthlyTop[0].month;
    const last = monthlyTop[monthlyTop.length - 1].month;
    const editionEl = document.querySelector('.masthead-edition');
    if (editionEl) {
      editionEl.textContent =
        `${DataLoader.formatMonthLong(first)} \u2013 ${DataLoader.formatMonthLong(last)} | ${monthlyTop.length} months of data`;
    }

    // ── Inline detail panel ───────────────────────────────────────────────────

    let currentInlineDetail = null;

    function closeInlineDetail() {
      if (currentInlineDetail) {
        currentInlineDetail.remove();
        currentInlineDetail = null;
      }
      if (FlagGrid.selectedCell) {
        FlagGrid.selectedCell.classList.remove('selected');
        FlagGrid.selectedCell = null;
      }
    }

    function showDetail(entry, rowEl) {
      if (currentInlineDetail) {
        currentInlineDetail.remove();
        currentInlineDetail = null;
      }
      if (!entry) return;

      const titles = entry.sample_titles || [];
      const runnerUp = entry.runner_up_name
        ? `${entry.runner_up_name} (${entry.runner_up_count})`
        : 'none';

      const titlesHtml = titles.length > 0
        ? titles.map(t => `<li>${t}</li>`).join('')
        : '<li class="inline-detail-empty">No sample titles available</li>';

      const panel = document.createElement('div');
      panel.className = 'inline-detail';
      panel.innerHTML = `
        <button class="inline-detail-close" aria-label="Close">&times;</button>
        <div class="inline-detail-top">
          <img class="detail-flag" src="${flagSrc(entry.country_iso2)}" alt="${entry.country_name}">
          <div>
            <strong class="detail-country">${entry.country_name}</strong>
            <span class="detail-month">${DataLoader.formatMonthLong(entry.month)}</span>
          </div>
          <div class="inline-detail-stats">
            <div class="stat"><span class="stat-number">${entry.mention_count}</span><span class="stat-label">mentions</span></div>
            <div class="stat"><span class="stat-number">${entry.total_records_scanned}</span><span class="stat-label">records scanned</span></div>
            <div class="stat"><span class="stat-number">${runnerUp}</span><span class="stat-label">runner-up</span></div>
          </div>
        </div>
        <ul class="inline-detail-titles">${titlesHtml}</ul>
      `;

      panel.querySelector('.inline-detail-close').addEventListener('click', closeInlineDetail);
      rowEl.insertAdjacentElement('afterend', panel);
      currentInlineDetail = panel;
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // ── Initialize flag grid ──────────────────────────────────────────────────

    const executiveData = exData;

    FlagGrid.init(monthlyTop, { onCellClick: showDetail });

    // ── Insights ──────────────────────────────────────────────────────────────

    const insights = StoryInsights.generate(monthlyTop);
    StoryInsights.render(insights);

    // ══════════════════════════════════════════════════════════════════════════
    // DATA STORY SECTIONS (always show congressional data)
    // ══════════════════════════════════════════════════════════════════════════

    const months = Object.keys(monthlyAll).sort();
    const countryMeta = buildCountryMeta(monthlyAll);
    const totals = computeTotals(monthlyAll);

    // ── Stat Cards ────────────────────────────────────────────────────────────

    document.getElementById('stat-months').textContent = months.length;
    document.getElementById('stat-mentions').textContent =
      (metadata.total_mentions_detected || 0).toLocaleString();
    document.getElementById('stat-countries').textContent =
      Object.keys(totals).length;

    const topTotal = Object.entries(totals).sort((a, b) => b[1] - a[1])[0];
    if (topTotal) {
      document.getElementById('stat-leader').textContent =
        countryMeta[topTotal[0]]?.name || topTotal[0];
    }

    const streak = computeStreak(monthlyTop);
    document.getElementById('stat-streak').textContent = streak.months;
    document.getElementById('stat-unique-leaders').textContent =
      new Set(monthlyTop.map(d => d.country_name)).size;

    // ── Bar Chart ─────────────────────────────────────────────────────────────

    (function renderBarChart() {
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
    })();

    // ── Era Grid ──────────────────────────────────────────────────────────────

    (function renderEraGrid() {
      const grid = document.getElementById('era-grid');

      for (const session of DataTransform.CONGRESS_SESSIONS) {
        const eraMonths = months.filter(m => m >= session.startMonth && m < session.endMonth);
        if (eraMonths.length === 0) continue;

        const eraTotals = {};
        for (const m of eraMonths) {
          for (const c of (monthlyAll[m]?.countries || [])) {
            eraTotals[c.iso3] = (eraTotals[c.iso3] || 0) + c.count;
          }
        }
        const topThree = Object.entries(eraTotals)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3);

        const startYear = session.startMonth.slice(0, 4);
        const endYear = String(parseInt(session.endMonth.slice(0, 4)) - 1);

        const flagsHtml = topThree.map(([iso3]) => {
          const meta = countryMeta[iso3] || {};
          return `<img class="era-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || iso3}" title="${meta.name || iso3}" />`;
        }).join('');

        const leaderMeta = countryMeta[topThree[0]?.[0]] || {};
        const politics = POLITICAL[session.number];
        const dotsHtml = politics ? `
          <div class="era-political" title="Pres: ${politics.name} (${politics.prez}) · Senate: ${partyLabel(politics.senate)} · House: ${partyLabel(politics.house)}">
            <span class="era-dot" style="background:${partyColor(politics.prez)}"></span>
            <span class="era-dot" style="background:${partyColor(politics.senate)}"></span>
            <span class="era-dot" style="background:${partyColor(politics.house)}"></span>
          </div>` : '';

        const card = document.createElement('div');
        card.className = 'era-card';
        card.innerHTML = `
          <div>
            <div class="era-congress">${congressOrdinal(session.number)}</div>
            <div class="era-years">${startYear}&ndash;${endYear}</div>
            ${dotsHtml}
          </div>
          <div class="era-flags">${flagsHtml}</div>
          ${leaderMeta.name ? `<div class="era-leader">${leaderMeta.name} led</div>` : ''}
          <div class="era-event">${ERA_EVENTS[session.number] || ''}</div>
        `;
        grid.appendChild(card);
      }
    })();

    // ── Crisis Timeline ───────────────────────────────────────────────────────

    (function renderCrisisTimeline() {
      const container = document.getElementById('crisis-timeline');

      for (const event of CRISIS_EVENTS) {
        const entry = monthlyAll[event.month];
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
    })();

    // ── Branch Comparison ─────────────────────────────────────────────────────

    (function renderBranchComparison() {
      const container = document.getElementById('branch-comparison');
      if (!container || !executiveData) {
        if (container) {
          container.innerHTML = '<p style="color:var(--text-muted);font-style:italic;">Executive order data not available.</p>';
        }
        return;
      }

      const exCountryMeta = buildCountryMeta(executiveData.monthlyAll);
      const exTotals = computeTotals(executiveData.monthlyAll);
      const allMeta = { ...countryMeta, ...exCountryMeta };

      const congTop10 = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 10);
      const exTop10 = Object.entries(exTotals).sort((a, b) => b[1] - a[1]).slice(0, 10);

      // Divergence
      const congByMonth = {};
      for (const d of monthlyTop) congByMonth[d.month] = d.country_iso3;
      const exByMonth = {};
      for (const d of executiveData.monthlyTop) exByMonth[d.month] = d.country_iso3;
      const shared = Object.keys(congByMonth).filter(m => exByMonth[m]);
      let agreements = 0;
      for (const m of shared) {
        if (congByMonth[m] === exByMonth[m]) agreements++;
      }
      const divergePct = shared.length ? Math.round((shared.length - agreements) / shared.length * 100) : 0;

      const congTop10Set = new Set(congTop10.map(([iso3]) => iso3));
      const exOnly = exTop10.filter(([iso3]) => !congTop10Set.has(iso3))
        .map(([iso3]) => allMeta[iso3]?.name || iso3);

      const congMax = congTop10[0]?.[1] || 1;
      const exMax = exTop10[0]?.[1] || 1;

      function buildRows(top10, maxCount, fillClass) {
        return top10.map(([iso3, count]) => {
          const meta = allMeta[iso3] || {};
          const pct = (count / maxCount * 100).toFixed(1);
          return `<div class="compare-row">
            <img class="compare-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || iso3}" />
            <span class="compare-name">${meta.name || iso3}</span>
            <div class="compare-track"><div class="compare-fill ${fillClass}" style="width:${pct}%"></div></div>
            <span class="compare-count">${count}</span>
          </div>`;
        }).join('');
      }

      container.innerHTML = `
        <div class="branch-compare-grid">
          <div class="branch-col">
            <div class="branch-col-header">
              <span class="branch-col-label">Congress</span>
              <span class="branch-col-sub">bills, nominations, amendments &mdash; all years</span>
            </div>
            ${buildRows(congTop10, congMax, 'compare-fill--congress')}
          </div>
          <div class="branch-col">
            <div class="branch-col-header">
              <span class="branch-col-label">Executive Orders</span>
              <span class="branch-col-sub">presidential orders &mdash; 1993 to present</span>
            </div>
            ${buildRows(exTop10, exMax, 'compare-fill--executive')}
          </div>
        </div>
        <p class="branch-compare-note">Each column is normalized to its own maximum. Congressional totals run into the thousands; executive totals into the dozens. Bars show relative rank within each branch, not absolute scale.</p>
        <div class="branch-diverge-stat">
          <strong>${divergePct}%</strong> of months where both datasets overlap, Congress and the White House focused on <em>different</em> countries at #1.${exOnly.length > 0 ? ` Countries that appear in the Executive top&nbsp;10 but not the Congressional top&nbsp;10: <strong>${exOnly.join(', ')}</strong>.` : ''}
        </div>
      `;
    })();

    // ── Patterns ──────────────────────────────────────────────────────────────

    (function renderPatterns() {
      const container = document.getElementById('patterns');
      const sorted = [...monthlyTop].sort((a, b) => a.month.localeCompare(b.month));

      // Most months at #1
      const monthsAtTop = {};
      for (const d of sorted) {
        monthsAtTop[d.country_name] = (monthsAtTop[d.country_name] || 0) + 1;
      }
      const topLeader = Object.entries(monthsAtTop).sort((a, b) => b[1] - a[1])[0];

      // Decade leaders
      const decadeLeaders = ['1970', '1980', '1990', '2000', '2010', '2020'].map(prefix => {
        const label = prefix + 's';
        const dec = sorted.filter(d => d.month.startsWith(prefix));
        if (dec.length === 0) return null;
        const counts = {};
        for (const d of dec) counts[d.country_name] = (counts[d.country_name] || 0) + 1;
        const leader = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
        return { label, country: leader[0] };
      }).filter(Boolean);

      // Top 5 concentration
      const total = metadata.total_mentions_detected || 1;
      const top5Sum = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 5)
        .reduce((s, [, v]) => s + v, 0);
      const top5Pct = Math.round(top5Sum / total * 100);
      const top5Names = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 5)
        .map(([iso3]) => countryMeta[iso3]?.name || iso3).join(', ');

      // Branch divergence
      let divergeCard = null;
      if (executiveData && executiveData.monthlyTop.length > 0) {
        const congByMonth = {};
        for (const d of sorted) congByMonth[d.month] = d.country_iso3;
        const exByMonth = {};
        for (const d of executiveData.monthlyTop) exByMonth[d.month] = d.country_iso3;
        const shared = Object.keys(congByMonth).filter(m => exByMonth[m]);
        let agreements = 0;
        for (const m of shared) {
          if (congByMonth[m] === exByMonth[m]) agreements++;
        }
        const divergePct = shared.length ? Math.round((shared.length - agreements) / shared.length * 100) : 0;
        divergeCard = {
          label: 'Branch Divergence',
          stat: `${divergePct}% diverge`,
          body: `Across ${shared.length} months where both datasets overlap, Congress and the White House named the same country #1 in only ${agreements} of them. The two branches choose different top priorities ${divergePct}% of the time.`,
        };
      }

      const patterns = [
        {
          label: 'Recurring Dominance',
          stat: `${topLeader[1]} months`,
          body: `${topLeader[0]} has held the #1 spot for ${topLeader[1]} of ${sorted.length} months in the full record \u2014 more than any other country.`,
        },
        {
          label: 'Era by Era',
          stat: decadeLeaders.length + ' decades',
          body: decadeLeaders.map(d => `<strong>${d.label}:</strong> ${d.country}`).join(' &nbsp;\u00b7&nbsp; '),
        },
        {
          label: 'Concentrated Attention',
          stat: `${top5Pct}%`,
          body: `Five countries \u2014 ${top5Names} \u2014 account for ${top5Pct}% of all ${total.toLocaleString()} mentions detected. The rest of the world splits the remaining ${100 - top5Pct}%.`,
        },
        ...(divergeCard ? [divergeCard] : []),
      ];

      for (const p of patterns) {
        const card = document.createElement('div');
        card.className = 'pattern-card';
        card.innerHTML = `
          <div class="pattern-label">${p.label}</div>
          <div class="pattern-stat">${p.stat}</div>
          <div class="pattern-body">${p.body}</div>
        `;
        container.appendChild(card);
      }
    })();

    // ── Heat Matrix ───────────────────────────────────────────────────────────

    (function renderHeatMatrixSection() {
      const top25 = Object.entries(totals)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 25)
        .map(([iso3]) => ({ iso3, ...countryMeta[iso3] }));

      HeatMatrix.render(
        monthlyAll,
        top25,
        months,
        document.getElementById('heat-matrix-container')
      );
    })();

    // ── Footer ────────────────────────────────────────────────────────────────

    if (metadata) {
      const updateEl = document.getElementById('last-update');
      if (updateEl) {
        const date = new Date(metadata.last_run);
        updateEl.textContent = `Last updated ${date.toLocaleDateString('en-US', {
          year: 'numeric', month: 'long', day: 'numeric',
        })}`;
      }
    }

  } catch (err) {
    console.error('Story init failed:', err);
    const grid = document.querySelector('.grid-section');
    if (grid) {
      grid.innerHTML = `
        <p style="text-align:center;padding:3rem;color:var(--text-muted);">
          Could not load data. ${err.message}
        </p>
      `;
    }
  }
})();
