/* Phần dùng chung cho sinh viên và Giảng viên: thẻ lớp, danh sách tuần, banner tiến độ. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    busy = NEU.busy,
    colorOf = NEU.colorOf,
    d = NEU.d,
    esc = NEU.esc,
    fail = NEU.fail,
    ic = NEU.ic,
    topStyle = NEU.topStyle;

  // ------------------------------------------------------------------ SINH VIÊN
  var WEEK_LABEL = { done: "Đã học", current: "Đang học", upcoming: "Chưa học" };

  function progress(tl) {
    var n = tl.weeks_done + (tl.current_week ? 1 : 0),
      tot = tl.week_count || 15;
    return (
      '<div class="wk-progress" title="' +
      n +
      "/" +
      tot +
      " " +
      (tl.unit_label || "Tuần").toLowerCase() +
      '"><span style="width:' +
      Math.round((n * 100) / tot) +
      '%"></span></div>'
    );
  }

  function shortName(n) {
    var w = String(n || "")
      .trim()
      .split(/\s+/);
    return w.length >= 4 ? w.slice(-2).join(" ") : w.join(" ");
  }

  async function pickClass(list) {
    // ưu tiên lớp đang trong tuần học, rồi đến lớp nhiều câu hỏi nhất
    var id = API.param("class");
    if (id) return +id;
    var sorted = list.slice().sort(function (a, b) {
      return (
        (b.current_week ? 1 : 0) - (a.current_week ? 1 : 0) ||
        (b.question_count || 0) - (a.question_count || 0)
      );
    });
    return sorted.length ? sorted[0].id : null;
  }

  function fileIcon(t) {
    var k = String(t || "").toLowerCase(),
      c = /pdf/.test(k)
        ? "pdf"
        : /doc/.test(k)
          ? "doc"
          : /ppt/.test(k)
            ? "ppt"
            : /xls|csv/.test(k)
              ? "xls"
              : /\.(png|jpe?g|gif|webp)$/.test(k)
                ? "img"
                : "txt";
    return (
      '<span class="fi ' +
      c +
      '">' +
      { pdf: "PDF", doc: "DOC", ppt: "PPT", xls: "XLS", img: "IMG", txt: "TXT" }[c] +
      "</span>"
    );
  }

  var PEN =
    '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/>' +
    '<path d="m13.5 6.5 4 4"/></svg>';

  function weekSection(w, role, docs, mine, ended) {
    // một tuần = một thẻ: số tuần · tên chương · trạng thái · câu hỏi (bấm để xem) · nút hành động; tài liệu ngay bên dưới
    var u = w.unit_label || "Tuần",
      q,
      act,
      list = docs || [];
    var emptyWeek = !w.title && !list.length;
    var base =
      (role === "lecturer" ? "lecturer-week.html?week=" : "student-week.html?week=") + w.id;
    if (role === "lecturer") {
      var waiting = (w.waiting_count || 0) + (w.review_count || 0);
      var qh = base + "&filter=waiting";
      if (waiting) {
        q = '<span class="wk-q warn">' + ic("chat") + waiting + " câu hỏi chờ trả lời</span>";
        act = '<a class="btn primary sm wk-act" href="' + qh + '">Trả lời câu hỏi</a>';
      } else if (w.status === "upcoming") {
        q = '<span class="wk-q">' + ic("chat") + "—</span>";
        act = '<a class="btn sm wk-act" href="' + base + '&tab=docs">Soạn nội dung</a>';
      } else if (w.question_count) {
        q = '<span class="wk-q ok">' + ic("check") + "Đã trả lời hết</span>";
        act = '<a class="btn sm wk-act" href="' + base + '&filter=answered">Xem câu hỏi</a>';
      } else {
        q = '<span class="wk-q">' + ic("chat") + "Chưa có câu hỏi</span>";
        act = emptyWeek
          ? '<a class="btn sm wk-act" href="' + base + '&tab=docs">Soạn nội dung</a>'
          : '<a class="btn sm wk-act" href="' + base + '">Xem tuần</a>';
      }
    } else {
      var m = mine || [],
        wait = m.filter(function (x) {
          return x.status !== "answered";
        }).length;
      var mh = base + "&tab=mine" + (wait ? "&focus=waiting" : "");
      q =
        w.status === "upcoming"
          ? '<span class="wk-q">' + ic("lock") + "Chưa mở hỏi</span>"
          : m.length
            ? '<a class="wk-q' +
              (wait ? " warn" : " ok") +
              '" href="' +
              mh +
              '" title="Xem câu hỏi của tôi">' +
              ic("chat") +
              m.length +
              " câu" +
              (wait ? " · " + wait + " câu chờ trả lời" : " · đã trả lời") +
              "</a>"
            : '<span class="wk-q">' + ic("chat") + "Chưa hỏi</span>";
      act = ended
        ? '<a class="btn sm wk-act" href="' + base + '&tab=mine">Xem câu hỏi</a>'
        : w.status === "upcoming"
          ? '<span class="btn sm wk-act" aria-disabled="true">Chưa mở hỏi</span>'
          : '<a class="btn ' +
            (w.status === "current" ? "primary " : "") +
            'sm wk-act" href="' +
            base +
            '">Đặt câu hỏi</a>';
    }
    var title = w.title
      ? esc(w.title)
      : "<i>" +
        (role === "lecturer" ? "Chưa đặt tiêu đề" : "Giảng viên chưa cập nhật nội dung") +
        "</i>";
    var pen =
      role === "lecturer"
        ? '<span class="wk-pen" role="button" tabindex="0" title="Sửa tiêu đề" aria-label="Sửa tiêu đề ' +
          esc(u.toLowerCase() + " " + w.number) +
          '" data-wk-title="' +
          w.id +
          '" data-title="' +
          esc(w.title || "") +
          '">' +
          PEN +
          "</span>"
        : "";
    var LIMIT = 4;
    var docsHTML = list.length
      ? '<div class="wk-docs">' +
        list
          .map(function (d, i) {
            return (
              '<button class="wk-doc"' +
              (i >= LIMIT ? " hidden data-more" : "") +
              ' data-open="/api/materials/' +
              d.id +
              '/download" data-name="' +
              esc(d.filename) +
              '" title="' +
              esc(d.filename) +
              '">' +
              fileIcon(d.file_type || d.filename) +
              "<span>" +
              esc(d.filename.replace(/\.[^.]+$/, "")) +
              "</span></button>"
            );
          })
          .join("") +
        (list.length > LIMIT
          ? '<button class="wk-more" data-wk-more>Xem thêm ' +
            (list.length - LIMIT) +
            " tài liệu</button>"
          : "") +
        "</div>"
      : "";
    return (
      '<div class="wk-card ' +
      w.status +
      '" data-st="' +
      w.status +
      '">' +
      '<div class="wk-row"><span class="wk-no"><small>' +
      esc(u) +
      "</small><b>" +
      w.number +
      "</b></span>" +
      '<span class="wk-tt"><b><span class="wk-tl">' +
      title +
      "</span>" +
      pen +
      "</b></span>" +
      '<span class="wk-st ' +
      w.status +
      '">' +
      WEEK_LABEL[w.status] +
      "</span>" +
      q +
      act +
      "</div>" +
      docsHTML +
      "</div>"
    );
  }

  function weekList(weeks, role, docs, mine, c, tl) {
    var byWeek = {},
      mineBy = {};
    (docs || [])
      .slice()
      .sort(function (a, b) {
        return a.id - b.id;
      })
      .forEach(function (m) {
        (byWeek[m.week_id] = byWeek[m.week_id] || []).push(m);
      }); // theo thứ tự tải lên
    (mine || []).forEach(function (q) {
      (mineBy[q.week_id] = mineBy[q.week_id] || []).push(q);
    });
    var u = (tl && tl.unit_label) || "Tuần";
    var head =
      '<div class="wk-head"><span class="wk-hico">' +
      ic("cal") +
      '</span><div class="grow"><b>Danh sách ' +
      u.toLowerCase() +
      " học</b><small>" +
      (c ? esc(c.semester) + " · " : "") +
      weeks.length +
      " " +
      u.toLowerCase() +
      "</small></div></div>";
    return (
      head +
      '<div class="wk-list">' +
      weeks
        .map(function (w) {
          return weekSection(w, role, byWeek[w.id], mineBy[w.id], tl && tl.phase === "ended");
        })
        .join("") +
      "</div>"
    );
  }

  // Giảng viên sửa tiêu đề ngay trên dòng tuần (✎) — Enter lưu, Esc hủy
  function wkTitleEdit(pen) {
    var tt = pen.closest(".wk-tt"),
      id = pen.dataset.wkTitle,
      old = pen.dataset.title || "";
    if (!tt || tt.classList.contains("editing")) return;
    tt.classList.add("editing");
    tt.dataset.html = tt.innerHTML;
    tt.innerHTML =
      '<span class="wk-edit"><input maxlength="160" placeholder="VD: Chương 1: Tổng quan về kiểm thử" value="' +
      esc(old) +
      '"><button type="button" class="btn primary sm" data-wk-save>Lưu</button>' +
      '<button type="button" class="btn sm" data-wk-cancel>Hủy</button></span>';
    var inp = $("input", tt);
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
    function cancel() {
      tt.classList.remove("editing");
      tt.innerHTML = tt.dataset.html;
    }
    async function save() {
      var v = inp.value.trim(),
        b = $("[data-wk-save]", tt);
      busy(b, true);
      try {
        await API.patch("/api/weeks/" + id, { title: v });
        toast(v ? "Đã lưu tiêu đề" : "Đã xóa tiêu đề");
        reload();
      } catch (err) {
        fail(err);
        busy(b, false);
      }
    }
    $("[data-wk-save]", tt).onclick = save;
    $("[data-wk-cancel]", tt).onclick = cancel;
    inp.onkeydown = function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        save();
      }
      if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      }
    };
  }

  document.addEventListener(
    "click",
    function (e) {
      var pen = e.target.closest && e.target.closest("[data-wk-title]");
      if (pen) {
        e.preventDefault();
        e.stopPropagation();
        wkTitleEdit(pen);
        return;
      }
      if (e.target.closest && e.target.closest(".wk-tt.editing")) e.preventDefault(); // bấm trong ô sửa: không mở trang tuần
    },
    true,
  );

  document.addEventListener(
    "keydown",
    function (e) {
      var pen = e.target.closest && e.target.closest("[data-wk-title]");
      if (pen && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        wkTitleEdit(pen);
      }
      if (e.target.closest && e.target.closest(".wk-tt.editing") && e.key === " ")
        e.stopPropagation();
    },
    true,
  );

  document.addEventListener("click", function (e) {
    var mb = e.target.closest("[data-wk-more]");
    if (!mb) return;
    $$("[data-more]", mb.parentElement).forEach(function (x) {
      x.hidden = false;
    });
    mb.remove();
  });

  document.addEventListener("click", function (e) {
    var card = e.target.closest(".week-card[data-href]");
    if (card && !e.target.closest("button, a")) location.href = card.dataset.href;
  });

  document.addEventListener("keydown", function (e) {
    var card = e.target.closest && e.target.closest(".week-card[data-href]");
    if (card && e.key === "Enter") location.href = card.dataset.href;
  });
  // lịch 15 tuần liền mạch, không có tuần nghỉ

  function daysUntil(v) {
    // số ngày từ hôm nay tới ngày v (không hiện ngày tháng, chỉ đếm ngược)
    if (!v) return null;
    var t = new Date();
    t.setHours(0, 0, 0, 0);
    var x = new Date(String(v).slice(0, 10) + "T00:00:00");
    return Math.round((x - t) / 86400000);
  }

  function startsIn(tl) {
    var n = daysUntil(tl.start_date);
    return n == null
      ? ""
      : n <= 0
        ? "bắt đầu từ hôm nay"
        : n === 1
          ? "bắt đầu từ ngày mai"
          : "bắt đầu học sau " + n + " ngày";
  }

  function timelineBanner(c, tl, role, studCount) {
    var cw = c.current_week,
      page = role === "lecturer" ? "lecturer-week.html" : "student-week.html";
    var n = tl.weeks_done + (tl.current_week ? 1 : 0),
      u = (tl.unit_label || "Tuần").toLowerCase();
    if (role === "lecturer" && (tl.phase === "not_started" || !studCount)) {
      // lớp mới: việc đầu tiên là gửi mã tham gia cho sinh viên
      var h =
        tl.phase === "not_started"
          ? "Lớp mới · " + startsIn(tl)
          : esc(tl.label) + (cw && cw.title ? " · " + esc(cw.title) : "");
      return (
        '<div class="timeline-banner tb-new"><div class="tb-body"><h3>' +
        h +
        '</h3><div class="tiny muted">' +
        (studCount
          ? "Đã có " + studCount + " sinh viên tham gia lớp."
          : "Chưa có sinh viên nào. Gửi mã tham gia cho sinh viên để các em vào lớp.") +
        "</div></div>" +
        '<span class="tb-code">' +
        esc(c.join_code) +
        '</span><button class="btn primary" data-copy="' +
        esc(c.join_code) +
        '">' +
        ic("copy") +
        "Sao chép mã</button>" +
        (cw
          ? '<a class="btn" href="' +
            page +
            "?week=" +
            cw.id +
            '">Vào tuần ' +
            cw.number +
            " " +
            ic("arrow") +
            "</a>"
          : "") +
        "</div>"
      );
    }
    if (tl.phase === "not_started") {
      var si = startsIn(tl);
      return (
        '<div class="timeline-banner"><div class="tb-body"><h3>' +
        (si ? "Lớp sẽ " + si.replace("bắt đầu học sau", "bắt đầu sau") : "Lớp chưa bắt đầu") +
        '</h3><div class="tiny muted">' +
        (role === "lecturer"
          ? "Đặt tiêu đề và tải tài liệu cho các " + u + " bằng nút ✎ hoặc mở từng " + u + "."
          : u.charAt(0).toUpperCase() +
            u.slice(1) +
            " 1 mở đặt câu hỏi khi lớp bắt đầu. Giảng viên sẽ cập nhật nội dung từng " +
            u +
            ".") +
        "</div></div></div>"
      );
    }
    return (
      '<div class="timeline-banner"><div class="tb-body"><h3>' +
      esc(tl.label) +
      (cw && cw.title ? " · " + esc(cw.title) : "") +
      '</h3><div class="tiny muted">Đã học ' +
      n +
      "/" +
      (tl.week_count || 15) +
      " " +
      u +
      "</div>" +
      progress(tl) +
      "</div>" +
      (cw
        ? '<a class="btn primary" href="' +
          page +
          "?week=" +
          cw.id +
          '">Vào tuần ' +
          cw.number +
          " " +
          ic("arrow") +
          "</a>"
        : "") +
      "</div>"
    );
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-open]");
    if (!b) return;
    e.preventDefault();
    API.openFile(b.dataset.open, b.dataset.name).catch(fail);
  });

  function reload(silent) {
    if (NEU.state.reloadFn) NEU.state.reloadFn().catch(silent ? function () {} : fail);
  }

  function subjIcon(t) {
    t = (t || "").toLowerCase();
    var p = /kiểm thử|test/.test(t)
      ? '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>'
      : /dự án|quản lý|quản trị/.test(t) && !/dữ liệu/.test(t)
        ? '<path d="M4 20V11M10 20V5M16 20v-8M22 20H2"/>'
        : /dữ liệu|csdl/.test(t)
          ? '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'
          : /lập trình|ứng dụng|python|web/.test(t)
            ? '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 4l-4 16"/>'
            : '<path d="M4 5a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-2z"/><path d="M8 7h6"/>';
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' + p + "</svg>";
  }

  function hcard(c, role, n) {
    var tl = c.timeline,
      col = colorOf(c.id);
    n = n || 0;
    var left =
      (role === "lecturer"
        ? "<span>" + ic("users") + c.student_count + " sinh viên</span>"
        : "<span>" +
          ic("users") +
          "Giảng viên " +
          esc(shortName(c.lecturer_name || "")) +
          "</span>") +
      "<span>" +
      ic("cal") +
      (tl.current_week
        ? (tl.unit_label || "Tuần") + " " + tl.current_week + "/" + tl.week_count
        : esc(tl.label)) +
      "</span>";
    return (
      '<a class="hcard" href="' +
      (role === "lecturer" ? "lecturer-class.html" : "student-class.html") +
      "?class=" +
      c.id +
      '" data-tags="all' +
      (n ? " live" : "") +
      '" data-search="' +
      esc(c.code + " " + c.subject + " " + c.semester) +
      '">' +
      '<div class="hcard-top" style="' +
      topStyle(c.id) +
      '"><b>' +
      esc(c.code) +
      "</b><span>" +
      esc(c.subject) +
      "</span>" +
      (typeof NEU.state.SHOW_SEM !== "undefined" && NEU.state.SHOW_SEM
        ? '<i class="hc-sem">' + esc(c.semester) + "</i>"
        : "") +
      subjIcon(c.subject) +
      "</div>" +
      '<div class="hcard-body"><div>' +
      left +
      '</div><div><span class="wait" title="' +
      (role === "lecturer"
        ? "Câu hỏi của sinh viên đang chờ trả lời"
        : "Câu hỏi của bạn đang chờ Giảng viên trả lời") +
      '"><span>chờ trả lời</span><em class="' +
      (n ? "" : "zero") +
      '">' +
      n +
      "</em></span></div></div></a>"
    );
  }

  function semFilterHTML(id, sems, withStatus, allFirst) {
    // allFirst: mặc định "Tất cả học kỳ" (trang sinh viên)
    return (
      '<div class="cls-filter"><label class="field-out"><span>Học kỳ</span><select id="' +
      id +
      '"><option value="all">Tất cả học kỳ</option>' +
      sems
        .map(function (x) {
          return (
            '<option value="' +
            x.id +
            '"' +
            (x.is_default && !allFirst ? " selected" : "") +
            ">" +
            esc(x.label) +
            " (" +
            esc(x.year) +
            ")</option>"
          );
        })
        .join("") +
      "</select></label>" +
      "</div>"
    );
  }
  NEU.WEEK_LABEL = WEEK_LABEL;
  NEU.fileIcon = fileIcon;
  NEU.hcard = hcard;
  NEU.pickClass = pickClass;
  NEU.reload = reload;
  NEU.semFilterHTML = semFilterHTML;
  NEU.shortName = shortName;
  NEU.subjIcon = subjIcon;
  NEU.timelineBanner = timelineBanner;
  NEU.weekList = weekList;
})((window.NEU = window.NEU || {}));
