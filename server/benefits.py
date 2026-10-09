#!/usr/bin/env python3
"""VSAA benefit rules used by the demo dashboard, with their legal sources.

Verified on 2026-10-09 against the consolidated texts on likumi.lv and the
VSAA service descriptions. Each rule names the act and article it comes from;
``type`` distinguishes legislation ('law', 'regulation') from agency guidance
('guidance'). The functions below are deliberately simple summaries for a
prototype: they are not eligibility decisions, and conditions that depend on
registry data the demo does not hold (insurance record before the seeded
months, the mother's maternity period, guardianship, out-of-family care,
EU coordination) are documented as simulations in OPEN_DATA.md and README.md.
"""
from datetime import date, timedelta

VERIFIED_AT = '2026-10-09'

LIFE_SITUATIONS = {
    'berna_piedzimsana': 'https://latvija.gov.lv/LifeSituations/22503',
    'slimibas_lapa': 'https://latvija.gov.lv/LifeSituations/23773',
    'bezdarbs': 'https://latvija.gov.lv/LifeSituations/22291',
}
VSAA_ESERVICE = 'https://latvija.gov.lv/Services/45686'  # "VSAA informācija un pakalpojumi"

LAW_MS = 'https://likumi.lv/ta/id/38051-par-maternitates-un-slimibas-apdrosinasanu'
LAW_VSP = 'https://likumi.lv/ta/id/68483-valsts-socialo-pabalstu-likums'
LAW_DL = 'https://likumi.lv/ta/id/26019-darba-likums'
LAW_BEZ = 'https://likumi.lv/ta/id/14595-par-apdrosinasanu-bezdarba-gadijumam'
MK_1546 = 'https://likumi.lv/ta/id/202714-noteikumi-par-berna-piedzimsanas-pabalsta-pieskirsanas-un-izmaksasanas-kartibu'
MK_1609 = 'https://likumi.lv/ta/id/202854'  # MK 22.12.2009. noteikumi Nr. 1609 (bērna kopšanas pabalsta apmērs, piemaksa par dvīņiem)
MK_1609_2026 = 'https://likumi.lv/ta/id/365450'  # MK 22.12.2025. noteikumi Nr. 848 — grozījumi Nr. 1609 (298 EUR formula, spēkā 01.01.2026.)
MK_864 = 'https://likumi.lv/ta/id/328673'  # MK noteikumi Nr. 864 — ģimenes valsts pabalsta un piemaksas piešķiršanas kārtība
VSAA = 'https://www.vsaa.gov.lv/lv/pakalpojumi/'

# Amounts set by the Cabinet or the law, with the dates they apply from.
CHILDBIRTH_AMOUNT = [(date(2026, 1, 1), 600.00), (date(2013, 1, 1), 421.17)]   # MK Nr. 1546, 2. punkts (MK 22.12.2025. Nr. 815)
CHILDCARE_MONTHLY = 298.00                                                     # MK Nr. 1609, 2. punkts (no 01.01.2026.; 171 EUR līdz 2025)
CHILDCARE_REDUCED = 42.69                                                      # 1,5–2 gadi, tikai bērniem, kas dzimuši līdz 02.11.2026.
CHILDCARE_TRANSITION_BIRTH = date(2026, 11, 2)
FAMILY_BENEFIT = {1: 25.00, 2: 100.00, 3: 225.00}                              # VSP likuma 6. panta 2.² daļa; 4 un vairāk: 100 EUR par katru


def ref(act, article, url, kind, note=''):
    return {'act': act, 'article': article, 'url': url, 'type': kind, 'note': note}


# Official service names follow the Latvija.gov.lv catalogue
# ("<pabalsta> piešķiršana un izmaksāšana").
BENEFITS = {
    'maternitates': {
        'name': 'Maternitātes pabalsta piešķiršana un izmaksāšana',
        'short': 'Maternitātes pabalsts',
        'group': 'berns',
        'roles': ['māte'],
        'onePerFamily': False,
        'kind': 'one_time',
        'insurance': True,
        'amount': '80 % no vidējās apdrošināšanas iemaksu algas',
        'period': '56 + 56 kalendāra dienas (70 + 56, ja grūtniecības aprūpe sākta līdz 12. nedēļai; +14 dienas komplikāciju vai vairāku bērnu gadījumā)',
        'deadlineFrom': 'leave_start',
        'deadlineMonths': 6,
        'lateRule': 'Pēc 6 mēnešiem pabalstu nepiešķir.',
        'processingDays': 10,
        'requires': ['darba ņēmēja vai pašnodarbinātā', 'iemaksas 3 no pēdējiem 6 vai 6 no pēdējiem 24 mēnešiem', 'darbnespējas lapa B reģistrēta e-veselībā'],
        'legal': [
            ref('Likums "Par maternitātes un slimības apdrošināšanu"', '4. panta pirmā daļa (apdrošināšanas stāžs), 5. pants (tiesības, 56/70 dienas), 6. pants (tēvs vai cita persona), 9. pants (darbnespējas lapa), 10. pants (80 %)', LAW_MS, 'law'),
            ref('Likums "Par maternitātes un slimības apdrošināšanu"', '25. panta pirmā daļa — pabalstu pieprasa 6 mēnešu laikā no apdrošināšanas gadījuma', LAW_MS, 'law'),
            ref('VSAA pakalpojuma apraksts', 'Maternitātes pabalsta piešķiršana un izmaksāšana', VSAA + 'maternitates-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Izpildes termiņš 10 darba dienas'),
        ],
        'source': VSAA + 'maternitates-pabalsta-pieskirsana-un-izmaksasana',
    },
    'paternitates': {
        'name': 'Paternitātes pabalsta piešķiršana un izmaksāšana',
        'short': 'Paternitātes pabalsts',
        'group': 'berns',
        'roles': ['tēvs'],
        'onePerFamily': False,
        'kind': 'one_time',
        'insurance': True,
        'amount': '80 % no vidējās apdrošināšanas iemaksu algas (VSAA piemēro koeficientu 1,46)',
        'period': '10 darba dienu atvaļinājums (par katru bērnu, ja dzimuši vairāki); atvaļinājums jāpiešķir ne vēlāk kā 6 mēnešu laikā pēc dzimšanas',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'lateRule': 'Atvaļinājums jāizmanto līdz bērna 6 mēnešu vecumam; pabalstu pieprasa 6 mēnešu laikā no atvaļinājuma pirmās dienas.',
        'processingDays': 10,
        'requires': ['darba ņēmējs vai pašnodarbinātais', 'iemaksas 3 no pēdējiem 6 vai 6 no pēdējiem 24 mēnešiem', 'darba devēja piešķirts atvaļinājums'],
        'legal': [
            ref('Likums "Par maternitātes un slimības apdrošināšanu"', '10.¹ pants (tiesības, 10 darba dienas, par katru bērnu — redakcija no 01.01.2026.), 10.³ pants (80 %), 4. panta pirmā daļa (stāžs), 25. panta pirmā daļa (6 mēneši)', LAW_MS, 'law'),
            ref('Darba likums', '155. panta pirmā daļa — atvaļinājumu piešķir tūlīt pēc bērna piedzimšanas, bet ne vēlāk kā sešu mēnešu laikā', LAW_DL, 'law'),
            ref('VSAA pakalpojuma apraksts', 'Paternitātes pabalsta piešķiršana un izmaksāšana', VSAA + 'paternitates-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Koeficients 1,46 un izpildes termiņš 10 darba dienas ir VSAA skaidrojums'),
        ],
        'source': VSAA + 'paternitates-pabalsta-pieskirsana-un-izmaksasana',
    },
    'berna_piedzimsanas': {
        'name': 'Bērna piedzimšanas pabalsta piešķiršana un izmaksāšana',
        'short': 'Bērna piedzimšanas pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'kind': 'one_time',
        'insurance': False,
        'amount': '600 EUR vienreizējs maksājums par bērnu, kas dzimis no 01.01.2026. (421,17 EUR par bērnu, kas dzimis līdz 31.12.2025.)',
        'period': 'Vienreizējs; apmērs — kāds noteikts bērna piedzimšanas dienā',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'lateRule': 'Pēc 6 mēnešiem pabalstu nepiešķir.',
        'processingDays': 8,
        'requires': ['bērnam piešķirts personas kods un aktīvs statuss Fizisko personu reģistrā', 'pastāvīga dzīvesvieta Latvijā'],
        'legal': [
            ref('Valsts sociālo pabalstu likums', '8. pants (vienam no vecākiem), 4. panta trešā daļa (bērna personas kods), 16. panta pirmā daļa (vienam no vecākiem), 18. panta pirmā daļa (6 mēnešu termiņš)', LAW_VSP, 'law'),
            ref('MK noteikumi Nr. 1546 "Noteikumi par bērna piedzimšanas pabalsta piešķiršanas un izmaksāšanas kārtību"', '2. punkts — 600 euro (MK 22.12.2025. noteikumu Nr. 815 redakcijā, spēkā no 01.01.2026.); 7. punkts — lēmums 10 dienu laikā', MK_1546, 'regulation'),
            ref('VSAA pakalpojuma apraksts', 'Bērna piedzimšanas pabalsta piešķiršana un izmaksāšana', VSAA + 'berna-piedzimsanas-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Izpildes termiņš 8 darba dienas'),
        ],
        'source': VSAA + 'berna-piedzimsanas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'berna_kopsanas': {
        'name': 'Bērna kopšanas pabalsta piešķiršana un izmaksāšana',
        'short': 'Bērna kopšanas pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'kind': 'monthly',
        'insurance': False,
        'amount': '298 EUR mēnesī līdz 1,5 gadu vecumam (no 01.01.2026.); bērnam, kas dzimis līdz 02.11.2026., papildus 42,69 EUR mēnesī no 1,5 līdz 2 gadiem',
        'period': 'Līdz bērna 1,5 gadu vecumam; neatkarīgi no nodarbinātības; kopā ar vecāku pabalstu to saņem viena un tā pati persona',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'lateRule': 'Piesakoties vēlāk par 6 mēnešiem, izmaksā tikai par iepriekšējiem 6 mēnešiem.',
        'processingDays': 22,
        'requires': ['bērnam personas kods un pastāvīga dzīvesvieta Latvijā', 'par periodu nav piešķirts maternitātes pabalsts'],
        'legal': [
            ref('Valsts sociālo pabalstu likums', '7. panta 1.¹ daļa (līdz 1,5 gadiem), 7. panta otrā daļa (kopā ar vecāku pabalstu — vienai personai; ne par maternitātes pabalsta periodu), 7. panta trešā daļa (piemaksa par dvīņiem — MK), 16. panta pirmā daļa, 18. panta pirmā daļa (6 mēneši, izmaksa par iepriekšējiem 6 mēnešiem)', LAW_VSP, 'law'),
            ref('Grozījumi Valsts sociālo pabalstu likumā (spēkā no 01.01.2026.)', 'pārejas noteikumi — 42,69 EUR no 1,5 līdz 2 gadiem bērniem, kas dzimuši līdz 02.11.2026.', 'https://likumi.lv/ta/id/365261', 'law'),
            ref('MK 22.12.2009. noteikumi Nr. 1609 "Noteikumi par bērna kopšanas pabalsta un piemaksas pie bērna kopšanas pabalsta un vecāku pabalsta par dvīņiem vai vairākiem vienās dzemdībās dzimušiem bērniem apmēru …"', '2. punkts — 35 % no minimālo ienākumu mediānas (298 EUR 2026. gadā), pārrēķina katru otro gadu; 16.8.² punkts — piemaksa par dvīņiem 42,69 EUR mēnesī par katru nākamo bērnu no 1,5 līdz 2 gadiem', MK_1609, 'regulation'),
            ref('MK 22.12.2025. noteikumi Nr. 848 (grozījumi noteikumos Nr. 1609)', '1.1. punkts — jaunā 2. punkta redakcija; stājas spēkā 01.01.2026.', MK_1609_2026, 'regulation'),
            ref('VSAA pakalpojuma apraksts', 'Bērna kopšanas pabalsta piešķiršana un izmaksāšana', VSAA + 'berna-kopsanas-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Izpildes termiņš 22 darba dienas'),
        ],
        'source': VSAA + 'berna-kopsanas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'vecaku': {
        'name': 'Vecāku pabalsta piešķiršana un izmaksāšana',
        'short': 'Vecāku pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'kind': 'monthly',
        'insurance': True,
        'amount': '60 % no vidējās iemaksu algas (13 mēneši) vai 43,75 % (19 mēneši); strādājot bērna kopšanas atvaļinājuma vietā — 75 % no šīs summas 2026. gadā',
        'period': '13 mēneši (līdz 1 gada vecumam + nenododamā daļa) vai 19 mēneši (līdz 1,5 gadiem + nenododamā daļa); katram vecākam 2 nenododami kalendāra mēneši līdz bērna 8 gadu vecumam; izvēli nevar mainīt',
        'deadlineFrom': 'birth',
        'deadlineMonths': 6,
        'lateRule': 'Pabalstu pieprasa 6 mēnešu laikā no datuma, no kura to pieprasa.',
        'processingDays': 10,
        'requires': ['darba ņēmējs vai pašnodarbinātais bērna kopšanas atvaļinājumā (vai bez pašnodarbinātā ienākumiem)', 'iemaksas 3 no pēdējiem 6 vai 6 no pēdējiem 24 mēnešiem', 'ne par to pašu periodu, par kuru piešķirts maternitātes pabalsts (izņemot nenododamo daļu)'],
        'options': {'ilgums': ['13 mēneši', '19 mēneši']},
        'legal': [
            ref('Likums "Par maternitātes un slimības apdrošināšanu"', '10.⁴ pants (tiesības; 1.¹ daļa — bērna personas kods un dzīvesvieta no 01.07.2026.; 2. daļa — ne vienlaikus ar maternitātes pabalstu; 4. daļa — 13/19 mēneši; 4.² daļa — nenododamā daļa; 5. daļa — izvēli nemaina), 10.⁶ pants (60 % / 43,75 %; strādājot 50 %), 10.⁷ pants (aptur bezdarbnieka pabalsta laikā), 25. panta pirmā daļa (6 mēneši)', LAW_MS, 'law'),
            ref('Grozījumi likumā "Par maternitātes un slimības apdrošināšanu" (27.11.2025.)', 'pārejas noteikumi — strādājošiem vecākiem 75 % apmērs pagarināts līdz 2026. gada beigām; priekšlaicīgi dzimušiem bērniem no 01.01.2026. ieskaita tikai pēcdzemdību periodu', 'https://likumi.lv/ta/id/364789', 'law'),
            ref('VSAA pakalpojuma apraksts', 'Vecāku pabalsta piešķiršana un izmaksāšana', VSAA + 'vecaku-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Izpildes termiņš 10 darba dienas; VSAA kalkulators Latvija.gov.lv'),
        ],
        'source': VSAA + 'vecaku-pabalsta-pieskirsana-un-izmaksasana',
    },
    'gimenes_valsts': {
        'name': 'Ģimenes valsts pabalsta piešķiršana un izmaksāšana',
        'short': 'Ģimenes valsts pabalsts',
        'group': 'berns',
        'roles': ['māte', 'tēvs'],
        'onePerFamily': True,
        'kind': 'monthly',
        'insurance': False,
        'amount': '25 EUR mēnesī par vienu bērnu, 100 EUR par diviem, 225 EUR par trim, 100 EUR par katru bērnu, ja ir četri vai vairāk; piemaksa par bērnu ar invaliditāti',
        'period': 'No bērna 1 gada līdz 16 gadu vecumam (līdz 20 gadiem, ja mācās un nav precējies)',
        'availableFromYears': 1,
        'deadlineFrom': 'first_birthday',
        'deadlineMonths': 24,
        'lateRule': 'Piesakoties vēlāk par 24 mēnešiem, izmaksā tikai par iepriekšējiem 24 mēnešiem.',
        'processingDays': 10,
        'requires': ['bērnam personas kods un pastāvīga dzīvesvieta Latvijā'],
        'legal': [
            ref('Valsts sociālo pabalstu likums', '6. panta otrā daļa (no 1 līdz 16 gadiem; 16–20 gadi, ja mācās, no 2026. gada arī augstskolā), 6. panta 2.² daļa (apmēri), 6. panta trešā daļa (piemaksa — MK), 16. panta pirmā daļa (vienam no vecākiem), 18. panta 1.¹ daļa (24 mēnešu termiņš)', LAW_VSP, 'law'),
            ref('MK noteikumi Nr. 864 "Kārtība, kādā piešķir un izmaksā ģimenes valsts pabalstu un piemaksu pie ģimenes valsts pabalsta par bērnu ar invaliditāti"', '6. punkts — piemaksa par bērnu ar invaliditāti 160 EUR mēnesī (redakcija spēkā no 01.01.2026.)', MK_864, 'regulation'),
            ref('VSAA pakalpojuma apraksts', 'Ģimenes valsts pabalsta piešķiršana un izmaksāšana', VSAA + 'gimenes-valsts-pabalsta-pieskirsana-un-izmaksasana', 'guidance', 'Izpildes termiņš 10 darba dienas'),
        ],
        'source': VSAA + 'gimenes-valsts-pabalsta-pieskirsana-un-izmaksasana',
    },
    'slimibas': {
        'name': 'Slimības pabalsta piešķiršana un izmaksāšana',
        'short': 'Slimības pabalsts',
        'group': 'slimiba',
        'roles': [],
        'onePerFamily': False,
        'kind': 'one_time',
        'insurance': True,
        'amount': '80 % no vidējās apdrošināšanas iemaksu algas no 10. darbnespējas dienas (lapa B); 2.–9. dienu apmaksā darba devējs (lapa A)',
        'period': 'Līdz 26 nedēļām nepārtraukti vai 52 nedēļām trīs gados',
        'deadlineFrom': 'incapacity_start',
        'deadlineMonths': 6,
        'lateRule': 'Pēc 6 mēnešiem pabalstu nepiešķir.',
        'processingDays': 10,
        'requires': ['darba ņēmējs vai pašnodarbinātais', 'iemaksas 3 no pēdējiem 6 vai 6 no pēdējiem 24 mēnešiem', 'noslēgta darbnespējas lapa B e-veselībā'],
        'legal': [
            ref('Likums "Par maternitātes un slimības apdrošināšanu"', '11. pants (tiesības), 13. pants (no 10. dienas; 26/52 nedēļas), 17. pants (80 %), 36. pants (darba devēja apmaksātās dienas), 25. panta pirmā daļa (6 mēneši)', LAW_MS, 'law'),
            ref('VSAA pakalpojuma apraksts', 'Slimības pabalsta piešķiršana un izmaksāšana', VSAA + 'slimibas-pabalsta-pieskirsana-un-izmaksasana', 'guidance'),
        ],
        'source': VSAA + 'slimibas-pabalsta-pieskirsana-un-izmaksasana',
    },
    'bezdarbnieka': {
        'name': 'Bezdarbnieka pabalsta piešķiršana un izmaksāšana',
        'short': 'Bezdarbnieka pabalsts',
        'group': 'bezdarbs',
        'roles': [],
        'onePerFamily': False,
        'kind': 'monthly',
        'insurance': True,
        'amount': '50–65 % no vidējās iemaksu algas atkarībā no stāža; 1.–2. mēnesī pilnā apmērā, 3.–4. mēnesī 75 %, 5.–6. mēnesī 50 %, 7.–8. mēnesī 45 %',
        'period': 'Līdz 8 mēnešiem 12 mēnešu periodā; piešķir no iesnieguma dienas',
        'deadlineFrom': 'unemployed_status',
        'deadlineMonths': None,
        'lateRule': 'Piešķir no iesnieguma iesniegšanas dienas.',
        'processingDays': 22,
        'requires': ['NVA piešķirts bezdarbnieka statuss', 'apdrošināšanas stāžs vismaz 1 gads', 'iemaksas 12 no pēdējiem 16 mēnešiem'],
        'legal': [
            ref('Likums "Par apdrošināšanu bezdarba gadījumam"', '3. panta pirmā daļa (bezdarbnieka statuss), 5. panta pirmā daļa (stāžs ≥ 1 gads; 12 no 16 mēnešiem), 7. panta pirmā daļa (50–65 %), 9. pants (8 mēneši; 75/50/45 %), 13. panta pirmā daļa (no iesnieguma dienas)', LAW_BEZ, 'law'),
            ref('VSAA pakalpojuma apraksts', 'Bezdarbnieka pabalsta piešķiršana un izmaksāšana', VSAA + 'bezdarbnieka-pabalsta-pieskirsana-un-izmaksasana', 'guidance'),
        ],
        'source': VSAA + 'bezdarbnieka-pabalsta-pieskirsana-un-izmaksasana',
    },
}

# Child benefits that the law grants to one and the same person per child.
SAME_PERSON_GROUP = ('berna_kopsanas', 'vecaku')


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(day.day, last))


def childbirth_amount(birth):
    for since, amount in CHILDBIRTH_AMOUNT:
        if birth >= since:
            return amount
    return CHILDBIRTH_AMOUNT[-1][1]


def childcare_schedule(birth):
    """Monthly amounts and the age they stop at, by birth date (2026 transition)."""
    schedule = [{'until': add_months(birth, 18).isoformat(), 'monthly': CHILDCARE_MONTHLY}]
    if birth <= CHILDCARE_TRANSITION_BIRTH:
        schedule.append({'until': add_months(birth, 24).isoformat(), 'monthly': CHILDCARE_REDUCED})
    return schedule


def family_benefit_monthly(children):
    """Monthly family state benefit for ``children`` eligible children (6. panta 2.² daļa)."""
    if children <= 0:
        return 0.0
    return FAMILY_BENEFIT.get(children, 100.0 * children)


def insured(months_paid_last_6, months_paid_last_24):
    """4. panta pirmā daļa: 3 of the last 6 or 6 of the last 24 months."""
    return months_paid_last_6 >= 3 or months_paid_last_24 >= 6


def child_benefit_status(code, role, birth, today, own_application, other_applications, *, insured_person=True, family_children=1):
    """Return the status of one child benefit for one parent.

    own_application is this person's application row (or None);
    other_applications maps benefit code -> the other parent's application for
    the same child. ``insured_person`` is the social-insurance test for the
    insurance-based benefits; ``family_children`` sizes the family benefit.
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
        # Pregnancy leave begins before the birth; the demo approximates it with 70 days.
        leave_start = birth - timedelta(days=70)
        available_from = leave_start
        deadline = add_months(leave_start, rule['deadlineMonths'])

    result = {
        'code': code,
        'name': rule['name'],
        'short': rule['short'],
        'amount': rule['amount'],
        'period': rule['period'],
        'requires': rule['requires'],
        'options': rule.get('options'),
        'onePerFamily': rule['onePerFamily'],
        'kind': rule['kind'],
        'lateRule': rule['lateRule'],
        'processingDays': rule['processingDays'],
        'source': rule['source'],
        'legal': rule['legal'],
        'verifiedAt': VERIFIED_AT,
        'availableFrom': available_from.isoformat(),
        'deadline': deadline.isoformat() if deadline else None,
        'daysLeft': (deadline - today).days if deadline else None,
        'windowDays': (deadline - available_from).days if deadline else None,
        'estimate': None,
    }
    if code == 'berna_piedzimsanas':
        result['estimate'] = {'oneTime': childbirth_amount(birth)}
    elif code == 'berna_kopsanas':
        result['estimate'] = {'schedule': childcare_schedule(birth)}
    elif code == 'gimenes_valsts':
        result['estimate'] = {'monthly': family_benefit_monthly(family_children), 'children': family_children}

    other_same_person = any(other_applications.get(other) for other in SAME_PERSON_GROUP) if code in SAME_PERSON_GROUP else False
    if role not in rule['roles']:
        result['status'] = 'nav_attiecas'
        result['statusText'] = 'Attiecas uz otru vecāku'
    elif own_application:
        result['status'] = own_application['status']
        result['statusText'] = {'iesniegts': 'Iesniegts VSAA', 'izskatisana': 'Izskatīšanā', 'pieskirts': 'Piešķirts', 'atteikts': 'Atteikts'}.get(own_application['status'], own_application['status'])
        result['application'] = own_application
    elif other_applications.get(code) and rule['onePerFamily']:
        result['status'] = 'otrs_vecaks'
        result['statusText'] = 'Pieteicis otrs vecāks'
    elif other_same_person:
        result['status'] = 'otrs_vecaks'
        result['statusText'] = 'Saņem otrs vecāks (kopā ar vecāku pabalstu)' if code == 'berna_kopsanas' else 'Saņem otrs vecāks (kopā ar bērna kopšanas pabalstu)'
    elif rule['insurance'] and not insured_person:
        result['status'] = 'nav_apdrosinats'
        result['statusText'] = 'Nav izpildīts iemaksu nosacījums'
    elif today < available_from:
        result['status'] = 'gaidams'
        result['statusText'] = f'Pieejams no {available_from:%d.%m.%Y}'
    elif deadline and today > deadline and rule['kind'] == 'one_time':
        result['status'] = 'nokavets'
        result['statusText'] = 'Pieteikšanās termiņš pagājis'
    elif deadline and today > deadline:
        result['status'] = 'pieejams'
        result['late'] = True
        result['statusText'] = 'Pieejams; termiņš pagājis — izmaksā ierobežoti'
    elif deadline and (deadline - today).days <= 30:
        result['status'] = 'steidzami'
        result['statusText'] = f'Termiņš pēc {(deadline - today).days} dienām'
    else:
        result['status'] = 'pieejams'
        result['statusText'] = 'Pieejams, nav pieteikts'
    return result


def legal_references():
    """All benefit rules with sources, for the data-usage page and the API."""
    return {'verifiedAt': VERIFIED_AT, 'benefits': {code: {'name': rule['name'], 'short': rule['short'], 'legal': rule['legal'], 'amount': rule['amount'], 'period': rule['period'], 'lateRule': rule['lateRule']} for code, rule in BENEFITS.items()}}
