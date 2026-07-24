import { showToast, confirmDoubleAction } from "./base.js";
const MANAGER_LIMITS = {
    free: 2,
    pro: 10,
    ultra: 50,
};
let currentUserId = 0;
let managersLimit = 2;
let managersCount = 0;
const tableBody = document.querySelector("#team_table_body");
const addBtn = document.querySelector("#add_member_btn");
const modal = document.querySelector("#add_member_modal");
const form = document.querySelector("#add_member_form");
const cancelBtn = document.querySelector("#cancel_add_btn");
function openModal() {
    if (modal)
        modal.style.display = "flex";
}
function closeModal() {
    if (modal)
        modal.style.display = "none";
    if (form)
        form.reset();
}
async function loadCompany() {
    const stored = localStorage.getItem("user");
    if (stored) {
        const parsed = JSON.parse(stored);
        currentUserId = parsed.user?.user_id ?? 0;
    }
    const response = await fetch("/api/admin/company", {
        credentials: "include",
    });
    if (response.ok) {
        const company = await response.json();
        managersLimit = MANAGER_LIMITS[company.plan] ?? 2;
        managersCount = company.managers_count;
        updateAddButton();
    }
}
function updateAddButton() {
    if (!addBtn)
        return;
    const atLimit = managersCount >= managersLimit;
    addBtn.textContent = `Add Member (${managersCount}/${managersLimit})`;
    addBtn.disabled = atLimit;
    if (atLimit) {
        addBtn.style.opacity = "0.5";
        addBtn.style.cursor = "not-allowed";
    }
    else {
        addBtn.style.opacity = "1";
        addBtn.style.cursor = "pointer";
    }
}
async function loadUsers() {
    if (!tableBody)
        return;
    tableBody.innerHTML = "<tr><td colspan='8'>Loading...</td></tr>";
    const response = await fetch("/api/admin/users", {
        credentials: "include",
    });
    if (response.ok) {
        const users = await response.json();
        users.sort((a, b) => a.user_id - b.user_id);
        tableBody.innerHTML = "";
        if (users.length === 0) {
            tableBody.innerHTML =
                "<tr><td colspan='8'>No team members found.</td></tr>";
            return;
        }
        for (const user of users) {
            const tr = document.createElement("tr");
            const createdDate = new Date(user.user_created_at);
            const formattedCreated = createdDate.toLocaleDateString();
            const lastLogin = user.last_login
                ? new Date(user.last_login).toLocaleDateString()
                : "Never";
            const status = user.is_active
                ? '<span style="color:#869c74">Active</span>'
                : '<span style="color:#ff6b6b">Inactive</span>';
            const isSelf = user.user_id === currentUserId;
            const deleteBtn = isSelf
                ? '<span style="color:#555">—</span>'
                : `<button class="delete-button" data-id="${user.user_id}">Delete</button>`;
            const username = user.username.length > 20
                ? user.username.slice(0, 20) + "..."
                : user.username;
            const email = user.email.length > 20
                ? user.email.slice(0, 20) + "..."
                : user.email;
            tr.innerHTML = `
        <td>${user.user_id}</td>
        <td title="${user.username}">${username}</td>
        <td title="${user.email}">${email}</td>
        <td>${user.role}</td>
        <td>${status}</td>
        <td>${lastLogin}</td>
        <td>${formattedCreated}</td>
        <td>${deleteBtn}</td>
      `;
            tableBody.appendChild(tr);
        }
        tableBody.querySelectorAll(".delete-button").forEach((btn) => {
            btn.addEventListener("click", () => {
                const userId = Number(btn.dataset.id);
                confirmDoubleAction("Remove this team member?", async () => {
                    const res = await fetch(`/api/admin/users/${userId}`, {
                        method: "DELETE",
                        credentials: "include",
                    });
                    if (res.ok) {
                        showToast("Member removed.", "success");
                        managersCount = Math.max(0, managersCount - 1);
                        updateAddButton();
                        loadUsers();
                    }
                    else {
                        const data = await res.json();
                        showToast(data.detail || "Failed to remove member.", "error");
                    }
                });
            });
        });
    }
    else {
        tableBody.innerHTML =
            "<tr><td colspan='8'>Failed to load team members.</td></tr>";
        showToast("Failed to load team members.", "error");
    }
}
async function handleSubmit(e) {
    e.preventDefault();
    const formData = new FormData(form);
    const username = formData.get("username");
    const email = formData.get("email");
    const password = formData.get("password");
    const response = await fetch("/api/admin/users", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, role: "manager" }),
    });
    if (response.ok) {
        showToast("Member added.", "success");
        closeModal();
        managersCount++;
        updateAddButton();
        loadUsers();
    }
    else {
        const data = await response.json();
        showToast(data.detail || "Failed to add member.", "error");
    }
}
addBtn?.addEventListener("click", openModal);
cancelBtn?.addEventListener("click", closeModal);
modal?.addEventListener("click", (e) => {
    if (e.target === modal)
        closeModal();
});
form?.addEventListener("submit", handleSubmit);
async function init() {
    await loadCompany();
    await loadUsers();
}
init();
