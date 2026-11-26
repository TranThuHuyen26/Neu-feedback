/* Trang week (studentWeek). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ED_TOOLS = NEU.ED_TOOLS,
    QS = NEU.QS,
    busy = NEU.busy,
    d = NEU.d,
    edCount = NEU.edCount,
    edInit = NEU.edInit,
    empty = NEU.empty,
    esc = NEU.esc,
    fail = NEU.fail,
    fileIcon = NEU.fileIcon,
    fsize = NEU.fsize,
    ic = NEU.ic,
    initSeen = NEU.initSeen,
    openQModal = NEU.openQModal,
    qChips = NEU.qChips,
    qFilter = NEU.qFilter,
    qRow = NEU.qRow,
    resolveWeekId = NEU.resolveWeekId,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val,
    weekHeader = NEU.weekHeader,
    weekNav = NEU.weekNav;

  async function studentWeek() {
    var wid = await resolveWeekId("student-week.html");
    if (!wid) {
      txt("wTitle", "Bạn chưa tham gia lớp nào");
      return;
    }
    var w = await API.get("/api/weeks/" + wid),
      docs = [];
    var slot = $("#askEditorSlot");
    if (slot) {
      slot.outerHTML = askEditorHTML(
        "askBox",
        "Nhập câu hỏi của bạn… (có thể in đậm, gạch đầu dòng, đính kèm ảnh/tài liệu)",
      );
      edInit();
    }
    weekHeader(w);
    $("#wBack").href = "student-class.html?class=" + w.class_id + "&tab=weeks";
    weekNav(w, "student-week.html");
    API.get("/api/materials?week_id=" + wid).then(function (d) {
      docs = d;
      set(
        "wDocsList",
        d.length
          ? d
              .map(function (m) {
                return (
                  '<div class="list-row"><div class="file-cell">' +
                  fileIcon(m.file_type || m.filename) +
                  "<div><b>" +
                  esc(m.filename) +
                  '</b><div class="meta">' +
                  fsize(m.size_bytes) +
                  "</div></div></div>" +
                  '<button class="btn sm" data-open="/api/materials/' +
                  m.id +
                  '/download" data-name="' +
                  esc(m.filename) +
                  '">' +
                  ic("eye") +
                  "Xem</button></div>"
                );
              })
              .join("")
          : empty("Chưa có tài liệu."),
      );
      NEU.state.reloadFn().catch(function () {});
    });
    if (!w.can_ask) {
      $("#askMain").classList.add("locked");
      var bl = $("#askBlocked");
      bl.hidden = false;
      $("b", bl).textContent =
        w.status === "upcoming"
          ? (w.unit_label || "Tuần") + " này chưa mở đặt câu hỏi"
          : w.ask_blocked_reason;
      $("#askBox").setAttribute("contenteditable", "false");
      $("#askBtn").disabled = true;
      $$("#askArea .ed-tools button").forEach(function (b) {
        b.disabled = true;
      });
    }
    var focusWaiting = API.param("focus") === "waiting";
    if (API.param("tab") === "mine") tabs($("[data-target=sw3]"), "sw");
    function side(mine) {
      var ans = mine.filter(function (q) {
        return q.status === "answered";
      }).length;
      set(
        "wSide",
        "<h3>Thông tin " +
          (w.unit_label || "tuần").toLowerCase() +
          "</h3>" +
          '<div class="wi-content"><span>Nội dung</span><b>' +
          esc(w.title || "Chưa cập nhật") +
          "</b></div>" +
          '<div class="info-row"><span>Trạng thái</span><b>' +
          esc(w.status_label) +
          "</b></div>" +
          '<div class="info-row"><span>Câu hỏi của tôi</span><b>' +
          mine.length +
          (mine.length ? " · " + ans + " đã trả lời" : "") +
          "</b></div>" +
          '<div class="info-row"><span>Tài liệu</span><b>' +
          (docs.length ? docs.length + " tệp" : "Chưa có") +
          "</b></div>" +
          (docs.length
            ? '<div class="side-docs">' +
              docs
                .map(function (m) {
                  return (
                    '<button class="wdoc" data-open="/api/materials/' +
                    m.id +
                    '/download" data-name="' +
                    esc(m.filename) +
                    '">' +
                    fileIcon(m.file_type || m.filename) +
                    "<span><b>" +
                    esc(m.filename) +
                    "</b><small>" +
                    fsize(m.size_bytes) +
                    "</small></span>" +
                    ic("eye") +
                    "</button>"
                  );
                })
                .join("") +
              "</div>"
            : ""),
      );
    }
    var fileInput = $("#askFile"),
      askFiles = [],
      ASK_OK = /\.(png|jpe?g|gif|webp|pdf|docx|pptx|xlsx)$/i;
    function renderAskFiles() {
      var box = $("#askFiles");
      box.hidden = !askFiles.length;
      box.innerHTML = askFiles
        .map(function (f, i) {
          return (
            '<span class="ask-file">' +
            fileIcon(f.name) +
            '<b title="' +
            esc(f.name) +
            '">' +
            esc(f.name) +
            "</b><small>" +
            fsize(f.size) +
            '</small><button type="button" data-rm-ask="' +
            i +
            '" aria-label="Bỏ tệp">×</button></span>'
          );
        })
        .join("");
    }
    function addAskFiles(list) {
      Array.prototype.forEach.call(list || [], function (f) {
        if (askFiles.length >= 3) {
          toast("Chỉ đính kèm tối đa 3 tệp", "error");
          return;
        }
        if (!ASK_OK.test(f.name)) {
          toast("“" + f.name + "”: chỉ đính kèm ảnh, PDF, Word, PowerPoint, Excel", "error");
          return;
        }
        if (f.size > 20 * 1024 * 1024) {
          toast("“" + f.name + "” vượt quá 20 MB", "error");
          return;
        }
        if (
          askFiles.some(function (x) {
            return x.name === f.name && x.size === f.size;
          })
        )
          return;
        askFiles.push(f);
      });
      renderAskFiles();
    }
    fileInput.addEventListener("change", function () {
      addAskFiles(fileInput.files);
      fileInput.value = "";
    });
    var askEd = $("#askArea .ask-editor");
    $("[data-attach]", askEd).onclick = function () {
      if (w.can_ask) fileInput.click();
    };
    $("#askFiles").addEventListener("click", function (e) {
      var b = e.target.closest("[data-rm-ask]");
      if (b) {
        askFiles.splice(+b.dataset.rmAsk, 1);
        renderAskFiles();
      }
    });
    ["dragenter", "dragover"].forEach(function (ev) {
      askEd.addEventListener(ev, function (e) {
        if (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types, "Files") > -1) {
          e.preventDefault();
          askEd.classList.add("drag");
        }
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      askEd.addEventListener(ev, function () {
        askEd.classList.remove("drag");
      });
    });
    askEd.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        e.preventDefault();
        if (w.can_ask) addAskFiles(e.dataTransfer.files);
      }
    });
    $("#askBox").addEventListener("paste", function (e) {
      // dán ảnh chụp màn hình → thành tệp đính kèm
      var fs = e.clipboardData && e.clipboardData.files;
      if (!fs || !fs.length) return;
      e.preventDefault();
      e.stopPropagation();
      addAskFiles(fs);
    });
    var mineSf = "",
      lastMine = [];
    $("#myChips").onclick = function (e) {
      var c = e.target.closest("[data-s]");
      if (!c) return;
      mineSf = c.dataset.s;
      NEU.state.reloadFn();
    };
    NEU.state.reloadFn = async function () {
      var mine = await API.get("/api/weeks/" + wid + "/my-questions");
      txt("myCount", mine.length);
      initSeen(mine);
      mine = mine.slice().sort(function (x, y) {
        return d(y.created_at) - d(x.created_at);
      });
      set("myChips", qChips(mine, mineSf));
      var shown = qFilter(mine, mineSf);
      set(
        "myQs",
        shown
          .map(function (q) {
            return qRow(q, false);
          })
          .join("") ||
          empty(
            mine.length
              ? "Không có câu hỏi nào ở mục này."
              : "Bạn chưa gửi câu hỏi nào trong " +
                  (w.unit_label || "tuần").toLowerCase() +
                  " này.",
          ),
      );
      if (NEU.state.qmOpenId !== null && NEU.state.qmEditing === null && QS[NEU.state.qmOpenId])
        openQModal(NEU.state.qmOpenId);
      side(mine);
      if (focusWaiting && mine.length) {
        focusWaiting = false;
        var ws = mine.filter(function (x) {
          return x.status !== "answered";
        })[0];
        var el = ws && $('#myQs [data-qrow="' + ws.id + '"]');
        if (el) {
          el.scrollIntoView({ block: "center" });
          el.classList.add("flash");
        }
      }
    };
    await NEU.state.reloadFn();
    API.poll(function () {
      NEU.state.reloadFn().catch(function () {});
    }, 8000);
    $("#askBtn").addEventListener("click", async function () {
      var content = val("askBox");
      if (!content) {
        $("#askBox").focus();
        toast("Vui lòng nhập câu hỏi", "error");
        return;
      }
      if (content.length > 2000) {
        toast("Câu hỏi dài quá 2.000 ký tự", "error");
        return;
      }
      var btn = this;
      busy(btn, true);
      try {
        var fd = new FormData();
        fd.append("content", content);
        askFiles.forEach(function (f) {
          fd.append("attachments", f);
        });
        await API.form("/api/weeks/" + wid + "/questions", fd);
        $("#askBox").value = "";
        askFiles = [];
        renderAskFiles();
        edCount($("#askBox"));
        toast("Đã gửi câu hỏi ẩn danh");
        await NEU.state.reloadFn();
        tabs($("[data-target=sw3]"), "sw");
      } catch (e) {
        fail(e);
      } finally {
        busy(btn, false);
      }
    });
  }

  var ED_TOOLS_SV = ED_TOOLS.replace(/<button type="button" data-ed="img"[\s\S]*?<\/button>/, "");

  function askEditorHTML(id, ph) {
    // ô đặt câu hỏi của sinh viên: cùng kiểu ô soạn của Giảng viên + nút Đính kèm, đếm ký tự
    return (
      '<div class="editor ask-editor" data-editor="' +
      id +
      '" data-max="2000"><div class="ed-tools">' +
      ED_TOOLS_SV +
      '<span class="ed-sep"></span>' +
      '<button type="button" class="ed-attach" data-attach title="Đính kèm ảnh hoặc tài liệu" aria-label="Đính kèm ảnh hoặc tài liệu">' +
      '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="m21 11-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 7"/></svg>' +
      "Đính kèm</button>" +
      '<span class="ed-count">0/2000</span></div>' +
      '<div class="ed-area" contenteditable="true" role="textbox" aria-multiline="true" aria-label="Nội dung câu hỏi" id="' +
      id +
      '" data-ph="' +
      esc(ph || "") +
      '"></div>' +
      '<div class="ask-files" id="askFiles" hidden></div></div>'
    );
  }
  NEU.studentWeek = studentWeek;
  NEU.pages.studentWeek = studentWeek;
})((window.NEU = window.NEU || {}));
