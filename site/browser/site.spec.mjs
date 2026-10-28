import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';

for (const width of [1440, 360]) for (const theme of ['light', 'dark']) {
  test(`MoonBit design at ${width}px in ${theme}`, async ({ page }, info) => {
    const base = info.project.metadata.base;
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ colorScheme: theme });
    await page.goto(base);
    await expect(page.getByRole('heading', { name: 'Morphir, in Python', exact: true })).toBeVisible();
    await expect(page.locator('.hero .code-window')).toBeVisible();
    await expect(page.locator('.code-window pre')).toHaveCSS('background-color', 'rgb(15, 20, 27)');
    const model = await readFile(new URL('../../examples/model/acme/models.py', import.meta.url), 'utf8');
    expect((await page.locator('.code-window pre code').textContent()).trimEnd()).toBe(model.trimEnd());
    await expect(page.locator('.pipeline li')).toHaveCount(3);
    await expect(page.locator('.features .feature')).toHaveCount(3);
    await expect(page.locator('.button.primary')).toHaveCSS('background-color', 'rgb(255, 106, 0)');
    await expect(page.locator('body')).toHaveCSS('background-color', theme === 'dark' ? 'rgb(15, 20, 27)' : 'rgb(255, 255, 255)');
    const metrics = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth, columns: getComputedStyle(document.querySelector('.hero')).gridTemplateColumns.split(' ').length }));
    expect(metrics.width).toBeLessThanOrEqual(metrics.viewport + 1);
    expect(metrics.columns).toBe(width === 360 ? 1 : 2);
    await page.screenshot({ path: fileURLToPath(new URL(`../../.dev/site-browser/${info.project.name}-home-${width}-${theme}.png`, import.meta.url)), fullPage: true });
    await page.getByRole('link', { name: 'Start with Python', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'A Python model round trip', exact: true })).toBeVisible();
    await expect(page.locator('body')).toHaveCSS('background-color', theme === 'dark' ? 'rgb(15, 20, 27)' : 'rgb(255, 255, 255)');
  });
}

for (const width of [1440, 360]) for (const theme of ['light', 'dark']) {
  test(`read and navigate at ${width}px in ${theme}`, async ({ page }, info) => {
    const base = info.project.metadata.base;
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ colorScheme: theme });
    await page.goto(base + 'docs/quickstart/');
    await expect(page.getByRole('heading', { name: 'A Python model round trip', exact: true })).toBeVisible();
    const size = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, screen: innerWidth }));
    expect(size.page).toBeLessThanOrEqual(size.screen + 1);
    await page.keyboard.press('Tab');
    const skip = page.getByRole('link', { name: 'Skip to content' });
    await expect(skip).toBeFocused();
    await expect(skip).not.toHaveCSS('outline-style', 'none');
    if (width === 360) {
      const menu = page.getByRole('button', { name: 'Menu', exact: true });
      await menu.focus();
      await page.keyboard.press('Enter');
      await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
      await expect(menu).toHaveAttribute('aria-expanded', 'true');
    }
    await page.screenshot({ path: fileURLToPath(new URL(`../../.dev/site-browser/${info.project.name}-${width}-${theme}.png`, import.meta.url)), fullPage: true });
  });
}

test('search finds the checked API guide and excludes development artifacts', async ({ page }, info) => {
  const base = info.project.metadata.base;
  await page.goto(base);
  const search = page.getByRole('searchbox', { name: 'Search the site' });
  await page.keyboard.press('/');
  await expect(search).toBeFocused();
  await search.fill('SourceDocument');
  await expect(page.locator('.search-results a').first()).toBeVisible();
  const hrefs = await page.locator('.search-results a').evaluateAll(nodes => nodes.map(n => n.getAttribute('href')));
  expect(hrefs.every(href => href.startsWith(base + 'docs/'))).toBe(true);
  expect(hrefs.some(href => href.includes('python-compiler') || href.includes('api-reference'))).toBe(true);
  await search.fill('Privatetemplatetoken');
  await expect(page.locator('.search-empty')).toHaveText('No results');
  const index = await (await page.request.get(base + 'search-index.json')).text();
  expect(index).not.toMatch(/docs\/templates|docs\/superpowers|openspec\/changes/);
});

test('copy preserves canonical code, and the example archive is downloadable', async ({ page, context }, info) => {
  const base = info.project.metadata.base;
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(base + 'docs/quickstart/');
  const source = await page.locator('pre code').first().textContent();
  const copy = page.getByRole('button', { name: 'Copy code', exact: true }).first();
  await copy.focus();
  await page.keyboard.press('Enter');
  await expect(copy).toHaveAttribute('data-state', 'copied');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(source.trimEnd());
  const download = await page.request.get(base + 'assets/downloads/examples.zip');
  expect(download.ok()).toBe(true);
  expect((await download.body()).subarray(0, 2).toString()).toBe('PK');
});
