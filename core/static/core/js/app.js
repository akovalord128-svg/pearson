(function () {
  // Dark / Light rejim (tanlov brauzerda saqlanadi)
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var root = document.documentElement;
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  });

  // Parolni ko'rsatish / yashirish (login sahifasi)
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = btn.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
    });
  });

  // Google tugmasi — hozircha faqat dizayn
  document.querySelectorAll("[data-soon]").forEach(function (btn) {
    btn.addEventListener("click", function () { alert(btn.dataset.soon); });
  });

  // Ro'yxatdan o'tish: tutor tanlansa kod maydoni chiqadi
  var reg = document.querySelector("[data-register]");
  if (reg) {
    var box = reg.querySelector("[data-tutor-code]");
    var sync = function () {
      var r = reg.querySelector("input[name=role]:checked");
      box.hidden = !(r && r.value === "tutor");
    };
    reg.querySelectorAll("input[name=role]").forEach(function (r) { r.addEventListener("change", sync); });
    sync();
  }

  // O'chirishdan oldin tasdiqlash
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // Practice dropdown
  document.querySelectorAll("[data-nav-group]").forEach(function (btn) {
    btn.addEventListener("click", function () { btn.parentElement.classList.toggle("open"); });
  });

  // User menu
  var ub = document.querySelector("[data-user-toggle]");
  if (ub) {
    var dd = ub.parentElement.querySelector(".dropdown");
    ub.addEventListener("click", function (e) { e.stopPropagation(); dd.hidden = !dd.hidden; });
    document.addEventListener("click", function () { dd.hidden = true; });
  }

  // Xabarlar (toast) avtomatik yo'qoladi
  setTimeout(function () {
    document.querySelectorAll(".toast").forEach(function (t) { t.style.display = "none"; });
  }, 5000);
})();
