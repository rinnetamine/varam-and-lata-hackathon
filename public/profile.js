// Profile sections and a fictional inbox; no external messages are sent.
(() => {
  const titles = {overview:'Laipni gaidīts Mana Faketvija.lv', data:'Mani dati reģistros', mail:'Saņemtie ziņojumi', history:'Veikto darbību vēsture', notifications:'Paziņojumi'};
  function showSection() {
    const key = location.hash.slice(1);
    const section = Object.hasOwn(titles, key) ? key : 'overview';
    document.querySelectorAll('[data-profile-panel]').forEach(panel => { panel.hidden = panel.dataset.profilePanel !== section; });
    document.querySelectorAll('[data-profile-nav]').forEach(link => {
      if (link.dataset.profileNav === section) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    setTranslatedStatus(document.querySelector('#profile-section-title'), titles[section]);
  }
  window.addEventListener('hashchange', showSection);
  showSection();
  const list = document.querySelector('#message-list');
  const status = document.querySelector('#mail-status');
  const search = document.querySelector('#mail-search');
  let messages = [];
  function token() {
    try { return JSON.parse(localStorage.getItem('faketvijaSession'))?.token; } catch { return null; }
  }
  async function request(path, method = 'GET') {
    const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token() || ''}`}});
    if (response.status === 401) {
      localStorage.removeItem('faketvijaSession');
      location.replace('login.html');
      throw new Error('unauthorized');
    }
    if (!response.ok) throw new Error('request_failed');
    return response.json();
  }
  function counts(data) {
    messages = data.messages;
    document.querySelector('.unread-number').replaceChildren(document.createTextNode(String(data.unreadCount) + ' '));
    const badge = document.createElement('span');
    setTranslatedStatus(badge, '', data.unreadCount ? 'inbox.unread' : 'inbox.read');
    document.querySelector('.unread-number').append(badge);
    setTranslatedStatus(document.querySelector('#notification-count'), '', data.unreadCount ? 'inbox.hasUnread' : 'inbox.noUnread');
    setTranslatedStatus(document.querySelector('#notification-read-status'), '', data.unreadCount ? 'inbox.unread' : 'inbox.read');
  }
  function filter() {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    list.querySelectorAll('details').forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
      if (!row.hidden) visible++;
    });
    document.querySelector('#mail-empty').hidden = visible !== 0;
  }
  // System messages carry a template key and parameters, so they render in the selected language;
  // messages without a template keep their stored text.
  function localized(message) {
    const params = {...(message.params || {})};
    const bn = code => t(`benefit.${code}`);
    if (!message.template || i18n.language === 'lv') return {subject: message.subject, body: message.body};
    switch (message.template) {
      case 'application_received': {
        const subject = params.child ? t('msg.forChild', {benefit: bn(params.benefit), child: params.child}) : params.number ? t('msg.forLeave', {number: params.number}) : bn(params.benefit);
        return {subject: t('msg.applicationSubject', {subject}), body: t('msg.applicationBody', {service: t(`service.${params.benefit}`), date: i18n.formatDate(params.date), days: params.days, iban: params.iban})};
      }
      case 'share': {
        const lines = (params.items || []).map(item => t('msg.shareItem', {benefit: bn(item.benefit), deadline: i18n.formatDate(item.deadline)}) + (item.shared ? t('msg.shareShared') : ''));
        return {subject: t('msg.shareSubject', {child: params.child}), body: [t('msg.shareBody', {from: params.from, child: params.child, birth: i18n.formatDate(params.birth), role: t(`role.dative.${params.role}`)}), ...lines, t('msg.shareEnd')].join('\n')};
      }
      case 'decision': {
        const label = params.child ? t('msg.forChild', {benefit: bn(params.benefit), child: params.child}) : bn(params.benefit);
        return {subject: t('msg.decisionSubject', {status: t(`status.${params.status}`), label}), body: t('msg.decisionBody', {status: t(`decision.${params.status}`), service: t(`service.${params.benefit}`), date: i18n.formatDate(params.date)})};
      }
      default: {
        if (!message.template.startsWith('reminder_')) return {subject: message.subject, body: message.body};
        if (params.benefit) params.benefit = bn(params.benefit);
        for (const key of ['deadline', 'date']) if (params[key]) params[key] = i18n.formatDate(params[key]);
        let body = t(`${message.template}.text`, params);
        if (message.template === 'reminder_nva') body += ' ' + t(params.eligible ? 'reminder_nva.eligible' : 'reminder_nva.ineligible');
        return {subject: t('msg.reminderPrefix') + t(`${message.template}.title`, params), body: body + t('msg.reminderSuffix')};
      }
    }
  }
  function render() {
    list.replaceChildren();
    for (const message of messages) {
      const text = localized(message);
      const row = document.createElement('details');
      row.className = 'received-message';
      const summary = document.createElement('summary');
      const sender = document.createElement('span');
      sender.className = 'message-sender'; sender.textContent = message.sender;
      const subject = document.createElement('span'); subject.textContent = text.subject; subject.setAttribute('data-no-translate', '');
      const meta = document.createElement('span'); meta.className = 'message-meta';
      const badge = document.createElement('span'); badge.className = message.readAt ? 'read-tag' : 'unread-tag';
      badge.dataset.i18n = message.readAt ? 'inbox.read' : 'inbox.unread'; badge.textContent = t(badge.dataset.i18n);
      const date = document.createElement('time'); date.dateTime = message.receivedAt;
      date.textContent = i18n.formatDate(message.receivedAt);
      date.setAttribute('data-no-translate', '');
      meta.append(badge, date); summary.append(sender, subject, meta);
      const body = document.createElement('div'); body.className = 'message-body';
      const paragraph = document.createElement('p'); paragraph.textContent = text.body; paragraph.style.whiteSpace = 'pre-line'; paragraph.setAttribute('data-no-translate', '');
      const link = document.createElement('a'); link.href = message.template ? 'vsaa.html' : 'pakalpojumi.html'; link.dataset.i18n = message.template ? 'inbox.openVsaa' : 'inbox.viewServices'; link.textContent = t(link.dataset.i18n);
      body.append(paragraph, link); row.append(summary, body); list.append(row);
      let saving = false;
      row.addEventListener('toggle', async () => {
        if (!row.open || message.readAt || saving) return;
        saving = true;
        try {
          const data = await request(`/api/messages/${message.id}/read`, 'POST');
          message.readAt = data.messages.find(item => item.id === message.id).readAt;
          counts(data);
          badge.className = 'read-tag';
          setTranslatedStatus(badge, '', 'inbox.read');
          setTranslatedStatus(status, '');
        } catch {
          setTranslatedStatus(status, '', 'inbox.readFailed');
        } finally { saving = false; }
      });
    }
    applyLanguage(); filter();
  }
  async function load() {
    try {
      const data = await request('/api/messages');
      counts(data); render(); setTranslatedStatus(status, '');
    } catch { setTranslatedStatus(status, '', 'inbox.loadFailed'); }
  }
  async function loadVsaaSummary() {
    const target = document.querySelector('#vsaa-summary');
    if (!target) return;
    try {
      const {dashboard} = await request('/api/vsaa/dashboard');
      const describe = () => {
        const parts = [];
        if (dashboard.summary.available) parts.push(t('overview.available', {count: dashboard.summary.available}));
        if (dashboard.summary.unpaidSickLeaves) parts.push(t('overview.sick', {count: dashboard.summary.unpaidSickLeaves}));
        if (dashboard.employment.status === 'iemaksas_partrauktas') parts.push(t('overview.gap'));
        if (dashboard.summary.urgent) parts.push(t('overview.urgent', {count: dashboard.summary.urgent}));
        target.setAttribute('data-no-translate', '');
        target.textContent = parts.length ? t('overview.summary', {parts: parts.join(' · ')}) : t('overview.calm');
      };
      describe();
      i18n.onChange(describe);
    } catch {}
  }
  i18n.onChange(() => { if (messages.length) render(); });
  loadVsaaSummary();
  search.addEventListener('input', filter);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
  load();
})();
