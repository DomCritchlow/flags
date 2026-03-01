/**
 * Congressional World View — Main data story orchestrator.
 */

(async function() {
  'use strict';

  try {
    const { monthlyTop, metadata, monthlyTopBySource } = await DataLoader.loadAll();

    if (!monthlyTop || monthlyTop.length === 0) {
      document.querySelector('.grid-section').innerHTML =
        '<p style="text-align:center;padding:3rem;color:var(--text-muted);">No data yet. Run the pipeline to generate data.</p>';
      return;
    }

    // Masthead edition line
    const first = monthlyTop[0].month;
    const last = monthlyTop[monthlyTop.length - 1].month;
    const editionEl = document.querySelector('.masthead-edition');
    if (editionEl) {
      editionEl.textContent =
        `${DataLoader.formatMonthLong(first)} \u2013 ${DataLoader.formatMonthLong(last)} | ${monthlyTop.length} months of data`;
    }

    // -- Detail panel handler --
    function showDetail(entry) {
      const detail = document.getElementById('cell-detail');
      if (!entry) {
        detail.classList.add('hidden');
        return;
      }

      document.getElementById('detail-flag').src = DataLoader.flagPath(entry.country_iso2);
      document.getElementById('detail-flag').alt = entry.country_name;
      document.getElementById('detail-country').textContent = entry.country_name;
      document.getElementById('detail-month').textContent = DataLoader.formatMonthLong(entry.month);
      document.getElementById('detail-count').textContent = entry.mention_count;
      document.getElementById('detail-total').textContent = entry.total_records_scanned;
      document.getElementById('detail-runner-up').textContent =
        entry.runner_up_name ? `${entry.runner_up_name} (${entry.runner_up_count})` : '\u2014';

      const titlesList = document.getElementById('detail-titles');
      titlesList.innerHTML = '';
      const titles = entry.sample_titles || [];
      if (titles.length > 0) {
        for (const t of titles) {
          const li = document.createElement('li');
          li.textContent = t;
          titlesList.appendChild(li);
        }
      } else {
        const li = document.createElement('li');
        li.textContent = 'No sample titles available';
        li.style.fontStyle = 'italic';
        li.style.borderLeft = 'none';
        titlesList.appendChild(li);
      }

      detail.classList.remove('hidden');
      detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // -- Build per-source monthlyTop arrays from monthlyTopBySource --
    function buildSourceTop(source) {
      if (!monthlyTopBySource) return [];
      const entries = [];
      for (const [month, sources] of Object.entries(monthlyTopBySource)) {
        const s = sources[source];
        if (s) {
          entries.push({
            month: month,
            country_iso3: s.iso3,
            country_iso2: s.iso2,
            country_name: s.name,
            mention_count: s.count,
            total_records_scanned: s.count,
            runner_up_iso3: null,
            runner_up_iso2: null,
            runner_up_name: null,
            runner_up_count: 0,
            sample_titles: s.sample_titles || [],
          });
        }
      }
      entries.sort((a, b) => a.month.localeCompare(b.month));
      return entries;
    }

    // -- Initialize grid with "all" data --
    let activeSource = 'all';

    FlagGrid.init(monthlyTop, { onCellClick: showDetail });

    // -- Source toggle --
    const toggleContainer = document.getElementById('source-toggle');
    if (toggleContainer) {
      toggleContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.toggle-btn');
        if (!btn) return;

        const source = btn.dataset.source;
        if (source === activeSource) return;

        // Update active button
        toggleContainer.querySelector('.active').classList.remove('active');
        btn.classList.add('active');
        activeSource = source;

        // Hide detail card
        document.getElementById('cell-detail').classList.add('hidden');

        // Get filtered data
        const filtered = source === 'all' ? monthlyTop : buildSourceTop(source);

        // Re-render grid
        FlagGrid.update(filtered);

        // Re-render insights
        const insights = StoryInsights.generate(filtered);
        StoryInsights.render(insights);
      });
    }

    // Detail close button
    const closeBtn = document.querySelector('.detail-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        document.getElementById('cell-detail').classList.add('hidden');
        if (FlagGrid.selectedCell) {
          FlagGrid.selectedCell.classList.remove('selected');
          FlagGrid.selectedCell = null;
        }
      });
    }

    // Insights
    const insights = StoryInsights.generate(monthlyTop);
    StoryInsights.render(insights);

    // Footer
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
