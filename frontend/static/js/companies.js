import { showToast, confirmDoubleAction } from "./base.js";
const tableBody = document.querySelector("#companies_table_body");
loadCompanies();
async function loadCompanies() {
    if (!tableBody)
        return;
    tableBody.innerHTML = "<tr><td colspan='8'>Loading...</td></tr>";
    const response = await fetch("/api/super-admin/companies");
    if (response.ok) {
        const companies = await response.json();
        tableBody.innerHTML = "";
        if (companies.length === 0) {
            tableBody.innerHTML = "<tr><td colspan='8'>No companies found.</td></tr>";
            return;
        }
        for (const company of companies) {
            const tr = document.createElement("tr");
            const date = new Date(company.company_created_at);
            const formattedDate = date.toLocaleDateString();
            const companyName = company.company_name.length > 20
                ? company.company_name.slice(0, 20) + "..."
                : company.company_name;
            tr.innerHTML = `
        <td>${company.company_id}</td>
        <td title="${company.company_name}">${companyName}</td>
        <td>${company.plan}</td>
        <td>${company.databases_count}</td>
        <td>${company.managers_count}</td>
        <td>${company.total_storage_mb.toFixed(2)}</td>
        <td>${formattedDate}</td>
        <td>
            <button class="delete-button" data-id="${company.company_id}" data-name="${company.company_name}">Delete</button>
        </td>
      `;
            tableBody.appendChild(tr);
        }
        const deleteButtons = document.querySelectorAll(".delete-button");
        deleteButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const id = button.getAttribute("data-id");
                const name = button.getAttribute("data-name");
                if (id && name) {
                    confirmDoubleAction(`Are you sure you want to permanently delete: ${name}?`, () => deleteCompany(parseInt(id), name));
                }
            });
        });
    }
    else {
        tableBody.innerHTML =
            "<tr><td colspan='8'>Failed to load companies.</td></tr>";
    }
}
async function deleteCompany(companyId, companyName) {
    const response = await fetch(`/api/super-admin/companies/${companyId}`, {
        method: "DELETE",
    });
    if (response.ok) {
        showToast(`The company ${companyName} was deleted.`, "success");
        await loadCompanies();
    }
    else {
        const errorData = await response.json();
        showToast(errorData.detail, "error");
    }
}
