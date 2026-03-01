/**
 * Flag Grid — calendar grid showing the #1 country per month.
 * Columns = months (Jan–Dec), rows = years (newest at top).
 * Supports filtering by source type via update().
 */

const FlagGrid = {

  MONTHS: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],

  // Political control by Congress number: prez / senate / house + president name for tooltip
  // R = Republican, D = Democrat, S = Split/tied
  POLITICAL: {
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
  },

  dataIndex: null,
  selectedCell: null,
  options: null,
  yearRange: null,

  init(monthlyTop, options) {
    this.options = options || {};
    this.selectedCell = null;

    // Index by "YYYY-MM" for O(1) lookup
    this.dataIndex = {};
    for (const entry of monthlyTop) {
      this.dataIndex[entry.month] = entry;
    }

    // Determine year range from the full dataset (never shrinks)
    const years = [...new Set(monthlyTop.map(d => d.month.split('-')[0]))];
    this.yearRange = this._computeYearRange(years);

    this._renderHeader();
    this._renderBody();
  },

  update(monthlyTop) {
    this.selectedCell = null;
    this.dataIndex = {};
    for (const entry of monthlyTop) {
      this.dataIndex[entry.month] = entry;
    }
    this._renderBody();
  },

  _computeYearRange(dataYears) {
    const nums = dataYears.map(Number);
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const years = [];
    for (let y = max; y >= min; y--) {
      years.push(String(y));
    }
    return years;
  },

  // Congress number for a given year (e.g. 2025 → 119)
  _congressNum(year) {
    return Math.floor((year - 1789) / 2) + 1;
  },

  _congressOrdinal(n) {
    if (n % 100 >= 11 && n % 100 <= 13) return n + 'th';
    switch (n % 10) {
      case 1: return n + 'st';
      case 2: return n + 'nd';
      case 3: return n + 'rd';
      default: return n + 'th';
    }
  },

  _partyColor(p) {
    return p === 'R' ? '#c95c5c' : p === 'D' ? '#4e7cc9' : '#a0a0a0';
  },

  _partyLabel(p) {
    return p === 'R' ? 'R' : p === 'D' ? 'D' : 'Split';
  },

  _renderHeader() {
    const header = document.getElementById('grid-header');
    header.innerHTML = '<div class="corner-cell"></div>';
    for (const m of this.MONTHS) {
      const div = document.createElement('div');
      div.className = 'month-label';
      div.textContent = m;
      header.appendChild(div);
    }
  },

  _renderBody() {
    const body = document.getElementById('grid-body');
    body.innerHTML = '';

    let prevCongress = null;

    for (const year of this.yearRange) {
      const yearNum = parseInt(year);
      const congress = this._congressNum(yearNum);
      const politics = this.POLITICAL[congress];

      const isNewCongress = prevCongress !== null && congress !== prevCongress;
      prevCongress = congress;

      const row = document.createElement('div');
      row.className = isNewCongress ? 'grid-row congress-start' : 'grid-row';

      // Year label with political dots
      const yearLabel = document.createElement('div');
      yearLabel.className = 'year-label';

      if (politics) {
        const dots = document.createElement('span');
        dots.className = 'year-dots';

        for (const [roleLabel, key] of [['Pres', 'prez'], ['Sen', 'senate'], ['House', 'house']]) {
          const dot = document.createElement('span');
          dot.className = 'year-dot';
          dot.style.background = this._partyColor(politics[key]);
          dots.appendChild(dot);
        }
        yearLabel.appendChild(dots);

        yearLabel.title = [
          this._congressOrdinal(congress) + ' Congress',
          'Pres: ' + politics.name + ' (' + politics.prez + ')',
          'Senate: ' + this._partyLabel(politics.senate),
          'House: ' + this._partyLabel(politics.house),
        ].join(' · ');
      }

      const yearText = document.createElement('span');
      yearText.textContent = year;
      yearLabel.appendChild(yearText);

      row.appendChild(yearLabel);

      for (let m = 1; m <= 12; m++) {
        const monthKey = `${year}-${String(m).padStart(2, '0')}`;
        const cell = document.createElement('div');
        const entry = this.dataIndex[monthKey];

        if (entry) {
          cell.className = 'grid-cell';
          cell.dataset.month = monthKey;
          const img = document.createElement('img');
          img.src = DataLoader.flagPath(entry.country_iso2);
          img.alt = entry.country_name;
          img.title = `${entry.country_name} — ${DataLoader.formatMonth(monthKey)}`;
          img.loading = 'lazy';
          cell.appendChild(img);
          cell.addEventListener('click', () => this._selectCell(cell, entry));
        } else {
          cell.className = 'grid-cell empty';
        }

        row.appendChild(cell);
      }

      body.appendChild(row);
    }
  },

  _selectCell(cell, entry) {
    if (this.selectedCell) {
      this.selectedCell.classList.remove('selected');
    }

    if (this.selectedCell === cell) {
      this.selectedCell = null;
      if (this.options.onCellClick) this.options.onCellClick(null);
      return;
    }

    cell.classList.add('selected');
    this.selectedCell = cell;
    if (this.options.onCellClick) this.options.onCellClick(entry, cell.closest('.grid-row'));
  },
};
