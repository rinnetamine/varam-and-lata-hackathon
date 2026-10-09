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
    setTranslatedStatus(badge, data.unreadCount ? 'Nelasīts' : 'Izlasīts');
    document.querySelector('.unread-number').append(badge);
    setTranslatedStatus(document.querySelector('#notification-count'), data.unreadCount ? 'Ir nelasīti paziņojumi' : 'Nav jaunu paziņojumu');
    setTranslatedStatus(document.querySelector('#notification-read-status'), data.unreadCount ? 'Nelasīts' : 'Izlasīts');
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
  function render() {
    list.replaceChildren();
    for (const message of messages) {
      const row = document.createElement('details');
      row.className = 'received-message';
      const summary = document.createElement('summary');
      const sender = document.createElement('span');
      sender.className = 'message-sender'; sender.textContent = message.sender;
      const subject = document.createElement('span'); subject.textContent = message.subject;
      const meta = document.createElement('span'); meta.className = 'message-meta';
      const badge = document.createElement('span'); badge.className = message.readAt ? 'read-tag' : 'unread-tag';
      badge.textContent = message.readAt ? 'Izlasīts' : 'Nelasīts';
      const date = document.createElement('time'); date.dateTime = message.receivedAt;
      date.textContent = new Date(message.receivedAt).toLocaleDateString('lv-LV');
      date.setAttribute('data-no-translate', '');
      meta.append(badge, date); summary.append(sender, subject, meta);
      const body = document.createElement('div'); body.className = 'message-body';
      const text = document.createElement('p'); text.textContent = message.body;
      const link = document.createElement('a'); link.href = 'pakalpojumi.html'; link.textContent = 'Skatīt pieejamos pakalpojumus';
      body.append(text, link); row.append(summary, body); list.append(row);
      let saving = false;
      row.addEventListener('toggle', async () => {
        if (!row.open || message.readAt || saving) return;
        saving = true;
        try {
          const data = await request(`/api/messages/${message.id}/read`, 'POST');
          message.readAt = data.messages.find(item => item.id === message.id).readAt;
          counts(data);
          badge.className = 'read-tag';
          setTranslatedStatus(badge, 'Izlasīts');
          setTranslatedStatus(status, '');
        } catch {
          setTranslatedStatus(status, 'Neizdevās saglabāt lasīšanas statusu. Aizver ziņojumu un mēģini vēlreiz.');
        } finally { saving = false; }
      });
    }
    applyLanguage(); filter();
  }
  async function load() {
    try {
      const data = await request('/api/messages');
      counts(data); render(); setTranslatedStatus(status, '');
    } catch { setTranslatedStatus(status, 'Neizdevās ielādēt ziņojumus. Atjauno lapu un mēģini vēlreiz.'); }
  }
  async function loadVsaaSummary() {
    const target = document.querySelector('#vsaa-summary');
    if (!target) return;
    try {
      const {dashboard} = await request('/api/vsaa/dashboard');
      const parts = [];
      if (dashboard.summary.available) parts.push(`${dashboard.summary.available} pieejami pabalsti nav pieteikti`);
      if (dashboard.summary.unpaidSickLeaves) parts.push(`${dashboard.summary.unpaidSickLeaves} darbnespējas lapa bez pabalsta`);
      if (dashboard.employment.status === 'iemaksas_partrauktas') parts.push('sociālās iemaksas pārtrauktas');
      if (dashboard.summary.urgent) parts.push(`${dashboard.summary.urgent} steidzami termiņi`);
      setTranslatedStatus(target, parts.length ? parts.join(' · ') + '.' : 'Šobrīd nav nepieteiktu pabalstu vai termiņu.');
    } catch {}
  }
  loadVsaaSummary();
  search.addEventListener('input', filter);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
  load();
})();
