/* Trang inbox (lecturerInbox). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    d = NEU.d,
    empty = NEU.empty,
    esc = NEU.esc,
    fDM = NEU.fDM,
    fTime = NEU.fTime,
    fail = NEU.fail,
    ic = NEU.ic,
    qPlain = NEU.qPlain,
    set = NEU.set,
    val = NEU.val;

  async function lecturerInbox() {
    var kind = API.param("kind") || "new",
      sm = await API.get("/api/lecturer/summary"),
      cnt = { new: sm.new, groups: sm.groups, flagged: sm.flagged };
    $$("#ibTabs button").forEach(function (b) {
      $("span", b).textContent = cnt[b.dataset.kind];
    });
    async function load() {
      $$("#ibTabs button").forEach(function (b) {
        b.classList.toggle("on", b.dataset.kind === kind);
      });
      var d = await API.get(
        "/api/lecturer/inbox?kind=" + kind + (val("ibClass") ? "&class_id=" + val("ibClass") : ""),
      );
      if (!$("#ibClass").dataset.filled) {
        $("#ibClass").dataset.filled = "1";
        $("#ibClass").insertAdjacentHTML(
          "beforeend",
          d.classes
            .map(function (c) {
              return (
                '<option value="' + c.id + '">' + esc(c.code + " · " + c.subject) + "</option>"
              );
            })
            .join(""),
        );
      }
      set(
        "ibList",
        d.sections
          .map(function (sec) {
            var rows = sec.items
              .map(function (it) {
                var href =
                  "lecturer-week.html?week=" +
                  sec.week_id +
                  (kind === "groups" ? "&confirm=1" : "&q=" + it.id);
                if (kind === "groups")
                  return (
                    '<a class="ib-row" href="' +
                    href +
                    '"><div class="grow"><b>Nhóm ' +
                    esc(it.label) +
                    " · " +
                    it.questions.length +
                    " câu hỏi giống nhau</b><small>" +
                    esc(
                      it.questions
                        .slice(0, 2)
                        .map(function (q) {
                          return qPlain(q.content);
                        })
                        .join(" · "),
                    ) +
                    '</small></div><span class="tag blue">Độ giống ' +
                    Math.round(it.score * 100) +
                    "%</span>" +
                    ic("arrow") +
                    "</a>"
                  );
                if (kind === "flagged")
                  return (
                    '<a class="ib-row" href="' +
                    href +
                    '"><div class="grow">' +
                    esc(qPlain(it.content)) +
                    "<small>" +
                    esc(it.code) +
                    " · " +
                    fDM(it.created_at) +
                    " " +
                    fTime(it.created_at) +
                    " · Lý do: " +
                    esc(it.reason) +
                    '</small></div><span class="tag red">Mức độ ' +
                    it.ai_score +
                    "</span>" +
                    ic("arrow") +
                    "</a>"
                  );
                return (
                  '<a class="ib-row" href="' +
                  href +
                  '"><div class="grow">' +
                  esc(qPlain(it.content)) +
                  "<small>" +
                  esc(it.code) +
                  " · " +
                  fDM(it.created_at) +
                  " " +
                  fTime(it.created_at) +
                  (it.has_attachment ? " · có tệp đính kèm" : "") +
                  '</small></div><span class="tag' +
                  (it.tag === "Chờ duyệt" ? " blue" : "") +
                  '">' +
                  esc(it.tag) +
                  "</span>" +
                  ic("arrow") +
                  "</a>"
                );
              })
              .join("");
            return (
              '<section class="ib-sec"><div class="ib-sec-head"><div><b>' +
              esc(sec.class_code) +
              " · " +
              (sec.unit_label || "Tuần") +
              " " +
              sec.week_number +
              "</b> <small>" +
              esc(sec.subject) +
              "</small></div><small>" +
              sec.items.length +
              (kind === "groups" ? " nhóm" : " câu") +
              "</small></div>" +
              rows +
              "</section>"
            );
          })
          .join("") ||
          empty(
            {
              new: "Không còn câu hỏi nào chờ trả lời.",
              groups: "Không có nhóm nào chờ xác nhận.",
              flagged: "Không có câu hỏi nào bị gắn cờ.",
            }[kind],
          ),
      );
    }
    $("#ibTabs").onclick = function (e) {
      var b = e.target.closest("[data-kind]");
      if (!b) return;
      kind = b.dataset.kind;
      history.replaceState(null, "", "?kind=" + kind);
      load().catch(fail);
    };
    $("#ibClass").onchange = function () {
      load().catch(fail);
    };
    await load();
  }
  NEU.lecturerInbox = lecturerInbox;
  NEU.pages.lecturerInbox = lecturerInbox;
})((window.NEU = window.NEU || {}));
