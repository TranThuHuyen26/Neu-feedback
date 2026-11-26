/* Trang stats (adminStats). */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    colorOf = NEU.colorOf,
    d = NEU.d,
    dur = NEU.dur,
    empty = NEU.empty,
    esc = NEU.esc,
    fDate = NEU.fDate,
    fail = NEU.fail,
    ic = NEU.ic,
    kpi = NEU.kpi,
    num = NEU.num,
    pct = NEU.pct,
    set = NEU.set,
    trendSVG = NEU.trendSVG,
    txt = NEU.txt,
    val = NEU.val;

  // ---- Xuất báo cáo (Admin → Thống kê hệ thống): dựng báo cáo dạng văn bản có logo trường rồi mở hộp thoại in.
  // Người dùng chọn "Lưu dưới dạng PDF". Số liệu lấy từ dữ liệu đang hiển thị nên khớp đúng năm học / học kỳ đang chọn.
  function logoDataURI() {
    return fetch("assets/images/neu-logo.png")
      .then(function (r) {
        return r.blob();
      })
      .then(function (b) {
        return new Promise(function (ok) {
          var fr = new FileReader();
          fr.onload = function () {
            ok(fr.result);
          };
          fr.onerror = function () {
            ok("");
          };
          fr.readAsDataURL(b);
        });
      })
      .catch(function () {
        return "";
      });
  }

  function statsReportHTML(data, logo) {
    var T = data.total,
      R = data.range,
      now = new Date();
    function rc(p) {
      return p >= 80 ? "#16A34A" : p >= 50 ? "#F59E0B" : "#DC2626";
    }
    function fmt(sec) {
      if (sec == null) return "—";
      var h = Math.floor(sec / 3600),
        m = Math.floor((sec % 3600) / 60),
        sc = Math.round(sec % 60);
      return h ? h + " giờ " + m + " phút" : m ? m + " phút " + sc + " giây" : sc + " giây";
    }
    function pct(x) {
      return (Math.round(x * 10) / 10).toFixed(1).replace(".", ",");
    }
    var label = R ? R.label : "Chưa có học kỳ nào";
    var yr = data.year ? data.year.replace("-", " – ") : "";
    var termTxt = data.term ? label : "Cả năm học";
    var period = R && R.from ? fDate(R.from) + " – " + fDate(R.to) : "—";
    var dateLine =
      "Hà Nội, ngày " +
      now.getDate() +
      " tháng " +
      (now.getMonth() + 1) +
      " năm " +
      now.getFullYear();
    var weeks = data.by_week.filter(function (w) {
      return w.learned || w.questions;
    });
    var classes = data.by_class.slice().sort(function (a, b) {
      return b.questions - a.questions;
    });
    var lecs = data.by_lecturer
      .filter(function (l) {
        return l.questions;
      })
      .sort(function (a, b) {
        return b.answer_rate - a.answer_rate;
      });
    var none = '<p class="none">Chưa có dữ liệu trong khoảng thời gian này.</p>';
    function sec(n, t) {
      return (
        '<div class="sh"><span class="no">' + n + '</span><span class="tt">' + t + "</span></div>"
      );
    }
    function icon(path) {
      return (
        '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        path +
        "</svg>"
      );
    }
    function card(ic, bg, fg, l, v, s) {
      return (
        '<td class="kc"><table><tr><td class="ic"><span class="ci" style="background:' +
        bg +
        ";color:" +
        fg +
        '">' +
        ic +
        '</span></td><td><div class="kl">' +
        l +
        '</div><div class="kvv">' +
        v +
        '</div><div class="ks">' +
        s +
        "</div></td></tr></table></td>"
      );
    }
    var kpis =
      '<table class="kpis"><tr>' +
      card(
        icon('<path d="M4 5h16v11H9l-5 4z"/>'),
        "#E3EEFC",
        "#2F6BC0",
        "Tổng số câu hỏi",
        num(T.questions),
        T.classes + " lớp · " + T.students + " sinh viên",
      ) +
      card(
        icon('<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>'),
        "#DDF3E6",
        "#16A34A",
        "Tỷ lệ phản hồi",
        T.answer_rate + "%",
        num(T.answered) + " câu đã trả lời",
      ) +
      card(
        icon('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
        "#EDE6FA",
        "#7C4DCB",
        "Phản hồi trung bình",
        esc(fmt(T.avg_response_seconds)),
        "Từ lúc hỏi đến lúc trả lời",
      ) +
      card(
        icon('<path d="M6 4v17M6 5h11l-2 4 2 4H6"/>'),
        "#FDE8E8",
        "#DC2626",
        "Đang chờ trả lời",
        num(T.waiting),
        T.review + " câu chờ duyệt",
      ) +
      "</tr></table>";

    // 2.1 Biểu đồ đường: số câu hỏi theo tuần
    function lineChart() {
      if (!weeks.length) return none;
      var W = 340,
        Hh = 138,
        L = 30,
        Rr = 10,
        Tp = 10,
        B = 22,
        iw = W - L - Rr,
        ih = Hh - Tp - B;
      var mxv = Math.max.apply(
        null,
        weeks
          .map(function (w) {
            return w.questions;
          })
          .concat([1]),
      );
      var step = mxv > 100 ? 50 : mxv > 40 ? 20 : mxv > 20 ? 10 : 5,
        top = Math.ceil(mxv / step) * step;
      function X(i) {
        return L + (weeks.length > 1 ? (i * iw) / (weeks.length - 1) : iw / 2);
      }
      function Y(v) {
        return Tp + ih - (v * ih) / top;
      }
      var g = "",
        k;
      for (k = 0; k <= 4; k++) {
        var yv = (top * k) / 4,
          y = Y(yv).toFixed(1);
        g +=
          '<line x1="' +
          L +
          '" y1="' +
          y +
          '" x2="' +
          (W - Rr) +
          '" y2="' +
          y +
          '" stroke="#DCE6F4" stroke-width="0.6"/><text x="' +
          (L - 4) +
          '" y="' +
          (+y + 2.5) +
          '" font-size="7" text-anchor="end" fill="#5B6B85">' +
          Math.round(yv) +
          "</text>";
      }
      var pq = weeks
        .map(function (w, i) {
          return X(i).toFixed(1) + "," + Y(w.questions).toFixed(1);
        })
        .join(" ");
      var pa = weeks
        .map(function (w, i) {
          return X(i).toFixed(1) + "," + Y(w.answered).toFixed(1);
        })
        .join(" ");
      var area =
        L + "," + (Tp + ih) + " " + pq + " " + X(weeks.length - 1).toFixed(1) + "," + (Tp + ih);
      var dots = weeks
        .map(function (w, i) {
          return (
            '<circle cx="' +
            X(i).toFixed(1) +
            '" cy="' +
            Y(w.questions).toFixed(1) +
            '" r="1.8" fill="#2F6BC0"/><circle cx="' +
            X(i).toFixed(1) +
            '" cy="' +
            Y(w.answered).toFixed(1) +
            '" r="1.8" fill="#16A34A"/>'
          );
        })
        .join("");
      var xl = weeks
        .map(function (w, i) {
          return (
            '<text x="' +
            X(i).toFixed(1) +
            '" y="' +
            (Hh - 7) +
            '" font-size="6.5" text-anchor="middle" fill="#5B6B85">T' +
            w.number +
            "</text>"
          );
        })
        .join("");
      return (
        '<svg viewBox="0 0 ' +
        W +
        " " +
        Hh +
        '" width="100%" xmlns="http://www.w3.org/2000/svg">' +
        g +
        '<polygon points="' +
        area +
        '" fill="#2F6BC0" fill-opacity="0.10"/><polyline points="' +
        pq +
        '" fill="none" stroke="#2F6BC0" stroke-width="1.6"/><polyline points="' +
        pa +
        '" fill="none" stroke="#16A34A" stroke-width="1.6"/>' +
        dots +
        xl +
        "</svg>" +
        '<p class="leg"><i style="background:#2F6BC0"></i>Tổng câu hỏi <i style="background:#16A34A"></i>Đã trả lời</p>'
      );
    }
    // 2.2 Biểu đồ tròn: phân bố câu hỏi theo lớp
    function donut() {
      var total = classes.reduce(function (a, c) {
        return a + c.questions;
      }, 0);
      if (!total) return none;
      var a0 = -Math.PI / 2,
        seg = ""; // vẽ từng cung bằng đường dẫn để hiển thị đúng ở mọi trình duyệt
      classes
        .filter(function (c) {
          return c.questions;
        })
        .forEach(function (c) {
          var frac = c.questions / total,
            a1 = a0 + frac * 2 * Math.PI,
            col = colorOf(c.id);
          if (frac > 0.9999)
            seg +=
              '<circle cx="50" cy="50" r="38" fill="none" stroke="' + col + '" stroke-width="15"/>';
          else
            seg +=
              '<path d="M' +
              (50 + 38 * Math.cos(a0)).toFixed(2) +
              " " +
              (50 + 38 * Math.sin(a0)).toFixed(2) +
              " A38 38 0 " +
              (frac > 0.5 ? 1 : 0) +
              " 1 " +
              (50 + 38 * Math.cos(a1)).toFixed(2) +
              " " +
              (50 + 38 * Math.sin(a1)).toFixed(2) +
              '" fill="none" stroke="' +
              col +
              '" stroke-width="15"/>';
          a0 = a1;
        });
      var lg = classes
        .filter(function (c) {
          return c.questions;
        })
        .map(function (c) {
          return (
            '<tr><td class="sq"><i style="background:' +
            colorOf(c.id) +
            '"></i></td><td>' +
            esc(c.code) +
            '</td><td class="r">' +
            pct((c.questions * 100) / total) +
            "%</td></tr>"
          );
        })
        .join("");
      return (
        '<table class="dn"><tr><td class="dg">' +
        '<svg viewBox="0 0 100 100" width="100" height="100" xmlns="http://www.w3.org/2000/svg">' +
        seg +
        '<text x="50" y="49" font-size="13" font-weight="700" text-anchor="middle" fill="#17428A">' +
        num(total) +
        '</text><text x="50" y="60" font-size="6.5" text-anchor="middle" fill="#5B6B85">câu hỏi</text></svg>' +
        '</td><td><table class="lgt">' +
        lg +
        "</table></td></tr></table>"
      );
    }
    // 2.3 Cột: tình hình xử lý câu hỏi
    function statusBars() {
      var items = [
        ["Đã trả lời", T.answered, "#16A34A"],
        ["Đang chờ", T.waiting, "#F2A93B"],
        ["Chờ duyệt", T.review, "#DC2626"],
      ];
      var mx = Math.max.apply(
          null,
          items
            .map(function (i) {
              return i[1];
            })
            .concat([1]),
        ),
        H = 70;
      return (
        '<table class="sb"><tr>' +
        items
          .map(function (i) {
            return (
              '<td><div class="n">' +
              i[1] +
              '</div><div class="col" style="height:' +
              ((i[1] * H) / mx).toFixed(1) +
              "pt;background:" +
              i[2] +
              '"></div></td>'
            );
          })
          .join("") +
        "</tr><tr>" +
        items
          .map(function (i) {
            return '<td class="lb">' + i[0] + "</td>";
          })
          .join("") +
        "</tr></table>"
      );
    }
    // 2.4 Giảng viên phản hồi
    function lecturers() {
      if (!data.by_lecturer.length) return none;
      return data.by_lecturer
        .map(function (l) {
          return (
            '<div class="lr"><table class="lh"><tr><td><b>' +
            esc(l.name) +
            '</b></td><td class="r"><b style="color:' +
            rc(l.answer_rate) +
            '">' +
            l.answer_rate +
            '%</b> phản hồi</td></tr></table><div class="m">' +
            esc(l.class_codes.join(", ")) +
            " · " +
            l.questions +
            " câu · " +
            l.waiting +
            " chờ · TB " +
            esc(fmt(l.avg_response_seconds)) +
            '</div><div class="rb"><i style="width:' +
            l.answer_rate +
            "%;background:" +
            rc(l.answer_rate) +
            '"></i></div></div>'
          );
        })
        .join("");
    }
    // 2.5 Bảng chi tiết theo lớp
    function table() {
      if (!classes.length) return none;
      var sq = 0,
        sa = 0,
        sw = 0;
      var rows = classes
        .map(function (c) {
          sq += c.questions;
          sa += c.answered;
          sw += c.waiting;
          return (
            "<tr><td><b>" +
            esc(c.code) +
            '</b><div class="sj">' +
            esc(c.subject) +
            "</div></td><td>" +
            esc(c.lecturer) +
            '</td><td class="n">' +
            c.students +
            '</td><td class="n">' +
            c.questions +
            '</td><td class="n">' +
            c.answered +
            '</td><td class="n">' +
            c.waiting +
            '</td><td class="n">' +
            c.answer_rate +
            "%</td></tr>"
          );
        })
        .join("");
      return (
        '<table class="dt"><thead><tr><th>Lớp</th><th>Giảng viên</th><th>Sinh viên</th><th>Câu hỏi</th><th>' +
        "Đã trả lời</th><th>Đang chờ</th><th>Tỷ lệ</th></tr></thead><tbody>" +
        rows +
        '<tr class="tot"><td colspan="3">Tổng cộng</td><td class="n">' +
        sq +
        '</td><td class="n">' +
        sa +
        '</td><td class="n">' +
        sw +
        '</td><td class="n">' +
        T.answer_rate +
        "%</td></tr></tbody></table>"
      );
    }
    // Phần 3: nhận xét (ghép từ số liệu, không dùng AI nên luôn khớp với bảng)
    var wkMax = weeks.reduce(function (a, w) {
      return !a || w.questions > a.questions ? w : a;
    }, null);
    var byRate = classes
      .filter(function (c) {
        return c.questions;
      })
      .sort(function (a, b) {
        return b.answer_rate - a.answer_rate;
      });
    var byWait = classes.slice().sort(function (a, b) {
      return b.waiting - a.waiting;
    });
    function ul(a) {
      return (
        "<ul>" +
        a
          .map(function (x) {
            return "<li>" + x + "</li>";
          })
          .join("") +
        "</ul>"
      );
    }
    var c1 = [
      "Hệ thống ghi nhận <b>" + num(T.questions) + "</b> câu hỏi tại " + T.classes + " lớp học.",
      "Tỷ lệ phản hồi chung đạt <b>" +
        T.answer_rate +
        "%</b> (" +
        num(T.answered) +
        "/" +
        num(T.questions) +
        " câu).",
    ];
    if (wkMax && wkMax.questions)
      c1.push(
        "Tuần có nhiều câu hỏi nhất: Tuần " + wkMax.number + " (" + wkMax.questions + " câu).",
      );
    var c2 = ["Thời gian phản hồi trung bình: <b>" + esc(fmt(T.avg_response_seconds)) + "</b>."];
    if (lecs.length)
      c2.push("Tỷ lệ phản hồi cao nhất: " + esc(lecs[0].name) + " (" + lecs[0].answer_rate + "%).");
    if (lecs.length > 1)
      c2.push(
        "Thấp nhất: " +
          esc(lecs[lecs.length - 1].name) +
          " (" +
          lecs[lecs.length - 1].answer_rate +
          "%).",
      );
    var c3 = [];
    if (classes.length && classes[0].questions)
      c3.push(
        "Lớp có nhiều câu hỏi nhất: " +
          esc(classes[0].code) +
          " (" +
          classes[0].questions +
          " câu).",
      );
    if (byRate.length)
      c3.push(
        "Tỷ lệ phản hồi cao nhất: " + esc(byRate[0].code) + " (" + byRate[0].answer_rate + "%).",
      );
    if (byRate.length > 1)
      c3.push(
        "Thấp nhất: " +
          esc(byRate[byRate.length - 1].code) +
          " (" +
          byRate[byRate.length - 1].answer_rate +
          "%).",
      );
    if (!c3.length) c3.push("Chưa có dữ liệu để đánh giá theo lớp.");
    var c4 = [
      T.waiting
        ? "Ưu tiên trả lời <b>" +
          T.waiting +
          "</b> câu đang chờ" +
          (byWait.length && byWait[0].waiting
            ? ", nhiều nhất ở lớp " + esc(byWait[0].code) + " (" + byWait[0].waiting + " câu)"
            : "") +
          "."
        : "Hiện không còn câu hỏi nào đang chờ trả lời.",
      T.questions && T.answer_rate < 80
        ? "Khuyến khích giảng viên phản hồi sớm để nâng cao tỷ lệ phản hồi."
        : "Duy trì tỷ lệ phản hồi hiện tại.",
    ];
    if (T.review) c4.push("Rà soát " + T.review + " câu đang chờ duyệt.");
    function box(t, items) {
      return '<td class="cb"><div class="ct">' + t + "</div>" + ul(items) + "</td>";
    }
    var comments =
      '<table class="cm"><tr>' +
      box("Tình hình chung", c1) +
      box("Hiệu quả phản hồi của giảng viên", c2) +
      "</tr><tr>" +
      box("Đánh giá theo lớp", c3) +
      box("Đề xuất", c4) +
      "</tr></table>";
    var concl = T.questions
      ? "Trong " +
        esc(label) +
        ", hệ thống NEU Feedback ghi nhận <b>" +
        num(T.questions) +
        "</b> câu hỏi tại " +
        T.classes +
        " lớp học với tỷ lệ phản hồi đạt <b>" +
        T.answer_rate +
        "%</b>, thời gian phản hồi trung bình " +
        esc(fmt(T.avg_response_seconds)) +
        ". " +
        (T.waiting
          ? "Hiện còn " + T.waiting + " câu hỏi đang chờ trả lời. "
          : "Tất cả câu hỏi đã được trả lời. ") +
        "Báo cáo phục vụ công tác quản lý và nâng cao chất lượng tương tác giữa sinh viên và giảng viên."
      : "Trong " + esc(label) + ", hệ thống chưa ghi nhận câu hỏi nào.";

    var SERIF = '"Cambria","Georgia","Times New Roman",serif',
      SANS = '"Segoe UI","Calibri","Helvetica Neue",Arial,sans-serif';
    var css = [
      '@page{size:A4;margin:14mm 14mm 16mm;@top-left{content:" "}@top-center{content:" "}' +
        '@top-right{content:" "}@bottom-left{content:"NEU Feedback · Báo cáo thống kê hệ thống";' +
        "font:italic 8.5pt " +
        SERIF +
        ';color:#17428A}@bottom-right{content:"Trang " counter(page) "/" counter(pages);font:8.5pt ' +
        SANS +
        ";color:#5B6B85}}",
      "*{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}",
      "body{font-family:" + SANS + ";font-size:9.5pt;line-height:1.4;color:#1F2A44;margin:0}",
      "table{border-collapse:collapse;width:100%}p{margin:0}ul{margin:0;padding-left:12pt}li{margin:1pt 0}",
      ".hd td{vertical-align:middle}.hd .lg{width:54pt}.hd .lg img{width:46pt;height:46pt;display:block}" +
        ".hd .org b{display:block;font:700 13pt " +
        SERIF +
        ";color:#17428A;letter-spacing:.01em}.hd .org span{font-size:9.5pt;color:#44546F}" +
        ".hd .sys{text-align:right;font:italic 10pt " +
        SERIF +
        ";color:#17428A}",
      ".hl{height:0;border-top:1.2pt solid #2F6BC0;margin:5pt 0 10pt}",
      ".ti{text-align:center;margin-bottom:8pt}.t1{font:700 15pt " +
        SERIF +
        ";color:#17428A;letter-spacing:.03em}.t2{font:700 21pt " +
        SERIF +
        ";color:#17428A;letter-spacing:.02em;margin:1pt 0 3pt}.ti .st{font:italic 10.5pt " +
        SERIF +
        ";color:#3C4A66;margin-top:2pt}",
      ".info{border-collapse:separate;border-spacing:0;margin:8pt 0 4pt}.info td{vertical-align:top}" +
        ".info .b1,.info .b2{background:" +
        "#F3F8FF" +
        ";border:.6pt solid #D5E4F7;border-radius:7pt;padding:8pt 10pt}.info .gap{width:10pt}.info .b1{width:50%}",
      ".kvt td{padding:2pt 0;font-size:9.5pt}.kvt td.k{width:38%;color:#44546F}.kvt td.v{font-weight:600}",
      ".it{font:700 10.5pt " +
        SERIF +
        ";color:#17428A;margin-bottom:3pt}.info .b2 p{font-size:9.5pt;line-height:1.45}",
      ".sh{margin:13pt 0 7pt;break-after:avoid;page-break-after:avoid}.sh .no{display:inline-block;" +
        "width:15pt;height:15pt;line-height:15pt;text-align:center;background:#17428A;color:#fff;" +
        "border-radius:3pt;font-weight:700;font-size:9.5pt;margin-right:7pt;vertical-align:middle}" +
        ".sh .tt{font:700 11.5pt " +
        SANS +
        ";color:#17428A;letter-spacing:.02em;vertical-align:middle}",
      ".blk{break-inside:avoid;page-break-inside:avoid}.bt{font:700 9.5pt " +
        SANS +
        ";color:#17428A;margin-bottom:3pt}",
      ".kpis{border-collapse:separate;border-spacing:7pt 0;margin:0 -7pt;width:calc(100% + 14pt)}" +
        ".kc{width:25%;background:#F5F9FF;border:.6pt solid #D5E4F7;border-radius:7pt;padding:7pt 8pt;" +
        "vertical-align:top}.kc table{width:100%}.kc td{vertical-align:top}.kc .ic{width:26pt}" +
        ".ci{display:inline-block;width:22pt;height:22pt;border-radius:11pt;text-align:center;" +
        "padding-top:3.5pt}.kl{font-size:8.5pt;color:#44546F}.kvv{font:700 13.5pt " +
        SANS +
        ";color:#17428A;line-height:1.25;white-space:nowrap}.ks{font-size:8pt;color:#5B6B85}",
      ".two{border-collapse:separate;border-spacing:0}.two>tbody>tr>td{vertical-align:top}" +
        ".card{background:#fff;border:.6pt solid #D5E4F7;border-radius:7pt;padding:7pt 9pt}.gap{width:10pt}",
      ".leg{text-align:center;font-size:8.5pt;margin-top:2pt}.leg i{display:inline-block;width:14pt;" +
        "height:3pt;margin:0 3pt 2pt 8pt;vertical-align:middle}",
      ".dn td{vertical-align:middle}.dn .dg{width:104pt}.lgt td{padding:2pt 3pt;font-size:9pt}" +
        ".lgt .sq{width:12pt}.lgt .sq i{display:inline-block;width:8pt;height:8pt;border-radius:2pt}" +
        ".lgt .r{text-align:right}",
      ".sb td{text-align:center;vertical-align:bottom;padding:0 8pt}.sb .n{font-size:9pt;font-weight:700}" +
        ".sb .col{width:70%;margin:0 auto;border-radius:2pt 2pt 0 0}.sb td.lb{font-size:8.5pt;" +
        "padding-top:3pt;vertical-align:top}.sb tr:first-child td{border-bottom:.6pt solid #9AAAC2}",
      ".lr{margin-bottom:6pt;break-inside:avoid;page-break-inside:avoid}.lh td{padding:0;font-size:9.5pt}" +
        ".lh .r{text-align:right}.lr .m{font-size:8.5pt;color:#44546F}.rb{background:#E6ECF5;height:6pt;" +
        "border-radius:3pt;overflow:hidden;font-size:0;margin-top:2pt}.rb i{display:block;height:6pt}",
      ".dt th{background:#17428A;color:#fff;font-weight:600;font-size:9pt;padding:5pt 6pt;" +
        "text-align:center}.dt td{padding:4pt 6pt;font-size:9pt;border-bottom:.5pt solid #DCE6F4}" +
        ".dt tbody tr:nth-child(even) td{background:#F6F9FE}.dt td.n{text-align:right}.dt .sj{font-size:8pt;" +
        "color:#5B6B85}.dt tr{break-inside:avoid;page-break-inside:avoid}.dt tr.tot td{background:#EAF1FB;" +
        "font-weight:700;color:#17428A}",
      ".cm{border-collapse:separate;border-spacing:8pt;margin:0 -8pt;width:calc(100% + 16pt)}.cb{width:50%;" +
        "background:#F5F9FF;border:.6pt solid #D5E4F7;border-radius:7pt;padding:7pt 10pt;vertical-align:top;" +
        "font-size:9pt}.ct{font:700 10pt " +
        SERIF +
        ";color:#17428A;margin-bottom:3pt}",
      ".cl{background:#EAF1FB;border-radius:7pt;padding:8pt 11pt;font-size:9.5pt;line-height:1.5}" +
        ".none{font-style:italic;color:#5B6B85}",
      ".sg{margin-top:12pt;break-inside:avoid;page-break-inside:avoid}.sg .dl{font:italic 9.5pt " +
        SERIF +
        ";margin-bottom:6pt}.sg td{width:50%;text-align:center;vertical-align:top}.sg b{display:block;" +
        "font-size:9pt;letter-spacing:.04em;color:#17428A}.sg i{font-size:8.5pt;color:#5B6B85;display:block}" +
        ".sg .sp{height:42pt}.sg .nm{font-weight:700;font-size:9.5pt}",
    ].join("");
    var title = "Báo cáo thống kê hệ thống - " + label;
    return (
      '<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>' +
      esc(title) +
      "</title><style>" +
      css +
      "</style></head><body>" +
      '<table class="hd"><tr><td class="lg">' +
      (logo ? '<img src="' + logo + '" alt="">' : "") +
      '</td><td class="org"><b>ĐẠI HỌC KINH TẾ QUỐC DÂN</b><span>National Economics University</span></td>' +
      '<td class="sys">Hệ thống NEU Feedback</td></tr></table><div class="hl"></div>' +
      '<div class="ti"><div class="t1">BÁO CÁO THỐNG KÊ HOẠT ĐỘNG</div><div class="t2">' +
      'HỆ THỐNG NEU FEEDBACK</div><p class="st">' +
      '(Tổng hợp tình hình hỏi – đáp giữa sinh viên và giảng viên)</p><p class="st">Thời gian báo cáo: ' +
      esc(yr ? (data.term ? "Năm học " + yr + ", " + label : "Năm học " + yr) : label) +
      "</p></div>" +
      '<table class="info"><tr><td class="b1"><table class="kvt"><tr><td class="k">Thời gian báo cáo</td>' +
      '<td class="v">' +
      esc(period) +
      '</td></tr><tr><td class="k">Năm học</td><td class="v">' +
      esc(yr || "—") +
      '</td></tr><tr><td class="k">Học kỳ</td><td class="v">' +
      esc(termTxt) +
      '</td></tr><tr><td class="k">Phạm vi</td><td class="v">' +
      T.classes +
      " lớp · " +
      T.lecturers +
      " giảng viên · " +
      T.students +
      ' sinh viên</td></tr></table></td><td class="gap"></td>' +
      '<td class="b2"><div class="it">Giới thiệu</div><p>' +
      "Báo cáo tổng hợp tình hình hoạt động của hệ thống NEU Feedback trong khoảng thời gian đã chọn, gồm số lượng câu hỏi, tỷ lệ và thời gian phản hồi của giảng viên, nhằm phục vụ công tác quản lý và nâng cao chất lượng tương tác giữa sinh viên và giảng viên.</p>" +
      "</td></tr></table>" +
      '<div class="blk">' +
      sec(1, "TỔNG QUAN HOẠT ĐỘNG") +
      kpis +
      "</div>" +
      "<div>" +
      sec(2, "BIỂU ĐỒ THỐNG KÊ") +
      '<table class="two"><tr><td style="width:58%"><div class="card blk"><div class="bt">' +
      "2.1. Xu hướng số lượng câu hỏi theo tuần học</div>" +
      lineChart() +
      '</div></td><td class="gap"></td><td><div class="card blk"><div class="bt">2.2. Phân bố câu hỏi theo lớp</div>' +
      donut() +
      "</div></td></tr></table>" +
      '<table class="two" style="margin-top:8pt"><tr><td style="width:42%"><div class="card blk">' +
      '<div class="bt">2.3. Tình hình xử lý câu hỏi</div>' +
      statusBars() +
      '</div></td><td class="gap"></td><td><div class="card blk"><div class="bt">' +
      "2.4. Giảng viên phản hồi thế nào?</div>" +
      lecturers() +
      "</div></td></tr></table>" +
      '<div class="blk" style="margin-top:8pt"><div class="bt">2.5. Thống kê chi tiết theo lớp</div>' +
      table() +
      "</div></div>" +
      '<div class="blk">' +
      sec(3, "NHẬN XÉT VÀ ĐÁNH GIÁ") +
      comments +
      "</div>" +
      '<div class="blk">' +
      sec(4, "KẾT LUẬN") +
      '<div class="cl">' +
      concl +
      "</div></div>" +
      '<div class="sg"><p class="dl">' +
      dateLine +
      '</p><table><tr><td><b>NGƯỜI LẬP BÁO CÁO</b><i>(Ký, ghi rõ họ tên)</i><div class="sp"></div>' +
      '<span class="nm">Quản trị viên</span></td><td><b>XÁC NHẬN CỦA ĐƠN VỊ</b><i>(Ký, đóng dấu)</i>' +
      '<div class="sp"></div></td></tr></table></div>' +
      "</body></html>"
    );
  }

  function printReport(html, title) {
    var prev = document.getElementById("reportFrame");
    if (prev) prev.remove();
    var f = document.createElement("iframe");
    f.id = "reportFrame";
    f.setAttribute("aria-hidden", "true");
    f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden";
    document.body.appendChild(f);
    var d = f.contentWindow.document;
    d.open();
    d.write(html);
    d.close();
    var oldTitle = document.title;
    document.title = title; // tên file PDF mặc định lấy từ tiêu đề trang
    function restore() {
      document.title = oldTitle;
    }
    f.contentWindow.onafterprint = restore;
    setTimeout(restore, 120000);
    setTimeout(function () {
      f.contentWindow.focus();
      f.contentWindow.print();
    }, 300);
  }

  async function adminStats() {
    var data = null,
      sortKey = "questions",
      sortDir = -1;
    function rateColor(p) {
      return p >= 80 ? "#16A34A" : p >= 50 ? "#F59E0B" : "#DC2626";
    }
    function query() {
      var q = ["year=" + encodeURIComponent(val("stYear") || "")];
      if (val("stSem")) q.push("term=" + val("stSem"));
      if (val("stFac")) q.push("faculty=" + encodeURIComponent(val("stFac")));
      if (val("stLecSel")) q.push("lecturer_id=" + val("stLecSel"));
      return "?" + q.join("&");
    }
    async function load(q) {
      data = await API.get("/api/admin/stats" + (q || ""));
      var F = data.filters;
      $("#stFac").innerHTML =
        '<option value="">Tất cả khoa</option>' +
        F.faculties
          .map(function (x) {
            return "<option" + (x === F.faculty ? " selected" : "") + ">" + esc(x) + "</option>";
          })
          .join("");
      $("#stLecSel").innerHTML =
        '<option value="">Tất cả Giảng viên</option>' +
        F.lecturers
          .map(function (x) {
            return (
              '<option value="' +
              x.id +
              '"' +
              (x.id === F.lecturer_id ? " selected" : "") +
              ">" +
              esc(x.name) +
              "</option>"
            );
          })
          .join("");
      $("#stYear").innerHTML =
        data.years
          .map(function (y) {
            return "<option" + (y === data.year ? " selected" : "") + ">" + esc(y) + "</option>";
          })
          .join("") || "<option>—</option>";
      $("#stSem").innerHTML =
        '<option value="">Cả năm học</option>' +
        data.semesters
          .map(function (x) {
            return (
              '<option value="' +
              x.term +
              '"' +
              (x.term === data.term ? " selected" : "") +
              ">" +
              esc(x.label) +
              "</option>"
            );
          })
          .join("");
      var T = data.total,
        R = data.range;
      txt(
        "stRangeText",
        R && !R.from
          ? R.label + " · Chưa có dữ liệu"
          : R
            ? R.label +
              " · " +
              T.classes +
              " lớp, " +
              T.lecturers +
              " Giảng viên, " +
              T.students +
              " sinh viên"
            : 'Chưa có học kỳ nào — bấm "Quản lý học kỳ" để khai báo.',
      );
      var AI = data.ai,
        GP = AI.grouping;
      set(
        "stKpis",
        kpi(num(T.questions), "Tổng câu hỏi", "chat", "blue", T.classes + " lớp") +
          kpi(
            T.answer_rate + "%",
            "Tỷ lệ phản hồi",
            "check",
            "green",
            num(T.answered) + " câu đã trả lời",
          ) +
          kpi(
            dur(T.avg_response_seconds),
            "Phản hồi trung bình",
            "clock",
            "amber",
            "Từ lúc hỏi đến lúc trả lời",
          ) +
          kpi(
            GP.accuracy == null ? "—" : GP.accuracy + "%",
            "Độ chính xác gom nhóm AI",
            "group",
            "violet",
            GP.confirmed + " nhóm xác nhận · " + GP.rejected + " từ chối",
          ),
      );
      set(
        "stDay",
        data.by_day.some(function (d) {
          return d.questions;
        })
          ? trendSVG(data.by_day, true)
          : empty("Chưa có câu hỏi."),
      );
      var tt = T.questions || 1,
        pa = (T.answered * 100) / tt,
        pw = ((T.answered + T.waiting) * 100) / tt,
        pf = ((T.answered + T.waiting + T.flagged) * 100) / tt;
      $("#stDonut").style.background =
        "conic-gradient(var(--accent) 0 " +
        pa +
        "%,var(--amber) 0 " +
        pw +
        "%,var(--red) 0 " +
        pf +
        "%,#98A2B3 0)";
      $("#stDonut").setAttribute("data-total", num(T.questions));
      set(
        "stLegend",
        [
          ["var(--accent)", "Đã phản hồi", T.answered],
          ["var(--amber)", "Chờ phản hồi", T.waiting],
          ["var(--red)", "Bị gắn cờ", T.flagged],
          ["#98A2B3", "Đã ẩn", T.hidden],
        ]
          .map(function (x) {
            return (
              '<p><span class="legend" style="background:' +
              x[0] +
              '"></span>' +
              x[1] +
              "<b>" +
              num(x[2]) +
              "</b></p>"
            );
          })
          .join(""),
      );
      set(
        "stFaculty",
        data.by_faculty
          .map(function (x) {
            return (
              '<div class="lect-row"><div class="lr-head"><b>' +
              esc(x.faculty) +
              '</b><span><b style="color:' +
              rateColor(x.answer_rate) +
              '">' +
              x.answer_rate +
              "%</b> phản hồi</span></div>" +
              '<div class="lr-meta">' +
              x.class_count +
              " lớp · " +
              x.questions +
              " câu hỏi · " +
              x.waiting +
              " đang chờ · phản hồi TB " +
              dur(x.avg_response_seconds) +
              "</div>" +
              '<div class="rate-bar"><i style="width:' +
              x.answer_rate +
              "%;background:" +
              rateColor(x.answer_rate) +
              '"></i></div></div>'
            );
          })
          .join("") || empty("Chưa có dữ liệu."),
      );
      var DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
        hmax = Math.max.apply(null, [].concat.apply([], data.heatmap).concat([1]));
      var hh = '<div class="heat"><span></span>';
      for (var hr = 0; hr < 24; hr++) hh += "<small>" + (hr % 3 === 0 ? hr : "") + "</small>";
      data.heatmap.forEach(function (row, d) {
        hh += "<b>" + DAYS[d] + "</b>";
        row.forEach(function (n, hr2) {
          hh +=
            '<i title="' +
            DAYS[d] +
            ", " +
            hr2 +
            "h: " +
            n +
            ' câu hỏi" style="opacity:' +
            (n ? (0.18 + (0.82 * n) / hmax).toFixed(2) : 0.06) +
            '"></i>';
        });
      });
      set("stHeat", hh + "</div>");
      set(
        "stKeywords",
        data.keywords
          .map(function (k) {
            return (
              '<div class="kw-row"><b>Tuần ' +
              k.week +
              '</b><span class="tiny muted">' +
              k.questions +
              " câu hỏi</span><div>" +
              k.top
                .map(function (x) {
                  return '<span class="kw">' + esc(x.term) + " <em>" + x.count + "</em></span>";
                })
                .join("") +
              "</div></div>"
            );
          })
          .join("") || empty("Chưa đủ câu hỏi để rút ra chủ đề."),
      );
      set(
        "stAIKpis",
        kpi(
          GP.accuracy == null ? "—" : GP.accuracy + "%",
          "Độ chính xác gom nhóm",
          "check",
          "green",
          "Nhóm được xác nhận ÷ nhóm đã xử lý",
        ) +
          kpi(
            num(AI.reused_answers),
            "Câu trả lời tự động",
            "reply",
            "blue",
            "Trả lời từ câu đã có hoặc từ nhóm",
          ) +
          kpi(
            GP.confirmed + "/" + GP.rejected,
            "Nhóm xác nhận / từ chối",
            "layers",
            "violet",
            num(GP.suggested) + " nhóm đang chờ duyệt",
          ) +
          kpi(
            AI.chat_avg_seconds == null ? "—" : AI.chat_avg_seconds + " giây",
            "NEU AI trả lời trung bình",
            "clock",
            "amber",
            num(AI.chat_answers) + " lượt trả lời",
          ),
      );
      set(
        "stWeek",
        data.by_week.some(function (w) {
          return w.questions;
        })
          ? data.by_week
              .map(function (w, i) {
                var mx = Math.max.apply(
                  null,
                  data.by_week
                    .map(function (x) {
                      return x.questions;
                    })
                    .concat([1]),
                );
                return (
                  '<div class="sb' +
                  (w.learned ? "" : " future") +
                  '" title="Tuần ' +
                  w.number +
                  ": " +
                  w.questions +
                  " câu hỏi, " +
                  w.answered +
                  ' đã trả lời"><div class="sb-col" style="height:' +
                  ((w.questions * 100) / mx).toFixed(1) +
                  "%;animation-delay:" +
                  (0.05 + i * 0.04).toFixed(2) +
                  's">' +
                  '<span class="sb-a" style="height:' +
                  (w.questions ? (w.answered * 100) / w.questions : 0).toFixed(1) +
                  '%"></span><span class="sb-w"></span><em>' +
                  (w.questions || "") +
                  '</em></div><small class="sb-label">' +
                  (w.learned ? "T" + w.number : "T" + w.number + "·") +
                  "</small></div>"
                );
              })
              .join("")
          : empty("Chưa có câu hỏi trong khoảng thời gian này."),
      );
      var mxc = Math.max.apply(
        null,
        data.by_class
          .map(function (c) {
            return c.questions;
          })
          .concat([1]),
      );
      set(
        "stClassBars",
        data.by_class
          .map(function (c) {
            return (
              '<div class="hbar" title="' +
              esc(c.subject) +
              " · " +
              c.questions +
              " câu hỏi, " +
              c.waiting +
              ' đang chờ"><b>' +
              esc(c.code) +
              '</b><div class="hb-track"><i style="width:' +
              (((c.questions - c.waiting) * 100) / mxc).toFixed(1) +
              "%;background:" +
              colorOf(c.id) +
              '"></i>' +
              '<i style="width:' +
              ((c.waiting * 100) / mxc).toFixed(1) +
              '%;background:#F2A93B"></i></div><span class="hb-num">' +
              c.questions +
              " câu</span></div>"
            );
          })
          .join("") +
          (data.by_class.length
            ? '<p class="tiny muted" style="margin-top:6px">Phần màu cam: câu hỏi đang chờ trả lời</p>'
            : empty("Chưa có lớp nào.")),
      );
      set(
        "stLect",
        data.by_lecturer
          .map(function (l) {
            return (
              '<div class="lect-row"><div class="lr-head"><b>Giảng viên ' +
              esc(l.name) +
              '</b><span><b style="color:' +
              rateColor(l.answer_rate) +
              '">' +
              l.answer_rate +
              "%</b> phản hồi</span></div>" +
              '<div class="lr-meta">' +
              l.class_codes.join(", ") +
              " · " +
              l.questions +
              " câu hỏi · " +
              l.waiting +
              " đang chờ · phản hồi trung bình " +
              dur(l.avg_response_seconds) +
              "</div>" +
              '<div class="rate-bar"><i style="width:' +
              l.answer_rate +
              "%;background:" +
              rateColor(l.answer_rate) +
              '"></i></div></div>'
            );
          })
          .join("") || empty("Chưa có dữ liệu."),
      );
      table();
      if (data.empty) {
        var msg = empty("Chưa có dữ liệu cho " + (R ? R.label : "khoảng thời gian này") + ".");
        set("stWeek", msg);
        set("stDay", msg);
        set("stClassBars", msg);
        set("stLect", msg);
        set("stClassTable", '<tr><td colspan="8">' + msg + "</td></tr>");
      }
    }
    function table() {
      var rows = data.by_class.slice().sort(function (a, b) {
        var x = a[sortKey],
          y = b[sortKey];
        x = x == null ? -1 : x;
        y = y == null ? -1 : y;
        return (x > y ? 1 : x < y ? -1 : 0) * sortDir;
      });
      set(
        "stClassTable",
        rows
          .map(function (c) {
            return (
              '<tr><td><span class="src-dot" style="background:' +
              colorOf(c.id) +
              ';display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px"></span><b>' +
              esc(c.code) +
              '</b><div class="meta">' +
              esc(c.subject) +
              "</div></td>" +
              "<td>" +
              esc(c.lecturer) +
              "</td><td>" +
              c.students +
              "</td><td>" +
              c.questions +
              "</td><td>" +
              c.answered +
              "</td><td" +
              (c.waiting ? ' style="color:#B45309;font-weight:600"' : "") +
              ">" +
              c.waiting +
              "</td>" +
              '<td><b style="color:' +
              rateColor(c.answer_rate) +
              '">' +
              c.answer_rate +
              "%</b></td><td>" +
              dur(c.avg_response_seconds) +
              "</td></tr>"
            );
          })
          .join("") ||
          '<tr><td colspan="8">' + empty("Chưa có lớp nào trong học kỳ này.") + "</td></tr>",
      );
      $$("#stTableEl th[data-sort]").forEach(function (th) {
        th.classList.toggle("asc", th.dataset.sort === sortKey && sortDir > 0);
        th.classList.toggle("desc", th.dataset.sort === sortKey && sortDir < 0);
      });
    }
    $("#stYear").onchange = function () {
      $("#stSem").value = "";
      $("#stFac").value = "";
      $("#stLecSel").value = "";
      load(query()).catch(fail);
    };
    ["stSem", "stFac", "stLecSel"].forEach(function (id) {
      $("#" + id).onchange = function () {
        load(query()).catch(fail);
      };
    });
    $("#stTableEl thead").addEventListener("click", function (e) {
      var th = e.target.closest("th[data-sort]");
      if (!th) return;
      if (sortKey === th.dataset.sort) sortDir = -sortDir;
      else {
        sortKey = th.dataset.sort;
        sortDir = -1;
      }
      table();
    });
    $("#stExport").onclick = async function () {
      if (!data) return;
      var logo = await logoDataURI();
      printReport(
        statsReportHTML(data, logo),
        "Bao-cao-thong-ke-" + (data.range ? data.range.label.replace(/\s+/g, "-") : "neu"),
      );
      toast('Trong hộp thoại in, chọn "Lưu dưới dạng PDF"');
    };
    await load("");
  }
  NEU.adminStats = adminStats;
  NEU.pages.adminStats = adminStats;
})((window.NEU = window.NEU || {}));
