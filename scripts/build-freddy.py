"""Adapt the supplied Freddy export to native JS, without React, eval or blob modules."""
import hashlib,json,re,sys,zipfile
from pathlib import Path


def main():
    archive=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1]
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest!='a09e252be68959ef85a956607dfc75906b6db6a440d38363823c49ddb08f1c09':raise ValueError('Review this new avatar export before updating the approved source hash.')
    with zipfile.ZipFile(archive) as source:
        runtime=source.read('avatar-runtime.ts').decode('utf-8')
        avatar=source.read('freddy.avatar.ts').decode('utf-8')
    def literal(name):
        match=re.search(r'^const '+name+r' = (".*")$',runtime,re.M)
        if not match:raise ValueError('Unknown avatar export format: '+name)
        return json.loads(match[1])
    engine=literal('ENGINE_SOURCE');browser=literal('BROWSER_RUNTIME_SOURCE')
    data=json.loads(avatar.split('export const avatarData = ',1)[1].split(' as const satisfies AvatarData',1)[0])
    if data['version']!=1:raise ValueError('Unsupported avatar version')
    if any(token in engine+browser for token in ('fetch(', 'eval(', 'new Function', 'setInterval(')):
        raise ValueError('Review the changed runtime before building')
    # The export keeps ambient frames alive while paused. Stop them explicitly.
    browser=browser.replace('frameRequest = null;\n    if (transitionState)', 'frameRequest = null;\n    if (!playing) return;\n    if (transitionState)')
    browser=browser.replace('pause() {\n      const now', 'pause() {\n      if (frameRequest !== null) cancelAnimationFrame(frameRequest);\n      frameRequest = null;\n      const now')
    browser=browser.replace('destroy() {\n      clearSchedule();', 'destroy() {\n      playing = false;\n      clearSchedule();')
    output=root/'apps/plus_point/plus_point/public/js/freddy-runtime.js'
    output.write_text('/* Freddy procedural SVG export supplied by the app owner. Source SHA256: '+digest+' */\n(()=>{\nif(window.plus_point?.freddy_runtime)return;\n'+engine+'\nconst DATA='+json.dumps(data,separators=(',',':'))+';\n'+browser+'\nwindow.plus_point ||= {};plus_point.freddy_runtime={create:mountAvatar,animations:Object.keys(DATA.animations)};\n})();\n',encoding='utf-8')
    print(json.dumps(dict(source_sha256=digest,animations=list(data['animations']),bytes=output.stat().st_size)))


if __name__=='__main__':main()
