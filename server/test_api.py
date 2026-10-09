#!/usr/bin/env python3
"""End-to-end check of the demo API against a throwaway database.

Run: python3 server/test_api.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8099
BASE = f'http://127.0.0.1:{PORT}'


def call(path, method='GET', body=None, token=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, raw
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main():
    failures = []

    def check(label, condition, detail=''):
        print(('PASS' if condition else 'FAIL'), label, detail if not condition else '')
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, 'test.db')
        env = {**os.environ, 'DB_PATH': db_path, 'PORT': str(PORT)}
        server = subprocess.Popen([sys.executable, str(HERE / 'app.py')], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(50):
                try:
                    call('/api/me')
                    break
                except Exception:
                    time.sleep(0.1)

            people = sqlite3.connect(db_path).execute('SELECT personas_kods, first_name, last_name FROM people').fetchall()
            check('database seeded with 60 people', len(people) == 60, str(len(people)))
            code, first, last = people[0]

            status, _ = call('/api/login', 'POST', {'personasKods': 'abc'})
            check('malformed code -> 400', status == 400, str(status))
            status, _ = call('/api/login', 'POST', {'personasKods': '000000-00000'})
            check('unknown code -> 401', status == 401, str(status))
            status, _ = call('/api/login', 'POST')
            check('missing body -> 400', status == 400, str(status))

            status, raw = call('/api/login', 'POST', {'personasKods': code})
            payload = json.loads(raw)
            token = payload.get('token', '')
            check('valid code -> 200 with token', status == 200 and len(token) >= 32, str(status))
            check('login returns an imported address', payload['person']['address'] in {item['label'] for item in json.loads((Path(__file__).resolve().parent.parent / 'public/data/addresses.json').read_text())['addresses']})
            check('login returns the right person', payload['person']['firstName'] == first and payload['person']['lastName'] == last)

            status, raw = call('/api/login', 'POST', {'personasKods': code.replace('-', '')})
            check('code without dash is accepted', status == 200, str(status))

            status, raw = call('/api/me', token=token)
            check('/api/me with token -> 200', status == 200 and json.loads(raw)['person']['personasKods'] == code, str(status))
            status, _ = call('/api/me', token='not-a-token')
            check('/api/me bad token -> 401', status == 401, str(status))
            status, _ = call('/api/me')
            check('/api/me no token -> 401', status == 401, str(status))

            stored = [row[0] for row in sqlite3.connect(db_path).execute('SELECT token_hash FROM sessions')]
            check('only token hashes are stored', token not in stored and all(len(item) == 64 for item in stored))

            conn = sqlite3.connect(db_path)
            conn.execute('UPDATE sessions SET expires_at = 1')
            conn.commit()
            conn.close()
            status, _ = call('/api/me', token=token)
            check('expired session -> 401', status == 401, str(status))

            status, raw = call('/api/login', 'POST', {'personasKods': code})
            token = json.loads(raw)['token']
            status, _ = call('/api/logout', 'POST', token=token)
            check('logout -> 200', status == 200, str(status))
            status, _ = call('/api/me', token=token)
            check('token rejected after logout', status == 401, str(status))

            status, _ = call('/index.html')
            check('static index.html served', status == 200, str(status))
            status, _ = call('/auth.js')
            check('static auth.js served', status == 200, str(status))
            status, _ = call('/api/nothing')
            check('unknown /api path -> 404', status == 404, str(status))
        finally:
            server.terminate()
            server.wait(timeout=5)

    print('\nAll checks passed.' if not failures else f'\n{len(failures)} check(s) failed.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
