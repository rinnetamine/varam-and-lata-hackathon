// Illustrative bundles only: replace these with real workflows as the project grows.
const bundles = {
  moving: {
    title: "Mainu dzīvesvietu",
    steps: ["Norādi jauno dzīvesvietu", "Apskati deklarēšanas pakalpojuma piemēru", "Iepazīsties ar jaunās pašvaldības pakalpojumiem"],
  },
  family: {
    title: "Ģimenē piedzimis bērns",
    steps: ["Apskati dzimšanas reģistrācijas piemēru", "Iepazīsties ar pieejamajiem pabalstiem", "Apskati pašvaldības atbalsta pieteikuma piemēru"],
  },
  business: {
    title: "Sāku uzņēmējdarbību",
    steps: ["Izvēlies uzņēmējdarbības veidu", "Apskati reģistrācijas pakalpojuma piemēru", "Iepazīsties ar nodokļu un pašvaldības pakalpojumiem"],
  },
};

const panel = document.querySelector("#bundle");
const title = document.querySelector("#bundle-title");
const steps = document.querySelector("#bundle-steps");
let activeButton;

document.querySelectorAll("[data-bundle]").forEach((button) => {
  button.setAttribute("aria-controls", "bundle");
  button.setAttribute("aria-expanded", "false");
  button.addEventListener("click", () => {
    activeButton?.setAttribute("aria-expanded", "false");
    activeButton = button;
    const bundle = bundles[button.dataset.bundle];
    title.textContent = bundle.title;
    steps.replaceChildren(...bundle.steps.map((step) => {
      const item = document.createElement("li");
      item.textContent = step;
      return item;
    }));
    panel.hidden = false;
    button.setAttribute("aria-expanded", "true");
    title.focus();
  });
});

document.querySelector("#close-bundle").addEventListener("click", () => {
  panel.hidden = true;
  activeButton?.setAttribute("aria-expanded", "false");
  activeButton?.focus();
});
