/**
 * E2E — Community flows
 * Covers: dashboard, Submit Sighting (form validation + successful submit)
 */
import { test, expect } from '@playwright/test';
import { loginAs, navTo } from './helpers.js';

test.describe('Community — Dashboard', () => {
  test('loads and shows welcome content', async ({ page }) => {
    await loginAs(page, 'community');
    await expect(page).toHaveURL(/\/community\/dashboard/);
    await expect(page.locator('aside')).toBeVisible();
  });
});

test.describe('Community — Submit Sighting', () => {
  test('Submit Sighting page loads with the form', async ({ page }) => {
    await loginAs(page, 'community');
    await navTo(page, 'Submit Sighting');
    await expect(page).toHaveURL(/\/community\/sightings/);
    await expect(page.getByText('Submit a Sighting')).toBeVisible();
    await expect(page.locator('input[placeholder*="HC12A"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="MH-CY"]')).toBeVisible();
  });

  test('shows validation error when no numbers provided', async ({ page }) => {
    await loginAs(page, 'community');
    await navTo(page, 'Submit Sighting');
    // Fill city and date but leave engine/chassis empty
    await page.fill('input[placeholder="Karachi"]', 'Lahore');
    await page.locator('input[type="date"]').fill('2024-01-15');
    await page.getByRole('button', { name: /submit sighting/i }).click();
    await expect(page.getByText(/partial engine|partial chassis|at least/i)).toBeVisible({ timeout: 5_000 });
  });

  test('submits a sighting with engine number and shows success', async ({ page }) => {
    await loginAs(page, 'community');
    await navTo(page, 'Submit Sighting');

    await page.fill('input[placeholder*="HC12A"]',  `ENG-${Date.now()}`);
    await page.fill('input[placeholder="Karachi"]',  'Lahore');
    await page.locator('input[type="date"]').fill('2024-03-10');
    await page.fill('textarea', 'Spotted near Anarkali Bazaar, heading north.');

    await page.getByRole('button', { name: /submit sighting/i }).click();

    // On success the page shows an alert-success banner
    await expect(
      page.locator('.alert-success, [class*="alert-success"]')
    ).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Community — Notifications', () => {
  test('Notifications page loads', async ({ page }) => {
    await loginAs(page, 'community');
    await navTo(page, 'Notifications');
    await expect(page).toHaveURL(/\/community\/notifications/);
  });
});
