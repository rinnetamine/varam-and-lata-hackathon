#!/usr/bin/env python3
"""Fictional Latvian people for the Faketvija demo database.

Everything here is invented. Names are randomly combined, e-mail addresses use
the reserved example.com domain, and phone numbers are random. Personas kodi
use the post-2017 format (32XXXX-XXXXX), which carries no birth date, so no
real person's data is encoded. They are demo identifiers only: a random code
or number can still coincide with a real one, so never treat these as real.

Usage:
    python3 server/seed_people.py --list     # show the people in the database
    python3 server/seed_people.py --reset    # drop and regenerate the people
"""
import argparse
import random
import sqlite3
import unicodedata
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'people.db'
DEFAULT_COUNT = 60
DEFAULT_SEED = 20240601

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  personas_kods TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expires_at ON sessions(expires_at);
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
    return connection


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

        code = f'32{rng.randrange(10000):04d}-{rng.randrange(100000):05d}'
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
        people.append((first, last, code, email, phone))
    return people


def seed(connection, count=DEFAULT_COUNT, seed_value=DEFAULT_SEED):
    with connection:
        connection.executemany(
            'INSERT INTO people (first_name, last_name, personas_kods, email, phone) VALUES (?, ?, ?, ?, ?)',
            generate_people(count, seed_value),
        )


def ensure_seeded(connection):
    if connection.execute('SELECT COUNT(*) FROM people').fetchone()[0] == 0:
        seed(connection)


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
        print(f'Regenerated {args.count} people in {args.db}')
    else:
        ensure_seeded(connection)

    if args.list:
        for row in connection.execute('SELECT * FROM people ORDER BY id'):
            print(f"{row['personas_kods']}  {row['first_name']} {row['last_name']:<14} {row['email']:<34} {row['phone']}")


if __name__ == '__main__':
    main()
