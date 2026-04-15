/**
 * Shared helpers for all Playwright E2E specs.
 * These match the demo credentials seeded by:
 *   python manage.py create_demo_users
 */

export const USERS = {
  admin: {
    email:    'admin@demo.btt',
    password: 'DemoAdmin@2024',
    role:     'admin',
    home:     '/admin/dashboard',
  },
  authority: {
    email:    'authority.karachi@demo.btt',
    password: 'Authority@2024',
    role:     'authority',
    home:     '/authority/dashboard',
  },
  owner: {
    email:    'owner000@demo.btt',
    password: 'Owner@2024',
    role:     'owner',
    home:     '/owner/dashboard',
  },
  community: {
    email:    'community@demo.btt',
    password: 'Community@2024',
    role:     'community',
    home:     '/community/dashboard',
  },
};

/**
 * Log in via the UI and wait for the dashboard.
 * Stores auth in localStorage so subsequent page.goto() calls stay logged in.
 */
export async function loginAs(page, userKey) {
  const u = USERS[userKey];
  await page.goto('/login');
  await page.fill('input[type="email"]',    u.email);
  await page.fill('input[type="password"]', u.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`**${u.home}`, { timeout: 10_000 });
}

/** Clear localStorage so the next test starts unauthenticated. */
export async function logout(page) {
  await page.evaluate(() => localStorage.clear());
}

/** Click a sidebar nav link by its visible text. */
export async function navTo(page, label) {
  await page.locator('aside').getByText(label, { exact: false }).first().click();
}
