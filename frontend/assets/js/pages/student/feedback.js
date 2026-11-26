/* Trang feedback (studentFeedback). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    QS = NEU.QS,
    d = NEU.d,
    empty = NEU.empty,
    esc = NEU.esc,
    initSeen = NEU.initSeen,
    openQModal = NEU.openQModal,
    qChips = NEU.qChips,
    qFilter = NEU.qFilter,
    qPlain = NEU.qPlain,
    qRow = NEU.qRow,
    set = NEU.set,
    val = NEU.val;

  async function studentFeedback() {
    // Theo dõi phản hồi: danh sách gọn (mới nhất trước), bấm một dòng để mở chi tiết
    var classes = await API.get("/api/classes"),
      all = [];
    $("#fbClass").insertAdjacentHTML(
      "beforeend",
      classes
        .map(function (c) {
          return '<option value="' + c.id + '">' + esc(c.code + " · " + c.subject) + "</option>";
        })
        .join(""),
    );
    var sfv =
      API.param("status") === "answered" || API.param("status") === "waiting"
        ? API.param("status")
        : "";
    var wantQ = +API.param("q") || null;
    function render() {
      set("fbTabs", qChips(all, sfv));
      var kw = val("fbQ").toLowerCase(),
        cl = val("fbClass"),
        old = val("fbSort") === "old";
      var list = qFilter(all, sfv).filter(function (q) {
        return (
          (!cl || String(q.class_id) === cl) &&
          (!kw || (qPlain(q.content) + " " + q.code).toLowerCase().indexOf(kw) > -1)
        );
      });
      list.sort(function (x, y) {
        return old ? d(x.created_at) - d(y.created_at) : d(y.created_at) - d(x.created_at);
      });
      set(
        "fbList",
        list
          .map(function (q) {
            return qRow(q, true);
          })
          .join("") ||
          empty(all.length ? "Không có câu hỏi nào phù hợp." : "Bạn chưa gửi câu hỏi nào."),
      );
    }
    async function load() {
      all = await API.get("/api/me/questions");
      initSeen(all);
      render();
      if (NEU.state.qmOpenId !== null && NEU.state.qmEditing === null && QS[NEU.state.qmOpenId])
        openQModal(NEU.state.qmOpenId);
    }
    NEU.state.reloadFn = load;
    $("#fbClass").onchange = $("#fbSort").onchange = render;
    $("#fbTabs").onclick = function (e) {
      var b = e.target.closest("[data-s]");
      if (!b) return;
      sfv = b.dataset.s;
      render();
    };
    $("#fbQ").oninput = render;
    await load();
    if (wantQ && QS[wantQ]) openQModal(wantQ);
  }
  NEU.studentFeedback = studentFeedback;
  NEU.pages.studentFeedback = studentFeedback;
})((window.NEU = window.NEU || {}));
