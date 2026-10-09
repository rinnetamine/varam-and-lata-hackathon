document.querySelector('.accessibility-button')?.addEventListener('click', event => {
  const enabled = document.body.classList.toggle('large-text');
  event.currentTarget.setAttribute('aria-pressed', String(enabled));
});

// Demo login, session storage, route guarding and log out live in auth.js (server-backed personas kods login).
