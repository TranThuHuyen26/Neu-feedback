/* Trang materials (lecturerMaterials). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    empty = NEU.empty,
    esc = NEU.esc,
    fDate = NEU.fDate,
    fTime = NEU.fTime,
    fileIcon = NEU.fileIcon,
    fsize = NEU.fsize,
    ic = NEU.ic,
    set = NEU.set,
    txt = NEU.txt,
    val = NEU.val;

  async function lecturerMaterials() {
    var classes = await API.get("/api/classes"),
      byId = {},
      weekNo = {},
      page = 1,
      all = [];
    classes.forEach(function (c) {
      byId[c.id] = c;
    });
    $("#mtClass").insertAdjacentHTML(
      "beforeend",
      classes
        .map(function (c) {
          return '<option value="' + c.id + '">' + esc(c.code + " · " + c.subject) + "</option>";
        })
        .join(""),
    );
    var wl = await Promise.all(
      classes.map(function (c) {
        return API.get("/api/classes/" + c.id + "/weeks");
      }),
    );
    wl.forEach(function (r) {
      r.weeks.forEach(function (w) {
        weekNo[w.id] = w;
      });
    });
    function loadWeeks() {
      // chưa chọn lớp: Tuần 1 → 15 (gộp mọi lớp); chọn lớp: các tuần của lớp đó kèm tiêu đề
      var cid = val("mtClass"),
        keep = val("mtWeek"),
        ws = Object.keys(weekNo).map(function (k) {
          return weekNo[k];
        });
      var opts;
      if (cid)
        opts = ws
          .filter(function (w) {
            return String(w.class_id) === cid;
          })
          .sort(function (a, b) {
            return a.number - b.number;
          })
          .map(function (w) {
            return (
              '<option value="' +
              w.number +
              '">' +
              (w.unit_label || "Tuần") +
              " " +
              w.number +
              (w.title ? " · " + esc(w.title) : "") +
              "</option>"
            );
          });
      else {
        var max = Math.max.apply(
          null,
          ws
            .map(function (w) {
              return w.number;
            })
            .concat([15]),
        );
        opts = [];
        for (var n = 1; n <= max; n++)
          opts.push('<option value="' + n + '">Tuần ' + n + "</option>");
      }
      $("#mtWeek").innerHTML = '<option value="">Tất cả tuần</option>' + opts.join("");
      if (keep && $('#mtWeek option[value="' + keep + '"]')) $("#mtWeek").value = keep;
    }
    loadWeeks();
    var TYPE = { PDF: "PDF", DOC: "Word", PPT: "PowerPoint", XLS: "Excel", TXT: "TXT" };
    function render() {
      // hiện toàn bộ tài liệu khớp bộ lọc (không phân trang)
      var cid = val("mtClass"),
        wk = val("mtWeek"),
        q = val("mtQ").toLowerCase();
      var list = all.filter(function (m) {
        var w = weekNo[m.week_id];
        return (
          (!cid || String(m.class_id) === cid) &&
          (!wk || (w && String(w.number) === wk)) &&
          (!q || m.filename.toLowerCase().indexOf(q) > -1)
        );
      });
      txt("mtCount", list.length + " tài liệu");
      set(
        "mtBody",
        list
          .map(function (m) {
            var c = byId[m.class_id] || {},
              w = weekNo[m.week_id];
            return (
              '<tr><td><div class="fname">' +
              fileIcon(m.file_type || m.filename) +
              '<div><b title="' +
              esc(m.filename) +
              '">' +
              esc(m.filename) +
              "</b><small>" +
              fsize(m.size_bytes) +
              " · " +
              (TYPE[m.file_type] || m.file_type || "") +
              "</small></div></div></td>" +
              '<td class="mt-cls" title="' +
              esc(c.subject || "") +
              '">' +
              esc(c.code || "") +
              "</td><td>" +
              (w ? (w.unit_label || "Tuần") + " " + w.number : "—") +
              "</td>" +
              "<td>" +
              fDate(m.created_at) +
              '<div class="tiny muted">' +
              fTime(m.created_at) +
              '</div></td><td><div class="mat-actions">' +
              '<button class="btn sm icon-only" title="Xem" data-open="/api/materials/' +
              m.id +
              '/download" data-name="' +
              esc(m.filename) +
              '">' +
              ic("eye") +
              "</button>" +
              '<button class="kebab" data-kebab aria-label="Thao tác">⋮</button><div class="pop-menu" hidden>' +
              '<button data-rename="' +
              m.id +
              '" data-name="' +
              esc(m.filename) +
              '">' +
              ic("edit") +
              "Đổi tên</button>" +
              '<button data-dl="/api/materials/' +
              m.id +
              '/download" data-name="' +
              esc(m.filename) +
              '">' +
              ic("download") +
              'Tải xuống</button><button class="danger" data-del-doc="' +
              m.id +
              '" data-name="' +
              esc(m.filename) +
              '">' +
              ic("trash") +
              "Xóa</button></div></div></td></tr>"
            );
          })
          .join("") ||
          '<tr><td colspan="5">' +
            empty(all.length ? "Không có tài liệu phù hợp bộ lọc." : "Chưa có tài liệu nào.") +
            "</td></tr>",
      );
    }
    NEU.state.reloadFn = async function () {
      all = await API.get("/api/materials");
      render();
    };
    $("#mtClass").onchange = function () {
      page = 1;
      loadWeeks();
      render();
    };
    $("#mtWeek").onchange = function () {
      render();
    };
    $("#mtQ").oninput = function () {
      page = 1;
      render();
    };
    await NEU.state.reloadFn();
  }
  NEU.lecturerMaterials = lecturerMaterials;
  NEU.pages.lecturerMaterials = lecturerMaterials;
})((window.NEU = window.NEU || {}));
