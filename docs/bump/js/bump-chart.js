/**
 * Bump chart — D3 rank-race visualization of country mentions over time.
 */

const BumpChart = {

  config: {
    monthWidth: 55,
    marginTop: 70,
    marginBottom: 50,
    marginLeft: 40,
    marginRight: 30,
    rankHeight: 45,
    flagWidth: 18,
    flagHeight: 13,
    nodeRadius: 4,
  },

  // State
  svg: null,
  data: null,
  topN: 10,
  xScale: null,
  yScale: null,
  locked: null,      // { month, iso3 } or null
  onSelect: null,     // callback(month, iso3, seriesEntry)

  init(containerEl, rankedData, options) {
    this.container = containerEl;
    this.data = rankedData;
    this.topN = options.topN || 10;
    this.onSelect = options.onSelect || function() {};

    this.render();
  },

  render() {
    const { months, series, congressSessions, annotations } = this.data;
    const cfg = this.config;

    const width = cfg.marginLeft + (months.length * cfg.monthWidth) + cfg.marginRight;
    const height = cfg.marginTop + (this.topN * cfg.rankHeight) + cfg.marginBottom;

    // Clear previous
    this.container.innerHTML = '';

    this.svg = d3.select(this.container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`);

    // Scales
    this.xScale = d3.scalePoint()
      .domain(months)
      .range([cfg.marginLeft, width - cfg.marginRight]);

    this.yScale = d3.scaleLinear()
      .domain([1, this.topN])
      .range([cfg.marginTop, height - cfg.marginBottom]);

    // Render layers
    this._renderCongressBands(congressSessions, width, height);
    this._renderAxes(months, height);
    this._renderLines(series);
    this._renderFlags(series);
    this._renderAnnotations(annotations, series);
    this._renderHoverColumns(months, height);
  },

  _renderCongressBands(sessions, width, height) {
    const g = this.svg.append('g').attr('class', 'congress-bands');

    sessions.forEach((session, i) => {
      const x1 = this.xScale(session.startMonth);
      const x2 = this.xScale(session.endMonth);
      if (x1 == null && x2 == null) return;

      const xStart = x1 != null ? x1 : this.config.marginLeft;
      const xEnd = x2 != null ? x2 : this.xScale.range()[1];

      // Alternating background
      g.append('rect')
        .attr('x', xStart - this.config.monthWidth / 2)
        .attr('y', 0)
        .attr('width', xEnd - xStart)
        .attr('height', height)
        .attr('fill', i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)')
        .attr('class', 'congress-bg');

      // Divider line at start
      if (x1 != null) {
        g.append('line')
          .attr('x1', xStart - this.config.monthWidth / 2)
          .attr('x2', xStart - this.config.monthWidth / 2)
          .attr('y1', 0)
          .attr('y2', height)
          .attr('class', 'congress-divider');
      }

      // Label
      const labelX = (xStart + xEnd) / 2;
      g.append('text')
        .attr('x', labelX)
        .attr('y', 16)
        .attr('text-anchor', 'middle')
        .attr('class', 'congress-label')
        .text(this._ordinal(session.number) + ' Congress');
    });
  },

  _renderAxes(months, height) {
    const g = this.svg.append('g').attr('class', 'axes');

    // X axis — year labels at January, small month ticks
    months.forEach(month => {
      const x = this.xScale(month);
      const [y, m] = month.split('-');
      const isJan = m === '01';

      // Year label
      if (isJan) {
        g.append('text')
          .attr('x', x)
          .attr('y', height - 8)
          .attr('text-anchor', 'middle')
          .attr('class', 'axis-year')
          .text(y);
      }

      // Month tick
      g.append('line')
        .attr('x1', x)
        .attr('x2', x)
        .attr('y1', height - this.config.marginBottom + 5)
        .attr('y2', height - this.config.marginBottom + (isJan ? 14 : 8))
        .attr('class', 'axis-tick');
    });

    // Y axis — rank labels
    for (let rank = 1; rank <= this.topN; rank++) {
      const y = this.yScale(rank);
      g.append('text')
        .attr('x', this.config.marginLeft - 12)
        .attr('y', y + 4)
        .attr('text-anchor', 'end')
        .attr('class', 'axis-rank')
        .text(rank);

      // Subtle horizontal gridline
      g.append('line')
        .attr('x1', this.config.marginLeft)
        .attr('x2', this.xScale.range()[1])
        .attr('y1', y)
        .attr('y2', y)
        .attr('class', 'gridline');
    }
  },

  _renderLines(series) {
    const g = this.svg.append('g').attr('class', 'lines');
    const xScale = this.xScale;
    const yScale = this.yScale;

    const line = d3.line()
      .defined(d => d.rank !== null && d.inTopN)
      .x(d => xScale(d.month))
      .y(d => yScale(d.rank))
      .curve(d3.curveBumpX);

    series.forEach(s => {
      g.append('path')
        .datum(s.ranks)
        .attr('d', line)
        .attr('fill', 'none')
        .attr('stroke', s.color)
        .attr('stroke-width', 2.5)
        .attr('class', 'bump-line')
        .attr('data-iso3', s.iso3);
    });
  },

  _renderFlags(series) {
    const g = this.svg.append('g').attr('class', 'flags');
    const xScale = this.xScale;
    const yScale = this.yScale;
    const fw = this.config.flagWidth;
    const fh = this.config.flagHeight;

    series.forEach(s => {
      s.ranks.forEach(r => {
        if (r.rank === null || !r.inTopN) return;

        const x = xScale(r.month);
        const y = yScale(r.rank);

        // Small circle behind flag
        g.append('circle')
          .attr('cx', x)
          .attr('cy', y)
          .attr('r', this.config.nodeRadius)
          .attr('fill', s.color)
          .attr('class', 'bump-node')
          .attr('data-iso3', s.iso3)
          .attr('data-month', r.month);

        // Flag image
        g.append('image')
          .attr('href', DataLoader.flagPath(s.iso2))
          .attr('x', x - fw / 2)
          .attr('y', y - fh / 2)
          .attr('width', fw)
          .attr('height', fh)
          .attr('class', 'bump-flag')
          .attr('data-iso3', s.iso3)
          .attr('data-month', r.month);
      });
    });
  },

  _renderAnnotations(annotations, series) {
    if (!annotations || !annotations.length) return;

    const g = this.svg.append('g').attr('class', 'annotations');
    const xScale = this.xScale;
    const yScale = this.yScale;

    // Stagger annotations vertically to avoid overlap
    const tiers = [28, 40, 52];
    let tierIdx = 0;

    annotations.forEach(ann => {
      const x = xScale(ann.month);
      if (x == null) return;

      const textY = tiers[tierIdx % tiers.length];
      tierIdx++;

      // Find the country's rank at this month for line target
      let targetY = this.config.marginTop;
      if (ann.iso3) {
        const s = series.find(s => s.iso3 === ann.iso3);
        if (s) {
          const r = s.ranks.find(r => r.month === ann.month);
          if (r && r.rank) targetY = yScale(r.rank);
        }
      }

      // Connector line
      g.append('line')
        .attr('x1', x)
        .attr('x2', x)
        .attr('y1', textY + 4)
        .attr('y2', targetY - 8)
        .attr('class', 'annotation-line');

      // Text
      g.append('text')
        .attr('x', x)
        .attr('y', textY)
        .attr('text-anchor', 'middle')
        .attr('class', 'annotation-text')
        .text(ann.text);
    });
  },

  _renderHoverColumns(months, height) {
    const g = this.svg.append('g').attr('class', 'hover-columns');
    const mw = this.config.monthWidth;

    months.forEach(month => {
      const x = this.xScale(month);
      g.append('rect')
        .attr('x', x - mw / 2)
        .attr('y', 0)
        .attr('width', mw)
        .attr('height', height)
        .attr('fill', 'transparent')
        .attr('class', 'hover-col')
        .attr('data-month', month)
        .on('mouseenter', () => this._onHover(month))
        .on('mouseleave', () => this._onLeave())
        .on('click', () => this._onClick(month));
    });
  },

  _onHover(month) {
    if (this.locked) return;
    this._highlightMonth(month);
  },

  _onLeave() {
    if (this.locked) return;
    this._clearHighlight();
  },

  _onClick(month) {
    // Find the top country for this month
    const topSeries = this._topSeriesForMonth(month);
    if (!topSeries) return;

    if (this.locked && this.locked.month === month && this.locked.iso3 === topSeries.iso3) {
      // Click same = unlock
      this.locked = null;
      this._clearHighlight();
      this.onSelect(null, null, null);
    } else {
      this.locked = { month, iso3: topSeries.iso3 };
      this._highlightMonth(month);
      this.onSelect(month, topSeries.iso3, topSeries);
    }
  },

  _highlightMonth(month) {
    const topSeries = this._topSeriesForMonth(month);
    if (!topSeries) return;

    // Dim all lines
    this.svg.selectAll('.bump-line')
      .classed('dimmed', true)
      .classed('highlighted', false);

    // Highlight the top country's line
    this.svg.selectAll(`.bump-line[data-iso3="${topSeries.iso3}"]`)
      .classed('dimmed', false)
      .classed('highlighted', true);

    // Dim all flags except for this month
    this.svg.selectAll('.bump-flag, .bump-node')
      .classed('dimmed', d => true);
    this.svg.selectAll(`.bump-flag[data-month="${month}"], .bump-node[data-month="${month}"]`)
      .classed('dimmed', false);

    // Show tooltip
    this._showTooltip(month, topSeries);

    // Notify detail panel
    this.onSelect(month, topSeries.iso3, topSeries);
  },

  _clearHighlight() {
    this.svg.selectAll('.bump-line')
      .classed('dimmed', false)
      .classed('highlighted', false);
    this.svg.selectAll('.bump-flag, .bump-node')
      .classed('dimmed', false);
    this._hideTooltip();
  },

  _topSeriesForMonth(month) {
    // Find series with rank 1 (or lowest rank) for this month
    let best = null;
    let bestRank = Infinity;
    for (const s of this.data.series) {
      const r = s.ranks.find(r => r.month === month);
      if (r && r.rank !== null && r.rank < bestRank) {
        bestRank = r.rank;
        best = s;
      }
    }
    return best;
  },

  _showTooltip(month, series) {
    this._hideTooltip();

    const r = series.ranks.find(r => r.month === month);
    if (!r || r.rank === null) return;

    const x = this.xScale(month);
    const y = this.yScale(r.rank);

    const tooltip = document.createElement('div');
    tooltip.className = 'bump-tooltip';
    tooltip.innerHTML = `
      <img src="${DataLoader.flagPath(series.iso2)}" alt="${series.name}" class="tooltip-flag" />
      <div class="tooltip-body">
        <strong>${series.name}</strong>
        <span class="tooltip-detail">Rank #${r.rank} &middot; ${r.count} mentions</span>
        <span class="tooltip-month">${DataLoader.formatMonth(month)}</span>
      </div>
    `;

    // Position relative to chart container
    const containerRect = this.container.getBoundingClientRect();
    const svgRect = this.svg.node().getBoundingClientRect();
    tooltip.style.left = (x + svgRect.left - containerRect.left + this.container.scrollLeft + 15) + 'px';
    tooltip.style.top = (y + svgRect.top - containerRect.top - 20) + 'px';

    this.container.appendChild(tooltip);
  },

  _hideTooltip() {
    const existing = this.container.querySelector('.bump-tooltip');
    if (existing) existing.remove();
  },

  _ordinal(n) {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  },

  /**
   * Update with new topN value.
   */
  updateTopN(newTopN, monthlyAll) {
    this.topN = newTopN;
    this.data = DataTransform.buildRankedSeries(monthlyAll, newTopN);
    this.locked = null;
    this.render();
  },
};
