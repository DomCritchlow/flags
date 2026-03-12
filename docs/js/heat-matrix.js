/**
 * Heat Matrix — D3 visualization of country mentions across all months.
 * Countries on Y axis, months on X axis, cell color = mention count.
 * Labels SVG is fixed; cells SVG scrolls independently.
 */

const HeatMatrix = {

  render(allData, countries, months, wrapper) {
    const cellW = 7;
    const cellH = 16;
    const cellGap = 1;
    const labelW = 120;
    const flagW = 22;
    const flagH = 15;
    const margin = { top: 28, right: 16, bottom: 0 };

    const innerW = months.length * (cellW + cellGap) - cellGap;
    const innerH = countries.length * (cellH + cellGap) - cellGap;
    const svgH = margin.top + innerH + margin.bottom;

    // Color scale
    const allCounts = [];
    for (const c of countries) {
      for (const m of months) {
        const found = (allData[m]?.countries || []).find(x => x.iso3 === c.iso3);
        if (found?.count > 0) allCounts.push(found.count);
      }
    }
    allCounts.sort(d3.ascending);
    const maxCount = d3.quantile(allCounts, 0.95) || 1;

    const colorScale = count => {
      if (count === 0) return '#faf8f4';
      const t = Math.min(count / maxCount, 1);
      return d3.interpolateRgb('#fce4e4', '#c41e1e')(t);
    };

    // Layout: flex row, labels fixed + cells scrollable
    const chartsRow = d3.select(wrapper).select('#heat-matrix').append('div')
      .attr('class', 'hm-charts');

    // Labels SVG (fixed)
    const labelsSvg = chartsRow.append('svg')
      .attr('class', 'hm-labels')
      .attr('width', labelW)
      .attr('height', svgH)
      .style('font-family', 'IBM Plex Sans, sans-serif');

    for (let ci = 0; ci < countries.length; ci++) {
      const c = countries[ci];
      const y = margin.top + ci * (cellH + cellGap);

      labelsSvg.append('image')
        .attr('href', `flags/${(c.iso2 || 'xx').toLowerCase()}.svg`)
        .attr('x', 4)
        .attr('y', y + (cellH - flagH) / 2)
        .attr('width', flagW)
        .attr('height', flagH)
        .attr('preserveAspectRatio', 'xMidYMid meet');

      const displayName = c.name && c.name.length > 15
        ? c.name.slice(0, 14) + '\u2026'
        : (c.name || c.iso3);

      labelsSvg.append('text')
        .attr('x', flagW + 8)
        .attr('y', y + cellH / 2)
        .attr('fill', '#333')
        .attr('font-size', '10px')
        .attr('font-family', 'IBM Plex Sans, sans-serif')
        .attr('dominant-baseline', 'middle')
        .text(displayName);
    }

    // Scrollable cells container
    const scrollDiv = chartsRow.append('div')
      .attr('class', 'hm-scroll');

    const svgW = innerW + margin.right;
    const svg = scrollDiv.append('svg')
      .attr('width', svgW)
      .attr('height', svgH)
      .style('display', 'block')
      .style('font-family', 'IBM Plex Sans, sans-serif');

    const g = svg.append('g')
      .attr('transform', `translate(0,${margin.top})`);

    // Year labels + dividers
    const years = [...new Set(months.map(m => m.slice(0, 4)))];
    for (const year of years) {
      const firstIdx = months.findIndex(m => m.startsWith(year));
      if (firstIdx === -1) continue;
      const x = firstIdx * (cellW + cellGap);

      g.append('line')
        .attr('x1', x).attr('x2', x)
        .attr('y1', -margin.top + 4).attr('y2', innerH)
        .attr('stroke', '#d0d0d0')
        .attr('stroke-width', 0.5);

      g.append('text')
        .attr('x', x + 2)
        .attr('y', -margin.top + 16)
        .attr('fill', '#999')
        .attr('font-size', '9px')
        .attr('font-weight', '600')
        .attr('font-family', 'IBM Plex Sans, sans-serif')
        .text(year);
    }

    // Tooltip
    const tooltip = d3.select('#heat-tooltip');

    // Cells
    for (let ci = 0; ci < countries.length; ci++) {
      const c = countries[ci];
      const cy = ci * (cellH + cellGap);

      for (let mi = 0; mi < months.length; mi++) {
        const m = months[mi];
        const cx = mi * (cellW + cellGap);

        const monthEntry = allData[m];
        let count = 0;
        let titles = [];
        let rank = null;
        if (monthEntry) {
          const idx = (monthEntry.countries || []).findIndex(x => x.iso3 === c.iso3);
          if (idx !== -1) {
            count = monthEntry.countries[idx].count;
            titles = monthEntry.countries[idx].sample_titles || [];
            rank = idx + 1;
          }
        }

        g.append('rect')
          .attr('x', cx)
          .attr('y', cy)
          .attr('width', cellW)
          .attr('height', cellH)
          .attr('fill', colorScale(count))
          .attr('stroke', '#e8e4dd')
          .attr('stroke-width', 0.3)
          .attr('rx', 1)
          .on('mouseover', function(event) {
            tooltip.classed('hidden', false);
            tooltip.html(buildHeatTooltip(c, m, count, rank, titles));
            positionHeatTooltip(event, wrapper, tooltip.node(), labelW);
          })
          .on('mousemove', function(event) {
            positionHeatTooltip(event, wrapper, tooltip.node(), labelW);
          })
          .on('mouseout', function() {
            tooltip.classed('hidden', true);
          });
      }
    }

    // Legend
    const legendRow = d3.select(wrapper).select('#heat-matrix').append('div')
      .attr('class', 'hm-legend')
      .style('padding-left', labelW + 'px');

    legendRow.append('span').text('fewer mentions');

    const legendSvg = legendRow.append('svg')
      .attr('width', 80)
      .attr('height', 10);

    const defs = legendSvg.append('defs');
    const grad = defs.append('linearGradient').attr('id', 'heat-legend-grad');
    for (let i = 0; i <= 10; i++) {
      grad.append('stop')
        .attr('offset', `${i * 10}%`)
        .attr('stop-color', colorScale(i / 10 * maxCount));
    }
    legendSvg.append('rect')
      .attr('x', 0).attr('y', 1)
      .attr('width', 80).attr('height', 8)
      .attr('fill', 'url(#heat-legend-grad)')
      .attr('rx', 2);

    legendRow.append('span').text('more mentions');
  },
};

// Helpers

function buildHeatTooltip(c, month, count, rank, titles) {
  const monthStr = DataLoader.formatMonthLong(month);
  const flagUrl = `flags/${(c.iso2 || 'xx').toLowerCase()}.svg`;

  let html = `
    <div class="ht-header">
      <img class="ht-flag" src="${flagUrl}" alt="${c.name || c.iso3}" />
      <div>
        <strong>${c.name || c.iso3}</strong>
        <span class="ht-month">${monthStr}</span>
      </div>
    </div>
  `;

  if (count === 0) {
    html += `<p class="ht-zero">No mentions this month</p>`;
  } else {
    const rankStr = rank === 1 ? '#1' : rank ? `#${rank}` : '';
    html += `<p class="ht-count">${count} mention${count !== 1 ? 's' : ''} ${rankStr ? '&mdash; ' + rankStr + ' that month' : ''}</p>`;
    if (titles.length > 0) {
      html += `<ul class="ht-titles">`;
      for (const t of titles.slice(0, 2)) {
        const truncated = t.length > 85 ? t.slice(0, 84) + '\u2026' : t;
        html += `<li>${truncated}</li>`;
      }
      html += `</ul>`;
    }
  }
  return html;
}

function positionHeatTooltip(event, wrapper, node, labelW) {
  const rect = wrapper.getBoundingClientRect();
  const tw = node.offsetWidth || 260;
  const th = node.offsetHeight || 120;
  let x = event.clientX - rect.left + 12;
  let y = event.clientY - rect.top - th / 2;

  if (x + tw > rect.width - 10) x = event.clientX - rect.left - tw - 12;
  if (x < labelW) x = labelW + 4;
  if (y < 4) y = 4;
  if (y + th > rect.height - 4) y = rect.height - th - 4;

  d3.select('#heat-tooltip')
    .style('left', x + 'px')
    .style('top', y + 'px');
}
