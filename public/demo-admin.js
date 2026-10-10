// Public demonstration inspector for fictional data; separate from user-facing services.
// Labels come from i18n.t('demo.*') and the panel re-renders when the language changes.
(() => {
  const stylesheet = document.createElement('link'); stylesheet.rel = 'stylesheet'; stylesheet.href = 'demo-admin.css?v=quick-login-9'; document.head.append(stylesheet);
  const node = (tag, text, className) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (className) e.className = className; return e; };
  const keyed = (tag, key, className) => { const e = node(tag, t(key), className); e.dataset.i18n = key; return e; };
  const launch = keyed('button', 'demo.launch', 'demo-launch'); launch.type = 'button'; document.body.append(launch);
  function adminToken(){try{return JSON.parse(localStorage.getItem('faketvijaSession'))?.token || '';}catch{return '';}}
  const dialog = node('dialog', null, 'demo-inspector'); dialog.setAttribute('data-no-translate', ''); dialog.setAttribute('aria-labelledby','demo-inspector-title');
  const header = node('header'); const title=keyed('h2','demo.title');title.id='demo-inspector-title';header.append(title);
  const close = node('button', '×', 'demo-close'); close.type = 'button'; close.dataset.i18nAttr = 'aria-label:common.close'; close.setAttribute('aria-label', t('common.close')); close.onclick = () => dialog.close(); header.append(close);
  const intro = keyed('p', 'demo.intro', 'demo-intro');
  const label = node('label'); const labelText = keyed('span', 'demo.select'); const select = node('select'); label.append(labelText, select);
  const search = node('input'); search.type = 'search'; search.dataset.i18nAttr = 'placeholder:demo.search,aria-label:demo.search'; search.placeholder = t('demo.search'); search.setAttribute('aria-label', search.placeholder);
  const content = node('div', null, 'demo-record'); const status = node('p'); status.setAttribute('role', 'status');
  status.className='demo-status'; dialog.append(header, intro, search, label, content, status); document.body.append(dialog);
  let people = [];

  const selectionKey = 'faketvijaDemoSelectedUser';
  let selectedCode = null;
  try { selectedCode = localStorage.getItem(selectionKey); } catch {}
  function rememberSelection() {
    const person = people.find(p => p.id === Number(select.value));
    if (person) {
      selectedCode = person.personas_kods;
      try { localStorage.setItem(selectionKey, selectedCode); } catch {}
    }
    render();
  }
  function copyField(labelText, value) {
    const row = node('div', null, 'demo-field'); row.append(node('strong', labelText), node('code', value || '—'));
    if (value) { const copy = node('button', t('demo.copy')); copy.type = 'button'; copy.onclick = async () => { try { await navigator.clipboard.writeText(value); status.textContent = t('demo.copied'); } catch { status.textContent = value; } }; row.append(copy); }
    return row;
  }
  function personName(id) { const p = people.find(p => p.id === id); return p ? `${p.first_name} ${p.last_name} (${p.personas_kods})` : t('common.noData'); }
  function render() {
    content.replaceChildren(); const p = people.find(p => p.id === Number(select.value)); if (!p) return;
    content.append(node('h3', `${p.first_name} ${p.last_name}`), node('p', p.scenario), copyField(t('common.personalCode'), p.personas_kods), copyField(t('demo.email'), p.email), copyField(t('demo.phone'), p.phone), copyField(t('demo.address'), p.address));
    const login=keyed('button','demo.loginAs','demo-switch-user');login.type='button';
    login.onclick=async()=>{
      login.disabled=true;select.disabled=true;search.disabled=true;status.textContent=t('demo.switching');
      let session;
      try{
        const response=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${adminToken()}`},body:JSON.stringify({personasKods:p.personas_kods})});
        if(!response.ok)throw new Error();
        session=await response.json();
        localStorage.setItem('faketvijaSession',JSON.stringify(session));
        const onVsaa=location.pathname.endsWith('/vsaa.html');
        location.replace(session.person.role==='admin'?'admin.html':!session.person.iban?'bank-account.html':onVsaa?'vsaa.html':'profile.html');
      }catch{
        if(session?.token){try{await fetch('/api/logout',{method:'POST',headers:{Authorization:`Bearer ${session.token}`}});}catch{}}
        status.textContent=t('demo.switchFailed');login.disabled=false;select.disabled=false;search.disabled=false;
      }
    };
    content.append(login);
    if (p.role === 'admin') { content.append(node('p', t('demo.adminHint'), 'demo-intro')); return; }
    content.append(node('h3', t('demo.accounts')));
    for (const a of p.bankAccounts) content.append(copyField(`IBAN (${a.active ? t('demo.active') : t('demo.inactive')})`, a.iban));
    content.append(node('p', t('demo.savedIban') + (p.iban || '—')));
    const clear = node('button', t('demo.clear'), 'demo-clear-iban');
    clear.type = 'button'; clear.disabled = !p.iban;
    clear.onclick = async () => {
      clear.disabled = true;
      try {
        const response = await fetch(`/api/demo/people/${p.id}/clear-iban`, {method: 'POST',headers:{Authorization:`Bearer ${adminToken()}`}});
        if (!response.ok) throw new Error();
        p.iban = null; render();
        try { const session = JSON.parse(localStorage.getItem('faketvijaSession')); if (session?.person?.id === p.id) { session.person.iban = null; localStorage.setItem('faketvijaSession', JSON.stringify(session)); } } catch {}
        status.textContent = t('demo.cleared');
      } catch { clear.disabled = false; status.textContent = t('demo.clearFailed'); }
    };
    content.append(clear);
    content.append(node('h3', `${t('demo.children')}: ${p.children.length}`));
    for (const c of p.children) {
      const card = node('article', null, 'demo-child'); card.append(node('h4', `${c.first_name} ${c.last_name}`), copyField(t('demo.childCode'), c.personas_kods), node('p', t('demo.birth') + i18n.formatDate(c.birth_date)), node('p', t('demo.mother') + personName(c.mother_id)), node('p', t('demo.father') + personName(c.father_id)));
      const table = node('table'); const heading = node('tr'); for (const title of [t('demo.benefit'), t('demo.motherReceiving'), t('demo.fatherReceiving')]) heading.append(node('th', title)); const thead = node('thead'); thead.append(heading); table.append(thead); const tbody = node('tbody');
      for (const b of c.benefits) { const tr = node('tr'); for (const value of [t(`benefit.${b.benefit_code}`), c.mother_id ? (b.mother_receiving ? t('common.yes') : t('common.no')) : '—', c.father_id ? (b.father_receiving ? t('common.yes') : t('common.no')) : '—']) tr.append(node('td', value)); tbody.append(tr); } table.append(tbody); const wrapper=node('div',null,'demo-table-scroll');wrapper.append(table);card.append(wrapper);
      for (const a of c.applications) card.append(node('p', `${t(`benefit.${a.benefit_code}`)} · ${personName(a.person_id)} · ${t(`status.${a.status}`)}`)); content.append(card);
    }
    const sources = keyed('a', 'footer.sources'); sources.href = 'data-licenses.html'; content.append(sources);
  }
  function options() { const selected = people.find(p => p.personas_kods === selectedCode)?.id?.toString() || select.value; select.replaceChildren(); const query = search.value.trim().toLocaleLowerCase(); for (const p of people) { if (!`${p.first_name} ${p.last_name} ${p.personas_kods}`.toLocaleLowerCase().includes(query)) continue; const option = node('option', `${p.id}. ${p.first_name} ${p.last_name} · ${p.scenario}`); option.value = p.id; select.append(option); } if ([...select.options].some(o => o.value === selected)) select.value = selected; render(); }
  select.onchange = rememberSelection; search.oninput = options;
  launch.onclick = async () => {people=[];select.replaceChildren();content.replaceChildren();search.value = ''; dialog.showModal(); status.textContent = t('demo.loading'); try { const response = await fetch('/api/demo/admin',{headers:{Authorization:`Bearer ${adminToken()}`}}); if (!response.ok) throw new Error(); people = (await response.json()).people; options(); status.textContent = ''; } catch { status.textContent = t('demo.unavailable'); } };
  i18n.onChange(() => { if (people.length) options(); });
})();
