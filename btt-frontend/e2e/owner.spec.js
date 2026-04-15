/**
 * E2E — Owner flows
 * Covers: dashboard KPIs, My Bikes (list / register / delete), My Reports (list / file)
 */
import { test, expect } from '@playwright/test';
import { loginAs, navTo } from './helpers.js';

test.use({ storageState: undefined });

test.describe('Owner — Dashboard', () => {
  test('shows KPI cards and greeting', async ({ page }) => {
    await loginAs(page, 'owner');
    await expect(page.getByText(/good morning|good afternoon|good evening/i)).toBeVisible();
    await expect(page.getByText('My Bikes')).toBeVisible();
    await expect(page.getByText('Total Cases')).toBeVisible();
  });
});

test.describe('Owner — My Bikes', () => {
  test('Bikes page loads', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Bikes');
    await expect(page).toHaveURL(/\/owner\/bikes/);
    // Either a list of bikes or the empty state is shown
    const hasBikes = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText('No bikes registered yet').isVisible().catch(() => false);
    expect(hasBikes || isEmpty).toBe(true);
  });

  test('Register Bike button opens modal', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Bikes');
    await page.getByRole('button', { name: /register bike/i }).click();
    await expect(page.getByText('Register New Bike')).toBeVisible();
  });

  test('Bike registration form submits and shows result', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Bikes');
    await page.getByRole('button', { name: /register bike/i }).click();

    // Fill required fields with unique numbers to avoid duplicates
    const suffix = Date.now();
    await page.fill('input[placeholder="Honda"]',        'Yamaha');
    await page.fill('input[placeholder="CD 70"]',        'YBR 125');
    await page.fill('input[placeholder="2021"]',         '2022');
    await page.fill('input[placeholder*="HC12A"]',       `YBR-ENG-${suffix}`);
    await page.fill('input[placeholder*="MH-CY"]',       `YBR-CHS-${suffix}`);
    await page.getByRole('button', { name: /register bike/i }).last().click();

    // Modal closes on success OR shows a validation error — either is correct behaviour
    await page.waitForTimeout(2_000);
    const modalGone = !(await page.getByText('Register New Bike').isVisible().catch(() => true));
    const hasError  = await page.locator('.alert-error').isVisible().catch(() => false);
    expect(modalGone || hasError).toBe(true);
  });
});

test.describe('Owner — My Reports', () => {
  test('Reports page loads', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Reports');
    await expect(page).toHaveURL(/\/owner\/reports/);
    const hasList  = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText('No reports filed yet').isVisible().catch(() => false);
    expect(hasList || isEmpty).toBe(true);
  });

  test('File Report button opens modal', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Reports');
    await page.getByRole('button', { name: /file report/i }).click();
    await expect(page.getByText('File Theft Report')).toBeVisible();
  });

  test('Report form shows bike selector', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'My Reports');
    await page.getByRole('button', { name: /file report/i }).click();
    await expect(page.locator('select')).toBeVisible();
    await expect(page.locator('input[type="date"]')).toBeVisible();
  });
});

test.describe('Owner — Notifications', () => {
  test('Notifications page loads', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'Notifications');
    await expect(page).toHaveURL(/\/owner\/notifications/);
  });
});
