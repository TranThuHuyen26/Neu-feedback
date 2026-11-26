/* Trang classes (studentClasses). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    empty = NEU.empty,
    fail = NEU.fail,
    hcard = NEU.hcard,
    recentMap = NEU.recentMap,
    semFilterHTML = NEU.semFilterHTML,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  async function studentClasses() {
    var rr = await Promise.all([
      API.get("/api/semesters"),
      API.get("/api/classes"),
      API.get("/api/me/summary").catch(function () {
        return {};
      }),
    ]);
    var sems = rr[0],
      allCls = rr[1],
      wb = rr[2].waiting_by_class || {};
    function card(c) {
      return hcard(c, "student", wb[c.id]);
    }
    if (!$("#scSem")) {
      var ttl = $("#allClasses") && $("#allClasses").previousElementSibling;
      if (ttl && ttl.classList.contains("section-title")) {
        ttl.classList.add("with-filter");
        ttl.insertAdjacentHTML("beforeend", semFilterHTML("scSem", sems, false, true));
      } else
        $("#allClasses").insertAdjacentHTML(
          "beforebegin",
          semFilterHTML("scSem", sems, false, true),
        );
    }
    var semSel = val("scSem");
    var classes =
      semSel === "all"
        ? allCls
        : allCls.filter(function (c) {
            return String(c.semester_id) === semSel;
          });
    NEU.state.SHOW_SEM = semSel === "all";
    $("#scSem").onchange = function () {
      studentClasses().catch(fail);
    };
    txt("clsCount", classes.length + " lớp đang tham gia.");
    var rm = recentMap();
    var recent = allCls
      .slice()
      .sort(function (a, b) {
        return (
          (rm[b.id] || 0) - (rm[a.id] || 0) || (b.current_week ? 1 : 0) - (a.current_week ? 1 : 0)
        );
      })
      .slice(0, 3);
    set("recentClasses", recent.map(card).join("") || empty("Bạn chưa tham gia lớp nào."));
    set("allClasses", classes.map(card).join("") || empty("Bạn chưa tham gia lớp nào."));
    ["recentClasses", "allClasses"].forEach(function (id) {
      var g = $("#" + id);
      if (g) g.classList.add("hgrid");
    });
    function syncRecent() {
      var q = (($("#qs") && $("#qs").value) || "").trim(),
        g = $("#recentClasses");
      if (!g) return;
      g.style.display = q ? "none" : "";
      if (g.previousElementSibling) g.previousElementSibling.style.display = q ? "none" : "";
    }
    if ($("#qs") && !$("#qs").dataset.recentBound) {
      $("#qs").dataset.recentBound = "1";
      $("#qs").addEventListener("input", syncRecent);
    }
    syncRecent();
  }
  NEU.studentClasses = studentClasses;
  NEU.pages.studentClasses = studentClasses;
})((window.NEU = window.NEU || {}));
