/* Trang home (lecturerHome). */
(function (NEU) {
  "use strict";
  var empty = NEU.empty,
    esc = NEU.esc,
    pct = NEU.pct,
    set = NEU.set,
    shortName = NEU.shortName,
    subjIcon = NEU.subjIcon,
    today = NEU.today,
    topStyle = NEU.topStyle,
    txt = NEU.txt;

  function hvClass(c, role, n) {
    var tl = c.timeline,
      wk = tl.current_week,
      pct = wk ? Math.round((100 * wk) / tl.week_count) : tl.label === "Đã kết thúc" ? 100 : 0,
      wait = n
        ? '<span class="hv-chip warn">' +
          n +
          (role === "lecturer" ? " chờ trả lời" : " câu hỏi đang chờ") +
          "</span>"
        : "";
    var btn =
      role === "lecturer" && n
        ? '<a class="btn primary sm" href="lecturer-class.html?class=' +
          c.id +
          '&focus=waiting">Trả lời câu hỏi</a>'
        : '<a class="btn sm" href="' +
          (role === "lecturer" ? "lecturer-class.html" : "student-class.html") +
          "?class=" +
          c.id +
          '">Vào lớp</a>';
    return (
      '<article class="hv-class"><span class="hv-ico" style="' +
      topStyle(c.id) +
      '">' +
      subjIcon(c.subject) +
      '</span><div class="hv-info"><a class="hv-name" href="' +
      (role === "lecturer" ? "lecturer-class.html" : "student-class.html") +
      "?class=" +
      c.id +
      '"><b>' +
      esc(c.code) +
      "</b> · " +
      esc(c.subject) +
      '</a><div class="hv-sub">' +
      (role === "lecturer"
        ? c.student_count + " sinh viên"
        : "Giảng viên " + esc(shortName(c.lecturer_name || ""))) +
      " · " +
      esc(wk ? (tl.unit_label || "Tuần") + " " + wk + "/" + tl.week_count : tl.label) +
      '</div><div class="hv-bar" aria-hidden="true"><i style="width:' +
      pct +
      '%"></i></div></div><div class="hv-act">' +
      wait +
      btn +
      "</div></article>"
    );
  }

  async function lecturerHome() {
    txt("today", today());
    set(
      "heroTitle",
      'Chào Giảng viên <span class="hero-name">' +
        esc(shortName(NEU.state.user.full_name)) +
        "</span>",
    );
    var r = await Promise.all([
        API.get("/api/classes"),
        API.get("/api/lecturer/summary"),
        API.get("/api/lecturer/inbox?kind=groups").catch(function () {
          return { sections: [] };
        }),
      ]),
      classes = r[0],
      sm = r[1],
      groups = [];
    r[2].sections.forEach(function (s) {
      s.items.forEach(function (g) {
        groups.push({ g: g, week: s.week_id, cls: s.class_code });
      });
    });
    if (classes[0]) txt("semTitle", "Lớp đang dạy · " + classes[0].semester);
    set(
      "heroText",
      "Có <b>" + sm.new + " câu hỏi</b> đang chờ bạn trả lời trong " + sm.classes_total + " lớp.",
    );
    set(
      "homeClasses",
      classes
        .map(function (c) {
          return hvClass(c, "lecturer", c.waiting_count);
        })
        .join("") || empty("Chưa có lớp nào. Tạo lớp ở mục Lớp giảng dạy."),
    );
    txt("tClasses", sm.classes_total);
    txt("sumNew", sm.new);
    txt("tRate", sm.answered_rate === null ? "—" : sm.answered_rate + "%");
    txt("tLive", sm.classes_in_session);
    txt("sumGroups", sm.groups);
    txt("sumFlag", sm.flagged);
    set(
      "homeGroups",
      groups
        .slice(0, 3)
        .map(function (x) {
          return (
            '<a class="hv-grp" href="lecturer-week.html?week=' +
            x.week +
            '&confirm=1"><b>Nhóm ' +
            esc(x.g.label) +
            "</b><span>" +
            x.g.questions.length +
            " câu hỏi giống nhau · " +
            Math.round(x.g.score * 100) +
            "%</span></a>"
          );
        })
        .join("") || '<p class="muted tiny">Không có nhóm nào cần xác nhận.</p>',
    );
    set(
      "homeBars",
      sm.weekly
        .map(function (w) {
          var p = w.asked ? Math.round((100 * w.answered) / w.asked) : 0;
          return (
            '<div class="hv-bcol" title="Tuần ' +
            w.week +
            ": " +
            w.answered +
            "/" +
            w.asked +
            ' đã trả lời"><em>' +
            p +
            '</em><i style="height:' +
            Math.max(p, 4) +
            '%"></i><span>T' +
            w.week +
            "</span></div>"
          );
        })
        .join("") || '<p class="muted tiny">Chưa có dữ liệu.</p>',
    );
  }
  NEU.lecturerHome = lecturerHome;
  NEU.pages.lecturerHome = lecturerHome;
})((window.NEU = window.NEU || {}));
