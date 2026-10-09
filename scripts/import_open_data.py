#!/usr/bin/env python3
"""Import licensed snapshots from data.gov.lv; requires Python 3 standard library only."""
import csv
import hashlib
import json
import shutil
import tempfile
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = 'https://data.gov.lv/dati/api/3/action/package_show?id='
DATASETS = ['varis-atvertie-dati', 'pasvaldibas-pakalpojumu-apraksti',
            'gimenes-valsts-pabalsta-sanemeji', 'vsaa-adm-pakalpojumu-sanemeju-skaits']
ADDRESS_FILES = ['aw_pilseta.csv', 'aw_novads.csv', 'aw_pagasts.csv',
                 'aw_ciems.csv', 'aw_iela.csv', 'aw_eka.csv']
LICENSES = {
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/legalcode.en',
    'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/legalcode.en',
}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'NewbornHackathon-OpenData/1.0'}), timeout=180) as response:
        if response.status != 200 or response.headers.get('Content-Range'):
            raise RuntimeError(f'Expected a full response: {url}')
        return response.read()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        header = stream.readline()
        delimiter = ';' if header.count(';') > header.count(',') else ','
        stream.seek(0)
        yield from csv.DictReader(stream, delimiter=delimiter)


def main():
    retrieved = datetime.now(timezone.utc).isoformat()
    manifest = {'retrievedAt': retrieved, 'datasets': [], 'licenses': [], 'limitations': [
        'Snapshot data, not a live government integration.',
        'Building/land addresses only; apartment/unit numbers are not imported.',
        'VSAA workbooks contain aggregate statistics, not benefit amounts, eligibility rules or personal records.',
        'Riga catalog covers Riga only and its publisher warns of incomplete data.',
    ]}
    # Complete and validate a snapshot before replacing the existing local files.
    with tempfile.TemporaryDirectory(prefix='newborn-open-data-') as temp:
        stage = Path(temp)
        raw = stage / 'data/raw'
        raw.mkdir(parents=True)
        for slug in DATASETS:
            package = json.loads(fetch(API + slug))
            if not package.get('success'):
                raise RuntimeError(f'Metadata fetch failed: {slug}')
            package = package['result']
            license_id = package['license_id']
            if license_id not in LICENSES:
                raise RuntimeError(f'Unreviewed license: {license_id}')
            write_json(stage / f'data/metadata/{slug}.json', package)
            entry = {'id': package['id'], 'slug': slug, 'title': package['title'],
                     'publisher': package.get('organization', {}).get('title'),
                     'source': 'https://data.gov.lv/dati/dataset/' + slug,
                     'license': license_id, 'licenseUrl': package.get('license_url'),
                     'metadataModified': package.get('metadata_modified'), 'resources': []}
            if slug == DATASETS[0]:
                selected = [next(r for r in package['resources'] if r['url'].lower().endswith('/' + name)) for name in ADDRESS_FILES]
            elif slug == DATASETS[1]:
                selected = [r for r in package['resources'] if r['format'].upper() == 'CSV']
            else:
                # The publishers' latest appended XLSX resource; original period stays in its name.
                selected = [r for r in package['resources'] if r['url'].lower().endswith('.xlsx')][-1:]
            if not selected:
                raise RuntimeError(f'No importable resources: {slug}')
            for resource in selected:
                name = resource['url'].rsplit('/', 1)[-1]
                destination = raw / slug / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                blob = fetch(resource['url'])
                if not blob or blob.lstrip().lower().startswith((b'<!doctype html', b'<html')):
                    raise RuntimeError(f'Empty or HTML resource: {name}')
                if name.endswith('.xlsx') and not blob.startswith(b'PK'):
                    raise RuntimeError(f'Invalid XLSX: {name}')
                destination.write_bytes(blob)
                entry['resources'].append({'id': resource['id'], 'name': resource['name'],
                    'url': resource['url'], 'format': resource['format'],
                    'lastModified': resource.get('last_modified'),
                    'localPath': str(destination.relative_to(stage)),
                    'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()})
                print(f'Downloaded {name}: {len(blob):,} bytes', flush=True)
            manifest['datasets'].append(entry)
        for license_id, url in LICENSES.items():
            blob = fetch(url)
            if b'<html' not in blob.lower():
                raise RuntimeError(f'Invalid license page: {license_id}')
            path = stage / f'data/licenses/{license_id}.html'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            manifest['licenses'].append({'id': license_id, 'url': url,
                'localPath': str(path.relative_to(stage)), 'sha256': hashlib.sha256(blob).hexdigest()})
        address_root = raw / DATASETS[0]
        nodes = {}
        for name in ADDRESS_FILES[:-1]:
            for row in read_csv(address_root / name):
                if row['STATUSS'] == 'EKS':
                    nodes[row['KODS']] = row
        municipalities = {}
        for code, row in nodes.items():
            if row['TIPS_CD'] == '113' or (row['TIPS_CD'] == '104' and row['VKUR_CD'] == '100000000'):
                municipalities[code] = row.get('SORT_NOS') or row['NOSAUKUMS']

        def municipality_of(row):
            parent = row['VKUR_CD']
            visited = set()
            while parent not in municipalities:
                if parent in visited or parent not in nodes:
                    return None
                visited.add(parent)
                parent = nodes[parent]['VKUR_CD']
            return parent

        groups = defaultdict(list)
        unresolved = []
        building_count = 0
        seen = set()
        for row in read_csv(address_root / 'aw_eka.csv'):
            if row['STATUSS'] != 'EKS':
                continue
            building_count += 1
            if row['KODS'] in seen:
                raise RuntimeError('Duplicate building address code')
            seen.add(row['KODS'])
            code = municipality_of(row)
            if not code:
                unresolved.append(row['KODS'])
                continue
            groups[code].append({'code': row['KODS'], 'label': row['STD'], 'municipalityCode': code})
        if not groups or not any(municipalities[c] == 'Rīga' for c in groups):
            raise RuntimeError('Import missing expected nationwide address coverage')
        index = []
        for code, rows in groups.items():
            rows.sort(key=lambda r: r['label'])
            write_json(stage / f'public/data/addresses/{code}.json', rows)
            index.append({'code': code, 'name': municipalities[code], 'addressCount': len(rows),
                          'file': f'addresses/{code}.json'})
        index.sort(key=lambda r: r['name'])
        write_json(stage / 'public/data/municipalities.json', index)
        # Preserve the initial demo API shape, with a representative subset for immediate UI use.
        preview = []
        for item in index:
            preview.extend({**row, 'municipality': item['name']} for row in groups[item['code']][:5])
        write_json(stage / 'public/data/addresses.json', {
            'source': manifest['datasets'][0]['source'], 'publisher': 'Valsts zemes dienests',
            'license': 'CC BY 4.0', 'retrievedAt': retrieved,
            'scope': 'Five sample building addresses per municipality. Full resolved snapshot is in addresses/; index is municipalities.json.',
            'addresses': preview})
        manifest['addressImport'] = {'activeBuildings': building_count,
            'resolvedBuildings': sum(map(len, groups.values())), 'municipalities': len(groups),
            'unresolvedCount': len(unresolved), 'unresolvedCodes': unresolved,
            'transformations': 'Filtered STATUSS=EKS; resolved municipality using VKUR_CD parent hierarchy; selected code and STD fields; grouped JSON by municipality.'}
        for entry in manifest['datasets']:
            if entry['slug'] == DATASETS[1]:
                rows = list(read_csv(stage / entry['resources'][0]['localPath']))
                write_json(stage / 'public/data/riga-services.json', {'source': entry['source'],
                    'license': entry['license'], 'retrievedAt': retrieved,
                    'warning': 'Riga-only catalog; publisher warns of incomplete data. Not eligibility rules.', 'records': rows})
                entry['recordCount'] = len(rows)
        write_json(stage / 'data/manifest.json', manifest)
        write_json(stage / 'public/data/sources.json', manifest)
        for relative in ['data/raw', 'data/metadata', 'data/licenses', 'public/data/addresses']:
            destination = ROOT / relative
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage / relative, destination, dirs_exist_ok=True)
        for relative in ['data/manifest.json', 'public/data/sources.json', 'public/data/municipalities.json',
                         'public/data/addresses.json', 'public/data/riga-services.json']:
            shutil.copy2(stage / relative, ROOT / relative)
        print(json.dumps(manifest['addressImport'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
