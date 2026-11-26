/* Trang ai (studentAI). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    aiText = NEU.aiText,
    confirmBox = NEU.confirmBox,
    empty = NEU.empty,
    esc = NEU.esc,
    fail = NEU.fail,
    ic = NEU.ic,
    nl = NEU.nl,
    pickClass = NEU.pickClass,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  function attChips(m) {
    var a = m.attachments || [];
    if (!a.length) return "";
    return (
      '<div class="att-chips">' +
      a
        .map(function (x) {
          return (
            '<button class="att-chip" data-open="/api/ai/messages/' +
            m.id +
            "/attachments/" +
            x.index +
            '" data-name="' +
            esc(x.name) +
            '">' +
            ic("file") +
            "<span>" +
            esc(x.name) +
            "</span></button>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function aiBubble(m) {
    if (m.role === "user")
      return '<div class="bubble me">' + nl(m.content) + attChips(m) + "</div>";
    var src = (m.sources || []).length
      ? '<div class="sources"><span class="tiny muted">Nguồn:</span>' +
        m.sources
          .map(function (x) {
            return (
              '<button class="src" data-open="/api/materials/' +
              x.material_id +
              '/download" data-name="' +
              esc(x.filename) +
              '">' +
              esc(x.filename) +
              (x.page ? (/\.xlsx$/i.test(x.filename) ? " · sheet " : " · tr.") + x.page : "") +
              "</button>"
            );
          })
          .join("") +
        "</div>"
      : "";
    return (
      '<div class="msg-ai"><span class="ai-avatar sm">' +
      NEU.ROBOT +
      '</span><div class="bubble ai">' +
      aiText(m.content) +
      src +
      "</div></div>"
    );
  }

  async function studentAI() {
    var classes = await API.get("/api/classes");
    var sel = $("#aiClass"),
      box = $("#aiMsgs");
    if (!classes.length) {
      set("aiMsgs", empty("Bạn cần tham gia lớp học để dùng NEU AI."));
      return;
    }
    sel.innerHTML = classes
      .map(function (c) {
        return '<option value="' + c.id + '">' + esc(c.code + " · " + c.subject) + "</option>";
      })
      .join("");
    sel.value = String(
      await pickClass(
        classes.map(function (c) {
          return Object.assign({}, c, { question_count: c.material_count });
        }),
      ),
    );
    API.get("/api/health").then(function (h) {
      txt("aiMode", h.ai_mode === "gemini" ? "Sẵn sàng" : "Chế độ demo (chưa có API key)");
    });
    function side() {
      set(
        "aiClasses",
        classes
          .map(function (c) {
            return (
              '<p data-cls="' +
              c.id +
              '" class="' +
              (String(c.id) === sel.value ? "chat-current" : "") +
              '"><b>' +
              esc(c.code) +
              "</b><span>" +
              esc(c.subject) +
              "</span></p>"
            );
          })
          .join(""),
      );
    }
    async function load() {
      side();
      var h = await API.get("/api/ai/history?class_id=" + sel.value);
      box.innerHTML = h.length
        ? h.map(aiBubble).join("")
        : '<div class="msg-ai"><span class="ai-avatar sm">' +
          NEU.ROBOT +
          '</span><div class="bubble ai">' +
          "Chào bạn! Mình là NEU AI, trợ lý học tập của hệ thống. Mình trả lời dựa trên tài liệu Giảng viên đã tải lên cho lớp <b>" +
          esc(sel.options[sel.selectedIndex].text) +
          "</b>. Bạn muốn hỏi gì?</div></div>";
      box.scrollTop = box.scrollHeight;
    }
    var files = [],
      OKF = /\.(png|jpe?g|webp|pdf|docx|pptx|xlsx|txt|md)$/i;
    function renderFiles() {
      set(
        "aiAttach",
        files
          .map(function (f, i) {
            return (
              '<span class="att-chip">' +
              ic("file") +
              "<span>" +
              esc(f.name) +
              '</span><button type="button" data-rm-att="' +
              i +
              '" aria-label="Bỏ tệp">×</button></span>'
            );
          })
          .join(""),
      );
    }
    var fi = $("#aiFiles");
    if (fi)
      fi.addEventListener("change", function () {
        Array.prototype.forEach.call(fi.files, function (f) {
          if (files.length >= 3) {
            toast("Tối đa 3 tệp mỗi tin nhắn", "error");
            return;
          }
          if (!OKF.test(f.name)) {
            toast(
              "“" + f.name + "” không được hỗ trợ. Chỉ nhận ảnh, PDF, Word, PowerPoint, Excel, TXT",
              "error",
            );
            return;
          }
          if (f.size > 10 * 1024 * 1024) {
            toast("“" + f.name + "” vượt quá 10 MB", "error");
            return;
          }
          files.push(f);
        });
        fi.value = "";
        renderFiles();
      });
    $("#aiAttach").addEventListener("click", function (e) {
      var b = e.target.closest("[data-rm-att]");
      if (b) {
        files.splice(+b.dataset.rmAtt, 1);
        renderFiles();
      }
    });
    async function send(text) {
      text = (text || "").trim();
      if (!text && files.length) text = "Giải thích giúp mình nội dung tệp đính kèm.";
      if (!text) return;
      var sending = files.slice();
      files = [];
      renderFiles();
      $("#aiInput").value = "";
      box.insertAdjacentHTML(
        "beforeend",
        '<div class="bubble me">' +
          nl(text) +
          (sending.length
            ? '<div class="att-chips">' +
              sending
                .map(function (f) {
                  return (
                    '<span class="att-chip">' +
                    ic("file") +
                    "<span>" +
                    esc(f.name) +
                    "</span></span>"
                  );
                })
                .join("") +
              "</div>"
            : "") +
          "</div>" +
          '<div class="msg-ai" id="aiTyping"><span class="ai-avatar sm">' +
          NEU.ROBOT +
          '</span><div class="bubble ai"><span class="typing"><i></i><i></i><i></i></span>' +
          (sending.length ? ' <span class="tiny muted">Đang đọc tệp đính kèm…</span>' : "") +
          "</div></div>",
      );
      box.scrollTop = box.scrollHeight;
      try {
        var fd = new FormData();
        fd.append("class_id", sel.value);
        fd.append("message", text);
        sending.forEach(function (f) {
          fd.append("files", f);
        });
        var r = await API.form("/api/ai/chat", fd);
        $("#aiTyping").outerHTML = aiBubble({ role: "ai", content: r.answer, sources: r.sources });
      } catch (e) {
        $("#aiTyping").outerHTML =
          '<div class="msg-ai"><span class="ai-avatar sm">' +
          NEU.ROBOT +
          '</span><div class="bubble ai">' +
          esc(e.message) +
          "</div></div>";
      }
      box.scrollTop = box.scrollHeight;
    }
    sel.onchange = function () {
      load().catch(fail);
    };
    $("#aiClasses").addEventListener("click", function (e) {
      var p = e.target.closest("[data-cls]");
      if (p) {
        sel.value = p.dataset.cls;
        load().catch(fail);
      }
    });
    $("#aiSend").onclick = function () {
      send(val("aiInput"));
    };
    $("#aiInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") send(val("aiInput"));
    });
    $$(".compose-api .suggest button").forEach(function (b) {
      b.onclick = function () {
        send(b.textContent);
      };
    });
    if ($("#aiNew"))
      $("#aiNew").onclick = async function () {
        if (
          !(await confirmBox(
            "Xóa lịch sử trò chuyện?",
            "Toàn bộ câu hỏi và câu trả lời với NEU AI của lớp này sẽ bị xóa, không khôi phục được.",
            "Xóa lịch sử",
          ))
        )
          return;
        await API.del("/api/ai/history?class_id=" + sel.value);
        load();
      };
    await load();
    if (API.param("q")) send(API.param("q"));
  }
  NEU.studentAI = studentAI;
  NEU.pages.studentAI = studentAI;
})((window.NEU = window.NEU || {}));
