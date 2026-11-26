/* Điểm khởi động: xem đang ở trang nào thì chạy hàm tương ứng. */
(function (NEU) {
  "use strict";
  var $$ = NEU.$$,
    PAGE = NEU.PAGE,
    empty = NEU.empty,
    fail = NEU.fail,
    initShell = NEU.initShell;

  // ------------------------------------------------------------------ khởi động
  var CONTROLLERS = {
    "student.html": NEU.pages.studentHome,
    "student-classes.html": NEU.pages.studentClasses,
    "student-courses.html": NEU.pages.studentClasses,
    "student-class.html": NEU.pages.studentClass,
    "student-week.html": NEU.pages.studentWeek,
    "student-feedback.html": NEU.pages.studentFeedback,
    "student-ai.html": NEU.pages.studentAI,
    "profile.html": NEU.pages.profilePage,
    "lecturer.html": NEU.pages.lecturerHome,
    "lecturer-classes.html": NEU.pages.lecturerClasses,
    "lecturer-class.html": NEU.pages.lecturerClass,
    "lecturer-week.html": NEU.pages.lecturerWeek,
    "lecturer-materials.html": NEU.pages.lecturerMaterials,
    "lecturer-inbox.html": NEU.pages.lecturerInbox,
    "lecturer-stats.html": NEU.pages.lecturerStats,
    "admin.html": NEU.pages.adminHome,
    "admin-stats.html": NEU.pages.adminStats,
    "admin-accounts.html": NEU.pages.adminAccounts,
    "admin-reports.html": NEU.pages.adminReports,
  };

  if (PAGE === "login.html") {
    NEU.pages.loginPage();
    return;
  }

  if (!document.body.hasAttribute("data-api")) return;

  if (!initShell()) return;

  if (NEU.state.user.role === "student") NEU.floatingAI();

  var ctl = CONTROLLERS[PAGE];

  if (ctl)
    ctl().catch(function (e) {
      fail(e);
      $$(".loading").forEach(function (x) {
        x.outerHTML = empty(e.message);
      });
    });
})((window.NEU = window.NEU || {}));
