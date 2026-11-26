/* Trang hồ sơ cá nhân và đổi mật khẩu. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    ACTIONS = NEU.ACTIONS,
    esc = NEU.esc,
    initShell = NEU.initShell,
    initials = NEU.initials,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  // Hồ sơ
  async function profilePage() {
    var u = await API.get("/api/auth/me");
    API.setUser(u);
    $("#pfAvatar").textContent = initials(u.full_name);
    txt("pfTitle", u.full_name);
    txt("pfRole", u.faculty ? "Khoa " + u.faculty : "");
    $("#pfName").value = u.full_name;
    $("#pfEmail").value = u.email;
    set(
      "pfInfo",
      '<div class="info-row"><span>Khoa</span><b>' +
        esc(u.faculty || "—") +
        "</b></div>" +
        (u.admin_class
          ? '<div class="info-row"><span>Lớp hành chính</span><b>' +
            esc(u.admin_class) +
            "</b></div>"
          : ""),
    );
    $$("[data-role-panel]").forEach(function (p) {
      p.hidden = true;
    });
  }

  ACTIONS.saveProfile = async function () {
    var u = await API.patch("/api/auth/me", { full_name: val("pfName") });
    API.setUser(u);
    toast("Đã lưu hồ sơ");
    profilePage();
    initShell();
  };

  ACTIONS.changePassword = async function () {
    await API.post("/api/auth/change-password", {
      old_password: $("#pwOld").value,
      new_password: $("#pwNew").value,
    });
    $("#pwOld").value = $("#pwNew").value = "";
    var u = API.user();
    u.must_change_password = false;
    API.setUser(u);
    toast("Đã đổi mật khẩu");
  };
  NEU.profilePage = profilePage;
  NEU.pages.profilePage = profilePage;
})((window.NEU = window.NEU || {}));
