#!/usr/bin/env python3
"""Demo API for Faketvija: personas kods login with token sessions.

Endpoints (JSON):
    POST /api/login   {"personasKods": "320000-00000"} -> {"token", "person"}
    GET  /api/me      Authorization: Bearer <token>    -> {"person"}
    POST /api/logout  Authorization: Bearer <token>    -> {"ok": true}

Only a SHA-256 hash of each token is stored, so a leaked database cannot be
used to impersonate anyone. This is a prototype: a personas kods alone is not
a credential in any real system. Use it only with the fictional demo data.

Run `python3 server/app.py` to serve both the API and the static `public/`
folder at http://127.0.0.1:8080. In Docker, nginx serves the static files and
proxies /api/ here.
"""
import hashlib
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from seed_people import DEFAULT_DB, connect, ensure_seeded

PUBLIC_DIR = Path(__file__).resolve().parent.parent / 'public'
DB_PATH = Path(os.environ.get('DB_PATH', DEFAULT_DB))
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_BODY_BYTES = 4096
CODE_PATTERN = re.compile(r'^(\d{6})-?(\d{5})$')


@contextmanager
def database():
    connection = connect(DB_PATH)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def public_person(row):
    return {
        'id': row['id'],
        'firstName': row['first_name'],
        'lastName': row['last_name'],
        'personasKods': row['personas_kods'],
        'email': row['email'],
        'phone': row['phone'],
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def bearer_token(self):
        header = self.headers.get('Authorization', '')
        scheme, _, token = header.partition(' ')
        return token.strip() if scheme.lower() == 'bearer' and token.strip() else None

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            return None
        if not 0 < length <= MAX_BODY_BYTES:
            return None
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/api/me':
            return self.handle_me()
        if path.startswith('/api/'):
            return self.send_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
        super().do_GET()

    def do_POST(self):
        path = self.path.split('?', 1)[0]
        if path == '/api/login':
            return self.handle_login()
        if path == '/api/logout':
            return self.handle_logout()
        self.send_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})

    def handle_login(self):
        data = self.read_json()
        match = CODE_PATTERN.match(str(data.get('personasKods', '')).strip()) if data else None
        if not match:
            return self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'invalid_format'})
        code = f'{match.group(1)}-{match.group(2)}'

        with database() as db:
            person = db.execute('SELECT * FROM people WHERE personas_kods = ?', (code,)).fetchone()
            if person is None:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unknown_code'})
            now = int(time.time())
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires_at < ?', (now,))
            db.execute(
                'INSERT INTO sessions (token_hash, person_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
                (hash_token(token), person['id'], now, now + SESSION_TTL_SECONDS),
            )
        self.send_json(HTTPStatus.OK, {
            'token': token,
            'expiresAt': now + SESSION_TTL_SECONDS,
            'person': public_person(person),
        })

    def handle_me(self):
        token = self.bearer_token()
        person = None
        if token:
            with database() as db:
                person = db.execute(
                    'SELECT people.* FROM sessions JOIN people ON people.id = sessions.person_id '
                    'WHERE sessions.token_hash = ? AND sessions.expires_at > ?',
                    (hash_token(token), int(time.time())),
                ).fetchone()
        if person is None:
            return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
        self.send_json(HTTPStatus.OK, {'person': public_person(person)})

    def handle_logout(self):
        token = self.bearer_token()
        if token:
            with database() as db:
                db.execute('DELETE FROM sessions WHERE token_hash = ?', (hash_token(token),))
        self.send_json(HTTPStatus.OK, {'ok': True})


def main():
    with database() as db:
        ensure_seeded(db)
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8080'))
    print(f'Faketvija demo server on http://{host}:{port} (database: {DB_PATH})')
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    main()
