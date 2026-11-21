// Screenshot the report page the way a judge would see it.
//
//   node scripts/shot_site.mjs
//
// Uses the playwright-core copy that is already in the workspace (no install).
import { chromium } from 'file:///C:/Users/%E5%BC%A0%E4%B8%80/WorkBuddy/spaces/2026_11_12_22-57-34/attribution/node_modules/playwright-core/index.mjs';
import path from 'node:path';
import url from 'node:url';

const here = path.dirname(url.fileURLToPath(import.meta.url));
const page_url = url.pathToFileURL(path.join(here, '..', 'site', 'index.html')).href;
const out = path.join(here, '..', 'out');

// Use the Chrome that is installed (Chrome, not Edge) or the cached chromium build;
// no browser download at run time.
const CHROME = 'C:/Users/张一/AppData/Local/Google/Chrome/Application/chrome.exe';
const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
for (const [name, width, height, full] of [
  ['shot-1280.png', 1280, 720, true],
  ['shot-first-screen.png', 1280, 720, false],
  ['shot-narrow.png', 420, 900, true],
]) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.goto(page_url, { waitUntil: 'load' });
  await page.screenshot({ path: path.join(out, name), fullPage: full });
  if (name === 'shot-first-screen.png') {
    const box = await page.evaluate(() => {
      const el = document.querySelector('.hero');
      const r = el.getBoundingClientRect();
      return { w: r.width, h: r.height };
    });
    console.log('hero box', JSON.stringify(box));
  }
  await page.close();
  console.log('wrote', name);
}
await browser.close();
