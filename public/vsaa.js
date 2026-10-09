// Mana VSAA dashboard: renders the signed-in person's fictional VSAA situation and the demo actions
// (apply with a prefilled form, notify the other parent, reminders). All data comes from /api/vsaa/*.
(() => {
  const $ = selector => document.querySelector(selector);
  const status = $('#page-status');
  let dashboard = null;

  const fmtDate = iso => iso ? new Date(iso).toLocaleDateString('lv-LV', {day: '2-digit', month: '2-digit', year: 'numeric'}) : '—';
  const fmtMonth = key => { const [year, month] = key.split('-'); return `${month}.${year}`; };
  const fmtMoney = value => value == null ? '' : new Intl.NumberFormat('lv-LV', {style: 'currency', currency: 'EUR', maximumFractionDigits: 2}).format(value);
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value == null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key === 'html') node.innerHTML = value;
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? '' : value);
    }
    for (const child of children.flat()) if (child != null) node.append(child.nodeType ? child : document.createTextNode(child));
    return node;
  };
  const icon = path => { const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '1.8'); svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('aria-hidden', 'true'); svg.innerHTML = path; return svg; };
  const ICONS = {send: '<path d="M4 12 20 4l-4 16-4-7z"/>', check: '<path d="m5 12 5 5L20 7"/>', arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>', bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>'};

  function token() { try { return JSON.parse(localStorage.getItem('faketvijaSession'))?.token; } catch { return null; } }
  async function request(path, method = 'GET', body) {
    const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token() || ''}`, ...(body ? {'Content-Type': 'application/json'} : {})}, body: body && JSON.stringify(body)});
    if (response.status === 401) { localStorage.removeItem('faketvijaSession'); location.replace('login.html'); throw new Error('unauthorized'); }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.error || 'request_failed'); error.code = data.error; throw error; }
    return data;
  }
  const ERRORS = {bank_account_unavailable:'IBAN konts neeksistē vai jums nav tam piekļuves.', invalid_iban: 'Konta numurs nav pareizs. Latvijas IBAN ir 21 zīme: LV, 2 cipari, 4 bankas burti, 13 cipari.', not_available: 'Šo pabalstu šobrīd nevar pieteikt (jau pieteikts vai nav pieejams).', not_eligible: 'Nav izpildīts iemaksu nosacījums: 12 mēneši no pēdējiem 16.', unknown_benefit: 'Nezināms pakalpojums.', no_other_parent: 'Otrs vecāks reģistros nav norādīts.'};
  const setStatus = text => setTranslatedStatus(status, text);

  function chip(state, text) { return el('span', {class: `chip ${state}`, text}); }

  // --- Summary tiles -------------------------------------------------------------------
  function renderSummary(summary) {
    const tiles = [
      ['#berni', summary.available, 'Pieejami, nepieteikti pabalsti'],
      ['#atgadinajumi', summary.urgent, 'Steidzami termiņi', 'urgent'],
      ['#slimiba', summary.unpaidSickLeaves, 'Neizmaksātas darbnespējas lapas'],
      ['#pieteikumi', summary.applications, 'Iesniegtie pieteikumi'],
    ];
    $('#summary').replaceChildren(...tiles.map(([href, count, label, extra]) => el('a', {class: `status-tile ${extra && count ? extra : ''}`, href},
      el('span', {class: `count ${count ? '' : 'zero'}`, text: String(count), 'data-no-translate': true}), el('span', {class: 'label', text: label}))));
  }

  // --- Children and the benefit checklist -----------------------------------------------
  function benefitRow(child, benefit) {
    const row = el('li', {class: `benefit ${['nav_attiecas', 'nokavets'].includes(benefit.status) ? 'inactive' : ''}`});
    row.append(el('div', {}, el('div', {class: 'title', text: benefit.short}, el('span', {class: 'official', text: benefit.name}))));
    row.append(el('div', {class: 'amount', text: benefit.amount}));
    const deadline = el('div', {class: 'deadline'});
    if (benefit.status === 'gaidams') {
      deadline.append(el('span', {}, 'Pieejams no ', el('strong', {text: fmtDate(benefit.availableFrom), 'data-no-translate': true})));
    } else if (benefit.deadline && !['nav_attiecas', 'pieskirts', 'iesniegts', 'otrs_vecaks'].includes(benefit.status)) {
      const used = Math.min(1, Math.max(0, 1 - benefit.daysLeft / benefit.windowDays));
      deadline.append(el('span', {}, 'Pieteikties līdz ', el('strong', {text: fmtDate(benefit.deadline), 'data-no-translate': true})));
      deadline.append(el('span', {class: `window ${benefit.daysLeft <= 30 ? 'urgent' : ''}`, role: 'img', 'aria-label': `Atlikušas ${benefit.daysLeft} dienas`}, el('i', {style: `width:${Math.round(used * 100)}%`})));
      deadline.append(el('span', {text: benefit.daysLeft < 0 ? 'Termiņš pagājis' : `Atlikušas ${benefit.daysLeft} dienas`}));
    } else if (benefit.application) {
      deadline.append(el('span', {}, 'Iesniegts ', el('strong', {text: fmtDate(benefit.application.submittedAt), 'data-no-translate': true})), el('span', {text: `Lēmums ${benefit.processingDays} darba dienu laikā`}));
    } else {
      deadline.append(el('span', {text: benefit.period}));
    }
    row.append(deadline);
    const actions = el('div', {class: 'actions'}, chip(benefit.status, benefit.statusText));
    if (['pieejams', 'steidzami'].includes(benefit.status)) {
      actions.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => openApply(benefit, {child})}, 'Pieteikties', icon(ICONS.arrow)));
    } else if (benefit.status === 'otrs_vecaks' || benefit.status === 'nav_attiecas') {
      actions.append(el('a', {class: 'section-link', href: benefit.source, target: '_blank', rel: 'noopener', text: 'Par pabalstu'}));
    }
    row.append(actions);
    return row;
  }

  function renderChildren(children) {
    const root = $('#children');
    if (!children.length) {
      root.replaceChildren(el('p', {class: 'empty', text: 'Reģistros nav bērnu, par kuriem būtu pieejami pabalsti. Piedzimstot bērnam, šeit parādīsies visi seši VSAA pabalsti ar termiņiem.'}));
      return;
    }
    root.replaceChildren(...children.map(child => {
      const card = el('article', {class: 'child-card', 'aria-label': `Bērns ${child.firstName}`});
      card.append(el('header', {}, el('h3', {text: `${child.firstName} ${child.lastName || ''}`, 'data-no-translate': true}),
        el('div', {class: 'meta'}, el('span', {}, 'Dzimis ', el('span', {text: fmtDate(child.birthDate), 'data-no-translate': true}), ` · ${child.ageText}`),
          el('span', {}, 'Personas kods: ', el('strong', {text: child.personasKods, 'data-no-translate': true})),
          el('span', {}, 'Jūsu loma: ', el('strong', {text: child.myRole})),
          el('span', {}, 'Deklarētā pašvaldība: ', el('strong', {text: child.municipal.municipality || '—', 'data-no-translate': true})))));
      card.append(el('ul', {class: 'benefit-list'}, child.benefits.map(benefit => benefitRow(child, benefit))));
      const footer = el('footer');
      const shared = child.benefits.filter(b => b.onePerFamily && ['pieejams', 'steidzami'].includes(b.status)).map(b => b.short);
      if (shared.length) footer.append(el('p', {class: 'compare-note', text: `${shared.join(', ')} — saņem tikai viens no vecākiem. Pirms pieteikšanās salīdziniet, kuram no jums pabalsts būs lielāks (VSAA kalkulators Latvija.gov.lv).`}));
      const parentRow = el('div', {class: 'parent-row'});
      if (child.otherParent.known) {
        parentRow.append(el('p', {text: 'Otra vecāka dati privātuma dēļ netiek rādīti. VSAA var nosūtīt otram vecākam paziņojumu ar viņam pieejamajiem pabalstiem, lai jūs varētu salīdzināt un vienoties.'}));
        const sent = el('span', {class: 'sent'});
        if (child.otherParent.notifiedAt) sent.textContent = `Nosūtīts ${fmtDate(child.otherParent.notifiedAt)}`;
        const button = el('button', {class: 'gov-btn secondary small', type: 'button', onclick: async () => {
          button.disabled = true; setStatus('Sūta paziņojumu otram vecākam…');
          try { const data = await request('/api/vsaa/notify-other-parent', 'POST', {childId: child.id}); render(data.dashboard); setStatus(data.notified ? 'Paziņojums otram vecākam nosūtīts uz e-adresi.' : 'Paziņojums šodien jau ir nosūtīts.'); }
          catch (error) { setStatus(ERRORS[error.code] || 'Neizdevās nosūtīt paziņojumu. Mēģiniet vēlreiz.'); button.disabled = false; }
        }}, icon(ICONS.send), 'Nosūtīt otram vecākam');
        parentRow.append(el('div', {style: 'display:flex;gap:12px;align-items:center;flex-wrap:wrap'}, sent, button));
      } else {
        parentRow.append(el('p', {text: 'Otrs vecāks reģistros nav norādīts, tāpēc pabalstu salīdzinājums nav nepieciešams.'}));
      }
      footer.append(parentRow);
      footer.append(el('div', {class: 'parent-row'}, el('p', {}, 'Pašvaldības vienreizējais pabalsts par bērna piedzimšanu — tikai jūsu deklarētajā pašvaldībā: ', el('strong', {text: child.municipal.municipality || '—', 'data-no-translate': true}), '. Citu novadu pakalpojumi šeit netiek rādīti.'),
        el('a', {class: 'gov-btn secondary small', href: child.municipal.lifeSituationUrl, target: '_blank', rel: 'noopener'}, 'Pašvaldības pabalsti')));
      card.append(footer);
      return card;
    }));
  }

  // --- Sick leaves ----------------------------------------------------------------------
  function renderSickLeaves(leaves) {
    const root = $('#sick-leaves');
    if (!leaves.length) { root.replaceChildren(el('p', {class: 'empty', text: 'Nav reģistrētu darbnespējas lapu B. Ja saslimsiet ilgāk par 9 dienām, noslēgtā lapa parādīsies šeit ar pieteikšanās iespēju.'})); return; }
    root.replaceChildren(...leaves.map(leave => {
      const row = el('article', {class: `leave ${leave.status === 'neizmaksata' ? 'open' : ''}`});
      row.append(el('div', {}, el('div', {class: 'title', text: `Darbnespējas lapa ${leave.kind} · ${leave.number}`, 'data-no-translate': true}), el('div', {class: 'sub', text: leave.employer, 'data-no-translate': true})));
      row.append(el('dl', {}, el('dt', {text: 'Periods'}), el('dd', {text: `${fmtDate(leave.dateFrom)} – ${fmtDate(leave.dateTo)} (${leave.days} d.)`, 'data-no-translate': true}), el('dt', {text: 'Noslēgta'}), el('dd', {text: fmtDate(leave.closedAt), 'data-no-translate': true})));
      row.append(el('dl', {}, el('dt', {text: 'VSAA apmaksā'}), el('dd', {text: `${leave.benefitDays} dienas (no 10. dienas)`}), el('dt', {text: 'Pieteikties līdz'}), el('dd', {text: fmtDate(leave.deadline), 'data-no-translate': true})));
      const actions = el('div', {class: 'actions', style: 'display:grid;gap:8px;justify-items:end'}, chip(leave.status, leave.statusText));
      if (leave.status === 'neizmaksata') actions.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => openApply({code: 'slimibas', short: 'Slimības pabalsts', name: 'Slimības pabalsta piešķiršana un izmaksāšana', processingDays: 10}, {leave})}, 'Pieprasīt pabalstu', icon(ICONS.arrow)));
      row.append(actions);
      return row;
    }));
  }

  // --- Employment, contributions and vacancies ------------------------------------------
  function renderEmployment(employment) {
    const root = $('#employment');
    const headline = {nodarbinats: 'Iemaksas tiek veiktas regulāri', iemaksas_partrauktas: `Iemaksas nav veiktas ${employment.gapMonths} mēnešus`, bezdarbnieks: 'Reģistrēts bezdarbnieka statuss'}[employment.status];
    root.replaceChildren(el('h3', {text: headline}));
    const months = el('ul', {class: 'months', 'aria-label': 'Sociālās iemaksas pa mēnešiem'});
    employment.months.forEach((item, index) => months.append(el('li', {class: `${item.paid ? '' : 'gap'} ${index === employment.months.length - 1 ? 'current' : ''}`, title: item.paid ? `${fmtMonth(item.month)}: ${item.employer}` : `${fmtMonth(item.month)}: iemaksas nav`}, el('i'), el('span', {text: item.month.slice(5), 'data-no-translate': true}))));
    root.append(months);
    root.append(el('dl', {class: 'facts'}, el('dt', {text: 'Iemaksas pēdējos 16 mēnešos'}), el('dd', {text: `${employment.monthsWithContributions} no 16 (pabalstam vajag 12)`}),
      el('dt', {text: 'Pēdējais darba devējs'}), el('dd', {text: employment.lastEmployer || '—', 'data-no-translate': true}),
      el('dt', {text: 'Pēdējās iemaksas'}), el('dd', {text: employment.lastContributionMonth ? fmtMonth(employment.lastContributionMonth) : '—', 'data-no-translate': true}),
      el('dt', {text: 'NVA bezdarbnieka statuss'}), el('dd', {text: employment.nvaRegistered ? 'Reģistrēts' : 'Nav reģistrēts'})));
    if (employment.application) {
      root.append(el('p', {style: 'margin:16px 0 0'}, chip(employment.application.status, employment.application.statusText), ' ', el('span', {text: `Bezdarbnieka pabalsts iesniegts ${fmtDate(employment.application.submittedAt)}. ${employment.rule.amount}.`})));
    } else if (employment.status === 'iemaksas_partrauktas') {
      root.append(el('p', {style: 'margin:16px 0 12px', text: employment.benefitEligible
        ? 'Iemaksu nosacījums bezdarbnieka pabalstam ir izpildīts. Reģistrējieties NVA un tajā pašā dienā iesniedziet VSAA iesniegumu — šeit abus soļus var veikt kopā.'
        : 'Bezdarbnieka pabalstam nepietiek iemaksu mēnešu, bet NVA bezdarbnieka statuss dod bezmaksas karjeras konsultācijas un apmācības.'}));
      root.append(el('button', {class: 'gov-btn', type: 'button', disabled: !employment.benefitEligible, onclick: () => openApply({code: 'bezdarbnieka', short: 'Bezdarbnieka pabalsts', name: 'Bezdarbnieka pabalsta piešķiršana un izmaksāšana', processingDays: 22}, {employment})}, 'Reģistrēties NVA un pieteikties pabalstam', icon(ICONS.arrow)));
    } else {
      root.append(el('p', {style: 'margin:16px 0 0', text: 'Ja iemaksas apstāsies, VSAA atgādinās reģistrēties NVA un parādīs bezdarbnieka pabalsta nosacījumus šeit.'}));
    }
  }

  function renderVacancies(data) {
    const root = $('#vacancies');
    root.replaceChildren(el('h3', {}, 'Vakances: ', el('span', {text: data.municipality || 'Latvija', 'data-no-translate': true})));
    root.append(el('p', {style: 'margin:6px 0 0;font-size:14px'}, el('strong', {text: String(data.count), 'data-no-translate': true}), ` NVA reģistrētas vakances jūsu pašvaldībā, ${data.total} visā Latvijā (${fmtDate(data.retrievedAt)}).`));
    if (data.samples.length) {
      root.append(el('ul', {class: 'vacancy-list'}, data.samples.map(job => el('li', {'data-no-translate': true}, el('span', {class: 'job', text: job.nosaukums}),
        el('span', {text: `${job.kategorija} · ${job.algaNo ? fmtMoney(job.algaNo) + (job.algaLidz && job.algaLidz !== job.algaNo ? ' – ' + fmtMoney(job.algaLidz) : '') : 'alga nav norādīta'}`}),
        el('span', {class: 'where', text: `${job.vieta} · līdz ${fmtDate(job.pieteiksanasTermins)}`}),
        job.vakancesId ? el('a', {href: data.portal + job.vakancesId, target: '_blank', rel: 'noopener', text: 'Skatīt NVA portālā'}) : null))));
    }
    root.append(el('p', {style: 'margin:14px 0 0'}, el('a', {class: 'gov-btn secondary small', href: 'https://cvvp.nva.gov.lv/#/pub/vakances/', target: '_blank', rel: 'noopener'}, 'Visas vakances NVA portālā')));
    root.append(el('p', {class: 'source-note'}, 'Avots: ', el('a', {href: data.source, target: '_blank', rel: 'noopener', text: 'Vakances (NVA), data.gov.lv'}), `, ${data.license}. Dienas momentuzņēmums.`));
  }

  // --- Reminders -------------------------------------------------------------------------
  function renderReminders(reminders, person) {
    $('#reminders-toggle').checked = person.remindersEnabled;
    const root = $('#reminders');
    if (!reminders.length) { root.replaceChildren(el('li', {class: 'empty', text: 'Šobrīd nav nekā, kas būtu jāpiesaka vai jāatceras.'})); return; }
    root.replaceChildren(...reminders.map(item => {
      const li = el('li', {class: `reminder ${item.level}`});
      const when = el('span', {class: 'when'});
      if (item.daysLeft != null) when.append(el('b', {text: String(item.daysLeft), 'data-no-translate': true}), 'dienas');
      else when.append(el('b', {text: '!', 'data-no-translate': true}), item.level === 'info' ? 'info' : 'tagad');
      li.append(when, el('div', {}, el('h3', {text: item.title}), el('p', {text: item.text})));
      if (item.action === 'apply') {
        li.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => {
          if (item.benefitCode === 'slimibas') { const leave = dashboard.sickLeaves.find(l => l.id === item.sickLeaveId); openApply({code: 'slimibas', short: 'Slimības pabalsts', name: 'Slimības pabalsta piešķiršana un izmaksāšana', processingDays: 10}, {leave}); }
          else if (item.benefitCode === 'bezdarbnieka') openApply({code: 'bezdarbnieka', short: 'Bezdarbnieka pabalsts', name: 'Bezdarbnieka pabalsta piešķiršana un izmaksāšana', processingDays: 22}, {employment: dashboard.employment});
          else { const child = dashboard.children.find(c => c.id === item.childId); openApply(child.benefits.find(b => b.code === item.benefitCode), {child}); }
        }}, 'Pieteikties'));
      } else if (item.action === 'profile') {
        li.append(el('a', {class: 'gov-btn secondary small', href: '#profile-alert', onclick: () => $('#iban-input').focus()}, 'Pievienot kontu'));
      }
      return li;
    }));
  }

  // --- Applications ----------------------------------------------------------------------
  function renderApplications(applications) {
    const root = $('#applications');
    if (!applications.length) { root.replaceChildren(el('p', {class: 'empty', text: 'Vēl nav iesniegtu pieteikumu. Pieteiktie pakalpojumi un VSAA lēmumi parādīsies šeit un e-adresē.'})); return; }
    root.replaceChildren(el('ul', {class: 'leave-list', style: 'list-style:none;padding:0;margin:0'}, applications.map(app => {
      const child = app.childId && dashboard.children.find(c => c.id === app.childId);
      const leave = app.sickLeaveId && dashboard.sickLeaves.find(l => l.id === app.sickLeaveId);
      const extra = Object.entries(app.details).filter(([key]) => key !== 'seed').map(([key, value]) => `${key}: ${value}`).join(' · ');
      return el('li', {class: 'leave'}, el('div', {}, el('div', {class: 'title', text: app.name}), el('div', {class: 'sub', text: child ? `Bērns: ${child.firstName}` : leave ? `Lapa ${leave.number}` : 'Bez piesaistes', 'data-no-translate': true})),
        el('dl', {}, el('dt', {text: 'Iesniegts'}), el('dd', {text: fmtDate(app.submittedAt), 'data-no-translate': true})),
        el('dl', {}, el('dt', {text: 'Detaļas'}), el('dd', {text: extra || '—', 'data-no-translate': true})),
        el('div', {class: 'actions'}, chip(app.status, app.statusText)));
    })));
  }

  // --- Open-data statistics for the person's municipality -------------------------------
  async function renderStatistics(municipality) {
    const root = $('#statistics');
    try {
      const [vsaa, gvp] = await Promise.all(['data/vsaa-statistics.json', 'data/gimenes-valsts-pabalsts.json'].map(url => fetch(url).then(r => r.json())));
      const find = (data, name) => { const row = data.rows.find(r => r[3] === name); return row && Object.fromEntries(data.columns.map((key, i) => [key, row[i]])); };
      const local = find(vsaa, municipality), national = find(vsaa, 'Kopā');
      const localGvp = find(gvp, municipality), nationalGvp = find(gvp, 'Kopā');
      root.replaceChildren();
      if (local && national) {
        const items = [['slimibasPabalsti', 'Slimības pabalsti'], ['bezdarbniekuPabalsti', 'Bezdarbnieku pabalsti'], ['maternitatesPabalsti', 'Maternitātes pabalsti'], ['paternitatesPabalsti', 'Paternitātes pabalsti'], ['vecakuUnBernaKopsanasPabalsti', 'Vecāku un bērna kopšanas pabalsti'], ['gimenesValstsPabalsti', 'Ģimenes valsts pabalsti']];
        const max = Math.max(...items.map(([key]) => local[key]));
        root.append(el('div', {class: 'gov-panel muted', style: 'margin:0'}, el('h3', {}, 'Pabalstu saņēmēji: ', el('span', {text: municipality, 'data-no-translate': true})), el('p', {style: 'margin:4px 0 0;font-size:13px;color:var(--gov-muted)', text: `VSAA administrētie pakalpojumi, ${fmtMonth(vsaa.period)}`}),
          el('ul', {class: 'bars'}, items.map(([key, label]) => el('li', {}, el('span', {text: label}), el('span', {class: 'value', text: `${local[key].toLocaleString('lv-LV')} (${(100 * local[key] / national[key]).toFixed(1)} % no valsts)`, 'data-no-translate': true}), el('span', {class: 'bar'}, el('i', {style: `width:${Math.max(1, 100 * local[key] / max)}%`}))))),
          el('p', {class: 'source-note'}, 'Avots: ', el('a', {href: vsaa.source, target: '_blank', rel: 'noopener', text: vsaa.title}), ` (${vsaa.publisher}), ${vsaa.license}.`)));
      }
      if (localGvp && nationalGvp) {
        const items = [['par1Bernu', 'Par 1 bērnu'], ['par2Berniem', 'Par 2 bērniem'], ['par3Berniem', 'Par 3 bērniem'], ['par4Berniem', 'Par 4 bērniem'], ['par5Berniem', 'Par 5 bērniem'], ['par6UnVairakBerniem', 'Par 6 un vairāk']];
        root.append(el('div', {class: 'gov-panel muted', style: 'margin:0'}, el('h3', {}, 'Ģimenes valsts pabalsts: ', el('span', {text: `${localGvp.kopa.toLocaleString('lv-LV')} ģimenes`, 'data-no-translate': true})), el('p', {style: 'margin:4px 0 0;font-size:13px;color:var(--gov-muted)', text: `Saņēmēji pēc bērnu skaita, ${fmtMonth(gvp.period)}; Latvijā kopā ${nationalGvp.kopa.toLocaleString('lv-LV')}`}),
          el('ul', {class: 'bars secondary'}, items.map(([key, label]) => el('li', {}, el('span', {text: label}), el('span', {class: 'value', text: `${localGvp[key].toLocaleString('lv-LV')} (${(100 * localGvp[key] / localGvp.kopa).toFixed(0)} %)`, 'data-no-translate': true}), el('span', {class: 'bar'}, el('i', {style: `width:${Math.max(1, 100 * localGvp[key] / localGvp.kopa)}%`}))))),
          el('p', {class: 'source-note'}, 'Avots: ', el('a', {href: gvp.source, target: '_blank', rel: 'noopener', text: gvp.title}), ` (${gvp.publisher}), ${gvp.license}.`)));
      }
      if (!root.children.length) root.append(el('p', {class: 'empty', text: 'Šai pašvaldībai statistika atvērtajos datos nav atrasta.'}));
      applyLanguage();
    } catch { root.replaceChildren(el('p', {class: 'empty', text: 'Statistiku neizdevās ielādēt.'})); }
  }

  // --- Prefilled application dialog ------------------------------------------------------
  function openApply(benefit, context) {
    const dialog = $('#apply-dialog');
    const person = dashboard.person;
    const form = el('form', {method: 'dialog'});
    form.append(el('button', {class: 'dialog-close', type: 'button', 'aria-label': 'Aizvērt', onclick: () => dialog.close()}, '×'));
    form.append(el('h2', {id: 'apply-title', text: benefit.short}), el('p', {class: 'official', text: `E-pakalpojums: ${benefit.name}`}));
    const facts = el('dl', {class: 'prefilled'}, el('div', {}, el('dt', {text: 'Iesniedzējs'}), el('dd', {text: `${person.firstName} ${person.lastName}`, 'data-no-translate': true})), el('div', {}, el('dt', {text: 'Personas kods'}), el('dd', {text: person.personasKods, 'data-no-translate': true})), el('div', {}, el('dt', {text: 'Deklarētā dzīvesvieta'}), el('dd', {text: person.address, 'data-no-translate': true})));
    if (context.child) facts.append(el('div', {}, el('dt', {text: 'Bērns'}), el('dd', {text: `${context.child.firstName}, dz. ${fmtDate(context.child.birthDate)}`, 'data-no-translate': true})));
    if (context.leave) facts.append(el('div', {}, el('dt', {text: 'Darbnespējas lapa'}), el('dd', {text: `${context.leave.number}, ${fmtDate(context.leave.dateFrom)} – ${fmtDate(context.leave.dateTo)}`, 'data-no-translate': true})));
    if (context.employment) facts.append(el('div', {}, el('dt', {text: 'Iemaksu mēneši'}), el('dd', {text: `${context.employment.monthsWithContributions} no 16`, 'data-no-translate': true})));
    form.append(facts, el('p', {class: 'prefilled-note', text: 'Aizpildīts no valsts reģistriem — nav jāievada vēlreiz. Darba devēja ziņas VSAA saņem no VID.'}));
    const ibanField = el('label', {class: 'field'}, 'Konts pabalsta izmaksai (IBAN)', el('input', {name: 'iban', value: person.iban || '', placeholder: 'LV00 BANK 0000 0000 0000 0', required: true, autocomplete: 'off', maxlength: '26'}), el('span', {class: 'hint', text: 'Saglabājas profilā; nākamajiem pieteikumiem to vairs nevajadzēs ievadīt.'}));
    form.append(ibanField);
    if (benefit.options) {
      for (const [name, values] of Object.entries(benefit.options)) {
        const choice = el('fieldset', {class: 'field choice', style: 'border:0;padding:0;margin:0'}, el('legend', {text: name === 'ilgums' ? 'Pabalsta ilgums' : name, style: 'margin-bottom:6px'}));
        values.forEach((value, index) => choice.append(el('label', {}, el('input', {type: 'radio', name: `opt-${name}`, value, checked: index === 0}), value === '13 mēneši' ? '13 mēneši — lielāks ikmēneša maksājums' : value === '19 mēneši' ? '19 mēneši — mazāks maksājums, ilgāks periods' : value)));
        form.append(choice);
      }
    }
    if (benefit.code === 'bezdarbnieka') form.append(el('p', {class: 'prefilled-note', text: 'Vienā solī: NVA reģistrē bezdarbnieka statusu, VSAA saņem pabalsta iesniegumu. Demonstrācijā abi soļi notiek tikai prototipa datubāzē.'}));
    const dialogStatus = el('p', {class: 'dialog-status', role: 'status'});
    const submit = el('button', {class: 'gov-btn', type: 'submit'}, icon(ICONS.check), 'Iesniegt VSAA');
    form.append(dialogStatus, el('div', {class: 'dialog-actions'}, el('button', {class: 'gov-btn secondary', type: 'button', onclick: () => dialog.close()}, 'Atcelt'), submit));
    form.addEventListener('submit', async event => {
      event.preventDefault();
      submit.disabled = true; setTranslatedStatus(dialogStatus, 'Iesniedz…');
      const options = {};
      form.querySelectorAll('input[type=radio]:checked').forEach(input => { options[input.name.replace('opt-', '')] = input.value; });
      try {
        const data = await request('/api/vsaa/apply', 'POST', {benefitCode: benefit.code, childId: context.child?.id, sickLeaveId: context.leave?.id, iban: form.iban.value, options});
        render(data.dashboard);
        dialog.replaceChildren(el('div', {class: 'dialog-ok'}, icon(ICONS.check), el('h2', {text: 'Iesniegums iesniegts'}), el('p', {text: `${benefit.name}: VSAA lēmums paredzams ${benefit.processingDays} darba dienu laikā. Apstiprinājums nosūtīts uz e-adresi.`}), el('button', {class: 'gov-btn', type: 'button', onclick: () => dialog.close()}, 'Aizvērt')));
        applyLanguage();
        setStatus('');
      } catch (error) {
        setTranslatedStatus(dialogStatus, ERRORS[error.code] || 'Iesniegumu neizdevās saglabāt. Mēģiniet vēlreiz.');
        submit.disabled = false;
      }
    });
    dialog.replaceChildren(form);
    applyLanguage();
    dialog.showModal();
    form.iban.focus();
  }

  // --- Profile alert and reminder toggle ---------------------------------------------------
  $('#iban-form').addEventListener('submit', async event => {
    event.preventDefault();
    setStatus('Saglabā kontu…');
    try { const data = await request('/api/vsaa/profile', 'POST', {iban: $('#iban-input').value}); render(data.dashboard); setStatus('Bankas konts saglabāts. Profils ir pilnībā iestatīts.'); }
    catch (error) { setStatus(ERRORS[error.code] || 'Kontu neizdevās saglabāt.'); $('#iban-input').focus(); }
  });
  $('#reminders-toggle').addEventListener('change', async event => {
    const enabled = event.target.checked;
    try { const data = await request('/api/vsaa/profile', 'POST', {remindersEnabled: enabled}); render(data.dashboard); setStatus(enabled ? (data.remindersDelivered ? `Atgādinājumi ieslēgti; ${data.remindersDelivered} nosūtīti uz e-adresi.` : 'Atgādinājumi ieslēgti.') : 'Atgādinājumi uz e-adresi izslēgti.'); }
    catch { event.target.checked = !enabled; setStatus('Iestatījumu neizdevās saglabāt.'); }
  });

  function render(data) {
    dashboard = data;
    renderSummary(data.summary);
    $('#profile-alert').hidden = data.person.profileComplete;
    renderChildren(data.children);
    renderSickLeaves(data.sickLeaves);
    renderEmployment(data.employment);
    renderReminders(data.reminders, data.person);
    renderApplications(data.applications);
    applyLanguage();
  }

  async function load() {
    try {
      const data = await request('/api/vsaa/dashboard');
      render(data.dashboard);
      setStatus(data.remindersDelivered ? `${data.remindersDelivered} jauni atgādinājumi nosūtīti uz e-adresi.` : '');
      request('/api/vsaa/vacancies').then(renderVacancies).then(applyLanguage).catch(() => $('#vacancies').replaceChildren(el('p', {class: 'empty', text: 'Vakances neizdevās ielādēt.'})));
      renderStatistics(data.dashboard.person.municipality);
    } catch (error) {
      if (error.message !== 'unauthorized') setStatus('Neizdevās ielādēt VSAA datus. Pārbaudiet, vai darbojas demo serveris (python3 server/app.py).');
    }
  }
  load();
})();
