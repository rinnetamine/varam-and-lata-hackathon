document.querySelector('.accessibility-button')?.addEventListener('click', event => {
  const enabled = document.body.classList.toggle('large-text');
  event.currentTarget.setAttribute('aria-pressed', String(enabled));
});

const numberForm = document.querySelector('#number-form');
if (numberForm) {
  numberForm.addEventListener('submit', event => {
    event.preventDefault();
    const userNumber = document.querySelector('#user-number').value.trim();
    const status = document.querySelector('#form-status');
    if (!/^\d+$/.test(userNumber)) {
      setTranslatedStatus(status, 'Ievadi tikai ciparus.');
      return;
    }
    try {
      sessionStorage.setItem('demoUserNumber', userNumber);
      window.location.assign('profile.html');
    } catch {
      setTranslatedStatus(status, 'Neizdevās saglabāt demonstrācijas sesiju šajā pārlūkā. Atļauj sesijas krātuvi un mēģini vēlreiz.');
    }
  });
}

if (document.body.hasAttribute('data-requires-demo-session')) {
  const profileStatus = document.querySelector('#profile-status');
  try {
    const userNumber = sessionStorage.getItem('demoUserNumber');
    if (!userNumber) {
      window.location.replace('login.html');
    } else {
      const profileNumber = document.querySelector('#profile-user-number');
      if (profileNumber) profileNumber.textContent = userNumber;
    }
  } catch {
    setTranslatedStatus(profileStatus, 'Neizdevās nolasīt demonstrācijas sesiju šajā pārlūkā. Atļauj sesijas krātuvi un pieslēdzies vēlreiz.');
  }
}

document.querySelector('#logout-button')?.addEventListener('click', event => {
  event.preventDefault();
  const status = document.querySelector('#profile-status');
  try {
    sessionStorage.removeItem('demoUserNumber');
    window.location.assign('login.html');
  } catch {
    setTranslatedStatus(status, 'Neizdevās beigt demonstrācijas sesiju. Aizver šo cilni, lai to beigtu.');
  }
});
