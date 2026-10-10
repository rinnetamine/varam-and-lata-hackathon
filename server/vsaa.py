#!/usr/bin/env python3
"""VSAA dashboard logic for the demo: situation overview, applications, notifications, admin inbox.

Everything works on the fictional people, family and bank registries. Benefit
rules come from benefits.py; nothing is sent to VSAA, NVA, a bank or any real
system. Inbox messages are stored in Latvian together with a ``template`` key
and JSON ``params`` so the interface can render them in either language.
"""
import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from benefits import BENEFITS, LIFE_SITUATIONS, SAME_PERSON_GROUP, VERIFIED_AT, VSAA_ESERVICE, add_months, child_benefit_status, insured, legal_references
from demo_registry import bank_error

PUBLIC_DIR = Path(__file__).resolve().parent.parent / 'public'
ADDRESS_FILE = Path(os.environ.get('ADDRESS_FILE', PUBLIC_DIR / 'data' / 'addresses.json'))
VACANCY_FILE = Path(os.environ.get('VACANCY_FILE', PUBLIC_DIR / 'data' / 'nva-vacancies.json'))
IBAN_PATTERN = re.compile(r'^LV[0-9]{2}[A-Z]{4}[A-Z0-9]{13}$')
SENDER = 'VSAA · DEMONSTRĀCIJA'
STATUS_TEXT = {'iesniegts': 'Iesniegts VSAA', 'izskatisana': 'Izskatīšanā', 'pieskirts': 'Piešķirts', 'atteikts': 'Atteikts'}
ADMIN_STATUSES = ('izskatisana', 'pieskirts', 'atteikts')
_municipalities = None


def municipality_of(address):
    global _municipalities
    if _municipalities is None:
        try:
            records = json.loads(ADDRESS_FILE.read_text(encoding='utf-8'))['addresses']
            _municipalities = {item['label']: item['municipality'] for item in records}
        except (OSError, ValueError, KeyError):
            _municipalities = {}
    return _municipalities.get(address) or (address.rsplit(',', 2)[-2].strip() if address.count(',') >= 2 else '')


def now_iso():
    return datetime.now(timezone(timedelta(hours=3))).replace(microsecond=0).isoformat()


def age_text(birth, today):
    days = (today - birth).days
    if days < 60:
        return f'{days} dienas'
    months = (today.year - birth.year) * 12 + today.month - birth.month - (today.day < birth.day)
    if months < 24:
        return f'{months} mēneši'
    return f'{months // 12} gadi'


def fmt(iso):
    return f'{date.fromisoformat(iso[:10]):%d.%m.%Y}'


def application_row(row):
    return {'id': row['id'], 'benefitCode': row['benefit_code'], 'childId': row['child_id'], 'sickLeaveId': row['sick_leave_id'],
            'submittedAt': row['submitted_at'], 'status': row['status'], 'statusText': STATUS_TEXT.get(row['status'], row['status']),
            'details': json.loads(row['details'] or '{}'), 'name': BENEFITS.get(row['benefit_code'], {}).get('short', row['benefit_code']),
            'decidedAt': row['decided_at'] if 'decided_at' in row.keys() else None}


def post_message(db, person_id, seed_key, subject, body, template, params):
    """Store an inbox message once per seed key; returns True when it was new."""
    cursor = db.execute('INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at, template, params) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (person_id, seed_key, SENDER, subject, body, now_iso(), template, json.dumps(params, ensure_ascii=False)))
    return cursor.rowcount == 1


def contribution_months(db, pid, today, back):
    paid = {row['month']: row for row in db.execute('SELECT * FROM contributions WHERE person_id = ?', (pid,))}
    months = []
    for offset in range(back, 0, -1):
        month = date(today.year + (today.month - 1 - offset) // 12, (today.month - 1 - offset) % 12 + 1, 1)
        key = f'{month:%Y-%m}'
        months.append({'month': key, 'paid': key in paid, 'employer': paid[key]['employer'] if key in paid else None})
    return months


def dashboard(db, person, today=None):
    today = today or date.today()
    pid = person['id']
    municipality = municipality_of(person['address'])
    applications = {}
    for row in db.execute('SELECT * FROM applications WHERE person_id = ? ORDER BY submitted_at DESC, id DESC', (pid,)):
        applications.setdefault((row['benefit_code'], row['child_id'], row['sick_leave_id']), application_row(row))
    my_applications = list(applications.values())

    months24 = contribution_months(db, pid, today, 24)
    months = months24[-16:]
    insured_person = insured(sum(1 for item in months24[-6:] if item['paid']), sum(1 for item in months24 if item['paid']))

    links = db.execute('SELECT c.*, cp.role FROM family.children c JOIN family.child_parents cp ON cp.child_id = c.id WHERE cp.person_id = ? ORDER BY c.birth_date DESC', (pid,)).fetchall()
    children = []
    for link in links:
        birth = date.fromisoformat(link['birth_date'])
        other = db.execute('SELECT person_id, role FROM family.child_parents WHERE child_id = ? AND person_id != ?', (link['id'], pid)).fetchone()
        other_apps = {}
        if other:
            for row in db.execute("SELECT * FROM applications WHERE person_id = ? AND child_id = ? AND status != 'atteikts'", (other['person_id'], link['id'])):
                other_apps.setdefault(row['benefit_code'], application_row(row))
        benefits = []
        for code, rule in BENEFITS.items():
            if rule['group'] != 'berns':
                continue
            own = applications.get((code, link['id'], None))
            if own and own['status'] == 'atteikts':
                own = None
            benefit=child_benefit_status(code, link['role'], birth, today, own, other_apps, insured_person=insured_person, family_children=len(links))
            if benefit['status']=='otrs_vecaks':
                benefit['status']='nav_pieejams'
                benefit['statusText']='Šobrīd nav pieejams'
            elif benefit['status']=='nav_attiecas':
                benefit['statusText']='Nav piemērojams jūsu situācijai'
            benefits.append(benefit)
        children.append({
            'id': link['id'], 'firstName': link['first_name'], 'lastName': link['last_name'], 'personasKods': link['personas_kods'], 'birthDate': link['birth_date'],
            'ageDays': (today - birth).days, 'ageText': age_text(birth, today), 'firstBirthday': add_months(birth, 12).isoformat(),
            'myRole': link['role'],
            'notification': {'allowed': today < add_months(birth,216)},
            'benefits': benefits,
            'municipal': {'municipality': municipality, 'lifeSituationUrl': LIFE_SITUATIONS['berna_piedzimsana']},
        })

    sick_leaves = []
    for row in db.execute('SELECT * FROM sick_leaves WHERE person_id = ? ORDER BY date_from DESC', (pid,)):
        start = date.fromisoformat(row['date_from'])
        deadline = add_months(start, BENEFITS['slimibas']['deadlineMonths'])
        app = applications.get(('slimibas', None, row['id']))
        status = app['status'] if app else row['status']
        sick_leaves.append({
            'id': row['id'], 'number': row['number'], 'kind': row['kind'], 'dateFrom': row['date_from'], 'dateTo': row['date_to'],
            'days': (date.fromisoformat(row['date_to']) - start).days + 1, 'closedAt': row['closed_at'], 'employer': row['employer'],
            'status': status,
            'statusText': {'neizmaksata': 'Pabalsts nav pieprasīts', 'izmaksata': 'Pabalsts izmaksāts', **STATUS_TEXT}.get(status, status),
            'deadline': deadline.isoformat(), 'daysLeft': (deadline - today).days, 'application': app,
            'benefitDays': max(0, (date.fromisoformat(row['date_to']) - start).days + 1 - 9),
            'insured': insured_person,
        })

    with_contributions = sum(1 for item in months if item['paid'])
    gap = 0
    for item in reversed(months):
        if item['paid']:
            break
        gap += 1
    last_paid = next((item for item in reversed(months) if item['paid']), None)
    unemployment_app = applications.get(('bezdarbnieka', None, None))
    employment = {
        'months': months, 'monthsWithContributions': with_contributions, 'gapMonths': gap,
        'lastContributionMonth': last_paid['month'] if last_paid else None, 'lastEmployer': last_paid['employer'] if last_paid else None,
        'status': 'bezdarbnieks' if person['nva_registered'] else ('iemaksas_partrauktas' if gap >= 1 else 'nodarbinats'),
        'benefitEligible': with_contributions >= 12, 'insured': insured_person, 'nvaRegistered': bool(person['nva_registered']),
        'application': unemployment_app, 'rule': {k: v for k, v in BENEFITS['bezdarbnieka'].items() if k != 'roles'},
        'lifeSituationUrl': LIFE_SITUATIONS['bezdarbs'], 'municipality': municipality,
    }

    reminders = []
    if not person['iban']:
        reminders.append({'key': 'iban', 'level': 'info', 'title': 'Profils nav pilnībā iestatīts',
                          'text': 'Pievienojiet bankas kontu, uz kuru VSAA izmaksās pabalstus. Pārējie dati (vārds, personas kods, deklarētā dzīvesvieta, bērna dati) jau ir reģistros.',
                          'dueDate': None, 'daysLeft': None, 'action': 'profile', 'template': 'reminder_iban', 'params': {}})
    for child in children:
        for benefit in child['benefits']:
            if benefit['status'] in ('pieejams', 'steidzami'):
                reminders.append({'key': f'{benefit["code"]}-{child["id"]}', 'level': 'steidzami' if benefit['status'] == 'steidzami' else 'pieejams',
                                  'title': f'{benefit["short"]} par {child["firstName"]} nav pieteikts',
                                  'text': f'Pieteikšanās termiņš {fmt(benefit["deadline"])}. {benefit["amount"]}.',
                                  'dueDate': benefit['deadline'], 'daysLeft': benefit['daysLeft'], 'action': 'apply', 'benefitCode': benefit['code'], 'childId': child['id'],
                                  'template': 'reminder_benefit', 'params': {'benefit': benefit['code'], 'child': child['firstName'], 'deadline': benefit['deadline']}})
            elif benefit['status'] == 'gaidams' and benefit['code'] == 'gimenes_valsts' and 0 <= (date.fromisoformat(benefit['availableFrom']) - today).days <= 60:
                reminders.append({'key': f'{benefit["code"]}-{child["id"]}-soon', 'level': 'info',
                                  'title': f'{child["firstName"]} drīz būs 1 gads',
                                  'text': f'No {fmt(benefit["availableFrom"])} varēs pieteikt ģimenes valsts pabalstu. Bērna kopšanas pabalsts turpinās līdz 1,5 gadu vecumam.',
                                  'dueDate': benefit['availableFrom'], 'daysLeft': (date.fromisoformat(benefit['availableFrom']) - today).days, 'action': None,
                                  'template': 'reminder_first_birthday', 'params': {'child': child['firstName'], 'date': benefit['availableFrom']}})
    for leave in sick_leaves:
        if leave['status'] == 'neizmaksata':
            reminders.append({'key': f'slimibas-{leave["id"]}', 'level': 'steidzami' if leave['daysLeft'] <= 30 else 'pieejams',
                              'title': f'Darbnespējas lapa {leave["number"]} noslēgta, pabalsts nav pieprasīts',
                              'text': f'Slimības pabalstu par {leave["benefitDays"]} dienām (no 10. dienas) var pieprasīt līdz {fmt(leave["deadline"])}.',
                              'dueDate': leave['deadline'], 'daysLeft': leave['daysLeft'], 'action': 'apply', 'benefitCode': 'slimibas', 'sickLeaveId': leave['id'],
                              'template': 'reminder_sick_leave', 'params': {'number': leave['number'], 'days': leave['benefitDays'], 'deadline': leave['deadline']}})
    if employment['status'] == 'iemaksas_partrauktas' and not unemployment_app:
        reminders.append({'key': 'nva', 'level': 'steidzami' if gap >= 2 else 'pieejams',
                          'title': f'Sociālās iemaksas nav veiktas {gap} mēnešus',
                          'text': 'Reģistrējieties NVA bezdarbnieka statusam un tajā pašā dienā piesakieties bezdarbnieka pabalstam. Iemaksas veiktas '
                                  f'{with_contributions} no pēdējiem 16 mēnešiem' + (' — pabalsta nosacījums (12 mēneši) ir izpildīts.' if with_contributions >= 12 else ' — nepietiek pabalstam (vajag 12).'),
                          'dueDate': None, 'daysLeft': None, 'action': 'apply', 'benefitCode': 'bezdarbnieka',
                          'template': 'reminder_nva', 'params': {'gap': gap, 'months': with_contributions, 'eligible': with_contributions >= 12}})
    order = {'steidzami': 0, 'pieejams': 1, 'info': 2}
    reminders.sort(key=lambda item: (order[item['level']], item['daysLeft'] if item['daysLeft'] is not None else 10 ** 6))

    summary = {
        'available': sum(1 for child in children for benefit in child['benefits'] if benefit['status'] in ('pieejams', 'steidzami')),
        'urgent': sum(1 for item in reminders if item['level'] == 'steidzami'),
        'unpaidSickLeaves': sum(1 for leave in sick_leaves if leave['status'] == 'neizmaksata'),
        'applications': len(my_applications),
        'reminders': len(reminders),
    }
    return {
        'today': today.isoformat(),
        'verifiedAt': VERIFIED_AT,
        'person': {'id': pid, 'firstName': person['first_name'], 'lastName': person['last_name'], 'personasKods': person['personas_kods'],
                   'address': person['address'], 'municipality': municipality, 'iban': person['iban'], 'ibanMasked': mask_iban(person['iban']),
                   'remindersEnabled': bool(person['reminders_enabled']), 'nvaRegistered': bool(person['nva_registered']),
                   'profileComplete': bool(person['iban']), 'insured': insured_person, 'role': person['role']},
        'children': children, 'sickLeaves': sick_leaves, 'employment': employment, 'reminders': reminders,
        'applications': my_applications, 'summary': summary,
        'links': {'vsaaEservice': VSAA_ESERVICE, 'lifeSituations': LIFE_SITUATIONS},
    }


def valid_iban(iban):
    """Latvian IBAN format plus the ISO 7064 mod-97 checksum, as in /api/iban."""
    if not IBAN_PATTERN.match(iban):
        return False
    rearranged = iban[4:] + iban[:4]
    return int(''.join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)) % 97 == 1


def mask_iban(iban):
    return f'{iban[:4]} •••• {iban[-4:]}' if iban and len(iban) > 8 else ''


def deliver_reminders(db, person, data):
    """Copy due reminders into the e-address inbox once (seed keys keep it idempotent)."""
    if not person['reminders_enabled']:
        return 0
    delivered = 0
    for item in data['reminders']:
        if item['key'] == 'iban':
            continue
        if post_message(db, person['id'], f'reminder-{item["key"]}', f'Atgādinājums: {item["title"]}',
                        item['text'] + ' Atveriet sadaļu "Mana VSAA", lai pieteiktos.', item['template'], item['params']):
            delivered += 1
    return delivered


def update_profile(db, person, payload):
    iban = str(payload.get('iban', '')).replace(' ', '').upper()
    if iban and not valid_iban(iban):
        return 'invalid_iban'
    if iban:
        error = bank_error(db, person['personas_kods'], iban)
        if error:
            return error
    reminders = payload.get('remindersEnabled')
    db.execute('UPDATE people SET iban = COALESCE(?, iban), reminders_enabled = COALESCE(?, reminders_enabled) WHERE id = ?',
               (iban if 'iban' in payload else None, None if reminders is None else int(bool(reminders)), person['id']))
    return None


def apply(db, person, payload, today=None):
    """Submit one application. Eligibility is checked here, never trusted from the browser.

    The applications table carries unique indexes (one application per person,
    benefit and child/certificate; one per family for the benefits the law
    grants to a single parent), so concurrent or repeated submissions end as a
    single stored record; the loser receives ``not_available``.
    """
    today = today or date.today()
    code = payload.get('benefitCode')
    if code not in BENEFITS:
        return 'unknown_benefit', None
    iban = str(payload.get('iban') or person['iban'] or '').replace(' ', '').upper()
    if not valid_iban(iban):
        return 'invalid_iban', None
    error = bank_error(db, person['personas_kods'], iban)
    if error:
        return error, None
    details = {key: value for key, value in (payload.get('options') or {}).items() if isinstance(value, str) and len(value) < 80}
    child_id = sick_leave_id = None
    message_params = {}
    rule = BENEFITS[code]
    if rule.get('options'):
        for name, allowed in rule['options'].items():
            if details.get(name) not in allowed:
                return 'invalid_option', None
    data = dashboard(db, person, today)
    if rule['group'] == 'berns':
        child = next((item for item in data['children'] if item['id'] == payload.get('childId')), None)
        benefit = next((item for item in child['benefits'] if item['code'] == code), None) if child else None
        if not benefit:
            return 'not_available', None
        if benefit['status'] == 'nav_apdrosinats':
            return 'not_insured', None
        if benefit['status'] not in ('pieejams', 'steidzami'):
            return 'not_available', None
        child_id = child['id']
        subject = f'Iesniegums saņemts: {rule["short"]} par {child["firstName"]}'
        message_params['child'] = child['firstName']
        details['bērns'] = f'{child["firstName"]} {child["lastName"]}'
        if benefit.get('late'):
            details['termiņš'] = 'nokavēts — ' + rule['lateRule']
    elif rule['group'] == 'slimiba':
        leave = next((item for item in data['sickLeaves'] if item['id'] == payload.get('sickLeaveId')), None)
        if not leave or leave['status'] != 'neizmaksata':
            return 'not_available', None
        if not data['person']['insured']:
            return 'not_insured', None
        if leave['daysLeft'] < 0:
            return 'not_available', None
        sick_leave_id = leave['id']
        subject = f'Iesniegums saņemts: slimības pabalsts par lapu {leave["number"]}'
        message_params['number'] = leave['number']
        details['lapa'] = leave['number']
    else:
        if data['employment']['application']:
            return 'not_available', None
        if not data['employment']['benefitEligible']:
            return 'not_eligible', None
        subject = 'Iesniegums saņemts: bezdarbnieka pabalsts'
    details['izmaksa'] = mask_iban(iban)
    try:
        cursor = db.execute('INSERT INTO applications (person_id, benefit_code, child_id, sick_leave_id, submitted_at, status, details) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (person['id'], code, child_id, sick_leave_id, now_iso(), 'iesniegts', json.dumps(details, ensure_ascii=False)))
    except sqlite3.IntegrityError:
        return 'not_available', None
    if rule['group'] == 'slimiba':
        db.execute("UPDATE sick_leaves SET status = 'iesniegts' WHERE id = ?", (sick_leave_id,))
    elif rule['group'] == 'bezdarbs':
        # Demo shortcut: NVA unemployed status and the VSAA application are filed together.
        db.execute('UPDATE people SET nva_registered = 1 WHERE id = ?', (person['id'],))
        db.execute('UPDATE applications SET details = ? WHERE id = ?',
                   (json.dumps({**details, 'nvaStatuss': f'Bezdarbnieka statuss reģistrēts {today:%d.%m.%Y} (demonstrācija)'}, ensure_ascii=False), cursor.lastrowid))
    db.execute('UPDATE people SET iban = ? WHERE id = ?', (iban, person['id']))
    post_message(db, person['id'], f'application-{cursor.lastrowid}', subject,
                 f'{rule["name"]}: iesniegums reģistrēts {today:%d.%m.%Y}. Lēmums paredzams {rule["processingDays"]} darba dienu laikā. '
                 f'Izmaksa uz kontu {mask_iban(iban)}. Demonstrācijas ziņojums, nekas nav nosūtīts VSAA.',
                 'application_received', {'benefit': code, **message_params, 'date': today.isoformat(), 'days': rule['processingDays'], 'iban': mask_iban(iban)})
    return None, cursor.lastrowid


def notify_other_parent(db, person, child_id, today=None):
    today = today or date.today()
    link = db.execute('SELECT c.*, cp.role FROM family.children c JOIN family.child_parents cp ON cp.child_id = c.id WHERE c.id = ? AND cp.person_id = ?',
                      (child_id, person['id'])).fetchone()
    if not link:
        return 'not_found'
    birth=date.fromisoformat(link['birth_date'])
    if today >= add_months(birth,216):
        return 'not_found'
    other=db.execute('SELECT person_id FROM family.child_parents WHERE child_id=? AND person_id!=?',(child_id,person['id'])).fetchone()
    # A generic acknowledgement never reveals whether a second parent exists.
    if not other:
        return None
    child=f'{link["first_name"]} {link["last_name"]}'
    sent=post_message(db,other['person_id'],f'share-{child_id}-{person["id"]}-{today.isoformat()}',
                      f'Informācija par bērnu {child}',
                      f'Informācija par bērnu {child} (dz. {birth:%d.%m.%Y}). Atveriet Mana VSAA, lai apskatītu bērna pakalpojumus. Demonstrācijas ziņojums.',
                      'share',{'child':child,'birth':link['birth_date']})
    return None if sent else 'already_sent_today'


def vacancies(municipality):
    try:
        data = json.loads(VACANCY_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    local = data['municipalities'].get(municipality)
    top = sorted(data['categories'].items(), key=lambda item: -item[1])[:5]
    return {'municipality': municipality, 'count': local['count'] if local else 0,
            'samples': [dict(zip(data['sampleColumns'], item)) for item in (local['samples'] if local else [])],
            'total': data['total'], 'retrievedAt': data['retrievedAt'], 'source': data['source'], 'license': data['license'],
            'portal': data['vacancyUrlPrefix'], 'topCategories': [{'name': name, 'count': count} for name, count in top]}


# --- Administrator inbox ---------------------------------------------------------------

def admin_applications(db):
    """Every persisted application with applicant, child or certificate, status and details."""
    rows = db.execute('''SELECT a.*, p.first_name, p.last_name, p.personas_kods, p.address,
                                c.first_name AS child_first, c.last_name AS child_last, c.birth_date AS child_birth, c.personas_kods AS child_code,
                                s.number AS leave_number, s.date_from AS leave_from, s.date_to AS leave_to
                         FROM applications a JOIN people p ON p.id = a.person_id
                         LEFT JOIN family.children c ON c.id = a.child_id
                         LEFT JOIN sick_leaves s ON s.id = a.sick_leave_id
                         ORDER BY a.submitted_at DESC, a.id DESC''').fetchall()
    items = []
    for row in rows:
        item = application_row(row)
        item.update({
            'applicant': {'id': row['person_id'], 'name': f'{row["first_name"]} {row["last_name"]}', 'personasKods': row['personas_kods'], 'municipality': municipality_of(row['address'])},
            'child': {'name': f'{row["child_first"]} {row["child_last"]}', 'birthDate': row['child_birth'], 'personasKods': row['child_code']} if row['child_id'] else None,
            'sickLeave': {'number': row['leave_number'], 'dateFrom': row['leave_from'], 'dateTo': row['leave_to']} if row['sick_leave_id'] else None,
            'benefitName': BENEFITS.get(row['benefit_code'], {}).get('name', row['benefit_code']),
            'processingDays': BENEFITS.get(row['benefit_code'], {}).get('processingDays'),
            'seeded': bool(item['details'].get('seed')),
        })
        items.append(item)
    counts = {}
    for item in items:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    return {'applications': items, 'counts': counts, 'total': len(items), 'statuses': list(ADMIN_STATUSES), 'verifiedAt': VERIFIED_AT}


def admin_decide(db, admin, application_id, status, today=None):
    """Record a decision on an application and notify the applicant in their inbox."""
    today = today or date.today()
    if status not in ADMIN_STATUSES:
        return 'invalid_status'
    row = db.execute('SELECT a.*, c.first_name AS child_first FROM applications a LEFT JOIN family.children c ON c.id = a.child_id WHERE a.id = ?', (application_id,)).fetchone()
    if row is None:
        return 'not_found'
    if row['status'] == status:
        return None
    details = json.loads(row['details'] or '{}')
    details['lēmums'] = f'{STATUS_TEXT[status]} {today:%d.%m.%Y} ({admin["first_name"]} {admin["last_name"]}, demonstrācija)'
    db.execute('UPDATE applications SET status = ?, decided_at = ?, details = ? WHERE id = ?',
               (status, now_iso() if status != 'izskatisana' else None, json.dumps(details, ensure_ascii=False), application_id))
    if row['sick_leave_id']:
        db.execute('UPDATE sick_leaves SET status = ? WHERE id = ?', (status if status != 'izskatisana' else 'iesniegts', row['sick_leave_id']))
    rule = BENEFITS.get(row['benefit_code'], {})
    label = rule.get('short', row['benefit_code']) + (f' par {row["child_first"]}' if row['child_first'] else '')
    post_message(db, row['person_id'], f'decision-{application_id}-{status}-{today.isoformat()}',
                 f'{STATUS_TEXT[status]}: {label}',
                 f'VSAA {STATUS_TEXT[status].lower()} jūsu iesniegumu "{rule.get("name", row["benefit_code"])}" {today:%d.%m.%Y}. Demonstrācijas lēmums, nav juridiska spēka.',
                 'decision', {'benefit': row['benefit_code'], 'child': row['child_first'], 'status': status, 'date': today.isoformat()})
    return None


def legal():
    return legal_references()


def seed_application_messages(db):
    """Backfill missing receipts/decisions for persisted demo applications once."""
    for app in db.execute('SELECT a.*, c.first_name AS child_first, s.number AS leave_number FROM applications a LEFT JOIN family.children c ON c.id=a.child_id LEFT JOIN sick_leaves s ON s.id=a.sick_leave_id').fetchall():
        rule=BENEFITS.get(app['benefit_code'],{})
        details=json.loads(app['details'] or '{}')
        submitted=app['submitted_at']
        params={'benefit':app['benefit_code'],'child':app['child_first'],'number':app['leave_number'],
                'date':submitted[:10],'days':rule.get('processingDays',0),'iban':details.get('izmaksa','—')}
        db.execute('INSERT OR IGNORE INTO messages (person_id,seed_key,sender,subject,body,received_at,template,params) VALUES (?,?,?,?,?,?,?,?)',
                   (app['person_id'],f'application-{app["id"]}',SENDER,
                    f'Iesniegums saņemts: {rule.get("short",app["benefit_code"])}',
                    'Iesniegums ir reģistrēts prototipa datubāzē. Demonstrācijas ziņojums, nekas nav nosūtīts VSAA.',
                    submitted,'application_received',json.dumps(params,ensure_ascii=False)))
        if app['status'] not in ('izskatisana','pieskirts','atteikts'):
            continue
        prefix=f'decision-{app["id"]}-{app["status"]}-%'
        if db.execute('SELECT 1 FROM messages WHERE person_id=? AND seed_key LIKE ?',(app['person_id'],prefix)).fetchone():
            continue
        decided=app['decided_at'] or submitted
        status=STATUS_TEXT.get(app['status'],app['status'])
        db.execute('INSERT OR IGNORE INTO messages (person_id,seed_key,sender,subject,body,received_at,template,params) VALUES (?,?,?,?,?,?,?,?)',
                   (app['person_id'],f'decision-{app["id"]}-{app["status"]}-{decided[:10]}',SENDER,
                    f'{status}: {rule.get("short",app["benefit_code"])}',
                    'Iesnieguma statuss ir saglabāts prototipa datubāzē. Demonstrācijas lēmums, nav juridiska spēka.',
                    decided,'decision',json.dumps({'benefit':app['benefit_code'],'child':app['child_first'],'status':app['status'],'date':decided[:10]},ensure_ascii=False)))


def sanitize_shared_messages(db):
    for message in db.execute("SELECT * FROM messages WHERE template='share'").fetchall():
        params=json.loads(message['params'] or '{}')
        clean={key:params[key] for key in ('child','birth') if key in params}
        child=clean.get('child','')
        body=f'Informācija par bērnu {child} (dz. {fmt(clean["birth"])}). Atveriet Mana VSAA, lai apskatītu bērna pakalpojumus. Demonstrācijas ziņojums.' if clean.get('birth') else f'Informācija par bērnu {child}. Demonstrācijas ziņojums.'
        if params!=clean or message['body']!=body:
            db.execute('UPDATE messages SET subject=?,body=?,params=? WHERE id=?',(f'Informācija par bērnu {child}',body,json.dumps(clean,ensure_ascii=False),message['id']))
