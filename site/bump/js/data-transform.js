/**
 * Data transform — converts monthly_all.json into ranked series for D3 bump chart.
 */

const DataTransform = {

  CONGRESS_SESSIONS: [
    { number: 93,  startMonth: '1973-01', endMonth: '1975-01' },
    { number: 94,  startMonth: '1975-01', endMonth: '1977-01' },
    { number: 95,  startMonth: '1977-01', endMonth: '1979-01' },
    { number: 96,  startMonth: '1979-01', endMonth: '1981-01' },
    { number: 97,  startMonth: '1981-01', endMonth: '1983-01' },
    { number: 98,  startMonth: '1983-01', endMonth: '1985-01' },
    { number: 99,  startMonth: '1985-01', endMonth: '1987-01' },
    { number: 100, startMonth: '1987-01', endMonth: '1989-01' },
    { number: 101, startMonth: '1989-01', endMonth: '1991-01' },
    { number: 102, startMonth: '1991-01', endMonth: '1993-01' },
    { number: 103, startMonth: '1993-01', endMonth: '1995-01' },
    { number: 104, startMonth: '1995-01', endMonth: '1997-01' },
    { number: 105, startMonth: '1997-01', endMonth: '1999-01' },
    { number: 106, startMonth: '1999-01', endMonth: '2001-01' },
    { number: 107, startMonth: '2001-01', endMonth: '2003-01' },
    { number: 108, startMonth: '2003-01', endMonth: '2005-01' },
    { number: 109, startMonth: '2005-01', endMonth: '2007-01' },
    { number: 110, startMonth: '2007-01', endMonth: '2009-01' },
    { number: 111, startMonth: '2009-01', endMonth: '2011-01' },
    { number: 112, startMonth: '2011-01', endMonth: '2013-01' },
    { number: 113, startMonth: '2013-01', endMonth: '2015-01' },
    { number: 114, startMonth: '2015-01', endMonth: '2017-01' },
    { number: 115, startMonth: '2017-01', endMonth: '2019-01' },
    { number: 116, startMonth: '2019-01', endMonth: '2021-01' },
    { number: 117, startMonth: '2021-01', endMonth: '2023-01' },
    { number: 118, startMonth: '2023-01', endMonth: '2025-01' },
    { number: 119, startMonth: '2025-01', endMonth: '2027-01' },
  ],

  ANNOTATIONS: [
    { month: '1973-10', text: 'Yom Kippur War', iso3: 'ISR' },
    { month: '1975-04', text: 'Fall of Saigon', iso3: 'VNM' },
    { month: '1979-01', text: 'Iran hostage crisis', iso3: 'IRN' },
    { month: '1979-12', text: 'Soviet invasion of Afghanistan', iso3: 'AFG' },
    { month: '1982-04', text: 'Falklands War', iso3: 'ARG' },
    { month: '1983-10', text: 'Grenada invasion', iso3: 'GRD' },
    { month: '1986-04', text: 'Libya bombing', iso3: 'LBY' },
    { month: '1989-06', text: 'Tiananmen Square', iso3: 'CHN' },
    { month: '1989-12', text: 'Panama invasion', iso3: 'PAN' },
    { month: '1990-08', text: 'Iraq invades Kuwait', iso3: 'IRQ' },
    { month: '1991-12', text: 'Soviet Union dissolves', iso3: 'RUS' },
    { month: '1994-07', text: 'Rwanda genocide', iso3: 'RWA' },
    { month: '1999-03', text: 'NATO bombs Yugoslavia', iso3: 'SRB' },
    { month: '2001-09', text: 'September 11 attacks', iso3: 'AFG' },
    { month: '2003-03', text: 'Iraq War begins', iso3: 'IRQ' },
    { month: '2011-05', text: 'Bin Laden killed', iso3: 'PAK' },
    { month: '2014-03', text: 'Russia annexes Crimea', iso3: 'RUS' },
    { month: '2015-07', text: 'Iran Nuclear Deal', iso3: 'IRN' },
    { month: '2017-08', text: 'North Korea ICBM tests', iso3: 'PRK' },
    { month: '2018-03', text: 'US-China trade war begins', iso3: 'CHN' },
    { month: '2019-12', text: 'COVID-19 emerges', iso3: 'CHN' },
    { month: '2020-01', text: 'Soleimani strike', iso3: 'IRN' },
    { month: '2021-08', text: 'Afghanistan withdrawal', iso3: 'AFG' },
    { month: '2022-02', text: 'Russia invades Ukraine', iso3: 'UKR' },
    { month: '2023-10', text: 'Israel-Hamas war', iso3: 'ISR' },
  ],

  COLORS: [
    '#4fc3f7', '#ef5350', '#66bb6a', '#ab47bc', '#ff7043',
    '#26c6da', '#ec407a', '#8d6e63', '#78909c', '#29b6f6',
    '#9ccc65', '#ffca28', '#7e57c2', '#26a69a', '#d4e157',
  ],

  /**
   * Build ranked series from monthly_all data.
   * @param {Object} monthlyAll - keyed by "YYYY-MM"
   * @param {number} topN - how many ranks to show
   * @returns {{ months, series, congressSessions }}
   */
  buildRankedSeries(monthlyAll, topN) {
    topN = topN || 10;
    const months = Object.keys(monthlyAll).sort();

    // Build per-month rankings
    const monthRanks = {};
    for (const month of months) {
      const countries = monthlyAll[month].countries || [];
      monthRanks[month] = countries.map((c, i) => ({
        ...c,
        rank: i + 1,
        inTopN: i < topN,
      }));
    }

    // Find all countries that ever appeared in top N
    const topCountries = new Map(); // iso3 -> { iso2, name, bestRank }
    for (const month of months) {
      for (const c of monthRanks[month]) {
        if (!c.inTopN) continue;
        const existing = topCountries.get(c.iso3);
        if (!existing || c.rank < existing.bestRank) {
          topCountries.set(c.iso3, {
            iso2: c.iso2,
            name: c.name,
            bestRank: c.rank,
          });
        }
      }
    }

    // Sort by best-ever rank for color assignment
    const sortedCountries = [...topCountries.entries()]
      .sort((a, b) => a[1].bestRank - b[1].bestRank);

    // Build series
    const series = sortedCountries.map(([iso3, info], colorIdx) => {
      const ranks = months.map(month => {
        const entry = monthRanks[month].find(c => c.iso3 === iso3);
        return {
          month,
          rank: entry && entry.inTopN ? entry.rank : null,
          count: entry ? entry.count : 0,
          inTopN: entry ? entry.inTopN : false,
          sampleTitles: entry ? (entry.sample_titles || []) : [],
        };
      });

      return {
        iso3,
        iso2: info.iso2,
        name: info.name,
        color: this.COLORS[colorIdx % this.COLORS.length],
        ranks,
      };
    });

    // Filter congress sessions to those overlapping our data range
    const firstMonth = months[0];
    const lastMonth = months[months.length - 1];
    const congressSessions = this.CONGRESS_SESSIONS.filter(
      s => s.endMonth > firstMonth && s.startMonth <= lastMonth
    );

    // Filter annotations to those within our data range
    const annotations = this.ANNOTATIONS.filter(
      a => a.month >= firstMonth && a.month <= lastMonth
    );

    return { months, series, congressSessions, annotations };
  },

  /**
   * Get the congress session a month belongs to.
   */
  getCongressForMonth(month) {
    for (const s of this.CONGRESS_SESSIONS) {
      if (month >= s.startMonth && month < s.endMonth) return s;
    }
    return null;
  },
};
