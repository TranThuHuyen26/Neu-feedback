/* Trang reports (adminReports). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ACTIONS = NEU.ACTIONS,
    confirmBox = NEU.confirmBox,
    empty = NEU.empty,
    esc = NEU.esc,
    fDM = NEU.fDM,
    fail = NEU.fail,
    md = NEU.md,
    qPlain = NEU.qPlain,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  async function adminReports() {
    var flags = [],
      current = null;
    function detail(f) {
      current = f;
      $$("#frList .fitem").forEach(function (x) {
        x.classList.toggle("active", +x.dataset.id === f.id);
      });
      set(
        "frDetail",
        '<div class="between"><div><span class="badge red">Đang chờ xử lý</span><h2>' +
          esc(f.question_code) +
          ' <span class="fl-class">' +
          esc(f.class_code) +
          '</span></h2></div><span class="tiny muted">' +
          esc(f.flagged_by) +
          " · " +
          fDM(f.created_at) +
          "</span></div>" +
          '<div class="card flagged"><div class="between"><b>Nội dung bị gắn cờ</b><span class="pill">' +
          esc(f.reason) +
          '</span></div><div class="q-md">' +
          md(f.content) +
          "</div></div>" +
          '<div class="ai-score"><span>Mức độ vi phạm (NEU AI)</span>' +
          '<div class="progress" style="color:var(--red)"><span style="width:' +
          f.ai_score +
          '%"></span></div><b>' +
          f.ai_score +
          "/100</b></div>" +
          '<h3 style="margin-top:18px">Quyết định kiểm duyệt</h3>' +
          '<textarea id="frNote" placeholder="Ghi lý do xử lý (gửi kèm thông báo cho người dùng)…" style="min-height:84px">' +
          "</textarea>" +
          '<div class="row" style="justify-content:flex-end;margin-top:10px">' +
          '<button class="btn" data-decide="dismissed">Không vi phạm</button>' +
          '<button class="btn" style="color:#9A4A07" data-decide="hidden">Ẩn nội dung</button>' +
          '<button class="btn danger" data-decide="deleted">Xóa nội dung</button></div>' +
          '<div class="trace-row"><div><b>Truy vết danh tính</b><div class="tiny muted">' +
          "Thao tác nhạy cảm, có ghi nhật ký. Chỉ dùng khi thật cần thiết.</div></div>" +
          '<button class="btn" id="frTrace">Yêu cầu truy vết</button></div>',
      );
      $("#frTrace").onclick = function () {
        $("#trReason").value = "";
        set("trResult", "");
        openModal("traceModal");
      };
    }
    async function load() {
      flags = await API.get("/api/admin/flags");
      txt("frCount", flags.length + " chờ xử lý");
      var c = $("#navFlagCount");
      if (c) {
        c.textContent = flags.length;
        c.hidden = !flags.length;
      }
      set(
        "frList",
        flags
          .map(function (f) {
            var col = f.ai_score >= 70 ? "#E5484D" : f.ai_score >= 40 ? "#F2A93B" : "#98A2B3";
            return (
              '<div class="moditem fitem" data-id="' +
              f.id +
              '" data-search="' +
              esc(f.content + " " + f.class_code + " " + f.reason) +
              '"><div class="row" style="flex-wrap:nowrap;align-items:flex-start">' +
              '<div class="score" style="background:' +
              col +
              '">' +
              f.ai_score +
              '</div><div style="min-width:0;flex:1"><div class="between"><b>' +
              esc(f.question_code) +
              '</b><span class="tiny muted">' +
              fDM(f.created_at) +
              '</span></div><p class="tiny" style="margin:4px 0">' +
              esc(qPlain(f.content)) +
              '</p><span class="pill" style="height:22px">' +
              esc(f.reason) +
              '</span> <span class="tiny muted">' +
              esc(f.class_code) +
              "</span></div></div></div>"
            );
          })
          .join("") || empty("Không có nội dung nào chờ xử lý."),
      );
      var want = +API.param("flag");
      var next =
        flags.filter(function (f) {
          return f.id === (current && current.id) || f.id === want;
        })[0] || flags[0];
      if (next) detail(next);
      else set("frDetail", empty("Đã xử lý hết nội dung gắn cờ."));
    }
    $("#frList").addEventListener("click", function (e) {
      var it = e.target.closest(".fitem");
      if (it)
        detail(
          flags.filter(function (f) {
            return f.id === +it.dataset.id;
          })[0],
        );
    });
    $("#frDetail").addEventListener("click", async function (e) {
      var b = e.target.closest("[data-decide]");
      if (!b || !current) return;
      var labels = {
        dismissed: [
          "Đóng gắn cờ?",
          "Nội dung được giữ nguyên và hiển thị lại cho Giảng viên.",
          "Không vi phạm",
        ],
        hidden: [
          "Ẩn nội dung?",
          "Nội dung bị ẩn khỏi lớp học. Người gửi nhận được thông báo.",
          "Ẩn nội dung",
        ],
        deleted: [
          "Xóa nội dung?",
          "Nội dung bị xóa khỏi lớp học. Người gửi nhận được thông báo.",
          "Xóa nội dung",
        ],
      }[b.dataset.decide];
      if (!(await confirmBox(labels[0], labels[1], labels[2]))) return;
      try {
        await API.post("/api/admin/flags/" + current.id + "/decision", {
          decision: b.dataset.decide,
          note: val("frNote") || null,
        });
        toast("Đã xử lý nội dung #" + current.question_code);
        current = null;
        load();
      } catch (err) {
        fail(err);
      }
    });
    ACTIONS.doTrace = async function () {
      var r = await API.post("/api/admin/flags/" + current.id + "/trace", {
        reason: val("trReason"),
      });
      set(
        "trResult",
        r.found
          ? '<div class="answered" style="margin-top:12px"><b>Người gửi</b><p>' +
              esc(r.user.full_name) +
              " · " +
              esc(r.user.email) +
              (r.user.admin_class ? " · " + esc(r.user.admin_class) : "") +
              '</p><p class="tiny muted">Thao tác đã được ghi vào nhật ký.</p></div>'
          : '<p class="warn-note"><span>' + esc(r.message) + "</span></p>",
      );
    };
    await load();
  }
  NEU.adminReports = adminReports;
  NEU.pages.adminReports = adminReports;
})((window.NEU = window.NEU || {}));
