/* Trang home (adminHome). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    ago = NEU.ago,
    empty = NEU.empty,
    esc = NEU.esc,
    fDM = NEU.fDM,
    fail = NEU.fail,
    ic = NEU.ic,
    num = NEU.num,
    set = NEU.set,
    trendSVG = NEU.trendSVG,
    txt = NEU.txt,
    val = NEU.val;

  // ------------------------------------------------------------------ ADMIN
  var lastOverview = null;

  async function adminHome() {
    var ovQ = ""; // bộ lọc đang chọn (giữ nguyên khi trang tự làm mới)
    function setOpts(id, html) {
      var el = $("#" + id);
      if (el.dataset.sig !== html) {
        el.innerHTML = html;
        el.dataset.sig = html;
      }
    }
    function todo(tone, icon, big, text, sub, href, btn) {
      return (
        '<div class="ov-card ' +
        tone +
        '"><span class="ov-ic">' +
        ic(icon) +
        '</span><div><b class="ov-num">' +
        big +
        '</b><p class="ov-text">' +
        text +
        '</p><p class="tiny muted">' +
        sub +
        '</p></div><a class="btn ' +
        (tone === "ok" ? "ghost" : "primary") +
        '" href="' +
        href +
        '">' +
        btn +
        "</a></div>"
      );
    }
    var NAMES = {
      create_user: "Tạo tài khoản",
      update_user: "Sửa tài khoản",
      lock_user: "Khóa tài khoản",
      unlock_user: "Mở khóa tài khoản",
      delete_user: "Xóa tài khoản",
      import_users: "Nhập tài khoản",
      flag_dismissed: "Đóng gắn cờ (không vi phạm)",
      flag_hidden: "Ẩn nội dung",
      flag_deleted: "Xóa nội dung",
      trace_identity: "Truy vết danh tính",
    };
    NEU.state.reloadFn = async function () {
      var o = (lastOverview = await API.get("/api/admin/overview" + ovQ));
      setOpts(
        "adYear",
        o.years
          .map(function (y) {
            return "<option" + (y === o.year ? " selected" : "") + ">" + esc(y) + "</option>";
          })
          .join("") || "<option>—</option>",
      );
      setOpts(
        "adSem",
        '<option value="">Cả năm học</option>' +
          o.semesters
            .map(function (x) {
              return (
                '<option value="' +
                x.term +
                '"' +
                (x.term === o.term ? " selected" : "") +
                ">" +
                esc(x.label) +
                "</option>"
              );
            })
            .join(""),
      );
      $("#adYear").value = o.year || "";
      $("#adSem").value = o.term || "";
      var Q = o.questions,
        T = o.today,
        G = o.grouping_week;
      txt(
        "adSummary",
        num(o.accounts.total) +
          " tài khoản · " +
          num(o.classes) +
          " lớp · " +
          num(Q.questions) +
          " câu hỏi" +
          (o.range.label ? " · " + o.range.label : ""),
      );
      var done = G.confirmed + G.rejected;
      set(
        "adTodo",
        todo(
          T.new_waiting ? "warn" : "ok",
          "chat",
          num(T.new_waiting),
          "câu hỏi mới hôm nay chưa trả lời",
          T.waiting
            ? "Tổng cộng " +
                num(T.waiting) +
                " câu đang chờ" +
                (T.over_48h ? ", " + num(T.over_48h) + " câu quá 48 giờ" : "")
            : "Không có câu nào đang chờ",
          "admin-stats.html#stDetail",
          "Xem ngay →",
        ) +
          todo(
            o.pending_flags ? "bad" : "ok",
            "flag",
            num(o.pending_flags),
            "nội dung bị gắn cờ cần duyệt",
            o.pending_flags ? "Sắp xếp theo điểm AI chấm" : "Hàng đợi đang trống",
            "admin-reports.html",
            "Duyệt ngay →",
          ) +
          todo(
            "ok",
            "check",
            G.accuracy == null ? "—" : G.accuracy + "%",
            "câu hỏi được AI gom nhóm thành công tuần này",
            done
              ? G.confirmed + "/" + done + " nhóm được xác nhận"
              : "Tuần này chưa có nhóm nào được Giảng viên xử lý",
            "admin-stats.html#stAI",
            "Xem chi tiết →",
          ),
      );
      var tr = o.trend;
      set("adTrend", trendSVG(tr.days));
      $("#adTrendLabel").className =
        "ov-trend " + (/Tăng/.test(tr.label) ? "up" : /Giảm/.test(tr.label) ? "down" : "flat");
      txt(
        "adTrendLabel",
        tr.label +
          (tr.change_pct == null
            ? ""
            : " (" + (tr.change_pct > 0 ? "+" : "") + tr.change_pct + "%)"),
      );
      txt("adFlagCount", o.pending_flags);
      set(
        "adFlags",
        o.top_flags
          .map(function (f) {
            return (
              '<a class="pend" href="admin-reports.html?flag=' +
              f.id +
              '"><div><b>' +
              esc(f.question_code) +
              " · " +
              esc(f.reason) +
              '</b><div class="tiny muted">' +
              esc(f.class_code) +
              " · " +
              fDM(f.created_at) +
              '</div></div><span class="sev" style="background:' +
              (f.ai_score >= 70 ? "#E5484D" : f.ai_score >= 40 ? "#F2A93B" : "#98A2B3") +
              '">' +
              f.ai_score +
              "</span></a>"
            );
          })
          .join("") || empty("Không có nội dung nào chờ xử lý."),
      );
      set(
        "adAttention",
        o.attention_classes
          .map(function (c) {
            return (
              '<a class="pend" href="admin-stats.html#stDetail"><div><b>' +
              esc(c.code) +
              " · " +
              esc(c.subject) +
              '</b><div class="tiny muted">Giảng viên ' +
              esc(c.lecturer) +
              '</div></div><span class="ov-wait">' +
              c.waiting +
              " chờ</span></a>"
            );
          })
          .join("") || empty("Chưa có lớp nào tồn đọng câu hỏi."),
      );
      set(
        "adActivity",
        o.recent_activity
          .map(function (x) {
            return (
              '<p><span class="dot" style="background:' +
              (/lock|delete|hidden|trace/.test(x.action) ? "var(--red)" : "var(--green)") +
              '"></span><span><b>' +
              esc(NAMES[x.action] || x.action) +
              '</b><br><span class="muted">' +
              esc(x.target) +
              " · " +
              esc(x.actor) +
              "</span></span><em>" +
              ago(x.created_at) +
              "</em></p>"
            );
          })
          .join("") || empty("Chưa có hoạt động nào."),
      );
    };
    await NEU.state.reloadFn();
    $("#adYear").onchange = function () {
      ovQ = "?year=" + encodeURIComponent(val("adYear"));
      NEU.state.reloadFn().catch(fail);
    };
    $("#adSem").onchange = function () {
      ovQ =
        "?year=" +
        encodeURIComponent(val("adYear")) +
        (val("adSem") ? "&term=" + val("adSem") : "");
      NEU.state.reloadFn().catch(fail);
    };
  }
  NEU.adminHome = adminHome;
  NEU.pages.adminHome = adminHome;
})((window.NEU = window.NEU || {}));
