// Illustrative bundles only: replace these with real workflows as the project grows.
// Design-only login mock: no database, authentication, persistence, or network submission.
const consent = document.querySelector('#demo-consent');
const providerLink = document.querySelector('#provider-link');
if (consent && providerLink) {
  consent.addEventListener('change', () => {
    providerLink.setAttribute('aria-disabled', String(!consent.checked));
    document.querySelector('#selection-status').textContent = consent.checked
      ? 'Vari atvērt eParaksts mobile saskarnes maketu.'
      : 'Lai atvērtu maketu, atzīmē demonstrācijas apliecinājumu.';
  });
  providerLink.addEventListener('click', event => {
    if (!consent.checked) {
      event.preventDefault();
      consent.focus();
    }
  });
}
const numberForm = document.querySelector('#number-form');
if (numberForm) {
  numberForm.addEventListener('submit', event => {
    event.preventDefault();
    document.querySelector('#user-number').value = '';
    document.querySelector('#form-status').textContent = 'Dizaina demonstrācija. Nekas nav nosūtīts, lietotājs nav izveidots.';
  });
}
