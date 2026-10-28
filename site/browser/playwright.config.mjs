import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.mjs',
  outputDir: '../../.dev/site-browser/test-results',
  reporter: [['list'], ['json', { outputFile: '../../.dev/site-browser/results.json' }]],
  workers: 2,
  forbidOnly: !!process.env.CI,
  retries: 0,
  use: { browserName: 'chromium', trace: 'retain-on-failure' },
  projects: [
    { name: 'pages', use: { baseURL: 'http://127.0.0.1:4173' }, metadata: { base: '/morphir-python/' } },
    { name: 'root', use: { baseURL: 'http://127.0.0.1:4174' }, metadata: { base: '/' } },
  ],
  webServer: [
    { command: 'python3 scripts/site_tool.py serve', cwd: root, url: 'http://127.0.0.1:4173/morphir-python/', reuseExistingServer: false },
    { command: 'python3 scripts/site_tool.py serve --base / --out .dev/site-root --port 4174', cwd: root, url: 'http://127.0.0.1:4174/', reuseExistingServer: false },
  ],
});
