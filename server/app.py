#!/usr/bin/env python3
"""Demo API for Faketvija: personas kods login with token sessions.

Endpoints (JSON):
    POST /api/login   {"personasKods": "320000-00000"} -> {"token", "person"}
    GET  /api/me      Authorization: Bearer <token>    -> {"person"}
    POST /api/logout  Authorization: Bearer <token>    -> {"ok": true}
    GET  /api/vsaa/dashboard            -> {"dashboard": {...}}  situation overview (children, sick leaves, contributions, reminders)
    POST /api/vsaa/apply                {"benefitCode", "childId"|"sickLeaveId", "iban", "options"} -> application + dashboard
    POST /api/vsaa/profile              {"iban", "remindersEnabled"} -> dashboard
    POST /api/vsaa/notify-other-parent  {"childId"} -> e-address message to the other parent + dashboard
    GET  /api/vsaa/vacancies            -> NVA open-data vacancies for the person's municipality
    GET  /api/vsaa/legal                -> benefit rules with their legal sources (public)
    GET  /api/admin/applications        -> every stored application (401 without a session, 403 for non-admins)
    POST /api/admin/applications/<id>/status {"status"} -> decision + applicant notification (admin only)

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
import sqlite3
import time
import threading
from contextlib import contextmanager
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import vsaa
import demo_registry
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
            demo_registry.promote_adult_children(connection)
            vsaa.sanitize_shared_messages(connection)
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
        'address': row['address'],
        'birthDate': row['birth_date'],
        'iban': row['iban'],
        'role': row['role'],
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
        if path == '/api/demo/admin':
            if os.environ.get('DEMO_ADMIN_ENABLED', '1') != '1':
                return self.send_json(HTTPStatus.NOT_FOUND, {'error':'not_found'})
            with database() as db:
                data = demo_registry.admin_data(db)
            return self.send_json(HTTPStatus.OK, data)
        if path == '/api/messages':
            return self.handle_messages()
        if path == '/api/me':
            return self.handle_me()
        if path == '/api/vsaa/dashboard':
            return self.handle_vsaa('dashboard')
        if path == '/api/vsaa/vacancies':
            return self.handle_vsaa('vacancies')
        if path == '/api/vsaa/legal':
            return self.send_json(HTTPStatus.OK, vsaa.legal())
        if path == '/api/admin/applications':
            return self.handle_admin()
        if path.startswith('/api/'):
            return self.send_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
        super().do_GET()

    def do_POST(self):
        path = self.path.split('?', 1)[0]
        reset_match = re.fullmatch(r'/api/demo/people/(\d+)/clear-iban', path)
        if reset_match:
            if os.environ.get('DEMO_ADMIN_ENABLED', '1') != '1':
                return self.send_json(HTTPStatus.NOT_FOUND, {'error':'not_found'})
            with database() as db:
                result = db.execute('UPDATE people SET iban = NULL WHERE id = ?', (int(reset_match.group(1)),))
                if not result.rowcount:
                    return self.send_json(HTTPStatus.NOT_FOUND, {'error':'not_found'})
            return self.send_json(HTTPStatus.OK, {'ok':True})
        read_match = re.fullmatch(r'/api/messages/(\d+)/read', path)
        if read_match:
            return self.handle_messages(int(read_match.group(1)))
        decision_match = re.fullmatch(r'/api/admin/applications/(\d+)/status', path)
        if decision_match:
            return self.handle_admin(int(decision_match.group(1)))
        if path == '/api/iban':
            return self.handle_iban()
        if path == '/api/login':
            return self.handle_login()
        if path == '/api/logout':
            return self.handle_logout()
        if path in ('/api/vsaa/apply', '/api/vsaa/profile', '/api/vsaa/notify-other-parent'):
            return self.handle_vsaa(path.rsplit('/', 1)[1])
        self.send_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})

    def current_person(self, db):
        token = self.bearer_token()
        if not token:
            return None
        return db.execute(
            'SELECT people.* FROM sessions JOIN people ON people.id = sessions.person_id '
            'WHERE sessions.token_hash = ? AND sessions.expires_at > ?',
            (hash_token(token), int(time.time())),
        ).fetchone()

    def handle_vsaa(self, action):
        """Dashboard of the signed-in person's VSAA situation and the demo actions on it."""
        payload = self.read_json() if self.command == 'POST' else {}
        if self.command == 'POST' and payload is None:
            return self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'invalid_body'})
        with database() as db:
            person = self.current_person(db)
            if person is None:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
            if person['role'] != 'person':
                return self.send_json(HTTPStatus.FORBIDDEN, {'error': 'forbidden'})
            result = {}
            if action == 'vacancies':
                data = vsaa.vacancies(vsaa.municipality_of(person['address']))
                if data is None:
                    return self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'vacancies_unavailable'})
                return self.send_json(HTTPStatus.OK, data)
            if action == 'apply':
                error, application_id = vsaa.apply(db, person, payload)
                if error:
                    return self.send_json(HTTPStatus.BAD_REQUEST, {'error': error})
                result['applicationId'] = application_id
            elif action == 'profile':
                error = vsaa.update_profile(db, person, payload)
                if error:
                    return self.send_json(HTTPStatus.BAD_REQUEST, {'error': error})
            elif action == 'notify-other-parent':
                error = vsaa.notify_other_parent(db, person, payload.get('childId'))
                if error in ('not_found', 'no_other_parent'):
                    return self.send_json(HTTPStatus.NOT_FOUND, {'error': error})
                result['notified'] = error is None
                result['notice'] = error
            person = db.execute('SELECT * FROM people WHERE id = ?', (person['id'],)).fetchone()
            data = vsaa.dashboard(db, person)
            result['remindersDelivered'] = vsaa.deliver_reminders(db, person, data)
            result['dashboard'] = data
        self.send_json(HTTPStatus.OK, result)

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
            # Switching accounts: the browser sends its previous token, which is revoked here.
            previous = self.bearer_token()
            if previous:
                db.execute('DELETE FROM sessions WHERE token_hash = ?', (hash_token(previous),))
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

    def handle_iban(self):
        token = self.bearer_token()
        with database() as db:
            session = db.execute('SELECT person_id FROM sessions WHERE token_hash = ? AND expires_at > ?',
                                 (hash_token(token), int(time.time()))).fetchone() if token else None
            if session is None:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
            data = self.read_json()
            iban = re.sub(r'\s+', '', str(data.get('iban', ''))).upper() if data else ''
            # Latvian IBAN: LV, checksum, four bank letters, thirteen account characters.
            valid = bool(re.fullmatch(r'LV[0-9]{2}[A-Z]{4}[A-Z0-9]{13}', iban))
            if valid:
                rearranged = iban[4:] + iban[:4]
                digits = ''.join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
                valid = int(digits) % 97 == 1
            if not valid:
                return self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'invalid_iban'})
            owner = db.execute('SELECT personas_kods FROM people WHERE id = ?', (session['person_id'],)).fetchone()
            error = demo_registry.bank_error(db, owner['personas_kods'], iban)
            if error:
                return self.send_json(HTTPStatus.BAD_REQUEST, {'error':error})
            db.execute('UPDATE people SET iban = ? WHERE id = ?', (iban, session['person_id']))
            person = db.execute('SELECT * FROM people WHERE id = ?', (session['person_id'],)).fetchone()
        self.send_json(HTTPStatus.OK, {'person': public_person(person)})

    def handle_messages(self, message_id=None):
        token = self.bearer_token()
        with database() as db:
            session = db.execute(
                'SELECT person_id FROM sessions WHERE token_hash = ? AND expires_at > ?',
                (hash_token(token), int(time.time())),
            ).fetchone() if token else None
            if session is None:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
            person_id = session['person_id']
            if message_id is not None:
                result = db.execute(
                    'UPDATE messages SET read_at = COALESCE(read_at, ?) WHERE id = ? AND person_id = ?',
                    (int(time.time()), message_id, person_id),
                )
                if result.rowcount == 0:
                    return self.send_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
            rows = db.execute('SELECT * FROM messages WHERE person_id = ? ORDER BY received_at DESC, id DESC',
                              (person_id,)).fetchall()
            messages = [{'id': row['id'], 'sender': row['sender'], 'subject': row['subject'],
                         'body': row['body'], 'receivedAt': row['received_at'], 'readAt': row['read_at'],
                         'template': row['template'], 'params': json.loads(row['params'] or '{}')}
                        for row in rows]
        self.send_json(HTTPStatus.OK, {'messages': messages,
                                     'unreadCount': sum(item['readAt'] is None for item in messages)})

    def handle_admin(self, application_id=None):
        """Administrator inbox: 401 without a valid session, 403 for ordinary portal users."""
        payload = self.read_json() if self.command == 'POST' else None
        with database() as db:
            person = self.current_person(db)
            if person is None:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
            if person['role'] != 'admin':
                return self.send_json(HTTPStatus.FORBIDDEN, {'error': 'forbidden'})
            if application_id is not None:
                if payload is None:
                    return self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'invalid_body'})
                error = vsaa.admin_decide(db, person, application_id, payload.get('status'))
                if error == 'not_found':
                    return self.send_json(HTTPStatus.NOT_FOUND, {'error': error})
                if error:
                    return self.send_json(HTTPStatus.BAD_REQUEST, {'error': error})
            data = vsaa.admin_applications(db)
            data['admin'] = {'name': f"{person['first_name']} {person['last_name']}"}
        self.send_json(HTTPStatus.OK, data)

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
    def refresh_adult_registry():
        while True:
            time.sleep(60)
            try:
                with database():
                    pass
            except sqlite3.Error as error:
                print(f'Adult registry update failed: {error}')
    threading.Thread(target=refresh_adult_registry,daemon=True).start()
    print(f'Faketvija demo server on http://{host}:{port} (database: {DB_PATH})')
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    main()
