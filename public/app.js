document.querySelector('.accessibility-button')?.addEventListener('click', event => {
  const enabled = document.body.classList.toggle('large-text');
  event.currentTarget.setAttribute('aria-pressed', String(enabled));
});
