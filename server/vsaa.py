#!/usr/bin/env python3
"""VSAA dashboard logic for the demo: situation overview, applications, notifications.

Everything works on the fictional people database. Benefit rules come from
benefits.py; nothing is sent to VSAA, NVA or any real system.
"""
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from benefits import BENEFITS, LIFE_SITUATIONS, VSAA_ESERVICE, add_months, child_benefit_status

PUBLIC_DIR = Path(__file__).resolve().parent.parent / 'public'
ADDRESS_FILE = Path(os.environ.get('ADDRESS_FILE', PUBLIC_DIR / 'data' / 'addresses.json'))
VACANCY_FILE = Path(os.environ.get('VACANCY_FILE', PUBLIC_DIR / 'data' / 'nva-vacancies.json'))
IBAN_PATTERN = re.compile(r'^LV[0-9]{2}[A-Z]{4}[A-Z0-9]{13}$')
SENDER = 'VSAA · DEMONSTRĀCIJA'
STATUS_TEXT = {'iesniegts': 'Iesniegts VSAA', 'izskatisana': 'Izskatīšanā', 'pieskirts': 'Piešķirts'}
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


def application_row(row):
    return {'id': row['id'], 'benefitCode': row['benefit_code'], 'childId': row['child_id'], 'sickLeaveId': row['sick_leave_id'],
            'submittedAt': row['submitted_at'], 'status': row['status'], 'statusText': STATUS_TEXT.get(row['status'], row['status']),
            'details': json.loads(row['details'] or '{}'), 'name': BENEFITS.get(row['benefit_code'], {}).get('short', row['benefit_code'])}


def dashboard(db, person, today=None):
    today = today or date.today()
    pid = person['id']
    municipality = municipality_of(person['address'])
    applications = {}
    for row in db.execute('SELECT * FROM applications WHERE person_id = ? ORDER BY submitted_at DESC, id DESC', (pid,)):
        applications.setdefault((row['benefit_code'], row['child_id'], row['sick_leave_id']), application_row(row))
    my_applications = list(applications.values())

    children = []
    for link in db.execute('SELECT c.*, cp.role FROM children c JOIN child_parents cp ON cp.child_id = c.id WHERE cp.person_id = ? ORDER BY c.birth_date DESC', (pid,)):
        birth = date.fromisoformat(link['birth_date'])
        other = db.execute('SELECT person_id, role FROM child_parents WHERE child_id = ? AND person_id != ?', (link['id'], pid)).fetchone()
        other_apps = {}
        if other:
            for row in db.execute('SELECT * FROM applications WHERE person_id = ? AND child_id = ?', (other['person_id'], link['id'])):
                other_apps.setdefault(row['benefit_code'], application_row(row))
        benefits = []
        for code, rule in BENEFITS.items():
            if rule['group'] != 'berns':
                continue
            own = applications.get((code, link['id'], None))
            benefits.append(child_benefit_status(code, link['role'], birth, today, own, other_apps.get(code)))
        notified = db.execute("SELECT received_at FROM messages WHERE seed_key LIKE ? ORDER BY received_at DESC LIMIT 1",
                              (f'share-{link["id"]}-{pid}-%',)).fetchone() if other else None
        children.append({
            'id': link['id'], 'firstName': link['first_name'], 'birthDate': link['birth_date'],
            'ageDays': (today - birth).days, 'ageText': age_text(birth, today), 'firstBirthday': add_months(birth, 12).isoformat(),
            'myRole': link['role'],
            'otherParent': {'known': bool(other), 'role': other['role'] if other else None, 'notifiedAt': notified['received_at'] if notified else None},
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
            'statusText': {'neizmaksata': 'Pabalsts nav pieprasīts', 'izmaksata': 'Pabalsts izmaksāts', 'iesniegts': 'Iesniegts VSAA', 'pieskirts': 'Piešķirts'}.get(status, status),
            'deadline': deadline.isoformat(), 'daysLeft': (deadline - today).days, 'application': app,
            'benefitDays': max(0, (date.fromisoformat(row['date_to']) - start).days + 1 - 9),
        })

    months = []
    paid = {row['month']: row for row in db.execute('SELECT * FROM contributions WHERE person_id = ?', (pid,))}
    for back in range(16, 0, -1):
        month = date(today.year + (today.month - 1 - back) // 12, (today.month - 1 - back) % 12 + 1, 1)
        key = f'{month:%Y-%m}'
        months.append({'month': key, 'paid': key in paid, 'employer': paid[key]['employer'] if key in paid else None})
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
        'benefitEligible': with_contributions >= 12, 'nvaRegistered': bool(person['nva_registered']),
        'application': unemployment_app, 'rule': {k: v for k, v in BENEFITS['bezdarbnieka'].items() if k != 'roles'},
        'lifeSituationUrl': LIFE_SITUATIONS['bezdarbs'], 'municipality': municipality,
    }

    reminders = []
    if not person['iban']:
        reminders.append({'key': 'iban', 'level': 'info', 'title': 'Profils nav pilnībā iestatīts',
                          'text': 'Pievienojiet bankas kontu, uz kuru VSAA izmaksās pabalstus. Pārējie dati (vārds, personas kods, deklarētā dzīvesvieta, bērna dati) jau ir reģistros.',
                          'dueDate': None, 'daysLeft': None, 'action': 'profile'})
    for child in children:
        for benefit in child['benefits']:
            if benefit['status'] in ('pieejams', 'steidzami'):
                reminders.append({'key': f'{benefit["code"]}-{child["id"]}', 'level': 'steidzami' if benefit['status'] == 'steidzami' else 'pieejams',
                                  'title': f'{benefit["short"]} par {child["firstName"]} nav pieteikts',
                                  'text': f'Pieteikšanās termiņš {date.fromisoformat(benefit["deadline"]):%d.%m.%Y}. {benefit["amount"]}.',
                                  'dueDate': benefit['deadline'], 'daysLeft': benefit['daysLeft'], 'action': 'apply', 'benefitCode': benefit['code'], 'childId': child['id']})
            elif benefit['status'] == 'gaidams' and benefit['code'] == 'gimenes_valsts' and 0 <= (date.fromisoformat(benefit['availableFrom']) - today).days <= 60:
                reminders.append({'key': f'{benefit["code"]}-{child["id"]}-soon', 'level': 'info',
                                  'title': f'{child["firstName"]} drīz būs 1 gads',
                                  'text': f'No {date.fromisoformat(benefit["availableFrom"]):%d.%m.%Y} varēs pieteikt ģimenes valsts pabalstu. Bērna kopšanas pabalsts turpinās līdz 1,5 gadu vecumam.',
                                  'dueDate': benefit['availableFrom'], 'daysLeft': (date.fromisoformat(benefit['availableFrom']) - today).days, 'action': None})
    for leave in sick_leaves:
        if leave['status'] == 'neizmaksata':
            reminders.append({'key': f'slimibas-{leave["id"]}', 'level': 'steidzami' if leave['daysLeft'] <= 30 else 'pieejams',
                              'title': f'Darbnespējas lapa {leave["number"]} noslēgta, pabalsts nav pieprasīts',
                              'text': f'Slimības pabalstu par {leave["benefitDays"]} dienām (no 10. dienas) var pieprasīt līdz {date.fromisoformat(leave["deadline"]):%d.%m.%Y}.',
                              'dueDate': leave['deadline'], 'daysLeft': leave['daysLeft'], 'action': 'apply', 'benefitCode': 'slimibas', 'sickLeaveId': leave['id']})
    if employment['status'] == 'iemaksas_partrauktas' and not unemployment_app:
        reminders.append({'key': 'nva', 'level': 'steidzami' if gap >= 2 else 'pieejams',
                          'title': f'Sociālās iemaksas nav veiktas {gap} mēnešus',
                          'text': 'Reģistrējieties NVA bezdarbnieka statusam un tajā pašā dienā piesakieties bezdarbnieka pabalstam. Iemaksas veiktas '
                                  f'{with_contributions} no pēdējiem 16 mēnešiem' + (' — pabalsta nosacījums (12 mēneši) ir izpildīts.' if with_contributions >= 12 else ' — nepietiek pabalstam (vajag 12).'),
                          'dueDate': None, 'daysLeft': None, 'action': 'apply', 'benefitCode': 'bezdarbnieka'})
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
        'person': {'id': pid, 'firstName': person['first_name'], 'lastName': person['last_name'], 'personasKods': person['personas_kods'],
                   'address': person['address'], 'municipality': municipality, 'iban': person['iban'], 'ibanMasked': mask_iban(person['iban']),
                   'remindersEnabled': bool(person['reminders_enabled']), 'nvaRegistered': bool(person['nva_registered']),
                   'profileComplete': bool(person['iban'])},
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
        if item['level'] == 'info' and item['key'] == 'iban':
            continue
        cursor = db.execute('INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at) VALUES (?, ?, ?, ?, ?, ?)',
                            (person['id'], f'reminder-{item["key"]}', SENDER, f'Atgādinājums: {item["title"]}', item['text'] + ' Atveriet sadaļu "Mana VSAA", lai pieteiktos.', now_iso()))
        delivered += cursor.rowcount
    return delivered


def update_profile(db, person, payload):
    iban = str(payload.get('iban', '')).replace(' ', '').upper()
    if iban and not valid_iban(iban):
        return 'invalid_iban'
    reminders = payload.get('remindersEnabled')
    db.execute('UPDATE people SET iban = COALESCE(?, iban), reminders_enabled = COALESCE(?, reminders_enabled) WHERE id = ?',
               (iban if 'iban' in payload else None, None if reminders is None else int(bool(reminders)), person['id']))
    return None


def apply(db, person, payload, today=None):
    today = today or date.today()
    code = payload.get('benefitCode')
    if code not in BENEFITS:
        return 'unknown_benefit', None
    iban = str(payload.get('iban') or person['iban'] or '').replace(' ', '').upper()
    if not valid_iban(iban):
        return 'invalid_iban', None
    details = {key: value for key, value in (payload.get('options') or {}).items() if isinstance(value, str) and len(value) < 80}
    child_id = sick_leave_id = None
    rule = BENEFITS[code]
    data = dashboard(db, person, today)
    if rule['group'] == 'berns':
        child = next((item for item in data['children'] if item['id'] == payload.get('childId')), None)
        benefit = next((item for item in child['benefits'] if item['code'] == code), None) if child else None
        if not benefit or benefit['status'] not in ('pieejams', 'steidzami'):
            return 'not_available', None
        child_id = child['id']
        subject = f'Iesniegums saņemts: {rule["short"]} par {child["firstName"]}'
    elif rule['group'] == 'slimiba':
        leave = next((item for item in data['sickLeaves'] if item['id'] == payload.get('sickLeaveId')), None)
        if not leave or leave['status'] != 'neizmaksata':
            return 'not_available', None
        sick_leave_id = leave['id']
        db.execute("UPDATE sick_leaves SET status = 'iesniegts' WHERE id = ?", (leave['id'],))
        subject = f'Iesniegums saņemts: slimības pabalsts par lapu {leave["number"]}'
    else:
        if data['employment']['application']:
            return 'not_available', None
        if not data['employment']['benefitEligible']:
            return 'not_eligible', None
        # Demo shortcut: NVA unemployed status and the VSAA application are filed together.
        db.execute('UPDATE people SET nva_registered = 1 WHERE id = ?', (person['id'],))
        details['nvaStatuss'] = f'Bezdarbnieka statuss reģistrēts {today:%d.%m.%Y} (demonstrācija)'
        subject = 'Iesniegums saņemts: bezdarbnieka pabalsts'
    db.execute('UPDATE people SET iban = ? WHERE id = ?', (iban, person['id']))
    details['izmaksa'] = mask_iban(iban)
    cursor = db.execute('INSERT INTO applications (person_id, benefit_code, child_id, sick_leave_id, submitted_at, status, details) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (person['id'], code, child_id, sick_leave_id, now_iso(), 'iesniegts', json.dumps(details, ensure_ascii=False)))
    db.execute('INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at) VALUES (?, ?, ?, ?, ?, ?)',
               (person['id'], f'application-{cursor.lastrowid}', SENDER, subject,
                f'{rule["name"]}: iesniegums reģistrēts {today:%d.%m.%Y}. Lēmums paredzams {rule["processingDays"]} darba dienu laikā. '
                f'Izmaksa uz kontu {mask_iban(iban)}. Demonstrācijas ziņojums, nekas nav nosūtīts VSAA.', now_iso()))
    return None, cursor.lastrowid


def notify_other_parent(db, person, child_id, today=None):
    today = today or date.today()
    link = db.execute('SELECT c.*, cp.role FROM children c JOIN child_parents cp ON cp.child_id = c.id WHERE c.id = ? AND cp.person_id = ?',
                      (child_id, person['id'])).fetchone()
    if not link:
        return 'not_found'
    other = db.execute('SELECT person_id, role FROM child_parents WHERE child_id = ? AND person_id != ?', (child_id, person['id'])).fetchone()
    if not other:
        return 'no_other_parent'
    birth = date.fromisoformat(link['birth_date'])
    lines = []
    for code, rule in BENEFITS.items():
        if rule['group'] != 'berns' or other['role'] not in rule['roles']:
            continue
        status = child_benefit_status(code, other['role'], birth, today, None, None)
        if status['status'] in ('pieejams', 'steidzami', 'gaidams'):
            shared = ' (saņem tikai viens no vecākiem — vienojieties, kurš piesakās)' if rule['onePerFamily'] else ''
            lines.append(f'• {rule["short"]}: {rule["amount"]}; termiņš {date.fromisoformat(status["deadline"]):%d.%m.%Y}{shared}')
    dative = {'māte': 'mātei', 'tēvs': 'tēvam'}.get(other['role'], 'vecākam')
    body = (f'{person["first_name"]} {person["last_name"]} aicina salīdzināt pabalstus par bērnu {link["first_name"]} (dz. {birth:%d.%m.%Y}). '
            f'Jums kā {dative} pieejamie VSAA pabalsti:\n' + '\n'.join(lines) +
            '\nAtveriet "Mana VSAA", lai pieteiktos vai aprēķinātu summu. Demonstrācijas ziņojums.')
    cursor = db.execute('INSERT OR IGNORE INTO messages (person_id, seed_key, sender, subject, body, received_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (other['person_id'], f'share-{child_id}-{person["id"]}-{today.isoformat()}', SENDER,
                         f'Pabalsti par bērnu {link["first_name"]}: salīdziniet, kurš no vecākiem piesakās', body, now_iso()))
    return None if cursor.rowcount else 'already_sent_today'


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
