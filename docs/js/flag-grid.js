/**
 * Flag Grid — calendar grid showing the #1 country per month.
 * Columns = months (Jan–Dec), rows = years (oldest at top).
 * Supports filtering by source type via update().
 */

const FlagGrid = {

  MONTHS: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],

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

  /**
   * Re-render the grid with new data (e.g. filtered by source).
   * Keeps the same year range so the grid doesn't jump around.
   */
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
    for (let y = min; y <= max; y++) {
      years.push(String(y));
    }
    return years;
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

    for (const year of this.yearRange) {
      const row = document.createElement('div');
      row.className = 'grid-row';

      const yearLabel = document.createElement('div');
      yearLabel.className = 'year-label';
      yearLabel.textContent = year;
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
    if (this.options.onCellClick) this.options.onCellClick(entry);
  },
};
