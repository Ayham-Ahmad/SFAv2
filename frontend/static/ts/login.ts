import type { User } from "./base";

interface UserLoginDetails {
  username: string;
  password: string;
}

interface UserSignUpDetails {
  username: string;
  email: string;
  password: string;
  company_name: string;
}

interface ReturnedUserDetails {
  session_id: number;
  user: User;
}

const loginForm = document.querySelector<HTMLFormElement>("#login_body");

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await login();
});

const signUpForm = document.querySelector<HTMLFormElement>("#sign_up_body");

signUpForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await signUp();
});

const loginTab = document.querySelector<HTMLDivElement>(".login");
const signupTab = document.querySelector<HTMLDivElement>(".sign-up");

loginTab?.addEventListener("click", loginCard);
signupTab?.addEventListener("click", signUpCard);

async function login(): Promise<void> {
  const usernameInput =
    document.querySelector<HTMLInputElement>("#login_username");
  const passwordInput =
    document.querySelector<HTMLInputElement>("#login_password");

  const user: UserLoginDetails = {
    username: usernameInput?.value || "",
    password: passwordInput?.value || "",
  };

  const formData = new URLSearchParams();

  formData.append("username", user.username);
  formData.append("password", user.password);

  const response = await fetch("/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });

  if (response.ok) {
    const data: ReturnedUserDetails = await response.json();

    localStorage.setItem("user", JSON.stringify(data));

    document.getElementById("error_message")?.classList.add("error-message");

    if (data.user.role === "superadmin") {
      window.location.href = "/super-admin/dashboard";
    } else if (data.user.role === "admin") {
      window.location.href = "/admin/settings";
    } else if (data.user.role === "manager") {
      window.location.href = "/analytics";
    }
  } else {
    const error = await response.json();

    const error_element = document.getElementById("error_message");

    if (error_element != null) {
      error_element.textContent = error.detail;
      error_element.style.color = "rgb(220, 20, 60)";
      error_element.classList.remove("error-message");
    }
  }
}

async function signUp(): Promise<void> {
  const usernameInput =
    document.querySelector<HTMLInputElement>("#signup_username");
  const emailInput = document.querySelector<HTMLInputElement>("#signup_email");
  const passwordInput =
    document.querySelector<HTMLInputElement>("#signup_password");
  const companyInput =
    document.querySelector<HTMLInputElement>("#company_name");

  const user: UserSignUpDetails = {
    username: usernameInput?.value || "",
    email: emailInput?.value || "",
    password: passwordInput?.value || "",
    company_name: companyInput?.value || "",
  };

  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(user),
  });

  if (response.ok) {
    const message = document.getElementById("error_message");

    if (message != null) {
      message.textContent =
        "Your Company is Registered Successfully, You can login now!";
      message.style.color = "rgb(139, 255, 113)";
      message.style.fontSize = "12";
      message.classList.remove("error-message");
    }
  } else {
    const error = await response.json();
    const error_element = document.getElementById("error_message");

    if (error_element != null) {
      error_element.textContent = error.detail;
      error_element.style.color = "rgb(220, 20, 60)";
      error_element.classList.remove("error-message");
    }
  }
}

function loginCard(): void {
  document.getElementById("error_message")?.classList.add("error-message");

  const signUp = document.getElementById("sign_up_body");
  const login = document.getElementById("login_body");

  if (signUp instanceof HTMLElement) {
    signUp.style.display = "none";
  }

  if (login instanceof HTMLElement) {
    login.style.display = "block";
  }
}

function signUpCard(): void {
  document.getElementById("error_message")?.classList.add("error-message");

  const signUp = document.getElementById("sign_up_body");
  const login = document.getElementById("login_body");

  if (login instanceof HTMLElement) {
    login.style.display = "none";
  }

  if (signUp instanceof HTMLElement) {
    signUp.style.display = "block";
  }
}
