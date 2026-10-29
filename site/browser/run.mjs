import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
for (const args of [
  ['scripts/site_tool.py', 'build'],
  ['scripts/site_tool.py', 'build', '--base', '/', '--out', '.dev/site-root'],
]) {
  const result = spawnSync('python3', args, { cwd: root, stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
const result = spawnSync(process.execPath, ['node_modules/@playwright/test/cli.js', 'test'], { stdio: 'inherit' });
process.exit(result.status ?? 1);
