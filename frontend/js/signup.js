// signup.js (FINAL WORKING VERSION)

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("signupForm");
  const signupMessage = document.getElementById("signupMessage");
  const signupButton = form.querySelector("button");

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // IMPORTANT

    // Reset message
    signupMessage.className = "state-box";
    signupMessage.textContent = "";
    signupMessage.style.display = "none";

    // Collect values
    const name = document.getElementById("name").value.trim();
    const organization = document.getElementById("organization").value;
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    // -------------------------
    // Validation
    // -------------------------
    if (!name || !organization || !email || !password || !confirmPassword) {
      showMessage("All fields are required.", "error");
      return;
    }

    if (password !== confirmPassword) {
      showMessage("Passwords do not match.", "error");
      return;
    }

    // -------------------------
    // Disable button
    // -------------------------
    signupButton.disabled = true;
    signupButton.textContent = "Creating account...";

    try {
      const res = await fetch("http://127.0.0.1:5000/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name,
          email,
          organization,
          password
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Signup failed");
      }

      showMessage("Account created successfully! Redirecting to login...", "success");

      setTimeout(() => {
        window.location.href = "/login.html";
      }, 1500);

    } catch (err) {
      showMessage(err.message, "error");
      signupButton.disabled = false;
      signupButton.textContent = "Sign Up";
    }
  });

  // -------------------------
  // Message helper
  // -------------------------
  function showMessage(msg, type) {
    signupMessage.textContent = msg;
    signupMessage.classList.add(type);
    signupMessage.style.display = "block";
  }
});
