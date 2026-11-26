/* Phần dùng chung giữa các trang của sinh viên. */
(function (NEU) {
  "use strict";
  var ACTIONS = NEU.ACTIONS,
    QS = NEU.QS,
    esc = NEU.esc,
    fTime = NEU.fTime,
    fWk = NEU.fWk,
    ic = NEU.ic,
    isNewAns = NEU.isNewAns,
    qPill = NEU.qPill,
    qPlain = NEU.qPlain,
    seenSince = NEU.seenSince,
    val = NEU.val;

  ACTIONS.join = async function () {
    var code = val("joinCode");
    if (!code) {
      toast("Vui lòng nhập mã tham gia");
      return;
    }
    var c = await API.post("/api/classes/join", { join_code: code });
    closeModal("joinModal");
    toast("Đã tham gia lớp " + c.code);
    setTimeout(function () {
      location.href = "student-class.html?class=" + c.id;
    }, 600);
  };
  // nhớ thẻ câu hỏi đang sửa + nội dung đang gõ (trang tự làm mới 5 giây/lần)
  function recentKey() {
    return (
      "neu_recent_classes:" +
      ((typeof NEU.state.user !== "undefined" && NEU.state.user && NEU.state.user.id) || "")
    );
  }

  function recentMap() {
    try {
      return JSON.parse(localStorage.getItem(recentKey()) || "{}") || {};
    } catch (e) {
      return {};
    }
  }

  function initSeen() {
    seenSince();
  }

  function qRow(q, withClass) {
    QS[q.id] = q;
    return (
      '<div role="button" tabindex="0" class="qr" data-qrow="' +
      q.id +
      '"><span class="qr-when"><span>' +
      ic("cal") +
      "<b>" +
      fWk(q.created_at) +
      "</b></span><span>" +
      ic("clock") +
      fTime(q.created_at) +
      '</span></span><span class="qr-main">' +
      (withClass
        ? '<span class="qr-class" title="' +
          esc(q.subject || "") +
          '">' +
          ic("layers") +
          "Lớp " +
          esc(q.class_code || "") +
          (q.week_number ? " · Tuần " + q.week_number : "") +
          "</span>"
        : "") +
      '<span class="qr-text">' +
      (isNewAns(q) ? '<i class="qr-dot" title="Giảng viên vừa trả lời"></i>' : "") +
      esc(qPlain(q.content)) +
      '</span></span><span class="qr-end">' +
      (q.can_modify
        ? '<span class="qr-acts"><button type="button" class="q-ico" data-qm-edit="' +
          q.id +
          '" title="Sửa câu hỏi" aria-label="Sửa câu hỏi">' +
          ic("edit") +
          '</button><button type="button" class="q-ico danger" data-qm-del="' +
          q.id +
          '" title="Xóa câu hỏi" aria-label="Xóa câu hỏi">' +
          ic("trash") +
          "</button></span>"
        : "") +
      qPill(q) +
      '<span class="qr-go">' +
      ic("chev").replace('class="ico"', 'class="ico qr-chev"') +
      "</span></span></div>"
    );
  }

  function qChips(list, cur) {
    var a = list.filter(function (q) {
      return q.status === "answered";
    }).length;
    return [
      ["", "Tất cả", list.length, "chat"],
      ["waiting", "Chờ trả lời", list.length - a, "clock"],
      ["answered", "Đã trả lời", a, "check"],
    ]
      .map(function (x) {
        return (
          '<button type="button" class="chip' +
          (cur === x[0] ? " on" : "") +
          '" data-s="' +
          x[0] +
          '">' +
          ic(x[3]) +
          x[1] +
          " <em>" +
          x[2] +
          "</em></button>"
        );
      })
      .join("");
  }

  function qFilter(list, sf) {
    return list.filter(function (q) {
      return !sf || (sf === "answered" ? q.status === "answered" : q.status !== "answered");
    });
  }
  NEU.initSeen = initSeen;
  NEU.qChips = qChips;
  NEU.qFilter = qFilter;
  NEU.qRow = qRow;
  NEU.recentKey = recentKey;
  NEU.recentMap = recentMap;
})((window.NEU = window.NEU || {}));
