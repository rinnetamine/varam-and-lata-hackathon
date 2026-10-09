// Global read-only inspector for fictional demo registries; intentionally available before login.
(() => {
  const stylesheet = document.createElement('link'); stylesheet.rel = 'stylesheet'; stylesheet.href = 'demo-admin.css'; document.head.append(stylesheet);
  const en = () => document.documentElement.lang === 'en';
  const t = (lv, english) => en() ? english : lv;
  const node = (tag, text, className) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (className) e.className = className; return e; };
  const launch = node('button', t('Demo panelis', 'Demo panel'), 'demo-launch'); launch.type = 'button'; document.body.append(launch);
  const dialog = node('dialog', null, 'demo-inspector');
  const header = node('header'); header.append(node('h2', t('Demo datu panelis', 'Demo data inspector')));
  const close = node('button', '×', 'demo-close'); close.type='button'; close.setAttribute('aria-label',t('Aizvērt','Close')); close.onclick = () => dialog.close(); header.append(close);
  const intro = node('p', t('Tikai izdomāti lietotāji, bērni un bankas konti. Panelis ir publiski pieejams demonstrācijai.', 'Fictional users, children and bank accounts only. This inspector is public for demonstration.'), 'demo-intro');
  const label = node('label', t('Izvēlies demo lietotāju', 'Select a demo user')); const select = node('select'); label.append(select);
  const search = node('input'); search.type='search'; search.placeholder=t('Meklēt vārdu vai personas kodu…','Search name or personal code…'); search.setAttribute('aria-label',search.placeholder);
  const content = node('div',null,'demo-record'); const status = node('p'); status.setAttribute('role','status');
  dialog.append(header,intro,search,label,content,status); document.body.append(dialog);
  let people=[];
  function copyField(label,value){
    const row=node('div',null,'demo-field');row.append(node('strong',label),node('code',value || '—'));
    if(value){const copy=node('button',t('Kopēt','Copy')); copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.writeText(value);status.textContent=t('Nokopēts','Copied');}catch{status.textContent=value;}}; row.append(copy);}return row;
  }
  function personName(id){const p=people.find(p=>p.id===id);return p ? `${p.first_name} ${p.last_name} (${p.personas_kods})` : t('Nav norādīts','Not recorded');}
  function render(){
    content.replaceChildren();const p=people.find(p=>p.id===Number(select.value));if(!p)return;
    content.append(node('h3',`${p.first_name} ${p.last_name}`),node('p',p.scenario),copyField(t('Personas kods','Personal code'),p.personas_kods),copyField(t('E-pasts','Email'),p.email),copyField(t('Tālrunis','Phone'),p.phone),copyField(t('Adrese','Address'),p.address));
    content.append(node('h3',t('Demo bankas konti','Demo bank accounts')));
    for(const a of p.bankAccounts)content.append(copyField(`IBAN (${a.active ? t('aktīvs','active') : t('neaktīvs','inactive')})`,a.iban));
    content.append(node('p',t('Profilā saglabātais IBAN: ','Saved profile IBAN: ')+(p.iban || '—')));
    const clear = node('button',t('Dzēst saglabāto IBAN','Clear saved IBAN'),'demo-clear-iban');
    clear.type='button'; clear.disabled=!p.iban;
    clear.onclick=async()=>{
      clear.disabled=true;
      try {
        const response=await fetch(`/api/demo/people/${p.id}/clear-iban`,{method:'POST'});
        if(!response.ok)throw new Error();
        p.iban=null; render();
        try {
          const session=JSON.parse(localStorage.getItem('faketvijaSession'));
          if(session?.person?.id===p.id){session.person.iban=null;localStorage.setItem('faketvijaSession',JSON.stringify(session));}
        } catch {}
        status.textContent=t('Saglabātais IBAN dzēsts. Nākamajā pieslēgšanās reizē tas būs jāievada vēlreiz.','Saved IBAN cleared. It will be requested on the next login.');
      }catch{clear.disabled=false;status.textContent=t('Neizdevās dzēst IBAN.','Could not clear IBAN.');}
    };
    content.append(clear);
    content.append(node('h3',`${t('Bērni','Children')}: ${p.children.length}`));
    for(const c of p.children){
      const card=node('article',null,'demo-child');card.append(node('h4',`${c.first_name} ${c.last_name}`),copyField(t('Bērna personas kods','Child personal code'),c.personas_kods),node('p',t('Dzimšanas datums: ','Birth date: ')+c.birth_date),node('p',t('Māte: ','Mother: ')+personName(c.mother_id)),node('p',t('Tēvs: ','Father: ')+personName(c.father_id)));
      const table=node('table');const heading=node('tr');for(const title of [t('Pabalsts','Benefit'),t('Māte saņem','Mother receiving'),t('Tēvs saņem','Father receiving')])heading.append(node('th',title));const thead=node('thead');thead.append(heading);table.append(thead);const tbody=node('tbody');
      for(const b of c.benefits){const tr=node('tr');for(const value of [b.benefit_code,c.mother_id ? (b.mother_receiving?t('Jā','Yes'):t('Nē','No')) : '—',c.father_id ? (b.father_receiving?t('Jā','Yes'):t('Nē','No')) : '—'])tr.append(node('td',value));tbody.append(tr);}table.append(tbody);card.append(table);
      for(const a of c.applications)card.append(node('p',`${a.benefit_code} · ${personName(a.person_id)} · ${a.status}`));content.append(card);
    }
    const sources=node('a',t('Datu avoti un licences','Data sources and licenses'));sources.href='data-licenses.html';content.append(sources);
  }
  function options(){const selected=select.value;select.replaceChildren();const query=search.value.trim().toLocaleLowerCase();for(const p of people){if(!`${p.first_name} ${p.last_name} ${p.personas_kods}`.toLocaleLowerCase().includes(query))continue;const option=node('option',`${p.id}. ${p.first_name} ${p.last_name} · ${p.scenario}`);option.value=p.id;select.append(option);}if([...select.options].some(o=>o.value===selected))select.value=selected;render();}
  select.onchange=render;search.oninput=options;
  launch.onclick=async()=>{dialog.showModal();status.textContent=t('Ielādē…','Loading…');try{const response=await fetch('/api/demo/admin');if(!response.ok)throw new Error();people=(await response.json()).people;options();status.textContent='';}catch{status.textContent=t('Demo panelis nav pieejams.','Demo inspector is unavailable.');}};
})();
