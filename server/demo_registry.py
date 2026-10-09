"""Separate fictional family and bank registries. No real bank or residents API."""
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

NAME_FILE = Path(os.environ.get('NAME_FILE', Path(__file__).resolve().parent.parent/'public/data/person-names.json'))
CASES = {1:'Nav bērnu', 2:'Viens jaundzimušais, divi vecāki', 3:'Divi bērni, daļa pabalstu jau piešķirta', 4:'Viens bērns, tēvs nav norādīts'}
CHILD_BENEFITS = ('berna_piedzimsanas','berna_kopsanas','vecaku','gimenes_valsts','maternitates','paternitates')

def attach(db, people_path):
    folder = Path(people_path).resolve().parent
    db.execute('ATTACH DATABASE ? AS family', (str(folder/'children.db'),))
    db.execute('ATTACH DATABASE ? AS bank', (str(folder/'bank.db'),))
    db.executescript('''
    CREATE TABLE IF NOT EXISTS family.children (
      id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
      personas_kods TEXT NOT NULL UNIQUE, birth_date TEXT NOT NULL, seed_key TEXT NOT NULL UNIQUE,
      mother_id INTEGER, father_id INTEGER, CHECK(mother_id IS NOT NULL OR father_id IS NOT NULL));
    CREATE TABLE IF NOT EXISTS family.benefits (
      child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, benefit_code TEXT NOT NULL,
      mother_receiving INTEGER NOT NULL DEFAULT 0 CHECK(mother_receiving IN (0,1)),
      father_receiving INTEGER NOT NULL DEFAULT 0 CHECK(father_receiving IN (0,1)),
      PRIMARY KEY(child_id, benefit_code));
    CREATE VIEW IF NOT EXISTS family.child_parents AS
      SELECT id AS child_id, mother_id AS person_id, 'māte' AS role FROM children WHERE mother_id IS NOT NULL
      UNION ALL SELECT id, father_id, 'tēvs' FROM children WHERE father_id IS NOT NULL;
    CREATE TABLE IF NOT EXISTS family.metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS bank.people (personas_kods TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS bank.accounts (
      iban TEXT PRIMARY KEY, personas_kods TEXT NOT NULL REFERENCES people(personas_kods), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
    ''')

def make_iban(index):
    bban = f'TEST{index:013d}'
    digits = ''.join(str(ord(c)-55) if c.isalpha() else c for c in bban+'LV00')
    return f'LV{98-int(digits)%97:02d}{bban}'

def bank_error(db, code, iban):
    row = db.execute('SELECT * FROM bank.accounts WHERE iban = ?', (iban,)).fetchone()
    if not row or not row['active']:
        return 'bank_account_unavailable'
    if row['personas_kods'] != code:
        return 'bank_account_unavailable'
    return None

def seed_registries(db, today=None):
    today = today or date.today()
    with db:
        db.execute('DELETE FROM bank.accounts WHERE personas_kods NOT IN (SELECT personas_kods FROM main.people WHERE id <= 4)')
        db.execute('DELETE FROM bank.people WHERE personas_kods NOT IN (SELECT personas_kods FROM main.people WHERE id <= 4)')
        db.execute("DELETE FROM main.people WHERE id > 4 AND role = 'person'")
    people = {r['id']:r for r in db.execute("SELECT * FROM people WHERE role = 'person'")}
    with db:
        for pid, person in people.items():
            db.execute('INSERT OR IGNORE INTO bank.people VALUES (?, ?, ?)', (person['personas_kods'],person['first_name'],person['last_name']))
            db.execute('INSERT OR IGNORE INTO bank.accounts (iban, personas_kods) VALUES (?, ?)', (make_iban(pid), person['personas_kods']))
        if db.execute("SELECT 1 FROM family.metadata WHERE key = 'showcase-v2-four-users'").fetchone():
            return
        # Replace repetitive old fictional family scenarios, retaining people and sessions.
        db.execute('DELETE FROM family.children')
        db.execute('DELETE FROM children')
        db.execute("DELETE FROM messages WHERE seed_key LIKE 'newborn-demo' OR seed_key LIKE 'reminder-%' OR seed_key LIKE 'share-%'")
        names = json.loads(NAME_FILE.read_text())['names']
        definitions = [(1,2,3,18), (2,None,3,335), (3,4,None,40)]
        for cid, mother, father, days in definitions:
            if (mother is not None and mother not in people) or (father is not None and father not in people):
                continue
            birth = today - timedelta(days=days)
            first = names[cid*7]['name']
            surname = people[father if father is not None else mother]['last_name']
            code = f'{birth:%d%m%y}-{random.Random(8100+cid).randrange(100000):05d}'
            db.execute('INSERT INTO family.children VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (cid,first,surname,code,birth.isoformat(),f'showcase-{cid}',mother,father))
            # Compatibility IDs only: applications retain their existing SQLite FK.
            db.execute('INSERT INTO main.children (id,first_name,birth_date,seed_key) VALUES (?, ?, ?, ?)', (cid,first,birth.isoformat(),f'showcase-{cid}'))
            for benefit in CHILD_BENEFITS:
                mom_receiving = int(cid == 1 and benefit == 'maternitates')
                dad_receiving = int(cid == 2 and benefit in ('berna_piedzimsanas','berna_kopsanas','vecaku'))
                db.execute('INSERT INTO family.benefits VALUES (?, ?, ?, ?)', (cid,benefit,mom_receiving,dad_receiving))
                for pid, receiving in ((mother,mom_receiving),(father,dad_receiving)):
                    if receiving and pid is not None:
                        db.execute('INSERT INTO applications (person_id,benefit_code,child_id,submitted_at,status,details) VALUES (?, ?, ?, ?, ?, ?)',
                                   (pid,benefit,cid,(birth+timedelta(days=10)).isoformat(),'pieskirts','{"seed":true}'))
        if 2 in people:
            db.execute('INSERT OR IGNORE INTO sick_leaves (person_id,number,kind,date_from,date_to,closed_at,employer,status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (2,f'B-{today.year}-SHOWCASE','B',(today-timedelta(days=41)).isoformat(),(today-timedelta(days=25)).isoformat(),(today-timedelta(days=24)).isoformat(),'SIA "Demo Būve"','neizmaksata'))
        # Only parents receive the seeded child-service notification.
        db.execute('''INSERT OR IGNORE INTO messages (person_id,seed_key,sender,subject,body,received_at)
                    SELECT DISTINCT person_id,'newborn-demo','FAKETVIJA.LV · DEMONSTRĀCIJA',
                    'Par bērna piedzimšanu ir pieejami pakalpojumi',
                    'Ar bērna piedzimšanu saistītie pakalpojumi ir apkopoti vienuviet. Izdomāts ziņojums hakatona prototipam.',
                    ? FROM family.child_parents''', (today.isoformat()+'T09:00:00+03:00',))
        # Existing arbitrary IBANs must pass the new mock-bank ownership check.
        db.execute('UPDATE people SET iban = NULL WHERE iban IS NOT NULL AND NOT EXISTS '
                   '(SELECT 1 FROM bank.accounts WHERE accounts.iban = people.iban AND accounts.personas_kods = people.personas_kods AND active = 1)')
        db.execute("INSERT INTO family.metadata VALUES ('showcase-v2-four-users', ?)", (today.isoformat(),))

def admin_data(db):
    children = [dict(r) for r in db.execute('SELECT * FROM family.children ORDER BY id')]
    for child in children:
        child['benefits'] = [dict(r) for r in db.execute('SELECT * FROM family.benefits WHERE child_id = ?', (child['id'],))]
        child['applications'] = [dict(r) for r in db.execute('SELECT person_id, benefit_code, status FROM applications WHERE child_id = ?', (child['id'],))]
    people = []
    for row in db.execute('SELECT * FROM people ORDER BY id'):
        person = dict(row)
        person['scenario'] = 'VSAA administrators (iesniegumu reģistrs)' if row['role'] == 'admin' else CASES.get(row['id'], 'Otrs vecāks' if row['id'] in (5,8) else 'Papildu demo lietotājs bez bērniem')
        person['children'] = [c for c in children if row['id'] in (c['mother_id'],c['father_id'])]
        person['bankAccounts'] = [dict(r) for r in db.execute('SELECT * FROM bank.accounts WHERE personas_kods = ?', (row['personas_kods'],))]
        people.append(person)
    return {'people':people, 'children':children, 'demoOnly':True}
