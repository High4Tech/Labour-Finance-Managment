"""Import only the local SVG variants consumed by PLUS POINT. Never extract archive paths."""
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'apps/plus_point/plus_point/public/images/design-system'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def inspect_svg(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('SVG entities are not allowed')
    root = ET.fromstring(data)
    if root.tag != f'{{{NS}}}svg':
        raise ValueError('Expected an SVG')
    for node in root.iter():
        tag = node.tag.split('}')[-1]
        if tag in {'script', 'style', 'foreignObject', 'image', 'set'} or tag.startswith('animate'):
            raise ValueError('Unexpected active or embedded content')
        for key, value in node.attrib.items():
            key = key.split('}')[-1].lower()
            if key.startswith('on') or (key in {'href', 'src'} and not value.startswith('#')):
                raise ValueError('External references and handlers are not allowed')
            for ref in re.findall(r'url\((.*?)\)', value):
                if not ref.strip(' \"\'').startswith('#'):
                    raise ValueError('External CSS URL is not allowed')
    return root


def install(archive):
    entries = []
    countries = {}
    with ZipFile(archive) as z:
        def save(source, name, data=None, note=None):
            data = z.read(source) if data is None else data
            inspect_svg(data)
            target = TARGET / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entries.append(dict(file=name, source=source, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), **({'note': note} if note else {})))

        for name in z.namelist():
            match = re.fullmatch(r'File Types/File type=(Document|Image|Archive|Media)/([\w]+), Type=Default.svg', name)
            if match:
                save(name, 'files/' + match[2].lower() + '.svg')
            match = re.fullmatch(r'File Types/(.+)-([A-Z]{2})-rectangle.svg', name)
            if match:
                code = match[2].lower()
                save(name, 'flags/' + code + '.svg')
                key = ''.join(c for c in unicodedata.normalize('NFKD', match[1]).lower() if c.isascii() and c.isalnum())
                countries[key] = code
        save('File Types/File type=Simple/Document, Type=Default.svg', 'files/document.svg')
        source = 'File Upload System/State=Default.svg'
        original = inspect_svg(z.read(source))
        icon = ET.Element(f'{{{NS}}}svg', dict(width='40', height='40', viewBox='0 0 40 40', fill='none'))
        group = ET.SubElement(icon, f'{{{NS}}}g', dict(transform='translate(-236 -16)'))
        group.append(next(child for child in original if child.tag == f'{{{NS}}}g'))
        for child in original:
            if child.tag == f'{{{NS}}}defs':
                icon.append(child)
        save(source, 'upload.svg', ET.tostring(icon, encoding='utf-8'), 'Extracted the upload symbol from the supplied composition; interactive text is rendered by the app.')
        # This integration is already supported by Frappe's uploader; no new connection is added.
        drive = 'File Types/App icons/google_drive.svg'
        save(drive, 'integrations/google-drive.svg')
    # Some regional flags share a country code; keep the final country variant
    # and its matching source/hash rather than duplicate records for one path.
    entries = list({entry['file']: entry for entry in entries}.values())
    countries.update({'czechrepublic':'cz', 'republicofkorea':'kr', 'korea':'kr', 'russianfederation':'ru', 'unitedstatesofamerica':'us', 'vietnam':'vn', 'turkey':'tr', 'taiwan':'tw', 'congodemocraticrepublic':'cd', 'congo':'cg', 'bolivia':'bo', 'venezuela':'ve', 'tanzania':'tz', 'moldova':'md', 'iran':'ir', 'syria':'sy', 'laos':'la', 'bruneidarussalam':'bn', 'palestinianterritory':'ps'})
    (TARGET / 'manifest.json').write_text(json.dumps(dict(source='User-provided Downloads.zip, 2026-10-29', files=entries, country_names=countries), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(entries), bytes=sum(e['bytes'] for e in entries), country_flags=len([e for e in entries if e['file'].startswith('flags/')]))))
    return countries


if __name__ == '__main__':
    import sys
    install(sys.argv[1])
