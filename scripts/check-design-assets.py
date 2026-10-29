"""Verify imported SVG integrity and allowlisted references without Frappe or network access."""
import hashlib
import json
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('asset_installer', root / 'scripts/install-design-assets.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
directory = root / 'apps/plus_point/plus_point/public/images/design-system'
manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
assert len({f['file'] for f in manifest['files']}) == len(manifest['files'])
for file in manifest['files']:
    path = (directory / file['file']).resolve()
    assert path.is_relative_to(directory.resolve()) and path.suffix == '.svg'
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == file['sha256']
    installer.inspect_svg(data)
for code in manifest['country_names'].values():
    assert (directory / 'flags' / (code + '.svg')).is_file(), code
print(json.dumps({'verified_svgs': len(manifest['files']), 'svg_bytes': sum(f['bytes'] for f in manifest['files']), 'external_references': 0, 'active_content': 0, 'all_country_aliases_resolve': True}))
