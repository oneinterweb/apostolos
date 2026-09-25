(function () {
  var root = document.querySelector("[data-hero-slider]");
  if (!root) return;

  var slides = Array.prototype.slice.call(root.querySelectorAll("[data-hero-slide]"));
  var dots = Array.prototype.slice.call(root.querySelectorAll("[data-hero-dot]"));
  var prev = root.querySelector("[data-hero-prev]");
  var next = root.querySelector("[data-hero-next]");
  if (slides.length < 2) return;

  var index = 0;
  var timer = null;
  var delay = 3000;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function show(nextIndex) {
    index = (nextIndex + slides.length) % slides.length;
    slides.forEach(function (slide, i) {
      var on = i === index;
      slide.classList.toggle("is-active", on);
      slide.setAttribute("aria-hidden", on ? "false" : "true");
    });
    dots.forEach(function (dot, i) {
      var on = i === index;
      dot.classList.toggle("is-active", on);
      if (on) dot.setAttribute("aria-current", "true");
      else dot.removeAttribute("aria-current");
    });
  }

  function start() {
    if (reduceMotion) return;
    stop();
    timer = window.setInterval(function () {
      show(index + 1);
    }, delay);
  }

  function stop() {
    if (timer) window.clearInterval(timer);
    timer = null;
  }

  if (prev) prev.addEventListener("click", function () {
    show(index - 1);
    start();
  });
  if (next) next.addEventListener("click", function () {
    show(index + 1);
    start();
  });
  dots.forEach(function (dot, i) {
    dot.addEventListener("click", function () {
      show(i);
      start();
    });
  });

  root.addEventListener("mouseenter", stop);
  root.addEventListener("mouseleave", start);
  root.addEventListener("focusin", stop);
  root.addEventListener("focusout", start);

  root.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") {
      show(index - 1);
      start();
    } else if (e.key === "ArrowRight") {
      show(index + 1);
      start();
    }
  });

  var startX = null;
  root.addEventListener("touchstart", function (e) {
    if (!e.changedTouches || !e.changedTouches.length) return;
    startX = e.changedTouches[0].clientX;
  }, { passive: true });
  root.addEventListener("touchend", function (e) {
    if (startX == null || !e.changedTouches || !e.changedTouches.length) return;
    var dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 40) {
      show(index + (dx < 0 ? 1 : -1));
      start();
    }
    startX = null;
  }, { passive: true });

  start();
})();
