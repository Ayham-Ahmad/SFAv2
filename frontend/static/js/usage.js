import { showToast } from "./base.js";
const tableBody = document.querySelector("#usage_table_body");
const totalCostCard = document.querySelector("#total_cost_card");
const totalTokensCard = document.querySelector("#total_tokens_card");
const totalCallsCard = document.querySelector("#total_calls_card");
const totalModelsCard = document.querySelector("#total_models_card");
loadUsage();
async function loadUsage() {
    if (!tableBody)
        return;
    tableBody.innerHTML = "<tr><td colspan='7'>Loading...</td></tr>";
    const response = await fetch("/api/super-admin/usage/llm", {
        credentials: "include",
    });
    if (response.ok) {
        const data = await response.json();
        const models = Object.entries(data);
        tableBody.innerHTML = "";
        if (models.length === 0) {
            tableBody.innerHTML =
                "<tr><td colspan='7'>No usage data available.</td></tr>";
            return;
        }
        let totalCost = 0;
        let totalTokens = 0;
        let totalCalls = 0;
        for (const [modelName, usage] of models) {
            totalCost += usage.cost;
            totalTokens += usage.tokens;
            totalCalls += usage.calls;
            const tr = document.createElement("tr");
            tr.innerHTML = `
        <td>${modelName}</td>
        <td>$${usage.cost.toFixed(2)}</td>
        <td>${formatNumber(usage.tokens)}</td>
        <td>${formatNumber(usage.calls)}</td>
        <td>${renderFeedback(usage.feedback)}</td>
        <td>
          ${usage.avg_response_time.toFixed(2)}
          <span class="metric-unit">s</span>
        </td>
        <td>
          ${usage.avg_memory_usage.toFixed(1)}
          <span class="metric-unit">MB</span>
        </td>
      `;
            tableBody.appendChild(tr);
        }
        if (totalCostCard)
            totalCostCard.textContent = `$${totalCost.toFixed(2)}`;
        if (totalTokensCard)
            totalTokensCard.textContent = formatNumber(totalTokens);
        if (totalCallsCard)
            totalCallsCard.textContent = formatNumber(totalCalls);
        if (totalModelsCard)
            totalModelsCard.textContent = String(models.length);
    }
    else {
        tableBody.innerHTML =
            "<tr><td colspan='7'>Failed to load usage data.</td></tr>";
        showToast("Failed to load usage data.", "error");
    }
}
function formatNumber(n) {
    if (n >= 1_000_000)
        return (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000)
        return (n / 1_000).toFixed(1) + "K";
    return String(n);
}
function renderFeedback(pct) {
    const clamped = Math.max(0, Math.min(100, pct));
    let cls = "neutral";
    if (clamped >= 50)
        cls = "positive";
    else if (clamped > 0)
        cls = "negative";
    return `
    <div class="feedback-bar-wrapper">
      <div class="feedback-bar">
        <div class="feedback-bar-fill ${cls}" style="width: ${clamped}%"></div>
      </div>
      <span class="feedback-value">${clamped.toFixed(0)}%</span>
    </div>
  `;
}
