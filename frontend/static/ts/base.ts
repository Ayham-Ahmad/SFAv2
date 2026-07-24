export interface User {
  user_id: number;
  username: string;
  email: string;
  company_id: number;
  company_name?: string;
  role: string;
}

async function initializeNav(): Promise<void> {
  const navBody = document.querySelector<HTMLDivElement>("#dynamic_nav");
  if (!navBody) return;

  const response = await fetch("/role");
  if (!response.ok) return;

  const data = await response.json();
  const role: string = data.role;

  const partialMap: Record<string, string> = {
    superadmin: "/partials/_sidebar_superadmin.html",
    admin: "/partials/_sidebar_admin.html",
  };

  const path = partialMap[role] || "";

  const partialResponse = await fetch(path);
  if (partialResponse.ok) {
    navBody.innerHTML = await partialResponse.text();
  }
}

const storedUser = localStorage.getItem("user");

if (storedUser) {
  const data = JSON.parse(storedUser);

  const usernameElement =
    document.querySelector<HTMLDivElement>("#username_tag");

  if (usernameElement) {
    usernameElement.textContent = data.user.username;
  }

  const linkElement = document.querySelector<HTMLAnchorElement>("#home_link");

  if (linkElement) {
    let link: string = "none";

    if (data.user.role === "superadmin") {
      link = "/super-admin/dashboard";
    } else if (data.user.role === "admin") {
      link = "/admin/settings";
    } else if (data.user.role === "manager") {
      link = "/analytics";
    }

    initializeNav();

    linkElement.href = link;

    if (
      (data.user.role === "admin" || data.user.role === "manager") &&
      data.user.company_name
    ) {
      const companyTag = document.getElementById("company_tag");
      if (companyTag) {
        companyTag.textContent = data.user.company_name;
      }
    }
  }
}

document.getElementById("logout_btn")?.addEventListener("click", async () => {
  await fetch("/logout", { method: "POST", credentials: "include" });
  localStorage.removeItem("user");
  window.location.href = "/login";
});

export function showToast(message: string, type: "success" | "error"): void {
  const toast = document.getElementById("toast_notification");
  const toastMessage = document.getElementById("toast_message");

  if (toast && toastMessage) {
    toastMessage.textContent = message;

    toast.className = "toast";
    toast.classList.add(type);
    toast.classList.add("show");

    setTimeout(() => {
      toast.classList.remove("show");
    }, 3000);
  }
}

export function confirmDoubleAction(
  message: string,
  onConfirm: () => void,
): void {
  const modal = document.getElementById("global_confirm_modal");
  const msgEl = document.getElementById("confirm_message");
  const cancelBtn = document.getElementById("confirm_cancel_btn");
  const actionBtn = document.getElementById("confirm_action_btn");

  if (!modal || !msgEl || !cancelBtn || !actionBtn) return;

  msgEl.textContent = message;
  actionBtn.textContent = "Delete";
  modal.style.display = "flex";

  let clickCount = 0;

  const handleAction = () => {
    clickCount++;
    if (clickCount === 1) {
      actionBtn.textContent = "Click again to confirm";
      actionBtn.style.backgroundColor = "#ff6b6b";
      actionBtn.style.color = "#2a1111";
    } else if (clickCount === 2) {
      cleanup();
      onConfirm();
    }
  };

  const handleCancel = () => {
    cleanup();
  };

  const cleanup = () => {
    modal.style.display = "none";
    actionBtn.style.backgroundColor = "";
    actionBtn.style.color = "";
    actionBtn.removeEventListener("click", handleAction);
    cancelBtn.removeEventListener("click", handleCancel);
  };

  actionBtn.addEventListener("click", handleAction);
  cancelBtn.addEventListener("click", handleCancel);
}

(window as any).showToast = showToast;
(window as any).confirmDoubleAction = confirmDoubleAction;

const isLoginPage = window.location.pathname === "/login";
if (!isLoginPage && !localStorage.getItem("user")) {
  window.location.href = "/login";
}
