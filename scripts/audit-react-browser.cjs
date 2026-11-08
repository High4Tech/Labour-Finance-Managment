/* Sequential company UI regression. Suite-level writes are intercepted. */
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa','react-audit');
fs.mkdirSync(out,{recursive:true});
const names=['foundation','dashboard','layout','planning','workers','clients','agreements','agreement-builder','payments','imports','resources','finance'];
const requested=process.argv.slice(2);
if(requested.some(name=>!names.includes(name)))throw new Error('Unknown browser suite');
const prior=requested.length&&fs.existsSync(path.join(out,'report.json'))?JSON.parse(fs.readFileSync(path.join(out,'report.json'),'utf8')).results:[];
const results=[...prior];
for(const name of requested.length?requested:names){
 const started=Date.now(),result=spawnSync(process.execPath,[path.join(__dirname,'browser-react-'+name+'.cjs')],{cwd:root,encoding:'utf8',timeout:300000});
 const output=(result.stdout||'')+(result.stderr||'');
 fs.writeFileSync(path.join(out,name+'.log'),output);
 let details;try{details=JSON.parse(output.match(/\{\s*"passed"[\s\S]*\}\s*$/)?.[0]);}catch{}
 const previous=results.findIndex(row=>row.suite===name);
 const current={suite:name,exit:result.status,passed:result.status===0,seconds:Math.round((Date.now()-started)/100)/10,details,error:result.error?.message};
 if(previous>=0)results[previous]=current;else results.push(current);
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({generated:new Date().toISOString(),results},null,2));
 console.log((result.status===0?'PASS ':'FAIL ')+name+' '+current.seconds+'s');
}
console.log(JSON.stringify({passed:results.filter(row=>row.passed).length,failed:results.filter(row=>!row.passed).map(row=>row.suite)}));
if(results.some(row=>!row.passed))process.exitCode=1;
