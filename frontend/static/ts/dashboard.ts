interface DashboardStatus {
  active_users: number;
  companies: number;
  llm_cost: number;
  active_databases: number;
  total_interactions: number;
}

async function getCards(): Promise<void> {
  const response = await fetch("/api/super-admin/dashboard/stats", {
    credentials: "include",
  });

  if (!response.ok) {
    console.log("Failed to fetch dashboard stats");
    return;
  }

  const details: DashboardStatus = await response.json();

  const costCardElement = document.querySelector<HTMLDivElement>("#cost_card");
  const usersCardElement =
    document.querySelector<HTMLDivElement>("#users_card");
  const companiesCardElement =
    document.querySelector<HTMLDivElement>("#companies_card");
  const databasesCardElement =
    document.querySelector<HTMLDivElement>("#databases_card");
  const interactionsCardElement =
    document.querySelector<HTMLDivElement>("#interactions_card");

  if (costCardElement) {
    costCardElement.textContent = `${details.llm_cost}$`;
  }

  if (usersCardElement) {
    usersCardElement.textContent = details.active_users.toString();
  }

  if (companiesCardElement) {
    companiesCardElement.textContent = details.companies.toString();
  }

  if (databasesCardElement) {
    databasesCardElement.textContent = details.active_databases.toString();
  }

  if (interactionsCardElement) {
    interactionsCardElement.textContent = details.total_interactions.toString();
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await getCards();
});
