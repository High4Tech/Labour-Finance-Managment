/* Read-only native contractor reports, filters, form shortcuts and XLSX export. */
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
    assert(site.endsWith('.localhost') && site !== 'platform.localhost', 'Report QA requires a local tenant');
    const base = `http://${site}:${settings.FRAPPE_PORT || 8000}`;
    const browser = await chromium.launch({headless:true,
        ...(process.env.PP_BROWSER_CHANNEL ? {channel:process.env.PP_BROWSER_CHANNEL} : {})});
    const page = await browser.newPage({viewport:{width:1440, height:1000}});
    page.setDefaultTimeout(30000);
    const failures = [];
    page.on('pageerror', error => failures.push(error.message));
    page.on('response', response => {if(response.status()>=400) failures.push(`HTTP ${response.status()}: ${response.url()}`);});
    const out = path.join(root, '.local', 'qa'); fs.mkdirSync(out,{recursive:true});
    try {
        // Chromium resolves *.localhost itself; browser-native fetch also works
        // when Windows' command-line DNS resolver has no corresponding entry.
        await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
        const login = await page.evaluate(async credentials => {
            const response = await fetch('/api/method/login',{method:'POST',
                headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)});
            return (await response.json()).message;
        }, {usr:process.env.PP_BROWSER_USER || 'Administrator', pwd:process.env.PP_BROWSER_PASSWORD || settings.PP_ADMIN_PASSWORD});
        assert.equal(login,'Logged In');
        await page.goto(base+'/desk/plus-point',{waitUntil:'domcontentloaded'});
        await page.locator('.pp-task-home').waitFor();
        await page.locator('.pp-task-home').getByRole('link',{name:'Project finances',exact:true}).click();
        await page.waitForFunction(() => frappe.query_report?.report_name === 'PLUS POINT Project Finances' && frappe.query_report.data?.length);
        const project = await page.evaluate(() => frappe.query_report.data[0].project);
        const company = await page.evaluate(() => frappe.query_report.get_filter_value('company'));
        const values = await page.evaluate(async project => {
            const result = await frappe.call({method:'plus_point.api.project_summary',args:{project}});
            return {actual:frappe.query_report.data.find(row=>row.project===project),expected:result.message};
        },project);
        for(const key of ['earned_revenue','labour_cost','wages_paid','cash_collected_gross','client_outstanding_gross','operational_profit'])
            assert.equal(values.actual[key],values.expected[key],key);
        await page.locator('.pp-context-bar').getByText(/Project results and workforce deployment/).waitFor();
        assert.equal(await page.locator('.pp-report-notes').evaluate(node=>node.open),false);
        await page.locator('.pp-report-notes > summary').click();
        await page.getByText(/Fixed revenue comes from approved milestones/).waitFor();
        await page.locator('.pp-report-notes > summary').click();
        await page.screenshot({path:path.join(out,'project-finances-report.png'),fullPage:true});
        await page.evaluate(() => frappe.query_report.set_filter_value('view','Deployment overview'));
        await page.waitForFunction(() => frappe.query_report.data?.[0]?.deployed_today !== undefined);
        await page.screenshot({path:path.join(out,'deployment-report.png'),fullPage:true});
        console.log('PASS native project finances and deployment views; values match the tested financial API');

        const worker = await page.evaluate(async () => {
            const rows=await frappe.db.get_list('Employee',{filters:{employee_name:'PLUS POINT Demo'},fields:['name'],limit:1});
            return rows[0]?.name;
        });
        assert(worker,'Seed the local demo worker before report QA');
        await page.goto(base+'/desk/employee/'+encodeURIComponent(worker),{waitUntil:'domcontentloaded'});
        await page.getByRole('button',{name:'Worker statement',exact:true}).click();
        await page.waitForFunction(() => frappe.query_report?.report_name==='PLUS POINT Worker Statement' && frappe.query_report.data?.length);
        assert.equal(await page.evaluate(()=>frappe.query_report.get_filter_value('employee')),worker);
        assert.equal(await page.evaluate(()=>frappe.query_report.get_filter_value('company')),company);
        const statement=await page.evaluate(()=>({rows:frappe.query_report.data,summary:frappe.query_report.raw_data.report_summary}));
        assert(statement.rows.some(row=>row.kind==='Work'));
        assert(statement.summary.some(card=>card.label==='Closing wage balance'));
        await page.screenshot({path:path.join(out,'worker-statement-report.png'),fullPage:true});
        await page.evaluate(()=>frappe.query_report.set_filter_value('view','Assignment history'));
        await page.waitForFunction(()=>frappe.query_report.data?.[0]?.start_date);
        assert(await page.evaluate(()=>frappe.query_report.data.some(row=>row.wage_rate)));
        const exported=await page.evaluate(async()=>{
            const body=new URLSearchParams({report_name:frappe.query_report.report_name,
                filters:JSON.stringify(frappe.query_report.get_filter_values()),file_format_type:'Excel',
                ignore_visible_idx:'1',export_in_background:'0'});
            const response=await fetch('/api/method/frappe.desk.query_report.export_query',{method:'POST',
                headers:{'X-Frappe-CSRF-Token':frappe.csrf_token},body});
            const bytes=new Uint8Array(await response.arrayBuffer());
            return {status:response.status,type:response.headers.get('content-type'),size:bytes.length,
                zip:bytes[0]===80 && bytes[1]===75};
        });
        assert.equal(exported.status,200); assert(exported.zip && exported.size>1000,JSON.stringify(exported));
        console.log('PASS worker form shortcut, work/payment statement, dated assignment history and native XLSX export');

        const terms=await page.evaluate(async project=>{
            const rows=await frappe.db.get_list('PP Contract Terms',{filters:{project},fields:['name'],limit:1});return rows[0].name;
        },project);
        await page.goto(base+'/desk/pp-contract-terms/'+encodeURIComponent(terms),{waitUntil:'domcontentloaded'});
        await page.getByRole('button',{name:'Project finances',exact:true}).click();
        await page.waitForFunction(project=>frappe.query_report?.report_name==='PLUS POINT Project Finances' &&
            frappe.query_report.get_filter_value('project')===project && frappe.query_report.data?.length,project);
        await page.setViewportSize({width:390,height:844});
        await page.screenshot({path:path.join(out,'project-report-mobile.png'),fullPage:true});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        assert.deepEqual(failures,[]);
        console.log('PASS billing terms shortcut, 390px native report layout and zero browser/server errors; no business records changed');
    } catch(error) {
        await page.screenshot({path:path.join(out,'reports-failure.png'),fullPage:true});
        console.error('Browser failures:',failures);
        console.error('Visible page:',(await page.locator('body').innerText()).slice(-2800));
        throw error;
    } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
