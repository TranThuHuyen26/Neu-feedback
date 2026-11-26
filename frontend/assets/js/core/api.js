/* NEU Feedback — thư viện gọi backend (dùng chung cho mọi trang). */
(function () {
  "use strict";
  var API_URL = (window.NEU_API_URL || "").replace(/\/$/, ""); // để trống: backend phục vụ luôn giao diện
  var HOME = { student: "student.html", lecturer: "lecturer.html", admin: "admin.html" };

  function errorText(data, status) {
    var d = data && data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d))
      return d
        .map(function (x) {
          return (x.msg || "").replace(/^Value error, /, "");
        })
        .join(", ");
    if (status === 0) return "Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa.";
    return "Có lỗi xảy ra (mã " + status + ")";
  }

  var API = {
    token: function () {
      return localStorage.getItem("neu_token");
    },
    user: function () {
      try {
        return JSON.parse(localStorage.getItem("neu_user") || "null");
      } catch (e) {
        return null;
      }
    },
    setUser: function (u) {
      localStorage.setItem("neu_user", JSON.stringify(u));
    },

    request: async function (path, opts) {
      opts = opts || {};
      var headers = {};
      if (API.token()) headers.Authorization = "Bearer " + API.token();
      if (opts.body !== undefined) headers["Content-Type"] = "application/json";
      var res;
      try {
        res = await fetch(API_URL + path, {
          method: opts.method || "GET",
          headers: headers,
          body: opts.form
            ? opts.form
            : opts.body !== undefined
              ? JSON.stringify(opts.body)
              : undefined,
        });
      } catch (e) {
        throw new Error(errorText(null, 0));
      }
      if (opts.raw) {
        if (!res.ok) {
          var err = null; // giữ lại lời nhắn của máy chủ (ví dụ "Tệp không còn trên máy chủ")
          try {
            err = await res.json();
          } catch (e) {}
          throw new Error(errorText(err, res.status));
        }
        return res;
      }
      var data = null;
      if ((res.headers.get("content-type") || "").indexOf("json") > -1) data = await res.json();
      if (res.status === 401 && path.indexOf("/api/auth/login") !== 0) {
        API.logout(true);
        throw new Error(errorText(data, 401));
      }
      if (!res.ok) throw new Error(errorText(data, res.status));
      return data;
    },
    get: function (p) {
      return API.request(p);
    },
    post: function (p, body) {
      return API.request(p, { method: "POST", body: body === undefined ? {} : body });
    },
    patch: function (p, body) {
      return API.request(p, { method: "PATCH", body: body });
    },
    del: function (p) {
      return API.request(p, { method: "DELETE" });
    },
    form: function (p, fd) {
      return API.request(p, { method: "POST", form: fd });
    },

    login: async function (email, password) {
      var r = await API.request("/api/auth/login", {
        method: "POST",
        body: { email: email, password: password },
      });
      localStorage.setItem("neu_token", r.access_token);
      API.setUser(r.user);
      return r.user;
    },
    logout: function (expired) {
      localStorage.removeItem("neu_token");
      localStorage.removeItem("neu_user");
      if (expired)
        sessionStorage.setItem(
          "neu_toast",
          JSON.stringify({
            msg: "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại",
            type: "error",
          }),
        );
      else
        sessionStorage.setItem(
          "neu_toast",
          JSON.stringify({ msg: "Bạn đã đăng xuất", type: "success" }),
        );
      if (!/login\.html$/.test(location.pathname)) location.href = "login.html";
    },
    home: function (role) {
      return HOME[role] || "login.html";
    },
    /** Chặn trang khi chưa đăng nhập hoặc sai vai trò */
    requireRole: function (roles) {
      var u = API.user();
      if (!u || !API.token()) {
        location.replace("login.html");
        return null;
      }
      if (roles && roles.indexOf(u.role) < 0) {
        location.replace(API.home(u.role));
        return null;
      }
      return u;
    },
    /** Mở tệp cần đăng nhập (tài liệu, ảnh đính kèm): xem được thì mở tab mới, không thì tải xuống */
    openFile: async function (path, filename) {
      var res = await API.request(path, { raw: true });
      var blob = await res.blob();
      var url = URL.createObjectURL(blob);
      if (/^(image\/|application\/pdf|text\/)/.test(blob.type)) window.open(url, "_blank");
      else {
        var a = document.createElement("a");
        a.href = url;
        a.download = filename || "tai-lieu";
        a.click();
      }
      setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 60000);
    },
    /** Gọi lặp lại mỗi `ms` mili giây (tự cập nhật). Trả về hàm dừng. */
    poll: function (fn, ms) {
      fn();
      var id = setInterval(function () {
        if (!document.hidden) fn();
      }, ms || 5000);
      return function () {
        clearInterval(id);
      };
    },
    param: function (name) {
      return new URLSearchParams(location.search).get(name);
    },
  };
  window.API = API;
})();
