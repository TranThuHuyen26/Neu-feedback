/* Trang accounts (adminAccounts). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ACTIONS = NEU.ACTIONS,
    TONE = NEU.TONE,
    ago = NEU.ago,
    confirmBox = NEU.confirmBox,
    d = NEU.d,
    empty = NEU.empty,
    esc = NEU.esc,
    fail = NEU.fail,
    ic = NEU.ic,
    initials = NEU.initials,
    kpi = NEU.kpi,
    num = NEU.num,
    reload = NEU.reload,
    semFilterHTML = NEU.semFilterHTML,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  var acPage = 1,
    acTotal = 0;

  async function adminAccounts() {
    var facs = await API.get("/api/admin/faculties");
    $("#acFac").insertAdjacentHTML(
      "beforeend",
      facs
        .map(function (f) {
          return "<option>" + esc(f) + "</option>";
        })
        .join(""),
    );
    set(
      "facList",
      facs
        .map(function (f) {
          return '<option value="' + esc(f) + '">';
        })
        .join(""),
    );
    NEU.state.reloadFn = async function () {
      var o = await API.get("/api/admin/overview");
      set(
        "acKpis",
        kpi(num(o.accounts.students), "Sinh viên", "grad", "blue") +
          kpi(num(o.accounts.lecturers), "Giảng viên", "monitor", "teal") +
          kpi(num(o.accounts.locked), "Tài khoản đang khóa", "lock", "red"),
      );
      txt("acSub", num(o.accounts.total) + " tài khoản sinh viên và Giảng viên.");
      var q = ["page=" + acPage, "size=15"];
      if (val("acQ")) q.push("q=" + encodeURIComponent(val("acQ")));
      if (val("acRole")) q.push("role=" + val("acRole"));
      if (val("acFac")) q.push("faculty=" + encodeURIComponent(val("acFac")));
      if (val("acStatus")) q.push("status_filter=" + val("acStatus"));
      var r = await API.get("/api/admin/users?" + q.join("&"));
      acTotal = r.total;
      var pages = Math.max(1, Math.ceil(r.total / r.size));
      txt("acCount", r.total + " kết quả");
      txt("acPage", "Trang " + r.page + " / " + pages);
      $("#acPrev").disabled = r.page <= 1;
      $("#acNext").disabled = r.page >= pages;
      set(
        "acRows",
        r.items
          .map(function (u, i) {
            var t = TONE[["blue", "teal", "amber", "violet", "green"][u.id % 5]];
            return (
              "<tr" +
              (u.is_locked ? ' class="is-locked"' : "") +
              '><td><div class="row" style="flex-wrap:nowrap"><span class="avatar" style="background:' +
              t[0] +
              ";color:" +
              t[1] +
              '">' +
              initials(u.full_name) +
              "</span><div><b>" +
              esc(u.full_name) +
              '</b><div class="meta">' +
              esc(u.email) +
              "</div></div></div></td>" +
              "<td>" +
              (u.role === "lecturer" ? "Giảng viên" : "Sinh viên") +
              "</td><td>" +
              esc(u.faculty || "—") +
              "</td><td>" +
              (u.is_locked
                ? '<span class="badge red">Đã khóa</span>'
                : '<span class="badge">Hoạt động</span>') +
              "</td>" +
              '<td class="muted">' +
              (u.last_active_at ? ago(u.last_active_at) : "Chưa đăng nhập") +
              '</td><td><div class="actions" style="justify-content:flex-end;flex-wrap:nowrap">' +
              '<button class="btn sm lock-btn' +
              (u.is_locked ? " unlock" : "") +
              '" data-lock-user="' +
              u.id +
              '" data-locked="' +
              (u.is_locked ? 1 : 0) +
              '" data-name="' +
              esc(u.full_name) +
              '">' +
              ic("lock") +
              (u.is_locked ? "Mở khóa" : "Khóa") +
              "</button>" +
              '<button class="btn sm icon-only" title="Sửa" aria-label="Sửa" data-edit-user=\'' +
              esc(JSON.stringify(u)) +
              "'>" +
              ic("edit") +
              "</button>" +
              '<button class="btn danger sm icon-only" title="Xóa" aria-label="Xóa" data-del-user="' +
              u.id +
              '" data-name="' +
              esc(u.full_name) +
              '">' +
              ic("trash") +
              "</button></div></td></tr>"
            );
          })
          .join("") ||
          '<tr><td colspan="6">' + empty("Không có tài khoản nào khớp bộ lọc.") + "</td></tr>",
      );
    };
    var timer = null;
    $("#acQ").addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        acPage = 1;
        reload();
      }, 350);
    });
    ["acRole", "acFac", "acStatus"].forEach(function (id) {
      $("#" + id).onchange = function () {
        acPage = 1;
        reload();
      };
    });
    $("#acPrev").onclick = function () {
      acPage--;
      reload();
    };
    $("#acNext").onclick = function () {
      acPage++;
      reload();
    };
    document.addEventListener("click", async function (e) {
      var lk = e.target.closest("[data-lock-user]"),
        ed = e.target.closest("[data-edit-user]"),
        dl = e.target.closest("[data-del-user]");
      try {
        if (lk) {
          var locked = lk.dataset.locked === "1";
          if (
            !locked &&
            !(await confirmBox(
              "Khóa tài khoản?",
              lk.dataset.name + " sẽ không đăng nhập được cho đến khi được mở khóa.",
              "Khóa",
            ))
          )
            return;
          await API.post(
            "/api/admin/users/" + lk.dataset.lockUser + (locked ? "/unlock" : "/lock"),
          );
          toast((locked ? "Đã mở khóa " : "Đã khóa ") + lk.dataset.name);
          reload();
        }
        if (ed) {
          var u = JSON.parse(ed.dataset.editUser);
          $("#afId").value = u.id;
          $("#afName").value = u.full_name;
          $("#afEmail").value = u.email;
          $("#afRole").value = u.role;
          $("#afFac").value = u.faculty || "";
          $("#afClass").value = u.admin_class || "";
          $("#accountModal .modal-title").textContent = "Sửa tài khoản";
          $("#afNote").hidden = true;
          openModal("accountModal");
        }
        if (dl) {
          if (
            !(await confirmBox(
              "Xóa tài khoản?",
              dl.dataset.name +
                " sẽ bị xóa vĩnh viễn. Câu hỏi đã gửi vẫn được giữ ẩn danh. Nếu chỉ muốn tạm ngừng, hãy dùng Khóa.",
              "Xóa tài khoản",
            ))
          )
            return;
          await API.del("/api/admin/users/" + dl.dataset.delUser);
          toast("Đã xóa tài khoản");
          reload();
        }
      } catch (err) {
        fail(err);
      }
    });
    await adminByClassInit(NEU.state.reloadFn);
    if (API.param("mode") !== "class") await NEU.state.reloadFn();
  }

  // ---------------------------------------------------------------- Admin: tài khoản THEO LỚP HỌC PHẦN
  var abcId = null,
    abcClasses = [],
    abcDetail = null,
    abcTimer = null;

  function abcMode(mode) {
    var cls = mode === "class";
    $("#acAll").hidden = cls;
    $("#acByClass").hidden = !cls;
    $$("[data-ac-mode]").forEach(function (b) {
      b.classList.toggle("on", b.dataset.acMode === mode);
      b.setAttribute("aria-selected", b.dataset.acMode === mode);
    });
    var tools = $$(".ph-actions .btn");
    tools.forEach(function (b) {
      b.hidden = cls;
    });
    try {
      history.replaceState(
        null,
        "",
        cls ? "?mode=class" + (abcId ? "&class=" + abcId : "") : location.pathname,
      );
    } catch (e) {}
    NEU.state.reloadFn = cls ? abcReload : acReloadAll;
    NEU.state.reloadFn().catch(fail);
  }

  var acReloadAll = null;

  async function abcLoadList() {
    var sem = val("abcSem"),
      q = val("abcQ").trim();
    var path = "/api/admin/classes?" + (sem && sem !== "all" ? "semester_id=" + sem + "&" : "");
    abcClasses = await API.get(path + (q ? "q=" + encodeURIComponent(q) : ""));
    set(
      "abcList",
      abcClasses
        .map(function (c) {
          return (
            '<button type="button" class="abc-item' +
            (c.id === abcId ? " on" : "") +
            '" data-abc-class="' +
            c.id +
            '"><b>' +
            esc(c.code) +
            "</b><span>" +
            esc(c.subject) +
            "</span><small>" +
            c.student_count +
            " sinh viên · " +
            esc((c.lecturer && c.lecturer.full_name) || "Chưa có giảng viên") +
            "</small></button>"
          );
        })
        .join("") || empty("Không có lớp nào khớp bộ lọc."),
    );
  }

  function abcStudentsHTML(d) {
    var q = ($("#abcSq") && $("#abcSq").value.trim().toLowerCase()) || "";
    var rows = d.students.filter(function (s) {
      return !q || (s.full_name + " " + s.email).toLowerCase().indexOf(q) >= 0;
    });
    return (
      rows
        .map(function (s) {
          var tn = TONE[["blue", "teal", "amber", "violet", "green"][s.id % 5]];
          return (
            "<tr" +
            (s.is_locked ? ' class="is-locked"' : "") +
            '><td><div class="row" style="flex-wrap:nowrap"><span class="avatar" style="background:' +
            tn[0] +
            ";color:" +
            tn[1] +
            '">' +
            initials(s.full_name) +
            "</span><div><b>" +
            esc(s.full_name) +
            '</b><div class="meta">' +
            esc(s.email) +
            "</div></div></div></td><td>" +
            esc(s.admin_class || s.faculty || "—") +
            "</td><td>" +
            (s.is_locked
              ? '<span class="badge red">Đã khóa</span>'
              : '<span class="badge">Hoạt động</span>') +
            '</td><td><div class="actions" style="justify-content:flex-end;flex-wrap:nowrap">' +
            '<button class="btn sm lock-btn' +
            (s.is_locked ? " unlock" : "") +
            '" data-lock-user="' +
            s.id +
            '" data-locked="' +
            (s.is_locked ? 1 : 0) +
            '" data-name="' +
            esc(s.full_name) +
            '">' +
            ic("lock") +
            (s.is_locked ? "Mở khóa" : "Khóa") +
            '</button><button class="btn sm danger" data-abc-remove="' +
            s.id +
            '" data-name="' +
            esc(s.full_name) +
            '" title="Gỡ khỏi lớp này (tài khoản vẫn còn)">Gỡ khỏi lớp</button></div></td></tr>'
          );
        })
        .join("") ||
      '<tr><td colspan="4">' +
        empty(q ? "Không có sinh viên nào khớp." : "Lớp chưa có sinh viên nào.") +
        "</td></tr>"
    );
  }

  function abcRenderDetail(d) {
    abcDetail = d;
    var lec = d.lecturer;
    var wk = d.current_week
      ? (d.unit_label || "Tuần") + " " + d.current_week.number + " / " + d.unit_count
      : "Chưa/đã hết " + (d.unit_label || "tuần").toLowerCase();
    set(
      "abcDetail",
      '<div class="abc-head"><div><h2>' +
        esc(d.code) +
        " · " +
        esc(d.subject) +
        '</h2><p class="muted">' +
        esc(d.semester || "") +
        " · " +
        esc(wk) +
        " · " +
        d.question_count +
        " câu hỏi</p></div></div>" +
        '<div class="abc-lec"><span class="avatar">' +
        (lec ? initials(lec.full_name) : "?") +
        '</span><div class="abc-lec-t"><small>Giảng viên phụ trách</small><b>' +
        esc(lec ? lec.full_name : "Chưa có giảng viên") +
        "</b>" +
        (lec ? '<div class="meta">' + esc(lec.email) + "</div>" : "") +
        '</div><button class="btn sm" data-submit="openChangeLecturer">' +
        ic("users") +
        "Đổi giảng viên</button></div>" +
        '<div class="abc-sthead"><h3>Sinh viên <span class="muted">(' +
        d.students.length +
        ')</span></h3><div class="abc-stools"><label class="search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="abcSq" placeholder="Tìm trong lớp…" aria-label="Tìm sinh viên trong lớp"/></label>' +
        '<button class="btn primary sm" data-modal="addStudentsModal">' +
        ic("plus") +
        "Thêm sinh viên</button></div></div>" +
        '<div class="table-wrap" style="border:0"><table><thead><tr><th>Sinh viên</th><th>Lớp / khoa</th><th>Trạng thái</th><th style="text-align:right">Thao tác</th></tr></thead><tbody id="abcRows">' +
        abcStudentsHTML(d) +
        "</tbody></table></div>" +
        '<p class="tiny muted abc-note">Gỡ khỏi lớp chỉ bỏ sinh viên khỏi lớp này, tài khoản và các lớp khác vẫn còn. Câu hỏi đã gửi vẫn được giữ ẩn danh.</p>',
    );
  }

  async function abcReload() {
    await abcLoadList();
    if (abcId) {
      var typing = document.activeElement && document.activeElement.id === "abcSq";
      var d = await API.get("/api/admin/classes/" + abcId);
      if (!typing) abcRenderDetail(d);
      else abcDetail = d;
    }
  }

  async function adminByClassInit(reloadAll) {
    acReloadAll = reloadAll;
    var sems = await API.get("/api/semesters");
    set("abcSemWrap", semFilterHTML("abcSem", sems, false, false));
    var want = +API.param("class") || null;
    if (want) abcId = want;
    $("#abcSem").onchange = function () {
      abcLoadList().catch(fail);
    };
    $("#abcQ").addEventListener("input", function () {
      clearTimeout(abcTimer);
      abcTimer = setTimeout(function () {
        abcLoadList().catch(fail);
      }, 300);
    });
    document.addEventListener("input", function (e) {
      if (e.target && e.target.id === "abcSq" && abcDetail)
        set("abcRows", abcStudentsHTML(abcDetail));
    });
    document.addEventListener("click", async function (e) {
      var m = e.target.closest("[data-ac-mode]"),
        c = e.target.closest("[data-abc-class]"),
        rm = e.target.closest("[data-abc-remove]");
      try {
        if (m) abcMode(m.dataset.acMode);
        if (c) {
          abcId = +c.dataset.abcClass;
          try {
            history.replaceState(null, "", "?mode=class&class=" + abcId);
          } catch (er) {}
          await abcReload();
        }
        if (rm) {
          if (
            !(await confirmBox(
              "Gỡ sinh viên khỏi lớp?",
              rm.dataset.name +
                " sẽ không còn thấy lớp " +
                abcDetail.code +
                ". Tài khoản và các lớp khác vẫn giữ nguyên.",
              "Gỡ khỏi lớp",
            ))
          )
            return;
          await API.del("/api/admin/classes/" + abcId + "/students/" + rm.dataset.abcRemove);
          toast("Đã gỡ " + rm.dataset.name + " khỏi lớp");
          await abcReload();
        }
      } catch (err) {
        fail(err);
      }
    });
    if (API.param("mode") === "class") abcMode("class");
  }

  ACTIONS.addClassStudents = async function () {
    var emails = val("asEmails")
      .split(/[\s,;]+/)
      .map(function (x) {
        return x.trim();
      })
      .filter(Boolean);
    if (!emails.length) {
      toast("Vui lòng nhập ít nhất một email", "error");
      return;
    }
    var r = await API.post("/api/admin/classes/" + abcId + "/students", { emails: emails });
    closeModal("addStudentsModal");
    $("#asEmails").value = "";
    var msg = "Đã thêm " + r.added.length + " sinh viên";
    if (r.already_in_class.length) msg += " · " + r.already_in_class.length + " đã có trong lớp";
    if (r.not_found.length) msg += " · không tìm thấy: " + r.not_found.join(", ");
    toast(msg, r.not_found.length ? "error" : undefined);
    await abcReload();
  };

  ACTIONS.openChangeLecturer = async function () {
    var list = await API.get("/api/admin/lecturers"),
      cur = abcDetail && abcDetail.lecturer ? abcDetail.lecturer.id : null;
    set(
      "clLecturer",
      list
        .map(function (u) {
          return (
            '<option value="' +
            u.id +
            '"' +
            (u.id === cur ? " selected" : "") +
            ">" +
            esc(u.full_name) +
            " — " +
            esc(u.email) +
            "</option>"
          );
        })
        .join(""),
    );
    openModal("changeLecturerModal");
  };

  ACTIONS.changeClassLecturer = async function () {
    await API.patch("/api/admin/classes/" + abcId + "/lecturer", {
      lecturer_id: +val("clLecturer"),
    });
    closeModal("changeLecturerModal");
    toast("Đã đổi giảng viên phụ trách");
    await abcReload();
  };

  ACTIONS.newAccount = function () {
    ["afId", "afName", "afEmail", "afFac", "afClass"].forEach(function (id) {
      $("#" + id).value = "";
    });
    $("#afRole").value = "student";
    $("#accountModal .modal-title").textContent = "Thêm tài khoản";
    $("#afNote").hidden = false;
    openModal("accountModal");
  };

  ACTIONS.saveAccount = async function () {
    var body = {
      full_name: val("afName"),
      email: val("afEmail"),
      role: val("afRole"),
      faculty: val("afFac"),
      admin_class: val("afClass") || null,
    };
    if (val("afId")) {
      await API.patch("/api/admin/users/" + val("afId"), body);
      closeModal("accountModal");
      toast("Đã lưu tài khoản");
    } else {
      var r = await API.post("/api/admin/users", body);
      closeModal("accountModal");
      set(
        "pwText",
        "<b>" +
          esc(r.user.email) +
          "</b><br>Mật khẩu tạm: <code>" +
          esc(r.temp_password) +
          "</code>",
      );
      openModal("pwModal");
    }
    reload();
  };

  ACTIONS.downloadTemplate = function () {
    var csv = "\ufefffull_name,email,role,faculty,admin_class\n";
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "mau-nhap-tai-khoan.csv";
    a.click();
  };

  ACTIONS.importAccounts = async function () {
    var f = $("#imFile").files[0];
    if (!f) {
      toast("Vui lòng chọn file");
      return;
    }
    var fd = new FormData();
    fd.append("file", f);
    var r = await API.form("/api/admin/users/import", fd);
    set(
      "imResult",
      '<p class="empty-note" style="margin-top:14px">Đã tạo ' +
        r.created.length +
        " tài khoản · " +
        r.errors.length +
        " dòng lỗi</p>" +
        (r.created.length
          ? '<div class="table-wrap" style="margin-top:10px;max-height:200px"><table><thead><tr><th>Email</th><th>Mật khẩu tạm</th></tr></thead><tbody>' +
            r.created
              .map(function (x) {
                return (
                  "<tr><td>" +
                  esc(x.email) +
                  "</td><td><code>" +
                  esc(x.temp_password) +
                  "</code></td></tr>"
                );
              })
              .join("") +
            "</tbody></table></div>"
          : "") +
        (r.errors.length
          ? '<ul class="tiny" style="color:var(--red-ink)">' +
            r.errors
              .map(function (x) {
                return "<li>Dòng " + x.row + ": " + esc(x.error) + "</li>";
              })
              .join("") +
            "</ul>"
          : ""),
    );
    $("#imFile").value = "";
    reload();
  };
  NEU.adminAccounts = adminAccounts;
  NEU.pages.adminAccounts = adminAccounts;
})((window.NEU = window.NEU || {}));
