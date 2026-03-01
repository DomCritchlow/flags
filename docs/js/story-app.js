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

    // -- Inline detail panel --
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
      // Remove existing panel
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
          <img class="detail-flag" src="${DataLoader.flagPath(entry.country_iso2)}" alt="${entry.country_name}">
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
    let activeBranch = 'congress';
    let executiveData = null;

    // Store the congressional edition text for restoring on branch switch
    const congressEditionText = editionEl ? editionEl.textContent : '';

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

        // Close any open inline detail
        closeInlineDetail();

        // Get filtered data
        const filtered = source === 'all' ? monthlyTop : buildSourceTop(source);

        // Re-render grid
        FlagGrid.update(filtered);

        // Re-render insights
        const insights = StoryInsights.generate(filtered);
        StoryInsights.render(insights);
      });
    }

    // -- Branch toggle (Congress / Executive) --
    const branchContainer = document.getElementById('branch-toggle');
    if (branchContainer) {
      branchContainer.addEventListener('click', async (e) => {
        const btn = e.target.closest('.branch-btn');
        if (!btn) return;

        const branch = btn.dataset.branch;
        if (branch === activeBranch) return;

        activeBranch = branch;
        branchContainer.querySelector('.active').classList.remove('active');
        btn.classList.add('active');
        closeInlineDetail();

        const ledeCongressEl = document.getElementById('lede-congress');
        const ledeExecutiveEl = document.getElementById('lede-executive');
        const captionEl = document.getElementById('grid-caption');

        const titleEl = document.querySelector('.masthead-title');

        if (branch === 'executive') {
          document.body.classList.add('executive');
          if (toggleContainer) toggleContainer.style.display = 'none';
          if (ledeCongressEl) ledeCongressEl.style.display = 'none';
          if (ledeExecutiveEl) ledeExecutiveEl.style.display = '';
          if (titleEl) titleEl.textContent = 'U.S. Executive Orders World View';
          if (captionEl) captionEl.textContent =
            'Each flag represents the most-mentioned country in presidential executive orders that month. Tap a cell for details.';

          // Lazy-load executive data on first switch
          if (!executiveData) {
            executiveData = await DataLoader.loadExecutive();
          }

          FlagGrid.update(executiveData.monthlyTop);
          const exInsights = StoryInsights.generate(executiveData.monthlyTop);
          StoryInsights.render(exInsights);

          if (editionEl) {
            const exFirst = executiveData.monthlyTop[0]?.month;
            const exLast = executiveData.monthlyTop[executiveData.monthlyTop.length - 1]?.month;
            editionEl.textContent = exFirst && exLast
              ? `Executive Orders \u2014 ${DataLoader.formatMonthLong(exFirst)} \u2013 ${DataLoader.formatMonthLong(exLast)}`
              : 'Executive Orders';
          }
        } else {
          document.body.classList.remove('executive');
          if (toggleContainer) toggleContainer.style.display = '';
          if (ledeCongressEl) ledeCongressEl.style.display = '';
          if (ledeExecutiveEl) ledeExecutiveEl.style.display = 'none';
          if (captionEl) captionEl.textContent =
            'Each flag represents the most-mentioned country in congressional records that month. Tap a cell for details.';

          const filtered = activeSource === 'all' ? monthlyTop : buildSourceTop(activeSource);
          FlagGrid.update(filtered);
          const conInsights = StoryInsights.generate(filtered);
          StoryInsights.render(conInsights);

          if (titleEl) titleEl.textContent = 'U.S. Congressional World View';
          if (editionEl) editionEl.textContent = congressEditionText;
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
