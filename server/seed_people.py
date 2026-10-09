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
import demo_registry

DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'people.db'
DEFAULT_COUNT = 4
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
    # Account role: 'person' (portal user) or 'admin' (VSAA demo administrator inbox).
    if 'role' not in columns:
        connection.execute("ALTER TABLE people ADD COLUMN role TEXT NOT NULL DEFAULT 'person'")
        connection.commit()
    message_columns = {row['name'] for row in connection.execute('PRAGMA table_info(messages)')}
    if 'template' not in message_columns:
        # Template key + JSON params let the interface render system messages in either language.
        connection.execute('ALTER TABLE messages ADD COLUMN template TEXT')
        connection.execute("ALTER TABLE messages ADD COLUMN params TEXT NOT NULL DEFAULT '{}'")
        connection.commit()
    application_columns = {row['name'] for row in connection.execute('PRAGMA table_info(applications)')}
    if 'decided_at' not in application_columns:
        connection.execute('ALTER TABLE applications ADD COLUMN decided_at TEXT')
        connection.commit()
    # Uniqueness: one application per person, benefit and child/certificate, and one per family for
    # the child benefits the law grants to a single parent. Pre-existing duplicates (older demo
    # databases) are collapsed to the earliest row before the indexes are created.
    connection.executescript('''
        DELETE FROM applications WHERE id NOT IN (
          SELECT MIN(id) FROM applications GROUP BY person_id, benefit_code, COALESCE(child_id, 0), COALESCE(sick_leave_id, 0));
        DELETE FROM applications WHERE child_id IS NOT NULL AND benefit_code IN ('berna_piedzimsanas', 'berna_kopsanas', 'vecaku', 'gimenes_valsts')
          AND status != 'atteikts' AND id NOT IN (
          SELECT MIN(id) FROM applications WHERE child_id IS NOT NULL AND status != 'atteikts' GROUP BY benefit_code, child_id);
        CREATE UNIQUE INDEX IF NOT EXISTS applications_unique_person
          ON applications(person_id, benefit_code, COALESCE(child_id, 0), COALESCE(sick_leave_id, 0));
        CREATE UNIQUE INDEX IF NOT EXISTS applications_unique_family
          ON applications(benefit_code, child_id)
          WHERE child_id IS NOT NULL AND status != 'atteikts' AND benefit_code IN ('berna_piedzimsanas', 'berna_kopsanas', 'vecaku', 'gimenes_valsts');
    ''')
    demo_registry.attach(connection, path)
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
    """Seed fictional employment and sick-leave cases; families live in children.db."""
    today = today or date.today()
    with connection:
        for person in connection.execute("SELECT id FROM people WHERE role = 'person'").fetchall():
            pid = person['id']
            rng = random.Random(DEFAULT_SEED * 7 + pid)
            employer = EMPLOYERS[pid % len(EMPLOYERS)]
            wage = 900 + rng.randrange(0, 1500)
            gap = 2 if pid % 4 == 0 else 0
            for back in range(1, 25):
                if back > gap:
                    connection.execute('INSERT OR IGNORE INTO contributions (person_id,month,employer,amount) VALUES (?, ?, ?, ?)',
                                       (pid,month_key(today,back),employer,round(wage * 0.3409,2)))


# Fictional VSAA administrator for the demo application inbox (no bank account, no benefits).
ADMIN_ACCOUNT = ('Ilze', 'Vētra', '150975-10001', 'ilze.vetra@example.com', '+371 20 000 001', 'VSAA demonstrācijas nodaļa, Rīga', '1975-09-15')


def ensure_admin(connection):
    with connection:
        connection.execute("INSERT OR IGNORE INTO people (first_name, last_name, personas_kods, email, phone, address, birth_date, role) VALUES (?, ?, ?, ?, ?, ?, ?, 'admin')", ADMIN_ACCOUNT)
        connection.execute("UPDATE people SET role = 'admin' WHERE personas_kods = ?", (ADMIN_ACCOUNT[2],))


def ensure_seeded(connection):
    if connection.execute('SELECT COUNT(*) FROM people').fetchone()[0] == 0:
        seed(connection)
    ensure_admin(connection)
    seed_vsaa_cases(connection)
    demo_registry.seed_registries(connection)


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
            connection.execute('DELETE FROM family.children')
            connection.execute('DELETE FROM family.metadata')
            connection.execute('DELETE FROM bank.accounts')
            connection.execute('DELETE FROM bank.people')
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
            label = 'VSAA administrators (iesniegumu reģistrs)' if row['role'] == 'admin' else demo_registry.CASES.get(row['id'], 'papildu demo lietotājs')
            print(f"{row['personas_kods']}  {row['first_name']} {row['last_name']:<14} {row['email']:<34} {row['phone']}  {label}")


if __name__ == '__main__':
    main()
