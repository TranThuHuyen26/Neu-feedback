/* Trang class (lecturerClass). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    ACTIONS = NEU.ACTIONS,
    WEEK_LABEL = NEU.WEEK_LABEL,
    bars = NEU.bars,
    classCache = NEU.classCache,
    confirmBox = NEU.confirmBox,
    dur = NEU.dur,
    empty = NEU.empty,
    esc = NEU.esc,
    fDate = NEU.fDate,
    fail = NEU.fail,
    ic = NEU.ic,
    initials = NEU.initials,
    kpi = NEU.kpi,
    pct = NEU.pct,
    pickClass = NEU.pickClass,
    reload = NEU.reload,
    set = NEU.set,
    timelineBanner = NEU.timelineBanner,
    txt = NEU.txt,
    val = NEU.val,
    weekList = NEU.weekList;

  function wkBadge(w) {
    return '<span class="wk-status ' + w.status + '">' + WEEK_LABEL[w.status] + "</span>";
  }

  function statsHTML(st) {
    var shown = st.weeks.filter(function (w) {
      return w.status !== "upcoming";
    });
    var rows = shown
      .slice()
      .reverse()
      .map(function (w) {
        return (
          '<tr><td><a href="lecturer-week.html?week=' +
          w.id +
          '"><b>Tuần ' +
          w.number +
          "</b></a>" +
          (w.title ? '<div class="meta">' + esc(w.title) + "</div>" : "") +
          "</td><td>" +
          w.question_count +
          "</td><td>" +
          pct(w.answered_count, w.question_count) +
          "%</td><td>" +
          (w.review_count || 0) +
          "</td><td>" +
          dur(w.avg_response_seconds) +
          "</td><td>" +
          wkBadge(w) +
          "</td></tr>"
        );
      })
      .join("");
    var t = st.question_count;
    return (
      '<div class="grid4">' +
      kpi(t, "Câu hỏi", "chat", "blue") +
      kpi(
        st.answer_rate + "%",
        "Tỷ lệ phản hồi",
        "check",
        "green",
        st.answered_count + "/" + t + " câu",
      ) +
      kpi(
        dur(st.avg_response_seconds),
        "Phản hồi trung bình",
        "clock",
        "amber",
        "Từ lúc hỏi đến lúc trả lời",
      ) +
      kpi(
        st.group_count,
        "Nhóm tương đồng",
        "group",
        "teal",
        (st.review_count || 0) + " câu chờ duyệt",
      ) +
      "</div>" +
      '<div class="grid" style="grid-template-columns:1.5fr 1fr;margin-top:18px;align-items:start">' +
      '<div class="panel"><div class="between"><h3>Câu hỏi theo tuần</h3><span class="tiny muted">' +
      '<span class="legend" style="background:var(--accent)"></span>' +
      'Đã phản hồi　<span class="legend" style="background:var(--amber);margin-left:10px"></span>' +
      'Chưa phản hồi</span></div><div class="stackbars">' +
      bars(
        shown.map(function (w) {
          return { label: "T" + w.number, total: w.question_count, done: w.answered_count };
        }),
      ) +
      "</div></div>" +
      '<div class="panel"><h3>Trạng thái xử lý</h3>' +
      [
        ["Đã phản hồi", st.answered_count, "var(--green)"],
        ["Chưa phản hồi", st.waiting_count, "var(--amber)"],
        ["Đã gắn cờ", st.flagged_count, "var(--red)"],
      ]
        .map(function (x) {
          return (
            "<p>" +
            x[0] +
            ' <b style="float:right">' +
            x[1] +
            " · " +
            pct(x[1], t) +
            '%</b></p><div class="progress"' +
            (x[2] ? ' style="color:' + x[2] + '"' : "") +
            '><span style="width:' +
            pct(x[1], t) +
            '%"></span></div>'
          );
        })
        .join("") +
      '</div></div><div class="section-title"><h2>Chi tiết theo tuần</h2></div><div class="table-wrap">' +
      "<table><thead><tr><th>Tuần</th><th>Câu hỏi</th><th>Đã phản hồi</th><th>Chờ duyệt</th><th>" +
      "Phản hồi TB</th><th>Trạng thái</th></tr></thead><tbody>" +
      (rows || '<tr><td colspan="6">' + empty("Chưa có tuần nào đã học.") + "</td></tr>") +
      "</tbody></table></div>"
    );
  }

  async function lecturerClass() {
    var classes = await API.get("/api/classes");
    var id = await pickClass(classes);
    if (!id) {
      set("lcBanner", empty("Chưa có lớp nào."));
      return;
    }
    NEU.state.reloadFn = async function () {
      var r = await Promise.all([
        API.get("/api/classes/" + id),
        API.get("/api/classes/" + id + "/weeks"),
        API.get("/api/materials?class_id=" + id),
        API.get("/api/classes/" + id + "/students"),
        API.get("/api/classes/" + id + "/stats"),
      ]);
      var c = r[0],
        tl = r[1].timeline,
        weeks = r[1].weeks,
        docs = r[2],
        studs = r[3],
        st = r[4];
      classCache[c.id] = c;
      txt("lcTitle", c.subject);
      document.title = c.subject + " | NEU Feedback";
      set(
        "lcMeta",
        esc(c.code) +
          " · " +
          esc(c.semester) +
          ' · Mã tham gia <span class="code">' +
          esc(c.join_code) +
          '</span> <button class="btn sm icon-only" aria-label="Sao chép mã" data-copy="' +
          esc(c.join_code) +
          '">' +
          ic("copy") +
          "</button>",
      );
      $("#lcEdit").setAttribute("data-edit-class", c.id);
      txt("joinHint", c.join_code);
      txt("cStud", studs.length);
      var wt = st.waiting_count || 0;
      $("#lcMeta").insertAdjacentHTML(
        "beforeend",
        '<span class="lc-counts"> · ' +
          studs.length +
          " sinh viên · " +
          st.question_count +
          " câu hỏi" +
          (wt ? ' (<b class="warn-ink">' + wt + " chờ trả lời</b>)" : "") +
          "</span>",
      );
      set("lcBanner", timelineBanner(c, tl, "lecturer", studs.length));
      set("weekGrid", weekList(weeks, "lecturer", docs, null, c, tl));
      set(
        "lcStudents",
        studs
          .map(function (s) {
            return (
              '<tr data-search="' +
              esc(s.full_name + " " + s.email) +
              '"><td><div class="row" style="flex-wrap:nowrap"><span class="avatar">' +
              initials(s.full_name) +
              "</span><b>" +
              esc(s.full_name) +
              '</b></div></td><td class="muted">' +
              esc(s.email) +
              "</td><td>" +
              esc(s.admin_class || "—") +
              '</td><td class="muted">' +
              fDate(s.joined_at) +
              '</td><td style="text-align:right"><button class="btn danger sm" data-rm-student="' +
              s.id +
              '" data-name="' +
              esc(s.full_name) +
              '">Xóa khỏi lớp</button></td></tr>'
            );
          })
          .join("") ||
          '<tr><td colspan="5">' +
            empty("Chưa có sinh viên. Gửi mã tham gia " + c.join_code + " cho sinh viên.") +
            "</td></tr>",
      );
      set("lcStats", statsHTML(st));
    };
    await NEU.state.reloadFn();
    if (API.param("tab") === "weeks") tabs($("[data-target=lc2]"), "lc");
    document.addEventListener("click", async function (e) {
      var et = e.target.closest("[data-edit-title]");
      if (et) {
        $("#ttId").value = et.dataset.editTitle;
        $("#ttTitle").value = et.dataset.title || "";
        openModal("titleModal");
        $("#ttTitle").focus();
        return;
      }
      var b = e.target.closest("[data-rm-student]");
      if (b) {
        if (
          !(await confirmBox(
            "Xóa sinh viên khỏi lớp?",
            b.dataset.name + " sẽ không truy cập lớp này nữa. Câu hỏi đã gửi vẫn được giữ ẩn danh.",
            "Xóa khỏi lớp",
          ))
        )
          return;
        try {
          await API.del("/api/classes/" + id + "/students/" + b.dataset.rmStudent);
          toast("Đã xóa sinh viên khỏi lớp");
          reload();
        } catch (err) {
          fail(err);
        }
      }
    });
    ACTIONS.saveTitle = async function () {
      await API.patch("/api/weeks/" + val("ttId"), { title: val("ttTitle") });
      closeModal("titleModal");
      toast("Đã lưu tiêu đề nội dung");
      reload();
    };
    ACTIONS.addStudents = async function () {
      var emails = val("addEmails")
        .split(/[\s,;]+/)
        .filter(Boolean);
      if (!emails.length) {
        toast("Vui lòng nhập email");
        return;
      }
      var r = await API.post("/api/classes/" + id + "/students", { emails: emails });
      closeModal("addStudentModal");
      $("#addEmails").value = "";
      toast(
        "Đã thêm " +
          r.added.length +
          " sinh viên" +
          (r.not_found.length ? " · " + r.not_found.length + " email chưa có tài khoản" : "") +
          (r.already_in_class.length ? " · " + r.already_in_class.length + " đã ở trong lớp" : ""),
      );
      reload();
    };
  }
  NEU.lecturerClass = lecturerClass;
  NEU.pages.lecturerClass = lecturerClass;
})((window.NEU = window.NEU || {}));
