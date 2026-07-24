import { showToast } from "./base.js";
const tableBody = document.querySelector("#tents_table_body");
setTimeout(() => loadTents(), 100);
async function loadTents() {
    if (!tableBody)
        return;
    tableBody.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";
    const response = await fetch("/api/tents/", {
        credentials: "include",
    });
    if (response.ok) {
        const tents = await response.json();
        tents.sort((a, b) => a.db_id - b.db_id);
        tableBody.innerHTML = "";
        if (tents.length === 0) {
            tableBody.innerHTML =
                "<tr><td colspan='6'>No databases found.</td></tr>";
            return;
        }
        for (const tent of tents) {
            const tr = document.createElement("tr");
            const status = tent.is_connected
                ? '<span style="color:#869c74">Connected</span>'
                : '<span style="color:#ff6b6b">Disconnected</span>';
            const lastSynced = tent.last_synced
                ? new Date(tent.last_synced).toLocaleDateString()
                : "Never";
            const createdDate = new Date(tent.db_created_at);
            const formattedCreated = createdDate.toLocaleDateString();
            const dbName = tent.db_name.length > 40
                ? tent.db_name.slice(0, 40) + "..."
                : tent.db_name;
            tr.innerHTML = `
        <td>${tent.db_id}</td>
        <td title="${tent.db_name}">${dbName}</td>
        <td>${tent.db_type}</td>
        <td>${status}</td>
        <td>${lastSynced}</td>
        <td>${formattedCreated}</td>
      `;
            tableBody.appendChild(tr);
        }
    }
    else {
        tableBody.innerHTML =
            "<tr><td colspan='6'>Failed to load databases.</td></tr>";
        showToast("Failed to load databases.", "error");
    }
}
