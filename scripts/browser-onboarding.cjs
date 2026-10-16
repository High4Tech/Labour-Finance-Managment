/* Read-only onboarding QA in native Desk. Uses local credentials from the
 * environment; only browser preferences are changed, never business documents. */
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
    assert(site.endsWith('.localhost'), 'Onboarding QA requires a local development site');
    const base = `http://${site}:${settings.FRAPPE_PORT || 8000}`;
    const browser = await chromium.launch({headless: true,
        ...(process.env.PP_BROWSER_CHANNEL ? {channel: process.env.PP_BROWSER_CHANNEL} : {})});
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    page.setDefaultTimeout(30000);
    const failures = [];
    page.on('pageerror', error => failures.push(error.message));
    page.on('response', response => { if (response.status() >= 400) failures.push(`HTTP ${response.status()}: ${response.url()}`); });
    const out = path.join(root, '.local', 'qa'); fs.mkdirSync(out, {recursive: true});
    const go = route => page.goto(base + route, {waitUntil: 'domcontentloaded'});
    const popover = page.locator('#driver-popover-item');
    try {
        const login = await page.request.post(base + '/api/method/login', {data: {
            usr: process.env.PP_BROWSER_USER || 'Administrator',
            pwd: process.env.PP_BROWSER_PASSWORD || settings.PP_ADMIN_PASSWORD,
        }});
        assert(login.ok() && (await login.json()).message === 'Logged In', 'Login failed');
        if (site === 'platform.localhost') {
            await go('/desk');
            await page.locator('.desktop-container .icon-title').getByText('High4Tech admin', {exact: true}).click();
            await page.locator('.pp-context-bar:visible').getByText(/Manage subscriber organizations/).waitFor();
            assert.equal(await page.getByRole('link', {name: 'Platform home', exact: true}).getAttribute('href'), '/desk/high4tech');
            assert.equal(await page.locator('.pp-welcome').count(), 0);
            await page.getByRole('button', {name: 'How it works', exact: true}).click();
            await page.getByRole('dialog').getByText('High4Tech admin', {exact: true}).waitFor();
            await page.getByRole('button', {name: 'Got it', exact: true}).click();
            await page.screenshot({path: path.join(out, 'onboarding-platform.png')});
            const tenants = await page.request.get(base + '/api/resource/PP%20Tenant?limit_page_length=1');
            const records = (await tenants.json()).data;
            assert(records?.length, 'Seed a local platform tenant before running field-help QA');
            await go('/desk/pp-tenant/' + encodeURIComponent(records[0].name));
            await page.getByRole('button', {name: 'Help: Customer Organization', exact: true}).click();
            await page.getByRole('tooltip').getByText(/The subscriber using PLUS POINT/).waitFor();
            assert.equal(await page.getByRole('link', {name: 'Platform home', exact: true}).getAttribute('href'), '/desk/high4tech');
            await page.keyboard.press('Escape');
            console.log('PASS platform guidance uses its own platform home; tenant quick start is absent');
        } else {
            await go('/desk/plus-point');
            await page.locator('.pp-welcome').waitFor();
            assert.equal(await page.locator('.pp-welcome .pp-workflow-step').count(), 6);
            await page.getByRole('button', {name: 'Show me around', exact: true}).click();
            await popover.getByText('Set up the client and job', {exact: true}).waitFor();
            await page.screenshot({path: path.join(out, 'onboarding-tour.png')});
            await popover.getByRole('button', {name: 'Next', exact: true}).click();
            await popover.getByText('Agree how the client will be billed', {exact: true}).waitFor();
            await popover.getByRole('button', {name: 'Back', exact: true}).click();
            await popover.getByText('Set up the client and job', {exact: true}).waitFor();
            await page.keyboard.press('Escape');
            await popover.waitFor({state: 'hidden'});
            await page.getByRole('button', {name: 'How it works', exact: true}).click();
            const dialog = page.getByRole('dialog');
            await dialog.getByText('Which app should I use?', {exact: true}).waitFor();
            await dialog.getByText('High4Tech admin', {exact: true}).waitFor();
            await page.screenshot({path: path.join(out, 'onboarding-app-guide.png')});
            await dialog.getByRole('button', {name: 'Got it', exact: true}).click();
            await page.locator('.pp-quick-start > summary').click();
            await page.waitForFunction(() => !document.querySelector('.pp-quick-start').open);
            await page.reload({waitUntil: 'domcontentloaded'});
            await page.locator('.pp-welcome').waitFor();
            assert.equal(await page.locator('.pp-quick-start').evaluate(element => element.open), false);
            await page.getByRole('button', {name: 'Show me around', exact: true}).click();
            await popover.getByText('Set up the client and job', {exact: true}).waitFor();
            for (let step = 1; step < 6; step++) await popover.getByRole('button', {name: 'Next', exact: true}).click();
            await popover.getByText('Pay workers and review the project', {exact: true}).waitFor();
            await popover.getByRole('button', {name: 'Finish', exact: true}).click();
            await popover.waitFor({state: 'hidden'});
            console.log('PASS six-step tour, Next/Back/Escape/Finish, app explanations and remembered quick-start preference');

            const assignments = await page.request.get(base + '/api/resource/PP%20Assignment?limit_page_length=1');
            const records = (await assignments.json()).data;
            assert(records?.length, 'Seed a local demo allocation before running field-help QA');
            await go('/desk/pp-assignment/' + encodeURIComponent(records[0].name));
            const wageHelp = page.getByRole('button', {name: 'Help: Daily Worker Wage', exact: true});
            await wageHelp.waitFor();
            await wageHelp.click();
            await page.getByRole('tooltip').getByText(/Amount the worker earns/).waitFor();
            await page.keyboard.press('Escape');
            await page.getByRole('tooltip').waitFor({state: 'hidden'});
            await page.getByRole('button', {name: 'Explain this screen', exact: true}).focus();
            await wageHelp.focus();
            await page.getByRole('tooltip').getByText(/Amount the worker earns/).waitFor();
            await page.waitForFunction(() => {
                const tooltip = document.querySelector('.pp-tooltip.show');
                return tooltip && Number(getComputedStyle(tooltip).opacity) >= 0.85;
            });
            await page.screenshot({path: path.join(out, 'onboarding-wage-tip.png'), fullPage: true});
            await page.keyboard.press('Escape');
            await page.getByRole('button', {name: 'Explain this screen', exact: true}).click();
            await page.getByRole('dialog').getByRole('button', {name: 'Show field tips', exact: true}).click();
            await popover.getByText('Worker', {exact: true}).waitFor();
            await page.keyboard.press('Escape');
            await popover.waitFor({state: 'hidden'});
            console.log('PASS field tooltip by keyboard and click, Escape dismissal and native field tour');

            await go('/desk/manufacturing');
            await page.locator('.pp-context-bar').getByText(/optional ERPNext module/).waitFor();
            await page.getByRole('link', {name: 'Workforce home', exact: true}).click();
            await page.locator('.pp-welcome').waitFor();
            await go('/desk');
            await page.locator('.desktop-icon .pp-app-purpose').first().waitFor();
            assert.equal(await page.locator('.pp-app-purpose').count(), 4);
            await page.screenshot({path: path.join(out, 'onboarding-apps.png'), fullPage: true});
            await page.setViewportSize({width: 390, height: 844});
            await go('/desk/plus-point');
            await page.locator('.pp-welcome').waitFor();
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Mobile guidance overflows the viewport');
            await page.screenshot({path: path.join(out, 'onboarding-mobile.png'), fullPage: true});
            await page.getByRole('button', {name: 'Show me around', exact: true}).click();
            await popover.getByText('Set up the client and job', {exact: true}).waitFor();
            const box = await popover.boundingBox();
            assert(box.x >= 0 && box.x + box.width <= 391, 'Mobile tour popover overflows the viewport');
            await page.keyboard.press('Escape');
            await popover.waitFor({state: 'hidden'});
            console.log('PASS optional-module way back, four app descriptions and 390px mobile layout');
        }
        assert.deepEqual(failures, [], 'Onboarding produced browser/server errors');
        console.log('PASS onboarding: zero JavaScript or HTTP errors; no business records changed');
    } catch (error) {
        await page.screenshot({path: path.join(out, 'onboarding-failure.png'), fullPage: true});
        console.error('Browser failures:', failures);
        console.error('Page:', (await page.locator('body').innerText()).slice(-2500));
        throw error;
    } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
