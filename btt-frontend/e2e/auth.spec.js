/**
 * E2E — Authentication flows
 * Covers: login (all roles), failed login, logout, page links
 */
import { test, expect } from '@playwright/test';
import { loginAs, logout, USERS } from './helpers.js';

test.describe('Login page', () => {
  test('shows the BTT branding and demo panel', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Bike Theft Tracker');
    await expect(page.getByText('Demo accounts')).toBeVisible();
  });

  test('shows links to Register and Forgot Password', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('link', { name: /register/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /forgot password/i })).toBeVisible();
  });

  test('shows error on wrong credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]',    'nobody@example.com');
    await page.fill('input[type="password"]', 'wrongpass');
    await page.click('button[type="submit"]');
    // DRF returns 401 — AuthContext surfaces the error message
    await expect(page.locator('.alert-error, [class*="alert"]')).toBeVisible({ timeout: 8_000 });
  });

  for (const [roleKey, u] of Object.entries(USERS)) {
    test(`${roleKey} can log in and reaches their dashboard`, async ({ page }) => {
      await loginAs(page, roleKey);
      await expect(page).toHaveURL(new RegExp(u.home));
      // Sidebar contains their role label
      await expect(page.locator('aside')).toBeVisible();
    });
  }
});

test.describe('Logout', () => {
  test('clears session and redirects to login', async ({ page }) => {
    await loginAs(page, 'owner');
    // Click the Sign Out button in the sidebar
    await page.locator('aside').getByText('Sign Out').click();
    await page.waitForURL('**/login', { timeout: 8_000 });
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Register page', () => {
  test('loads and shows the registration form', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByText(/create.*account|register/i)).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
  });
});

test.describe('Forgot password page', () => {
  test('loads and shows the email input', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });
});

test.describe('Protected routes redirect', () => {
  test('unauthenticated visit to /owner/dashboard goes to /login', async ({ page }) => {
    await logout(page);
    await page.goto('/owner/dashboard');
    await page.waitForURL('**/login', { timeout: 8_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('wrong role visiting /admin/dashboard gets unauthorized page', async ({ page }) => {
    await loginAs(page, 'owner');
    await page.goto('/admin/dashboard');
    await expect(page).toHaveURL(/unauthorized|admin\/dashboard/);
  });
});
