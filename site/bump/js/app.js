/**
 * Congressional World View — Bump Chart application entry point.
 */

(async function() {
  'use strict';

  // Override paths for subsite
  DataLoader.basePath = '../data/';
  const origFlagPath = DataLoader.flagPath.bind(DataLoader);
  DataLoader.flagPath = (iso2) => '../' + origFlagPath(iso2);

  const chartContainer = document.getElementById('chart-container');
  const topNSelect = document.getElementById('top-n-select');
  const scrollHint = document.getElementById('scroll-hint');
  const lastUpdateEl = document.getElementById('last-update');

  try {
    // Load all data
    const { monthlyAll, metadata } = await DataLoader.loadAll();

    if (!monthlyAll || Object.keys(monthlyAll).length === 0) {
      chartContainer.innerHTML = `
        <div style="text-align:center; padding:3rem; color:var(--text-muted);">
          <p>No data available yet.</p>
          <p style="margin-top:0.5rem; font-size:0.8rem;">
            Run: <code>python -m pipeline.run --month 2024-12</code>
          </p>
        </div>
      `;
      return;
    }

    // Build ranked series
    const topN = parseInt(topNSelect.value, 10);
    const rankedData = DataTransform.buildRankedSeries(monthlyAll, topN);

    // Initialize detail panel
    DetailPanel.init(monthlyAll, rankedData);

    // Initialize bump chart
    BumpChart.init(chartContainer, rankedData, {
      topN,
      onSelect(month, iso3, seriesEntry) {
        DetailPanel.update(month, iso3, seriesEntry);
      },
    });

    // Top-N control
    topNSelect.addEventListener('change', () => {
      const newTopN = parseInt(topNSelect.value, 10);
      BumpChart.updateTopN(newTopN, monthlyAll);
      DetailPanel.init(monthlyAll, BumpChart.data);
      DetailPanel.update(null, null, null);
    });

    // Scroll hint — hide after user scrolls
    if (scrollHint && chartContainer.scrollWidth > chartContainer.clientWidth) {
      chartContainer.addEventListener('scroll', function onScroll() {
        scrollHint.classList.add('hidden');
        chartContainer.removeEventListener('scroll', onScroll);
      }, { passive: true });
    } else if (scrollHint) {
      scrollHint.classList.add('hidden');
    }

    // Scroll chart to end (most recent data)
    chartContainer.scrollLeft = chartContainer.scrollWidth;

    // Footer metadata
    if (metadata && lastUpdateEl) {
      const date = new Date(metadata.last_run);
      lastUpdateEl.textContent = `Last updated: ${date.toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
      })}`;
    }

  } catch (err) {
    console.error('Failed to initialize:', err);
    chartContainer.innerHTML = `
      <div style="text-align:center; padding:3rem; color:var(--text-muted);">
        <p>Could not load data. Make sure the pipeline has been run at least once.</p>
        <p style="margin-top:0.5rem; font-size:0.8rem; color:#666;">
          Error: ${err.message}
        </p>
      </div>
    `;
  }
})();
