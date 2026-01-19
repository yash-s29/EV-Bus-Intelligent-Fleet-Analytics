// ===============================
// login.js — SPA JWT Integration (Redirect to index.html)
// ===============================

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const loginButton = document.querySelector(".primary-btn");
  const loginMessage = document.getElementById("loginMessage");

  if (!form || !loginButton || !loginMessage) return;

  // Handle form submit
  form.addEventListener("submit", loginUser);

  async function loginUser(e) {
    e.preventDefault();
    clearMessage();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!email || !password) {
      showMessage("Please enter both email and password.", "error");
      return;
    }

    // Disable button and show loading state
    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();

      // Check if login failed
      if (!res.ok || !data.success || !data.token) {
        showMessage(data.error || "Login failed. Check your credentials.", "error");
        loginButton.disabled = false;
        loginButton.textContent = "Login";
        return;
      }

      // ✅ Store JWT + user info in localStorage
      localStorage.setItem("evfleet_token", data.token);
      localStorage.setItem("evfleet_user", JSON.stringify({
        name: data.user.name,
        role: data.user.role,
        email: data.user.email || email
      }));

      showMessage(`Welcome ${data.user.name}! Redirecting...`, "success");

      // ✅ Redirect to dashboard (index.html)
      setTimeout(() => {
        window.location.href = "/index.html";
      }, 500);

    } catch (err) {
      console.error("Login error:", err);
      showMessage("Server error. Please try again later.", "error");
      loginButton.disabled = false;
      loginButton.textContent = "Login";
    }
  }

  // ==============================
  // Show feedback message
  // ==============================
  function showMessage(msg, type = "error") {
    loginMessage.textContent = msg;
    loginMessage.className = `state-box ${type}`;
    loginMessage.style.display = "block";
  }

  // ==============================
  // Clear feedback
  // ==============================
  function clearMessage() {
    loginMessage.textContent = "";
    loginMessage.className = "state-box hidden";
    loginMessage.style.display = "none";
  }

  // ==============================
  // SPA Auto-redirect if already logged in
  // ==============================
  const token = localStorage.getItem("evfleet_token");
  if (token) {
    // Optional: validate token with backend
    window.location.href = "/index.html";
  }
});
