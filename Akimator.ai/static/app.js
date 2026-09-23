const BILLION = 1_000_000_000;

const state = {
  city: null,
  decisions: {},
};

const cardsEl = document.getElementById("cards");
const usedEl = document.getElementById("budget-used");
const leftEl = document.getElementById("budget-left");
const fillEl = document.getElementById("budget-fill");
const errorEl = document.getElementById("budget-error");
const simulateBtn = document.getElementById("simulate-btn");
const resetBtn = document.getElementById("reset-btn");
const resultsEl = document.getElementById("results");
const overlayEl = document.getElementById("overlay");
const barsEl = document.getElementById("bars");

function formatBillion(value) {
  return `${Math.round(value / BILLION)} млрд ₸`;
}

function selectedMeasures() {
  if (!state.city) return [];
  return state.city.categories
    .map((category) => {
      const measureId = state.decisions[category.id];
      return category.measures.find((measure) => measure.id === measureId);
    })
    .filter(Boolean);
}

function budgetUsed() {
  return selectedMeasures().reduce((sum, measure) => sum + measure.cost, 0);
}

function updateBudget() {
  const total = state.city.budget_total;
  const used = budgetUsed();
  const left = total - used;
  const complete = state.city.categories.every((category) => state.decisions[category.id]);
  const over = used > total;

  usedEl.textContent = formatBillion(used);
  leftEl.textContent = formatBillion(Math.max(0, left));
  fillEl.style.width = `${Math.min(100, (used / total) * 100)}%`;
  fillEl.classList.toggle("over", over);

  if (over) {
    errorEl.textContent = `Бюджет превышен на ${Math.round((used - total) / BILLION)} млрд ₸. Выберите более доступный набор мер.`;
    errorEl.classList.remove("hidden");
  } else {
    errorEl.classList.add("hidden");
    errorEl.textContent = "";
  }

  simulateBtn.disabled = !complete || over;
}

function renderCards() {
  cardsEl.innerHTML = "";
  state.city.categories.forEach((category) => {
    const card = document.createElement("article");
    card.className = "card";
    const selected = category.measures.find((measure) => measure.id === state.decisions[category.id]);
    card.innerHTML = `
      <h2>${category.emoji} ${category.title}</h2>
      <select data-category="${category.id}">
        <option value="">Выберите меру</option>
        ${category.measures
          .map(
            (measure) =>
              `<option value="${measure.id}" ${
                state.decisions[category.id] === measure.id ? "selected" : ""
              }>${measure.name} — ${formatBillion(measure.cost)}</option>`
          )
          .join("")}
      </select>
      <p class="meta">${selected ? `Стоимость: ${formatBillion(selected.cost)}` : "Мера ещё не выбрана"}</p>
    `;
    cardsEl.appendChild(card);
  });
}

function aqolBand(score) {
  if (score >= 70) return { cls: "high", label: "Высокий уровень качества жизни" };
  if (score >= 55) return { cls: "mid", label: "Средний уровень качества жизни" };
  return { cls: "low", label: "Низкий уровень качества жизни" };
}

function renderList(id, items) {
  document.getElementById(id).innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function renderResults(data) {
  const scoreEl = document.getElementById("aqol-value");
  const band = aqolBand(data.aqol_score);
  scoreEl.textContent = `${data.aqol_score} / 100`;
  scoreEl.className = `score-value ${band.cls}`;
  document.getElementById("aqol-band").textContent = band.label;
  document.getElementById("budget-result").textContent =
    `Бюджет использован: ${Math.round(data.budget_used / BILLION)} / 100 млрд ₸`;
  document.getElementById("analysis-summary").textContent = data.analysis.summary;
  renderList("strengths", data.analysis.strengths);
  renderList("risks", data.analysis.risks);
  renderList("consequences", data.analysis.consequences);

  const labels = {
    transport: "Транспорт",
    green: "Зеленые зоны",
    social: "Социальная инфраструктура",
    safety: "Безопасность",
    services: "Городские услуги",
  };
  barsEl.innerHTML = Object.entries(labels)
    .map(
      ([key, label]) => `
      <div class="bar-row">
        <header><span>${label}</span><strong>${data.indicators[key]}/100</strong></header>
        <div class="track"><span data-width="${data.indicators[key]}"></span></div>
      </div>`
    )
    .join("");
  resultsEl.classList.remove("hidden");
  requestAnimationFrame(() => {
    barsEl.querySelectorAll(".track span").forEach((bar) => {
      bar.style.width = `${bar.dataset.width}%`;
    });
  });
}

cardsEl.addEventListener("change", (event) => {
  const select = event.target.closest("select");
  if (!select) return;
  const categoryId = select.dataset.category;
  if (select.value) {
    state.decisions[categoryId] = select.value;
  } else {
    delete state.decisions[categoryId];
  }
  const category = state.city.categories.find((item) => item.id === categoryId);
  const selected = category.measures.find((measure) => measure.id === select.value);
  const meta = select.parentElement.querySelector(".meta");
  meta.textContent = selected ? `Стоимость: ${formatBillion(selected.cost)}` : "Мера ещё не выбрана";
  updateBudget();
});

resetBtn.addEventListener("click", () => {
  state.decisions = {};
  resultsEl.classList.add("hidden");
  renderCards();
  updateBudget();
});

simulateBtn.addEventListener("click", async () => {
  overlayEl.classList.remove("hidden");
  try {
    const response = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decisions: state.decisions }),
    });
    const payload = await response.json();
    if (!response.ok) {
      errorEl.textContent = payload.detail || "Не удалось выполнить симуляцию.";
      errorEl.classList.remove("hidden");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 700));
    renderResults(payload);
  } catch (error) {
    errorEl.textContent = "Сервер недоступен. Проверьте, что приложение запущено.";
    errorEl.classList.remove("hidden");
  } finally {
    overlayEl.classList.add("hidden");
  }
});

async function boot() {
  const response = await fetch("/api/city");
  state.city = await response.json();
  document.getElementById("budget-total").textContent = formatBillion(state.city.budget_total);
  renderCards();
  updateBudget();
}

boot();
