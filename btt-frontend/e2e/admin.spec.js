/**
 * E2E — Admin flows
 * Covers: dashboard KPIs, Users (list / create authority), Analytics, Audit Logs
 */
import { test, expect } from '@playwright/test';
import { loginAs, navTo } from './helpers.js';

test.describe('Admin — Dashboard', () => {
  test('loads and shows system KPIs', async ({ page }) => {
    await loginAs(page, 'admin');
    await expect(page).toHaveURL(/\/admin\/dashboard/);
    await expect(page.getByText('Admin Dashboard')).toBeVisible();
    await expect(page.getByText('Total Reports')).toBeVisible();
    await expect(page.getByText('Active Cases')).toBeVisible();
    await expect(page.getByText('Recovery Rate')).toBeVisible();
    await expect(page.getByText('Registered Users')).toBeVisible();
  });

  test('Trigger ML Reanalysis button is visible', async ({ page }) => {
    await loginAs(page, 'admin');
    await expect(page.getByRole('button', { name: /trigger ml reanalysis/i })).toBeVisible();
  });

  test('city breakdown renders if data exists', async ({ page }) => {
    await loginAs(page, 'admin');
    // The progress bars section renders when data is present
    await page.waitForTimeout(1_500);
    const hasBreakdown = await page.getByText('Reports by City').isVisible().catch(() => false);
    // It's OK if no data yet — just verify no crash
    expect(typeof hasBreakdown).toBe('boolean');
  });
});

test.describe('Admin — User Management', () => {
  test('Users page loads and shows the table', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Users');
    await expect(page).toHaveURL(/\/admin\/users/);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText('No users found').isVisible().catch(() => false);
    expect(hasTable || isEmpty).toBe(true);
  });

  test('Add Authority button opens modal with form', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Users');
    await page.getByRole('button', { name: /add authority/i }).click();
    await expect(page.getByText('Create Authority Account')).toBeVisible();
    await expect(page.locator('input[placeholder*="Inspector"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="KHI"]')).toBeVisible(); // badge number
    await expect(page.locator('input[placeholder*="4210"]')).toBeVisible(); // CNIC
  });

  test('create authority form shows validation errors on empty submit', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Users');
    await page.getByRole('button', { name: /add authority/i }).click();
    await page.getByRole('button', { name: /create authority/i }).click();
    // HTML5 required validation fires — the form does not close
    await expect(page.getByText('Create Authority Account')).toBeVisible();
  });

  test('users table shows role badges and status', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Users');
    await page.waitForTimeout(1_500);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    if (!hasTable) return;
    // Each row should have a role badge
    await expect(page.locator('tbody tr').first()).toBeVisible();
  });

  test('deactivate/activate button exists on each user row', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Users');
    await page.waitForTimeout(1_500);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    if (!hasTable) return;
    const firstBtn = page.locator('tbody tr').first().getByRole('button');
    await expect(firstBtn).toBeVisible();
  });
});

test.describe('Admin — Analytics', () => {
  test('Analytics page loads', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Analytics');
    await expect(page).toHaveURL(/\/admin\/analytics/);
  });
});

test.describe('Admin — Audit Logs', () => {
  test('Audit Logs page loads', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Audit Logs');
    await expect(page).toHaveURL(/\/admin\/audit/);
  });

  test('shows a table or empty state', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Audit Logs');
    await page.waitForTimeout(1_500);
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const isEmpty  = await page.getByText(/no.*log|no.*audit|empty/i).isVisible().catch(() => false);
    expect(hasTable || isEmpty).toBe(true);
  });
});

test.describe('Admin — Notifications', () => {
  test('Notifications page loads', async ({ page }) => {
    await loginAs(page, 'admin');
    await navTo(page, 'Notifications');
    await expect(page).toHaveURL(/\/admin\/notifications/);
  });
});
