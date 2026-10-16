/* Real browser QA; needs Playwright plus its Chromium runtime. Secrets stay in memory. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

let browser, page;
(async () => {
  const root = path.resolve(__dirname, '..');
  const settings = Object.fromEntries(fs.readFileSync(path.join(root, '.env'), 'utf8').split(/\r?\n/)
    .filter(line => line.includes('=') && !line.startsWith('#')).map(line => {
      const i = line.indexOf('='); return [line.slice(0, i), line.slice(i + 1)];
    }));
  const site = process.env.PP_BROWSER_SITE || settings.LOCAL_SITE || 'demo.localhost';
  const platform = site === 'platform.localhost';
  const base = `http://${site}:${settings.FRAPPE_PORT || 8000}`;
  browser = await chromium.launch({ headless: true, ...(process.env.PP_BROWSER_CHANNEL ? {channel: process.env.PP_BROWSER_CHANNEL} : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  page = await context.newPage();
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  const login = await context.request.post(base + '/api/method/login', {
    data: { usr: 'Administrator', pwd: settings.PP_ADMIN_PASSWORD }
  });
  if (!login.ok() || (await login.json()).message !== 'Logged In') throw new Error('Browser session login failed');
  await page.goto(base + (platform ? '/app/high4tech' : '/app/plus-point'), { waitUntil: 'domcontentloaded' });
  const out = path.join(root, '.local', 'qa');
  fs.mkdirSync(out, { recursive: true });
  await page.screenshot({ path: path.join(out, 'workspace-initial.png'), fullPage: true });
  try {
    await page.getByText(platform ? 'Platform operations' : 'Workforce operations', { exact: true }).waitFor({ timeout: 60000 });
  } catch (error) {
    await page.screenshot({ path: path.join(out, 'workspace-failure.png'), fullPage: true });
    console.log('Page URL: ' + page.url());
    console.log('Page errors: ' + JSON.stringify(failures));
    console.log('Visible page: ' + (await page.locator('body').innerText()).slice(0, 2500));
    throw error;
  }
  await page.screenshot({ path: path.join(out, platform ? 'platform.png' : 'workspace.png'), fullPage: true });
  const routes = platform ? [['pp-tenant', 'PP Tenant'], ['subscription-plan', 'Subscription Plan'], ['subscription', 'Subscription']] :
    [['pp-site', 'PP Site'], ['pp-daily-register', 'PP Daily Register'], ['pp-contract-terms', 'PP Contract Terms']];
  for (const [route, label] of routes) {
    await page.goto(base + '/app/' + route, { waitUntil: 'domcontentloaded' });
    await page.locator('.layout-main-section').waitFor({ state: 'visible', timeout: 30000 });
    await page.getByRole('button', { name: new RegExp('Add ' + label + '|New') }).first().waitFor({ timeout: 30000 });
    console.log('PASS real Desk list: ' + label);
  }
  if (!platform) {
    const response = await context.request.get(base + '/api/resource/PP%20Site?filters=' +
      encodeURIComponent(JSON.stringify({site_name: 'PLUS POINT Demo'})));
    const sites = (await response.json()).data;
    if (sites && sites.length) {
      await page.goto(base + '/app/pp-site/' + encodeURIComponent(sites[0].name));
      await page.getByRole('button', {name: 'Prepare daily attendance', exact: true}).click();
      await page.waitForFunction(() => window.cur_dialog && cur_dialog.get_field('work_date'));
      await page.evaluate(() => cur_dialog.set_value('work_date', frappe.datetime.add_days(frappe.datetime.get_today(), 1)));
      await page.locator('.modal:visible').getByText('Submit', {exact: true}).click();
      await page.waitForURL('**/pp-daily-register/**', {timeout: 30000});
      await page.waitForFunction(() => window.cur_frm && cur_frm.doc.entries && cur_frm.doc.entries.length > 0);
      const record = await page.evaluate(() => ({name: cur_frm.doc.name, docstatus: cur_frm.doc.docstatus, rows: cur_frm.doc.entries.length}));
      try {
        if (record.docstatus !== 0 || record.rows < 1) throw new Error('Attendance action did not produce a reviewable draft');
        await page.screenshot({path: path.join(out, 'daily-attendance.png'), fullPage: true});
        console.log('PASS real site attendance button creates a populated native draft register');
      } finally {
        const csrf = await page.evaluate(() => frappe.csrf_token);
        const cleanup = await context.request.delete(base + '/api/resource/PP%20Daily%20Register/' + encodeURIComponent(record.name),
          {headers: {'X-Frappe-CSRF-Token': csrf}});
        if (!cleanup.ok()) throw new Error('Temporary browser register cleanup failed');
        console.log('PASS temporary browser attendance draft removed');
      }
    }
  }
  if (failures.length) throw new Error('Browser JavaScript errors: ' + failures.join('; '));
  console.log('PASS authenticated PLUS POINT workspace and Desk navigation, zero page errors');
  await browser.close();
})().catch(async error => {
  console.error(error.message);
  if (page) {
    await page.screenshot({path: path.resolve(__dirname, '../.local/qa/browser-failure.png')});
    console.error((await page.locator('body').innerText()).slice(-2500));
  }
  if (browser) await browser.close(); process.exitCode = 1;
});
