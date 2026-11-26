/* Phần dùng chung giữa các trang của Giảng viên. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ACTIONS = NEU.ACTIONS,
    confirmBox = NEU.confirmBox,
    fail = NEU.fail,
    reload = NEU.reload,
    val = NEU.val;

  // ------------------------------------------------------------------ GIẢNG VIÊN
  var classCache = {};

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-edit-class]");
    if (!b) return;
    var c = classCache[b.dataset.editClass];
    $("#ecId").value = c.id;
    $("#ecCode").value = c.code;
    $("#ecSubject").value = c.subject;
    $("#ecJoin").value = c.join_code;
    var ma = $("#editClassModal .modal-actions");
    if (ma && !$("#ecDelete"))
      ma.insertAdjacentHTML(
        "afterbegin",
        '<button class="btn danger" type="button" id="ecDelete" data-submit="deleteClass" style="margin-right:auto">' +
          "Xóa lớp</button>",
      );
    if ($("#ecDelete")) $("#ecDelete").hidden = !!(c.question_count || c.student_count);
    openModal("editClassModal");
  });

  ACTIONS.createClass = async function () {
    if (!val("ncStart")) {
      toast("Vui lòng chọn ngày bắt đầu học", "error");
      return;
    }
    var body = {
      code: val("ncCode"),
      subject: val("ncSubject"),
      start_date: val("ncStart"),
      course_type: val("ncType"),
    };
    if (!$("#ncDaysWrap").hidden)
      body.meeting_days = $$("#ncDaysWrap input:checked").map(function (x) {
        return +x.value;
      });
    var c = await API.post("/api/classes", body);
    closeModal("classModal");
    toastNext(
      "Đã tạo lớp " +
        c.code +
        " (" +
        c.unit_count +
        " " +
        c.unit_label.toLowerCase() +
        ") · mã tham gia " +
        c.join_code,
    );
    setTimeout(function () {
      location.href = "lecturer-class.html?class=" + c.id;
    }, 900);
  };

  ACTIONS.saveClass = async function () {
    await API.patch("/api/classes/" + val("ecId"), {
      code: val("ecCode"),
      subject: val("ecSubject"),
    });
    closeModal("editClassModal");
    toast("Đã lưu thay đổi");
    reload();
  };

  ACTIONS.regenCode = async function () {
    if (
      !(await confirmBox(
        "Tạo mã tham gia mới?",
        "Mã cũ sẽ không dùng được nữa. Sinh viên đã tham gia vẫn ở trong lớp.",
        "Tạo mã mới",
      ))
    )
      return;
    var r = await API.post("/api/classes/" + val("ecId") + "/join-code");
    $("#ecJoin").value = r.join_code;
    toast("Mã mới: " + r.join_code);
    reload(true);
  };

  ACTIONS.deleteClass = async function () {
    if (
      !(await confirmBox(
        "Xóa hẳn lớp học?",
        "Lớp còn trống (chưa có sinh viên và câu hỏi) nên có thể xóa hẳn. Thao tác này không hoàn tác được.",
        "Xóa lớp",
      ))
    )
      return;
    await API.del("/api/classes/" + val("ecId"));
    closeModal("editClassModal");
    if (/lecturer-class\.html/.test(location.pathname)) {
      toastNext("Đã xóa lớp học");
      location.href = "lecturer-classes.html";
    } else {
      toast("Đã xóa lớp học");
      reload();
    }
  };

  document.addEventListener("click", function (e) {
    // thẻ lớp (div) bấm cả thẻ để vào lớp, trừ khi bấm nút bên trong
    var cd = e.target.closest(".lc-card[data-href]");
    if (!cd || e.target.closest("button, a, [data-copy]")) return;
    location.href = cd.dataset.href;
  });

  document.addEventListener("keydown", function (e) {
    var cd = e.target.closest && e.target.closest(".lc-card[data-href]");
    if (cd && e.key === "Enter" && e.target === cd) location.href = cd.dataset.href;
  });

  document.addEventListener("click", async function (e) {
    var r = e.target.closest("[data-rename]");
    if (r) {
      $("#rnId").value = r.dataset.rename;
      $("#rnName").value = r.dataset.name;
      openModal("renameModal");
      return;
    }
    var dd = e.target.closest("[data-del-doc]");
    if (dd) {
      if (
        !(await confirmBox(
          "Xóa tài liệu?",
          "“" +
            dd.dataset.name +
            "” sẽ bị xóa. Sinh viên và NEU AI không dùng được tài liệu này nữa.",
          "Xóa tài liệu",
        ))
      )
        return;
      try {
        await API.del("/api/materials/" + dd.dataset.delDoc);
        toast("Đã xóa tài liệu");
        reload();
      } catch (err) {
        fail(err);
      }
    }
  });

  ACTIONS.renameDoc = async function () {
    await API.patch("/api/materials/" + val("rnId"), { filename: val("rnName") });
    closeModal("renameModal");
    toast("Đã đổi tên tài liệu");
    reload();
  };

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (!b) return;
    if (navigator.clipboard) navigator.clipboard.writeText(b.dataset.copy).catch(function () {});
  });
  NEU.classCache = classCache;
})((window.NEU = window.NEU || {}));
