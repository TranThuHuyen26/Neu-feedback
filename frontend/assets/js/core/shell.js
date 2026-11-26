/* Khung chung của các trang sau đăng nhập: tên người dùng, menu, thông báo, đăng xuất. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    PAGE = NEU.PAGE,
    ago = NEU.ago,
    esc = NEU.esc,
    initLiveSearch = NEU.initLiveSearch,
    initials = NEU.initials;

  // ------------------------------------------------------------------ khung chung (tên người dùng, thông báo, đăng xuất)
  function initShell() {
    var role = document.body.classList.contains("admin")
      ? "admin"
      : document.body.classList.contains("lecturer")
        ? "lecturer"
        : "student";
    var allowed = PAGE === "profile.html" ? ["student", "lecturer"] : [role];
    NEU.state.user = API.requireRole(allowed);
    if (!NEU.state.user) return false;
    if (PAGE === "profile.html" && API.param("role") !== NEU.state.user.role) {
      location.replace("profile.html?role=" + NEU.state.user.role);
      return false;
    }
    $$(".user .name b, .ud-name").forEach(function (el) {
      el.textContent = NEU.state.user.full_name;
    });
    $$(".ud-email").forEach(function (el) {
      el.textContent = NEU.state.user.email;
    });
    $$(".user .avatar, .ud-head .avatar").forEach(function (el) {
      el.textContent = NEU.state.user.role === "admin" ? "AD" : initials(NEU.state.user.full_name);
    });
    $$('a[href="login.html"]').forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        API.logout();
      });
    });
    var um = $(".user-menu");
    if (um) {
      var ub = $(".user", um);
      ub.addEventListener("click", function (e) {
        e.stopPropagation();
        var o = um.classList.toggle("open");
        ub.setAttribute("aria-expanded", o);
      });
      document.addEventListener("click", function (e) {
        if (!um.contains(e.target)) {
          um.classList.remove("open");
          ub.setAttribute("aria-expanded", "false");
        }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") um.classList.remove("open");
      });
    }
    initNotifications();
    initLiveSearch();
    if (NEU.state.user.role === "admin")
      API.get("/api/admin/flags")
        .then(function (f) {
          var c = $("#navFlagCount");
          if (c) {
            c.textContent = f.length;
            c.hidden = !f.length;
          }
        })
        .catch(function () {});
    if (
      NEU.state.user.must_change_password &&
      PAGE !== "profile.html" &&
      NEU.state.user.role !== "admin"
    )
      toast("Bạn đang dùng mật khẩu tạm — hãy đổi mật khẩu trong Hồ sơ cá nhân");
    return true;
  }

  function initNotifications() {
    var btn = $(".notif-btn-api");
    if (!btn) return;
    var panel = document.createElement("div");
    panel.className = "notif-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Thông báo");
    btn.parentNode.appendChild(panel);
    var dot = $(".dot", btn);
    if (dot) dot.remove();
    var badge = document.createElement("span");
    badge.className = "notif-count";
    badge.hidden = true;
    btn.appendChild(badge);
    var oldest = null,
      more = false,
      loadingMore = false;
    function itemHTML(n) {
      return (
        '<a class="notif-item' +
        (n.is_read ? "" : " unread") +
        '" data-nid="' +
        n.id +
        '" href="' +
        esc(n.link || "#") +
        '"><span class="notif-dot"></span><span><b>' +
        esc(String(n.title || "").replace(/#(?=[A-Z]\d)/g, "")) +
        "</b><small>" +
        esc(n.body || "") +
        (n.body ? " · " : "") +
        ago(n.created_at) +
        "</small></span></a>"
      );
    }
    function tail() {
      return more
        ? '<p class="notif-more"><span class="typing"><i></i><i></i><i></i></span> Cuộn để tải thêm…</p>'
        : "";
    }
    async function load() {
      try {
        var r = await API.get("/api/notifications");
        badge.hidden = !r.unread;
        badge.textContent = r.unread > 9 ? "9+" : r.unread;
        btn.setAttribute(
          "aria-label",
          "Thông báo" + (r.unread ? " (" + r.unread + " chưa đọc)" : ""),
        );
        if (panel.classList.contains("open") && panel.dataset.ready) return; // đang mở để đọc/cuộn: không vẽ lại (giữ vị trí cuộn)
        oldest = r.items.length ? r.items[r.items.length - 1].id : null;
        more = r.has_more;
        panel.innerHTML =
          '<div class="between notif-head"><b>Thông báo</b>' +
          (r.unread ? '<button class="notif-read">Đánh dấu tất cả đã đọc</button>' : "") +
          "</div>" +
          '<div class="notif-list">' +
          (r.items.length
            ? r.items.map(itemHTML).join("") + tail()
            : '<p class="muted" style="padding:10px">Chưa có thông báo nào.</p>') +
          "</div>";
        panel.dataset.ready = "1";
        var rb = $(".notif-read", panel);
        if (rb)
          rb.onclick = async function (e) {
            e.stopPropagation();
            await API.post("/api/notifications/read-all");
            panel.dataset.ready = "";
            load();
          };
      } catch (e) {
        /* bỏ qua */
      }
    }
    async function loadMore() {
      // cuộn gần cuối → tải tiếp thông báo cũ hơn
      if (!more || loadingMore || !oldest) return;
      loadingMore = true;
      try {
        var r = await API.get("/api/notifications?offset=" + $$(".notif-item", panel).length);
        var list = $(".notif-list", panel),
          t = $(".notif-more", panel);
        if (t) t.remove();
        list.insertAdjacentHTML("beforeend", r.items.map(itemHTML).join(""));
        oldest = r.items.length ? r.items[r.items.length - 1].id : oldest;
        more = r.has_more;
        list.insertAdjacentHTML("beforeend", tail());
      } catch (e) {
        /* bỏ qua */
      } finally {
        loadingMore = false;
      }
    }
    panel.addEventListener(
      "scroll",
      function (e) {
        // chỉ danh sách cuộn, tiêu đề "Thông báo" đứng yên
        var l = e.target;
        if (!l.classList || !l.classList.contains("notif-list")) return;
        if (l.scrollTop + l.clientHeight > l.scrollHeight - 60) loadMore();
      },
      true,
    );
    panel.addEventListener("click", function (e) {
      // bấm vào thông báo → đánh dấu đã đọc rồi mở trang
      var a = e.target.closest(".notif-item");
      if (!a) return;
      e.preventDefault();
      API.post("/api/notifications/" + a.dataset.nid + "/read")
        .catch(function () {})
        .then(function () {
          location.href = a.getAttribute("href");
        });
    });
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = panel.classList.toggle("open");
      if (open) {
        panel.dataset.ready = "";
        load().then(function () {
          var l = $(".notif-list", panel);
          if (l) l.scrollTop = 0;
        });
      }
    });
    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && !btn.contains(e.target)) panel.classList.remove("open");
    });
    API.poll(load, 30000);
  }
  NEU.initShell = initShell;
})((window.NEU = window.NEU || {}));
