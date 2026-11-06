// Evaluate healed selectors in real Chromium through Playwright.
//
// Usage: node benchmarks/browser_check.cjs <plan.json> <out.json>
// (normally invoked by benchmarks/browser_check.py)
//
// Each v2.html is loaded from disk with JavaScript disabled, so the browser
// sees the same static DOM (including declarative shadow roots) that
// dom-healer saw. The ground-truth markers (data-dh-target) are still in the
// raw files, which lets the browser side identify the true element.
const fs = require("fs");
const { chromium } = require("playwright");

async function probe(page, engine, selector) {
  try {
    const locator = page.locator(`${engine}=${selector}`);
    const count = await locator.count();
    const markers = [];
    for (let i = 0; i < Math.min(count, 5); i++) {
      markers.push(await locator.nth(i).evaluate((el) => el.getAttribute("data-dh-target")));
    }
    return { count, markers };
  } catch (err) {
    return { error: String(err).split("\n")[0].slice(0, 200) };
  }
}

(async () => {
  const [planPath, outPath] = process.argv.slice(2);
  const plan = JSON.parse(fs.readFileSync(planPath, "utf-8"));
  const browser = await chromium.launch();
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  const results = [];
  for (const suite of plan.suites) {
    await page.goto("file://" + suite.v2_path, { waitUntil: "load" });
    const shadowRoots = await page.evaluate(() => {
      let n = 0;
      const walk = (root) => {
        for (const el of root.querySelectorAll("*")) {
          if (el.shadowRoot) {
            n += 1;
            walk(el.shadowRoot);
          }
        }
      };
      walk(document);
      return n;
    });
    for (const t of suite.targets) {
      results.push({
        suite: suite.suite,
        target: t.target,
        shadow_roots_in_page: shadowRoots,
        truth: await probe(page, "css", `[data-dh-target="${t.target}"]`),
        css: await probe(page, "css", t.css),
        xpath: await probe(page, "xpath", t.xpath),
      });
    }
  }
  await browser.close();
  fs.writeFileSync(outPath, JSON.stringify(results, null, 1));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
