/* NEU Feedback — tương tác dùng chung cho mọi trang */
(function () {
  "use strict";
  var $ = function (s, r) {
    return (r || document).querySelector(s);
  };
  var $$ = function (s, r) {
    return Array.prototype.slice.call((r || document).querySelectorAll(s));
  };

  /* ---------- Thông báo nhỏ (toast): góc trên bên phải, mỗi lúc một thông báo ---------- */
  var toastTimer,
    toastLeft = 0,
    toastStart = 0;
  function toastBox() {
    var t = document.getElementById("toastV2");
    if (!t) {
      t = document.createElement("div");
      t.id = "toastV2";
      t.setAttribute("role", "status");
      t.setAttribute("aria-live", "polite");
      t.innerHTML =
        '<span class="t-ico"></span><span class="t-msg"></span><button class="t-x" type="button" aria-label="Đóng thông báo">×</button>';
      document.body.appendChild(t);
      t.querySelector(".t-x").addEventListener("click", function () {
        clearTimeout(toastTimer);
        t.classList.remove("show");
      });
      t.addEventListener("mouseenter", function () {
        clearTimeout(toastTimer);
        toastLeft -= Date.now() - toastStart;
      }); // rê chuột: tạm dừng
      t.addEventListener("mouseleave", function () {
        toastStart = Date.now();
        toastTimer = setTimeout(
          function () {
            t.classList.remove("show");
          },
          Math.max(toastLeft, 1200),
        );
      });
    }
    return t;
  }
  /** toast('Đã lưu') — thành công · toast('Có lỗi…', 'error') — lỗi (hiện lâu hơn) */
  window.toast = function (msg, type) {
    if (!msg) return;
    type = type === "error" ? "error" : "success";
    var t = toastBox();
    t.className = type;
    t.querySelector(".t-ico").textContent = type === "error" ? "!" : "✓";
    t.querySelector(".t-msg").textContent = msg;
    t.setAttribute("role", type === "error" ? "alert" : "status");
    void t.offsetWidth;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastLeft = type === "error" ? 5000 : 3000;
    toastStart = Date.now();
    toastTimer = setTimeout(function () {
      t.classList.remove("show");
    }, toastLeft);
  };
  /** Thông báo hiện ở trang kế tiếp (dùng khi thao tác xong thì chuyển trang) */
  window.flash = function (msg, type) {
    try {
      sessionStorage.setItem("neu_toast", JSON.stringify({ msg: msg, type: type || "success" }));
    } catch (e) {}
  };
  try {
    var fl = JSON.parse(sessionStorage.getItem("neu_toast") || "null");
    if (fl) {
      sessionStorage.removeItem("neu_toast");
      setTimeout(function () {
        toast(fl.msg, fl.type);
      }, 60);
    }
  } catch (e) {}
  $$("[data-toast]").forEach(function (x) {
    x.addEventListener("click", function () {
      toast(x.dataset.toast);
    });
  });

  /* ---------- Modal ---------- */
  window.openModal = function (id) {
    var m = document.getElementById(id);
    if (!m) return;
    m.classList.add("open");
    var f = $("input,select,textarea", m);
    if (f)
      setTimeout(function () {
        f.focus();
      }, 60);
  };
  window.closeModal = function (id) {
    var m = document.getElementById(id);
    if (m) m.classList.remove("open");
  };
  $$(".modal").forEach(function (m) {
    m.addEventListener("click", function (e) {
      if (e.target === m) m.classList.remove("open");
    });
  });

  window.createClass = function () {
    closeModal("classModal");
    toast("Đã tạo lớp học mới");
  };
  window.renameMaterial = function () {
    var v = ($("#renameInput") || {}).value,
      n = $("#materialName");
    if (v && n) n.textContent = v;
    closeModal("renameModal");
    toast("Đã đổi tên tài liệu");
  };

  /* ---------- Tabs ---------- */
  window.tabs = function (btn, group) {
    $$('[data-tabs="' + group + '"] button').forEach(function (b) {
      b.classList.toggle("active", b === btn);
    });
    $$('[data-tabpage="' + group + '"]').forEach(function (p) {
      p.classList.toggle("active", p.id === btn.dataset.target);
    });
  };
  $$("[data-tabset]").forEach(function (set) {
    $$("button", set).forEach(function (b) {
      b.addEventListener("click", function () {
        $$("button", set).forEach(function (x) {
          x.classList.remove("active");
        });
        b.classList.add("active");
      });
    });
  });

  /* ---------- Tệp đính kèm ---------- */
  window.addFiles = function (input, targetId) {
    var box = document.getElementById(targetId);
    if (!box) return;
    Array.prototype.forEach.call(input.files, function (file) {
      var el = document.createElement("span");
      el.className = "file-pill";
      var name = document.createElement("span");
      name.textContent = file.name;
      var rm = document.createElement("button");
      rm.type = "button";
      rm.setAttribute("aria-label", "Gỡ tệp");
      rm.textContent = "×";
      rm.onclick = function () {
        el.remove();
      };
      el.appendChild(name);
      el.appendChild(rm);
      box.appendChild(el);
    });
    input.value = "";
  };

  /* ---------- Thời lượng phiên ---------- */
  function updateDuration() {
    var s = $("#sessionStart"),
      e = $("#sessionEnd"),
      o = $("#durationPreview");
    if (!s || !e || !o || !s.value || !e.value) return;
    var a = s.value.split(":").map(Number),
      b = e.value.split(":").map(Number);
    var m = b[0] * 60 + b[1] - (a[0] * 60 + a[1]);
    if (m < 0) m += 1440;
    o.textContent = "Thời lượng phiên: " + Math.floor(m / 60) + " giờ " + (m % 60) + " phút";
  }
  $$("#sessionStart,#sessionEnd").forEach(function (x) {
    x.addEventListener("input", updateDuration);
  });

  /* ---------- Chọn mục trong danh sách ---------- */
  function selectable(sel, cls) {
    $$(sel).forEach(function (q) {
      q.addEventListener("click", function () {
        $$(sel).forEach(function (x) {
          x.classList.remove(cls);
        });
        q.classList.add(cls);
      });
    });
  }
  selectable(".queue .question", "selected");
  selectable(".moditem", "active");
  selectable(".chat-side p:not(.chat-tip)", "chat-current");

  /* ---------- NEU AI (nút nổi + trang chat) ---------- */
  window.toggleAI = function () {
    var c = $("#aiChat");
    if (!c) return;
    c.classList.toggle("open");
    if (c.classList.contains("open")) {
      var i = $("#aiInput");
      if (i)
        setTimeout(function () {
          i.focus();
        }, 80);
    }
  };
  /* ---------- Phím tắt ---------- */
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      $$(".modal.open").forEach(function (m) {
        m.classList.remove("open");
      });
      var c = $("#aiChat.open");
      if (c) c.classList.remove("open");
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      var s = $(".topbar .search input");
      if (s) {
        e.preventDefault();
        s.focus();
      }
    }
  });

  /* ---------- Hiệu ứng gợn khi bấm nút ---------- */
  document.addEventListener("pointerdown", function (e) {
    var b = e.target.closest && e.target.closest(".btn");
    if (!b) return;
    var r = b.getBoundingClientRect(),
      d = Math.max(r.width, r.height),
      s = document.createElement("span");
    s.className = "ripple";
    s.style.width = s.style.height = d + "px";
    s.style.left = e.clientX - r.left - d / 2 + "px";
    s.style.top = e.clientY - r.top - d / 2 + "px";
    b.appendChild(s);
    setTimeout(function () {
      s.remove();
    }, 650);
  });

  /* ---------- Xuất hiện lần lượt khi tải trang ---------- */
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce) {
    var targets = $$(
      ".page > *, .content > *, .grid > *, .grid2 > *, .grid3 > *, .grid4 > *, .statcards > *, .list > *, .login-card, .public-section > *",
    );
    targets.forEach(function (el, n) {
      if (el.closest(".modal") || el.closest(".tab")) return;
      el.classList.add("reveal");
      el.style.setProperty("--i", Math.min(n, 14));
    });

    /* Đếm số KPI */
    if (!document.body.hasAttribute("data-api"))
      $$(".kpi").forEach(function (k) {
        var raw = k.textContent.trim(),
          m = raw.match(/^([\d.,]+)(.*)$/);
        if (!m) return;
        var target = parseFloat(m[1].replace(/,/g, ""));
        if (!isFinite(target) || target === 0) return;
        var hasComma = m[1].indexOf(",") > -1,
          dec = (m[1].split(".")[1] || "").length,
          rest = m[2],
          t0 = null,
          dur = 900;
        if (m[1].indexOf(".") > -1 && m[1].split(".")[1].length === 3) return; // định dạng 1.214 kiểu VN: giữ nguyên
        function fmt(v) {
          var s = v.toFixed(dec);
          if (hasComma) s = Number(s).toLocaleString("en-US");
          return s + rest;
        }
        function step(ts) {
          if (!t0) t0 = ts;
          var p = Math.min(1, (ts - t0) / dur);
          p = 1 - Math.pow(1 - p, 3);
          k.textContent = fmt(target * p);
          if (p < 1) requestAnimationFrame(step);
          else k.textContent = raw;
        }
        k.textContent = fmt(0);
        setTimeout(function () {
          requestAnimationFrame(step);
        }, 250);
      });
  }

  /* ---------- Hồ sơ: đổi giao diện theo vai trò (?role=) ---------- */
  var role = new URLSearchParams(location.search).get("role");
  if (
    role &&
    /profile\.html$/.test(location.pathname) &&
    window.NF_SIDEBARS &&
    window.NF_SIDEBARS[role]
  ) {
    document.body.classList.remove("student", "lecturer", "admin");
    document.body.classList.add(role);
    var aside = $(".sidebar");
    if (aside) aside.outerHTML = window.NF_SIDEBARS[role];
    if (role !== "student")
      $$(".ai-fab, .ai-chat").forEach(function (x) {
        x.remove();
      });
    var u = window.NF_USERS[role];
    $$(".user .avatar, .panel .avatar").forEach(function (a) {
      a.textContent = u.ini;
    });
    $$(".user .name b").forEach(function (a) {
      a.textContent = u.name;
    });
    $$(".user .name small").forEach(function (a) {
      a.textContent = u.role;
    });
    var h = $(".content .panel h2");
    if (h) h.textContent = u.name;
    var sub = $(".content .panel h2 + p");
    if (sub) sub.textContent = u.role + " • NEU";
    var nm = $(".content .panel .field input");
    if (nm) nm.value = u.name;
  }
})();

/* ================= v3.4 — tương tác bổ sung ================= */
(function () {
  "use strict";
  var $ = function (s, r) {
    return (r || document).querySelector(s);
  };
  var $$ = function (s, r) {
    return Array.prototype.slice.call((r || document).querySelectorAll(s));
  };
  var body = document.body;
  var role = body.classList.contains("admin")
    ? "admin"
    : body.classList.contains("lecturer")
      ? "lecturer"
      : body.classList.contains("student")
        ? "student"
        : "";
  var lastTrigger = null;

  /* ---- Mở modal kèm dữ liệu: data-modal, data-fill, data-title ---- */
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-modal]");
    if (!t) return;
    e.preventDefault();
    lastTrigger = t;
    var m = document.getElementById(t.dataset.modal);
    if (!m) return;
    if (t.dataset.title) {
      var h = $(".modal-title", m);
      if (h) h.textContent = t.dataset.title;
    }
    if (t.dataset.fill) {
      try {
        var d = JSON.parse(t.dataset.fill);
        Object.keys(d).forEach(function (k) {
          $$('[name="' + k + '"]', m).forEach(function (f) {
            f.value = d[k];
          });
          $$('[data-bind="' + k + '"]', m).forEach(function (f) {
            f.textContent = d[k];
          });
        });
      } catch (err) {}
    }
    openModal(t.dataset.modal);
  });

  /* ---- Nút lưu trong modal: data-save + data-done ---- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-save]");
    if (!b) return;
    var m = document.getElementById(b.dataset.save);
    var req = m
      ? $$("input[name]:not([readonly]), textarea[name]", m).filter(function (f) {
          return f.type !== "file" && !f.value.trim();
        })
      : [];
    if (req.length && b.dataset.save !== "docModal") {
      req[0].focus();
      toast("Vui lòng điền đầy đủ thông tin");
      return;
    }
    if (b.dataset.save === "renameModal" && lastTrigger) {
      var row = lastTrigger.closest("tr"),
        v = $("[name=docName]", m).value;
      if (row && $(".doc-name", row)) $(".doc-name", row).textContent = v;
      if (row) row.dataset.search = v;
    }
    if (b.dataset.save === "accountModal" && lastTrigger && lastTrigger.closest("tr")) {
      var r = lastTrigger.closest("tr");
      var nb = $("b", r),
        em = $(".meta", r);
      if (nb) nb.textContent = $("[name=fullName]", m).value;
      if (em) em.textContent = $("[name=email]", m).value;
    }
    closeModal(b.dataset.save);
    if (b.dataset.done) toast(b.dataset.done);
  });

  /* ---- Hộp xác nhận chung: data-confirm ---- */
  var cm = document.createElement("div");
  cm.className = "modal";
  cm.id = "confirmModal";
  cm.setAttribute("role", "alertdialog");
  cm.setAttribute("aria-modal", "true");
  cm.innerHTML =
    '<div class="modal-card confirm-card"><div class="confirm-ico"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg></div><h2 class="modal-title"></h2><p class="muted confirm-msg"></p><div class="modal-actions"><button class="btn" data-cancel>Hủy</button><button class="btn danger" data-ok>Xác nhận</button></div></div>';
  body.appendChild(cm);
  cm.addEventListener("click", function (e) {
    if (e.target === cm || e.target.closest("[data-cancel]")) cm.classList.remove("open");
  });
  var pending = null;
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-confirm]");
    if (!t) return;
    e.preventDefault();
    pending = t;
    $(".modal-title", cm).textContent = t.dataset.confirm;
    $(".confirm-msg", cm).textContent = t.dataset.message || "";
    $("[data-ok]", cm).textContent = t.dataset.ok || "Xác nhận";
    cm.classList.add("open");
    setTimeout(function () {
      $("[data-ok]", cm).focus();
    }, 50);
  });
  $("[data-ok]", cm).addEventListener("click", function () {
    cm.classList.remove("open");
    if (!pending) return;
    var t = pending;
    pending = null;
    $$(".modal.open").forEach(function (m) {
      m.classList.remove("open");
    });
    if (t.dataset.done) toast(t.dataset.done);
    if (t.dataset.remove) {
      var el = t.closest(t.dataset.remove);
      if (el) {
        el.classList.add("leaving");
        setTimeout(function () {
          el.remove();
        }, 300);
      }
    }
    if (t.dataset.href)
      setTimeout(function () {
        location.href = t.dataset.href;
      }, 500);
    if (t.hasAttribute("data-d")) markCurrent("flag");
  });

  /* ---- Sao chép ---- */
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-copy]");
    if (!t) return;
    if (navigator.clipboard) navigator.clipboard.writeText(t.dataset.copy).catch(function () {});
    toast("Đã sao chép mã " + t.dataset.copy);
  });

  /* ---- Bộ lọc dạng nút: data-chip-filter="#target" data-attr="status" ---- */
  $$("[data-chip-filter]").forEach(function (set) {
    var target = $(set.dataset.chipFilter),
      attr = set.dataset.attr || "tags";
    function run(val) {
      var items = target ? Array.prototype.slice.call(target.children) : [],
        shown = 0;
      items.forEach(function (it) {
        var v = it.dataset[attr] || "";
        var ok = val === "all" || (attr === "tags" ? v.split(" ").indexOf(val) > -1 : v === val);
        it.hidden = !ok;
        if (ok) shown++;
      });
      var empty =
        target && target.closest("section, .page")
          ? $(".empty-filter", target.closest(".page") || document)
          : null;
      if (empty) empty.hidden = shown > 0;
    }
    $$("[data-filter]", set).forEach(function (b) {
      b.addEventListener("click", function () {
        $$("[data-filter]", set).forEach(function (x) {
          x.classList.toggle("active", x === b);
        });
        run(b.dataset.filter);
      });
    });
    var act = $("[data-filter].active", set);
    if (act) run(act.dataset.filter);
  });

  /* ---- Bộ lọc form: .filters[data-filter-list] ---- */
  $$(".filters[data-filter-list]").forEach(function (f) {
    var sel = f.dataset.filterList;
    function items() {
      var t = $(sel);
      if (!t) return [];
      return t.tagName === "TBODY" ? $$("tr", t) : Array.prototype.slice.call(t.children);
    }
    function apply(silent) {
      var shown = 0;
      items().forEach(function (it) {
        var ok = true;
        $$("[data-key]", f).forEach(function (c) {
          var v = (c.value || "").trim().toLowerCase();
          if (!v) return;
          if (c.dataset.key === "q") {
            if ((it.dataset.search || it.textContent).toLowerCase().indexOf(v) < 0) ok = false;
          } else if (it.dataset[c.dataset.key] === "__total") {
            ok = ok && true;
          } else if ((it.dataset[c.dataset.key] || "").toLowerCase() !== v) ok = false;
        });
        it.hidden = !ok;
        if (ok && it.dataset.fac !== "__total") shown++;
      });
      var empty = $(".empty-filter");
      if (empty) empty.hidden = shown > 0;
    }
    var ap = $("[data-apply]", f),
      rs = $("[data-reset]", f);
    if (ap)
      ap.addEventListener("click", function () {
        apply(false);
      });
    if (rs)
      rs.addEventListener("click", function () {
        $$("input, select", f).forEach(function (c) {
          if (c.tagName === "SELECT") c.selectedIndex = 0;
          else c.value = "";
        });
        apply(true);
      });
    if (f.hasAttribute("data-live"))
      $$("[data-key]", f).forEach(function (c) {
        c.addEventListener(c.tagName === "SELECT" ? "change" : "input", function () {
          apply(true);
        });
      });
    $$("input[data-key]", f).forEach(function (c) {
      c.addEventListener("keydown", function (e) {
        if (e.key === "Enter") apply(false);
      });
    });
  });

  /* ---- Tìm nhanh trong danh sách: data-live-search="selector" ---- */
  $$("[data-live-search]").forEach(function (inp) {
    inp.addEventListener("input", function () {
      var v = inp.value.trim().toLowerCase();
      $$(inp.dataset.liveSearch).forEach(function (it) {
        it.hidden = v && (it.dataset.search || it.textContent).toLowerCase().indexOf(v) < 0;
      });
    });
  });

  /* ---- Tìm kiếm nhanh ở thanh trên ---- */
  var PAGES = {
    student: [
      ["Trang chủ", "student.html"],
      ["Lớp học của tôi", "student-classes.html"],
      ["Theo dõi phản hồi", "student-feedback.html"],
      ["NEU AI", "student-ai.html"],
      ["Hồ sơ cá nhân", "profile.html?role=student"],
    ],
    lecturer: [
      ["Trang chủ", "lecturer.html"],
      ["Lớp giảng dạy", "lecturer-classes.html"],
      ["Kho tài liệu", "lecturer-materials.html"],
      ["Thống kê giảng dạy", "lecturer-stats.html"],
      ["Hồ sơ cá nhân", "profile.html?role=lecturer"],
    ],
    admin: [
      ["Tổng quan", "admin.html"],
      ["Quản lý tài khoản", "admin-accounts.html"],
      ["Nội dung gắn cờ", "admin-reports.html"],
      ["Thống kê", "admin-stats.html"],
    ],
  };
  var si = $(".topbar .search input");
  var _nu = null;
  try {
    _nu = JSON.parse(localStorage.getItem("neu_user") || "null");
  } catch (e) {}
  var liveSearch = document.body.hasAttribute("data-api") && _nu && _nu.role !== "admin"; // SV & Giảng viên: tìm kiếm thật (live.js)
  if (si && PAGES[role] && !liveSearch) {
    var sp = document.createElement("div");
    sp.className = "search-panel";
    si.closest(".search").appendChild(sp);
    var norm = function (x) {
      return x
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/đ/g, "d");
    };
    var render = function () {
      var v = norm(si.value.trim());
      var list = PAGES[role].filter(function (p) {
        return !v || norm(p[0]).indexOf(v) > -1;
      });
      sp.innerHTML = list.length
        ? list
            .map(function (p) {
              return '<a href="' + p[1] + '">' + p[0] + "</a>";
            })
            .join("")
        : "<p>Không tìm thấy kết quả cho “" + si.value.replace(/</g, "&lt;") + "”</p>";
      sp.classList.add("open");
    };
    si.addEventListener("focus", render);
    si.addEventListener("input", render);
    si.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        var a = $("a", sp);
        if (a) location.href = a.getAttribute("href");
      }
      if (e.key === "Escape") {
        sp.classList.remove("open");
        si.blur();
      }
    });
    document.addEventListener("click", function (e) {
      if (!si.closest(".search").contains(e.target)) sp.classList.remove("open");
    });
  }

  /* ---- Hồ sơ theo vai trò ---- */
  var r = new URLSearchParams(location.search).get("role");
  if (r)
    $$("[data-role-panel]").forEach(function (p) {
      p.hidden = p.dataset.rolePanel !== r;
    });
})();

/* ================= v3.17 — thanh bên 3 trạng thái ================= */
(function () {
  "use strict";
  var aside = document.querySelector(".sidebar"),
    top = document.querySelector(".topbar");
  if (!aside || !top) return;
  var KEY = "neu_nav",
    body = document.body;
  function saved() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }
  function remember(v) {
    try {
      localStorage.setItem(KEY, v);
    } catch (e) {}
  }
  function auto() {
    var w = window.innerWidth;
    return w >= 1200 ? "full" : w >= 900 ? "rail" : "hidden";
  }
  function desk() {
    return window.innerWidth >= 900;
  }
  function fit(m) {
    // máy tính: chỉ có 2 trạng thái (đầy đủ / chỉ biểu tượng) để luôn còn biểu tượng bấm; điện thoại: ẩn, mở dạng lớp phủ
    if (!desk()) return "hidden";
    return m === "full" ? "full" : "rail";
  }
  function apply(mode) {
    mode = fit(mode);
    body.classList.remove("nav-full", "nav-rail", "nav-hidden", "nav-open");
    body.classList.add("nav-" + mode);
    btn.setAttribute("aria-expanded", mode === "full");
    btn.title = {
      full: "Thu gọn thanh bên",
      rail: "Mở rộng thanh bên",
      hidden: "Mở thanh bên",
    }[mode];
  }
  var mode = saved() || auto();
  var cur = document.querySelector(".nav a.active");
  var title = cur ? cur.textContent.trim() : "";
  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "nav-toggle";
  btn.setAttribute("aria-label", "Đóng / mở thanh bên");
  btn.innerHTML =
    '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>';
  var wrap = document.createElement("div");
  wrap.className = "top-title";
  wrap.appendChild(btn);
  if (title) {
    var s = document.createElement("span");
    s.textContent = title;
    wrap.appendChild(s);
  }
  top.insertBefore(wrap, top.firstChild);
  var back = document.createElement("div");
  back.className = "nav-backdrop";
  document.body.appendChild(back);
  aside.querySelectorAll(".nav a").forEach(function (a) {
    a.title = a.textContent.trim();
  });
  btn.addEventListener("click", function () {
    if (body.classList.contains("nav-hidden")) {
      body.classList.toggle("nav-open");
      return;
    }
    mode = body.classList.contains("nav-full") ? "rail" : "full";
    remember(mode);
    apply(mode);
  });
  btn.addEventListener("dblclick", function () {
    mode = "full";
    remember(mode);
    apply(mode);
  });
  back.addEventListener("click", function () {
    body.classList.remove("nav-open");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") body.classList.remove("nav-open");
  });
  window.addEventListener("resize", function () {
    apply(saved() || auto());
  });
  apply(mode);
})();
