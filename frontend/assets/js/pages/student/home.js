/* Trang home (studentHome). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    ago = NEU.ago,
    empty = NEU.empty,
    esc = NEU.esc,
    ic = NEU.ic,
    pct = NEU.pct,
    set = NEU.set,
    shortName = NEU.shortName,
    subjIcon = NEU.subjIcon,
    topStyle = NEU.topStyle,
    txt = NEU.txt;

  function shClass(c, n) {
    var tl = c.timeline,
      wk = tl.current_week,
      pct = wk ? Math.round((100 * wk) / tl.week_count) : tl.label === "Đã kết thúc" ? 100 : 0,
      href = "student-class.html?class=" + c.id;
    return (
      '<article class="sh-class"><span class="sh-ico" style="' +
      topStyle(c.id) +
      '">' +
      subjIcon(c.subject) +
      '</span><div class="sh-info"><a class="sh-name" href="' +
      href +
      '">' +
      esc(c.code) +
      '</a><div class="sh-sub">' +
      ic("grad") +
      "<span>Giảng viên: " +
      esc(shortName(c.lecturer_name || "")) +
      " · " +
      esc(c.subject) +
      '</span></div><div class="sh-prog"><div class="hv-bar" aria-hidden="true"><i style="width:' +
      pct +
      '%"></i></div><em>' +
      esc(wk ? (tl.unit_label || "Tuần") + " " + wk + "/" + tl.week_count : tl.label) +
      '</em></div></div><div class="sh-act">' +
      (n ? '<span class="sh-wait">' + ic("chat") + n + " câu hỏi đang chờ</span>" : "") +
      '<a class="sh-go-btn" href="' +
      href +
      '">Vào lớp ' +
      ic("arrow") +
      "</a></div></article>"
    );
  }

  async function studentHome() {
    set(
      "heroTitle",
      'Chào <span class="hero-name">' + esc(shortName(NEU.state.user.full_name)) + "</span> 👋",
    );
    var r = await Promise.all([
        API.get("/api/classes"),
        API.get("/api/me/summary"),
        API.get("/api/notifications?limit=5"),
      ]),
      classes = r[0],
      sm = r[1],
      acts = r[2].items || [];
    API.get("/api/health")
      .then(function (h) {
        txt("aiMode", h.ai_mode === "gemini" ? "Trực tuyến" : "Chế độ demo");
        if (h.ai_mode !== "gemini") $("#aiMode").classList.add("demo");
      })
      .catch(function () {});
    if (classes[0])
      set(
        "semTitle",
        'Lớp học của tôi<small class="sh-sem">' + esc(classes[0].semester) + "</small>",
      );
    set(
      "heroText",
      classes.length
        ? "Bạn đang học " +
            classes.length +
            " lớp, có <b>" +
            sm.waiting +
            " câu hỏi</b> đang chờ trả lời.<br>Cùng khám phá và đóng góp ý kiến nhé! Câu hỏi của bạn luôn được giữ ẩn danh."
        : "Bạn chưa có lớp nào đang học. Tham gia lớp bằng mã do Giảng viên cung cấp.",
    );
    set(
      "recentClasses",
      classes
        .map(function (c) {
          return shClass(c, (sm.waiting_by_class || {})[c.id]);
        })
        .join("") || empty('Bạn chưa tham gia lớp nào — bấm "Tham gia bằng mã lớp".'),
    );
    set(
      "activity",
      acts
        .map(function (n) {
          var rep = /trả lời|phản hồi/i.test(n.title);
          return (
            '<a class="sh-act-row' +
            (n.is_read ? "" : " new") +
            '" href="' +
            esc(n.link || "#") +
            '"><span class="sh-ai-ico">' +
            ic("chat") +
            '</span><span class="sh-act-t"><b>' +
            esc(n.title) +
            "</b><small>" +
            esc(n.body ? n.body : ago(n.created_at)) +
            (n.body ? " · " + esc(ago(n.created_at)) : "") +
            "</small></span>" +
            (rep ? '<span class="sh-done">' + ic("check") + "Đã phản hồi</span>" : "") +
            ic("chev").replace('class="ico"', 'class="ico sh-chev"') +
            "</a>"
          );
        })
        .join("") || empty("Chưa có hoạt động nào."),
    );
  }
  NEU.studentHome = studentHome;
  NEU.pages.studentHome = studentHome;
})((window.NEU = window.NEU || {}));
