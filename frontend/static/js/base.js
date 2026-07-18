const storedUser = localStorage.getItem("user");
if (storedUser) {
    const data = JSON.parse(storedUser);
    const usernameElement = document.querySelector("#username_tag");
    if (usernameElement) {
        usernameElement.textContent = data.user.username;
    }
    const linkElement = document.querySelector("#home_link");
    if (linkElement) {
        let link = "none";
        if (data.user.role === "superadmin") {
            link = "/super-admin/dashboard";
        }
        else if (data.user.role === "admin") {
            link = "/admin/settings";
        }
        linkElement.href = link;
    }
}
export function showToast(message, type) {
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
export function confirmDoubleAction(message, onConfirm) {
    const modal = document.getElementById("global_confirm_modal");
    const msgEl = document.getElementById("confirm_message");
    const cancelBtn = document.getElementById("confirm_cancel_btn");
    const actionBtn = document.getElementById("confirm_action_btn");
    if (!modal || !msgEl || !cancelBtn || !actionBtn)
        return;
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
        }
        else if (clickCount === 2) {
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
window.showToast = showToast;
window.confirmDoubleAction = confirmDoubleAction;
