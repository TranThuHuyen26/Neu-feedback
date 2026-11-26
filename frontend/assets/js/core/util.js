/* Hàm tiện ích dùng ở mọi trang: chọn phần tử ($), định dạng ngày giờ, hiện thông báo, icon, bảng màu. */
(function (NEU) {
  "use strict";
  NEU.pages = {};
  NEU.state = {
    user: null,
    reloadFn: null,
    SHOW_SEM: false,
    qmEditing: null,
    qmDraft: "",
    qmOpenId: null,
  };

  ("use strict");

  var $ = function (s, r) {
    return (r || document).querySelector(s);
  };

  var $$ = function (s, r) {
    return Array.prototype.slice.call((r || document).querySelectorAll(s));
  };

  var PAGE = location.pathname.split("/").pop() || "index.html";

  var ACTIONS = {};

  // ------------------------------------------------------------------ tiện ích
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function nl(s) {
    return esc(s).replace(/\n/g, "<br>");
  }

  function d(v) {
    return v ? new Date(v) : null;
  }

  function pad(n) {
    return ("0" + n).slice(-2);
  }

  function fDate(v) {
    var x = d(v);
    return x ? pad(x.getDate()) + "/" + pad(x.getMonth() + 1) + "/" + x.getFullYear() : "";
  }

  function fDM(v) {
    var x = d(v);
    return x ? pad(x.getDate()) + "/" + pad(x.getMonth() + 1) : "";
  }

  function fTime(v) {
    var x = d(v);
    return x ? pad(x.getHours()) + ":" + pad(x.getMinutes()) : "";
  }

  function ago(v) {
    var x = d(v);
    if (!x) return "";
    var s = (Date.now() - x.getTime()) / 1000;
    if (s < 60) return "vừa xong";
    if (s < 3600) return Math.floor(s / 60) + " phút trước";
    if (s < 86400) return Math.floor(s / 3600) + " giờ trước";
    if (s < 172800) return "Hôm qua";
    return fDate(v);
  }

  function dur(sec) {
    if (sec == null) return "—";
    var m = Math.floor(sec / 60),
      s = sec % 60;
    return m ? m + "m " + pad(s) + "s" : s + " giây";
  }

  function num(n) {
    return (n || 0).toLocaleString("en-US");
  }

  function pct(a, b) {
    return b ? Math.round((a * 100) / b) : 0;
  }

  function initials(name) {
    var p = String(name || "?")
      .trim()
      .split(/\s+/);
    return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : p[0].slice(0, 2)).toUpperCase();
  }

  function fail(e) {
    toast(e && e.message ? e.message : "Có lỗi xảy ra", "error");
  }

  // Thông báo nhỏ: góc trên bên phải, hiện ngay, mỗi lúc một cái; thành công 3 giây, lỗi 5 giây; rê chuột để dừng; có nút ×
  // Thông báo nhỏ dùng chung từ app.js (toast / flash); toastNext = hiện ở trang kế tiếp
  window.toastNext = function (msg, type) {
    if (window.flash) window.flash(msg, type);
  };

  function empty(msg) {
    return '<p class="empty-note">' + esc(msg) + "</p>";
  }

  function today() {
    var x = new Date();
    return (
      ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"][x.getDay()] +
      ", " +
      fDate(x)
    );
  }

  function set(id, html) {
    var el = document.getElementById(id);
    if (el) {
      el.innerHTML = html;
      if (typeof NEU.edInit === "function" && html.indexOf("ed-area") >= 0) NEU.edInit(el);
    }
    return el;
  }

  function txt(id, t) {
    var el = document.getElementById(id);
    if (el) el.textContent = t;
    return el;
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  var P = {
    chev: '<path d="m6 9 6 6 6-6"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    users:
      '<circle cx="9" cy="8" r="3.5"/>' +
      '<path d="M2 20a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M18 13.5a7 7 0 0 1 4 6.5"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    file: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    group: '<circle cx="8" cy="12" r="4"/><circle cx="16" cy="12" r="4"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    flag: '<path d="M5 21V4M5 4h12l-2 4 2 4H5"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    refresh: '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
    reply: '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 5 5v6"/>',
    grad: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>',
    monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    upload: '<path d="M12 20V9M7 14l5-5 5 5M5 4h14"/>',
    image:
      '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  };

  var SPARK =
    '<svg class="robot" viewBox="0 0 24 24" aria-hidden="true">' +
    '<rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V5"/><circle cx="12" cy="4" r="1.3"/>' +
    '<circle class="eye" cx="9" cy="13" r="1.4"/><circle class="eye" cx="15" cy="13" r="1.4"/>' +
    '<path d="M9.5 16.3h5"/><path d="M2.5 12.5v2.5M21.5 12.5v2.5"/></svg>';
  // biểu tượng NEU AI (chatbot) dùng thống nhất
  function ic(n) {
    return '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">' + P[n] + "</svg>";
  }

  var TONE_ONE = ["var(--accent-soft)", "var(--accent)"];
  // SV & GV: dải xanh NEU
  var TONE = document.body.classList.contains("admin") // Admin giữ nguyên màu cũ
    ? {
        blue: ["#ECF1FF", "#2F5BEA"],
        teal: ["#E2F4F2", "#0B7A75"],
        amber: ["#FEF4E2", "#9A4A07"],
        green: ["#E3F6EC", "#127245"],
        red: ["#FDECEA", "#B42318"],
        violet: ["#F3EDFD", "#6B2FC9"],
      }
    : {
        blue: TONE_ONE,
        teal: TONE_ONE,
        amber: ["#FEF4E2", "#9A4A07"],
        green: TONE_ONE,
        red: ["#FDECEA", "#B42318"],
        violet: TONE_ONE,
      };

  function kpi(value, label, icon, tone, sub) {
    var t = TONE[tone];
    return (
      '<div class="card stat"><span class="stat-ico" style="background:' +
      t[0] +
      ";color:" +
      t[1] +
      '">' +
      ic(icon) +
      '</span><div class="stat-body"><div class="stat-label">' +
      esc(label) +
      '</div><div class="kpi">' +
      esc(value) +
      "</div>" +
      (sub ? '<div class="stat-sub">' + esc(sub) + "</div>" : "") +
      "</div></div>"
    );
  }

  // Bảng màu lớp (pastel): [nền nhạt, màu đậm] — Xanh trời, Bạc hà, Oải hương, Đào nhạt, Xanh xám, Hồng phấn trầm.
  // Dùng thống nhất ở thẻ lớp (trang chủ, Lớp học của tôi, Lớp giảng dạy), biểu đồ thống kê và nhãn lớp ở Kho tài liệu.
  var PALETTE = [
    ["#E4F1FA", "#2F7FA8"],
    ["#E4F4EE", "#2E8B6E"],
    ["#ECEBFA", "#5B5BB5"],
    ["#FBEFE4", "#B7703A"],
    ["#EAF0F4", "#5B7A93"],
    ["#F7EAF0", "#A65478"],
  ];

  var COLORS = PALETTE.map(function (x) {
    return x[1];
  });

  function colorOf(id) {
    return COLORS[(id || 0) % COLORS.length];
  }

  function softOf(id) {
    return PALETTE[(id || 0) % PALETTE.length][0];
  }

  function topStyle(id) {
    return "background:" + softOf(id) + ";--cc:" + colorOf(id);
  }

  function qBadge(st, forStudent) {
    var m = {
      waiting: ["badge warn", "Chờ trả lời"],
      answered: ["badge", "Đã trả lời"],
      flagged: ["badge red", forStudent ? "Đang được xem xét" : "Đã gắn cờ"],
      hidden: ["pill", "Đã ẩn"],
    }[st] || ["pill", st];
    return '<span class="' + m[0] + '">' + m[1] + "</span>";
  }

  function bars(items) {
    // items: [{label, total, done, color?}] — phần đã phản hồi theo màu (lớp), phần còn lại màu cam
    var max = Math.max.apply(
      null,
      items
        .map(function (x) {
          return x.total;
        })
        .concat([1]),
    );
    return (
      items
        .map(function (x, i) {
          return (
            '<div class="sb"><div class="sb-col" style="height:' +
            ((x.total * 100) / max).toFixed(1) +
            "%;animation-delay:" +
            (0.1 + i * 0.06).toFixed(2) +
            's"><span class="sb-a" style="height:' +
            (x.total ? (x.done * 100) / x.total : 0).toFixed(1) +
            "%" +
            (x.color ? ";background:" + x.color : "") +
            '"></span><span class="sb-w"></span><em>' +
            x.total +
            "</em></div><small>" +
            esc(x.label) +
            "</small></div>"
          );
        })
        .join("") || '<p class="muted">Chưa có dữ liệu.</p>'
    );
  }

  function busy(btn, on) {
    if (!btn) return;
    if (on) {
      btn.dataset.label = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    } else {
      btn.disabled = false;
      if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
    }
  }

  // Hộp xác nhận riêng (trả về Promise)
  function confirmBox(title, msg, okLabel) {
    return new Promise(function (resolve) {
      var m = document.getElementById("apiConfirm");
      if (!m) {
        m = document.createElement("div");
        m.className = "modal";
        m.id = "apiConfirm";
        m.innerHTML =
          '<div class="modal-card confirm-card"><div class="confirm-ico">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4M12 17h.01"/>' +
          '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>' +
          '</div><h2 class="modal-title"></h2><p class="muted"></p><div class="modal-actions">' +
          '<button class="btn" data-x>Hủy</button><button class="btn danger" data-ok></button></div></div>';
        document.body.appendChild(m);
      }
      $("h2", m).textContent = title;
      $("p", m).textContent = msg;
      $("[data-ok]", m).textContent = okLabel || "Xác nhận";
      m.classList.add("open");
      function done(v) {
        m.classList.remove("open");
        $("[data-ok]", m).onclick = null;
        $("[data-x]", m).onclick = null;
        resolve(v);
      }
      $("[data-ok]", m).onclick = function () {
        done(true);
      };
      $("[data-x]", m).onclick = function () {
        done(false);
      };
    });
  }

  document.addEventListener("click", async function (e) {
    var b = e.target.closest("[data-submit]");
    if (!b || !ACTIONS[b.dataset.submit]) return;
    e.preventDefault();
    busy(b, true);
    try {
      await ACTIONS[b.dataset.submit](b);
    } catch (err) {
      fail(err);
    } finally {
      busy(b, false);
    }
  });
  NEU.$ = $;
  NEU.$$ = $$;
  NEU.ACTIONS = ACTIONS;
  NEU.P = P;
  NEU.PAGE = PAGE;
  NEU.SPARK = SPARK;
  NEU.TONE = TONE;
  NEU.ago = ago;
  NEU.bars = bars;
  NEU.busy = busy;
  NEU.colorOf = colorOf;
  NEU.confirmBox = confirmBox;
  NEU.d = d;
  NEU.dur = dur;
  NEU.empty = empty;
  NEU.esc = esc;
  NEU.fDM = fDM;
  NEU.fDate = fDate;
  NEU.fTime = fTime;
  NEU.fail = fail;
  NEU.ic = ic;
  NEU.initials = initials;
  NEU.kpi = kpi;
  NEU.nl = nl;
  NEU.num = num;
  NEU.pad = pad;
  NEU.pct = pct;
  NEU.set = set;
  NEU.today = today;
  NEU.topStyle = topStyle;
  NEU.txt = txt;
  NEU.val = val;
})((window.NEU = window.NEU || {}));
