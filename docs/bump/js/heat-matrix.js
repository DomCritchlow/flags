/**
 * Heat Matrix — D3 visualization of country mentions across all months.
 * Countries on Y axis, months on X axis, cell color = mention count.
 */

const HeatMatrix = {

  render(allData, countries, months, wrapper) {
    const cellW = 7;
    const cellH = 16;
    const cellGap = 1;
    const labelW = 118;
    const flagW = 22;
    const flagH = 15;
    const margin = { top: 48, right: 16, bottom: 12, left: labelW };

    const innerW = months.length * (cellW + cellGap) - cellGap;
    const innerH = countries.length * (cellH + cellGap) - cellGap;
    const svgW = margin.left + innerW + margin.right;
    const svgH = margin.top + innerH + margin.bottom;

    // ── Color scale ──────────────────────────────────────────────────────────
    // Collect all non-zero counts to find a reasonable max
    const allCounts = [];
    for (const c of countries) {
      for (const m of months) {
        const found = (allData[m]?.countries || []).find(x => x.iso3 === c.iso3);
        if (found?.count > 0) allCounts.push(found.count);
      }
    }
    allCounts.sort(d3.ascending);
    const maxCount = d3.quantile(allCounts, 0.95) || 1;

    // 0 → page background, 1+ → reds
    const colorScale = count => {
      if (count === 0) return '#faf8f4';
      const t = Math.min(count / maxCount, 1);
      return d3.interpolateRgb('#fce4e4', '#c41e1e')(t);
    };

    // ── SVG ──────────────────────────────────────────────────────────────────
    const svg = d3.select('#heat-matrix')
      .append('svg')
      .attr('width', svgW)
      .attr('height', svgH)
      .style('font-family', 'IBM Plex Sans, sans-serif');

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // ── Year labels + dividers ────────────────────────────────────────────────
    const years = [...new Set(months.map(m => m.slice(0, 4)))];
    for (const year of years) {
      const firstIdx = months.findIndex(m => m.startsWith(year));
      if (firstIdx === -1) continue;
      const x = firstIdx * (cellW + cellGap);

      // Divider
      g.append('line')
        .attr('x1', x).attr('x2', x)
        .attr('y1', -margin.top + 4).attr('y2', innerH)
        .attr('stroke', '#d0d0d0')
        .attr('stroke-width', 0.5);

      // Year label
      g.append('text')
        .attr('x', x + 2)
        .attr('y', -margin.top + 16)
        .attr('class', 'heat-year-label')
        .attr('fill', '#999')
        .attr('font-size', '9px')
        .attr('font-weight', '600')
        .attr('font-family', 'IBM Plex Sans, sans-serif')
        .text(year);
    }

    // ── Country labels + flags (Y axis) ──────────────────────────────────────
    for (let ci = 0; ci < countries.length; ci++) {
      const c = countries[ci];
      const y = ci * (cellH + cellGap);
      const midY = y + cellH / 2;

      // Flag
      svg.append('image')
        .attr('href', `../flags/${(c.iso2 || 'xx').toLowerCase()}.svg`)
        .attr('x', margin.left - labelW + 4)
        .attr('y', margin.top + y + (cellH - flagH) / 2)
        .attr('width', flagW)
        .attr('height', flagH)
        .attr('preserveAspectRatio', 'xMidYMid meet');

      // Name
      const displayName = c.name && c.name.length > 15
        ? c.name.slice(0, 14) + '\u2026'
        : (c.name || c.iso3);

      svg.append('text')
        .attr('x', margin.left - labelW + flagW + 8)
        .attr('y', margin.top + midY)
        .attr('class', 'heat-country-label')
        .attr('fill', '#333')
        .attr('font-size', '10px')
        .attr('font-family', 'IBM Plex Sans, sans-serif')
        .attr('dominant-baseline', 'middle')
        .text(displayName);
    }

    // ── Tooltip ───────────────────────────────────────────────────────────────
    const tooltip = d3.select('#heat-tooltip');

    // ── Cells ─────────────────────────────────────────────────────────────────
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
            // Highlight row
            d3.selectAll('.heat-row-' + ci).attr('opacity', 1);

            tooltip.classed('hidden', false);
            tooltip.html(buildTooltip(c, m, count, rank, titles));
            positionTooltip(event, wrapper, tooltip.node());
          })
          .on('mousemove', function(event) {
            positionTooltip(event, wrapper, tooltip.node());
          })
          .on('mouseout', function() {
            tooltip.classed('hidden', true);
          });
      }
    }

    // ── Legend ────────────────────────────────────────────────────────────────
    const legendW = 100;
    const legendH = 8;
    const legendX = margin.left;
    const legendY = svgH - margin.bottom - legendH;

    const defs = svg.append('defs');
    const grad = defs.append('linearGradient').attr('id', 'heat-legend-grad');
    for (let i = 0; i <= 10; i++) {
      grad.append('stop')
        .attr('offset', `${i * 10}%`)
        .attr('stop-color', colorScale(i / 10 * maxCount));
    }

    svg.append('rect')
      .attr('x', legendX)
      .attr('y', legendY)
      .attr('width', legendW)
      .attr('height', legendH)
      .attr('fill', 'url(#heat-legend-grad)')
      .attr('rx', 2);

    svg.append('text')
      .attr('x', legendX)
      .attr('y', legendY - 3)
      .attr('font-size', '8px')
      .attr('fill', '#999')
      .attr('font-family', 'IBM Plex Sans, sans-serif')
      .text('fewer mentions');

    svg.append('text')
      .attr('x', legendX + legendW)
      .attr('y', legendY - 3)
      .attr('font-size', '8px')
      .attr('fill', '#999')
      .attr('text-anchor', 'end')
      .attr('font-family', 'IBM Plex Sans, sans-serif')
      .text('more mentions');
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildTooltip(c, month, count, rank, titles) {
  const monthStr = DataLoader.formatMonthLong(month);
  const flagUrl = `../flags/${(c.iso2 || 'xx').toLowerCase()}.svg`;

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

function positionTooltip(event, wrapper, node) {
  const rect = wrapper.getBoundingClientRect();
  const tw = node.offsetWidth || 260;
  const th = node.offsetHeight || 120;
  let x = event.clientX - rect.left + 12;
  let y = event.clientY - rect.top - th / 2;

  if (x + tw > rect.width - 10) x = event.clientX - rect.left - tw - 12;
  if (y < 4) y = 4;
  if (y + th > rect.height - 4) y = rect.height - th - 4;

  d3.select('#heat-tooltip')
    .style('left', x + 'px')
    .style('top', y + 'px');
}
