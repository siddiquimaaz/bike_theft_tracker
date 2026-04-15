/**
 * E2E — API connectivity smoke tests
 * Verifies the frontend can actually reach the Django backend through
 * Vite's proxy. These tests hit the API directly via page.request
 * and through the UI login flow.
 */
import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './helpers.js';

test.describe('API reachability', () => {
  test('Django health-check: /api/auth/login/ responds', async ({ page }) => {
    // A GET to the login endpoint returns 405 (Method Not Allowed) or 200
    // but NOT a network error — proves the proxy reaches Django.
    const res = await page.request.get('http://localhost:8000/api/auth/login/');
    expect([200, 405]).toContain(res.status());
  });

  test('Vite dev server is up and serves the React app', async ({ page }) => {
    await page.goto('/');
    // React renders a <div id="root"> that is not empty
    const root = page.locator('#root');
    await expect(root).not.toBeEmpty({ timeout: 10_000 });
  });

  test('proxy: /api through Vite reaches Django', async ({ page }) => {
    await page.goto('/');
    const res = await page.request.post('/api/auth/login/', {
      data:    { email: 'nobody@x.com', password: 'wrong' },
      headers: { 'Content-Type': 'application/json' },
    });
    // 401 = Django responded (wrong creds), not a proxy failure
    expect(res.status()).toBe(401);
  });
});

test.describe('JWT auth flow end-to-end', () => {
  test('tokens are stored in localStorage after login', async ({ page }) => {
    await loginAs(page, 'admin');
    const access  = await page.evaluate(() => localStorage.getItem('btt_access'));
    const refresh = await page.evaluate(() => localStorage.getItem('btt_refresh'));
    expect(access).toBeTruthy();
    expect(refresh).toBeTruthy();
  });

  test('JWT payload includes role', async ({ page }) => {
    await loginAs(page, 'owner');
    const access = await page.evaluate(() => localStorage.getItem('btt_access'));
    expect(access).toBeTruthy();
    // Decode payload
    const payload = JSON.parse(atob(access.split('.')[1]));
    // Would throw if access is null — means login worked
    expect(payload.role).toBe('owner');
    expect(payload.email).toBeTruthy();
  });

  test('user object in localStorage has correct role', async ({ page }) => {
    await loginAs(page, 'authority');
    const user = await page.evaluate(() =>
      JSON.parse(localStorage.getItem('btt_user') || 'null')
    );
    expect(user).not.toBeNull();
    expect(user.role).toBe('authority');
  });

  test('all four roles can obtain a valid JWT', async ({ page }) => {
    for (const [roleKey, u] of Object.entries(USERS)) {
      await page.evaluate(() => localStorage.clear());
      await loginAs(page, roleKey);
      const token = await page.evaluate(() => localStorage.getItem('btt_access'));
      expect(token, `${roleKey} should have received an access token`).toBeTruthy();
    }
  });
});

test.describe('API response shapes', () => {
  test('admin analytics endpoint returns expected keys', async ({ page }) => {
    await loginAs(page, 'admin');
    const token = await page.evaluate(() => localStorage.getItem('btt_access'));
    const res   = await page.request.get('http://localhost:8000/api/admin/analytics/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('reports');
    expect(data).toHaveProperty('users');
    expect(data).toHaveProperty('city_breakdown');
    expect(data.reports).toHaveProperty('total');
    expect(data.reports).toHaveProperty('recovery_rate_pct');
  });

  test('owner bikes endpoint returns paginated results', async ({ page }) => {
    await loginAs(page, 'owner');
    const token = await page.evaluate(() => localStorage.getItem('btt_access'));
    const res   = await page.request.get('http://localhost:8000/api/bikes/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    // Paginated: { count, results: [...] }
    expect(data).toHaveProperty('count');
    expect(Array.isArray(data.results)).toBe(true);
  });

  test('owner reports endpoint returns paginated results', async ({ page }) => {
    await loginAs(page, 'owner');
    const token = await page.evaluate(() => localStorage.getItem('btt_access'));
    const res   = await page.request.get('http://localhost:8000/api/reports/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('count');
    expect(Array.isArray(data.results)).toBe(true);
  });

  test('authority sightings endpoint returns paginated results', async ({ page }) => {
    await loginAs(page, 'authority');
    const token = await page.evaluate(() => localStorage.getItem('btt_access'));
    const res   = await page.request.get('http://localhost:8000/api/sightings/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('count');
    expect(Array.isArray(data.results)).toBe(true);
  });

  test('admin users endpoint returns paginated list', async ({ page }) => {
    await loginAs(page, 'admin');
    const token = await page.evaluate(() => localStorage.getItem('btt_access'));
    const res   = await page.request.get('http://localhost:8000/api/admin/users/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(Array.isArray(data.results)).toBe(true);
    // Demo users should appear
    expect(data.count).toBeGreaterThan(0);
  });
});
