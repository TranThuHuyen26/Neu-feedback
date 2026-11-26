/* Trang week (lecturerWeek). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ACTIONS = NEU.ACTIONS,
    ED_TOOLS = NEU.ED_TOOLS,
    ROBOT = NEU.ROBOT,
    SPARK = NEU.SPARK,
    bars = NEU.bars,
    busy = NEU.busy,
    confirmBox = NEU.confirmBox,
    dur = NEU.dur,
    edCount = NEU.edCount,
    edInit = NEU.edInit,
    empty = NEU.empty,
    esc = NEU.esc,
    fDM = NEU.fDM,
    fDate = NEU.fDate,
    fTime = NEU.fTime,
    fail = NEU.fail,
    fileIcon = NEU.fileIcon,
    fsize = NEU.fsize,
    ic = NEU.ic,
    kpi = NEU.kpi,
    md = NEU.md,
    mdInline = NEU.mdInline,
    mdToEd = NEU.mdToEd,
    nl = NEU.nl,
    qPlain = NEU.qPlain,
    resolveWeekId = NEU.resolveWeekId,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val,
    weekHeader = NEU.weekHeader,
    weekNav = NEU.weekNav;

  function aiToMd(t) {
    // gợi ý của NEU AI → nội dung soạn được (giữ đậm/nghiêng/danh sách, tiêu đề thành chữ đậm)
    return String(t || "")
      .replace(/\r/g, "")
      .replace(/```[a-z]*\n?/gi, "")
      .replace(/^\s*#{1,6}\s+(.*)$/gm, "**$1**")
      .replace(/^(\s*)[*•]\s+/gm, "$1- ")
      .replace(/__([^_]+)__/g, "**$1**")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function editorHTML(id, value, ph) {
    return (
      '<div class="editor" data-editor="' +
      id +
      '"><div class="ed-tools">' +
      ED_TOOLS +
      '</div><div class="ed-area" contenteditable="true" role="textbox" aria-multiline="true" id="' +
      id +
      '" data-ph="' +
      esc(ph || "") +
      '">' +
      (value ? mdToEd(value) : "") +
      "</div></div>"
    );
  }

  // Khung kéo thả tải tài liệu (dùng ở trang tuần và Kho tài liệu)
  function initDropzone(root, opts) {
    if (!root) return;
    var input = $("input[type=file]", root),
      zone = $(".dropzone", root),
      list = $(".dz-files", root),
      btn = $(".dz-upload", root);
    var OK = /\.(pdf|docx|pptx|xlsx|txt|md)$/i,
      MAX = 20 * 1024 * 1024,
      items = [],
      uploading = false;
    function ftype(n) {
      var e = (n.split(".").pop() || "").toLowerCase();
      return (
        { pdf: "PDF", docx: "DOC", pptx: "PPT" }[e] ||
        (e === "txt" || e === "md" ? "TXT" : e.slice(0, 4).toUpperCase())
      );
    }
    function size(b) {
      return b > 1048576
        ? (b / 1048576).toFixed(1) + " MB"
        : Math.max(1, Math.round(b / 1024)) + " KB";
    }
    function render() {
      list.innerHTML = items
        .map(function (it, i) {
          return (
            '<div class="dz-file' +
            (it.err ? " bad" : "") +
            '"><span class="ftype">' +
            esc(ftype(it.file.name)) +
            '</span><b title="' +
            esc(it.file.name) +
            '">' +
            esc(it.file.name) +
            "</b><small>" +
            size(it.file.size) +
            "</small>" +
            (it.err
              ? '<span class="dz-state err">' + esc(it.err) + "</span>"
              : it.state
                ? '<span class="dz-state ' + (it.cls || "") + '">' + it.state + "</span>"
                : it.dup
                  ? '<span class="dz-state warn">Trùng tên</span>'
                  : "") +
            (uploading
              ? ""
              : '<button type="button" data-rm="' + i + '" aria-label="Bỏ tệp">×</button>') +
            "</div>"
          );
        })
        .join("");
      var good = items.filter(function (x) {
        return !x.err && !x.done;
      }).length;
      btn.disabled = uploading || !good || !opts.getWeekId();
      btn.innerHTML = ic("upload") + (good ? "Tải lên " + good + " tệp" : "Tải lên");
      var cnt = $(".dz-count", root);
      if (cnt) cnt.textContent = opts.getWeekId() ? "" : "Chọn tuần trước khi tải";
    }
    function add(files) {
      var names = opts.existing ? opts.existing() : [];
      Array.prototype.forEach.call(files, function (f) {
        if (
          items.some(function (x) {
            return x.file.name === f.name && x.file.size === f.size;
          })
        )
          return;
        items.push({
          file: f,
          err: !OK.test(f.name)
            ? "Chỉ nhận PDF, Word, PowerPoint, Excel, TXT"
            : f.size > MAX
              ? "Vượt quá 20 MB"
              : "",
          dup: names.indexOf(f.name) > -1,
        });
      });
      render();
    }
    ["dragenter", "dragover"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.add("drag");
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.remove("drag");
      });
    });
    zone.addEventListener("drop", function (e) {
      if (!uploading) add(e.dataTransfer.files);
    });
    zone.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", function () {
      add(input.files);
      input.value = "";
    });
    list.addEventListener("click", function (e) {
      var b = e.target.closest("[data-rm]");
      if (b) {
        items.splice(+b.dataset.rm, 1);
        render();
      }
    });
    btn.addEventListener("click", async function () {
      var todo = items.filter(function (x) {
        return !x.err && !x.done;
      });
      if (
        todo.some(function (x) {
          return x.dup;
        }) &&
        !(await confirmBox(
          "Đã có tài liệu cùng tên",
          "Một số tệp trùng tên với tài liệu đã có trong tuần. Vẫn tải lên thêm?",
          "Vẫn tải lên",
        ))
      )
        return;
      uploading = true;
      var wid = opts.getWeekId(),
        ok = 0,
        warn = 0;
      for (var i = 0; i < todo.length; i++) {
        var it = todo[i];
        it.state = "Đang tải lên & xử lý cho NEU AI…";
        it.cls = "";
        render();
        try {
          var fd = new FormData();
          fd.append("files", it.file);
          var res = await API.form("/api/weeks/" + wid + "/materials", fd);
          if (res[0] && res[0].status === "failed") {
            it.state = "Đã tải, nhưng không đọc được nội dung (có thể là ảnh scan)";
            it.cls = "warn";
            warn++;
          } else {
            it.state = "✓ Xong";
            it.cls = "ok";
            ok++;
          }
          it.done = true;
        } catch (e) {
          it.state = e.message;
          it.cls = "err";
        }
        render();
      }
      uploading = false;
      render();
      toast(
        "Đã tải lên " +
          (ok + warn) +
          " tài liệu" +
          (warn ? " · " + warn + " tệp NEU AI không đọc được" : ""),
      );
      if (opts.onDone) opts.onDone();
      setTimeout(function () {
        items = items.filter(function (x) {
          return !(x.done && x.cls === "ok");
        });
        render();
      }, 2000);
    });
    render();
    return { refresh: render };
  }

  // Trang tuần học của Giảng viên: câu hỏi · nội dung & tài liệu · báo cáo
  async function lecturerWeek() {
    var wid = await resolveWeekId("lecturer-week.html");
    if (!wid) {
      txt("wTitle", "Chưa có lớp nào");
      return;
    }
    var w = await API.get("/api/weeks/" + wid);
    weekHeader(w);
    $("#wBack").href = "lecturer-class.html?class=" + w.class_id + "&tab=weeks";
    weekNav(w, "lecturer-week.html");
    $("#wkTitle").value = w.title;
    if (API.param("tab") === "docs") {
      tabs($("[data-target=lw2]"), "lw");
      if (!w.title)
        setTimeout(function () {
          $("#wkTitle").focus();
        }, 60);
    }
    ACTIONS.saveWeek = async function () {
      var r = await API.patch("/api/weeks/" + wid, { title: val("wkTitle") });
      w.title = r.title;
      weekHeader(Object.assign(w, r));
      toast("Đã lưu nội dung tuần " + w.number);
    };
    var docNames = [],
      docsAll = [];
    function renderDocs() {
      var k = val("wkSort") || "new",
        list = docsAll.slice();
      list.sort(function (x, y) {
        return k === "old"
          ? new Date(x.created_at) - new Date(y.created_at)
          : k === "name"
            ? x.filename.localeCompare(y.filename, "vi")
            : k === "size"
              ? (y.size_bytes || 0) - (x.size_bytes || 0)
              : new Date(y.created_at) - new Date(x.created_at);
      });
      set(
        "wkDocs",
        list
          .map(function (m) {
            return (
              '<tr><td><div class="fname">' +
              fileIcon(m.file_type || m.filename) +
              '<b title="' +
              esc(m.filename) +
              '">' +
              esc(m.filename) +
              "</b></div></td>" +
              "<td>" +
              fDate(m.created_at) +
              '<div class="tiny muted">' +
              fTime(m.created_at) +
              '</div></td><td class="nowrap">' +
              fsize(m.size_bytes) +
              "</td>" +
              '<td><div class="mat-actions"><button class="btn sm icon-only" title="Xem" data-open="/api/materials/' +
              m.id +
              '/download" data-name="' +
              esc(m.filename) +
              '">' +
              ic("eye") +
              "</button>" +
              '<button class="kebab" data-kebab aria-label="Thao tác">⋮</button><div class="pop-menu" hidden>' +
              '<button data-rename="' +
              m.id +
              '" data-name="' +
              esc(m.filename) +
              '">' +
              ic("edit") +
              "Đổi tên</button>" +
              '<button data-dl="/api/materials/' +
              m.id +
              '/download" data-name="' +
              esc(m.filename) +
              '">' +
              ic("download") +
              'Tải xuống</button><button class="danger" data-del-doc="' +
              m.id +
              '" data-name="' +
              esc(m.filename) +
              '">' +
              ic("trash") +
              "Xóa</button></div></div></td></tr>"
            );
          })
          .join("") || '<tr><td colspan="4">' + empty("Tuần này chưa có tài liệu.") + "</td></tr>",
      );
    }
    async function loadDocs() {
      docsAll = await API.get("/api/materials?week_id=" + wid);
      docNames = docsAll.map(function (m) {
        return m.filename;
      });
      txt("wkDocCount", "(" + docsAll.length + ")");
      renderDocs();
    }
    if ($("#wkSort")) $("#wkSort").onchange = renderDocs;
    NEU.state.reloadFn = loadDocs;
    initDropzone($("#weekUpload"), {
      getWeekId: function () {
        return wid;
      },
      existing: function () {
        return docNames;
      },
      onDone: loadDocs,
    });
    loadDocs();

    // ---- câu hỏi: lọc chọn nhiều · duyệt câu tương đồng · sửa câu trả lời · trả lời câu hỏi tiếp · soạn có định dạng
    var sel = { all: true },
      current = null,
      qMap = {},
      lastData = null,
      suggestion = "",
      sugCache = {},
      gSug = {},
      shownGroupSig = "",
      groupsCache = [],
      editing = null,
      curGroup = null;
    window.__edClassId = w.class_id;
    var slot = $("#lsEditorSlot");
    if (slot) {
      slot.outerHTML = editorHTML("lsReply", "", "Viết câu trả lời cho sinh viên…");
      edInit();
    }
    var focusId = +API.param("q") || null;
    if (API.param("filter") === "waiting") sel = { waiting: true };
    if (API.param("filter") === "answered") sel = { answered: true };
    function stOf(q) {
      if (q.status === "waiting" && q.reuse) return ["review", "Chờ duyệt"];
      return (
        {
          waiting: ["waiting", "Chờ trả lời"],
          answered: ["answered", "Đã trả lời"],
          flagged: ["flagged", "Đã gắn cờ"],
          hidden: ["hidden", "Đã ẩn"],
        }[q.status] || ["answered", q.status]
      );
    }
    function groupsOnly() {
      var k = Object.keys(sel).filter(function (x) {
        return sel[x];
      });
      return k.length === 1 && k[0] === "groups";
    }
    function inFilter(q) {
      if (sel.all) return true;
      var st = stOf(q)[0];
      return (
        (sel.waiting && st === "waiting") ||
        (sel.review && st === "review") ||
        (sel.answered && st === "answered") ||
        (sel.flagged && st === "flagged") ||
        (sel.groups && !!q.group)
      );
    }
    function syncMenu() {
      $$("#lsFilterMenu input").forEach(function (cb) {
        cb.checked = !!sel[cb.value];
      });
      var on = Object.keys(sel).filter(function (k) {
        return sel[k] && k !== "all";
      });
      $("#lsFilterBtn").classList.toggle("primary", !sel.all);
      txt("lsFilterLbl", sel.all ? "Lọc" : "Lọc (" + on.length + ")");
    }
    var noticeSeen = { groups: false };
    function renderNotice() {
      var cnt = (lastData && lastData.counts) || {},
        html = "";
      var pg = groupsCache.filter(function (g) {
        return g.status === "suggested";
      }).length;
      if (pg && !groupsOnly() && !noticeSeen.groups)
        html +=
          '<div class="notice-bar"><span class="nb-ico">' +
          SPARK +
          '</span><span class="nb-text"><b>' +
          pg +
          " đề xuất nhóm câu hỏi tương đồng</b> cần xử lý</span>" +
          '<button data-modal="groupsModal" data-seen-groups>Xem ' +
          ic("arrow") +
          "</button></div>";
      if (
        cnt.review &&
        Object.keys(sel)
          .filter(function (k) {
            return sel[k];
          })
          .join() !== "review"
      )
        html +=
          '<div class="notice-bar"><span class="nb-ico">' +
          SPARK +
          '</span><span class="nb-text"><b>' +
          cnt.review +
          " câu hỏi giống câu đã trả lời</b> đang chờ duyệt</span>" +
          "<button data-show-review>Xem</button><button data-approve-all>Duyệt tất cả</button></div>";
      set("lsNotice", html);
    }
    function render(data) {
      lastData = data;
      var qs = data.questions;
      qs.forEach(function (q) {
        qMap[q.id] = q;
      });
      var c = {
        all: qs.length,
        waiting: 0,
        review: 0,
        answered: 0,
        flagged: 0,
        groups: groupsCache.filter(function (g) {
          return g.status === "confirmed";
        }).length,
      };
      qs.forEach(function (q) {
        var st = stOf(q)[0];
        if (c[st] !== undefined) c[st]++;
      });
      $$("#lsFilterMenu em").forEach(function (e) {
        e.textContent = "(" + (c[e.dataset.c] || 0) + ")";
      });
      txt("cWait", c.waiting + c.review);
      syncMenu();
      renderNotice();
      if (groupsOnly()) {
        txt("lsTotal", "(" + c.groups + " nhóm)");
        renderGroupList();
        return;
      }
      var list = qs.filter(inFilter);
      txt("lsTotal", "(" + list.length + ")");
      set(
        "lsList",
        list
          .map(function (q) {
            var st = stOf(q);
            return (
              '<div class="qrow' +
              (current === q.id ? " selected" : "") +
              '" data-qid="' +
              q.id +
              '"><div class="qr-main"><span class="qdot ' +
              st[0] +
              '" title="' +
              st[1] +
              '"></span><div style="min-width:0">' +
              '<div class="qr-text">' +
              esc(qPlain(q.content)) +
              '</div><div class="qr-meta">' +
              esc(q.code) +
              " · " +
              fDM(q.created_at) +
              " " +
              fTime(q.created_at) +
              (q.reuse ? ' · <span class="hl">giống ' + esc(q.reuse.code) + "</span>" : "") +
              (q.group ? " · nhóm " + esc(q.group.label) : "") +
              "</div></div></div>" +
              ic("arrow").replace('class="ico"', 'class="ico qr-chev"') +
              "</div>"
            );
          })
          .join("") ||
          (Object.keys(sel)
            .filter(function (k) {
              return sel[k];
            })
            .join() === "review"
            ? empty("Đã duyệt hết câu hỏi giống câu đã trả lời.") +
              '<p style="text-align:center;margin:-4px 0 12px"><button class="btn sm" data-show-waiting>' +
              "Xem câu chờ trả lời</button></p>"
            : empty("Không có câu hỏi phù hợp bộ lọc.")),
      );
      if (
        !current ||
        !qMap[current] ||
        !list.some(function (q) {
          return q.id === current;
        })
      ) {
        var first = focusId && qMap[focusId] ? qMap[focusId] : list[0];
        focusId = null;
        if (first) show(first.id);
        else {
          current = null;
          set("lsDetail", '<p class="muted">Chọn một câu hỏi để xem chi tiết.</p>');
          $("#lsReplyBox").hidden = true;
        }
      } else if (!editing) show(current, true);
    }
    function qHead(t) {
      // [tiêu đề HTML, phần thân HTML]; câu hỏi có định dạng: dòng đầu làm tiêu đề, phần còn lại hiển thị đúng định dạng
      t = String(t || "").trim();
      if (/\*\*|\+\+|^\s*([-*•]|\d+[.)])\s|\]\(https?:/m.test(t)) {
        var lines = t.split("\n"),
          first = lines[0];
        if (!/^\s*([-*•]|\d+[.)])\s/.test(first) && qPlain(first).length <= 160)
          return [
            mdInline(esc(first)),
            lines.slice(1).join("\n").trim()
              ? '<div class="dq-body md-q">' + md(lines.slice(1).join("\n")) + "</div>"
              : "",
          ];
        return ["", '<div class="dq-body md-q">' + md(t) + "</div>"];
      }
      var tt = splitTitle(t);
      return [esc(tt[0]), tt[1] ? '<p class="dq-body">' + nl(tt[1]) + "</p>" : ""];
    }
    function splitTitle(t) {
      t = String(t || "").trim();
      var m = t.match(/^(.{12,160}?[?？.!])\s+(.+)$/s);
      return m ? [m[1], m[2]] : [t, ""];
    }
    function lecturerAnswerHTML(a) {
      var head =
        (a.via_group ? "Trả lời chung cho các câu tương tự" : "Phản hồi đã gửi") +
        " · " +
        fDM(a.created_at) +
        " " +
        fTime(a.created_at) +
        (a.edited_at
          ? " <small>· đã chỉnh sửa " + fDM(a.edited_at) + " " + fTime(a.edited_at) + "</small>"
          : "");
      return (
        '<div class="ans-block" data-ans="' +
        a.id +
        '"><div class="ab-head"><span>' +
        head +
        '</span><button class="btn sm" data-edit-ans="' +
        a.id +
        '">' +
        ic("edit") +
        "Sửa</button></div>" +
        '<div class="ab-body">' +
        md(a.content) +
        "</div>" +
        (a.copies_count
          ? '<div class="ab-foot">Đã dùng cho ' + a.copies_count + " câu hỏi tương tự</div>"
          : "") +
        (a.is_copy ? '<div class="ab-foot">Dùng lại từ câu trả lời của câu tương tự</div>' : "") +
        "</div>"
      );
    }
    function show(id, keep) {
      var q = qMap[id];
      if (!q) return;
      var changed = current !== id;
      current = id;
      $$("#lsList .qrow").forEach(function (x) {
        x.classList.toggle("selected", +x.dataset.qid === id);
      });
      if (keep && !changed) return;
      suggestion = "";
      editing = null;
      var st = stOf(q),
        tt = qHead(q.content);
      var reuse = q.reuse
        ? '<div class="reuse-box"><div class="rb-head">Giống câu ' +
          esc(q.reuse.code) +
          " đã trả lời (tuần " +
          q.reuse.week_number +
          ") · độ giống " +
          Math.round(q.reuse.score * 100) +
          "%</div>" +
          '<div class="rb-old">Câu cũ: “' +
          esc(qPlain(q.reuse.content)) +
          '”</div><div class="rb-ans"><b>Câu trả lời sẽ gửi:</b>' +
          md(q.reuse.answer) +
          "</div>" +
          '<div class="row"><button class="btn primary sm" data-approve="' +
          q.id +
          '">' +
          ic("check") +
          'Duyệt &amp; gửi</button><button class="btn sm" data-reject="' +
          q.id +
          '">' +
          ic("edit") +
          "Không giống — trả lời riêng</button></div></div>"
        : "";
      var aiBox =
        q.status === "waiting" && !q.reuse
          ? '<div class="ai-card"><div class="ai-card-head"><span class="nb-ico">' +
            SPARK +
            '</span><div class="grow"><b>NEU AI gợi ý câu trả lời</b></div>' +
            '<button class="btn sm" id="lsSuggest">' +
            ROBOT.replace('class="robot"', 'class="robot ico" style="color:var(--accent)"') +
            'Tạo gợi ý</button><button class="ai-toggle" id="lsAiToggle" aria-label="Thu gọn">▾</button></div>' +
            '<div class="ai-card-body" id="lsAiBody" hidden><p class="tiny muted" id="lsHint">' +
            'NEU AI chỉ tạo gợi ý khi Giảng viên bấm.</p><div id="lsOut" hidden><div class="ai-text"></div>' +
            '<div class="row" style="margin-top:8px"><button class="btn primary sm" id="lsUse">' +
            "Dùng gợi ý</button></div></div></div></div>"
          : "";
      var atts = q.attachments || [];
      var att = atts.length
        ? '<div class="att-card"><h4>Tệp đính kèm (' +
          atts.length +
          ")</h4>" +
          atts
            .map(function (x) {
              var u = "/api/questions/" + q.id + "/attachments/" + x.id;
              return (
                '<div class="att-row">' +
                fileIcon(x.name) +
                "<b>" +
                esc(x.name) +
                '</b><small class="muted">' +
                fsize(x.size) +
                "</small>" +
                '<button class="btn sm icon-only" title="Tải xuống" data-dl="' +
                u +
                '" data-name="' +
                esc(x.name) +
                '">' +
                ic("download") +
                "</button>" +
                '<button class="btn sm icon-only" title="Xem" data-open="' +
                u +
                '" data-name="' +
                esc(x.name) +
                '">' +
                ic("eye") +
                "</button></div>"
              );
            })
            .join("") +
          "</div>"
        : "";
      set(
        "lsDetail",
        '<div class="dt-head"><div class="qmeta"><span class="st-pill ' +
          st[0] +
          '">' +
          st[1] +
          '</span> <span class="tiny muted">' +
          esc(q.code) +
          " · " +
          fDate(q.created_at) +
          " " +
          fTime(q.created_at) +
          " · Ẩn danh</span></div>" +
          '<div class="dt-actions">' +
          (q.status === "flagged"
            ? ""
            : '<button class="btn sm flag" data-modal="flagModal">' +
              ic("flag") +
              "Gắn cờ</button>") +
          '<button class="kebab" data-kebab aria-label="Thêm">⋮</button><div class="pop-menu" hidden>' +
          (q.group ? '<button data-modal="groupsModal">Xem nhóm tương đồng</button>' : "") +
          '<button data-copy-q="' +
          q.id +
          '">Sao chép nội dung</button></div></div></div>' +
          (tt[0] ? '<h2 class="dq-title">' + tt[0] + "</h2>" : "") +
          tt[1] +
          (q.group
            ? '<button class="sim-link" data-modal="groupsModal"><span class="sim-tag">' +
              esc(q.group.label) +
              "</span> " +
              (q.group.status === "confirmed" ? "Nhóm đã xác nhận" : "NEU AI đề xuất gộp nhóm") +
              " · độ giống " +
              Math.round(q.group.score * 100) +
              "%</button>"
            : "") +
          reuse +
          aiBox +
          att +
          (q.answers || []).map(lecturerAnswerHTML).join("") +
          (q.status === "flagged"
            ? '<div class="answered" style="background:var(--red-soft)"><b style="color:var(--red-ink)">Đã chuyển cho Admin kiểm duyệt</b><p>Câu hỏi đang chờ Admin xử lý.</p></div>'
            : ""),
      );
      var box = $("#lsReplyBox");
      box.hidden =
        q.status === "flagged" || q.status === "hidden" || !!q.reuse || q.status === "answered";
      $("#lsReply").value = "";
      $("#lsReply").style.height = "";
      edCount($("#lsReply"));
      $("#lsReply").placeholder = "Viết câu trả lời cho sinh viên…";
      txt(
        "lsReplyHint",
        q.group && q.group.status === "confirmed" && q.status === "waiting"
          ? "Nhóm đã xác nhận: câu trả lời gửi cho mọi câu đang chờ trong nhóm " + q.group.label
          : "",
      );
      var tg = $("#lsAiToggle");
      if (tg)
        tg.onclick = function () {
          var b = $("#lsAiBody");
          b.hidden = !b.hidden;
          tg.textContent = b.hidden ? "▾" : "▴";
        };
      var sb = $("#lsSuggest");
      if (sb)
        sb.onclick = async function () {
          $("#lsAiBody").hidden = false;
          $("#lsAiToggle").textContent = "▴";
          busy(sb, true);
          $("#lsHint").hidden = false;
          $("#lsHint").innerHTML =
            '<span class="typing"><i></i><i></i><i></i></span> NEU AI đang soạn gợi ý…';
          try {
            var r = await API.post("/api/questions/" + q.id + "/suggest");
            sugCache[q.id] = r.suggestion;
            if (current === q.id) {
              suggestion = r.suggestion;
              $("#lsOut .ai-text").innerHTML = md(r.suggestion);
              $("#lsOut").hidden = false;
              $("#lsHint").hidden = true;
              sb.innerHTML = ic("refresh") + "Tạo lại";
            }
          } catch (e) {
            $("#lsHint").textContent = e.message;
          } finally {
            busy(sb, false);
          }
        };
      if (sb && sugCache[q.id]) {
        // gợi ý đã tạo trước đó: giữ nguyên khi chuyển câu / cuộn / danh sách tự cập nhật
        suggestion = sugCache[q.id];
        $("#lsAiBody").hidden = false;
        $("#lsAiToggle").textContent = "▴";
        $("#lsHint").hidden = true;
        $("#lsOut .ai-text").innerHTML = md(suggestion);
        $("#lsOut").hidden = false;
        sb.innerHTML = ic("refresh") + "Tạo lại";
      }
      var ub = $("#lsUse");
      if (ub)
        ub.onclick = function () {
          $("#lsReply").value = aiToMd(suggestion);
          $("#lsReply").dispatchEvent(new Event("input", { bubbles: true }));
          $("#lsReply").focus();
        };
    }
    async function load() {
      render(await API.get("/api/weeks/" + wid + "/questions"));
    }
    function groupHTML(g, full) {
      var waiting = g.questions.filter(function (q) {
        return q.status === "waiting";
      }).length;
      var head =
        '<div class="between"><div><b>' +
        esc(g.label) +
        '</b><div class="tiny muted">' +
        g.questions
          .map(function (q) {
            return q.code + " (T" + q.week_number + ")";
          })
          .join(" + ") +
        " · độ giống " +
        Math.round(g.score * 100) +
        "%</div></div>" +
        (g.status === "confirmed"
          ? '<span class="badge">Đã xác nhận</span>'
          : '<span class="badge warn">Chờ xác nhận</span>') +
        "</div>";
      var qs = g.questions
        .map(function (q) {
          var st = stOf(q);
          return (
            '<p class="tiny"><b>' +
            esc(q.code) +
            "</b> " +
            esc(qPlain(q.content)) +
            ' <span class="qr-st ' +
            st[0] +
            '">' +
            st[1] +
            "</span></p>"
          );
        })
        .join("");
      var act;
      if (g.status === "suggested")
        act =
          '<div class="row"><button class="btn primary sm" data-grp="' +
          g.id +
          '" data-act="confirm">Xác nhận nhóm</button><button class="btn sm" data-grp="' +
          g.id +
          '" data-act="reject">Không gộp</button></div>';
      else if (waiting)
        act =
          '<div class="ai-card"><div class="ai-card-head"><span class="nb-ico">' +
          SPARK +
          '</span><div class="grow"><b>Gợi ý câu trả lời chung từ NEU AI</b></div>' +
          '<button class="btn sm" data-gsuggest="' +
          g.id +
          '">' +
          ic("refresh") +
          'Tạo gợi ý</button></div><div class="ai-card-body"><p class="tiny muted" id="gHint' +
          g.id +
          '" hidden></p>' +
          '<div id="gOut' +
          g.id +
          '" hidden><div class="ai-text"></div><div class="row" style="margin-top:8px">' +
          '<button class="btn primary sm" data-guse="' +
          g.id +
          '">Dùng gợi ý</button></div></div></div></div>' +
          editorHTML("ga" + g.id, "", "Câu trả lời chung cho " + waiting + " câu đang chờ…") +
          '<div class="row" style="margin-top:8px">' +
          (g.previous_answer
            ? '<button class="btn sm" data-gprev="' +
              g.id +
              '">Dùng lại câu trả lời trước (' +
              esc(g.previous_answer.question_code) +
              ")</button>"
            : "") +
          '<button class="btn primary sm" data-grp-answer="' +
          g.id +
          '">Trả lời cả nhóm</button>' +
          (g.can_split
            ? '<button class="btn sm" data-grp="' + g.id + '" data-act="split">Tách nhóm</button>'
            : "") +
          "</div>";
      else act = "";
      if (g.answer && g.status === "confirmed") {
        // nhóm đã trả lời: hiện câu trả lời chung, sửa được
        var ga = g.answer;
        act =
          '<div class="ans-block grp-ans" data-gans="' +
          g.id +
          '"><div class="ab-head"><span>Trả lời chung · ' +
          fDM(ga.created_at) +
          " " +
          fTime(ga.created_at) +
          (ga.edited_at
            ? " <small>· đã chỉnh sửa " + fDM(ga.edited_at) + " " + fTime(ga.edited_at) + "</small>"
            : "") +
          "</span>" +
          '<button class="btn sm" data-gedit="' +
          g.id +
          '">' +
          ic("edit") +
          'Sửa</button></div><div class="ab-body">' +
          md(ga.content) +
          "</div>" +
          (ga.copies_count
            ? '<div class="ab-foot">Đã gửi cho ' +
              (ga.copies_count + 1) +
              " câu hỏi trong nhóm</div>"
            : "") +
          "</div>" +
          act;
      }
      return (
        '<div class="similar-group' +
        (g.status === "confirmed" ? " confirmed" : "") +
        '" id="grp' +
        g.id +
        '">' +
        head +
        qs +
        act +
        "</div>"
      );
    }
    function renderGroupList() {
      function wait(g) {
        return g.questions.filter(function (q) {
          return q.status === "waiting";
        }).length;
      }
      var gs = groupsCache
        .filter(function (g) {
          return g.status === "confirmed";
        })
        .sort(function (a, b) {
          return wait(b) - wait(a);
        });
      set(
        "lsList",
        gs
          .map(function (g) {
            var n = wait(g);
            return (
              '<div class="qrow' +
              (curGroup === g.id ? " selected" : "") +
              '" data-gid="' +
              g.id +
              '"><div class="qr-main"><span class="qdot ' +
              (n ? "waiting" : "answered") +
              '"></span><div style="min-width:0"><div class="qr-text">Nhóm ' +
              esc(g.label) +
              " · " +
              g.questions.length +
              " câu hỏi giống nhau</div>" +
              '<div class="qr-meta">' +
              esc(g.questions[0] ? g.questions[0].content : "") +
              '</div></div></div><span class="qr-st ' +
              (n ? "waiting" : "answered") +
              '">' +
              (n ? n + " chờ" : "Đã trả lời") +
              "</span></div>"
            );
          })
          .join("") || empty("Chưa có nhóm nào được xác nhận."),
      );
      var g =
        gs.filter(function (x) {
          return x.id === curGroup;
        })[0] || gs[0];
      // chỉ vẽ lại khung chi tiết khi đổi nhóm hoặc dữ liệu nhóm thay đổi → không mất gợi ý NEU AI / nội dung đang soạn
      var sig = g ? JSON.stringify(g) : "";
      if (g && (shownGroupSig !== sig || !$("#grp" + g.id))) showGroup(g);
      else if (g)
        $$("#lsList .qrow").forEach(function (x) {
          x.classList.toggle("selected", +x.dataset.gid === g.id);
        });
      else set("lsDetail", '<p class="muted">Chọn một nhóm để trả lời.</p>');
      $("#lsReplyBox").hidden = true;
    }
    function showGroup(g) {
      curGroup = g.id;
      current = null;
      shownGroupSig = JSON.stringify(g);
      $$("#lsList .qrow").forEach(function (x) {
        x.classList.toggle("selected", +x.dataset.gid === g.id);
      });
      set("lsDetail", '<h2 class="dq-title">Nhóm ' + esc(g.label) + "</h2>" + groupHTML(g));
      if (gSug[g.id]) {
        var o = $("#gOut" + g.id);
        if (o) {
          $(".ai-text", o).innerHTML = md(gSug[g.id]);
          o.dataset.text = gSug[g.id];
          o.hidden = false;
        }
      }
    }
    async function loadGroups() {
      groupsCache = await API.get("/api/weeks/" + wid + "/groups");
      set(
        "groupsBody",
        groupsCache
          .filter(function (g) {
            return g.status === "suggested";
          })
          .map(function (g) {
            return groupHTML(g);
          })
          .join("") || empty("Không có nhóm nào chờ xác nhận."),
      );
      if (lastData) render(lastData);
    }
    function choiceBox(title, msg, a, b) {
      return new Promise(function (resolve) {
        var m = document.getElementById("apiChoice");
        if (!m) {
          m = document.createElement("div");
          m.className = "modal";
          m.id = "apiChoice";
          document.body.appendChild(m);
        }
        m.innerHTML =
          '<div class="modal-card confirm-card"><h2 class="modal-title">' +
          esc(title) +
          '</h2><p class="muted">' +
          esc(msg) +
          '</p><div class="modal-actions">' +
          '<button class="btn" data-c="">Hủy</button><button class="btn" data-c="a">' +
          esc(a) +
          '</button><button class="btn primary" data-c="b">' +
          esc(b) +
          "</button></div></div>";
        m.classList.add("open");
        m.onclick = function (e) {
          var x = e.target.closest("[data-c]");
          if (x || e.target === m) {
            m.classList.remove("open");
            resolve(x ? x.dataset.c || null : null);
          }
        };
      });
    }
    // bộ lọc chọn nhiều
    $("#lsFilterBtn").onclick = function (e) {
      e.stopPropagation();
      $("#lsFilterMenu").hidden = !$("#lsFilterMenu").hidden;
    };
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".filter-dd")) $("#lsFilterMenu").hidden = true;
    });
    $("#lsFilterMenu").addEventListener("change", function (e) {
      var v = e.target.value;
      if (v === "all") sel = e.target.checked ? { all: true } : { waiting: true };
      else {
        sel[v] = e.target.checked;
        delete sel.all;
        if (
          !Object.keys(sel).some(function (k) {
            return sel[k];
          })
        )
          sel = { all: true };
      }
      current = null;
      curGroup = null;
      if (lastData) render(lastData);
    });
    $("#lsList").addEventListener("click", function (e) {
      var gq = e.target.closest("[data-gid]");
      if (gq) {
        var g = groupsCache.filter(function (x) {
          return x.id === +gq.dataset.gid;
        })[0];
        if (g) showGroup(g);
        return;
      }
      var q = e.target.closest("[data-qid]");
      if (q) show(+q.dataset.qid);
    });
    $("#lsSend").onclick = async function () {
      var t = val("lsReply");
      if (!t) {
        $("#lsReply").focus();
        toast("Vui lòng nhập nội dung phản hồi", "error");
        return;
      }
      if (t.length > 5000) {
        toast("Câu trả lời dài quá 5.000 ký tự", "error");
        return;
      }
      var q = qMap[current],
        btn = this;
      busy(btn, true);
      try {
        if (q.group && q.group.status === "confirmed" && q.status === "waiting") {
          var r = await API.post("/api/groups/" + q.group.id + "/answer", { content: t });
          toast("Đã trả lời chung cho " + r.answered.length + " câu hỏi trong nhóm");
        } else {
          await API.post("/api/questions/" + q.id + "/answer", { content: t });
          toast("Đã gửi phản hồi cho sinh viên");
        }
        current = null;
        await load();
        loadGroups();
      } catch (e) {
        fail(e);
      } finally {
        busy(btn, false);
      }
    };
    ACTIONS.flagQuestion = async function () {
      await API.post("/api/questions/" + current + "/flag", { reason: val("flReason") });
      closeModal("flagModal");
      toast("Đã gắn cờ để Admin kiểm duyệt");
      current = null;
      load();
    };
    document.addEventListener("click", async function (e) {
      var t = e.target;
      var g = t.closest("[data-grp]"),
        ga = t.closest("[data-grp-answer]"),
        gs = t.closest("[data-gsuggest]"),
        gu = t.closest("[data-guse]"),
        gp = t.closest("[data-gprev]");
      var ap = t.closest("[data-approve]"),
        rj = t.closest("[data-reject]"),
        aa = t.closest("[data-approve-all]"),
        sr = t.closest("[data-show-review]"),
        ed = t.closest("[data-edit-ans]");
      var es = t.closest("[data-edit-save]"),
        ec = t.closest("[data-edit-cancel]"),
        cp = t.closest("[data-copy-q]");
      var ge = t.closest("[data-gedit]"),
        gsv = t.closest("[data-gedit-save]"),
        gcl = t.closest("[data-gedit-cancel]");
      try {
        if (t.closest("[data-seen-groups]")) {
          noticeSeen.groups = true;
          renderNotice();
        }
        if (ge || gsv || gcl) {
          var gg2 = groupsCache.filter(function (x) {
            return (
              String(x.id) ===
              (ge || gsv || gcl).dataset[ge ? "gedit" : gsv ? "geditSave" : "geditCancel"]
            );
          })[0];
          if (!gg2 || !gg2.answer) return;
          var gb = $('[data-gans="' + gg2.id + '"]');
          if (ge) {
            editing = "g" + gg2.id;
            $(".ab-body", gb).outerHTML =
              editorHTML("gedit" + gg2.id, gg2.answer.content, "") +
              '<div class="ab-edit-actions"><button class="btn sm" data-gedit-cancel="' +
              gg2.id +
              '">Hủy</button><button class="btn primary sm" data-gedit-save="' +
              gg2.id +
              '">Lưu</button></div>';
            edInit(gb);
            ge.hidden = true;
            $("#gedit" + gg2.id).focus();
          } else if (gcl) {
            editing = null;
            showGroup(gg2);
          } else {
            var gtxt = val("gedit" + gg2.id);
            if (!gtxt) {
              toast("Câu trả lời không được để trống", "error");
              return;
            }
            busy(gsv, true);
            var r5 = await API.patch("/api/answers/" + gg2.answer.id, {
              content: gtxt,
              apply_to_copies: true,
            });
            toast(
              "Đã sửa câu trả lời chung" +
                (r5.copies_updated
                  ? " và cập nhật cho " + r5.copies_updated + " câu trong nhóm"
                  : ""),
            );
            editing = null;
            await loadGroups();
            var ng = groupsCache.filter(function (x) {
              return x.id === gg2.id;
            })[0];
            if (ng) showGroup(ng);
          }
          return;
        }
        if (cp) {
          var qq = qMap[+cp.dataset.copyQ];
          if (qq && navigator.clipboard) await navigator.clipboard.writeText(qq.content);
          toast("Đã sao chép nội dung câu hỏi");
        }
        if (g) {
          busy(g, true);
          await API.post("/api/groups/" + g.dataset.grp, { action: g.dataset.act });
          toast(
            {
              confirm: "Đã xác nhận nhóm — trả lời chung ở mục Nhóm tương đồng",
              reject: "Đã bỏ đề xuất gộp nhóm",
              split: "Đã tách nhóm, các câu được trả lời riêng",
            }[g.dataset.act],
          );
          if (g.dataset.act === "confirm") {
            closeModal("groupsModal");
            sel = { groups: true };
            curGroup = +g.dataset.grp;
          }
          if (g.dataset.act === "split") curGroup = null;
          await loadGroups();
          current = null;
          await load();
        }
        if (gs) {
          var id = gs.dataset.gsuggest,
            hint = $("#gHint" + id);
          busy(gs, true);
          hint.hidden = false;
          hint.innerHTML =
            '<span class="typing"><i></i><i></i><i></i></span> NEU AI đang soạn câu trả lời chung…';
          try {
            var r = await API.post("/api/groups/" + id + "/suggest");
            var out = $("#gOut" + id);
            $(".ai-text", out).innerHTML = md(r.suggestion);
            out.dataset.text = r.suggestion;
            gSug[id] = r.suggestion;
            out.hidden = false;
            hint.hidden = true;
            gs.innerHTML = ic("refresh") + "Tạo lại";
          } finally {
            busy(gs, false);
          }
        }
        if (gu) {
          var o = $("#gOut" + gu.dataset.guse),
            ta = $("#ga" + gu.dataset.guse);
          ta.value = aiToMd(o.dataset.text || "");
          ta.dispatchEvent(new Event("input", { bubbles: true }));
          ta.focus();
        }
        if (gp) {
          var gg = groupsCache.filter(function (x) {
            return String(x.id) === gp.dataset.gprev;
          })[0];
          if (gg && gg.previous_answer) {
            var tb = $("#ga" + gp.dataset.gprev);
            tb.value = gg.previous_answer.content;
            tb.dispatchEvent(new Event("input", { bubbles: true }));
          }
        }
        if (ga) {
          var text = val("ga" + ga.dataset.grpAnswer);
          if (!text) {
            toast("Vui lòng nhập câu trả lời chung", "error");
            return;
          }
          busy(ga, true);
          var r2 = await API.post("/api/groups/" + ga.dataset.grpAnswer + "/answer", {
            content: text,
          });
          toast("Đã trả lời " + r2.answered.length + " câu hỏi trong nhóm");
          await load();
          await loadGroups();
        }
        if (ap) {
          busy(ap, true);
          await API.post("/api/questions/" + ap.dataset.approve + "/approve-reuse");
          toast("Đã duyệt và gửi câu trả lời cho sinh viên");
          current = null;
          await load();
          loadGroups();
        }
        if (rj) {
          await API.post("/api/questions/" + rj.dataset.reject + "/reject-reuse");
          var keep = +rj.dataset.reject,
            moved = !sel.all && !sel.waiting;
          if (moved) sel = { waiting: true }; // câu hỏi chuyển sang "Chờ trả lời" → đổi bộ lọc theo để không mất câu đang xử lý
          toast(
            moved
              ? "Đã chuyển sang bộ lọc Chờ trả lời — mời trả lời riêng"
              : "Đã bỏ câu trả lời cũ — mời trả lời riêng",
          );
          current = null;
          focusId = keep;
          await load();
          var rb = $("#lsReplyBox");
          if (rb && !rb.hidden) {
            rb.scrollIntoView({ behavior: "smooth", block: "center" });
            setTimeout(function () {
              $("#lsReply").focus();
            }, 250);
          }
        }
        if (aa) {
          if (
            !(await confirmBox(
              "Duyệt tất cả?",
              "Gửi câu trả lời đã có cho mọi câu hỏi đang chờ duyệt trong tuần này.",
              "Duyệt tất cả",
            ))
          )
            return;
          var r3 = await API.post("/api/weeks/" + wid + "/approve-all");
          toast("Đã duyệt và gửi " + r3.approved.length + " câu trả lời");
          current = null;
          await load();
          loadGroups();
        }
        if (sr) {
          sel = { review: true };
          current = null;
          render(lastData);
        }
        if (t.closest("[data-show-waiting]")) {
          sel = { waiting: true };
          current = null;
          render(lastData);
        }
        if (ed) {
          var blk = ed.closest(".ans-block"),
            aid = +ed.dataset.editAns,
            ans0 = (qMap[current].answers || []).filter(function (a) {
              return a.id === aid;
            })[0];
          editing = aid;
          $(".ab-body", blk).outerHTML =
            editorHTML("edit" + aid, ans0 ? ans0.content : "", "") +
            '<div class="ab-edit-actions"><button class="btn sm" data-edit-cancel>Hủy</button>' +
            '<button class="btn primary sm" data-edit-save="' +
            aid +
            '">Lưu</button></div>';
          edInit(blk);
          ed.hidden = true;
          $("#edit" + aid).focus();
        }
        if (ec) {
          editing = null;
          var cq = current;
          current = null;
          show(cq);
        }
        if (es) {
          var aid2 = +es.dataset.editSave,
            content = val("edit" + aid2);
          if (!content) {
            toast("Câu trả lời không được để trống", "error");
            return;
          }
          var ans = (qMap[current].answers || []).filter(function (a) {
              return a.id === aid2;
            })[0],
            apply = false;
          if (ans && ans.copies_count) {
            var ch = await choiceBox(
              "Cập nhật cho các câu tương tự?",
              "Câu trả lời này đã được gửi cho " +
                ans.copies_count +
                " câu hỏi tương tự. Cập nhật bản mới cho cả " +
                ans.copies_count +
                " câu không?",
              "Chỉ sửa câu này",
              "Cập nhật cả " + ans.copies_count + " câu",
            );
            if (!ch) return;
            apply = ch === "b";
          }
          busy(es, true);
          var r4 = await API.patch("/api/answers/" + aid2, {
            content: content,
            apply_to_copies: apply,
          });
          toast(
            r4.copies_updated
              ? "Đã sửa và cập nhật cho " + r4.copies_updated + " câu tương tự"
              : "Đã sửa câu trả lời",
          );
          editing = null;
          var cur = current;
          current = null;
          await load();
          show(cur);
        }
      } catch (err) {
        fail(err);
      }
    });
    await loadGroups();
    if (
      API.param("confirm") &&
      groupsCache.some(function (g) {
        return g.status === "suggested";
      })
    )
      openModal("groupsModal");
    var lastCount = null;
    API.poll(
      async function () {
        if (
          editing ||
          (document.activeElement &&
            (document.activeElement.tagName === "TEXTAREA" ||
              document.activeElement.isContentEditable) &&
            (document.activeElement.value || document.activeElement.textContent).trim())
        )
          return;
        try {
          var data = await API.get("/api/weeks/" + wid + "/questions");
          var n = data.questions.length;
          if (lastCount !== null && n > lastCount) {
            toast("Có " + (n - lastCount) + " câu hỏi mới");
            loadGroups();
          }
          lastCount = n;
          render(data);
        } catch (e) {
          /* thử lại lần sau */
        }
      },
      w.status === "current" ? 5000 : 30000,
    );

    // ---- báo cáo tuần
    var rep = await API.get("/api/weeks/" + wid + "/report");
    set(
      "rhKpis",
      kpi(rep.question_count, "Câu hỏi", "chat", "blue") +
        kpi(rep.answered_count, "Đã trả lời", "check", "green", rep.answer_rate + "% câu hỏi") +
        kpi(dur(rep.avg_response_seconds), "Phản hồi trung bình", "clock", "amber") +
        kpi(
          rep.group_count,
          "Nhóm tương đồng",
          "group",
          "teal",
          (rep.reused_count || 0) + " câu dùng lại câu trả lời",
        ),
    );
    set(
      "rhTimeline",
      bars(
        rep.by_day.map(function (x) {
          var dd = new Date(x.date + "T00:00:00");
          return {
            label: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"][dd.getDay()],
            total: x.questions,
            done: x.answered,
          };
        }),
      ),
    );
    function showSummary(text) {
      set("rhSummary", '<p style="margin:10px 0 0;line-height:1.65">' + md(text) + "</p>");
      $("#rhSummary").hidden = false;
      $("#rhSumHint").hidden = true;
      $("#rhSumBtn").innerHTML = ic("refresh") + "Tạo lại";
    }
    if (rep.summary) showSummary(rep.summary);
    $("#rhSumBtn").onclick = async function () {
      var btn = this;
      busy(btn, true);
      try {
        var r = await API.post(
          "/api/weeks/" + wid + "/summary" + (rep.summary ? "?regenerate=true" : ""),
        );
        rep.summary = r.summary;
        busy(btn, false);
        showSummary(r.summary);
      } catch (e) {
        fail(e);
        busy(btn, false);
      }
    };
  }
  NEU.lecturerWeek = lecturerWeek;
  NEU.pages.lecturerWeek = lecturerWeek;
})((window.NEU = window.NEU || {}));
