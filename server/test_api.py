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


def read_rows(path, query, parameters=()):
    connection = sqlite3.connect(path)
    try:
        return connection.execute(query, parameters).fetchall()
    finally:
        connection.close()


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

            people = read_rows(db_path, "SELECT personas_kods, first_name, last_name FROM people WHERE role = 'person' ORDER BY id")
            check('database seeded with four showcase people and three partners', len(people) == 7, str(len(people)))
            admin_row = read_rows(db_path, "SELECT personas_kods FROM people WHERE role = 'admin'")
            check('one demo administrator account is seeded', len(admin_row) == 1)
            _, bootstrap_raw=call('/api/login','POST',{'personasKods':admin_row[0][0]})
            demo_admin_token=json.loads(bootstrap_raw)['token']
            code, first, last = people[1]

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

            status, _ = call('/api/messages')
            check('inbox requires authentication', status == 401)
            status, raw = call('/api/messages', token=token)
            inbox = json.loads(raw)
            check('new user has unread demo mail', status == 200 and inbox['unreadCount'] >= 1)
            message_id = inbox['messages'][0]['id']
            _, other_raw = call('/api/login', 'POST', {'personasKods': people[4][0]})
            other_token = json.loads(other_raw)['token']
            status, _ = call(f'/api/messages/{message_id}/read', 'POST', token=other_token)
            check('other user cannot mark this message read', status == 404)
            status, raw = call(f'/api/messages/{message_id}/read', 'POST', token=token)
            read_at = json.loads(raw)['messages'][0]['readAt']
            check('reading mail clears unread count', status == 200 and json.loads(raw)['unreadCount'] == inbox['unreadCount'] - 1 and read_at is not None)
            _, raw = call(f'/api/messages/{message_id}/read', 'POST', token=token)
            check('marking read twice preserves timestamp', json.loads(raw)['messages'][0]['readAt'] == read_at)
            _, raw = call('/api/messages', token=token)
            check('read state persists on reload', json.loads(raw)['unreadCount'] == inbox['unreadCount'] - 1)
            saved = read_rows(db_path, 'SELECT read_at FROM messages WHERE id = ?', (message_id,))[0][0]
            check('read state stored in SQLite', saved == read_at)
            _, raw = call('/api/messages', token=other_token)
            check('other user retains unread mail', json.loads(raw)['unreadCount'] >= 1)

            check('fictional demonstration registry stays public',call('/api/demo/admin')[0] == 200)
            check('demo registry is explicitly labeled fictional',json.loads(call('/api/demo/admin',token=token)[1])['demoOnly'])
            status, raw = call('/api/demo/admin',token=demo_admin_token)
            registry = json.loads(raw)
            check('demo inspector exposes fictional registries', status == 200 and registry['demoOnly'])
            cases = {p['id']: p for p in registry['people']}
            check('four showcase child counts', [len(cases[i]['children']) for i in (1,2,3,4)] == [0,1,2,1])
            check('household counts match showcase', [len(cases[i]['children']) for i in (1,7,2,5,6,3,4)] == [0,0,1,1,2,2,1])
            check('single mother has no second parent',cases[4]['children'][0]['father_id'] is None)
            names = {r['name'] for r in json.loads((HERE.parent/'public/data/person-names.json').read_text())['names']}
            from datetime import date
            check('child names use imported PMLP data', all(c['first_name'] in names for c in registry['children']))
            check('child codes match valid birth dates', all(c['personas_kods'][:6] == date.fromisoformat(c['birth_date']).strftime('%d%m%y') for c in registry['children']))
            check('child inherits father surname or mother fallback', all(c['last_name'] in next((pair for pair in __import__('seed_people').SURNAMES if cases[c['father_id'] or c['mother_id']]['last_name'] in pair), (cases[c['father_id'] or c['mother_id']]['last_name'],)) for c in registry['children']))
            check('mother and father benefit fields seeded', any(b['mother_receiving'] for c in registry['children'] for b in c['benefits']) and any(b['father_receiving'] for c in registry['children'] for b in c['benefits']))
            check('separate registry databases exist', (Path(tmp)/'children.db').exists() and (Path(tmp)/'bank.db').exists())
            wrong_iban = __import__('demo_registry').make_iban(3)
            status, raw = call('/api/iban', 'POST', {'iban': wrong_iban}, token=token)
            check('IBAN belonging to another person rejected', status == 400 and json.loads(raw)['error'] == 'bank_account_unavailable')
            missing_iban = __import__('demo_registry').make_iban(900)
            status, raw = call('/api/iban', 'POST', {'iban': missing_iban}, token=token)
            check('valid but nonexistent IBAN rejected', status == 400 and json.loads(raw)['error'] == 'bank_account_unavailable')
            status, raw = call('/api/vsaa/profile', 'POST', {'iban':wrong_iban}, token=token)
            check('VSAA profile cannot bypass bank ownership', status == 400 and json.loads(raw)['error'] == 'bank_account_unavailable')

            # VSAA dashboard: scenarios, applications, notifications, reminders.
            status, _ = call('/api/vsaa/dashboard')
            check('dashboard requires authentication', status == 401)
            status, raw = call('/api/vsaa/dashboard', token=token)
            dash = json.loads(raw)['dashboard']
            check('person 2 has a newborn with six benefits', status == 200 and len(dash['children']) == 1 and len(dash['children'][0]['benefits']) == 6)
            child = dash['children'][0]
            available = [b['code'] for b in child['benefits'] if b['status'] in ('pieejams', 'steidzami')]
            check('newborn benefits are available but unclaimed', 'berna_piedzimsanas' in available and 'berna_kopsanas' in available)
            check('family state benefit waits for first birthday', next(b for b in child['benefits'] if b['code'] == 'gimenes_valsts')['status'] == 'gaidams')
            check('official service names are used', all(b['name'].endswith('piešķiršana un izmaksāšana') for b in child['benefits']))
            check('unpaid sick leave is listed with a deadline', any(l['status'] == 'neizmaksata' and l['deadline'] for l in dash['sickLeaves']))
            check('reminders cover unclaimed benefits', any(r['benefitCode'] == 'berna_piedzimsanas' for r in dash['reminders']))
            check('profile reports missing bank account', dash['person']['profileComplete'] is False)
            check('municipality resolved from address', bool(dash['person']['municipality']))

            status, raw = call('/api/vsaa/apply', 'POST', {'benefitCode': 'berna_piedzimsanas', 'childId': child['id'], 'iban': 'nope'}, token=token)
            check('application rejects a malformed IBAN', status == 400 and json.loads(raw)['error'] == 'invalid_iban')
            status, raw = call('/api/vsaa/apply', 'POST', {'benefitCode': 'berna_piedzimsanas', 'childId': child['id'], 'iban': __import__('demo_registry').make_iban(2)}, token=token)
            applied = json.loads(raw)['dashboard']
            check('application is accepted and status changes', status == 200 and next(b for b in applied['children'][0]['benefits'] if b['code'] == 'berna_piedzimsanas')['status'] == 'iesniegts')
            check('IBAN is stored on the profile', applied['person']['profileComplete'] and applied['person']['iban'] == __import__('demo_registry').make_iban(2))
            status, _ = call('/api/vsaa/apply', 'POST', {'benefitCode': 'berna_piedzimsanas', 'childId': child['id']}, token=token)
            check('same benefit cannot be applied twice', status == 400)
            _, raw = call('/api/messages', token=token)
            check('application confirmation lands in the inbox', any(m['subject'].startswith('Iesniegums saņemts') for m in json.loads(raw)['messages']))

            other_code = read_rows(db_path, 'SELECT personas_kods FROM people WHERE id = 5')[0][0]
            _, raw = call('/api/login', 'POST', {'personasKods': other_code})
            other_parent = json.loads(raw)['token']
            _, raw = call('/api/vsaa/dashboard', token=other_parent)
            other_dash = json.loads(raw)['dashboard']
            check('other parent sees the same child from their role', other_dash['children'] and other_dash['children'][0]['id'] == child['id'] and other_dash['children'][0]['myRole'] != child['myRole'])
            check('one-per-family benefit shows as claimed by the other parent', next(b for b in other_dash['children'][0]['benefits'] if b['code'] == 'berna_piedzimsanas')['status'] == 'nav_pieejams')
            status, raw = call('/api/vsaa/notify-other-parent', 'POST', {'childId': child['id']}, token=token)
            check('notification to the other parent is sent once per day', status == 200 and json.loads(raw)['notified'] is True)
            status, raw = call('/api/vsaa/notify-other-parent', 'POST', {'childId': child['id']}, token=token)
            check('repeat notification is reported, not duplicated', status == 200 and json.loads(raw)['notified'] is False)
            _, raw = call('/api/messages', token=other_parent)
            check('other parent receives the comparison message', any('Informācija par bērnu' in m['subject'] for m in json.loads(raw)['messages']))
            check('other parent details are not exposed', 'otherParent' not in child)

            status, raw = call('/api/vsaa/profile', 'POST', {'remindersEnabled': True}, token=token)
            check('enabling reminders delivers them to the inbox', status == 200 and json.loads(raw)['remindersDelivered'] >= 1)
            _, raw = call('/api/messages', token=token)
            check('reminder subjects are prefixed', any(m['subject'].startswith('Atgādinājums') for m in json.loads(raw)['messages']))

            unemployed_code = read_rows(db_path, 'SELECT personas_kods FROM people WHERE id = 4')[0][0]
            _, raw = call('/api/login', 'POST', {'personasKods': unemployed_code})
            unemployed = json.loads(raw)['token']
            _, raw = call('/api/vsaa/dashboard', token=unemployed)
            employment = json.loads(raw)['dashboard']['employment']
            check('contribution gap detected for scenario 0', employment['status'] == 'iemaksas_partrauktas' and employment['gapMonths'] == 2 and employment['benefitEligible'])
            status, raw = call('/api/vsaa/apply', 'POST', {'benefitCode': 'bezdarbnieka', 'iban': __import__('demo_registry').make_iban(4)}, token=unemployed)
            check('combined NVA + VSAA unemployment application', status == 200 and json.loads(raw)['dashboard']['employment']['status'] == 'bezdarbnieks')
            status, raw = call('/api/vsaa/vacancies', token=unemployed)
            vacancies = json.loads(raw)
            check('vacancies come from the NVA open-data snapshot', status == 200 and vacancies['total'] > 0 and vacancies['source'].startswith('https://data.gov.lv'))

            # --- Audit: benefit rules, eligibility, uniqueness, admin inbox, persistence ---------------
            legal_status, raw = call('/api/vsaa/legal')
            legal = json.loads(raw)
            check('legal references are public and dated', legal_status == 200 and legal['verifiedAt'] == '2026-10-09' and len(legal['benefits']) == 8)
            check('every benefit cites at least one law or regulation with a likumi.lv link', all(any(r['type'] in ('law', 'regulation') and r['url'].startswith('https://likumi.lv') for r in b['legal']) for b in legal['benefits'].values()))
            _, raw = call('/api/vsaa/dashboard', token=token)
            dash2 = json.loads(raw)['dashboard']
            newborn = dash2['children'][0]
            birth_amount = next(b for b in newborn['benefits'] if b['code'] == 'berna_piedzimsanas')['estimate']['oneTime']
            check('childbirth benefit for a 2026 birth is 600 EUR (MK 1546, 2. punkts)', birth_amount == 600)
            care = next(b for b in newborn['benefits'] if b['code'] == 'berna_kopsanas')['estimate']['schedule']
            check('childcare benefit is 298 EUR to 1.5 years with the 42.69 EUR transition', care[0]['monthly'] == 298 and care[1]['monthly'] == 42.69)
            check('maternity benefit is shown to the mother only', next(b for b in newborn['benefits'] if b['code'] == 'maternitates')['status'] != 'nav_attiecas' and newborn['myRole'] == 'māte')
            check('paternity benefit is marked as the other parent’s', next(b for b in newborn['benefits'] if b['code'] == 'paternitates')['status'] == 'nav_attiecas')
            check('legal citations travel with each benefit', all(b['legal'] and b['verifiedAt'] for b in newborn['benefits']))
            _, raw = call('/api/vsaa/dashboard', token=other_parent)
            father_dash = json.loads(raw)['dashboard']
            _, two_raw = call('/api/login','POST',{'personasKods':people[2][0]})
            two_token = json.loads(two_raw)['token']
            _, two_raw = call('/api/vsaa/dashboard',token=two_token)
            two_dash = json.loads(two_raw)['dashboard']
            older = next(c for c in two_dash['children'] if c['id'] == 2)
            check('father of two children sees both and the family benefit estimate counts two', len(two_dash['children']) == 2 and next(b for b in older['benefits'] if b['code'] == 'gimenes_valsts')['estimate']['children'] == 2)
            check('2025 birth keeps the 421.17 EUR childbirth amount', next(b for b in older['benefits'] if b['code'] == 'berna_piedzimsanas')['estimate']['oneTime'] == 421.17)
            check('paternity leave deadline (6 months) is reported as missed for the 11-month-old', next(b for b in older['benefits'] if b['code'] == 'paternitates')['status'] == 'nokavets')
            status, _ = call('/api/vsaa/apply', 'POST', {'benefitCode': 'paternitates', 'childId': older['id'], 'iban': father_dash['person']['iban'] or 'LV80BANK0000435195001'}, token=two_token)
            check('server refuses an application after the deadline even if the browser asks', status == 400)
            status, raw = call('/api/vsaa/apply', 'POST', {'benefitCode': 'vecaku', 'childId': newborn['id'], 'options': {'ilgums': '7 mēneši'}, 'iban': __import__('demo_registry').make_iban(2)}, token=token)
            check('invalid parental-benefit duration is rejected', status == 400 and json.loads(raw)['error'] == 'invalid_option')
            status, raw = call('/api/vsaa/apply', 'POST', {'benefitCode': 'vecaku', 'childId': newborn['id'], 'options': {'ilgums': '13 mēneši'}, 'iban': __import__('demo_registry').make_iban(2)}, token=token)
            check('mother applies for parental benefit (13 months)', status == 200)
            _, raw = call('/api/vsaa/dashboard', token=other_parent)
            kopsanas = next(b for b in next(c for c in json.loads(raw)['dashboard']['children'] if c['id'] == newborn['id'])['benefits'] if b['code'] == 'berna_kopsanas')
            check('childcare benefit follows the parental-benefit recipient (VSP likuma 7. panta otrā daļa)', kopsanas['status'] == 'nav_pieejams')
            concurrent_iban = father_dash['person']['iban']
            if not concurrent_iban:
                bank_connection = sqlite3.connect(Path(tmp) / 'bank.db')
                try:
                    concurrent_iban = bank_connection.execute(
                        'SELECT iban FROM accounts WHERE personas_kods=?', (other_code,)).fetchone()[0]
                finally:
                    bank_connection.close()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(lambda _: call('/api/vsaa/apply', 'POST', {'benefitCode': 'paternitates', 'childId': newborn['id'], 'iban': concurrent_iban}, token=other_parent)[0], range(6)))
            stored_count = read_rows(db_path, "SELECT count(*) FROM applications WHERE benefit_code = 'paternitates' AND child_id = ?", (newborn['id'],))[0][0]
            check('concurrent duplicate submissions store a single application', stored_count == 1 and results.count(200) == 1, str(results))
            # Restore the father's profile (the demo panel action) so later isolation checks start clean.
            status, _ = call('/api/demo/people/5/clear-iban', 'POST',token=demo_admin_token)
            _, raw = call('/api/me', token=other_parent)
            check('demo panel clears the IBAN the father saved while applying', status == 200 and json.loads(raw)['person']['iban'] is None)
            status, _ = call('/api/admin/applications')
            check('admin inbox requires authentication (401)', status == 401)
            status, _ = call('/api/admin/applications', token=token)
            check('admin inbox refuses ordinary users (403)', status == 403)
            status, raw = call('/api/login', 'POST', {'personasKods': admin_row[0][0]})
            admin_token = json.loads(raw)['token']
            check('administrator login reports the admin role', status == 200 and json.loads(raw)['person']['role'] == 'admin')
            status, _ = call('/api/vsaa/dashboard', token=admin_token)
            check('administrator has no personal dashboard (403)', status == 403)
            status, raw = call('/api/admin/applications', token=admin_token)
            register = json.loads(raw)
            submitted = [a for a in register['applications'] if a['status'] == 'iesniegts' and not a['seeded']]
            check('admin inbox lists persisted applications with applicant and child', status == 200 and submitted and all(a['applicant']['personasKods'] and (a['child'] or a['sickLeave'] or a['benefitCode'] == 'bezdarbnieka') for a in submitted))
            target = next(a for a in submitted if a['benefitCode'] == 'vecaku')
            check('stored application keeps the chosen option', target['details'].get('ilgums') == '13 mēneši')
            status, raw = call(f"/api/admin/applications/{target['id']}/status", 'POST', {'status': 'pieskirts'}, token=admin_token)
            decided = next(a for a in json.loads(raw)['applications'] if a['id'] == target['id'])
            check('administrator decision is persisted', status == 200 and decided['status'] == 'pieskirts' and decided['decidedAt'])
            status, _ = call(f"/api/admin/applications/{target['id']}/status", 'POST', {'status': 'nonsense'}, token=admin_token)
            check('invalid decision status rejected', status == 400)
            _, raw = call('/api/messages', token=token)
            decision_mail = [m for m in json.loads(raw)['messages'] if m['template'] == 'decision']
            check('applicant receives the decision in the inbox with a template', decision_mail and decision_mail[0]['params']['status'] == 'pieskirts' and decision_mail[0]['readAt'] is None)
            _, raw = call('/api/vsaa/dashboard', token=token)
            check('decision is consistent on the applicant dashboard', next(b for b in json.loads(raw)['dashboard']['children'][0]['benefits'] if b['code'] == 'vecaku')['status'] == 'pieskirts')
            status, raw = call('/api/login', 'POST', {'personasKods': code}, token=token)
            switched = json.loads(raw)['token']
            status2, _ = call('/api/me', token=token)
            check('logging in again revokes the previous token', status == 200 and status2 == 401)
            token = switched
            # Restart the server with the same database: everything must survive.
            server.terminate(); server.wait(timeout=5)
            server = subprocess.Popen([sys.executable, str(HERE / 'app.py')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            for _ in range(50):
                try:
                    call('/api/me'); break
                except Exception:
                    time.sleep(0.1)
            status, raw = call('/api/admin/applications', token=admin_token)
            check('applications and sessions persist across a server restart', status == 200 and any(a['id'] == target['id'] and a['status'] == 'pieskirts' for a in json.loads(raw)['applications']))
            with_children = sqlite3.connect(db_path)
            with_children.execute('ATTACH DATABASE ? AS family', (os.path.join(tmp, 'children.db'),))
            check('restart does not duplicate seeded data', with_children.execute('SELECT count(*) FROM family.children').fetchone()[0] == 4 and with_children.execute("SELECT count(*) FROM people WHERE role = 'admin'").fetchone()[0] == 1)
            with_children.close()

            status, _ = call('/api/iban', 'POST', {'iban': 'LV00TEST0000000000001'})
            check('IBAN requires authentication', status == 401)
            status, _ = call('/api/iban', 'POST', {'iban': 'LV00TEST0000000000001'}, token=token)
            check('invalid IBAN checksum rejected', status == 400)
            bban = 'TEST0000000000001'
            numeric = ''.join(str(ord(char) - 55) if char.isalpha() else char for char in bban + 'LV00')
            iban = __import__('demo_registry').make_iban(2)
            status, raw = call('/api/iban', 'POST', {'iban': iban.lower()}, token=token)
            check('valid demo IBAN saved and normalized', status == 200 and json.loads(raw)['person']['iban'] == iban)
            _, raw = call('/api/me', token=token)
            check('IBAN persists in profile', json.loads(raw)['person']['iban'] == iban)
            _, raw = call('/api/me', token=other_token)
            check('IBAN update isolated to current user', json.loads(raw)['person']['iban'] is None)

            bank_conn = sqlite3.connect(Path(tmp)/'bank.db')
            bank_conn.execute('UPDATE accounts SET active = 0 WHERE iban = ?', (iban,))
            bank_conn.commit()
            status, raw = call('/api/iban', 'POST', {'iban':iban}, token=token)
            check('inactive bank account rejected', status == 400 and json.loads(raw)['error'] == 'bank_account_unavailable')
            bank_conn.execute('UPDATE accounts SET active = 1 WHERE iban = ?', (iban,))
            bank_conn.commit(); bank_conn.close()
            from seed_people import connect, ensure_seeded
            seeded = connect(db_path)
            try:
                with seeded:
                    ensure_seeded(seeded)
                    check('reseeding preserves four children', seeded.execute('SELECT count(*) FROM family.children').fetchone()[0] == 4)
                    check('reseeding retains saved IBAN', seeded.execute('SELECT iban FROM people WHERE id = 2').fetchone()[0] == iban)
            finally:
                seeded.close()

            status, _ = call('/api/demo/people/2/clear-iban','POST',token=admin_token)
            check('demo panel clears saved IBAN', status == 200)
            _, raw = call('/api/me',token=token)
            check('cleared IBAN visible in profile',json.loads(raw)['person']['iban'] is None)
            bank = sqlite3.connect(Path(tmp)/'bank.db')
            check('clearing profile keeps mock bank account',bank.execute('SELECT count(*) FROM accounts WHERE iban = ?',(iban,)).fetchone()[0] == 1)
            bank.close()
            status, _ = call('/api/demo/people/999999/clear-iban','POST',token=admin_token)
            check('unknown demo person rejected',status == 404)

            stored = [row[0] for row in read_rows(db_path, 'SELECT token_hash FROM sessions')]
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
