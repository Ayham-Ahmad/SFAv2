"use strict";
async function getCards() {
    const response = await fetch("/api/super-admin/dashboard/stats", {
        credentials: "include",
    });
    if (!response.ok) {
        console.log("Failed to fetch dashboard stats");
        return;
    }
    const details = await response.json();
    const costCardElement = document.querySelector("#cost_card");
    const usersCardElement = document.querySelector("#users_card");
    const companiesCardElement = document.querySelector("#companies_card");
    const databasesCardElement = document.querySelector("#databases_card");
    const interactionsCardElement = document.querySelector("#interactions_card");
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
