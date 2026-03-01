/**
 * Story Insights — auto-generates editorial narrative blocks from data.
 */

const StoryInsights = {

  generate(monthlyTop) {
    const insights = [];

    if (!monthlyTop || monthlyTop.length === 0) return insights;

    if (monthlyTop.length < 3) {
      insights.push({
        kicker: 'Early days',
        headline: 'The archive is growing',
        body: `Only ${monthlyTop.length} month${monthlyTop.length !== 1 ? 's' : ''} of data collected so far. As the pipeline backfills to 2013, patterns in congressional attention will emerge here.`,
      });
      return insights;
    }

    // Dominance — which country led most months
    const countByCountry = {};
    for (const d of monthlyTop) {
      countByCountry[d.country_name] = (countByCountry[d.country_name] || 0) + 1;
    }
    const sorted = Object.entries(countByCountry).sort((a, b) => b[1] - a[1]);
    const [topName, topCount] = sorted[0];
    const totalMonths = monthlyTop.length;
    const pct = Math.round((topCount / totalMonths) * 100);
    insights.push({
      kicker: 'Dominance',
      headline: `${topName} leads in ${topCount} of ${totalMonths} months`,
      body: `Accounting for ${pct}% of all months tracked, ${topName} is the most frequently top-mentioned country in congressional records.`,
    });

    // Latest — most recent month
    const latest = monthlyTop[monthlyTop.length - 1];
    let latestBody = `With ${latest.mention_count} mention${latest.mention_count !== 1 ? 's' : ''} across ${latest.total_records_scanned} records, ${latest.country_name} led congressional language.`;
    if (latest.runner_up_name) {
      latestBody += ` The runner-up was ${latest.runner_up_name} with ${latest.runner_up_count}.`;
    }
    insights.push({
      kicker: 'Latest',
      headline: `${DataLoader.formatMonthLong(latest.month)}: ${latest.country_name}`,
      body: latestBody,
    });

    // Breadth — unique countries
    const uniqueCountries = [...new Set(monthlyTop.map(d => d.country_name))];
    insights.push({
      kicker: 'Breadth',
      headline: `${uniqueCountries.length} different countries have led`,
      body: `Across ${totalMonths} months of data, ${uniqueCountries.length} distinct nations have topped the congressional mention count.`,
    });

    return insights;
  },

  render(insights) {
    const container = document.getElementById('insights');
    if (!container) return;

    container.innerHTML = '';

    if (insights.length === 0) return;

    const divider = document.createElement('div');
    divider.className = 'insights-divider';
    container.appendChild(divider);

    for (const ins of insights) {
      const article = document.createElement('article');
      article.className = 'insight';
      article.innerHTML = `
        <span class="insight-kicker">${ins.kicker}</span>
        <h3 class="insight-headline">${ins.headline}</h3>
        <p class="insight-body">${ins.body}</p>
      `;
      container.appendChild(article);
    }
  },
};
