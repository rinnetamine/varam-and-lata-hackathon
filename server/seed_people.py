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
  birth_date TEXT NOT NULL
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

"""

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


def ensure_seeded(connection):
    if connection.execute('SELECT COUNT(*) FROM people').fetchone()[0] == 0:
        seed(connection)
    with connection:
        connection.execute("""
            INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at)
            SELECT id, 'newborn-demo', 'FAKETVIJA.LV · DEMONSTRĀCIJA',
              'Par bērna piedzimšanu ir pieejami pakalpojumi',
              'Ar bērna piedzimšanu saistītie pakalpojumi ir apkopoti vienuviet. Izdomāts ziņojums hakatona prototipam.',
              '2026-10-09T09:00:00+03:00' FROM people
        """)


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
            connection.execute('DELETE FROM people')
        seed(connection, args.count, args.seed)
        ensure_seeded(connection)
        print(f'Regenerated {args.count} people in {args.db}')
    else:
        ensure_seeded(connection)

    if args.list:
        for row in connection.execute('SELECT * FROM people ORDER BY id'):
            print(f"{row['personas_kods']}  {row['first_name']} {row['last_name']:<14} {row['email']:<34} {row['phone']}")


if __name__ == '__main__':
    main()
