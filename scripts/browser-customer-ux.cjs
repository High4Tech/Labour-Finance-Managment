/* Native customer UX regression, including review-only attendance creation,
 * repeat opening of the same draft, and administrator cleanup of its fixture. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

(async () => {
    const root = path.resolve(__dirname, '..');
    const settings = Object.fromEntries(fs.readFileSync(path.join(root, '.env'), 'utf8').split(/\r?\n/)
        .filter(line => line.includes('=') && !line.startsWith('#')).map(line => {
            const i = line.indexOf('='); return [line.slice(0, i), line.slice(i + 1)];
        }));
    const site = process.env.PP_BROWSER_SITE || settings.LOCAL_SITE || 'demo.localhost';
    assert(site.endsWith('.localhost') && site !== 'platform.localhost', 'Customer UX test requires a local tenant');
    const base = `http://${site}:${settings.FRAPPE_PORT || 8000}`;
    const browser = await chromium.launch({headless: true, ...(process.env.PP_BROWSER_CHANNEL ? {channel: process.env.PP_BROWSER_CHANNEL} : {})});
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    page.setDefaultTimeout(30000);
    const failures = [];
    page.on('pageerror', error => failures.push(error.message));
    page.on('response', response => {if (response.status() >= 400) failures.push(`HTTP ${response.status()}: ${response.url()}`);});
    const out = path.join(root, '.local', 'qa'); fs.mkdirSync(out, {recursive: true});
    let cleanupName;
    const goHome = async () => {
        const homeLink = page.getByRole('link', {name:'Workforce home', exact:true});
        if (page.url().startsWith(base+'/desk/') && await homeLink.isVisible()) await homeLink.click();
        else await page.goto(base + '/desk/plus-point', {waitUntil: 'domcontentloaded'});
        await page.locator('.pp-task-home').waitFor();
    };
    const browserGet=async url=>{
        const data=await page.evaluate(async url=>(await(await fetch(url)).json()),url);
        return {json:async()=>data};
    };
    try {
        await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
        const result=await page.evaluate(async credentials=>(await(await fetch('/api/method/login',{
            method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)})).json()),
            {usr:process.env.PP_BROWSER_USER||'Administrator',pwd:process.env.PP_BROWSER_PASSWORD||settings.PP_ADMIN_PASSWORD});
        assert.equal(result.message,'Logged In');
        assert.equal(result.home_page,'/desk/plus-point');
        await goHome();
        assert.equal(await page.locator('.pp-quick-start').evaluate(node => node.open), false);
        assert.equal(await page.locator('.pp-all-records').count(), 0);
        assert(!(await page.locator('.body-sidebar').innerText()).includes('PP Assignment'));
        await page.locator('.body-sidebar').getByText('Assign workers', {exact: true}).waitFor();
        const primary = await page.getByRole('button', {name: 'Mark attendance', exact: true}).boundingBox();
        assert(primary.height >= 44, 'Attendance action must have a comfortable target');
        await page.screenshot({path: path.join(out, 'customer-home.png'), fullPage: true});

        await page.goto(base + '/desk/plus-point/pp-milestone', {waitUntil: 'domcontentloaded'});
        await page.getByRole('button', {name: 'Add milestone', exact: true}).waitFor();
        await page.getByText('Fixed contract milestones', {exact: true}).first().waitFor();
        assert.equal(await page.locator('.list-row-head').getByText('ID', {exact: true}).count(), 0);
        await page.screenshot({path: path.join(out, 'customer-milestones.png'), fullPage: true});
        console.log('PASS compact task home, grouped plain-language navigation, optional setup and readable milestone list');

        await goHome();
        const date = await page.evaluate(() => frappe.datetime.add_days(frappe.datetime.get_today(), 2));
        const sites = await browserGet(base + '/api/resource/PP%20Site?filters=' + encodeURIComponent(JSON.stringify({site_name:'DHA construction site (Demo)'})));
        const records = (await sites.json()).data;
        assert(records?.length, 'Seed the demo site before running attendance UX QA');
        const filters = encodeURIComponent(JSON.stringify({site: records[0].name, work_date: date}));
        const existing = await browserGet(base + '/api/resource/PP%20Daily%20Register?filters=' + filters);
        assert.equal((await existing.json()).data.length, 0, 'Refusing to modify existing attendance on the test date');
        const openAttendance = async () => {
            await page.getByRole('button', {name:'Mark attendance', exact:true}).click();
            await page.getByRole('dialog').getByRole('button', {name:'Review attendance', exact:true}).waitFor();
            await page.waitForFunction(() => window.cur_dialog?.display && cur_dialog.get_field('work_date'));
            await page.evaluate(async values => {
                const dialog = cur_dialog;
                await dialog.set_value('site', values.site);
                await dialog.set_value('work_date', values.date);
            }, {site: records[0].name, date});
            const preparation = !cleanupName ? page.waitForResponse(response =>
                response.url().includes('/api/method/plus_point.api.prepare_daily_register') &&
                response.request().method() === 'POST') : null;
            await page.getByRole('dialog').getByRole('button', {name:'Review attendance', exact:true}).click();
            if (preparation) {
                const response = await preparation;
                const result = await response.json();
                assert(response.ok() && result.message?.name, 'Attendance preparation failed');
                cleanupName = result.message.name;
            }
            await page.waitForURL('**/pp-daily-register/**');
            await page.waitForFunction(() => window.cur_frm?.doctype === 'PP Daily Register' && cur_frm.doc.name && !cur_frm.is_new());
            return page.evaluate(() => ({name:cur_frm.doc.name, state:cur_frm.doc.docstatus, workers:cur_frm.doc.entries.length}));
        };
        const first = await openAttendance();
        assert.equal(first.name, cleanupName);
        assert.equal(first.state, 0); assert(first.workers > 0);
        await page.screenshot({path: path.join(out, 'customer-attendance-draft.png'), fullPage: true});
        await goHome();
        const second = await openAttendance();
        assert.equal(second.name, first.name, 'Opening saved attendance must reuse the draft');
        assert.equal(second.state, 0, 'The shortcut must never approve work automatically');
        const count = await browserGet(base + '/api/resource/PP%20Daily%20Register?filters=' + filters);
        assert.equal((await count.json()).data.length, 1);
        console.log('PASS attendance shortcut creates a populated draft and reopens it without a duplicate or approval');

        await page.setViewportSize({width:390, height:844});
        await goHome();
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await page.screenshot({path: path.join(out, 'customer-home-mobile.png'), fullPage: true});
        await page.getByRole('button', {name:'Mark attendance', exact:true}).click();
        await page.getByRole('dialog').getByRole('button', {name:'Review attendance', exact:true}).waitFor();
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await page.keyboard.press('Escape');
        assert.deepEqual(failures, [], 'Customer UX produced browser/server errors');
        console.log('PASS 390px mobile home and attendance picker; zero browser/server errors');
    } catch (error) {
        await page.screenshot({path:path.join(out,'customer-ux-failure.png'),fullPage:true});
        console.error('Browser failures:',failures);
        console.error('Visible page:',(await page.locator('body').innerText()).slice(-2500));
        throw error;
    } finally {
        try {
            if (cleanupName) {
                // Operators can create/submit attendance but cannot delete it.
                // Cleanup uses the existing local bootstrap administrator separately.
                const context = await browser.newContext();
                try {
                    const cleanupPage=await context.newPage();
                    await cleanupPage.goto(base+'/login',{waitUntil:'domcontentloaded'});
                    assert.equal(await cleanupPage.evaluate(async credentials=>(await(await fetch('/api/method/login',{
                        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)})).json()).message,
                        {usr:'Administrator',pwd:settings.PP_ADMIN_PASSWORD}),'Logged In');
                    await cleanupPage.goto(base+'/desk/plus-point',{waitUntil:'domcontentloaded'});
                    await cleanupPage.waitForFunction(()=>window.frappe?.csrf_token);
                    const status=await cleanupPage.evaluate(async name=>(await fetch('/api/resource/PP%20Daily%20Register/'+encodeURIComponent(name),{
                        method:'DELETE',headers:{'X-Frappe-CSRF-Token':frappe.csrf_token}})).status,cleanupName);
                    assert.equal(status,202,'Temporary attendance draft cleanup failed');
                    console.log('PASS temporary attendance draft removed by local administrator');
                } finally { await context.close(); }
            }
        } finally { await browser.close(); }
    }
})().catch(error=>{console.error(error.message);process.exitCode=1;});
