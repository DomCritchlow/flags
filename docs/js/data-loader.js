/**
 * Data loader — fetches aggregated JSON files for the frontend.
 */

const DataLoader = {
  basePath: 'data/',

  async loadAll() {
    try {
      const [monthlyTop, monthlyAll, metadata, monthlyTopBySource] = await Promise.all([
        this.fetchJSON('monthly_top.json'),
        this.fetchJSON('monthly_all.json'),
        this.fetchJSON('metadata.json'),
        this.fetchJSON('monthly_top_by_source.json'),
      ]);
      return { monthlyTop, monthlyAll, metadata, monthlyTopBySource };
    } catch (err) {
      console.error('Failed to load data:', err);
      throw err;
    }
  },

  async loadExecutive() {
    try {
      const [monthlyTop, monthlyAll, metadata] = await Promise.all([
        this.fetchJSON('executive_monthly_top.json'),
        this.fetchJSON('executive_monthly_all.json'),
        this.fetchJSON('executive_metadata.json'),
      ]);
      return { monthlyTop, monthlyAll, metadata };
    } catch (err) {
      console.error('Failed to load executive data:', err);
      throw err;
    }
  },

  async fetchJSON(filename) {
    const response = await fetch(this.basePath + filename);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} loading ${filename}`);
    }
    return response.json();
  },

  /**
   * Format a YYYY-MM string for display.
   */
  formatMonth(monthStr) {
    const [year, month] = monthStr.split('-');
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    return `${months[parseInt(month) - 1]} ${year}`;
  },

  /**
   * Format a YYYY-MM string as full month name + year.
   */
  formatMonthLong(monthStr) {
    const [year, month] = monthStr.split('-');
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return `${months[parseInt(month) - 1]} ${year}`;
  },

  /**
   * Get the flag image path for an ISO2 code.
   */
  flagPath(iso2) {
    if (!iso2) return '';
    return `flags/${iso2.toLowerCase()}.svg`;
  },
};
