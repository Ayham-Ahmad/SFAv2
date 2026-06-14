/* base.js — sidebar toggle, toast system, modal helpers, table utils */

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
const Sidebar = (() => {
  let collapsed = localStorage.getItem('sidebar_collapsed') === '1';

  function apply() {
    const el = document.getElementById('sidebar');
    if (!el) return;
    el.classList.toggle('collapsed', collapsed);
  }

  function toggle() {
    const isMobile = window.innerWidth < 768;
    if (isMobile) {
      const el = document.getElementById('sidebar');
      el?.classList.toggle('mobile-open');
    } else {
      collapsed = !collapsed;
      localStorage.setItem('sidebar_collapsed', collapsed ? '1' : '0');
      apply();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    apply();
    Auth.hydrateSidebar();
    document.getElementById('sidebar-toggle')?.addEventListener('click', toggle);
    document.getElementById('logout-btn')?.addEventListener('click', () => Auth.logout());
    /* Mark active nav item */
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(el => {
      if (el.getAttribute('href') && path.startsWith(el.getAttribute('href')) && el.getAttribute('href') !== '/') {
        el.classList.add('active');
      }
    });
  });

  return { toggle };
})();

/* ── Toast ───────────────────────────────────────────────────────────────── */
const Toast = (() => {
  function show(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const icons = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle' };
    const colors = { success: 'var(--emerald)', error: 'var(--rose)', info: 'var(--blue)' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas ${icons[type]||icons.info}" style="color:${colors[type]||colors.info}"></i><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(40px)'; toast.style.transition = '.3s'; setTimeout(() => toast.remove(), 300); }, duration);
  }
  return { success: m => show(m,'success'), error: m => show(m,'error'), info: m => show(m,'info') };
})();

/* ── Modal ───────────────────────────────────────────────────────────────── */
const Modal = (() => {
  function open(id)  { document.getElementById(id)?.classList.add('open'); }
  function close(id) { document.getElementById(id)?.classList.remove('open'); }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('open'); });
    });
    document.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', () => btn.closest('.modal-overlay')?.classList.remove('open'));
    });
  });
  return { open, close };
})();

/* ── Table utils ─────────────────────────────────────────────────────────── */
const Table = (() => {
  function searchFilter(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
  return { searchFilter };
})();

/* ── Confirm dialog ──────────────────────────────────────────────────────── */
function confirmAction(message, onConfirm) {
  const overlay = document.getElementById('confirm-modal');
  const msg = document.getElementById('confirm-message');
  const btn = document.getElementById('confirm-ok');
  if (!overlay) return onConfirm();
  if (msg) msg.textContent = message;
  Modal.open('confirm-modal');
  const handler = () => { onConfirm(); Modal.close('confirm-modal'); btn.removeEventListener('click', handler); };
  btn.addEventListener('click', handler);
}
