"""Separate fictional family and bank registries. No real bank or residents API."""
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

NAME_FILE = Path(os.environ.get('NAME_FILE', Path(__file__).resolve().parent.parent/'public/data/person-names.json'))
CASES = {1:'Nav bērnu', 2:'Viens jaundzimušais, divi vecāki', 3:'Divi bērni, daļa pabalstu jau piešķirta', 4:'Viens bērns, tēvs nav norādīts'}
CHILD_BENEFITS = ('berna_piedzimsanas','berna_kopsanas','vecaku','gimenes_valsts','maternitates','paternitates')

def attach(db, people_path, initialize=True):
    folder = Path(people_path).resolve().parent
    db.execute('ATTACH DATABASE ? AS family', (str(folder/'children.db'),))
    db.execute('ATTACH DATABASE ? AS bank', (str(folder/'bank.db'),))
    if not initialize:
        return
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
    people = {r['id']:r for r in db.execute("SELECT * FROM people WHERE role = 'person'")}
    with db:
        for pid, person in people.items():
            db.execute('INSERT OR IGNORE INTO bank.people VALUES (?, ?, ?)', (person['personas_kods'],person['first_name'],person['last_name']))
            if not db.execute('SELECT 1 FROM bank.accounts WHERE personas_kods=?',(person['personas_kods'],)).fetchone():
                db.execute('INSERT INTO bank.accounts (iban, personas_kods) VALUES (?, ?)', (make_iban(pid), person['personas_kods']))
        if db.execute("SELECT 1 FROM family.metadata WHERE key = 'showcase-v2-four-users'").fetchone():
            restore_partners(db)
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
        restore_partners(db)

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


def restore_partners(db):
    """Add missing spouses without replacing applications, bank accounts or sessions."""
    names = json.loads(NAME_FILE.read_text())['names']
    if not db.execute("SELECT 1 FROM family.metadata WHERE key='restored-partners-v2'").fetchone():
        db.execute("UPDATE people SET first_name='Mārtiņš', last_name='Purviņš', email='martins.purvins@example.com' WHERE id=3 AND role='person'")
        db.execute("UPDATE people SET last_name='Purviņa' WHERE id=2 AND role='person'")
        partners = [('120489-90005','male','Grīnbergs','1989-04-12',4),
                    ('210687-90006','female','Purviņa','1987-06-21',3),
                    ('140280-90007','male','Rozītis','1980-02-14',1)]
        ids = []
        for index,(code,gender,surname,birth,partner) in enumerate(partners):
            candidates=[n['name'] for n in names if n['gender']==('VĪRIETIS' if gender=='male' else 'SIEVIETE')]
            address=db.execute('SELECT address FROM people WHERE id=?',(partner,)).fetchone()['address']
            db.execute("INSERT OR IGNORE INTO people (first_name,last_name,personas_kods,email,phone,address,birth_date,role) VALUES (?,?,?,?,?,?,?,'person')",
                       (candidates[index+5],surname,code,f'partner{index+1}@example.com',f'+371 2000900{index+1}',address,birth))
            ids.append(db.execute('SELECT id FROM people WHERE personas_kods=?',(code,)).fetchone()['id'])
        db.execute('UPDATE family.children SET father_id=? WHERE id=3',(ids[0],))
        db.execute('UPDATE family.children SET mother_id=? WHERE id=2',(ids[1],))
        # Children inherit the family surname with the appropriate Latvian form.
        from seed_people import SURNAMES
        gender_by_name={n['name']:n['gender'] for n in names}
        for child in db.execute('SELECT * FROM family.children').fetchall():
            surname=db.execute('SELECT last_name FROM people WHERE id=?',(child['father_id'] or child['mother_id'],)).fetchone()['last_name']
            female=gender_by_name.get(child['first_name'])=='SIEVIETE'
            surname=next((pair[1 if female else 0] for pair in SURNAMES if surname in pair),surname)
            db.execute('UPDATE family.children SET last_name=? WHERE id=?',(surname,child['id']))
        db.execute("INSERT INTO family.metadata VALUES ('restored-partners-v2','applied')")
    for person in db.execute("SELECT * FROM people WHERE role='person'").fetchall():
        db.execute('INSERT INTO bank.people VALUES (?,?,?) ON CONFLICT(personas_kods) DO UPDATE SET first_name=excluded.first_name,last_name=excluded.last_name',
                   (person['personas_kods'],person['first_name'],person['last_name']))
        if not db.execute('SELECT 1 FROM bank.accounts WHERE personas_kods=?',(person['personas_kods'],)).fetchone():
            db.execute('INSERT INTO bank.accounts (iban,personas_kods) VALUES (?,?)',(make_iban(person['id']),person['personas_kods']))
    CASES[4]='Viens bērns, divi vecāki'


def order_demo_accounts(db):
    """Keep primary users 1–4, partner users 5–7, and the administrator 999."""
    targets = {'120489-90005':5, '210687-90006':6, '140280-90007':7}
    changes=[]
    for person in db.execute('SELECT id,personas_kods,role FROM people').fetchall():
        target=999 if person['role']=='admin' else targets.get(person['personas_kods'],person['id'])
        if person['id']!=target:
            changes.append((person['id'],target))
    if not changes:
        return
    db.execute('PRAGMA defer_foreign_keys = ON')
    def move(old,new):
        db.execute('UPDATE people SET id=? WHERE id=?',(new,old))
        for table in ('sessions','messages','child_parents','sick_leaves','contributions','applications'):
            db.execute(f'UPDATE {table} SET person_id=? WHERE person_id=?',(new,old))
        db.execute('UPDATE family.children SET mother_id=? WHERE mother_id=?',(new,old))
        db.execute('UPDATE family.children SET father_id=? WHERE father_id=?',(new,old))
    for old,new in changes:
        move(old,-old)
    for old,new in changes:
        move(-old,new)
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Demo account ID migration left invalid references')


def repair_showcase_names(db):
    """Keep fictional showcase names consistent with their explicitly seeded roles."""
    from seed_people import SURNAMES, ascii_fold
    names = json.loads(NAME_FILE.read_text())['names']
    pools = {gender: [n['name'] for n in names if n['gender'] == gender]
             for gender in ('SIEVIETE', 'VĪRIETIS')}
    roles = {1: 'SIEVIETE', 2: 'SIEVIETE', 3: 'VĪRIETIS', 4: 'SIEVIETE',
             5: 'VĪRIETIS', 6: 'SIEVIETE', 7: 'VĪRIETIS'}
    for pid, gender in roles.items():
        person = db.execute("SELECT * FROM people WHERE id=? AND role='person'", (pid,)).fetchone()
        if not person:
            continue
        first = person['first_name'] if person['first_name'] in pools[gender] else pools[gender][pid % len(pools[gender])]
        last = next((pair[1 if gender == 'SIEVIETE' else 0] for pair in SURNAMES
                     if person['last_name'] in pair), person['last_name'])
        if (first, last) != (person['first_name'], person['last_name']):
            email = f'{ascii_fold(first)}.{ascii_fold(last)}@example.com'
            if db.execute('SELECT 1 FROM people WHERE email=? AND id!=?', (email, pid)).fetchone():
                email = f'{ascii_fold(first)}.{ascii_fold(last)}{pid}@example.com'
            db.execute('UPDATE people SET first_name=?,last_name=?,email=? WHERE id=?', (first,last,email,pid))


def seed_household_showcase(db, today=None):
    """Four distinct households: zero, one, two children and a single mother."""
    today=today or date.today()
    if not db.execute("SELECT 1 FROM family.metadata WHERE key='household-showcase-v3'").fetchone():
        names=json.loads(NAME_FILE.read_text())['names']
        female_names=[n['name'] for n in names if n['gender']=='SIEVIETE']
        db.execute("UPDATE people SET last_name='Kļaviņa' WHERE id=2")
        db.execute("UPDATE people SET last_name='Kļaviņš',address=(SELECT address FROM people WHERE id=2) WHERE id=5")
        db.execute('UPDATE people SET first_name=? WHERE id=6',(female_names[12],))
        # Move the existing one-child household's father applications and messages together.
        for app in db.execute('SELECT id FROM applications WHERE child_id=1 AND person_id=3').fetchall():
            db.execute('UPDATE messages SET person_id=5 WHERE person_id=3 AND (seed_key=? OR seed_key LIKE ?)',(f'application-{app["id"]}',f'decision-{app["id"]}-%'))
        db.execute('UPDATE applications SET person_id=5 WHERE child_id=1 AND person_id=3')
        db.execute('UPDATE family.children SET mother_id=2,father_id=5 WHERE id=1')
        db.execute('UPDATE family.children SET mother_id=6,father_id=3 WHERE id=2')
        db.execute('UPDATE family.children SET mother_id=4,father_id=NULL WHERE id=3')
        birth=today-timedelta(days=18)
        name=names[28]['name']
        code=f'{birth:%d%m%y}-{random.Random(8104).randrange(100000):05d}'
        db.execute('INSERT INTO family.children (id,first_name,last_name,personas_kods,birth_date,seed_key,mother_id,father_id) VALUES (4,?,?,?,?,?,6,3)',(name,'Purviņa',code,birth.isoformat(),'showcase-4'))
        db.execute('INSERT INTO children (id,first_name,birth_date,seed_key) VALUES (4,?,?,?)',(name,birth.isoformat(),'showcase-4'))
        for benefit in CHILD_BENEFITS:
            db.execute('INSERT INTO family.benefits VALUES (4,?,0,0)',(benefit,))
        from seed_people import SURNAMES
        genders={n['name']:n['gender'] for n in names}
        for child in db.execute('SELECT * FROM family.children').fetchall():
            surname=db.execute('SELECT last_name FROM people WHERE id=?',(child['father_id'] or child['mother_id'],)).fetchone()['last_name']
            surname=next((pair[1 if genders.get(child['first_name'])=='SIEVIETE' else 0] for pair in SURNAMES if surname in pair),surname)
            db.execute('UPDATE family.children SET last_name=? WHERE id=?',(surname,child['id']))
        db.execute("INSERT OR IGNORE INTO messages (person_id,seed_key,sender,subject,body,received_at) SELECT DISTINCT person_id,'newborn-demo','FAKETVIJA.LV · DEMONSTRĀCIJA','Par bērna piedzimšanu ir pieejami pakalpojumi','Ar bērna piedzimšanu saistītie pakalpojumi ir apkopoti vienuviet. Izdomāts ziņojums hakatona prototipam.',? FROM family.child_parents",(today.isoformat()+'T09:00:00+03:00',))
        db.execute("INSERT INTO family.metadata VALUES ('household-showcase-v3',?)",(today.isoformat(),))
    repair_showcase_names(db)
    for person in db.execute("SELECT * FROM people WHERE role='person'").fetchall():
        db.execute('UPDATE bank.people SET first_name=?,last_name=? WHERE personas_kods=?',(person['first_name'],person['last_name'],person['personas_kods']))
    CASES.update({1:'Māte bez bērniem',7:'Tēvs bez bērniem',2:'Māte ar vienu bērnu',5:'Tēvs ar vienu bērnu',6:'Māte ar diviem bērniem',3:'Tēvs ar diviem bērniem',4:'Māte ar vienu bērnu, otrs vecāks nav norādīts'})


def promote_adult_children(db, today=None):
    """Keep historical applications, but move adults out of the active child registry."""
    from benefits import add_months
    today=today or date.today()
    db.execute('CREATE TABLE IF NOT EXISTS family.former_children (personas_kods TEXT PRIMARY KEY, citizen_id INTEGER NOT NULL, archived_at TEXT NOT NULL, record TEXT NOT NULL)')
    for child in db.execute('SELECT * FROM family.children').fetchall():
        if today < add_months(date.fromisoformat(child['birth_date']),216):
            continue
        parent=db.execute('SELECT address FROM people WHERE id=?',(child['mother_id'] or child['father_id'],)).fetchone()
        digits=child['personas_kods'].replace('-','')
        phone=f'+371 20{digits[-6:]}'
        suffix=int(digits[-6:])
        while db.execute('SELECT 1 FROM people WHERE phone=? AND personas_kods!=?',(phone,child['personas_kods'])).fetchone():
            suffix=(suffix+1)%1000000
            phone=f'+371 20{suffix:06d}'
        db.execute("INSERT OR IGNORE INTO people (first_name,last_name,personas_kods,email,phone,address,birth_date,role) VALUES (?,?,?,?,?,?,?,'person')",(child['first_name'],child['last_name'],child['personas_kods'],f'citizen{digits}@example.com',phone,parent['address'] if parent else '',child['birth_date']))
        citizen=db.execute('SELECT * FROM people WHERE personas_kods=?',(child['personas_kods'],)).fetchone()
        db.execute('INSERT OR IGNORE INTO family.former_children VALUES (?,?,?,?)',(child['personas_kods'],citizen['id'],today.isoformat(),json.dumps(dict(child),ensure_ascii=False)))
        db.execute('INSERT OR IGNORE INTO bank.people VALUES (?,?,?)',(citizen['personas_kods'],citizen['first_name'],citizen['last_name']))
        db.execute('INSERT OR IGNORE INTO bank.accounts (iban,personas_kods) VALUES (?,?)',(make_iban(citizen['id']),citizen['personas_kods']))
        db.execute('DELETE FROM messages WHERE seed_key LIKE ?',(f'share-{child["id"]}-%',))
        db.execute('DELETE FROM family.benefits WHERE child_id=?',(child['id'],))
        db.execute('DELETE FROM family.children WHERE id=?',(child['id'],))


def seed_current_showcase(db, today=None):
    """Versioned six-account presentation dataset; initialise once, preserve later actions."""
    from seed_people import generate_people, DEFAULT_SEED, ensure_admin, SURNAMES
    today = today or date.today()
    CASES.clear()
    CASES.update({1:'Māte ar 3 dienas vecu bērnu',2:'Tēvs ar 3 dienas vecu bērnu',
                  3:'Māte ar diviem bērniem, daļa pabalstu piešķirta',
                  4:'Tēvs ar diviem bērniem, daļa pabalstu piešķirta',
                  5:'Vientuļā māte ar trim bērniem'})
    if db.execute("SELECT 1 FROM family.metadata WHERE key='six-account-showcase-v4'").fetchone():
        return
    # This migration intentionally replaces the previous fictional showcase scenarios.
    for table in ('sessions','messages','applications','child_parents','sick_leaves','contributions','children'):
        db.execute(f'DELETE FROM main.{table}')
    db.execute('DELETE FROM family.benefits')
    db.execute('DELETE FROM family.children')
    db.execute('DELETE FROM family.former_children') if db.execute("SELECT 1 FROM family.sqlite_master WHERE name='former_children'").fetchone() else None
    db.execute('DELETE FROM bank.accounts')
    db.execute('DELETE FROM bank.people')
    db.execute('DELETE FROM people')
    db.execute("DELETE FROM sqlite_sequence WHERE name IN ('people','children','applications','messages','sick_leaves')")
    records = generate_people(5, DEFAULT_SEED)
    names = json.loads(NAME_FILE.read_text())['names']
    female = [n['name'] for n in names if n['gender']=='SIEVIETE']
    male = [n['name'] for n in names if n['gender']=='VĪRIETIS']
    # Imported first names, fictional family names with Latvian gender forms.
    families = [(female[2],'Kļaviņa'),(male[2],'Kļaviņš'),(female[5],'Purviņa'),
                (male[5],'Purviņš'),(female[8],'Grīnberga')]
    from seed_people import ascii_fold
    for pid,(record,(first,last)) in enumerate(zip(records,families),1):
        _,_,code,_,phone,address,birth = record
        if pid in (2,4):address=db.execute('SELECT address FROM people WHERE id=?',(pid-1,)).fetchone()['address']
        db.execute('INSERT INTO people (id,first_name,last_name,personas_kods,email,phone,address,birth_date,role) VALUES (?,?,?,?,?,?,?,?,?)',
                   (pid,first,last,code,f'{ascii_fold(first)}.{ascii_fold(last)}@example.com',phone,address,birth,'person'))
        db.execute('INSERT INTO bank.people VALUES (?,?,?)',(code,first,last))
        db.execute('INSERT INTO bank.accounts (iban,personas_kods) VALUES (?,?)',(make_iban(pid),code))
    ensure_admin(db)
    admin=db.execute("SELECT id FROM people WHERE role='admin'").fetchone()['id']
    db.execute('UPDATE people SET id=999 WHERE id=?',(admin,))
    definitions=[(1,1,2,3),(2,3,4,400),(3,3,4,40),(4,5,None,3),(5,5,None,240),(6,5,None,800)]
    for cid,mom,dad,age in definitions:
        birth=today-timedelta(days=age)
        first=names[cid*7]['name']
        surname=db.execute('SELECT last_name FROM people WHERE id=?',(dad or mom,)).fetchone()['last_name']
        gender=next(n['gender'] for n in names if n['name']==first)
        surname=next((pair[1 if gender=='SIEVIETE' else 0] for pair in SURNAMES if surname in pair),surname)
        code=f'{birth:%d%m%y}-{random.Random(9100+cid).randrange(100000):05d}'
        db.execute('INSERT INTO family.children VALUES (?,?,?,?,?,?,?,?)',(cid,first,surname,code,birth.isoformat(),f'showcase-v4-{cid}',mom,dad))
        db.execute('INSERT INTO children VALUES (?,?,?,?)',(cid,first,birth.isoformat(),f'showcase-v4-{cid}'))
        used = {'berna_piedzimsanas','berna_kopsanas','vecaku','gimenes_valsts'} if cid==2 else {'maternitates'} if cid==3 else set()
        for benefit in CHILD_BENEFITS:
            receiving=int(benefit in used)
            db.execute('INSERT INTO family.benefits VALUES (?,?,?,0)',(cid,benefit,receiving))
            if receiving:
                submitted=birth+timedelta(days=366 if benefit=='gimenes_valsts' else 10)
                db.execute('INSERT INTO applications (person_id,benefit_code,child_id,submitted_at,status,details,decided_at) VALUES (?,?,?,?,?,?,?)',
                           (mom,benefit,cid,submitted.isoformat(),'pieskirts',json.dumps({'seed':True,'iban':make_iban(mom)}),(submitted+timedelta(days=7)).isoformat()))
    for pid in range(1,6):
        end=today-timedelta(days=pid+2)
        db.execute('INSERT INTO sick_leaves (person_id,number,kind,date_from,date_to,closed_at,employer,status) VALUES (?,?,?,?,?,?,?,?)',
                   (pid,f'B-{today.year}-SHOWCASE-{pid}','B',(end-timedelta(days=15)).isoformat(),end.isoformat(),end.isoformat(),'SIA "Demo Būve"','neizmaksata'))
        db.execute('INSERT INTO messages (person_id,seed_key,sender,subject,body,received_at) VALUES (?,?,?,?,?,?)',
                   (pid,'newborn-demo','VSAA','Ar bērnu saistītie pakalpojumi','Apskati bērna pabalstus un pieejamo atbalstu sadaļā Mana VSAA.',today.isoformat()+'T09:00:00+03:00'))
    db.execute("INSERT INTO family.metadata VALUES ('six-account-showcase-v4',?)",(today.isoformat(),))
