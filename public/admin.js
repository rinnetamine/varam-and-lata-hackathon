// Administrator inbox: lists every persisted application from /api/admin/applications and records
// demo decisions. The server answers 401 without a session and 403 for ordinary portal users.
(() => {
  const $ = selector => document.querySelector(selector);
  const status = $('#page-status');
  let data = null;
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
  function token() { try { return JSON.parse(localStorage.getItem('faketvijaSession'))?.token; } catch { return null; } }
  async function request(path, method = 'GET', body) {
    const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token() || ''}`, ...(body ? {'Content-Type': 'application/json'} : {})}, body: body && JSON.stringify(body)});
    if (response.status === 401) { localStorage.removeItem('faketvijaSession'); location.replace('login.html'); throw new Error('unauthorized'); }
    if (response.status === 403) { location.replace('profile.html'); throw new Error('forbidden'); }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(payload.error || 'request_failed'); error.code = payload.error; throw error; }
    return payload;
  }
  const setStatus = (key, params) => { if (!key) { status.textContent = ''; delete status.dataset.i18n; return; } setTranslatedStatus(status, '', key, params); };
  const fmtDate = iso => i18n.formatDate(iso);

  function renderSummary() {
    const counts = data.counts;
    const tiles = [[data.total, 'admin.total'], [counts.iesniegts || 0, 'admin.pending', 'urgent'], [counts.izskatisana || 0, 'admin.review'], [counts.pieskirts || 0, 'admin.granted']];
    $('#summary').replaceChildren(...tiles.map(([count, key, extra]) => el('span', {class: `status-tile ${extra && count ? extra : ''}`}, el('span', {class: `count ${count ? '' : 'zero'}`, text: String(count), 'data-no-translate': true}), el('span', {class: 'label', i18n: key}))));
  }

  function subjectCell(app) {
    if (app.child) return el('td', {'data-label': t('admin.subject')}, el('span', {text: app.child.name, 'data-no-translate': true}), el('span', {class: 'sub', 'data-no-translate': true}, `${t('common.born')} ${fmtDate(app.child.birthDate)} · ${app.child.personasKods}`));
    if (app.sickLeave) return el('td', {'data-label': t('admin.subject')}, el('span', {text: app.sickLeave.number, 'data-no-translate': true}), el('span', {class: 'sub', text: `${fmtDate(app.sickLeave.dateFrom)} – ${fmtDate(app.sickLeave.dateTo)}`, 'data-no-translate': true}));
    return el('td', {'data-label': t('admin.subject'), i18n: 'apps.none'});
  }

  async function decide(app, next, button) {
    button.disabled = true; setStatus('admin.saving');
    try { data = await request(`/api/admin/applications/${app.id}/status`, 'POST', {status: next}); renderList(); setStatus('admin.saved'); }
    catch (error) { if (error.message !== 'unauthorized' && error.message !== 'forbidden') { setStatus('admin.failed'); button.disabled = false; } }
  }

  function renderList() {
    renderSummary();
    const filter = $('#status-filter').value;
    const query = $('#search').value.trim().toLocaleLowerCase();
    const rows = data.applications.filter(app => (!filter || app.status === filter) && (!query || `${app.applicant.name} ${app.applicant.personasKods} ${app.child?.name || ''} ${app.sickLeave?.number || ''} ${t(`benefit.${app.benefitCode}`)} ${app.benefitName}`.toLocaleLowerCase().includes(query)));
    const root = $('#applications');
    if (!rows.length) { root.replaceChildren(el('p', {class: 'empty', i18n: 'admin.empty'})); applyLanguage(); return; }
    const table = el('table', {class: 'admin-table'}, el('thead', {}, el('tr', {}, ...['admin.applicant', 'admin.service', 'admin.subject', 'admin.status', 'admin.submitted', 'admin.actions'].map(key => el('th', {i18n: key})))));
    const body = el('tbody');
    for (const app of rows) {
      const details = Object.entries(app.details).filter(([key]) => key !== 'seed').map(([key, value]) => `${key}: ${value}`).join(' · ');
      const actions = el('div', {class: 'actions'});
      if (app.status === 'iesniegts') actions.append(el('button', {class: 'gov-btn secondary small', type: 'button', i18n: 'admin.review.btn', onclick: event => decide(app, 'izskatisana', event.currentTarget)}));
      if (app.status !== 'pieskirts') actions.append(el('button', {class: 'gov-btn small', type: 'button', i18n: 'admin.grant', onclick: event => decide(app, 'pieskirts', event.currentTarget)}));
      if (app.status !== 'atteikts') actions.append(el('button', {class: 'gov-btn secondary small', type: 'button', i18n: 'admin.reject', onclick: event => decide(app, 'atteikts', event.currentTarget)}));
      body.append(el('tr', {},
        el('td', {'data-label': t('admin.applicant')}, el('span', {text: app.applicant.name, 'data-no-translate': true}), el('span', {class: 'sub', 'data-no-translate': true}, `${app.applicant.personasKods} · ${app.applicant.municipality || '—'}`)),
        el('td', {'data-label': t('admin.service')}, el('span', {i18n: `benefit.${app.benefitCode}`}), el('span', {class: 'sub', i18n: `service.${app.benefitCode}`}), details ? el('details', {}, el('summary', {i18n: 'admin.detailsLabel'}), el('span', {text: details, 'data-no-translate': true})) : null, app.seeded ? el('span', {class: 'sub', i18n: 'admin.seeded'}) : null),
        subjectCell(app),
        el('td', {'data-label': t('admin.status')}, el('span', {class: `chip ${app.status}`, i18n: `status.${app.status}`}), app.decidedAt ? el('span', {class: 'sub', 'data-no-translate': true}, `${t('admin.decided')}: ${fmtDate(app.decidedAt)}`) : null),
        el('td', {'data-label': t('admin.submitted'), text: fmtDate(app.submittedAt), 'data-no-translate': true}),
        el('td', {'data-label': t('admin.actions')}, actions)));
    }
    table.append(body);
    root.replaceChildren(table);
    applyLanguage();
  }

  async function load() {
    try { data = await request('/api/admin/applications'); $('#profile-account-name').textContent = data.admin.name; renderList(); setStatus(''); }
    catch (error) { if (!['unauthorized', 'forbidden'].includes(error.message)) setStatus('admin.loadFailed'); }
  }
  $('#status-filter').addEventListener('change', () => data && renderList());
  $('#search').addEventListener('input', () => data && renderList());
  $('#refresh').addEventListener('click', load);
  i18n.onChange(() => data && renderList());
  document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
  load();
})();
