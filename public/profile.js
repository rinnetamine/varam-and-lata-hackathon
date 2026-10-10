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
  function renderHistory() {
    const root = document.querySelector('#activity-history');
    if (!root) return;
    const english = i18n.language === 'en';
    const labels = english ? {application_received:'Application submitted',decision:'Application status updated',received:'Message received',read:'Message read'} : {application_received:'Iesniegums iesniegts',decision:'Iesnieguma statuss atjaunināts',received:'Ziņojums saņemts',read:'Ziņojums izlasīts'};
    const events = [];
    for (const message of messages) {
      const subject = localized(message).subject;
      events.push({date:message.receivedAt,label:subject,type:['application_received','decision'].includes(message.template) ? message.template : 'received'});
      if (message.readAt) events.push({date:new Date(message.readAt * 1000).toISOString(),label:subject,type:'read'});
    }
    events.sort((a,b) => new Date(b.date) - new Date(a.date));
    root.replaceChildren();
    if (!events.length) { root.textContent = english ? 'No recorded activity yet.' : 'Vēl nav reģistrētu darbību.'; return; }
    const intro=document.createElement('p');intro.className='history-description';intro.textContent=english?'Your applications, status updates and messages, newest first.':'Tavi iesniegumi, statusu izmaiņas un ziņojumi — jaunākās darbības vispirms.';root.append(intro);
    let day=null, timeline;
    const paths={application_received:'M12 16V4m-4 4 4-4 4 4M4 14v6h16v-6',decision:'m5 12 4 4L19 6',received:'M3 5h18v14H3zM3 6l9 7 9-7',read:'M3 8l9-5 9 5v12H3zM3 9l9 6 9-6'};
    for (const event of events) {
      const dateValue=new Date(event.date);
      const dateLabel=i18n.formatDate(event.date);
      if(day!==dateLabel){day=dateLabel;const heading=document.createElement('h3');heading.className='history-day';heading.textContent=dateLabel;timeline=document.createElement('ol');timeline.className='history-timeline';root.append(heading,timeline);}
      const row=document.createElement('li');row.className='history-entry';
      const marker=document.createElement('span');marker.className='history-marker';marker.setAttribute('aria-hidden','true');
      const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[event.type]);svg.append(path);marker.append(svg);
      const copy=document.createElement('div');copy.className='history-copy';const title=document.createElement('strong');title.textContent=labels[event.type];const detail=document.createElement('p');detail.textContent=event.label;copy.append(title,detail);
      const time=document.createElement('time');time.dateTime=event.date;time.textContent=event.date.length>10?dateValue.toLocaleTimeString(english?'en-GB':'lv-LV',{hour:'2-digit',minute:'2-digit'}):'—';
      row.append(marker,copy,time);timeline.append(row);
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
      const link = document.createElement('a'); link.href = message.template ? 'vsaa.html' : 'vsaa.html#berni'; link.dataset.i18n = 'inbox.openVsaa'; link.textContent = t(link.dataset.i18n);
      body.append(paragraph, link); row.append(summary, body); list.append(row);
      let saving = false;
      row.addEventListener('toggle', async () => {
        if (!row.open || message.readAt || saving) return;
        saving = true;
        try {
          const data = await request(`/api/messages/${message.id}/read`, 'POST');
          message.readAt = data.messages.find(item => item.id === message.id).readAt;
          counts(data); renderHistory();
          badge.className = 'read-tag';
          setTranslatedStatus(badge, '', 'inbox.read');
          setTranslatedStatus(status, '');
        } catch {
          setTranslatedStatus(status, '', 'inbox.readFailed');
        } finally { saving = false; }
      });
    }
    renderHistory(); applyLanguage(); filter();
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
