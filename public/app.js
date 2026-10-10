// Shared accessibility preference, applied before rendering on every page.
(() => {
  const key = 'faketvijaLargeText';
  const root = document.documentElement;
  function apply(enabled) {
    root.style.zoom = enabled ? '1.2' : '';
    root.classList.toggle('large-text', enabled);
    document.querySelectorAll('.accessibility-button').forEach(button => button.setAttribute('aria-pressed', String(enabled)));
  }
  try { apply(localStorage.getItem(key) === 'true'); } catch { apply(false); }
  document.addEventListener('click', event => {
    const button = event.target.closest('.accessibility-button');
    if (!button) return;
    const enabled = !root.classList.contains('large-text');
    try { localStorage.setItem(key, String(enabled)); } catch {}
    apply(enabled);
  });
  document.addEventListener('DOMContentLoaded', () => apply(root.classList.contains('large-text')));
  window.addEventListener('storage', event => { if (event.key === key || event.key === null) apply(event.key === null ? false : event.newValue === 'true'); });
})();
