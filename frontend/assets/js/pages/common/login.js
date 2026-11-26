/* Trang đăng nhập. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    busy = NEU.busy,
    fail = NEU.fail;

  // ------------------------------------------------------------------ ĐĂNG NHẬP
  function loginPage() {
    var u = API.user();
    if (u && API.token()) {
      location.replace(API.home(u.role));
      return;
    }
    var pw = $("form input[type=password]");
    window.demoLogin = async function (e) {
      e.preventDefault();
      var btn = $("form button.btn");
      busy(btn, true);
      try {
        var usr = await API.login($("#email").value.trim(), pw.value);
        toastNext(
          "Đăng nhập thành công. Chào " +
            (usr.role === "lecturer" ? "Giảng viên " : "") +
            usr.full_name,
        );
        location.href = API.home(usr.role);
      } catch (err) {
        fail(err);
        busy(btn, false);
      }
      return false;
    };
    $$("[data-demo]").forEach(function (b) {
      b.addEventListener("click", function () {
        var p = b.dataset.demo.split("|");
        $("#email").value = p[0];
        pw.value = p[1];
      });
    });
  }
  NEU.loginPage = loginPage;
  NEU.pages.loginPage = loginPage;
})((window.NEU = window.NEU || {}));
