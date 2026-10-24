/* Sequential QA browser audit. Stop if a failed fixture was not restored. */
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const names=process.argv.slice(2).length?process.argv.slice(2):['browser-draft-flow.cjs','browser-planning.cjs','browser-calendar.cjs','browser-agreement-flow.cjs','browser-import-deletion.cjs','browser-finance.cjs','browser-resources.cjs','browser-attendance.cjs','browser-worker-flows.cjs'];
 const day=new Date(),stamp=process.env.PP_AUDIT_DATE||String(day.getFullYear())+String(day.getMonth()+1).padStart(2,'0')+String(day.getDate()).padStart(2,'0');
 const evidence=path.join(out,'full-audit-browsers-'+stamp+'.json'),results=fs.existsSync(evidence)?JSON.parse(fs.readFileSync(evidence,'utf8')):[];const previous=results.length;
 for(const name of names){
  const start=Date.now();let log='';console.log('START '+name);
  const code=await new Promise(resolve=>{const child=spawn(process.execPath,[path.join(root,'scripts',name)],{cwd:root,env:{...process.env,PP_TEST_BROWSER:'msedge',PP_BROWSER_CHANNEL:'msedge'},windowsHide:true});child.stdout.on('data',chunk=>log+=chunk);child.stderr.on('data',chunk=>log+=chunk);child.on('error',error=>{log+=error.stack;resolve(-1);});child.on('close',resolve);});
  const result={script:name,status:code===0?'passed':'failed',exitCode:code,seconds:Math.round((Date.now()-start)/100)/10,restored:/restored/i.test(log),log:'.local/qa/audit-'+name+'.log'};results.push(result);
  fs.writeFileSync(path.join(out,'audit-'+name+'.log'),log);fs.writeFileSync(evidence,JSON.stringify(results,null,2));console.log(JSON.stringify(result));
  if(code!==0){console.log(log.slice(-3500));if(!result.restored){console.log('STOP: fixture restoration needs inspection');break;}}
 }
 if(results.slice(previous).some(r=>r.status==='failed'))process.exitCode=1;
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
