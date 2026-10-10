// Mana VSAA dashboard: renders the signed-in person's fictional VSAA situation and the demo actions
// (apply with a prefilled form, notify the other parent, reminders). All data comes from /api/vsaa/*.
// Text comes from i18n.t(key) so the page re-renders in the selected language without reloading.
(() => {
  const $ = selector => document.querySelector(selector);
  const status = $('#page-status');
  let dashboard = null;
  let selectedChild = 'all';

  const fmtDate = iso => i18n.formatDate(iso);
  const fmtMonth = key => i18n.formatMonth(key);
  const fmtMoney = value => (value == null ? '' : i18n.formatMoney(value));
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value == null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key === 'i18n') { node.dataset.i18n = value; node.textContent = t(value); }
      else if (key === 'i18nParams') { node.dataset.i18nParams = JSON.stringify(value); node.textContent = t(node.dataset.i18n, value); }
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? '' : value);
    }
    for (const child of children.flat()) if (child != null) node.append(child.nodeType ? child : document.createTextNode(child));
    return node;
  };
  const tx = (key, params) => el('span', {i18n: key, i18nParams: params});
  const icon = path => { const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '1.8'); svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('aria-hidden', 'true'); svg.innerHTML = path; return svg; };
  const ICONS = {send: '<path d="M4 12 20 4l-4 16-4-7z"/>', check: '<path d="m5 12 5 5L20 7"/>', arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>'};

  function token() { try { return JSON.parse(localStorage.getItem('faketvijaSession'))?.token; } catch { return null; } }
  async function request(path, method = 'GET', body) {
    const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token() || ''}`, ...(body ? {'Content-Type': 'application/json'} : {})}, body: body && JSON.stringify(body)});
    if (response.status === 401) { localStorage.removeItem('faketvijaSession'); location.replace('login.html'); throw new Error('unauthorized'); }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.error || 'request_failed'); error.code = data.error; throw error; }
    return data;
  }
  const errorText = (error, fallbackKey) => (error.code && MESSAGES.lv[`err.${error.code}`] ? t(`err.${error.code}`) : t(fallbackKey));
  const setStatus = (key, params) => { if (!key) { status.textContent = ''; delete status.dataset.i18n; return; } setTranslatedStatus(status, '', key, params); };
  const statusKey = benefit => (benefit.status === 'pieejams' && benefit.late ? 'status.late' : benefit.status === 'otrs_vecaks' && /kopā/.test(benefit.statusText) ? 'status.otrs_vecaks_same' : `status.${benefit.status}`);
  const statusParams = benefit => ({days: benefit.daysLeft, date: fmtDate(benefit.availableFrom)});
  function chip(state, key, params) { return el('span', {class: `chip ${state}`, i18n: key, i18nParams: params}); }

  function benefitAmount(benefit) {
    const estimate = benefit.estimate || {};
    if (benefit.code === 'berna_piedzimsanas' && estimate.oneTime != null) return t('amount.berna_piedzimsanas', {amount: fmtMoney(estimate.oneTime)});
    if (benefit.code === 'berna_kopsanas' && estimate.schedule) return t('amount.berna_kopsanas', {monthly: fmtMoney(estimate.schedule[0].monthly)}) + (estimate.schedule[1] ? t('amount.berna_kopsanas_reduced', {reduced: fmtMoney(estimate.schedule[1].monthly)}) : '');
    if (benefit.code === 'gimenes_valsts' && estimate.monthly != null) return t('amount.gimenes_valsts', {monthly: fmtMoney(estimate.monthly), children: estimate.children});
    return t(`amount.${benefit.code}`);
  }
  const ageKey = days => (days < 60 ? ['age.days', {n: days}] : days < 730 ? ['age.months', {n: Math.floor(days / 30.44)}] : ['age.years', {n: Math.floor(days / 365.25)}]);
  const lateKey = benefit => (benefit.kind === 'one_time' ? 'late.one_time' : benefit.code === 'gimenes_valsts' ? 'late.monthly24' : 'late.monthly6');

  // --- Summary tiles -------------------------------------------------------------------
  function renderSummary(summary) {
    const tiles = [['#berni', summary.available, 'tile.available'], ['#atgadinajumi', summary.urgent, 'tile.urgent', 'urgent'], ['#slimiba', summary.unpaidSickLeaves, 'tile.sick'], ['#pieteikumi', summary.applications, 'tile.applications']];
    $('#summary').replaceChildren(...tiles.map(([href, count, key, extra]) => el('a', {class: `status-tile ${extra && count ? extra : ''}`, href},
      el('span', {class: `count ${count ? '' : 'zero'}`, text: String(count), 'data-no-translate': true}), el('span', {class: 'label', i18n: key}))));
  }

  // --- Children and the benefit checklist -----------------------------------------------
  function legalDetails(benefit) {
    const details = el('details', {class: 'legal-refs'}, el('summary', {i18n: 'benefit.legal'}));
    const list = el('ul');
    for (const ref of benefit.legal || []) {
      list.append(el('li', {}, el('a', {href: ref.url, target: '_blank', rel: 'noopener', text: ref.act, 'data-no-translate': true}), ' — ', el('span', {text: ref.article, 'data-no-translate': true}), ' ', el('em', {i18n: `legal.type.${ref.type}`}), ref.note ? el('span', {class: 'note', text: ` (${ref.note})`, 'data-no-translate': true}) : null));
    }
    details.append(list, el('p', {class: 'note', i18n: 'legal.verified', i18nParams: {date: fmtDate(benefit.verifiedAt)}}));
    return details;
  }

  function benefitRow(child, benefit) {
    const row = el('li', {class: `benefit ${['nav_attiecas', 'nokavets', 'nav_apdrosinats'].includes(benefit.status) ? 'inactive' : ''}`});
    row.append(el('div', {}, el('div', {class: 'title', i18n: `benefit.${benefit.code}`}, el('span', {class: 'official', i18n: `service.${benefit.code}`})), legalDetails(benefit)));
    row.append(el('div', {class: 'amount'}, el('span', {text: benefitAmount(benefit), 'data-no-translate': true}), el('span', {class: 'period', i18n: `period.${benefit.code}`})));
    const deadline = el('div', {class: 'deadline'});
    if (benefit.status === 'gaidams') {
      deadline.append(el('span', {}, tx('benefit.availableFrom'), ' ', el('strong', {text: fmtDate(benefit.availableFrom), 'data-no-translate': true})));
    } else if (benefit.deadline && !['nav_attiecas', 'pieskirts', 'iesniegts', 'izskatisana', 'otrs_vecaks'].includes(benefit.status)) {
      const used = Math.min(1, Math.max(0, 1 - benefit.daysLeft / benefit.windowDays));
      deadline.append(el('span', {}, tx('benefit.applyBy'), ' ', el('strong', {text: fmtDate(benefit.deadline), 'data-no-translate': true})));
      deadline.append(el('span', {class: `window ${benefit.daysLeft <= 30 ? 'urgent' : ''}`, role: 'img', 'data-i18n-attr': 'aria-label:benefit.daysLeft'}, el('i', {style: `width:${Math.round(used * 100)}%`})));
      deadline.append(benefit.daysLeft < 0 ? el('span', {i18n: lateKey(benefit)}) : tx('benefit.daysLeft', {days: benefit.daysLeft}));
    } else if (benefit.application) {
      deadline.append(el('span', {}, tx('benefit.submittedOn'), ' ', el('strong', {text: fmtDate(benefit.application.submittedAt), 'data-no-translate': true})), tx('benefit.decisionIn', {days: benefit.processingDays}));
    } else if (benefit.status !== 'nav_attiecas') {
      deadline.append(el('span', {i18n: lateKey(benefit)}));
    }
    row.append(deadline);
    const actions = el('div', {class: 'actions'}, chip(benefit.status, statusKey(benefit), statusParams(benefit)));
    if (['pieejams', 'steidzami'].includes(benefit.status)) {
      actions.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => openApply(benefit, {child})}, tx('common.apply'), icon(ICONS.arrow)));
    } else {
      actions.append(el('a', {class: 'section-link', href: benefit.source, target: '_blank', rel: 'noopener', i18n: 'common.about'}));
    }
    row.append(actions);
    return row;
  }

  function childCard(child) {
    const card = el('article', {class: 'child-card', 'data-child': child.id});
    card.setAttribute('aria-label', t('child.ariaLabel', {name: child.firstName}));
    card.append(el('header', {}, el('h3', {text: `${child.firstName} ${child.lastName || ''}`.trim(), 'data-no-translate': true}),
      el('div', {class: 'meta'}, el('span', {}, tx('common.born'), ' ', el('span', {text: fmtDate(child.birthDate), 'data-no-translate': true}), ' · ', tx(...ageKey(child.ageDays))),
        el('span', {}, tx('common.personalCode'), ': ', el('strong', {text: child.personasKods, 'data-no-translate': true})),
        el('span', {}, tx('common.role'), ' ', el('strong', {i18n: `role.${child.myRole}`})),
        el('span', {}, tx('common.municipality'), ' ', el('strong', {text: child.municipal.municipality || '—', 'data-no-translate': true})))));
    card.append(el('ul', {class: 'benefit-list'}, child.benefits.map(benefit => benefitRow(child, benefit))));
    const footer = el('footer');
    const shared = child.benefits.filter(b => b.onePerFamily && ['pieejams', 'steidzami'].includes(b.status)).map(b => t(`benefit.${b.code}`));
    if (shared.length) footer.append(el('p', {class: 'compare-note', i18n: 'child.compare', i18nParams: {list: shared.join(', ')}}));
    const parentRow = el('div', {class: 'parent-row'});
    if (child.otherParent.known) {
      parentRow.append(el('p', {i18n: 'child.otherParent'}));
      const sent = el('span', {class: 'sent'});
      if (child.otherParent.notifiedAt) { sent.dataset.i18n = 'child.sentOn'; sent.dataset.i18nParams = JSON.stringify({date: fmtDate(child.otherParent.notifiedAt)}); sent.textContent = t('child.sentOn', {date: fmtDate(child.otherParent.notifiedAt)}); }
      const button = el('button', {class: 'gov-btn secondary small', type: 'button', onclick: async () => {
        button.disabled = true; setStatus('child.sending');
        try { const data = await request('/api/vsaa/notify-other-parent', 'POST', {childId: child.id}); render(data.dashboard); setStatus(data.notified ? 'child.sent' : 'child.sentAlready'); }
        catch (error) { setStatus(error.code && MESSAGES.lv[`err.${error.code}`] ? `err.${error.code}` : 'child.sendFailed'); button.disabled = false; }
      }}, icon(ICONS.send), tx('child.notify'));
      parentRow.append(el('div', {style: 'display:flex;gap:12px;align-items:center;flex-wrap:wrap'}, sent, button));
    } else {
      parentRow.append(el('p', {i18n: 'child.noOtherParent'}));
    }
    footer.append(parentRow);
    footer.append(el('div', {class: 'parent-row'}, el('p', {i18n: 'child.municipal', i18nParams: {municipality: child.municipal.municipality || '—'}}),
      el('a', {class: 'gov-btn secondary small', href: child.municipal.lifeSituationUrl, target: '_blank', rel: 'noopener', i18n: 'child.municipalLink'})));
    card.append(footer);
    return card;
  }

  function renderChildren(children) {
    const root = $('#children');
    const picker = $('#child-picker');
    if (!children.length) {
      picker.hidden = true;
      root.replaceChildren(el('p', {class: 'empty', i18n: 'children.empty'}));
      return;
    }
    picker.hidden = false;
    if (selectedChild !== 'all' && !children.some(child => child.id === selectedChild)) selectedChild = 'all';
    const options = [['all', t('children.all')], ...children.map(child => [child.id, `${child.firstName} ${child.lastName || ''}`.trim()])];
    picker.replaceChildren(...options.map(([value, label]) => el('button', {type: 'button', class: `picker-btn ${String(selectedChild) === String(value) ? 'active' : ''}`, 'aria-pressed': String(String(selectedChild) === String(value)), 'data-no-translate': value !== 'all' || null, ...(value === 'all' ? {i18n: 'children.all'} : {text: label}), onclick: () => { selectedChild = value === 'all' ? 'all' : Number(value); renderChildren(dashboard.children); applyLanguage(); $('#child-picker').querySelector('[aria-pressed="true"]')?.focus(); }})));
    for (const [index, child] of children.entries()) {
      picker.children[index + 1].append(el('small', {class: 'child-sidebar-code', text: child.personasKods, 'data-no-translate': true}));
    }
    root.replaceChildren();
    if (selectedChild === 'all' && children.length > 1) {
      root.append(el('div', {class: 'gov-panel muted'}, el('h3', {i18n: 'children.overview'}), el('ul', {class: 'overview-list'}, children.map(child => {
        const counts = {available: child.benefits.filter(b => ['pieejams', 'steidzami'].includes(b.status)).length, applied: child.benefits.filter(b => ['iesniegts', 'izskatisana'].includes(b.status)).length, granted: child.benefits.filter(b => b.status === 'pieskirts').length};
        return el('li', {}, el('a', {href: '#berni', onclick: event => { event.preventDefault(); selectedChild = child.id; renderChildren(dashboard.children); applyLanguage(); }, i18n: 'children.overviewOf', i18nParams: {child: `${child.firstName} ${child.lastName || ''}`.trim(), ...counts}}));
      }))));
    }
    root.append(...children.filter(child => selectedChild === 'all' || child.id === selectedChild).map(childCard));
  }

  // --- Sick leaves ----------------------------------------------------------------------
  function renderSickLeaves(leaves) {
    const root = $('#sick-leaves');
    if (!leaves.length) { root.replaceChildren(el('p', {class: 'empty', i18n: 'sick.empty'})); return; }
    root.replaceChildren(...leaves.map(leave => {
      const row = el('article', {class: `leave ${leave.status === 'neizmaksata' ? 'open' : ''}`});
      row.append(el('div', {}, el('div', {class: 'title', i18n: 'sick.certificate', i18nParams: {kind: leave.kind, number: leave.number}}), el('div', {class: 'sub', text: leave.employer, 'data-no-translate': true})));
      row.append(el('dl', {}, el('dt', {i18n: 'sick.period'}), el('dd', {text: `${fmtDate(leave.dateFrom)} – ${fmtDate(leave.dateTo)} (${leave.days} d.)`, 'data-no-translate': true}), el('dt', {i18n: 'sick.closed'}), el('dd', {text: fmtDate(leave.closedAt), 'data-no-translate': true})));
      row.append(el('dl', {}, el('dt', {i18n: 'sick.pays'}), el('dd', {i18n: 'sick.paysDays', i18nParams: {days: leave.benefitDays}}), el('dt', {i18n: 'sick.applyBy'}), el('dd', {text: fmtDate(leave.deadline), 'data-no-translate': true})));
      const actions = el('div', {class: 'actions', style: 'display:grid;gap:8px;justify-items:end'}, chip(leave.status, `status.${leave.status}`));
      if (leave.status === 'neizmaksata' && leave.daysLeft >= 0) actions.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => openApply({code: 'slimibas', processingDays: 10}, {leave})}, tx('sick.claim'), icon(ICONS.arrow)));
      row.append(actions);
      return row;
    }));
  }

  // --- Employment, contributions and vacancies ------------------------------------------
  function renderEmployment(employment) {
    const root = $('#employment');
    const headline = {nodarbinats: ['work.regular', {}], iemaksas_partrauktas: ['work.gap', {gap: employment.gapMonths}], bezdarbnieks: ['work.registered', {}]}[employment.status];
    root.replaceChildren(el('h3', {i18n: headline[0], i18nParams: headline[1]}));
    const months = el('ul', {class: 'months', 'data-i18n-attr': 'aria-label:work.months'});
    employment.months.forEach((item, index) => months.append(el('li', {class: `${item.paid ? '' : 'gap'} ${index === employment.months.length - 1 ? 'current' : ''}`, title: item.paid ? t('work.monthPaid', {month: fmtMonth(item.month), employer: item.employer}) : t('work.monthGap', {month: fmtMonth(item.month)})}, el('i'), el('span', {text: item.month.slice(5), 'data-no-translate': true}))));
    root.append(months);
    root.append(el('dl', {class: 'facts'}, el('dt', {i18n: 'work.contributions'}), el('dd', {i18n: 'work.of16', i18nParams: {months: employment.monthsWithContributions}}),
      el('dt', {i18n: 'work.employer'}), el('dd', {text: employment.lastEmployer || '—', 'data-no-translate': true}),
      el('dt', {i18n: 'work.last'}), el('dd', {text: employment.lastContributionMonth ? fmtMonth(employment.lastContributionMonth) : '—', 'data-no-translate': true}),
      el('dt', {i18n: 'work.nva'}), el('dd', {i18n: employment.nvaRegistered ? 'work.nvaYes' : 'work.nvaNo'})));
    if (employment.application) {
      root.append(el('p', {style: 'margin:16px 0 0'}, chip(employment.application.status, `status.${employment.application.status}`), ' ', tx('work.applied', {date: fmtDate(employment.application.submittedAt), amount: employment.rule.amount})));
    } else if (employment.status === 'iemaksas_partrauktas') {
      root.append(el('p', {style: 'margin:16px 0 12px', i18n: employment.benefitEligible ? 'work.eligible' : 'work.ineligible'}));
      root.append(el('button', {class: 'gov-btn', type: 'button', disabled: !employment.benefitEligible, onclick: () => openApply({code: 'bezdarbnieka', processingDays: 22}, {employment})}, tx('work.register'), icon(ICONS.arrow)));
    } else {
      root.append(el('p', {style: 'margin:16px 0 0', i18n: 'work.calm'}));
    }
  }

  function renderVacancies(data) {
    const root = $('#vacancies');
    root.replaceChildren(el('h3', {i18n: 'vac.title', i18nParams: {municipality: data.municipality || 'Latvija'}}));
    root.append(el('p', {style: 'margin:6px 0 0;font-size:14px', i18n: 'vac.count', i18nParams: {count: data.count, total: data.total, date: fmtDate(data.retrievedAt)}}));
    if (data.samples.length) {
      root.append(el('ul', {class: 'vacancy-list'}, data.samples.map(job => el('li', {}, el('span', {class: 'job', text: job.nosaukums, 'data-no-translate': true}),
        el('span', {'data-no-translate': true}, `${job.kategorija} · `, job.algaNo ? fmtMoney(job.algaNo) + (job.algaLidz && job.algaLidz !== job.algaNo ? ' – ' + fmtMoney(job.algaLidz) : '') : tx('vac.noSalary')),
        el('span', {class: 'where'}, el('span', {text: `${job.vieta} · `, 'data-no-translate': true}), tx('vac.until', {date: fmtDate(job.pieteiksanasTermins)})),
        job.vakancesId ? el('a', {href: data.portal + job.vakancesId, target: '_blank', rel: 'noopener', i18n: 'vac.view'}) : null))));
    }
    root.append(el('p', {style: 'margin:14px 0 0'}, el('a', {class: 'gov-btn secondary small', href: 'https://cvvp.nva.gov.lv/#/pub/vakances/', target: '_blank', rel: 'noopener', i18n: 'vac.all'})));
    root.append(el('p', {class: 'source-note'}, tx('vac.source'), el('a', {href: data.source, target: '_blank', rel: 'noopener', i18n: 'vac.sourceName'}), el('span', {text: `, ${data.license}. `, 'data-no-translate': true}), tx('vac.snapshot')));
  }

  // --- Reminders -------------------------------------------------------------------------
  function reminderText(item) {
    const params = {...item.params};
    if (params.benefit) params.benefit = t(`benefit.${params.benefit}`);
    for (const key of ['deadline', 'date']) if (params[key]) params[key] = fmtDate(params[key]);
    const title = t(`${item.template}.title`, params);
    let text = t(`${item.template}.text`, params);
    if (item.template === 'reminder_nva') text += ' ' + t(params.eligible ? 'reminder_nva.eligible' : 'reminder_nva.ineligible');
    if (item.template === 'reminder_benefit' && item.benefitCode) { const child = dashboard.children.find(c => c.id === item.childId); const benefit = child?.benefits.find(b => b.code === item.benefitCode); if (benefit) text += ' ' + benefitAmount(benefit) + '.'; }
    return {title, text};
  }
  function renderReminders(reminders, person) {
    $('#reminders-toggle').checked = person.remindersEnabled;
    const root = $('#reminders');
    if (!reminders.length) { root.replaceChildren(el('li', {class: 'empty', i18n: 'rem.empty'})); return; }
    root.replaceChildren(...reminders.map(item => {
      const li = el('li', {class: `reminder ${item.level}`});
      const when = el('span', {class: 'when'});
      if (item.daysLeft != null) when.append(el('b', {text: String(item.daysLeft), 'data-no-translate': true}), tx('common.days'));
      else when.append(el('b', {text: '!', 'data-no-translate': true}), tx(item.level === 'info' ? 'common.info' : 'common.now'));
      const {title, text} = reminderText(item);
      li.append(when, el('div', {'data-no-translate': true}, el('h3', {text: title}), el('p', {text})));
      if (item.action === 'apply') {
        li.append(el('button', {class: 'gov-btn small', type: 'button', onclick: () => {
          if (item.benefitCode === 'slimibas') { const leave = dashboard.sickLeaves.find(l => l.id === item.sickLeaveId); openApply({code: 'slimibas', processingDays: 10}, {leave}); }
          else if (item.benefitCode === 'bezdarbnieka') openApply({code: 'bezdarbnieka', processingDays: 22}, {employment: dashboard.employment});
          else { const child = dashboard.children.find(c => c.id === item.childId); openApply(child.benefits.find(b => b.code === item.benefitCode), {child}); }
        }}, tx('common.apply')));
      } else if (item.action === 'profile') {
        li.append(el('a', {class: 'gov-btn secondary small', href: '#profile-alert', onclick: () => $('#iban-input').focus(), i18n: 'rem.addAccount'}));
      }
      return li;
    }));
  }

  // --- Applications ----------------------------------------------------------------------
  function renderApplications(applications) {
    const root = $('#applications');
    if (!applications.length) { root.replaceChildren(el('p', {class: 'empty', i18n: 'apps.empty'})); return; }
    root.replaceChildren(el('ul', {class: 'leave-list', style: 'list-style:none;padding:0;margin:0'}, applications.map(app => {
      const child = app.childId && dashboard.children.find(c => c.id === app.childId);
      const leave = app.sickLeaveId && dashboard.sickLeaves.find(l => l.id === app.sickLeaveId);
      const extra = Object.entries(app.details).filter(([key]) => key !== 'seed').map(([key, value]) => `${key}: ${value}`).join(' · ');
      const subject = child ? el('div', {class: 'sub'}, tx('common.child'), el('span', {text: `: ${child.firstName}`, 'data-no-translate': true})) : leave ? el('div', {class: 'sub', i18n: 'apps.leave', i18nParams: {number: leave.number}}) : el('div', {class: 'sub', i18n: 'apps.none'});
      return el('li', {class: 'leave'}, el('div', {}, el('div', {class: 'title', i18n: `benefit.${app.benefitCode}`}), subject),
        el('dl', {}, el('dt', {i18n: 'common.submitted'}), el('dd', {text: fmtDate(app.submittedAt), 'data-no-translate': true})),
        el('dl', {}, el('dt', {i18n: 'common.details'}), el('dd', {text: extra || '—', 'data-no-translate': true})),
        el('div', {class: 'actions'}, chip(app.status, `status.${app.status}`)));
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
      const bars = (items, valueOf, labelOf, max, secondary) => el('ul', {class: `bars ${secondary ? 'secondary' : ''}`}, items.map(([key, labelKey]) => el('li', {}, el('span', {i18n: labelKey}), el('span', {class: 'value', text: labelOf(key), 'data-no-translate': true}), el('span', {class: 'bar'}, el('i', {style: `width:${Math.max(1, 100 * valueOf(key) / max)}%`})))));
      if (local && national) {
        const items = [['slimibasPabalsti', 'stats.slimibas'], ['bezdarbniekuPabalsti', 'stats.bezdarbnieku'], ['maternitatesPabalsti', 'stats.maternitates'], ['paternitatesPabalsti', 'stats.paternitates'], ['vecakuUnBernaKopsanasPabalsti', 'stats.vecaku'], ['gimenesValstsPabalsti', 'stats.gimenes']];
        const max = Math.max(...items.map(([key]) => local[key]));
        root.append(el('div', {class: 'gov-panel muted', style: 'margin:0'}, el('h3', {i18n: 'stats.recipients', i18nParams: {municipality}}), el('p', {style: 'margin:4px 0 0;font-size:13px;color:var(--gov-muted)', i18n: 'stats.vsaaPeriod', i18nParams: {period: fmtMonth(vsaa.period)}}),
          bars(items, key => local[key], key => t('stats.ofCountry', {value: i18n.formatNumber(local[key]), share: (100 * local[key] / national[key]).toFixed(1)}), max, false),
          el('p', {class: 'source-note'}, tx('stats.source'), el('a', {href: vsaa.source, target: '_blank', rel: 'noopener', text: vsaa.title, 'data-no-translate': true}), el('span', {text: ` (${vsaa.publisher}), ${vsaa.license}.`, 'data-no-translate': true}))));
      }
      if (localGvp && nationalGvp) {
        const items = [['par1Bernu', 'stats.par1'], ['par2Berniem', 'stats.par2'], ['par3Berniem', 'stats.par3'], ['par4Berniem', 'stats.par4'], ['par5Berniem', 'stats.par5'], ['par6UnVairakBerniem', 'stats.par6']];
        root.append(el('div', {class: 'gov-panel muted', style: 'margin:0'}, el('h3', {i18n: 'stats.family', i18nParams: {count: i18n.formatNumber(localGvp.kopa)}}), el('p', {style: 'margin:4px 0 0;font-size:13px;color:var(--gov-muted)', i18n: 'stats.familyPeriod', i18nParams: {period: fmtMonth(gvp.period), total: i18n.formatNumber(nationalGvp.kopa)}}),
          bars(items, key => localGvp[key], key => `${i18n.formatNumber(localGvp[key])} (${(100 * localGvp[key] / localGvp.kopa).toFixed(0)} %)`, localGvp.kopa, true),
          el('p', {class: 'source-note'}, tx('stats.source'), el('a', {href: gvp.source, target: '_blank', rel: 'noopener', text: gvp.title, 'data-no-translate': true}), el('span', {text: ` (${gvp.publisher}), ${gvp.license}.`, 'data-no-translate': true}))));
      }
      if (!root.children.length) root.append(el('p', {class: 'empty', i18n: 'stats.empty'}));
      applyLanguage();
    } catch { root.replaceChildren(el('p', {class: 'empty', i18n: 'stats.failed'})); }
  }

  // --- Prefilled application dialog ------------------------------------------------------
  function openApply(benefit, context) {
    const dialog = $('#apply-dialog');
    const person = dashboard.person;
    const form = el('form', {method: 'dialog'});
    form.append(el('button', {class: 'dialog-close', type: 'button', 'data-i18n-attr': 'aria-label:common.close', onclick: () => dialog.close()}, '×'));
    form.append(el('h2', {id: 'apply-title', i18n: `benefit.${benefit.code}`}), el('p', {class: 'official', i18n: 'dialog.eservice', i18nParams: {name: t(`service.${benefit.code}`)}}));
    const facts = el('dl', {class: 'prefilled'}, el('div', {}, el('dt', {i18n: 'dialog.applicant'}), el('dd', {text: `${person.firstName} ${person.lastName}`, 'data-no-translate': true})), el('div', {}, el('dt', {i18n: 'common.personalCode'}), el('dd', {text: person.personasKods, 'data-no-translate': true})), el('div', {}, el('dt', {i18n: 'dialog.address'}), el('dd', {text: person.address, 'data-no-translate': true})));
    if (context.child) facts.append(el('div', {}, el('dt', {i18n: 'common.child'}), el('dd', {i18n: 'dialog.childBorn', i18nParams: {name: `${context.child.firstName} ${context.child.lastName || ''}`.trim(), date: fmtDate(context.child.birthDate)}})));
    if (context.leave) facts.append(el('div', {}, el('dt', {i18n: 'dialog.leave'}), el('dd', {text: `${context.leave.number}, ${fmtDate(context.leave.dateFrom)} – ${fmtDate(context.leave.dateTo)}`, 'data-no-translate': true})));
    if (context.employment) facts.append(el('div', {}, el('dt', {i18n: 'dialog.months'}), el('dd', {i18n: 'dialog.of16', i18nParams: {months: context.employment.monthsWithContributions}})));
    form.append(facts, el('p', {class: 'prefilled-note', i18n: 'dialog.prefilled'}));
    if (benefit.estimate) form.append(el('p', {class: 'prefilled-note'}, tx('benefit.estimate'), el('span', {text: `: ${benefitAmount(benefit)}`, 'data-no-translate': true})));
    if (benefit.late) form.append(el('p', {class: 'prefilled-note', i18n: 'dialog.late', i18nParams: {rule: t(lateKey(benefit))}}));
    form.append(el('label', {class: 'field'}, tx('dialog.iban'), el('input', {name: 'iban', value: person.iban || '', placeholder: 'LV00 BANK 0000 0000 0000 0', required: true, autocomplete: 'off', maxlength: '26'}), el('span', {class: 'hint', i18n: 'dialog.ibanHint'})));
    if (benefit.options) {
      for (const [name, values] of Object.entries(benefit.options)) {
        const choice = el('fieldset', {class: 'field choice', style: 'border:0;padding:0;margin:0'}, el('legend', {i18n: 'dialog.duration', style: 'margin-bottom:6px'}));
        values.forEach((value, index) => choice.append(el('label', {}, el('input', {type: 'radio', name: `opt-${name}`, value, checked: index === 0}), tx(value === '13 mēneši' ? 'dialog.opt13' : 'dialog.opt19'))));
        form.append(choice);
      }
    }
    if (benefit.code === 'bezdarbnieka') form.append(el('p', {class: 'prefilled-note', i18n: 'dialog.nva'}));
    const dialogStatus = el('p', {class: 'dialog-status', role: 'status'});
    const submit = el('button', {class: 'gov-btn', type: 'submit'}, icon(ICONS.check), tx('dialog.submit'));
    form.append(dialogStatus, el('div', {class: 'dialog-actions'}, el('button', {class: 'gov-btn secondary', type: 'button', onclick: () => dialog.close(), i18n: 'common.cancel'}), submit));
    let submitting = false;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (submitting) return;
      submitting = true; submit.disabled = true; setTranslatedStatus(dialogStatus, '', 'dialog.submitting');
      const options = {};
      form.querySelectorAll('input[type=radio]:checked').forEach(input => { options[input.name.replace('opt-', '')] = input.value; });
      try {
        const data = await request('/api/vsaa/apply', 'POST', {benefitCode: benefit.code, childId: context.child?.id, sickLeaveId: context.leave?.id, iban: form.iban.value, options});
        render(data.dashboard);
        dialog.replaceChildren(el('div', {class: 'dialog-ok'}, icon(ICONS.check), el('h2', {i18n: 'dialog.done'}), el('p', {i18n: 'dialog.doneText', i18nParams: {service: t(`service.${benefit.code}`), days: benefit.processingDays}}), el('button', {class: 'gov-btn', type: 'button', onclick: () => dialog.close(), i18n: 'common.close'})));
        applyLanguage();
        setStatus('');
      } catch (error) {
        setTranslatedStatus(dialogStatus, '', error.code && MESSAGES.lv[`err.${error.code}`] ? `err.${error.code}` : 'dialog.failed');
        submitting = false; submit.disabled = false;
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
    setStatus('profile.saving');
    try { const data = await request('/api/vsaa/profile', 'POST', {iban: $('#iban-input').value}); render(data.dashboard); setStatus('profile.saved'); }
    catch (error) { setStatus(error.code && MESSAGES.lv[`err.${error.code}`] ? `err.${error.code}` : 'err.ibanSave'); $('#iban-input').focus(); }
  });
  $('#reminders-toggle').addEventListener('change', async event => {
    const enabled = event.target.checked;
    try { const data = await request('/api/vsaa/profile', 'POST', {remindersEnabled: enabled}); render(data.dashboard); setStatus(enabled ? (data.remindersDelivered ? 'rem.onSent' : 'rem.on') : 'rem.off', {count: data.remindersDelivered}); }
    catch { event.target.checked = !enabled; setStatus('rem.saveFailed'); }
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
    const disclaimer = $('#disclaimer');
    disclaimer.dataset.i18nParams = JSON.stringify({date: fmtDate(data.verifiedAt)});
    applyLanguage();
  }
  // Re-render locale-dependent values (dates, money) when the language changes.
  i18n.onChange(() => { if (dashboard) { render(dashboard); request('/api/vsaa/vacancies').then(renderVacancies).then(() => applyLanguage()).catch(() => {}); renderStatistics(dashboard.person.municipality); } });

  async function load() {
    try {
      const data = await request('/api/vsaa/dashboard');
      render(data.dashboard);
      setStatus(data.remindersDelivered ? 'rem.delivered' : '', {count: data.remindersDelivered});
      request('/api/vsaa/vacancies').then(renderVacancies).then(() => applyLanguage()).catch(() => $('#vacancies').replaceChildren(el('p', {class: 'empty', i18n: 'vac.failed'})));
      renderStatistics(data.dashboard.person.municipality);
    } catch (error) {
      if (error.code === 'forbidden') { location.replace('admin.html'); return; }
      if (error.message !== 'unauthorized') setStatus('err.load');
    }
  }
  load();
})();
