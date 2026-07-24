"use strict";
const cards = {};
const prev = {};
function initCards() {
    const ids = ["cost_card", "users_card", "companies_card", "databases_card", "interactions_card"];
    for (const id of ids) {
        const el = document.querySelector(`#${id}`);
        if (el)
            cards[id] = el;
    }
}
function updateCards(details) {
    const mapping = {
        cost_card: `$${details.llm_cost.toFixed(2)}`,
        users_card: String(details.active_users),
        companies_card: String(details.companies),
        databases_card: String(details.active_databases),
        interactions_card: String(details.total_interactions),
    };
    for (const [id, value] of Object.entries(mapping)) {
        const el = cards[id];
        if (!el)
            continue;
        if (prev[id] !== undefined && prev[id] !== value) {
            const card = el.closest(".card");
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
async function initialFetch() {
    const response = await fetch("/api/super-admin/dashboard/stats", {
        credentials: "include",
    });
    if (response.ok) {
        const details = await response.json();
        updateCards(details);
    }
}
function connectSSE() {
    const source = new EventSource("/api/super-admin/dashboard/stream");
    source.onmessage = (event) => {
        try {
            const details = JSON.parse(event.data);
            updateCards(details);
        }
        catch {
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
