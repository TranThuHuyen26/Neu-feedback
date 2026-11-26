/* Nút chat NEU AI nổi ở góc màn hình (chỉ sinh viên). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    aiText = NEU.aiText,
    d = NEU.d,
    esc = NEU.esc,
    fDate = NEU.fDate,
    fail = NEU.fail,
    ic = NEU.ic,
    nl = NEU.nl;

  function floatingAI() {
    // nút NEU AI nổi ở các trang sinh viên: chọn lớp, xem lịch sử theo lớp, mở trang đầy đủ
    var box = $("#aiChat");
    if (!box) return;
    var EXP =
      '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/></svg>';
    box.innerHTML =
      '<div class="ai-head"><b>NEU AI · Trợ lý học tập</b>' +
      '<a class="btn sm icon-only" id="fExpand" href="student-ai.html" title="Mở trang NEU AI đầy đủ" aria-label="Mở trang NEU AI">' +
      EXP +
      "</a>" +
      '<button class="btn sm icon-only" type="button" onclick="toggleAI()" aria-label="Đóng">' +
      ic("x") +
      "</button></div>" +
      '<div class="fai-cls"><label for="fClass">Lớp</label><select id="fClass"><option>Đang tải…</option>' +
      "</select></div>" +
      '<div class="ai-body" id="aiBody"></div>' +
      '<div class="ai-compose">' +
      '<input id="aiInput" placeholder="Hỏi NEU AI…" aria-label="Câu hỏi cho NEU AI" autocomplete="off">' +
      '<button class="btn primary sm" type="button" id="fSend">Gửi</button></div>';
    var classes = null,
      sel = $("#fClass"),
      body = $("#aiBody"),
      input = $("#aiInput"),
      busyNow = false;
    function dayLabel(v) {
      var x = d(v);
      if (!x) return "";
      var t = new Date();
      t.setHours(0, 0, 0, 0);
      var k = new Date(x);
      k.setHours(0, 0, 0, 0);
      var diff = Math.round((t - k) / 86400000);
      return diff === 0 ? "Hôm nay" : diff === 1 ? "Hôm qua" : fDate(v);
    }
    function srcHTML(list) {
      return (list || []).length
        ? '<div class="fai-src">' +
            list
              .map(function (s) {
                return (
                  '<button type="button" data-open="/api/materials/' +
                  s.material_id +
                  '/download" data-name="' +
                  esc(s.filename) +
                  '">' +
                  esc(s.filename) +
                  (s.page
                    ? " · " + (/\.xlsx$/i.test(s.filename) ? "sheet " : "tr.") + s.page
                    : "") +
                  "</button>"
                );
              })
              .join("") +
            "</div>"
        : "";
    }
    function bubble(m) {
      return m.role === "user"
        ? '<div class="me">' +
            nl(m.content) +
            (m.attachments && m.attachments.length
              ? '<div class="fai-att">' + ic("file") + m.attachments.length + " tệp đính kèm</div>"
              : "") +
            "</div>"
        : '<div class="ai">' + aiText(m.content) + srcHTML(m.sources) + "</div>";
    }
    function cur() {
      return (classes || []).filter(function (c) {
        return String(c.id) === sel.value;
      })[0];
    }
    async function load() {
      var c = cur();
      if (!c) return;
      $("#fExpand").href = "student-ai.html?class=" + c.id;
      input.placeholder = "Hỏi NEU AI về lớp " + c.code + "…";
      body.innerHTML =
        '<div class="loading"><span class="typing"><i></i><i></i><i></i></span></div>';
      var h = await API.get("/api/ai/history?class_id=" + c.id),
        last = "",
        html = "";
      h.forEach(function (m) {
        var dl = dayLabel(m.created_at);
        if (dl !== last) {
          html += '<div class="fai-day">' + dl + "</div>";
          last = dl;
        }
        html += bubble(m);
      });
      body.innerHTML =
        html ||
        '<div class="ai">Mình trả lời dựa trên tài liệu Giảng viên đã tải lên cho lớp <b>' +
          esc(c.code + " · " + c.subject) +
          "</b>. Bạn muốn hỏi gì?</div>" +
          '<div class="fai-sg"><button type="button">Tóm tắt tài liệu tuần này</button><button type="button">' +
          'Giải thích khái niệm khó trong bài</button><button type="button">Gợi ý câu hỏi ôn tập</button></div>';
      body.scrollTop = body.scrollHeight;
    }
    async function init() {
      if (classes) return;
      classes = await API.get("/api/classes");
      if (!classes.length) {
        sel.innerHTML = "<option>Chưa có lớp</option>";
        body.innerHTML = '<div class="ai">Bạn cần tham gia lớp học để dùng NEU AI.</div>';
        return;
      }
      sel.innerHTML = classes
        .map(function (c) {
          return '<option value="' + c.id + '">' + esc(c.code + " · " + c.subject) + "</option>";
        })
        .join("");
      var want = API.param("class");
      if (!want && API.param("week")) {
        try {
          want = (await API.get("/api/weeks/" + API.param("week"))).class_id;
        } catch (e) {
          /* bỏ qua */
        }
      }
      var c0 =
        classes.filter(function (c) {
          return String(c.id) === String(want);
        })[0] ||
        classes.filter(function (c) {
          return c.current_week;
        })[0] ||
        classes[0];
      sel.value = String(c0.id);
      await load();
    }
    async function send(text) {
      text = (text || "").trim();
      if (!text || busyNow || !cur()) return;
      busyNow = true;
      input.value = "";
      var sg = $(".fai-sg", body);
      if (sg) sg.remove();
      body.insertAdjacentHTML(
        "beforeend",
        '<div class="me">' +
          esc(text) +
          '</div><div class="ai" id="fTyping"><span class="typing"><i></i><i></i><i></i></span></div>',
      );
      body.scrollTop = body.scrollHeight;
      try {
        var fd = new FormData();
        fd.append("class_id", sel.value);
        fd.append("message", text);
        var r = await API.form("/api/ai/chat", fd);
        $("#fTyping").outerHTML =
          '<div class="ai">' + aiText(r.answer) + srcHTML(r.sources) + "</div>";
      } catch (e) {
        $("#fTyping").outerHTML = '<div class="ai">' + esc(e.message) + "</div>";
      }
      busyNow = false;
      body.scrollTop = body.scrollHeight;
    }
    window.askAI = function () {
      send(input.value);
    };
    $("#fSend").onclick = window.askAI;
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.isComposing) {
        e.preventDefault();
        send(input.value);
      }
    });
    body.addEventListener("click", function (e) {
      var b = e.target.closest(".fai-sg button");
      if (b) send(b.textContent);
    });
    sel.onchange = function () {
      load().catch(fail);
    };
    var orig = window.toggleAI;
    window.toggleAI = function () {
      if (orig) orig();
      if (box.classList.contains("open")) init().catch(fail);
    };
  }
  NEU.floatingAI = floatingAI;
})((window.NEU = window.NEU || {}));
