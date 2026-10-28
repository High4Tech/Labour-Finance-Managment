const fs=require('fs'),path=require('path'),crypto=require('crypto'),zlib=require('zlib'),esbuild=require('esbuild');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'apps/plus_point/plus_point/public/js/vendor');
fs.mkdirSync(out,{recursive:true});
const target=path.join(out,'echarts-dashboard.min.js');
esbuild.buildSync({entryPoints:[path.join(__dirname,'entry.js')],outfile:target,bundle:true,minify:true,format:'iife',globalName:'PlusPointECharts',target:['es2020'],legalComments:'eof',charset:'utf8',banner:{js:'/* Apache ECharts 6.1.0 — modular PLUS POINT build. See echarts-dashboard.LICENSE.txt. */'}});
// Keep upstream license text, normalizing only trailing whitespace in legal comments.
fs.writeFileSync(target,fs.readFileSync(target,'utf8').replace(/\/\*![\s\S]*?\*\//g,comment=>comment.replace(/[ \t]+$/gm,'')));
const pkg=path.dirname(require.resolve('echarts/package.json'));
fs.writeFileSync(path.join(out,'echarts-dashboard.LICENSE.txt'),['Apache ECharts 6.1.0 (Apache-2.0)',fs.readFileSync(path.join(pkg,'LICENSE'),'utf8'),fs.readFileSync(path.join(pkg,'NOTICE'),'utf8'),'Bundled transitive dependency: zrender',fs.readFileSync(path.join(path.dirname(require.resolve('zrender/package.json')),'LICENSE'),'utf8')].join('\n\n'));
const bytes=fs.readFileSync(target),meta={library:'Apache ECharts',version:require('echarts/package.json').version,modules:['LineChart','BarChart','PieChart','GridComponent','TooltipComponent','AriaComponent','SVGRenderer'],bytes:bytes.length,gzipBytes:zlib.gzipSync(bytes).length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
fs.writeFileSync(path.join(out,'echarts-dashboard.manifest.json'),JSON.stringify(meta,null,2)+'\n');console.log(JSON.stringify(meta));
