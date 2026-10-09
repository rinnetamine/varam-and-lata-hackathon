#!/usr/bin/env python3
"""Fictional Latvian people for the Faketvija demo database.

People and their associations with addresses are invented. Addresses come from
the imported VZD open-data snapshot, not residents records. Names are randomly
combined, e-mail addresses use
the reserved example.com domain, and phone numbers are random. Personas kodi
use DDMMYY-XXXXX with fictional birth dates and random five-digit suffixes. They are demo identifiers only: a random code
or number can still coincide with a real one, so never treat these as real.

Usage:
    python3 server/seed_people.py --list     # show the people in the database
    python3 server/seed_people.py --reset    # drop and regenerate the people
"""
import argparse
import json
import os
import random
import sqlite3
import unicodedata
from pathlib import Path
from datetime import date, timedelta

DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'people.db'
DEFAULT_COUNT = 60
DEFAULT_SEED = 20240601
ADDRESS_FILE = Path(os.environ.get('ADDRESS_FILE', Path(__file__).resolve().parent.parent / 'public' / 'data' / 'addresses.json'))

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  personas_kods TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL UNIQUE,
  address TEXT NOT NULL,
  birth_date TEXT NOT NULL,
  iban TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expires_at ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  seed_key TEXT NOT NULL,
  sender TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  received_at TEXT NOT NULL,
  read_at INTEGER,
  UNIQUE(person_id, seed_key)
);
CREATE INDEX IF NOT EXISTS messages_person ON messages(person_id, received_at);
CREATE TABLE IF NOT EXISTS children (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT NOT NULL,
  birth_date TEXT NOT NULL,
  seed_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS child_parents (
  child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  PRIMARY KEY (child_id, person_id)
);
CREATE TABLE IF NOT EXISTS sick_leaves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  number TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,
  date_from TEXT NOT NULL,
  date_to TEXT NOT NULL,
  closed_at TEXT,
  employer TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contributions (
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  month TEXT NOT NULL,
  employer TEXT NOT NULL,
  amount REAL NOT NULL,
  PRIMARY KEY (person_id, month)
);
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  benefit_code TEXT NOT NULL,
  child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
  sick_leave_id INTEGER REFERENCES sick_leaves(id) ON DELETE CASCADE,
  submitted_at TEXT NOT NULL,
  status TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS applications_person ON applications(person_id, benefit_code);

"""

# Fictional employers for the contribution history; no real company is meant.
EMPLOYERS = ['SIA "Demo Būve"', 'AS "Demo Enerģija"', 'SIA "Demo Loģistika"', 'Demo pašvaldības iestāde',
             'SIA "Demo Veselība"', 'SIA "Demo Tirdzniecība"']
CHILD_NAMES = ['Marta', 'Emīlija', 'Alise', 'Sofija', 'Roberts', 'Gustavs', 'Jēkabs', 'Oskars']

MALE_NAMES = [
    'Jānis', 'Andris', 'Mārtiņš', 'Edgars', 'Kristaps', 'Raimonds', 'Artūrs', 'Normunds',
    'Aigars', 'Gatis', 'Ilgvars', 'Roberts', 'Rihards', 'Valdis', 'Uldis', 'Ēriks', 'Dāvis',
    'Toms', 'Kārlis', 'Pēteris', 'Imants', 'Guntis', 'Māris', 'Oskars', 'Arnis',
]
FEMALE_NAMES = [
    'Anna', 'Līga', 'Inese', 'Ilze', 'Dace', 'Sanita', 'Kristīne', 'Laura', 'Evija', 'Zane',
    'Baiba', 'Agnese', 'Elīna', 'Marta', 'Santa', 'Linda', 'Gunta', 'Ieva', 'Madara', 'Iveta',
    'Daina', 'Sandra', 'Anita', 'Liene', 'Una',
]
# (masculine, feminine) forms of common Latvian surnames.
SURNAMES = [
    ('Bērziņš', 'Bērziņa'), ('Kalniņš', 'Kalniņa'), ('Ozoliņš', 'Ozoliņa'),
    ('Liepiņš', 'Liepiņa'), ('Krūmiņš', 'Krūmiņa'), ('Jansons', 'Jansone'),
    ('Pētersons', 'Pētersone'), ('Ozols', 'Ozola'), ('Vītols', 'Vītola'),
    ('Balodis', 'Balode'), ('Eglītis', 'Eglīte'), ('Zariņš', 'Zariņa'),
    ('Siliņš', 'Siliņa'), ('Kļaviņš', 'Kļaviņa'), ('Lapiņš', 'Lapiņa'),
    ('Rozītis', 'Rozīte'), ('Priedītis', 'Priedīte'), ('Kazaks', 'Kazaka'),
    ('Zvirbulis', 'Zvirbule'), ('Vanags', 'Vanaga'), ('Grīnbergs', 'Grīnberga'),
    ('Dzenis', 'Dzene'), ('Melnis', 'Melne'), ('Circenis', 'Circene'),
    ('Strazdiņš', 'Strazdiņa'), ('Žukovskis', 'Žukovska'), ('Āboliņš', 'Āboliņa'),
    ('Lācis', 'Lāce'), ('Purviņš', 'Purviņa'), ('Skujiņš', 'Skujiņa'),
]


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript(SCHEMA)
    # Migrate existing demo databases without resetting people or sessions.
    columns = {row['name'] for row in connection.execute('PRAGMA table_info(people)')}
    if 'address' not in columns:
        connection.execute("ALTER TABLE people ADD COLUMN address TEXT NOT NULL DEFAULT ''")
    with connection:
        for row in connection.execute("SELECT id FROM people WHERE address = ''").fetchall():
            connection.execute('UPDATE people SET address = ? WHERE id = ?',
                               (demo_address(row['id']), row['id']))
    # Upgrade only generated placeholder addresses; preserve existing user data.
    with connection:
        for row in connection.execute("SELECT id FROM people WHERE address LIKE 'Demonstrācijas iela %'").fetchall():
            connection.execute('UPDATE people SET address = ? WHERE id = ?',
                               (demo_address(row['id']), row['id']))
    if 'birth_date' not in columns:
        connection.execute("ALTER TABLE people ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''")
    # VSAA dashboard profile fields: bank account for payouts, reminder opt-in, NVA status.
    if 'reminders_enabled' not in columns:
        connection.execute("ALTER TABLE people ADD COLUMN reminders_enabled INTEGER NOT NULL DEFAULT 0")
    if 'nva_registered' not in columns:
        connection.execute("ALTER TABLE people ADD COLUMN nva_registered INTEGER NOT NULL DEFAULT 0")
    with connection:
        used = {row[0] for row in connection.execute('SELECT personas_kods FROM people')}
        for row in connection.execute("SELECT id FROM people WHERE birth_date = ''").fetchall():
            rng = random.Random(DEFAULT_SEED + row['id'])
            birth, code = demo_identity(rng)
            while code in used:
                birth, code = demo_identity(rng)
            used.add(code)
            connection.execute('UPDATE people SET birth_date = ?, personas_kods = ? WHERE id = ?',
                               (birth.isoformat(), code, row['id']))
    if 'iban' not in columns:
        connection.execute('ALTER TABLE people ADD COLUMN iban TEXT')
        connection.commit()
    return connection


def demo_identity(rng):
    start, end = date(1970, 1, 1), date(2006, 12, 31)
    birth = start + timedelta(days=rng.randrange((end - start).days + 1))
    return birth, f'{birth:%d%m%y}-{rng.randrange(100000):05d}'


def demo_address(index):
    if not ADDRESS_FILE.is_file():
        raise FileNotFoundError(f'Imported address snapshot is required: {ADDRESS_FILE}')
    records = json.loads(ADDRESS_FILE.read_text(encoding='utf-8'))['addresses']
    if not records:
        raise ValueError('Imported address snapshot contains no addresses')
    # A separate deterministic RNG keeps existing demo personas kodi unchanged.
    return random.Random(DEFAULT_SEED + index).choice(records)['label']


def ascii_fold(text):
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in decomposed if not unicodedata.combining(char)).lower()


def generate_people(count, seed):
    rng = random.Random(seed)
    people = []
    codes, emails, phones = set(), set(), set()
    while len(people) < count:
        is_female = rng.random() < 0.5
        first = rng.choice(FEMALE_NAMES if is_female else MALE_NAMES)
        last = rng.choice(SURNAMES)[1 if is_female else 0]

        birth, code = demo_identity(rng)
        local = f'{ascii_fold(first)}.{ascii_fold(last)}'
        email = f'{local}@example.com'
        suffix = 1
        while email in emails:
            suffix += 1
            email = f'{local}{suffix}@example.com'
        number = f'2{rng.randrange(10000000):07d}'
        phone = f'+371 {number[:2]} {number[2:5]} {number[5:]}'
        if code in codes or phone in phones:
            continue

        codes.add(code)
        emails.add(email)
        phones.add(phone)
        people.append((first, last, code, email, phone, demo_address(len(people) + 1), birth.isoformat()))
    return people


def seed(connection, count=DEFAULT_COUNT, seed_value=DEFAULT_SEED):
    with connection:
        connection.executemany(
            'INSERT INTO people (first_name, last_name, personas_kods, email, phone, address, birth_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
            generate_people(count, seed_value),
        )


def month_key(day, months_back):
    month = day.month - 1 - months_back
    return f'{day.year + month // 12}-{month % 12 + 1:02d}'


def seed_vsaa_cases(connection, today=None):
    """Create the fictional VSAA situations behind the dashboard.

    Scenario by person id (1-based): 1 newborn plus an unpaid sick-leave
    certificate, 2 the other parent of that newborn, 3 a child approaching
    its first birthday with granted benefits, 0 social contributions stopped
    two months ago (unemployment). Everything is idempotent via seed keys, so
    an existing demo database gains the tables without losing people,
    sessions or read status.
    """
    today = today or date.today()
    if connection.execute('SELECT COUNT(*) FROM children').fetchone()[0]:
        return
    people = connection.execute('SELECT id, first_name FROM people ORDER BY id').fetchall()
    if not people:
        return
    partners = [row for row in people if row['id'] % 4 == 2]
    used = set()

    def pick_partner(person):
        female = person['first_name'] in FEMALE_NAMES
        for candidate in partners:
            if candidate['id'] in used or candidate['id'] <= person['id']:
                continue
            if (candidate['first_name'] in FEMALE_NAMES) != female:
                used.add(candidate['id'])
                return candidate
        for candidate in partners:
            if candidate['id'] not in used and candidate['id'] > person['id']:
                used.add(candidate['id'])
                return candidate
        return None

    with connection:
        for person in people:
            pid = person['id']
            rng = random.Random(DEFAULT_SEED * 7 + pid)
            scenario = pid % 4
            employer = EMPLOYERS[pid % len(EMPLOYERS)]
            wage = 900 + rng.randrange(0, 1500)
            gap = 2 if scenario == 0 else 0
            for back in range(1, 17):
                if back > gap:
                    connection.execute('INSERT OR IGNORE INTO contributions (person_id, month, employer, amount) VALUES (?, ?, ?, ?)',
                                       (pid, month_key(today, back), employer, round(wage * 0.3409, 2)))
            role = 'māte' if person['first_name'] in FEMALE_NAMES else 'tēvs'
            if scenario == 1:
                birth = today - timedelta(days=18)
                child = connection.execute('INSERT OR IGNORE INTO children (first_name, birth_date, seed_key) VALUES (?, ?, ?)',
                                           (CHILD_NAMES[pid % len(CHILD_NAMES)], birth.isoformat(), f'child-{pid}')).lastrowid
                connection.execute('INSERT OR IGNORE INTO child_parents VALUES (?, ?, ?)', (child, pid, role))
                partner = pick_partner(person)
                if partner:
                    partner_role = 'māte' if partner['first_name'] in FEMALE_NAMES else 'tēvs'
                    if partner_role == role:
                        partner_role = 'tēvs' if role == 'māte' else 'māte'
                    connection.execute('INSERT OR IGNORE INTO child_parents VALUES (?, ?, ?)', (child, partner['id'], partner_role))
                # Maternity benefit was granted before the birth; it shows as already granted.
                mother = pid if role == 'māte' else (partner['id'] if partner else None)
                if mother:
                    connection.execute('INSERT INTO applications (person_id, benefit_code, child_id, submitted_at, status, details) VALUES (?, ?, ?, ?, ?, ?)',
                                       (mother, 'maternitates', child, (birth - timedelta(days=60)).isoformat(), 'pieskirts', '{"seed": true}'))
                connection.execute('INSERT OR IGNORE INTO sick_leaves (person_id, number, kind, date_from, date_to, closed_at, employer, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                   (pid, f'B-{today.year}-{pid:04d}-2', 'B', (today - timedelta(days=41)).isoformat(), (today - timedelta(days=25)).isoformat(), (today - timedelta(days=24)).isoformat(), employer, 'neizmaksata'))
                connection.execute('INSERT OR IGNORE INTO sick_leaves (person_id, number, kind, date_from, date_to, closed_at, employer, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                   (pid, f'B-{today.year}-{pid:04d}-1', 'B', (today - timedelta(days=200)).isoformat(), (today - timedelta(days=186)).isoformat(), (today - timedelta(days=185)).isoformat(), employer, 'izmaksata'))
            elif scenario == 3:
                birth = today - timedelta(days=335)
                child = connection.execute('INSERT OR IGNORE INTO children (first_name, birth_date, seed_key) VALUES (?, ?, ?)',
                                           (CHILD_NAMES[(pid + 3) % len(CHILD_NAMES)], birth.isoformat(), f'child-{pid}')).lastrowid
                connection.execute('INSERT OR IGNORE INTO child_parents VALUES (?, ?, ?)', (child, pid, role))
                granted = [('berna_piedzimsanas', 12, '{"seed": true}'), ('berna_kopsanas', 20, '{"seed": true}'), ('vecaku', 20, '{"seed": true, "ilgums": "13 mēneši"}'),
                           ('paternitates', 15, '{"seed": true}') if role == 'tēvs' else ('maternitates', -60, '{"seed": true}')]
                for code, offset, details in granted:
                    connection.execute('INSERT INTO applications (person_id, benefit_code, child_id, submitted_at, status, details) VALUES (?, ?, ?, ?, ?, ?)',
                                       (pid, code, child, (birth + timedelta(days=offset)).isoformat(), 'pieskirts', details))
                connection.execute('INSERT OR IGNORE INTO sick_leaves (person_id, number, kind, date_from, date_to, closed_at, employer, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                   (pid, f'B-{today.year}-{pid:04d}-1', 'B', (today - timedelta(days=19)).isoformat(), (today - timedelta(days=6)).isoformat(), (today - timedelta(days=5)).isoformat(), employer, 'neizmaksata'))


def ensure_seeded(connection):
    if connection.execute('SELECT COUNT(*) FROM people').fetchone()[0] == 0:
        seed(connection)
    with connection:
        connection.execute("""
            INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at)
            SELECT id, 'newborn-demo', 'FAKETVIJA.LV · DEMONSTRĀCIJA',
              'Par bērna piedzimšanu ir pieejami pakalpojumi',
              'Ar bērna piedzimšanu saistītie pakalpojumi ir apkopoti vienuviet. Izdomāts ziņojums hakatona prototipam.',
              '2026-10-09T09:00:00+03:00' FROM people WHERE id % 4 != 0
        """)
    seed_vsaa_cases(connection)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', default=str(DEFAULT_DB), help='SQLite file (default: %(default)s)')
    parser.add_argument('--count', type=int, default=DEFAULT_COUNT)
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED, help='random seed, same seed gives same people')
    parser.add_argument('--reset', action='store_true', help='delete existing people and sessions, then regenerate')
    parser.add_argument('--list', action='store_true', help='print the people')
    args = parser.parse_args()

    connection = connect(args.db)
    if args.reset:
        with connection:
            connection.execute('DELETE FROM sessions')
            connection.execute('DELETE FROM children')
            connection.execute('DELETE FROM people')
        seed(connection, args.count, args.seed)
        ensure_seeded(connection)
        print(f'Regenerated {args.count} people in {args.db}')
    else:
        ensure_seeded(connection)

    if args.list:
        scenarios = {1: 'jaundzimušais + slimības lapa', 2: 'otrs vecāks', 3: 'bērns tuvojas 1 gadam', 0: 'iemaksas pārtrauktas'}
        for row in connection.execute('SELECT * FROM people ORDER BY id'):
            print(f"{row['personas_kods']}  {row['first_name']} {row['last_name']:<14} {row['email']:<34} {row['phone']}  {scenarios[row['id'] % 4]}")


if __name__ == '__main__':
    main()
