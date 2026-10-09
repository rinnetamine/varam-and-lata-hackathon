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
  const message = document.querySelector('#demo-message');
  document.querySelector('#mail-search').addEventListener('input', event => {
    const matches = message.textContent.toLocaleLowerCase().includes(event.target.value.trim().toLocaleLowerCase());
    message.hidden = !matches;
    document.querySelector('#mail-empty').hidden = matches;
  });
  message.addEventListener('toggle', () => {
    if (!message.open) return;
    message.querySelector('.unread-tag').hidden = true;
    document.querySelector('.unread-number').textContent = '0';
  });
})();
