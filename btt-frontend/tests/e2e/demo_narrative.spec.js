/**
 * E2E — Full demo narrative (six cross-role events).
 *
 * Mirrors the backend integration test:
 *   tests/test_inter_role_sync.py::TestEndToEndDemoNarrative
 *     ::test_full_demo_scenario_runs_end_to_end
 *
 * The six events covered in order:
 *   1. Owner reports a stolen bike.
 *   2. Community user submits a sighting (high confidence; photo).
 *   3. Owner receives the handshake prompt and responds "Yes".
 *   4. Authority receives the URGENT escalation and moves the case to
 *      bike_located → records a recovery.
 *   5. Authority marks the case recovered; Owner sees the pickup request.
 *   6. Owner confirms pickup; case closes; community contributors are
 *      thanked via a closure broadcast.
 *
 * Prerequisites:
 *   • PostgreSQL running on the configured port
 *   • Backend API live at http://localhost:8000
 *   • Frontend dev server live at http://localhost:3000
 *   • Demo accounts seeded:    python manage.py create_demo_users
 *
 * Run with:
 *   npx playwright test tests/e2e/demo_narrative.spec.js
 *
 * NOTE: This is an opt-in long flow — it touches every role and is
 * therefore slow. Designed to validate the demo story end-to-end before
 * a presentation, not to run on every commit.
 */
import { test, expect } from '@playwright/test';
import { loginAs, logout, navTo } from '../../e2e/helpers.js';

test.use({ storageState: undefined });
test.setTimeout(180_000);                  // long, multi-step flow

// Shared between the six events so we can refer to the bike/report we
// just created instead of guessing from the page DOM.
const ctx = {
  bikeSuffix: Date.now().toString().slice(-8),
  caseRefVisibleText: null,
};

test.describe.serial('Demo narrative — full six-event cross-role flow', () => {

  // ── Event 1 ─────────────────────────────────────────────────────────────
  test('1. Owner reports a stolen bike', async ({ page }) => {
    await loginAs(page, 'owner');

    // Register the bike that will be stolen — unique numbers per run.
    await navTo(page, 'My Bikes');
    await page.getByRole('button', { name: /register bike/i }).click();
    await page.fill('input[placeholder="Honda"]',  'Honda');
    await page.fill('input[placeholder="CD 70"]',  'CG 125');
    await page.fill('input[placeholder="2021"]',   '2023');
    await page.fill('input[placeholder*="HC12A"]', `DEMO-ENG-${ctx.bikeSuffix}`);
    await page.fill('input[placeholder*="MH-CY"]', `DEMO-CHS-${ctx.bikeSuffix}`);
    await page.getByRole('button', { name: /register bike/i }).last().click();
    await page.waitForTimeout(1500);

    // File the theft report against that bike.
    await navTo(page, 'My Reports');
    await page.getByRole('button', { name: /file report/i }).click();
    await expect(page.getByText('File Theft Report')).toBeVisible();
    // The bike <select> defaults to the most recent bike — fine for the demo.
    await page.locator('input[type="date"]').first().fill(new Date().toISOString().slice(0, 10));
    const cityInput = page.locator('input').filter({ hasText: '' }).first();
    await page.fill('input[placeholder*="Karachi"], input[placeholder*="city" i]', 'Karachi').catch(() => {});
    await page.getByRole('button', { name: /file report|submit/i }).last().click();
    await page.waitForTimeout(2000);

    // Page now lists at least one report — capture its reference number.
    const refCell = await page.locator('td').filter({ hasText: /BTT-\d{4}/ }).first().textContent();
    expect(refCell).toMatch(/BTT-\d+/);
    ctx.caseRefVisibleText = refCell.trim();
    await logout(page);
  });

  // ── Event 2 ─────────────────────────────────────────────────────────────
  test('2. Community user submits a high-confidence sighting', async ({ page }) => {
    await loginAs(page, 'community');
    await navTo(page, 'Submit Sighting');

    // Use the engine number from event 1 so fuzzy match scores HIGH.
    await page.fill('input[placeholder*="engine" i]',  `DEMO-ENG-${ctx.bikeSuffix}`);
    await page.fill('input[placeholder*="chassis" i]', `DEMO-CHS-${ctx.bikeSuffix}`);
    await page.fill('input[placeholder*="city" i]',    'Karachi');
    await page.locator('input[type="date"]').first().fill(new Date().toISOString().slice(0, 10));

    // Optional photo — the file input is hidden; skip if not present.
    const photoInput = page.locator('input[type="file"]');
    if (await photoInput.count()) {
      // Upload a 1-byte placeholder so confidence is still flagged "with-photo"
      await photoInput.setInputFiles({
        name: 'evidence.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from([0xff, 0xd8, 0xff, 0xd9]),
      });
    }

    await page.getByRole('button', { name: /submit sighting|submit/i }).click();
    await page.waitForTimeout(2000);
    // The community dashboard should now show this sighting in the list.
    await navTo(page, 'My Sightings');
    await expect(page.getByText(/karachi/i).first()).toBeVisible();
    await logout(page);
  });

  // ── Event 3 ─────────────────────────────────────────────────────────────
  test('3. Owner receives handshake and responds Yes', async ({ page }) => {
    await loginAs(page, 'owner');
    await navTo(page, 'Notifications');

    // The handshake notification is rendered with a "Yes / No / Not sure"
    // affordance. Wait for it to appear (notifications fan out via daemon
    // threads — give them a moment).
    const handshakeRow = page.getByText(/is this your.*honda|may match your/i).first();
    await expect(handshakeRow).toBeVisible({ timeout: 10_000 });

    // Click "Yes" on the row.
    await page.getByRole('button', { name: /^yes$/i }).first().click();
    await page.waitForTimeout(1500);
    // Owner sees the receipt confirmation toast/badge.
    await expect(
      page.getByText(/thanks.*authorities|escalated|will investigate/i).first(),
    ).toBeVisible();
    await logout(page);
  });

  // ── Event 4 ─────────────────────────────────────────────────────────────
  test('4. Authority sees URGENT escalation and moves case to bike_located', async ({ page }) => {
    await loginAs(page, 'authority');
    await navTo(page, 'Notifications');

    // The URGENT notification from event 3 should be present.
    await expect(
      page.getByText(/owner confirmed sighting|urgent/i).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Open the cases queue and pick the first NEW/active case.
    await navTo(page, 'Cases');
    await page.locator('table tbody tr').first().click();

    // Use the status dropdown to advance to bike_located.
    const statusSelect = page.locator('select').first();
    await statusSelect.selectOption({ label: /bike located/i });
    await page.getByRole('button', { name: /update|save|change/i }).first().click();
    await page.waitForTimeout(1500);
    await logout(page);
  });

  // ── Event 5 ─────────────────────────────────────────────────────────────
  test('5. Authority logs recovery → Owner sees pickup request', async ({ page }) => {
    // Authority logs the recovery record.
    await loginAs(page, 'authority');
    await navTo(page, 'Cases');
    await page.locator('table tbody tr').first().click();
    await page.getByRole('button', { name: /log recovery|record recovery/i }).click();
    await page.locator('input[type="date"]').first().fill(new Date().toISOString().slice(0, 10));
    await page.fill('input[placeholder*="city" i]', 'Karachi').catch(() => {});
    await page.getByRole('button', { name: /save|submit|log/i }).last().click();
    await page.waitForTimeout(1500);
    await logout(page);

    // Owner now sees the recovery notification with a confirm-pickup CTA.
    await loginAs(page, 'owner');
    await navTo(page, 'Notifications');
    await expect(
      page.getByText(/recovered|confirm pickup|finalize/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    await logout(page);
  });

  // ── Event 6 ─────────────────────────────────────────────────────────────
  test('6. Owner confirms pickup → case closes → community contributors thanked', async ({ page }) => {
    // Owner confirms.
    await loginAs(page, 'owner');
    await navTo(page, 'My Reports');
    await page.locator('table tbody tr').first().click();
    await page.getByRole('button', { name: /confirm pickup|confirm recovery/i }).click();
    await page.waitForTimeout(2000);
    // Case should now show as Closed.
    await expect(page.getByText(/closed/i).first()).toBeVisible();
    await logout(page);

    // Community contributor receives the closure broadcast.
    await loginAs(page, 'community');
    await navTo(page, 'Notifications');
    await expect(
      page.getByText(/resolved|recovered.*thanks|community/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
