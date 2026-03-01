/**
 * Detail panel — sticky bottom panel showing country info, rankings, and sample legislation.
 */

const DetailPanel = {
  monthlyAll: null,
  rankedData: null,

  init(monthlyAll, rankedData) {
    this.monthlyAll = monthlyAll;
    this.rankedData = rankedData;
  },

  /**
   * Update panel for a selected month + country.
   * @param {string|null} month - "YYYY-MM" or null to clear
   * @param {string|null} iso3 - selected country ISO3
   * @param {Object|null} seriesEntry - series object from rankedData
   */
  update(month, iso3, seriesEntry) {
    const emptyEl = document.getElementById('detail-empty');
    const contentEl = document.getElementById('detail-content');

    if (!month || !iso3) {
      emptyEl.classList.remove('hidden');
      contentEl.classList.add('hidden');
      return;
    }

    emptyEl.classList.add('hidden');
    contentEl.classList.remove('hidden');

    // Header — flag + country name + rank info
    this._updateHeader(month, iso3, seriesEntry);

    // Rankings — full list for this month
    this._updateRankings(month, iso3);

    // Sample legislation
    this._updateSamples(month, iso3);
  },

  _updateHeader(month, iso3, seriesEntry) {
    const flagEl = document.getElementById('detail-flag');
    const countryEl = document.getElementById('detail-country');
    const infoEl = document.getElementById('detail-info');

    if (!seriesEntry) return;

    const rankEntry = seriesEntry.ranks.find(r => r.month === month);
    const rank = rankEntry ? rankEntry.rank : null;
    const count = rankEntry ? rankEntry.count : 0;

    flagEl.src = DataLoader.flagPath(seriesEntry.iso2);
    flagEl.alt = seriesEntry.name;
    countryEl.textContent = seriesEntry.name;

    const parts = [];
    if (rank) parts.push(`Rank #${rank}`);
    if (count) parts.push(`${count} mentions`);
    parts.push(DataLoader.formatMonth(month));
    infoEl.textContent = parts.join(' · ');
  },

  _updateRankings(month, selectedIso3) {
    const listEl = document.getElementById('detail-list');
    listEl.innerHTML = '';

    const monthData = this.monthlyAll[month];
    if (!monthData) return;

    const countries = monthData.countries || [];
    const topN = Math.min(countries.length, 15);

    for (let i = 0; i < topN; i++) {
      const c = countries[i];
      const li = document.createElement('li');
      if (c.iso3 === selectedIso3) li.classList.add('active');

      li.innerHTML = `
        <span class="rank-num">${i + 1}</span>
        <img class="rank-flag" src="${DataLoader.flagPath(c.iso2)}" alt="${c.name}" />
        <span>${c.name}</span>
        <span class="rank-count">${c.count}</span>
      `;
      listEl.appendChild(li);
    }
  },

  _updateSamples(month, iso3) {
    const titlesEl = document.getElementById('detail-titles');
    titlesEl.innerHTML = '';

    const monthData = this.monthlyAll[month];
    if (!monthData) return;

    const country = (monthData.countries || []).find(c => c.iso3 === iso3);
    const titles = country ? (country.sample_titles || []) : [];

    if (titles.length === 0) {
      const li = document.createElement('li');
      li.textContent = 'No sample titles available';
      li.style.fontStyle = 'italic';
      titlesEl.appendChild(li);
      return;
    }

    titles.forEach(title => {
      const li = document.createElement('li');
      li.textContent = title;
      titlesEl.appendChild(li);
    });
  },
};
