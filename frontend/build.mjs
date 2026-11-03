import {build} from 'esbuild';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
const out=new URL('../apps/plus_point/plus_point/public/react/',import.meta.url);
await mkdir(out,{recursive:true});
const result=await build({entryPoints:['src/index.tsx'],outdir:out.pathname.replace(/^\/([A-Za-z]:)/,'$1'),bundle:true,splitting:true,format:'esm',target:['es2022'],minify:true,metafile:true,jsx:'automatic',define:{'process.env.NODE_ENV':'"production"'},chunkNames:'chunks/[name]-[hash]',legalComments:'eof',charset:'utf8'});
const outputs=[];
for(const [file,meta] of Object.entries(result.metafile.outputs)){
 const bytes=await readFile(file);outputs.push({file,bytes:bytes.length,gzipBytes:gzipSync(bytes).length,sha256:createHash('sha256').update(bytes).digest('hex'),imports:meta.imports});
}
// Keep old local chunks served for already-open tabs, but publish only the
// dependency graph of this build. A development rebuild must not accumulate
// unrelated chunks in a release or delete files an open tab may still request.
const chunks=outputs.map(({file})=>file.replaceAll('\\','/').split('/public/react/')[1]).filter(file=>file?.startsWith('chunks/')).sort();
await writeFile(new URL('.gitignore',out),'# Previous development chunks remain available locally for open tabs.\nchunks/*\n'+chunks.map(file=>'!'+file).join('\n')+'\n');
await writeFile(new URL('manifest.json',out),JSON.stringify({framework:'React',version:'19.3.1',outputs},null,2)+'\n');
const licenses=[];
for(const name of ['react','react-dom','scheduler'])licenses.push(name+'\n'+await readFile(new URL('node_modules/'+name+'/LICENSE',import.meta.url),'utf8'));
await writeFile(new URL('LICENSE.txt',out),licenses.join('\n\n'));
console.log(JSON.stringify(outputs.map(({file,bytes,gzipBytes})=>({file,bytes,gzipBytes})),null,2));
