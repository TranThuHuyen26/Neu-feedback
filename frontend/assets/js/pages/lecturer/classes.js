/* Trang classes (lecturerClasses). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    classCache = NEU.classCache,
    empty = NEU.empty,
    esc = NEU.esc,
    fail = NEU.fail,
    hcard = NEU.hcard,
    ic = NEU.ic,
    pad = NEU.pad,
    semFilterHTML = NEU.semFilterHTML,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  function termOf(v) {
    // giống máy chủ: tháng 7–11 Thu · 12–4 Xuân · 5–6 Hè
    var m = /^(\d{4})-(\d{2})/.exec(v || "");
    if (!m) return null;
    var y = +m[1],
      mo = +m[2];
    if (mo >= 7 && mo <= 11)
      return { term: "thu", year: y + "-" + (y + 1), label: "Học kỳ Thu " + y };
    if (mo === 12)
      return { term: "xuan", year: y + "-" + (y + 1), label: "Học kỳ Xuân " + (y + 1) };
    return mo <= 4
      ? { term: "xuan", year: y - 1 + "-" + y, label: "Học kỳ Xuân " + y }
      : { term: "he", year: y - 1 + "-" + y, label: "Học kỳ Hè " + y };
  }

  function codeChecker(input, hintAfter, semFn, excludeFn) {
    var hint = document.createElement("p");
    hint.className = "field-hint";
    hintAfter.insertAdjacentElement("afterend", hint);
    var tm = null;
    async function check() {
      var code = input.value.trim();
      if (!code) {
        hint.textContent = "";
        return;
      }
      try {
        var q =
          "/api/classes-check-code?code=" +
          encodeURIComponent(code) +
          (semFn() ? "&" + semFn() : "") +
          (excludeFn && excludeFn() ? "&exclude_id=" + excludeFn() : "");
        var r = await API.get(q);
        hint.className = "field-hint " + (r.available ? "good" : "bad");
        hint.textContent = r.available ? "✓ Tên lớp " + r.code + " dùng được" : r.message;
      } catch (e) {
        hint.textContent = "";
      }
    }
    input.addEventListener("input", function () {
      clearTimeout(tm);
      tm = setTimeout(check, 450);
    });
    input.addEventListener("blur", check);
    return function () {
      hint.textContent = "";
    };
  }

  async function lecturerClasses() {
    var sems = await API.get("/api/semesters");
    // Học kỳ tự động theo ngày bắt đầu học (Admin không khai báo): mặc định ngày bắt đầu của học kỳ đang diễn ra, chưa có thì thứ Hai tuần sau
    var curSem = sems.filter(function (x) {
      return x.is_current;
    })[0];
    function iso(x) {
      return x.getFullYear() + "-" + pad(x.getMonth() + 1) + "-" + pad(x.getDate());
    }
    var nx = new Date();
    nx.setDate(nx.getDate() + ((8 - nx.getDay()) % 7 || 7));
    $("#ncStart").value = curSem ? String(curSem.start_date).slice(0, 10) : iso(nx);
    function syncDays() {
      var t = termOf($("#ncStart").value);
      $("#ncDaysWrap").hidden = !(t && t.term === "he");
    }
    $("#ncStart").oninput = $("#ncStart").onchange = function () {
      syncDays();
      $("#ncCode").dispatchEvent(new Event("blur"));
    };
    syncDays();
    codeChecker($("#ncCode"), $("#ncCode"), function () {
      return val("ncStart") ? "start_date=" + val("ncStart") : "";
    });
    if ($("#ecCode"))
      codeChecker(
        $("#ecCode"),
        $("#ecCode"),
        function () {
          var c = classCache[val("ecId")];
          return c && c.semester_id ? "semester_id=" + c.semester_id : "";
        },
        function () {
          return val("ecId");
        },
      );
    if (!$("#lcSem"))
      $("#lecClasses").insertAdjacentHTML("beforebegin", semFilterHTML("lcSem", sems, true));
    var tb = $("#lq"),
      flt = $("#lcSem").closest(".cls-filter");
    while (tb && tb.parentElement && !tb.parentElement.classList.contains("page"))
      tb = tb.parentElement; // khối chứa ô "Tìm lớp"
    if (tb && flt && !tb.contains(flt)) {
      tb.classList.add("cls-toolbar");
      var nb = $(".tb-add", tb);
      if (nb) tb.insertBefore(flt, nb);
      else tb.appendChild(flt);
    }
    function lcard(c) {
      // thẻ lớp kiểu trang chủ + nút sửa + mã tham gia
      classCache[c.id] = c;
      var h = hcard(c, "lecturer", c.waiting_count),
        href = "lecturer-class.html?class=" + c.id;
      h = h
        .replace(
          /^<a class="hcard" href="[^"]*"/,
          '<div class="hcard lc-card" data-href="' + href + '" tabindex="0"',
        )
        .replace(/<\/a>$/, "");
      h = h.replace(
        '<div class="hcard-body">',
        '<button class="hc-act" type="button" aria-label="Sửa lớp" title="Sửa lớp" data-edit-class="' +
          c.id +
          '">' +
          ic("edit") +
          '</button><div class="hcard-body">',
      );
      var foot =
        '<div class="hc-foot"><span>Mã tham gia <span class="code">' +
        esc(c.join_code) +
        '</span></span><button class="hc-copy" type="button" data-copy="' +
        esc(c.join_code) +
        '">' +
        ic("copy") +
        "Sao chép</button></div>";
      return h + foot + "</div>";
    }
    NEU.state.reloadFn = async function () {
      var sem = val("lcSem");
      var classes = await API.get("/api/classes");
      if (sem !== "all")
        classes = classes.filter(function (c) {
          return String(c.semester_id) === sem;
        });
      NEU.state.SHOW_SEM = sem === "all";
      classes.sort(function (a, b) {
        return (b.semester_id || 0) - (a.semester_id || 0) || a.code.localeCompare(b.code);
      });
      classes.forEach(function (c) {
        classCache[c.id] = c;
      });
      var semLabel =
        sem === "all"
          ? "mọi học kỳ"
          : $("#lcSem").selectedOptions[0].textContent.replace(/ \(.*\)$/, "");
      txt("clsCount", classes.length + " lớp trong " + semLabel + ".");
      var g = $("#lecClasses");
      if (g) g.classList.add("hgrid");
      set(
        "lecClasses",
        classes.map(lcard).join("") ||
          empty('Chưa có lớp nào trong học kỳ này — bấm "Tạo lớp" để bắt đầu.'),
      );
    };
    $("#lcSem").onchange = function () {
      NEU.state.reloadFn().catch(fail);
    };
    await NEU.state.reloadFn();
  }
  NEU.lecturerClasses = lecturerClasses;
  NEU.pages.lecturerClasses = lecturerClasses;
})((window.NEU = window.NEU || {}));
