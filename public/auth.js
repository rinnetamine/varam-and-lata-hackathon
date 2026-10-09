// Demo session handling: personas kods login against /api, bearer token kept in localStorage.
// The token survives reloads and other tabs until the user logs out or the server expires it.
(() => {
  const STORAGE_KEY = 'faketvijaSession';
  const LOGIN_PAGE = 'login.html';
  const PROFILE_PAGE = 'profile.html';
  const destination = session => session.person.iban ? PROFILE_PAGE : 'bank-account.html';
  const CODE_PATTERN = /^\d{6}-?\d{5}$/;

  const readSession = () => {
    try {
      const session = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return session && typeof session.token === 'string' && session.person ? session : null;
    } catch {
      return null;
    }
  };
  const writeSession = session => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      return true;
    } catch {
      return false;
    }
  };
  const clearSession = () => {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  };

  async function api(path, { method = 'GET', token, body } = {}) {
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body) headers['Content-Type'] = 'application/json';
    const response = await fetch(`/api/${path}`, { method, headers, body: body && JSON.stringify(body) });
    let data = null;
    try { data = await response.json(); } catch {}
    return { ok: response.ok, httpStatus: response.status, data };
  }

  // Confirms the stored token with the server. A rejected token ends the session;
  // an unreachable server keeps the cached one so a brief outage does not log anyone out.
  async function currentSession() {
    const session = readSession();
    if (!session) return null;
    try {
      const { ok, httpStatus, data } = await api('me', { token: session.token });
      if (ok) {
        const refreshed = { ...session, person: data.person };
        writeSession(refreshed);
        return refreshed;
      }
      if (httpStatus === 401) {
        clearSession();
        return null;
      }
    } catch {}
    return session;
  }

  async function logout() {
    const session = readSession();
    clearSession();
    if (session) {
      try { await api('logout', { method: 'POST', token: session.token }); } catch {}
    }
  }

  const setText = (selector, text) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = text;
  };

  const consent = document.querySelector('#demo-consent');
  const providerLink = document.querySelector('#provider-link');
  if (consent && providerLink) {
    const updateConsent = () => {
      providerLink.setAttribute('aria-disabled', String(!consent.checked));
      const status = document.querySelector('#selection-status');
      if (status) status.hidden = consent.checked;
    };
    consent.addEventListener('change', updateConsent);
    providerLink.addEventListener('click', event => {
      if (!consent.checked) {
        event.preventDefault();
        consent.focus();
      }
    });
    updateConsent();
  }

  const numberForm = document.querySelector('#number-form');
  const guardedPage = document.body.hasAttribute('data-requires-demo-session');
  const loginButton = document.querySelector('#login-button');

  // Login page: signed-in users skip straight to the profile; otherwise check the code on the server.
  if (numberForm) {
    currentSession().then(session => { if (session) location.replace(destination(session)); });

    const input = document.querySelector('#user-number');
    const status = document.querySelector('#form-status');
    const submit = numberForm.querySelector('[type="submit"]');
    numberForm.addEventListener('submit', async event => {
      event.preventDefault();
      const personasKods = input.value.trim();
      if (!CODE_PATTERN.test(personasKods)) {
        setTranslatedStatus(status, 'Ievadi personas kodu formātā 000000-00000.');
        input.focus();
        return;
      }
      submit.disabled = true;
      setTranslatedStatus(status, 'Notiek pieslēgšanās…');
      try {
        const { ok, httpStatus, data } = await api('login', { method: 'POST', body: { personasKods } });
        if (ok) {
          if (writeSession({ token: data.token, person: data.person })) {
            setTranslatedStatus(status, 'Pieslēgšanās veiksmīga. Notiek pāreja…');
            location.assign(destination({person: data.person}));
            return;
          }
          setTranslatedStatus(status, 'Pārlūks neļauj saglabāt sesiju. Atļauj vietnes datu glabāšanu un mēģini vēlreiz.');
        } else if (httpStatus === 401) {
          setTranslatedStatus(status, 'Šāds personas kods demonstrācijas datubāzē nav atrasts.');
        } else if (httpStatus === 400) {
          setTranslatedStatus(status, 'Ievadi personas kodu formātā 000000-00000.');
        } else {
          setTranslatedStatus(status, 'Serveris nevarēja apstrādāt pieprasījumu. Mēģini vēlreiz.');
        }
      } catch {
        setTranslatedStatus(status, 'Neizdevās sazināties ar serveri. Pārbaudi, vai tas darbojas.');
      }
      submit.disabled = false;
    });
  }

  const bankForm = document.querySelector('#bank-form');
  if (bankForm) {
    currentSession().then(session => {
      if (!session) location.replace(LOGIN_PAGE);
      else if (session.person.iban) location.replace(PROFILE_PAGE);
    });
    bankForm.addEventListener('submit', async event => {
      event.preventDefault();
      const status = document.querySelector('#bank-status');
      const submit = bankForm.querySelector('[type="submit"]');
      if (submit.disabled) return;
      const input = document.querySelector('#bank-iban');
      const iban = input.value.replace(/\s+/g, '').toUpperCase();
      input.removeAttribute('aria-invalid');
      if (!/^LV[0-9]{2}[A-Z]{4}[A-Z0-9]{13}$/.test(iban)) {
        input.setAttribute('aria-invalid', 'true');
        setTranslatedStatus(status, 'IBAN formāts nav pareizs. Tam jāsākas ar LV un jāsatur 21 rakstzīme.');
        input.focus();
        return;
      }
      const session = readSession();
      if (!session) return location.replace(LOGIN_PAGE);
      input.value = iban;
      submit.disabled = true;
      input.disabled = true;
      bankForm.setAttribute('aria-busy', 'true');
      status.classList.add('bank-checking');
      setTranslatedStatus(status, 'Pārbauda bankas kontu…');
      try {
        // Simulate the bank verification step after local format validation.
        await new Promise(resolve => setTimeout(resolve, 1100));
        const result = await api('iban', {method:'POST', token:session.token,
          body:{iban}});
        if (result.httpStatus === 401) {
          clearSession(); location.replace(LOGIN_PAGE); return;
        }
        if (!result.ok) {
          const errors = {invalid_iban:'IBAN konts neeksistē vai jums nav tam piekļuves.', bank_account_unavailable:'IBAN konts neeksistē vai jums nav tam piekļuves.'};
          setTranslatedStatus(status, errors[result.data?.error] || 'Neizdevās saglabāt konta numuru. Mēģini vēlreiz.');
        } else if (writeSession({...session, person:result.data.person})) {
          location.replace(PROFILE_PAGE);
        } else {
          setTranslatedStatus(status, 'Neizdevās saglabāt sesiju. Mēģini vēlreiz.');
        }
      } catch { setTranslatedStatus(status, 'Neizdevās saglabāt konta numuru. Mēģini vēlreiz.'); }
      finally {
        submit.disabled = false;
        input.disabled = false;
        bankForm.removeAttribute('aria-busy');
        status.classList.remove('bank-checking');
      }
    });
  }

  // Profile and services pages: require a session, fill in the person's data, wire up log out.
  if (guardedPage) {
    const renderPerson = ({ person }) => {
      setText('#profile-name', person.firstName);
      setText('#profile-account-name', `${person.firstName} ${person.lastName}`);
      setText('#profile-avatar', person.firstName.charAt(0).toUpperCase());
      setText('#profile-full-name', `${person.firstName} ${person.lastName}`);
      setText('#profile-user-number', person.personasKods);
      setText('#profile-email', person.email);
      setText('#profile-phone', person.phone);
      setText('#profile-address', person.address || '—');
      setText('#profile-iban', person.iban || '—');
    };

    const cached = readSession();
    if (!cached) {
      location.replace(LOGIN_PAGE);
    } else {
      renderPerson(cached);
      currentSession().then(session => {
        if (!session) location.replace(LOGIN_PAGE);
        else if (!session.person.iban) location.replace('bank-account.html');
        else renderPerson(session);
      });
    }

  }

    document.querySelector('#logout-button')?.addEventListener('click', async event => {
      event.preventDefault();
      await logout();
      location.assign('index.html');
    });

  // Portal landing page: when signed in, the login button becomes a link to the profile.
  if (loginButton) {
    const signedOutMarkup = loginButton.innerHTML;
    const signedOutHref = loginButton.getAttribute('href');

    const showSignedIn = ({ person }) => {
      loginButton.setAttribute('href', person.iban ? PROFILE_PAGE : 'bank-account.html');
      loginButton.replaceChildren();
      const name = document.createElement('span');
      name.setAttribute('data-no-translate', '');
      name.style.fontSize = 'inherit';
      name.textContent = `${person.firstName} ${person.lastName}`;
      const arrow = document.createElement('span');
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '→';
      loginButton.append(name, ' ', arrow);
    };
    const showSignedOut = () => {
      loginButton.setAttribute('href', signedOutHref);
      loginButton.innerHTML = signedOutMarkup;
      applyLanguage();
    };

    const cached = readSession();
    if (cached) showSignedIn(cached);
    currentSession().then(session => {
      if (session) showSignedIn(session);
      else if (cached) showSignedOut();
    });
  }

  // Keep other open tabs in step when someone logs in or out.
  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY && (guardedPage || loginButton)) location.reload();
  });
})();
