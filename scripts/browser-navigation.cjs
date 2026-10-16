/* Native app switching regression. Run against a local tenant, optionally with
 * PP_BROWSER_USER / PP_BROWSER_PASSWORD for a non-Administrator account.
 * PP_BROWSER_EMPLOYEE_APP=1 additionally checks linked employee self-service.
 */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const settings = Object.fromEntries(fs.readFileSync(path.join(root, '.env'), 'utf8')
    .split(/\r?\n/).filter(line => line.includes('=') && !line.startsWith('#'))
    .map(line => { const i = line.indexOf('='); return [line.slice(0, i), line.slice(i + 1)]; }));
  const site = process.env.PP_BROWSER_SITE || settings.LOCAL_SITE || 'demo.localhost';
  assert(site.endsWith('.localhost'), 'Browser regression requires a local development tenant');
  const base = `http://${site}:${settings.FRAPPE_PORT || 8000}`;
  const browser = await chromium.launch({ headless: true,
    ...(process.env.PP_BROWSER_CHANNEL ? { channel: process.env.PP_BROWSER_CHANNEL } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(30000);
  const failures = [];
  page.on('pageerror', error => failures.push(`JavaScript: ${error.message}`));
  page.on('response', response => {
    if (response.status() >= 400) failures.push(`HTTP ${response.status()}: ${response.url()}`);
  });
  const out = path.join(root, '.local', 'qa');
  fs.mkdirSync(out, { recursive: true });
  const desktopIcon = title => page.locator('.desktop-container .icon-title').getByText(title, { exact: true });
  const allApps = async () => {
    await page.locator('.body-sidebar .sidebar-header').click();
    const appsMenu = page.getByText('Apps', { exact: true }).last();
    if (await appsMenu.isVisible()) await appsMenu.hover();
    await page.getByText('All apps', { exact: true }).last().click();
    await desktopIcon('PLUS POINT').waitFor({ state: 'visible' });
    assert(!page.url().includes('setup-wizard'), 'All apps returned to the setup wizard');
  };
  try {
    const login = await page.request.post(base + '/api/method/login', { data: {
      usr: process.env.PP_BROWSER_USER || 'Administrator',
      pwd: process.env.PP_BROWSER_PASSWORD || settings.PP_ADMIN_PASSWORD,
    } });
    assert(login.ok() && (await login.json()).message === 'Logged In', 'Local login failed');
    await page.goto(base + '/desk', { waitUntil: 'domcontentloaded' });
    await desktopIcon('PLUS POINT').waitFor({ state: 'visible' });
    assert.equal(await page.evaluate(() => frappe.boot.home_page), 'desktop');
    assert.equal(await page.evaluate(() => frappe.boot.apps_data.is_desk_apps), 1);
    await desktopIcon('PLUS POINT').click();
    await page.getByText('Workforce overview', { exact: true }).waitFor();
    await allApps();
    await desktopIcon('Frappe HR').click();
    await page.getByText('Department Wise Employee Count', { exact: true }).waitFor();
    await allApps();
    await desktopIcon('Framework').click();
    await page.locator('.header-title').getByText('Build', { exact: true }).waitFor();
    await page.goto(base + '/desk/setup/home', { waitUntil: 'domcontentloaded' });
    await page.getByText('Annual Purchase', { exact: true }).waitFor();
    await page.waitForFunction(() => !document.body.innerText.includes('Loading...'));
    await page.goto(base + '/desk/user', { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: 'Add User', exact: true }).waitFor();
    await page.screenshot({ path: path.join(out, 'navigation-users.png'), fullPage: true });
    await allApps();
    await desktopIcon('PLUS POINT').click();
    await page.getByText('Workforce overview', { exact: true }).waitFor();
    await page.screenshot({ path: path.join(out, 'navigation-return.png'), fullPage: true });
    if (process.env.PP_BROWSER_EMPLOYEE_APP === '1') {
      await page.goto(base + '/hrms', { waitUntil: 'domcontentloaded' });
      await page.waitForURL('**/hrms/home');
      await page.getByText('Login Failed', { exact: true }).waitFor({ state: 'hidden' });
      await page.getByText('Attendance', { exact: true }).first().waitFor();
      await page.screenshot({ path: path.join(out, 'navigation-employee.png'), fullPage: true });
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await page.getByText('Workforce overview', { exact: true }).waitFor();
      console.log('PASS linked employee self-service and browser Back to PLUS POINT');
    }
    assert.deepEqual(failures, [], 'App switching produced browser/server errors');
    console.log('PASS All apps → PLUS POINT → HR → Framework → Home dashboard → Users → PLUS POINT; zero browser/server errors');
  } catch (error) {
    await page.screenshot({ path: path.join(out, 'navigation-failure.png'), fullPage: true });
    console.error('Navigation failures:', failures);
    console.error('Visible page:', (await page.locator('body').innerText()).slice(-2500));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
