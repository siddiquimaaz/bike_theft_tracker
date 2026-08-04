/**
 * Runs before Playwright starts dev servers: apply migrations and ensure demo users exist.
 * Requires PostgreSQL + PostGIS reachable per btt-backend/.env (see docs for PostGIS install).
 *
 * Override Python: set BTT_PYTHON to an absolute path (e.g. another venv's python.exe).
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function resolveRepoRoot() {
  return path.resolve(__dirname, '..');
}

function resolvePython(repoRoot) {
  const fromEnv = process.env.BTT_PYTHON?.trim();
  if (fromEnv && fs.existsSync(fromEnv)) {
    return fromEnv;
  }
  const win = process.platform === 'win32';
  const rel = win ? ['venv', 'Scripts', 'python.exe'] : ['venv', 'bin', 'python'];
  const venvPy = path.join(repoRoot, ...rel);
  if (fs.existsSync(venvPy)) {
    return venvPy;
  }
  return null;
}

export default async function globalSetup() {
  const repoRoot = resolveRepoRoot();
  const py = resolvePython(repoRoot);
  if (!py) {
    console.error(
      '[playwright globalSetup] No repo venv Python found. Run scripts\\install_all.ps1 (creates .\\venv) ' +
        'or set BTT_PYTHON to your python.exe.',
    );
    process.exit(1);
  }

  const backendDir = path.join(repoRoot, 'btt-backend');
  const run = (args) => {
    const r = spawnSync(py, args, {
      cwd: backendDir,
      stdio: 'inherit',
      env: { ...process.env },
    });
    if (r.error) {
      throw r.error;
    }
    if (r.status !== 0) {
      throw new Error(`[playwright globalSetup] Command failed (${r.status}): ${args.join(' ')}`);
    }
  };

  console.log('[playwright globalSetup] Using Python:', py);
  run(['manage.py', 'migrate', '--noinput']);
  run(['manage.py', 'create_demo_users']);
}
