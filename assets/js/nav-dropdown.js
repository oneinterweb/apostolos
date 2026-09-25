(function () {
  function closeAll(except) {
    document.querySelectorAll(".masthead__menu-item--has-children.is-open").forEach(function (item) {
      if (item === except) return;
      item.classList.remove("is-open");
      var btn = item.querySelector(".masthead__dropdown-trigger");
      if (btn) btn.setAttribute("aria-expanded", "false");
    });
  }

  document.querySelectorAll(".masthead__dropdown-trigger").forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      var item = btn.closest(".masthead__menu-item--has-children");
      var open = !item.classList.contains("is-open");
      closeAll(item);
      item.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".masthead__menu-item--has-children")) closeAll();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeAll();
  });
})();
