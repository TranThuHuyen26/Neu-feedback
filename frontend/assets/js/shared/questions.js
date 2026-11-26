/* Danh sách câu hỏi, cửa sổ "Chi tiết câu hỏi", hiển thị nội dung Markdown. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    SPARK = NEU.SPARK,
    aiText = NEU.aiText,
    busy = NEU.busy,
    confirmBox = NEU.confirmBox,
    d = NEU.d,
    esc = NEU.esc,
    fDM = NEU.fDM,
    fDate = NEU.fDate,
    fTime = NEU.fTime,
    fail = NEU.fail,
    fileIcon = NEU.fileIcon,
    hydrateImgs = NEU.hydrateImgs,
    ic = NEU.ic,
    reload = NEU.reload,
    txt = NEU.txt,
    val = NEU.val;

  // ===== Danh sách câu hỏi gọn + cửa sổ "Chi tiết câu hỏi" (sinh viên) =====
  var WKD = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"],
    QS = {};

  function fWk(v) {
    var x = d(v);
    return x ? WKD[x.getDay()] + ", " + fDM(v) : "";
  }

  function seenIds() {
    try {
      var r = localStorage.getItem("neu_seen_ans");
      return r === null ? null : JSON.parse(r) || [];
    } catch (e) {
      return [];
    }
  }

  function markSeen(id) {
    try {
      var a = seenIds() || [];
      if (a.indexOf(id) < 0) {
        a.push(id);
        localStorage.setItem("neu_seen_ans", JSON.stringify(a.slice(-500)));
      }
    } catch (e) {}
  }

  function seenSince() {
    // chấm xanh chỉ báo câu trả lời đến sau lần đầu dùng tính năng này trên trình duyệt
    try {
      var v = localStorage.getItem("neu_seen_since");
      if (!v) {
        v = new Date().toISOString();
        localStorage.setItem("neu_seen_since", v);
      }
      return new Date(v);
    } catch (e) {
      return new Date();
    }
  }

  function isNewAns(q) {
    var t = d(q.answered_at);
    return q.status === "answered" && !!t && t > seenSince() && (seenIds() || []).indexOf(q.id) < 0;
  }

  function qPill(q) {
    var ok = q.status === "answered";
    return (
      '<span class="qr-pill ' +
      (ok ? "ok" : "wait") +
      '">' +
      ic(ok ? "check" : "clock") +
      (q.status === "flagged" ? "Đang xem xét" : ok ? "Đã trả lời" : "Chờ trả lời") +
      "</span>"
    );
  }

  function qModalEl() {
    var m = document.getElementById("qModal");
    if (!m) {
      m = document.createElement("div");
      m.className = "modal";
      m.id = "qModal";
      m.setAttribute("role", "dialog");
      m.setAttribute("aria-modal", "true");
      m.setAttribute("aria-label", "Chi tiết câu hỏi");
      document.body.appendChild(m);
      m.addEventListener("click", function (e) {
        if (e.target === m || e.target.closest("[data-qm-close]")) closeQModal();
      });
    }
    return m;
  }

  function closeQModal() {
    NEU.state.qmOpenId = null;
    NEU.state.qmEditing = null;
    var m = document.getElementById("qModal");
    if (m) m.classList.remove("open");
  }

  function qmFiles(q) {
    return (q.attachments || []).length
      ? '<div class="q-files">' +
          q.attachments
            .map(function (x) {
              return (
                '<button class="q-file" data-open="/api/questions/' +
                q.id +
                "/attachments/" +
                x.id +
                '" data-name="' +
                esc(x.name) +
                '">' +
                fileIcon(x.name) +
                "<span>" +
                esc(x.name) +
                "</span></button>"
              );
            })
            .join("") +
          "</div>"
      : "";
  }

  function qmAnswer(a) {
    return (
      '<div class="qm-box qm-ans"><div class="qm-label">Phản hồi của Giảng viên</div>' +
      '<div class="qm-by"><span class="qm-av">' +
      ic("grad") +
      "</span><div><b>" +
      esc(a.lecturer_name || "Giảng viên") +
      '</b><div class="qm-when">' +
      fWk(a.created_at) +
      " · " +
      fTime(a.created_at) +
      (a.edited_at ? " · đã chỉnh sửa" : "") +
      "</div></div></div>" +
      (a.via_group ? '<div class="qm-note">Trả lời chung cho các câu hỏi tương tự</div>' : "") +
      '<div class="qm-body">' +
      md(a.content) +
      "</div></div>"
    );
  }

  function qModalHTML(q) {
    var ok = q.status === "answered",
      editing = NEU.state.qmEditing === q.id;
    return (
      '<div class="modal-card qm-card"><div class="qm-head"><span class="qm-ico">' +
      ic("chat") +
      '</span><h2 class="qm-title">Chi tiết câu hỏi</h2>' +
      qPill(q) +
      '<span class="qm-tools">' +
      (q.can_modify && !editing
        ? '<button class="q-ico" data-qm-edit="' +
          q.id +
          '" title="Sửa câu hỏi" aria-label="Sửa câu hỏi">' +
          ic("edit") +
          '</button><button class="q-ico danger" data-qm-del="' +
          q.id +
          '" title="Xóa câu hỏi" aria-label="Xóa câu hỏi">' +
          ic("trash") +
          "</button>"
        : "") +
      '<button class="q-ico" data-qm-close title="Đóng" aria-label="Đóng">' +
      ic("x") +
      '</button></span></div><div class="qm-meta"><div><span class="qm-label">Mã câu hỏi</span><b class="qm-code">' +
      esc(q.code) +
      '</b></div><div><span class="qm-label">Thời gian gửi</span><div class="qm-dt"><span>' +
      ic("cal") +
      fDate(q.created_at) +
      "</span><span>" +
      ic("clock") +
      fTime(q.created_at) +
      "</span></div></div></div>" +
      '<div class="qm-box"><div class="qm-label">Nội dung câu hỏi' +
      (q.edited_at ? ' <span class="q-edited">· đã chỉnh sửa</span>' : "") +
      "</div>" +
      (editing
        ? '<textarea id="qmText" maxlength="2000" aria-label="Nội dung câu hỏi">' +
          esc(NEU.state.qmDraft) +
          '</textarea><div class="ab-edit-actions"><button class="btn sm" data-qm-cancel>Hủy</button>' +
          '<button class="btn primary sm" data-qm-save="' +
          q.id +
          '">Lưu thay đổi</button></div>'
        : '<div class="qm-body">' + md(q.content) + "</div>" + qmFiles(q)) +
      "</div>" +
      (ok
        ? (q.answers || []).map(qmAnswer).join("") +
          '<div class="qm-actions"><button class="btn sm" data-explain="' +
          q.id +
          '">' +
          SPARK.replace('class="robot"', 'class="robot ico" style="color:var(--accent)"') +
          'Nhờ NEU AI giải thích thêm</button></div><div id="explain' +
          q.id +
          '"></div>'
        : '<div class="qm-wait">' +
          ic("clock") +
          "Đang chờ Giảng viên trả lời. Bạn sẽ thấy chấm xanh khi có phản hồi.</div>") +
      "</div>"
    );
  }

  function openQModal(id) {
    var q = QS[id];
    if (!q) return;
    var m = qModalEl();
    NEU.state.qmOpenId = id;
    if (NEU.state.qmEditing !== id) NEU.state.qmEditing = null;
    m.innerHTML = qModalHTML(q);
    m.classList.add("open");
    if (typeof hydrateImgs === "function") hydrateImgs();
    if (q.status === "answered" && isNewAns(q)) {
      markSeen(q.id);
      $$('[data-qrow="' + id + '"] .qr-dot').forEach(function (x) {
        x.remove();
      });
    }
  }

  document.addEventListener("keydown", function (e) {
    var r = e.target.closest && e.target.closest("[data-qrow]");
    if (r && e.target === r && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      openQModal(+r.dataset.qrow);
    }
    if (e.key === "Escape" && NEU.state.qmOpenId !== null) closeQModal();
  });

  document.addEventListener("input", function (e) {
    if (e.target && e.target.id === "qmText") NEU.state.qmDraft = e.target.value;
  });

  document.addEventListener("click", async function (e) {
    var row = e.target.closest("[data-qrow]"),
      ed = e.target.closest("[data-qm-edit]"),
      dl = e.target.closest("[data-qm-del]"),
      cn = e.target.closest("[data-qm-cancel]"),
      sv = e.target.closest("[data-qm-save]");
    if (row && !ed && !dl) openQModal(+row.dataset.qrow);
    if (ed) {
      NEU.state.qmEditing = +ed.dataset.qmEdit;
      NEU.state.qmDraft = QS[NEU.state.qmEditing].content;
      openQModal(NEU.state.qmEditing);
      var t = document.getElementById("qmText");
      if (t) t.focus();
    }
    if (cn) {
      var cid = NEU.state.qmOpenId;
      NEU.state.qmEditing = null;
      openQModal(cid);
    }
    if (sv) {
      var sid = +sv.dataset.qmSave,
        txt2 = val("qmText");
      if (!txt2) {
        toast("Vui lòng nhập nội dung câu hỏi", "error");
        return;
      }
      busy(sv, true);
      try {
        await API.patch("/api/questions/" + sid + "/mine", { content: txt2 });
        NEU.state.qmEditing = null;
        toast("Đã lưu câu hỏi");
        if (NEU.state.reloadFn) await NEU.state.reloadFn().catch(function () {});
        openQModal(sid);
      } catch (err) {
        fail(err);
        busy(sv, false);
      }
    }
    if (dl) {
      var did = +dl.dataset.qmDel;
      if (
        !(await confirmBox(
          "Xóa câu hỏi này?",
          "Câu hỏi sẽ bị xóa hẳn khỏi hệ thống và không thể khôi phục. Chỉ xóa được khi Giảng viên chưa phản hồi.",
          "Xóa",
        ))
      )
        return;
      try {
        await API.del("/api/questions/" + did + "/mine");
        toast("Đã xóa câu hỏi");
        closeQModal();
        reload(true);
      } catch (err) {
        fail(err);
        reload(true);
      }
    }
  });

  document.addEventListener("click", async function (e) {
    var ex = e.target.closest("[data-explain]");
    if (ex) {
      var box = document.getElementById("explain" + ex.dataset.explain);
      busy(ex, true);
      box.innerHTML =
        '<div class="explain-box"><span class="typing"><i></i><i></i><i></i></span> NEU AI đang giải thích…</div>';
      try {
        var r = await API.post("/api/questions/" + ex.dataset.explain + "/explain");
        box.innerHTML =
          '<div class="explain-box"><div class="eb-head">NEU AI giải thích thêm</div>' +
          aiText(r.explanation) +
          (r.sources && r.sources.length
            ? '<div class="tiny muted" style="margin-top:6px">Nguồn: ' +
              r.sources
                .map(function (x) {
                  return (
                    esc(x.filename) +
                    (x.page ? (/\.xlsx$/i.test(x.filename) ? " · sheet " : " · tr.") + x.page : "")
                  );
                })
                .join(", ") +
              "</div>"
            : "") +
          "</div>";
      } catch (err) {
        box.innerHTML = "";
        fail(err);
      }
      busy(ex, false);
    }
  });

  async function weekNav(w, page) {
    var all = (await API.get("/api/classes/" + w.class_id + "/weeks")).weeks;
    var prev = all.filter(function (x) {
        return x.number === w.number - 1;
      })[0],
      next = all.filter(function (x) {
        return x.number === w.number + 1;
      })[0];
    if (prev) {
      $("#wPrev").hidden = false;
      $("#wPrev").href = page + "?week=" + prev.id;
    }
    if (next) {
      $("#wNext").hidden = false;
      $("#wNext").href = page + "?week=" + next.id; // tuần chưa học vẫn mở được để xem tài liệu
    }
  }

  async function resolveWeekId(page) {
    var wid = API.param("week");
    if (wid) return +wid;
    var cs = await API.get("/api/classes");
    var c = cs.filter(function (x) {
      return x.current_week;
    })[0];
    if (c) return c.current_week.id;
    if (cs[0]) {
      var ws = (await API.get("/api/classes/" + cs[0].id + "/weeks")).weeks;
      return ws[0].id;
    }
    return null;
  }

  function weekHeader(w) {
    var u = w.unit_label || "Tuần";
    txt("wCrumb", w.subject + " · " + w.class_code);
    txt("wTitle", u + " " + w.number);
    document.title = u + " " + w.number + " · " + w.subject + " | NEU Feedback";
    var b = $("#wBadge");
    b.className = "wh-pill " + w.status;
    b.textContent = w.status_label;
    txt("wMeta", "Giảng viên " + (w.lecturer_name || ""));
    if ($("#wPrev")) $("#wPrev").innerHTML = ic("back") + u + " trước";
    if ($("#wNext")) $("#wNext").innerHTML = u + " sau " + ic("arrow");
  }

  // NEU AI (trang riêng + nút nổi)
  var ROBOT =
    '<svg class="robot" viewBox="0 0 24 24" aria-hidden="true">' +
    '<rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V5"/><circle cx="12" cy="4" r="1.3"/>' +
    '<circle class="eye" cx="9" cy="13" r="1.4"/><circle class="eye" cx="15" cy="13" r="1.4"/>' +
    '<path d="M9.5 16.3h5"/><path d="M2.5 12.5v2.5M21.5 12.5v2.5"/></svg>';

  function mdInline(t) {
    t = t
      .replace(
        /!\[([^\]]*)\]\((\/api\/answer-images\/\d+)\)/g,
        '<img class="ans-img" alt="$1" data-auth-src="$2">',
      )
      .replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
      )
      .replace(/\+\+([^+]+)\+\+/g, "<u>$1</u>");
    return t
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(/__([^_]+)__/g, "<b>$1</b>")
      .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s.,;:!?)]|$)/g, "$1<i>$2</i>");
  }

  function md(text) {
    // hiển thị câu trả lời dạng Markdown của AI (đã lọc an toàn)
    var lines = esc(String(text || ""))
        .replace(/\r/g, "")
        .split("\n"),
      out = [],
      list = null,
      para = [],
      code = null;
    function flushP() {
      if (para.length) {
        out.push("<p>" + mdInline(para.join("<br>")) + "</p>");
        para = [];
      }
    }
    function flushL() {
      if (list) {
        out.push(
          "<" +
            list.t +
            ">" +
            list.items
              .map(function (x) {
                return "<li>" + mdInline(x) + "</li>";
              })
              .join("") +
            "</" +
            list.t +
            ">",
        );
        list = null;
      }
    }
    lines.forEach(function (ln) {
      if (/^\s*```/.test(ln)) {
        if (code) {
          out.push("<pre><code>" + code.join("\n") + "</code></pre>");
          code = null;
        } else {
          flushP();
          flushL();
          code = [];
        }
        return;
      }
      if (code) {
        code.push(ln);
        return;
      }
      var m;
      if (!ln.trim()) {
        flushP();
        flushL();
        return;
      }
      if ((m = ln.match(/^\s*#{1,6}\s+(.*)$/))) {
        flushP();
        flushL();
        out.push("<h4>" + mdInline(m[1]) + "</h4>");
        return;
      }
      if ((m = ln.match(/^\s*[-*•]\s+(.*)$/))) {
        flushP();
        if (!list || list.t !== "ul") {
          flushL();
          list = { t: "ul", items: [] };
        }
        list.items.push(m[1]);
        return;
      }
      if ((m = ln.match(/^\s*\d+[.)]\s+(.*)$/))) {
        flushP();
        if (!list || list.t !== "ol") {
          flushL();
          list = { t: "ol", items: [] };
        }
        list.items.push(m[1]);
        return;
      }
      flushL();
      para.push(ln.trim());
    });
    if (code) out.push("<pre><code>" + code.join("\n") + "</code></pre>");
    flushP();
    flushL();
    return '<div class="md">' + out.join("") + "</div>";
  }

  function qPlain(t) {
    // nội dung có định dạng → một dòng chữ thường (danh sách câu hỏi, hộp thư, tìm kiếm)
    return String(t || "")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\+\+([^+]+)\+\+/g, "$1")
      .replace(/(^|[\s(])\*([^*\s][^*]*?)\*/g, "$1$2")
      .replace(/^\s*([-*•]|\d+[.)])\s+/gm, "")
      .replace(/\s*\n+\s*/g, " ")
      .trim();
  }
  NEU.QS = QS;
  NEU.ROBOT = ROBOT;
  NEU.fWk = fWk;
  NEU.isNewAns = isNewAns;
  NEU.md = md;
  NEU.mdInline = mdInline;
  NEU.openQModal = openQModal;
  NEU.qPill = qPill;
  NEU.qPlain = qPlain;
  NEU.resolveWeekId = resolveWeekId;
  NEU.seenSince = seenSince;
  NEU.weekHeader = weekHeader;
  NEU.weekNav = weekNav;
})((window.NEU = window.NEU || {}));
