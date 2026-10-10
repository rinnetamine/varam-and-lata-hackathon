// Illustrative 2026 estimates. Daily contribution wage is entered explicitly;
// this tool does not reconstruct VSAA insurance records or determine entitlement.
function calculateChildBenefit(code, values) {
  const daily = Number(values.daily), days = Number(values.days);
  if (['maternitates', 'paternitates', 'vecaku'].includes(code) && (!Number.isFinite(daily) || daily <= 0 || daily > 100000)) throw new Error('input');
  if (code === 'maternitates') {
    if (![112, 126, 140].includes(days)) throw new Error('input');
    return {amount: daily * .8 * days, unit: 'calc.total', formula: `${daily} × 80% × ${days}`};
  }
  if (code === 'paternitates') return {amount: Math.round((daily * .8 * 1.46 + Number.EPSILON) * 100) / 100 * 10, unit: 'calc.total', formula: `${daily} × 80% × 1.46 × 10`};
  if (code === 'vecaku') {
    if (![13, 19].includes(Number(values.duration)) || !Number.isInteger(days) || days < 28 || days > 31) throw new Error('input');
    const rate = Number(values.duration) === 13 ? .6 : .4375;
    const multiplier = values.working ? .75 : 1;
    return {amount: daily * rate * days * multiplier, unit: 'calc.month', formula: `${daily} × ${rate * 100}% × ${days}${values.working ? ' × 75%' : ''}`};
  }
  if (code === 'gimenes_valsts') {
    const count = Number(values.count);
    if (!Number.isInteger(count) || count < 0 || count > 20) throw new Error('input');
    return {amount: count === 0 ? 0 : count === 1 ? 25 : count === 2 ? 100 : count === 3 ? 225 : count * 100, unit: 'calc.month', formula: null};
  }
  const birth = values.birth;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birth || '') || Number.isNaN(Date.parse(birth)) || new Date(birth).toISOString().slice(0, 10) !== birth || birth < '2013-01-01' || birth > '2026-12-31') throw new Error('input');
  if (code === 'berna_piedzimsanas') return {amount: birth >= '2026-01-01' ? 600 : 421.17, unit: 'calc.once', formula: null};
  if (code === 'berna_kopsanas') {
    if (!['under18', '18to24'].includes(values.age)) throw new Error('input');
    return {amount: values.age === 'under18' ? 298 : birth <= '2026-11-02' ? 42.69 : 0, unit: 'calc.month', formula: null};
  }
  throw new Error('input');
}
if (typeof module !== 'undefined') module.exports = {calculateChildBenefit};
if (typeof document !== 'undefined') (() => {
  const root = document.querySelector('#benefit-calculator');
  if (!root) return;
  const form = root.querySelector('form'), select = form.elements.benefit;
  const result = root.querySelector('[data-calculator-result]');
  let lastResult = null;
  const codes = ['maternitates', 'paternitates', 'berna_piedzimsanas', 'berna_kopsanas', 'vecaku', 'gimenes_valsts'];
  const slugs = ['maternitates', 'paternitates', 'berna-piedzimsanas', 'berna-kopsanas', 'vecaku', 'gimenes-valsts'];
  function showFields() {
    root.querySelectorAll('[data-calculator-for]').forEach(field => {
      const active = field.dataset.calculatorFor.split(' ').includes(select.value);
      field.hidden = !active;
      field.querySelectorAll('input,select').forEach(input => { input.disabled = !active; });
    });
    root.querySelector('[data-calculator-source]').href = `https://www.vsaa.gov.lv/lv/pakalpojumi/${slugs[codes.indexOf(select.value)]}-pabalsta-pieskirsana-un-izmaksasana`;
  }
  function paintResult() {
    result.replaceChildren();
    if (!lastResult) { result.hidden = true; return; }
    result.hidden = false;
    const label = document.createElement('p'); label.textContent = t('calc.result');
    const amount = document.createElement('strong'); amount.className = 'calculator-amount'; amount.textContent = i18n.formatMoney(lastResult.amount);
    const unit = document.createElement('p'); unit.textContent = t(lastResult.unit);
    result.append(label, amount, unit);
    if (lastResult.formula) { const formula = document.createElement('p'); formula.className = 'form-note'; formula.textContent = `${t('calc.formula')}: ${lastResult.formula}`; result.append(formula); }
  }
  select.addEventListener('change', () => { showFields(); lastResult = null; paintResult(); });
  form.addEventListener('input', () => { lastResult = null; paintResult(); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    try {
      lastResult = calculateChildBenefit(select.value, {daily: form.elements.daily.value, days: select.value === 'vecaku' ? form.elements.monthDays.value : form.elements.days.value, duration: form.elements.duration.value, working: form.elements.working.checked, count: form.elements.count.value, birth: form.elements.birth.value, age: form.elements.age.value});
      paintResult();
    } catch { lastResult = null; result.hidden = false; result.textContent = t('calc.invalid'); }
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-benefit-calculator]');
    if (!link) return;
    select.value = link.dataset.benefitCalculator; showFields(); lastResult = null; paintResult();
    requestAnimationFrame(() => select.focus({preventScroll: true}));
  });
  i18n.onChange(paintResult);
  const requested = new URLSearchParams(location.search).get('benefit');
  if (codes.includes(requested)) select.value = requested;
  showFields();
})();
