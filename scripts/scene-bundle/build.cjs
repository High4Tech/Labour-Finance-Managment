const fs=require('fs'),path=require('path'),crypto=require('crypto'),zlib=require('zlib'),esbuild=require('esbuild');
const out=path.resolve(__dirname,'../../apps/plus_point/plus_point/public/js/vendor'),target=path.join(out,'three-scene.min.js');
fs.mkdirSync(out,{recursive:true});
esbuild.buildSync({entryPoints:[path.join(__dirname,'entry.js')],outfile:target,bundle:true,minify:true,format:'iife',globalName:'PlusPointScene3D',target:['es2020'],legalComments:'eof',charset:'utf8',banner:{js:'/* Three.js r180 (MIT). Optional PLUS POINT event scene. See three-scene.LICENSE.txt. */'}});
// Normalize insignificant trailing whitespace inside upstream shader templates.
fs.writeFileSync(target,fs.readFileSync(target,'utf8').replace(/[ \t]+$/gm,''));
const pkg=path.resolve(path.dirname(require.resolve('three')),'..');
fs.copyFileSync(path.join(pkg,'LICENSE'),path.join(out,'three-scene.LICENSE.txt'));
const bytes=fs.readFileSync(target),meta={library:'Three.js',version:JSON.parse(fs.readFileSync(path.join(pkg,'package.json'),'utf8')).version,bytes:bytes.length,gzipBytes:zlib.gzipSync(bytes).length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),loading:'Explicit View event scene action only; no CDN or runtime model requests'};
fs.writeFileSync(path.join(out,'three-scene.manifest.json'),JSON.stringify(meta,null,2)+'\n');console.log(JSON.stringify(meta));
