// Extracts visible watch links from a YouTube page.
// Called via eval_on_selector_all("a[href*='/watch']", script, {limit, excludeV, checkVisible})
(els, { limit, excludeV, checkVisible }) => {
    const seen = new Set();
    const out = [];
    for (const a of els) {
        const href = a.getAttribute('href');
        const text = (a.textContent || '').replace(/\s+/g, ' ').trim();
        const r = a.getBoundingClientRect();
        const visible = !checkVisible || (r.bottom > 0 && r.top < window.innerHeight);
        const excluded = excludeV && href && href.includes('v=' + excludeV);
        if (visible && href && text.length > 10 && text.length < 200 && !seen.has(href) && !excluded) {
            seen.add(href);
            out.push({ href, title: text });
        }
        if (out.length >= limit) break;
    }
    return out;
}
