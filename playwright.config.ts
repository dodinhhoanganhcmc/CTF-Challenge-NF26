import { defineConfig } from '@playwright/test';
import path from 'node:path';
const database = process.env.E2E_DATABASE_PATH || path.resolve(`.scratch/e2e-${Date.now()}.sqlite3`);
process.env.E2E_DATABASE_PATH = database;
export default defineConfig({
  testDir: './tests', timeout: 60000, fullyParallel: false, workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:3100', headless: true, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: [
    { command: '.venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8100', url: 'http://127.0.0.1:8100/health', reuseExistingServer: false,
      env: { DATABASE_PATH: database, APP_ORIGINS: 'http://127.0.0.1:3100' } },
    { command: 'npm run start -- --port 3100', url: 'http://127.0.0.1:3100', reuseExistingServer: false,
      env: { BACKEND_URL: 'http://127.0.0.1:8100', APP_ORIGINS: 'http://127.0.0.1:3100' } },
  ],
});
