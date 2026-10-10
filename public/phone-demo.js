// A fictional email-to-portal journey. No Google login, email API or personal data.
(() => {
  const tools = document.createElement('div'); tools.className = 'login-demo-tools';
  const existing = document.querySelector('.demo-launch'); if (existing) tools.append(existing);
  const launch = document.createElement('button'); launch.type = 'button'; launch.className = 'phone-demo-launch'; launch.setAttribute('aria-haspopup', 'dialog');
  const icon = document.createElementNS('http://www.w3.org/2000/svg','svg'); icon.setAttribute('viewBox','0 0 24 24'); icon.setAttribute('fill','none'); icon.setAttribute('stroke','currentColor'); icon.setAttribute('stroke-width','1.8'); icon.setAttribute('aria-hidden','true');
  const path = document.createElementNS(icon.namespaceURI,'path'); path.setAttribute('d','M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2M10 18h4'); icon.append(path);
  const label = document.createElement('span'); label.dataset.i18n = 'phone.launch'; launch.append(icon,label); tools.append(launch); document.body.append(tools);
  const dialog = document.createElement('dialog'); dialog.className = 'phone-demo-dialog'; dialog.setAttribute('aria-labelledby','phone-demo-title');
  // This markup is static; all translated email content is inserted as text.
  dialog.innerHTML = `<div class="phone-demo-caption"><span id="phone-demo-title" data-i18n="phone.title"></span><button type="button" class="phone-demo-close" data-i18n-attr="aria-label:common.close">×</button></div><div class="phone-frame"><div class="phone-statusbar"><time class="phone-status-time"></time><span class="phone-island" aria-hidden="true"></span><span class="phone-status-icons" aria-hidden="true"><svg viewBox="0 0 20 16" fill="currentColor"><path d="M1 12h3v3H1zm5-4h3v7H6zm5-4h3v11h-3zm5-4h3v15h-3z"/></svg><small>5G</small><svg viewBox="0 0 24 14" fill="none" stroke="currentColor"><rect x="1" y="1" width="19" height="12" rx="3"/><path d="M22 4v6" stroke-width="2"/><rect x="3" y="3" width="15" height="8" rx="1" fill="currentColor"/></svg><small>92%</small></span></div><div class="phone-demo-screen"></div><div class="phone-home-bar" aria-hidden="true"></div></div>`;
  document.body.append(dialog);
  const screen = dialog.querySelector('.phone-demo-screen');
  let view = 'home', timer;
  const gmailIcon = `<svg viewBox="0 0 48 36" aria-hidden="true"><path d="M5 31V8l19 14L43 8v23" fill="none" stroke="#4285f4" stroke-width="7" stroke-linejoin="round"/><path d="M5 31V8" stroke="#34a853" stroke-width="7"/><path d="M43 31V8" stroke="#fbbc04" stroke-width="7"/><path d="M5 8l19 14L43 8" fill="none" stroke="#ea4335" stroke-width="7" stroke-linejoin="round"/></svg>`;
  function make(tag, key, className) { const node = document.createElement(tag); if (className) node.className = className; if (key) { node.dataset.i18n = key; node.textContent = t(key); } return node; }
  function time() {
    const now = new Date(), value = now.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
    dialog.querySelector('.phone-status-time').textContent = value;
    const clock = screen.querySelector('.phone-home-clock'); if (clock) clock.textContent = value;
    const date = screen.querySelector('.phone-home-date'); if (date) date.textContent = now.toLocaleDateString(i18n.locale(),{weekday:'long',day:'numeric',month:'long'});
  }
  function render() {
    screen.replaceChildren();
    if (view === 'home') {
      const home = make('div', null, 'phone-home'); home.append(make('p',null,'phone-home-date'),make('div',null,'phone-home-clock'));
      const gmail = make('button', null, 'phone-app'); gmail.type = 'button'; gmail.setAttribute('aria-label',t('phone.gmailOpen'));
      const logo = make('span',null,'phone-gmail-icon'); logo.innerHTML = gmailIcon; const badge=make('span',null,'phone-app-badge'); badge.textContent='1'; logo.append(badge);
      const name=make('span');name.textContent='Gmail';gmail.append(logo,name);gmail.onclick=()=>{view='inbox';render();screen.querySelector('.phone-email-row').focus();};home.append(gmail);screen.append(home);
    } else {
      const header=make('div',null,'phone-mail-header'); const back=make('button',null,'phone-mail-back');back.type='button';back.textContent='←';back.setAttribute('aria-label',t('phone.back'));back.onclick=()=>{view=view==='message'?'inbox':'home';render();screen.querySelector('button')?.focus();};
      const title=make('h3');title.textContent='Gmail';header.append(back,title);screen.append(header);
      if (view === 'inbox') {
        screen.append(make('p','phone.inbox','phone-mail-folder'));
        const row=make('button',null,'phone-email-row');row.type='button';const avatar=make('span',null,'phone-sender-avatar');avatar.textContent='V';
        const preview=make('div',null,'phone-email-preview');const sender=make('strong');sender.textContent='VSAA · DEMO';preview.append(sender,make('p','phone.subject'),make('small','phone.preview'));row.append(avatar,preview);row.onclick=()=>{view='message';render();screen.querySelector('.phone-site-link').focus();};screen.append(row);
      } else {
        const message=make('article',null,'phone-email-message');const sender=make('p',null,'phone-email-sender');sender.textContent='VSAA · demo@vsaa.example';
        const link=make('a','phone.visit','phone-site-link');link.href='index.html#pakalpojumi';link.onclick=()=>dialog.close();
        message.append(make('h2','phone.subject'),sender,make('p','phone.greeting'),make('p','phone.body'),link,make('p','phone.note','phone-email-note'));screen.append(message);
      }
    }
    applyLanguage(dialog);time();
  }
  launch.onclick=()=>{view='home';render();dialog.showModal();timer=setInterval(time,60000);screen.querySelector('button')?.focus();};
  dialog.querySelector('.phone-demo-close').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{clearInterval(timer);launch.focus();});
  dialog.addEventListener('click',event=>{if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close();}});
  i18n.onChange(()=>{label.textContent=t('phone.launch');if(dialog.open)render();});
  applyLanguage(tools);
})();
