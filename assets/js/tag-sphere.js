(function () {
  var root = document.querySelector("[data-tag-sphere]");
  if (!root) return;

  var stage = root.querySelector("[data-tag-stage]");
  if (!stage) return;

  var tags = Array.prototype.slice.call(stage.querySelectorAll("a"));
  if (!tags.length) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var points = [];
  var maxCount = 1;
  var golden = Math.PI * (3 - Math.sqrt(5));

  tags.forEach(function (el) {
    maxCount = Math.max(maxCount, parseInt(el.getAttribute("data-tag-count"), 10) || 1);
  });

  tags.forEach(function (el, i) {
    var count = parseInt(el.getAttribute("data-tag-count"), 10) || 1;
    var weight = Math.log(count + 1) / Math.log(maxCount + 1);
    var y = tags.length === 1 ? 0 : 1 - (i / (tags.length - 1)) * 2;
    var r = Math.sqrt(Math.max(0, 1 - y * y));
    var theta = golden * i;
    var shrink = el.textContent.trim().length > 16 ? 0.82 : 1;
    el.style.fontSize = ((0.52 + weight * 0.72) * shrink) + "rem";
    points.push({
      el: el,
      x: Math.cos(theta) * r,
      y: y,
      z: Math.sin(theta) * r
    });
  });

  var rotX = 0.18;
  var rotY = 0.4;
  var panX = 0;
  var panY = 0;
  var scale = 1;
  var radius = 180;
  var dragging = false;
  var dragged = false;
  var lastX = 0;
  var lastY = 0;
  var pointers = {};
  var pinchStart = 0;
  var pinchScale = 1;
  var panStartX = 0;
  var panStartY = 0;
  var midStartX = 0;
  var midStartY = 0;
  var frame = 0;
  var DRAG_THRESHOLD = 10;

  function linkFrom(el) {
    if (!el) return null;
    if (el.closest) return el.closest("[data-tag-stage] a");
    return el.tagName === "A" ? el : null;
  }

  function isModified(event) {
    return !!(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey);
  }

  function openTag(link) {
    if (!link || !link.href) return;
    window.location.assign(link.href);
  }

  function measure() {
    var box = root.getBoundingClientRect();
    var w = box.width || window.innerWidth;
    var h = box.height || window.innerHeight;
    radius = Math.min(w, h) * (w < 640 ? 0.3 : 0.36);
  }

  function pointerList() {
    return Object.keys(pointers).map(function (id) {
      return pointers[id];
    });
  }

  function project() {
    var cosX = Math.cos(rotX);
    var sinX = Math.sin(rotX);
    var cosY = Math.cos(rotY);
    var sinY = Math.sin(rotY);
    var i;
    var p;
    var x;
    var y;
    var z;
    var depth;
    var size;

    for (i = 0; i < points.length; i += 1) {
      p = points[i];
      y = p.y * cosX - p.z * sinX;
      z = p.y * sinX + p.z * cosX;
      x = p.x * cosY + z * sinY;
      z = -p.x * sinY + z * cosY;
      depth = (z + 1) / 2;
      size = 0.5 + depth * 0.72;
      p.el.style.transform =
        "translate(-50%, -50%) translate(" +
        (x * radius * scale + panX) +
        "px, " +
        (y * radius * scale + panY) +
        "px) scale(" +
        size +
        ")";
      p.el.style.zIndex = String(Math.round(depth * 200));
      p.el.style.opacity = String(0.06 + Math.pow(depth, 1.6) * 0.94);
      p.el.style.pointerEvents = z > 0.02 ? "auto" : "none";
    }
  }

  function tick() {
    if (!dragging && !reduceMotion) rotY += 0.0022;
    project();
    frame = window.requestAnimationFrame(tick);
  }

  function distance(a, b) {
    var dx = a.x - b.x;
    var dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function midpoint(a, b) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  function onPointerDown(event) {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    pointers[event.pointerId] = {
      x: event.clientX,
      y: event.clientY,
      target: event.target
    };
    var list = pointerList();
    if (list.length === 1) {
      dragging = true;
      dragged = false;
      lastX = event.clientX;
      lastY = event.clientY;
    } else if (list.length === 2) {
      dragging = true;
      pinchStart = distance(list[0], list[1]);
      pinchScale = scale;
      var mid = midpoint(list[0], list[1]);
      midStartX = mid.x;
      midStartY = mid.y;
      panStartX = panX;
      panStartY = panY;
    }
  }

  function onPointerMove(event) {
    if (!pointers[event.pointerId]) return;
    pointers[event.pointerId].x = event.clientX;
    pointers[event.pointerId].y = event.clientY;
    var list = pointerList();
    if (list.length === 2) {
      var mid = midpoint(list[0], list[1]);
      var dist = distance(list[0], list[1]);
      if (pinchStart) {
        scale = Math.min(2.3, Math.max(0.55, pinchScale * (dist / pinchStart)));
      }
      panX = panStartX + (mid.x - midStartX);
      panY = panStartY + (mid.y - midStartY);
      dragged = true;
      return;
    }
    if (!dragging || list.length !== 1) return;
    var dx = event.clientX - lastX;
    var dy = event.clientY - lastY;
    if (!dragged && Math.abs(dx) + Math.abs(dy) > DRAG_THRESHOLD) {
      dragged = true;
      if (root.setPointerCapture) {
        try { root.setPointerCapture(event.pointerId); } catch (err) {}
      }
    }
    if (!dragged) return;
    rotY += dx * 0.007;
    rotX += dy * 0.007;
    rotX = Math.max(-1.2, Math.min(1.2, rotX));
    lastX = event.clientX;
    lastY = event.clientY;
  }

  function onPointerUp(event) {
    var info = pointers[event.pointerId];
    delete pointers[event.pointerId];
    if (pointerList().length) return;
    dragging = false;
    if (root.hasPointerCapture && root.hasPointerCapture(event.pointerId)) {
      try { root.releasePointerCapture(event.pointerId); } catch (err) {}
    }
    if (dragged || isModified(event)) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    var link = linkFrom(info && info.target);
    if (!link) {
      link = linkFrom(document.elementFromPoint(event.clientX, event.clientY));
    }
    if (link) openTag(link);
  }

  function onClick(event) {
    var link = linkFrom(event.target);
    if (dragged) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (link && !isModified(event) && event.button === 0) {
      event.preventDefault();
      event.stopPropagation();
      openTag(link);
    }
  }

  function onDragStart(event) {
    event.preventDefault();
  }

  function onWheel(event) {
    event.preventDefault();
    var next = scale * Math.exp(-event.deltaY * 0.0015);
    scale = Math.min(2.3, Math.max(0.55, next));
  }

  function onKey(event) {
    var step = 18;
    if (event.key === "ArrowUp") panY += step;
    else if (event.key === "ArrowDown") panY -= step;
    else if (event.key === "ArrowLeft") panX += step;
    else if (event.key === "ArrowRight") panX -= step;
    else if (event.key === "+" || event.key === "=") scale = Math.min(2.3, scale * 1.08);
    else if (event.key === "-" || event.key === "_") scale = Math.max(0.55, scale / 1.08);
    else return;
    event.preventDefault();
  }

  root.addEventListener("pointerdown", onPointerDown);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  window.addEventListener("pointercancel", function (event) {
    delete pointers[event.pointerId];
    if (!pointerList().length) dragging = false;
  });
  stage.addEventListener("click", onClick, true);
  stage.addEventListener("dragstart", onDragStart);
  root.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("keydown", onKey);
  window.addEventListener("resize", function () {
    measure();
    project();
  });

  measure();
  if (reduceMotion) {
    root.classList.add("is-static");
    project();
    return;
  }
  tick();
})();
