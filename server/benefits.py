#!/usr/bin/env python3
"""VSAA benefit rules used by the demo dashboard.

The rules summarise public VSAA service descriptions (vsaa.gov.lv) and the
Latvija.gov.lv life-situation pages as read on 2026-10-09. They are a
prototype simplification: amounts, deadlines and eligibility must be
verified against the official sources linked in each entry before any real
use. Nothing here is an eligibility decision.
"""
from datetime import date, timedelta

LIFE_SITUATIONS = {
    'berna_piedzimsana': 'https://latvija.gov.lv/LifeSituations/22503',
    'slimibas_lapa': 'https://latvija.gov.lv/LifeSituations/23773',
    'bezdarbs': 'https://latvija.gov.lv/LifeSituations/22291',
}
VSAA_ESERVICE = 'https://latvija.gov.lv/Services/45686'  # "VSAA informācija un pakalpojumi"

# Official service names follow the Latvija.gov.lv catalogue
# ("<pabalsta> piešķiršana un izmaksāšana").
BENEFITS = {
    'maternitates': {
        'name': 'Maternitātes pabalsta piešķiršana un izmaksāšana',
        'short': 'Maternitātes pabalsts',
        'group': 'berns',
        'roles': ['māte'],
        'onePerFamily': False,
        'amount': '80 % no vidējās apdrošināšanas iemaksu algas',
        'period': '56 vai 70 dienas pirms un pēc dzemdībām',
        'deadlineFrom': 'leave_start',
        'deadlineMonths': 6,
        'processingDays': 10,
        'requires': ['darbnespējas lapa B reģistrēta e-veselībā'],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/maternitates-pabalsta-pieskirsana-un-izmaksasana',
    },
    'paternitates': {
        'name': 'Paternitātes pabalsta piešķiršana un izmaksāšana',
        'short': 'Paternitātes pabalsts',
        'group': 'berns',
        'roles': ['tēvs'],
        'onePerFamily': False,
        'amount': '80 % no vidējās apdrošināšanas iemaksu algas (ar koeficientu 1,46)',
        'period': '10 darba dienu atvaļinājums, jāizmanto līdz bērna 6 mēnešu vecumam',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'processingDays': 10,
        'requires': ['darba devēja piešķirts atvaļinājums'],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/paternitates-pabalsta-pieskirsana-un-izmaksasana',
    },
    'berna_piedzimsanas': {
        'name': 'Bērna piedzimšanas pabalsta piešķiršana un izmaksāšana',
        'short': 'Bērna piedzimšanas pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'amount': '421,17 EUR vienreizējs maksājums',
        'period': 'Lēmums ne agrāk kā bērna 8. dzīves dienā',
        'availableFromDays': 8,
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'processingDays': 8,
        'requires': ['bērnam piešķirts personas kods'],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/berna-piedzimsanas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'berna_kopsanas': {
        'name': 'Bērna kopšanas pabalsta piešķiršana un izmaksāšana',
        'short': 'Bērna kopšanas pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'amount': '298 EUR mēnesī līdz 1,5 gadu vecumam (no 01.01.2026.)',
        'period': 'Līdz bērna 1,5 gadu vecumam; neatkarīgi no nodarbinātības',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'processingDays': 22,
        'requires': [],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/berna-kopsanas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'vecaku': {
        'name': 'Vecāku pabalsta piešķiršana un izmaksāšana',
        'short': 'Vecāku pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'amount': 'Atkarīgs no iemaksu algas un izvēlētā ilguma (13 vai 19 mēneši)',
        'period': '13 vai 19 mēneši; katram vecākam 2 nenododami mēneši līdz bērna 8 gadu vecumam',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'processingDays': 10,
        'requires': ['darba ņēmējs vai pašnodarbinātais'],
        'options': {'ilgums': ['13 mēneši', '19 mēneši']},
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/vecaku-pabalsta-pieskirsana-un-izmaksasana',
    },
    'gimenes_valsts': {
        'name': 'Ģimenes valsts pabalsta piešķiršana un izmaksāšana',
        'short': 'Ģimenes valsts pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'amount': '25 EUR par 1 bērnu, 50 EUR par katru no 2, 75 EUR par katru no 3, 100 EUR par katru no 4 un vairāk bērniem',
        'period': 'No bērna 1 gada līdz 16 gadu vecumam (līdz 20 gadiem, ja mācās)',
        'availableFromYears': 1,
        'deadlineFrom': 'first_birthday',
        'deadlineMonths': 24,
        'processingDays': 10,
        'requires': [],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/gimenes-valsts-pabalsta-pieskirsana-un-izmaksasana',
    },
    'slimibas': {
        'name': 'Slimības pabalsta piešķiršana un izmaksāšana',
        'short': 'Slimības pabalsts',
        'group': 'slimiba',
        'roles': [],
        'onePerFamily': False,
        'amount': 'No 10. darbnespējas dienas (lapa B); pirmās 9 dienas maksā darba devējs (lapa A)',
        'period': 'Līdz 26 nedēļām nepārtraukti vai 52 nedēļām trīs gados',
        'deadlineFrom': 'incapacity_start',
        'deadlineMonths': 6,
        'processingDays': 10,
        'requires': ['noslēgta darbnespējas lapa B e-veselībā'],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/slimibas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'bezdarbnieka': {
        'name': 'Bezdarbnieka pabalsta piešķiršana un izmaksāšana',
        'short': 'Bezdarbnieka pabalsts',
        'group': 'bezdarbs',
        'roles': [],
        'onePerFamily': False,
        'amount': 'Atkarīgs no vidējās iemaksu algas un stāža; 1.–2. mēn. 100 %, 3.–4. mēn. 75 %, 5.–6. mēn. 50 %, 7.–8. mēn. 45 %',
        'period': 'Līdz 8 mēnešiem',
        'deadlineFrom': 'unemployed_status',
        'deadlineMonths': None,
        'processingDays': 22,
        'requires': ['NVA piešķirts bezdarbnieka statuss', 'iemaksas 12 no pēdējiem 16 mēnešiem'],
        'source': 'https://www.vsaa.gov.lv/lv/pakalpojumi/bezdarbnieka-pabalsta-pieskirsana-un-izmaksasana',
    },
}


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(day.day, last))


def child_benefit_status(code, role, birth, today, own_application, other_application):
    """Return the status of one child benefit for one parent.

    own_application / other_application are application rows (or None) made
    by this person and by the other parent for the same child and benefit.
    """
    rule = BENEFITS[code]
    deadline = None
    available_from = birth
    if rule['deadlineFrom'] == 'birth':
        deadline = add_months(birth, rule['deadlineMonths'])
    elif rule['deadlineFrom'] == 'first_birthday':
        available_from = add_months(birth, 12)
        deadline = add_months(available_from, rule['deadlineMonths'])
    elif rule['deadlineFrom'] == 'leave_start':
        # Pregnancy leave begins before the birth; approximate with 70 days before.
        leave_start = birth - timedelta(days=70)
        deadline = add_months(leave_start, rule['deadlineMonths'])
    if rule.get('availableFromDays'):
        available_from = birth + timedelta(days=rule['availableFromDays'])

    result = {
        'code': code,
        'name': rule['name'],
        'short': rule['short'],
        'amount': rule['amount'],
        'period': rule['period'],
        'requires': rule['requires'],
        'options': rule.get('options'),
        'onePerFamily': rule['onePerFamily'],
        'processingDays': rule['processingDays'],
        'source': rule['source'],
        'availableFrom': available_from.isoformat(),
        'deadline': deadline.isoformat() if deadline else None,
        'daysLeft': (deadline - today).days if deadline else None,
        'windowDays': (deadline - available_from).days if deadline else None,
    }
    if role not in rule['roles']:
        result['status'] = 'nav_attiecas'
        result['statusText'] = 'Attiecas uz otru vecāku'
    elif own_application:
        result['status'] = own_application['status']
        result['statusText'] = {'iesniegts': 'Iesniegts VSAA', 'izskatisana': 'Izskatīšanā', 'pieskirts': 'Piešķirts'}.get(own_application['status'], own_application['status'])
        result['application'] = own_application
    elif other_application and rule['onePerFamily']:
        result['status'] = 'otrs_vecaks'
        result['statusText'] = 'Pieteicis otrs vecāks'
    elif today < available_from:
        result['status'] = 'gaidams'
        result['statusText'] = f'Pieejams no {available_from:%d.%m.%Y}'
    elif deadline and today > deadline:
        result['status'] = 'nokavets'
        result['statusText'] = 'Pieteikšanās termiņš pagājis'
    elif deadline and (deadline - today).days <= 30:
        result['status'] = 'steidzami'
        result['statusText'] = f'Termiņš pēc {(deadline - today).days} dienām'
    else:
        result['status'] = 'pieejams'
        result['statusText'] = 'Pieejams, nav pieteikts'
    return result
