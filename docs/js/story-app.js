/**
 * Congressional World View — Unified data story orchestrator.
 * Narrative arc: Hook → Scale → Rankings → Turning Points → Eras → Twist → Explore → Takeaway
 */

(async function() {
  'use strict';

  // ── Crisis events ─────────────────────────────────────────────────────────
  // month = the peak legislative month (verified against data); peak is also
  // computed dynamically from data so sparklines show the real shape.

  const CRISIS_EVENTS = [
    {
      month: '1975-04', iso3: 'VNM',
      headline: 'The Fall of Saigon',
      context: 'Vietnam\'s 40 mentions in April 1975 is the largest single-month count in the dataset for over a decade \u2014 and it didn\'t come out of nowhere. Vietnam had dominated the congressional record for years: the War Powers Resolution, appropriations fights, the draft. The fall of Saigon accelerated a debate already in motion about refugees, accountability, and what the United States owed to those it had left behind.',
    },
    {
      month: '1977-01', iso3: 'PAN',
      headline: 'The Panama Canal Treaties',
      context: 'Returning the Canal to Panamanian sovereignty required 67 Senate votes \u2014 a supermajority \u2014 and consumed two years of floor debate. Panama\'s 20 mentions in January 1977 mark the opening of that fight. The Canal wasn\'t just infrastructure; it was a proxy for how the United States understood its role in the Western Hemisphere. This is what purely legislative foreign policy looks like in the record: no troops deployed, no crisis declared, just a Senate that wouldn\'t stop talking.',
    },
    {
      month: '1979-01', iso3: 'TWN',
      headline: 'The Taiwan Relations Act',
      context: 'When President Carter announced diplomatic recognition of China on December 15, 1978, Congress had 30 days to respond. It did, overwhelmingly. The Taiwan Relations Act \u2014 passed in April 1979 \u2014 established a security framework that was neither a treaty nor an abandonment. Taiwan\'s 12 mentions in January 1979 are the opening of a legislative argument that has never fully closed. Taiwan is the #4 all-time country in this dataset, present in the congressional record across every era since.',
    },
    {
      month: '1979-11', iso3: 'IRN',
      headline: 'The Iran Hostage Crisis',
      context: 'When Iranian students storm the U.S. Embassy and take 52 Americans hostage, Iran becomes the dominant subject of the congressional record overnight. The crisis stretched 444 days, reshaping American foreign policy and dominating the legislative agenda through the Carter and early Reagan years. Iran is the #3 all-time country in this dataset \u2014 a presence built across multiple eras, not just this one.',
    },
    {
      month: '1985-02', iso3: 'ZAF',
      headline: 'The Anti-Apartheid Movement',
      context: 'South Africa led the congressional agenda for 14 months in the mid-1980s \u2014 not because of military action, but because of a sustained domestic movement demanding legislative response. Divestment bills, sanctions legislation, and ultimately the Comprehensive Anti-Apartheid Act of 1986, which Congress passed over President Reagan\'s veto. This is one of the most significant exercises of independent congressional foreign policy authority in the 20th century, and it barely shows up in conventional histories of the era.',
    },
    {
      month: '1991-01', iso3: 'IRQ',
      headline: 'Desert Storm: Congress Votes for War',
      context: 'Congress authorized the use of force against Iraq on January 12, 1991, in one of the closest war votes in modern history: 52\u201347 in the Senate. Iraq\'s 24 mentions that month reflect the authorization debate, not the invasion \u2014 which came five months after Saddam Hussein seized Kuwait. The legislative machinery ran well behind the news. By January, the question was no longer whether Iraq had invaded but whether Congress would send Americans to fight.',
    },
    {
      month: '2001-12', iso3: 'AFG',
      headline: 'September 11 and the Authorization Trap',
      context: 'September 11 happened on the 11th, but most September legislation was already in the record. Congress passed the Authorization for Use of Military Force within a week \u2014 in language so broad it is still being invoked. The actual peaks in Afghanistan mentions came in December 2001 and beyond, as hearings, nominations, and supplemental appropriations filled the record with the machinery of a long war. The legislative record is a delayed mirror of the news.',
    },
    {
      month: '2003-04', iso3: 'IRQ',
      headline: 'The Iraq War',
      context: 'The invasion began March 20, 2003, but the congressional peak came one month later as committee hearings, reconstruction legislation, and early oversight hearings flooded the record. Iraq went on to accumulate 454 total mentions in the War on Terror era \u2014 the highest concentration of any country in any single era in this dataset. No other country in any other era comes close.',
    },
    {
      month: '2015-09', iso3: 'IRN',
      headline: 'The Iran Nuclear Deal',
      context: 'The JCPOA was signed in July 2015, but the congressional peak came in September as the Iran Nuclear Agreement Review Act process played out. Iran dominated the 114th Congress not through military crisis but through sustained legislative debate: resolutions of disapproval, letters to the Supreme Leader, sanctions legislation, floor speeches. Every month of that fight is recorded here. The legislative record doesn\'t distinguish between a law that passes and one that fails.',
    },
    {
      month: '2021-09', iso3: 'AFG',
      headline: 'The Fall of Kabul',
      context: 'The U.S. withdrawal and the Taliban\'s rapid seizure of Kabul drives the highest single-month Afghanistan mention count on record. September\'s 15 mentions came from emergency hearings, resolutions of condemnation, and refugee legislation \u2014 a twenty-year war closing in a matter of days, the formal reckoning arriving one month after the chaos.',
    },
    {
      month: '2022-03', iso3: 'UKR',
      headline: 'Russia Invades Ukraine',
      context: 'Ukraine was only #3 in February \u2014 behind China and Russia \u2014 as the invasion launched on the 24th. By March the legislative response had arrived in full: Lend-Lease legislation, sanctions packages, emergency aid bills. 28 mentions in a single month, the highest count in the dataset for over a decade. The gap between February and March is the measure of how long it takes Congress to convert a news event into a bill.',
    },
    {
      month: '2023-10', iso3: 'ISR',
      headline: 'Hamas Attacks Israel',
      context: 'The October 7 attacks and the ensuing Gaza war send Israel to the top of the congressional agenda. One of the rare crises where congressional and real-world timing align almost perfectly \u2014 the bills and resolutions came fast enough to appear in the same month as the events that triggered them.',
    },
  ];

  // ── Narrative eras (grouped congresses) ───────────────────────────────────

  const NARRATIVE_ERAS = [
    {
      name: 'Cold War Twilight',
      range: '1973 \u2013 1980',
      congresses: [93, 94, 95, 96],
      startMonth: '1973-01', endMonth: '1981-01',
      narrative: 'Vietnam is the era\u2019s story \u2014 330 mentions, the largest total of any country in this period by a wide margin. Not as Cold War backdrop but as active legislative preoccupation: War Powers Resolution, appropriations fights, the fall of Saigon, the long POW/MIA accounting. Russia shapes the strategic frame. Panama\u2019s 196 mentions are almost entirely the Canal treaty fight, one of the most intensive Senate ratification battles in modern history. The era ends when Iran displaces everything else overnight.',
    },
    {
      name: 'Reagan\u2019s Cold War',
      range: '1981 \u2013 1988',
      congresses: [97, 98, 99, 100],
      startMonth: '1981-01', endMonth: '1989-01',
      narrative: 'Russia leads with 270 mentions, but the era\u2019s most revealing entries are Japan (125) and South Africa (122). Congressional attention to Japan reflects trade deficits, semiconductor disputes, and fears of economic competition \u2014 a story that barely fits the Cold War frame. South Africa\u2019s 122 mentions are the fingerprint of the anti-apartheid movement: divestment bills, sanctions debates, and the Comprehensive Anti-Apartheid Act of 1986, passed over Reagan\u2019s veto. Nicaragua\u2019s 118 mentions are the Contra funding fight, Iran-Contra, and the Boland Amendment \u2014 the covert conflict that kept Congress occupied when the overt ones were constrained.',
    },
    {
      name: 'New World Order',
      range: '1989 \u2013 1994',
      congresses: [101, 102, 103],
      startMonth: '1989-01', endMonth: '1995-01',
      narrative: 'Taiwan leads this era with 110 mentions \u2014 barely ahead of Iraq\u2019s 107, which is itself a surprise. Congressional attention to Taiwan in this period is arms sales debates, questions about what \u201cone China\u201d means in practice, and early anxiety about Beijing\u2019s trajectory. Iraq surges with the Gulf War but is bounded: it peaks sharply around Desert Storm and fades. Russia\u2019s 104 mentions are the legislative processing of a superpower\u2019s collapse \u2014 START treaties, aid packages, the question of loose nuclear weapons. Vietnam\u2019s 98 mentions are now about trade normalization, not war.',
    },
    {
      name: 'Pax Americana',
      range: '1995 \u2013 2000',
      congresses: [104, 105, 106],
      startMonth: '1995-01', endMonth: '2001-01',
      narrative: 'Taiwan leads by a significant margin with 157 mentions \u2014 arms sales legislation, Taiwan Relations Act reaffirmations, and the 1995\u201396 Strait crisis. Mexico\u2019s 73 mentions reflect NAFTA\u2019s aftermath, immigration debates, and the 1995 peso crisis bailout. The narrative of this era as \u201crelative calm\u201d is partly right, but the legislative record shows Congress actively managing the China-Taiwan relationship and hemispheric economics. The quiet isn\u2019t absence of attention \u2014 it\u2019s attention to problems that don\u2019t fit neatly into a crisis frame.',
    },
    {
      name: 'The War on Terror',
      range: '2001 \u2013 2008',
      congresses: [107, 108, 109, 110],
      startMonth: '2001-01', endMonth: '2009-01',
      narrative: 'Iraq\u2019s 454 mentions make this the most concentrated single-country era in the dataset \u2014 no country in any other era comes close. But the era\u2019s hidden story is that Iran and Taiwan each also register 148 mentions: while Congress was consumed by Iraq, the Iran nuclear sanctions regime was being built and Taiwan security legislation was being written in parallel. Vietnam\u2019s persistent 100 mentions are entirely trade and normalization \u2014 the country that once dominated the record is now a trading partner, its presence measured in commerce rather than conflict.',
    },
    {
      name: 'Pivots and Resets',
      range: '2009 \u2013 2016',
      congresses: [111, 112, 113, 114],
      startMonth: '2009-01', endMonth: '2017-01',
      narrative: 'Iran leads with 257 mentions \u2014 a decade-long sanctions architecture culminating in the JCPOA debate. But the era\u2019s most revealing numbers are Cuba (92) and Vietnam (105). Cuba\u2019s legislative presence reflects 50 years of embargo followed by Obama\u2019s normalization: sanctions bills, travel restrictions, and the political fight over whether to end a Cold War-era policy. Vietnam appears as trade legislation, human rights bills, and defense cooperation agreements. The War on Terror\u2019s single-country focus is replaced by something more plural \u2014 and more honest about the range of American foreign policy interests.',
    },
    {
      name: 'Fracture',
      range: '2017 \u2013 Present',
      congresses: [115, 116, 117, 118, 119],
      startMonth: '2017-01', endMonth: '2027-01',
      narrative: 'China\u2019s 494 mentions make it the defining legislative story of this era by a wide margin \u2014 more than Russia (357), more than Taiwan (317), more than Ukraine (262). Trade war legislation, the CHIPS Act, Taiwan security bills, Uyghur human rights legislation, TikTok hearings, supply chain bills: China is the organizing framework for nearly everything in modern congressional foreign policy. Ukraine\u2019s 262 mentions are compressed into a short window, making the invasion response one of the most intense legislative moments in the dataset. But China was already there, and China is still there.',
    },
  ];

  // ── Political control by Congress number ──────────────────────────────────

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

  // ── Helpers ───────────────────────────────────────────────────────────────

  function partyColor(p) {
    return p === 'R' ? '#c95c5c' : p === 'D' ? '#4e7cc9' : '#a0a0a0';
  }

  function partyLabel(p) {
    return p === 'R' ? 'R' : p === 'D' ? 'D' : 'Split';
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

  /** Advance/retreat a YYYY-MM string by n months */
  function offsetMonth(ym, n) {
    const [y, m] = ym.split('-').map(Number);
    const total = y * 12 + (m - 1) + n;
    const ny = Math.floor(total / 12);
    const nm = (total % 12) + 1;
    return `${ny}-${String(nm).padStart(2, '0')}`;
  }

  /** Get mention count for a country in a given month */
  function getCount(monthlyAll, month, iso3) {
    const entry = monthlyAll[month];
    if (!entry) return 0;
    const found = (entry.countries || []).find(c => c.iso3 === iso3);
    return found ? found.count : 0;
  }

  /** Find peak month for a country in a window around a center month */
  function findPeak(monthlyAll, centerMonth, iso3, windowSize) {
    let peakMonth = centerMonth;
    let peakCount = 0;
    for (let i = -windowSize; i <= windowSize; i++) {
      const m = offsetMonth(centerMonth, i);
      const count = getCount(monthlyAll, m, iso3);
      if (count > peakCount) {
        peakCount = count;
        peakMonth = m;
      }
    }
    return { month: peakMonth, count: peakCount };
  }

  /** Build sparkline SVG for a country around a center month.
   *  All labels live inside the SVG — no external label div needed. */
  function buildSparkline(monthlyAll, centerMonth, iso3, windowSize) {
    const W = 340, H = 80;
    const padT = 22, padB = 20, padL = 30, padR = 10;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;

    const points = [];
    for (let i = -windowSize; i <= windowSize; i++) {
      const m = offsetMonth(centerMonth, i);
      points.push({ month: m, count: getCount(monthlyAll, m, iso3), offset: i });
    }
    const maxC = Math.max(...points.map(p => p.count), 1);
    const peak = findPeak(monthlyAll, centerMonth, iso3, windowSize);
    const stepX = innerW / (points.length - 1);

    const coords = points.map((p, i) => ({
      x: padL + i * stepX,
      y: padT + innerH - (p.count / maxC) * innerH,
      ...p,
    }));

    // Area path
    let areaD = `M ${coords[0].x},${padT + innerH}`;
    for (const c of coords) areaD += ` L ${c.x},${c.y}`;
    areaD += ` L ${coords[coords.length - 1].x},${padT + innerH} Z`;

    // Line path
    let pathD = `M ${coords[0].x},${coords[0].y}`;
    for (let i = 1; i < coords.length; i++) pathD += ` L ${coords[i].x},${coords[i].y}`;

    const eventCoord = coords.find(c => c.offset === 0);
    const peakCoord  = coords.find(c => c.month === peak.month);
    let svg = `<svg class="crisis-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">`;

    // Y-axis tick + label at max
    svg += `<line x1="${padL - 4}" x2="${padL}" y1="${padT}" y2="${padT}" stroke="var(--rule-light)" stroke-width="0.75"/>`;
    svg += `<text x="${padL - 6}" y="${padT + 3}" text-anchor="end" font-size="8" fill="var(--text-muted)" font-family="IBM Plex Sans, sans-serif">${maxC}</text>`;
    // Zero tick
    svg += `<line x1="${padL - 4}" x2="${padL}" y1="${padT + innerH}" y2="${padT + innerH}" stroke="var(--rule-light)" stroke-width="0.75"/>`;
    svg += `<text x="${padL - 6}" y="${padT + innerH + 3}" text-anchor="end" font-size="8" fill="var(--text-muted)" font-family="IBM Plex Sans, sans-serif">0</text>`;
    // Y axis line
    svg += `<line x1="${padL}" x2="${padL}" y1="${padT}" y2="${padT + innerH}" stroke="var(--rule-light)" stroke-width="0.75"/>`;
    // Baseline
    svg += `<line x1="${padL}" x2="${W - padR}" y1="${padT + innerH}" y2="${padT + innerH}" stroke="var(--rule-light)" stroke-width="0.75"/>`;

    // Area fill + line
    svg += `<path d="${areaD}" fill="var(--accent)" opacity="0.09"/>`;
    svg += `<path d="${pathD}" fill="none" stroke="var(--accent)" stroke-width="1.75" opacity="0.65" stroke-linejoin="round" stroke-linecap="round"/>`;

    // Event month: dashed vertical + month label below axis
    if (eventCoord) {
      svg += `<line x1="${eventCoord.x}" x2="${eventCoord.x}" y1="${padT}" y2="${padT + innerH}" stroke="var(--text-muted)" stroke-width="0.75" stroke-dasharray="3,2" opacity="0.55"/>`;
      const evLabel = DataLoader.formatMonth(centerMonth);
      svg += `<text x="${eventCoord.x}" y="${H - 3}" text-anchor="middle" font-size="8" fill="var(--text-muted)" font-family="IBM Plex Sans, sans-serif">${evLabel}</text>`;
    }

    // Peak: horizontal dashed guide + dot + count label above + month label if different
    if (peakCoord && peak.count > 0) {
      svg += `<line x1="${padL}" x2="${W - padR}" y1="${peakCoord.y}" y2="${peakCoord.y}" stroke="var(--accent)" stroke-width="0.6" stroke-dasharray="3,2" opacity="0.3"/>`;
      svg += `<circle cx="${peakCoord.x}" cy="${peakCoord.y}" r="3.5" fill="var(--accent)"/>`;

      // Count label: nudge so it doesn't clip edges
      const countX = Math.min(Math.max(peakCoord.x, padL + 10), W - padR - 10);
      const countY = peakCoord.y > padT + 12 ? peakCoord.y - 7 : peakCoord.y + 14;
      svg += `<text x="${countX}" y="${countY}" text-anchor="middle" font-size="9" font-weight="600" fill="var(--accent)" font-family="IBM Plex Sans, sans-serif">${peak.count} mentions</text>`;

      // Peak month label below axis only if it differs from event month
      if (peak.month !== centerMonth) {
        const pkLabel = DataLoader.formatMonth(peak.month);
        // avoid overlap: offset slightly if x coords are close
        const labelX = Math.min(Math.max(peakCoord.x, padL + 14), W - padR - 14);
        svg += `<text x="${labelX}" y="${H - 3}" text-anchor="middle" font-size="8" font-weight="600" fill="var(--accent)" font-family="IBM Plex Sans, sans-serif">${pkLabel}</text>`;
      }
    }

    svg += `</svg>`;
    return svg;
  }

  // ── Main init ─────────────────────────────────────────────────────────────

  try {
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

    const executiveData = exData;
    const months = Object.keys(monthlyAll).sort();
    const countryMeta = buildCountryMeta(monthlyAll);
    const totals = computeTotals(monthlyAll);

    // ── Masthead ──────────────────────────────────────────────────────────

    const first = monthlyTop[0].month;
    const last = monthlyTop[monthlyTop.length - 1].month;
    const editionEl = document.querySelector('.masthead-edition');
    if (editionEl) {
      editionEl.textContent =
        `${DataLoader.formatMonthLong(first)} \u2013 ${DataLoader.formatMonthLong(last)} | ${monthlyTop.length} months of data`;
    }

    // ── Inline detail panel ───────────────────────────────────────────────

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

    // ── Flag grid + insights ──────────────────────────────────────────────

    FlagGrid.init(monthlyTop, { onCellClick: showDetail });

    const insights = StoryInsights.generate(monthlyTop);
    StoryInsights.render(insights);

    // ══════════════════════════════════════════════════════════════════════
    // THE DATA STORY
    // ══════════════════════════════════════════════════════════════════════

    // ── Big Numbers (The Scale) ───────────────────────────────────────────

    (function renderBigNumbers() {
      const container = document.getElementById('big-numbers');
      const totalMentions = metadata.total_mentions_detected || 0;
      const uniqueCountries = Object.keys(totals).length;
      const topEntry = Object.entries(totals).sort((a, b) => b[1] - a[1])[0];
      const topMeta = countryMeta[topEntry[0]] || {};
      const streak = computeStreak(monthlyTop);

      container.innerHTML = `
        <div class="big-number-grid">
          <div class="big-number-card">
            <span class="big-num">${months.length}</span>
            <span class="big-label">months tracked</span>
          </div>
          <div class="big-number-card">
            <span class="big-num">${totalMentions.toLocaleString()}</span>
            <span class="big-label">country mentions detected</span>
          </div>
          <div class="big-number-card">
            <span class="big-num">${uniqueCountries}</span>
            <span class="big-label">countries in the record</span>
          </div>
        </div>
        <p class="big-number-reveal">
          One country &mdash;
          <img class="inline-flag" src="${flagSrc(topMeta.iso2)}" alt="${topMeta.name}" />
          <strong>${topMeta.name}</strong>
          &mdash; leads the all-time count. It has held the #1 spot
          for <strong>${streak.months} consecutive months</strong> at its peak.
        </p>
      `;
    })();

    // ── Bar Chart (Who Dominates) ─────────────────────────────────────────

    (function renderBarChart() {
      const sorted = Object.entries(totals)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);
      const max = sorted[0][1];
      const topMeta = countryMeta[sorted[0][0]] || {};

      // Narrative intro
      const introEl = document.getElementById('bar-intro');
      if (introEl) {
        const top5Sum = sorted.slice(0, 5).reduce((s, [, v]) => s + v, 0);
        const total = metadata.total_mentions_detected || 1;
        const top5Pct = Math.round(top5Sum / total * 100);
        const top5Names = sorted.slice(0, 5).map(([iso3]) => countryMeta[iso3]?.name || iso3);
        introEl.innerHTML = `Across all bills, nominations, amendments, and congressional records, <strong>${topMeta.name}</strong> leads with ${max.toLocaleString()} mentions. Five countries &mdash; ${top5Names.join(', ')} &mdash; account for <strong>${top5Pct}%</strong> of all mentions. The rest of the world splits the remainder.`;
      }

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
          <span class="bar-count">${count.toLocaleString()}</span>
        `;
        container.appendChild(row);
      }
    })();

    // ── Crisis Timeline (Turning Points) ──────────────────────────────────

    (function renderCrisisTimeline() {
      const container = document.getElementById('crisis-timeline');

      for (const event of CRISIS_EVENTS) {
        const meta = countryMeta[event.iso3] || {};
        const peak = findPeak(monthlyAll, event.month, event.iso3, 6);

        // Get rank at peak
        const peakEntry = monthlyAll[peak.month];
        let rank = null;
        if (peakEntry) {
          const idx = (peakEntry.countries || []).findIndex(c => c.iso3 === event.iso3);
          if (idx !== -1) rank = idx + 1;
        }

        const titles = peakEntry
          ? ((peakEntry.countries || []).find(c => c.iso3 === event.iso3)?.sample_titles || [])
          : [];
        const titlesHtml = titles.slice(0, 2).map(t =>
          `<li>${t.length > 100 ? t.slice(0, 99) + '\u2026' : t}</li>`
        ).join('');

        const sparkline = buildSparkline(monthlyAll, event.month, event.iso3, 6);

        const card = document.createElement('article');
        card.className = 'crisis-card';
        card.innerHTML = `
          <div class="crisis-dateline">${DataLoader.formatMonthLong(event.month)}</div>
          <div class="crisis-header">
            <img class="crisis-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || event.iso3}" />
            <h3 class="crisis-headline">${event.headline}</h3>
          </div>
          <p class="crisis-context">${event.context}</p>
          <div class="crisis-viz">
            <div class="crisis-spark-wrap">
              ${sparkline}
            </div>
            ${rank ? `<div class="crisis-rank-badge">#${rank} that month</div>` : ''}
          </div>
          ${titles.length > 0 ? `<ul class="crisis-samples">${titlesHtml}</ul>` : ''}
        `;
        container.appendChild(card);
      }
    })();

    // ── Era Narrative ─────────────────────────────────────────────────────

    (function renderEraNarrative() {
      const container = document.getElementById('era-narrative');

      for (const era of NARRATIVE_ERAS) {
        const eraMonths = months.filter(m => m >= era.startMonth && m < era.endMonth);
        if (eraMonths.length === 0) continue;

        const eraTotals = {};
        for (const m of eraMonths) {
          for (const c of (monthlyAll[m]?.countries || [])) {
            eraTotals[c.iso3] = (eraTotals[c.iso3] || 0) + c.count;
          }
        }
        const topFive = Object.entries(eraTotals)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5);

        if (topFive.length === 0) continue;

        const eraMax = topFive[0][1];

        // Political summary for this era's congresses
        const prezNames = [...new Set(era.congresses.map(n => POLITICAL[n]?.name).filter(Boolean))];

        const countriesHtml = topFive.map(([iso3, count]) => {
          const meta = countryMeta[iso3] || {};
          const pct = (count / eraMax * 100).toFixed(0);
          return `
            <div class="era-country-row">
              <img class="era-flag" src="${flagSrc(meta.iso2)}" alt="${meta.name || iso3}" />
              <span class="era-country-name">${meta.name || iso3}</span>
              <div class="era-bar-track"><div class="era-bar-fill" style="width:${pct}%"></div></div>
              <span class="era-country-count">${count}</span>
            </div>
          `;
        }).join('');

        // Political dots for all congresses in this era
        const dotsHtml = era.congresses.map(n => {
          const p = POLITICAL[n];
          if (!p) return '';
          return `<span class="era-mini-dots" title="${n}th: ${p.name} (P:${p.prez} S:${partyLabel(p.senate)} H:${partyLabel(p.house)})">
            <span class="era-dot" style="background:${partyColor(p.prez)}"></span>
            <span class="era-dot" style="background:${partyColor(p.senate)}"></span>
            <span class="era-dot" style="background:${partyColor(p.house)}"></span>
          </span>`;
        }).join('');

        const block = document.createElement('div');
        block.className = 'era-block';
        block.innerHTML = `
          <div class="era-block-header">
            <div>
              <h3 class="era-block-name">${era.name}</h3>
              <span class="era-block-range">${era.range}</span>
            </div>
            <div class="era-block-politics">
              ${dotsHtml}
              <span class="era-prez-names">${prezNames.join(' \u2192 ')}</span>
            </div>
          </div>
          <p class="era-block-narrative">${era.narrative}</p>
          <div class="era-block-countries">${countriesHtml}</div>
        `;
        container.appendChild(block);
      }
    })();

    // ── Branch Comparison ─────────────────────────────────────────────────

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
        <div class="branch-diverge-callout">
          <span class="branch-diverge-num">${divergePct}%</span>
          <span class="branch-diverge-text">of overlapping months, the two branches focused on <em>different</em> #1 countries</span>
        </div>
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
        <p class="branch-compare-note">Each column normalized to its own maximum. Congressional totals run into the thousands; executive totals into the dozens.${exOnly.length > 0 ? ` Executive-only top\u00a010: <strong>${exOnly.join(', ')}</strong>.` : ''}</p>
      `;
    })();

    // ── Heat Matrix ───────────────────────────────────────────────────────

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

    // ── Closing ───────────────────────────────────────────────────────────

    (function renderClosing() {
      const container = document.getElementById('closing');
      const uniqueLeaders = new Set(monthlyTop.map(d => d.country_name)).size;
      const totalCountries = Object.keys(totals).length;

      container.innerHTML = `
        <div class="closing-rule"></div>
        <p class="closing-text">
          Across ${months.length} months of data, <strong>${uniqueLeaders}</strong> countries
          have held the #1 spot &mdash; out of <strong>${totalCountries}</strong> that appear
          in the record. Congressional attention is concentrated, reactive, and
          often late. But it is never random. The legislative record is a map of
          where America believed the world mattered most.
        </p>
        <p class="closing-text closing-sub">
          This dataset updates weekly. The story is still being written.
        </p>
      `;
    })();

    // ── Footer ────────────────────────────────────────────────────────────

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
