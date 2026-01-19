// ===============================
// authGuard.js — FINAL (JWT)
// ===============================

// API
const AUTH_ME_API = "http://127.0.0.1:5000/api/auth/me";

// Pages
const LOGIN_PAGE = "login.html";

/* ======================================
   GET CURRENT USER (JWT)
====================================== */
async function getCurrentUser() {
  const token = localStorage.getItem("token");
  if (!token) return null;

  try {
    const res = await fetch(AUTH_ME_API, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json"
      }
    });

    if (!res.ok) return null;

    // Backend returns: { name, email, role }
    return await res.json();

  } catch (err) {
    console.error("❌ Auth check failed:", err);
    return null;
  }
}

/* ======================================
   REQUIRE AUTH (ANY USER)
====================================== */
async function requireAuth() {
  const user = await getCurrentUser();

  if (!user) {
    localStorage.removeItem("token");
    window.location.replace(LOGIN_PAGE);
    return;
  }

  // Expose globally
  window.currentUser = user;
}

/* ======================================
   REQUIRE ROLE
====================================== */
async function requireRole(...allowedRoles) {
  const user = await getCurrentUser();

  if (!user) {
    localStorage.removeItem("token");
    window.location.replace(LOGIN_PAGE);
    return;
  }

  if (!allowedRoles.includes(user.role)) {
    alert("❌ Access denied");
    window.history.back();
    return;
  }

  window.currentUser = user;
}

/* ======================================
   LOGOUT (JWT = CLIENT SIDE)
====================================== */
function logoutUser() {
  localStorage.removeItem("token");
  window.location.replace(LOGIN_PAGE);
}

/* ======================================
   AUTO-BIND LOGOUT BUTTONS
====================================== */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".logout-btn").forEach(btn => {
    btn.addEventListener("click", logoutUser);
  });
});

// Expose functions globally
window.requireAuth = requireAuth;
window.requireRole = requireRole;
window.logoutUser = logoutUser;
