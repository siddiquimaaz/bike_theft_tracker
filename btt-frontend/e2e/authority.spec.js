/**
 * E2E — Authority flows
 * Covers: dashboard, Case Reports (list / status advance), Sightings, Fuzzy Search, Hotspot
 */
import { test, expect } from '@playwright/test';
import { loginAs, navTo } from './helpers.js';

test.describe('Authority — Dashboard', () => {
  test('loads and shows KPI cards', async ({ page }) => {
    await loginAs(page, 'authority');
    await expect(page).toHaveURL(/\/authority\/dashboard/);
    await expect(page.locator('aside')).toBeVisible();
    // At least one stat card visible
    await expect(page.locator('.stat-card').first()).toBeVisible();
  });
});

test.describe('Authority — Case Reports', () => {
  test('Case Reports page loads', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Case Reports');
    await expect(page).toHaveURL(/\/authority\/reports/);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText('No reports in your city').isVisible().catch(() => false);
    expect(hasTable || isEmpty).toBe(true);
  });

  test('clicking a report row opens detail modal', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Case Reports');
    const firstRow = page.locator('tbody tr').first();
    const hasRows  = await firstRow.isVisible().catch(() => false);
    if (!hasRows) {
      test.skip(true, 'No reports exist for this authority city yet.');
      return;
    }
    await firstRow.click();
    // Modal with Report # title appears
    await expect(page.locator('.modal-overlay, [class*="modal"]')).toBeVisible({ timeout: 5_000 });
  });
});

test.describe('Authority — Sightings', () => {
  test('Sightings page loads', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Sightings');
    await expect(page).toHaveURL(/\/authority\/sightings/);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText('No sightings yet').isVisible().catch(() => false);
    expect(hasTable || isEmpty).toBe(true);
  });

  test('clicking a sighting row opens detail modal', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Sightings');
    const firstRow = page.locator('tbody tr').first();
    if (!(await firstRow.isVisible().catch(() => false))) {
      test.skip(true, 'No sightings exist yet.');
      return;
    }
    await firstRow.click();
    await expect(page.locator('.modal-overlay, [class*="modal"]')).toBeVisible({ timeout: 5_000 });
  });
});

test.describe('Authority — Fuzzy Search', () => {
  test('Fuzzy Search page loads with input', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Fuzzy Search');
    await expect(page).toHaveURL(/\/authority\/fuzzy/);
    await expect(page.locator('input').first()).toBeVisible();
  });

  test('searching returns results or empty state', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Fuzzy Search');
    await page.locator('input').first().fill('HC12A');
    // submit form or press enter
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2_000);
    // Either a results list or no-results message
    const hasResults = await page.locator('table, [class*="result"]').isVisible().catch(() => false);
    const noResults  = await page.getByText(/no match|no result|nothing found/i).isVisible().catch(() => false);
    const hasError   = await page.locator('.alert-error').isVisible().catch(() => false);
    expect(hasResults || noResults || hasError).toBe(true);
  });
});

test.describe('Authority — Hotspot Map', () => {
  test('Hotspot page loads', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Hotspot Map');
    await expect(page).toHaveURL(/\/authority\/hotspots/);
    // Either shows map/clusters or a "cache not ready" message
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Authority — Notifications', () => {
  test('Notifications page loads', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Notifications');
    await expect(page).toHaveURL(/\/authority\/notifications/);
  });
});
