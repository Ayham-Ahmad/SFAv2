interface DashboardStatus {
  active_users: number;
  companies: number;
  llm_cost: number;
  active_databases: number;
  total_interactions: number;
}

const cards: Record<string, HTMLDivElement> = {};
const prev: Record<string, string> = {};

function initCards(): void {
  const ids = ["cost_card", "users_card", "companies_card", "databases_card", "interactions_card"];
  for (const id of ids) {
    const el = document.querySelector<HTMLDivElement>(`#${id}`);
    if (el) cards[id] = el;
  }
}

function updateCards(details: DashboardStatus): void {
  const mapping: Record<string, string> = {
    cost_card: `$${details.llm_cost.toFixed(2)}`,
    users_card: String(details.active_users),
    companies_card: String(details.companies),
    databases_card: String(details.active_databases),
    interactions_card: String(details.total_interactions),
  };

  for (const [id, value] of Object.entries(mapping)) {
    const el = cards[id];
    if (!el) continue;
    if (prev[id] !== undefined && prev[id] !== value) {
      const card = el.closest<HTMLDivElement>(".card");
      if (card) {
        card.classList.remove("pulse");
        void card.offsetWidth;
        card.classList.add("pulse");
      }
    }
    el.textContent = value;
    prev[id] = value;
  }
}

async function initialFetch(): Promise<void> {
  const response = await fetch("/api/super-admin/dashboard/stats", {
    credentials: "include",
  });
  if (response.ok) {
    const details: DashboardStatus = await response.json();
    updateCards(details);
  }
}

function connectSSE(): void {
  const source = new EventSource("/api/super-admin/dashboard/stream");

  source.onmessage = (event) => {
    try {
      const details: DashboardStatus = JSON.parse(event.data);
      updateCards(details);
    } catch {
      // skip malformed
    }
  };

  source.onerror = () => {
    source.close();
    setTimeout(connectSSE, 3000);
  };
}

document.addEventListener("DOMContentLoaded", async () => {
  initCards();
  await initialFetch();
  connectSSE();
});
