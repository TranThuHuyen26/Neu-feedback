/* Trang stats (lecturerStats). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    bars = NEU.bars,
    colorOf = NEU.colorOf,
    empty = NEU.empty,
    esc = NEU.esc,
    kpi = NEU.kpi,
    pct = NEU.pct,
    semFilterHTML = NEU.semFilterHTML,
    set = NEU.set;

  var lsSem = null;
  // học kỳ đang xem ở trang thống kê: null = chưa chọn (lấy học kỳ hiện tại), 'all' = tất cả
  async function lecturerStats() {
    var st = await API.get(
      "/api/lecturer/stats" + (lsSem ? "?semester_id=" + encodeURIComponent(lsSem) : ""),
    );
    if (lsSem === null) {
      // lần đầu: chuyển sang học kỳ hiện tại do máy chủ gợi ý
      lsSem = st.current_semester_id ? String(st.current_semester_id) : "all";
      if (lsSem !== "all")
        st = await API.get("/api/lecturer/stats?semester_id=" + encodeURIComponent(lsSem));
    }
    if (!$("#stSem") && st.semesters.length) {
      $("#stKpis").insertAdjacentHTML(
        "beforebegin",
        semFilterHTML("stSem", st.semesters, false, false),
      );
      $("#stSem").closest(".cls-filter").classList.add("st-filter");
      $("#stSem").onchange = function () {
        lsSem = this.value;
        lecturerStats();
      };
    }
    if ($("#stSem")) $("#stSem").value = lsSem;
    var isCur = lsSem !== "all" && String(st.current_semester_id) === lsSem;
    set(
      "stKpis",
      kpi(st.class_count, isCur ? "Lớp đang dạy" : "Số lớp", "layers", "teal") +
        kpi(st.current_week_label, "Tuần hiện tại", "cal", "blue", st.semester || "") +
        kpi(
          st.question_count,
          "Câu hỏi",
          "chat",
          "violet",
          "Tuần này: " + (st.questions_this_week || 0),
        ) +
        kpi(
          st.answer_rate + "%",
          "Tỷ lệ phản hồi",
          "check",
          "green",
          st.answered_count + "/" + st.question_count + " câu",
        ),
    );
    set(
      "stBars",
      bars(
        st.classes.map(function (c) {
          return {
            label: c.code,
            total: c.question_count,
            done: c.answered_count,
            color: colorOf(c.id),
          };
        }),
      ),
    );
    set(
      "stRates",
      st.classes
        .map(function (c) {
          var p = pct(c.answered_count, c.question_count);
          return (
            "<p>" +
            esc(c.code) +
            ' <b style="float:right">' +
            p +
            '%</b></p><div class="progress" style="color:' +
            colorOf(c.id) +
            '"><span style="width:' +
            p +
            '%"></span></div>'
          );
        })
        .join("") || empty("Chưa có dữ liệu."),
    );
    var head = $("#stTable") && $("#stTable").closest("table").querySelector("thead tr");
    if (head) head.cells[2].textContent = "Tuần đã học";
    set(
      "stTable",
      st.classes
        .map(function (c) {
          return (
            "<tr><td><b>" +
            esc(c.code) +
            '</b><div class="meta">' +
            esc(c.subject) +
            "</div></td><td>" +
            c.student_count +
            "</td><td>" +
            c.weeks_learned +
            "</td><td>" +
            c.question_count +
            "</td><td>" +
            pct(c.answered_count, c.question_count) +
            "%</td></tr>"
          );
        })
        .join("") +
        '<tr class="total-row"><td><b>Tổng</b></td><td></td><td></td><td><b>' +
        st.question_count +
        "</b></td><td><b>" +
        st.answer_rate +
        "%</b></td></tr>",
    );
  }
  NEU.lecturerStats = lecturerStats;
  NEU.pages.lecturerStats = lecturerStats;
})((window.NEU = window.NEU || {}));
