#!/usr/bin/env python3
"""Import a small CC0 PMLP first-name statistics snapshot for fictional children."""
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def main():
    metadata = json.load(urllib.request.urlopen('https://data.gov.lv/dati/api/3/action/package_show?id=personu-vardi'))['result']
    if metadata['license_id'] != 'CC0-1.0':
        raise ValueError('Name dataset license changed; review before importing')
    resource = next(r for r in metadata['resources'] if r['name'].startswith('Vardi-dz-'))
    raw = urllib.request.urlopen(resource['url']).read()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    names = []
    for gender in ('SIEVIETE', 'VĪRIETIS'):
        matches = [r for r in rows if r['Dzimums'] == gender and r['Vardi'].isalpha()]
        matches.sort(key=lambda r: -int(r['Skaits']))
        names.extend({'name':r['Vardi'].title(), 'gender':gender, 'count':int(r['Skaits'])} for r in matches[:100])
    output = {'source':'https://data.gov.lv/dati/dataset/personu-vardi', 'publisher':metadata['organization']['title'],
              'license':'CC0-1.0', 'resource':resource['url'], 'resourceName':resource['name'],
              'retrievedAt':datetime.now(timezone.utc).isoformat(), 'sha256':hashlib.sha256(raw).hexdigest(),
              'changes':'Top 100 alphabetic single first names per gender; title case; no personal records.', 'names':names}
    (ROOT/'data/metadata/personu-vardi.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    (ROOT/'public/data/person-names.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(f'Imported {len(names)} names, {output["license"]}')
if __name__ == '__main__': main()
