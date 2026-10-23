import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = new URL('../', import.meta.url);
const evidence = new URL('evidence/', root);
const target = process.env.TEST_URL || 'http://127.0.0.1:4174/';
await mkdir(evidence, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
});
const results = [];
for (const width of [1440, 768, 390, 320]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(target, { waitUntil: 'networkidle' });
  const data = await page.evaluate(() => ({
    title: document.title,
    h1: document.querySelector('h1')?.textContent.trim(),
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    colophon: document.querySelectorAll('#cwu-colophon').length,
    sections: document.querySelectorAll('main section').length,
    footer: Boolean(document.querySelector('footer')),
  }));
  const label = target.startsWith('http://127.0.0.1') ? 'local' : 'live';
  await page.screenshot({ path: fileURLToPath(new URL(`${label}-${width}.png`, evidence)), fullPage: true });
  results.push({ width, ...data, errors });
  await page.close();
}
await browser.close();
console.log(JSON.stringify(results, null, 2));

if (results.some(result => result.scrollWidth !== result.clientWidth || result.colophon !== 1 || result.errors.length)) {
  process.exitCode = 1;
}
