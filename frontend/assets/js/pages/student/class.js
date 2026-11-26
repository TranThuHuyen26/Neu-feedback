/* Trang class (studentClass). */
(function (NEU) {
  "use strict";
  var empty = NEU.empty,
    pickClass = NEU.pickClass,
    recentKey = NEU.recentKey,
    recentMap = NEU.recentMap,
    set = NEU.set,
    timelineBanner = NEU.timelineBanner,
    txt = NEU.txt,
    weekList = NEU.weekList;

  function touchRecent(id) {
    try {
      var m = recentMap();
      m[id] = Date.now();
      localStorage.setItem(recentKey(), JSON.stringify(m));
    } catch (e) {}
  }

  async function studentClass() {
    // trang lớp của sinh viên: chỉ khung tiến độ + danh sách tuần (tài liệu nằm dưới từng tuần)
    var classes = await API.get("/api/classes");
    var id = await pickClass(classes);
    if (!id) {
      set("classBanner", empty("Bạn chưa tham gia lớp nào."));
      return;
    }
    touchRecent(id);
    var r = await Promise.all([
      API.get("/api/classes/" + id),
      API.get("/api/classes/" + id + "/weeks"),
      API.get("/api/materials?class_id=" + id),
      API.get("/api/me/questions?class_id=" + id),
    ]);
    var c = r[0],
      tl = r[1].timeline,
      weeks = r[1].weeks,
      docs = r[2],
      mine = r[3];
    txt("classTitle", c.subject);
    document.title = c.subject + " | NEU Feedback";
    txt("classMeta", c.code + " · Giảng viên " + c.lecturer_name + " · " + c.semester);
    set("classBanner", timelineBanner(c, tl, "student"));
    set("weekGrid", weekList(weeks, "student", docs, mine, c, tl));
  }
  NEU.studentClass = studentClass;
  NEU.pages.studentClass = studentClass;
})((window.NEU = window.NEU || {}));
