// Open a cited rule when arriving through a source link or the contents menu.
(() => {
  function revealReference() {
    const id = location.hash.slice(1);
    const target = document.getElementById(id);
    if (target?.matches('details')) target.open = true;
  }
  window.addEventListener('hashchange', revealReference);
  revealReference();
})();
