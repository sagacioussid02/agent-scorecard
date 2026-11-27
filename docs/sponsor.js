/*
 * Sponsor slot config, shared by index.html (the "Presented by" slot under
 * the scored repos) and sponsor.html (the rate page).
 *
 * To run a sponsor: fill in `sponsor` and push. The slot shows only from
 * `start` to `end` (inclusive, UTC dates), so it switches itself off when the
 * month is over. Leave `sponsor` as null and the slot shows "This slot is
 * open", linking to the rate page.
 *
 * Only https links and logos are shown; anything else is ignored.
 */
window.SPONSOR_CONFIG = {
  sponsor: null,
  // Example:
  // sponsor: {
  //   name: "Acme Guard",
  //   url: "https://acme.example/?utm_source=agent-scorecard&utm_medium=sponsor",
  //   logo: "https://acme.example/logo.svg",   // optional, square works best
  //   tagline: "Runtime policy checks for agent tool calls.",
  //   start: "2026-12-01",
  //   end: "2026-12-31",
  // },

  // Rate page. Price is per calendar month, one sponsor at a time.
  price: 49,
  currency: "USD",
  // Gumroad product link once it exists. Empty means "Book the slot" opens an email.
  checkoutUrl: "https://binosus.gumroad.com/l/sponsor",
  bookEmail: "siddharthuncc@gmail.com",

  // Audience numbers shown on the rate page. Update before pitching a sponsor.
  statsAsOf: "27 November 2026",
  stats: [
    { value: "21", label: "unique GitHub visitors in the last 14 days" },
    { value: "24", label: "unique clones in the last 14 days" },
    { value: "27", label: "safety checks across seven layers" },
    { value: "7", label: "public agent repos scored on the site" },
  ],
};

(function () {
  const httpsOnly = (u) => {
    try { return new URL(u).protocol === "https:" ? new URL(u).href : null; } catch { return null; }
  };
  const day = (s) => (/^\d{4}-\d{2}-\d{2}$/.test(s || "") ? Date.parse(s + "T00:00:00Z") : NaN);

  // The sponsor to show right now, or null. `now` is a Date (for tests).
  window.activeSponsor = function (cfg, now) {
    const s = cfg && cfg.sponsor;
    if (!s || !s.name || !httpsOnly(s.url)) return null;
    const start = day(s.start), end = day(s.end);
    if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null;
    const t = (now || new Date()).getTime();
    if (t < start || t >= end + 86400000) return null;
    return {
      name: String(s.name).slice(0, 60),
      url: httpsOnly(s.url),
      logo: s.logo ? httpsOnly(s.logo) : null,
      tagline: s.tagline ? String(s.tagline).slice(0, 120) : "",
    };
  };

  // Where "Book the slot" goes: the Gumroad link if set, else an email.
  window.sponsorCheckout = function (cfg) {
    const url = httpsOnly(cfg && cfg.checkoutUrl);
    if (url) return { href: url, external: true };
    const subject = encodeURIComponent("Sponsor slot on agent-scorecard");
    return { href: "mailto:" + cfg.bookEmail + "?subject=" + subject, external: false };
  };
})();
