/* Phần dùng chung giữa các trang của quản trị. */
(function (NEU) {
  "use strict";
  var d = NEU.d;

  // Đường xu hướng nhỏ cho "Tương tác 7 ngày"
  function trendSVG(days, dense) {
    var W = 560,
      H = 150,
      L = 28,
      B = 24;
    var max = Math.max.apply(
      null,
      days
        .map(function (d) {
          return d.questions;
        })
        .concat([3]),
    );
    var X = function (i) {
        return L + ((W - L - 30) * i) / Math.max(days.length - 1, 1);
      },
      Y = function (v) {
        return H - B - ((H - B - 12) * v) / max;
      };
    var pts = days.map(function (d, i) {
      return X(i).toFixed(1) + "," + Y(d.questions).toFixed(1);
    });
    var grid = [0, 0.5, 1]
      .map(function (k) {
        var v = Math.round(max * k);
        return (
          '<line x1="' +
          L +
          '" x2="' +
          (W - 6) +
          '" y1="' +
          Y(v) +
          '" y2="' +
          Y(v) +
          '" stroke="#EEF1F6"/><text x="' +
          (L - 6) +
          '" y="' +
          (Y(v) + 4) +
          '" text-anchor="end" font-size="11" fill="#5B6479">' +
          v +
          "</text>"
        );
      })
      .join("");
    var dots = days
      .map(function (d, i) {
        if (dense) {
          var show = i === 0 || i === days.length - 1 || i === Math.floor(days.length / 2);
          return (
            "<g><title>" +
            d.date.slice(8, 10) +
            "/" +
            d.date.slice(5, 7) +
            ": " +
            d.questions +
            " câu hỏi</title>" +
            (show
              ? '<text x="' +
                X(i) +
                '" y="' +
                (H - 6) +
                '" text-anchor="middle" font-size="11" fill="#5B6479">' +
                d.date.slice(8, 10) +
                "/" +
                d.date.slice(5, 7) +
                "</text>"
              : "") +
            "</g>"
          );
        }
        return (
          "<g><title>" +
          d.date.slice(8, 10) +
          "/" +
          d.date.slice(5, 7) +
          ": " +
          d.questions +
          ' câu hỏi</title><circle cx="' +
          X(i) +
          '" cy="' +
          Y(d.questions) +
          '" r="4" fill="#fff" stroke="var(--accent)" stroke-width="2"/>' +
          '<text x="' +
          X(i) +
          '" y="' +
          (H - 6) +
          '" text-anchor="middle" font-size="11" fill="#5B6479">' +
          d.date.slice(8, 10) +
          "/" +
          d.date.slice(5, 7) +
          "</text></g>"
        );
      })
      .join("");
    return (
      '<svg class="ov-line" viewBox="0 0 ' +
      W +
      " " +
      H +
      '" role="img" aria-label="Số câu hỏi 7 ngày gần nhất">' +
      grid +
      '<polyline points="' +
      pts.join(" ") +
      '" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>' +
      dots +
      "</svg>"
    );
  }
  NEU.trendSVG = trendSVG;
})((window.NEU = window.NEU || {}));
