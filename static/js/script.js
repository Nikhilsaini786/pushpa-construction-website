document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".nav-links");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "Are you sure?")) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("flash-hide");
      window.setTimeout(() => message.remove(), 350);
    }, 5000);
  });

  // Floating WhatsApp Widget Interactive Toggle
  const waBtn = document.getElementById("whatsappFloatBtn");
  const waCard = document.getElementById("whatsappCard");
  const waClose = document.getElementById("waCloseBtn");

  if (waBtn && waCard) {
    waBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = waCard.style.display === "block";
      waCard.style.display = isVisible ? "none" : "block";
    });

    if (waClose) {
      waClose.addEventListener("click", (e) => {
        e.stopPropagation();
        waCard.style.display = "none";
      });
    }

    document.addEventListener("click", (e) => {
      if (waCard.style.display === "block" && !waCard.contains(e.target) && !waBtn.contains(e.target)) {
        waCard.style.display = "none";
      }
    });
  }

  // Contact Page: Send Inquiry Directly via WhatsApp
  const sendWhatsAppBtn = document.getElementById("sendWhatsAppBtn");
  if (sendWhatsAppBtn) {
    sendWhatsAppBtn.addEventListener("click", () => {
      const name = (document.getElementById("name")?.value || "").trim();
      const phone = (document.getElementById("phone")?.value || "").trim();
      const email = (document.getElementById("email")?.value || "").trim();
      const projectType = (document.getElementById("project_type")?.value || "").trim();
      const message = (document.getElementById("message")?.value || "").trim();

      if (!name || !phone || !message) {
        alert("Please fill in your Name, Phone Number, and Project Details first!");
        return;
      }

      let text = `🏗️ *New Project Inquiry - Pushpa Construction*\n\n`;
      text += `*Customer Name:* ${name}\n`;
      text += `*Phone:* ${phone}\n`;
      if (email) text += `*Email:* ${email}\n`;
      if (projectType) text += `*Project Scope:* ${projectType}\n`;
      text += `*Requirement Details:*\n${message}\n\n`;
      text += `_Sent via Pushpa Construction Website Portal_`;

      const encoded = encodeURIComponent(text);
      window.open(`https://wa.me/919351788485?text=${encoded}`, "_blank");
    });
  }

  // Show / Hide Password Toggle with Eye Icon
  document.querySelectorAll(".toggle-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) return;

      const eyeOpen = btn.querySelector(".eye-open");
      const eyeClosed = btn.querySelector(".eye-closed");

      if (input.type === "password") {
        input.type = "text";
        btn.setAttribute("aria-label", "Hide password");
        if (eyeOpen) eyeOpen.style.display = "none";
        if (eyeClosed) eyeClosed.style.display = "block";
      } else {
        input.type = "password";
        btn.setAttribute("aria-label", "Show password");
        if (eyeOpen) eyeOpen.style.display = "block";
        if (eyeClosed) eyeClosed.style.display = "none";
      }
    });
  });
});

