interface User {
  username: string;
  role: "admin" | "superadmin" | "manager";
}

type ToastType = "success" | "error" | "info";

interface IconMap {
  [key: string]: string;
}

interface ColorMap {
  [key: string]: string;
}

interface SidebarAPI {
  toggle(): void;
}

interface ToastAPI {
  success(message: string): void;
  error(message: string): void;
  info(message: string): void;
}

interface ModalAPI {
  open(id: string): void;
  close(id: string): void;
}

interface TableAPI {
  searchFilter(inputId: string, tableId: string): void;
}

declare const Auth: {
  getUser(): User | null; // check if i should remove null later or not
  hydrateSidebar(): void;
  logout(): void;
};

const Sidebar = (() => {
  let collapsed = localStorage.getItem("sidebar_collapsed") === "1";
  console.log(collapsed);
  

  const apply = (): void => {
    const el = document.getElementById("sidebar");
    if (!el) return;
    el.classList.toggle("collapsed", collapsed);
  };

  const toggle = (): void => {
    const isMobile = window.innerWidth < 768;
    if (isMobile) {
      const el = document.getElementById("sidebar");
      el?.classList.toggle("mobile-open");
    } else {
      collapsed = !collapsed;
      localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
      apply();
    }
  };

  document.addEventListener("DOMContentLoaded", (): void => {
    apply();
    Auth.hydrateSidebar();
    document
      .getElementById("sidebar-toggle")
      ?.addEventListener("click", toggle);
    document
      .getElementById("logout-btn")
      ?.addEventListener("click", () => Auth.logout());

    const path = window.location.pathname;
    document.querySelectorAll<HTMLAnchorElement>(".nav-item").forEach((el) => {
      const href = el.getAttribute("href");
      if (href && path.startsWith(href) && href !== "/") {
        el.classList.add("active");
      }
    });
  });

  return { toggle } as SidebarAPI;
})();

const Toast = (() => {
  const show = (
    message: string,
    type: ToastType = "info",
    duration: number = 4000,
  ): void => {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const icons: IconMap = {
      success: "fa-check-circle",
      error: "fa-times-circle",
      info: "fa-info-circle",
    };

    const colors: ColorMap = {
      success: "var(--emerald)",
      error: "var(--rose)",
      info: "var(--blue)",
    };

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="color:${colors[type] || colors.info}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(40px)";
      toast.style.transition = ".3s";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  };

  return {
    success: (m: string) => show(m, "success"),
    error: (m: string) => show(m, "error"),
    info: (m: string) => show(m, "info"),
  } as ToastAPI;
})();

const Modal = (() => {
  const open = (id: string): void => {
    document.getElementById(id)?.classList.add("open");
  };

  const close = (id: string): void => {
    document.getElementById(id)?.classList.remove("open");
  };

  document.addEventListener("DOMContentLoaded", (): void => {
    document
      .querySelectorAll<HTMLElement>(".modal-overlay")
      .forEach((overlay) => {
        overlay.addEventListener("click", (e: Event) => {
          if (e.target === overlay) overlay.classList.remove("open");
        });
      });

    document
      .querySelectorAll<HTMLButtonElement>(".modal-close")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          btn.closest(".modal-overlay")?.classList.remove("open");
        });
      });
  });

  return { open, close } as ModalAPI;
})();

const Table = (() => {
  const searchFilter = (inputId: string, tableId: string): void => {
    const input = document.getElementById(inputId) as HTMLInputElement | null;
    const table = document.getElementById(tableId);
    if (!input || !table) return;

    input.addEventListener("input", (): void => {
      const query = input.value.toLowerCase();
      table.querySelectorAll<HTMLTableRowElement>("tbody tr").forEach((row) => {
        row.style.display = row.textContent?.toLowerCase().includes(query)
          ? ""
          : "none";
      });
    });
  };

  return { searchFilter } as TableAPI;
})();

const confirmAction = (message: string, onConfirm: () => void): void => {
  const overlay = document.getElementById("confirm-modal");
  const msg = document.getElementById("confirm-message");
  const btn = document.getElementById("confirm-ok") as HTMLButtonElement | null;

  if (!overlay) return onConfirm();
  if (msg) msg.textContent = message;

  Modal.open("confirm-modal");

  const handler = (): void => {
    onConfirm();
    Modal.close("confirm-modal");
    btn?.removeEventListener("click", handler);
  };

  btn?.addEventListener("click", handler);
};

const buildNav = (): void => {
  const user = Auth.getUser();
  if (!user) {
    window.location.href = "/login";
    return;
  }

  const nav = document.getElementById("sidebar-nav");
  if (!nav) return;

  const role = user.role;

  const shared = `
    <div class="nav-section-label">Workspace</div>
    <a class="nav-item" href="/analytics"><i class="fas fa-robot"></i><span class="nav-label">AI Advisor</span></a>`;

  const adminNav = `
    <div class="nav-section-label">Management</div>
    <a class="nav-item" href="/admin/settings"><i class="fas fa-building"></i><span class="nav-label">Company Settings</span></a>
    <a class="nav-item" href="/admin/tents"><i class="fas fa-database"></i><span class="nav-label">Data Sources</span></a>
    <a class="nav-item" href="/admin/team"><i class="fas fa-users"></i><span class="nav-label">Team</span></a>`;

  const superNav = `
    <div class="nav-section-label">Platform</div>
    <a class="nav-item" href="/super-admin/dashboard"><i class="fas fa-tachometer-alt"></i><span class="nav-label">Dashboard</span></a>
    <a class="nav-item" href="/super-admin/companies"><i class="fas fa-building"></i><span class="nav-label">Companies</span></a>
    <a class="nav-item" href="/super-admin/users"><i class="fas fa-users"></i><span class="nav-label">All Users</span></a>
    <a class="nav-item" href="/super-admin/usage"><i class="fas fa-chart-bar"></i><span class="nav-label">LLM Usage</span></a>`;

  const profileNav = `
    <div class="nav-section-label">Account</div>
    <a class="nav-item" href="/profile"><i class="fas fa-user-cog"></i><span class="nav-label">My Profile</span></a>`;

  switch (role) {
    case "superadmin":
      nav.innerHTML = superNav + shared + profileNav;
      break;
    case "admin":
      nav.innerHTML = shared + adminNav + profileNav;
      break;
    default:
      nav.innerHTML = shared + profileNav;
  }
};

buildNav();
