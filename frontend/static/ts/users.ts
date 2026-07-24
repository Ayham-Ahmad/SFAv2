import { showToast } from "./base.js";

interface UserOut {
  user_id: number;
  username: string;
  email: string;
  role: string;
  company_id: number | null;
  is_active: boolean;
  user_created_at: string;
  last_login: string | null;
}

const tableBody =
  document.querySelector<HTMLTableSectionElement>("#users_table_body");

loadUsers();

async function loadUsers(): Promise<void> {
  if (!tableBody) return;
  tableBody.innerHTML = "<tr><td colspan='8'>Loading...</td></tr>";

  const response = await fetch("/api/super-admin/all-users", {
    credentials: "include",
  });

  if (response.ok) {
    const users: UserOut[] = await response.json();
    tableBody.innerHTML = "";

    if (users.length === 0) {
      tableBody.innerHTML = "<tr><td colspan='8'>No users found.</td></tr>";
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

      const username: string =
        user.username.length > 20
          ? user.username.slice(0, 20) + "..."
          : user.username;
      const email: string =
        user.email.length > 20 ? user.email.slice(0, 20) + "..." : user.email;

      tr.innerHTML = `
        <td>${user.user_id}</td>
        <td title="${user.username}">${username}</td>
        <td title="${user.email}">${email}</td>
        <td>${user.role}</td>
        <td>${user.company_id ?? "-"}</td>
        <td>${status}</td>
        <td>${lastLogin}</td>
        <td>${formattedCreated}</td>
      `;
      tableBody.appendChild(tr);
    }
  } else {
    tableBody.innerHTML = "<tr><td colspan='8'>Failed to load users.</td></tr>";
    showToast("Failed to load users.", "error");
  }
}
