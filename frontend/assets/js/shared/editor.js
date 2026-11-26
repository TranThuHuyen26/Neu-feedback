/* Ô soạn thảo (đậm, nghiêng, danh sách, ảnh) và các hàm hỗ trợ tệp đính kèm. */
(function (NEU) {
  "use strict";
  var $ = NEU.$,
    $$ = NEU.$$,
    P = NEU.P,
    d = NEU.d,
    esc = NEU.esc,
    fail = NEU.fail;

  // ---- Ô soạn thảo kiểu Word (WYSIWYG). Nội dung vẫn LƯU dạng Markdown gọn (**đậm**, *nghiêng*, ++gạch chân++, - danh sách,
  //      [liên kết](https://…), ![ảnh](/api/answer-images/N)) nên sinh viên thấy đúng như Giảng viên soạn, câu trả lời cũ mở đúng định dạng.
  var ED_ICONS = {
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    img: P.image,
    ul: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    ol: '<path d="M10 6h10M10 12h10M10 18h10"/><path d="M4 4.5h1.5V9M4 9h3M4 14.5c.4-.6 1-.9 1.6-.9.8 0 1.4.5 1.4 1.2 0 1.2-3 2.1-3 3.7h3"/>',
  };

  var ED_TOOLS = [
    ["b", "In đậm (Ctrl+B)", "<b>B</b>"],
    ["i", "In nghiêng (Ctrl+I)", '<i style="font-family:Georgia,serif">I</i>'],
    ["u", "Gạch chân (Ctrl+U)", "<u>U</u>"],
    ["ul", "Gạch đầu dòng", "ul"],
    ["ol", "Danh sách số", "ol"],
    ["link", "Chèn liên kết", "link"],
    ["img", "Chèn ảnh", "img"],
  ]
    .map(function (x) {
      var inner = ED_ICONS[x[2]]
        ? '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">' + ED_ICONS[x[2]] + "</svg>"
        : x[2];
      return (
        '<button type="button" data-ed="' +
        x[0] +
        '" title="' +
        x[1] +
        '" aria-label="' +
        x[1] +
        '">' +
        inner +
        "</button>"
      );
    })
    .join("");

  function mdToEd(text) {
    var h = NEU.md(text);
    return h.replace(/^<div class="md">/, "").replace(/<\/div>$/, "");
  }

  function edToMd(root) {
    // HTML trong ô soạn → Markdown
    var lines = [],
      cur = "";
    function brk() {
      lines.push(cur);
      cur = "";
    }
    function blockStart() {
      if (cur.trim()) brk();
      else cur = "";
    }
    function inline(n) {
      if (n.nodeType === 3) return n.nodeValue.replace(/ /g, " ").replace(/[\r\n]+/g, " ");
      if (n.nodeType !== 1) return "";
      var tag = n.tagName,
        kids = Array.prototype.map.call(n.childNodes, inline).join(""),
        st = n.getAttribute("style") || "";
      if (tag === "BR") return "\n";
      if (tag === "IMG") {
        var s = n.getAttribute("data-auth-src") || "";
        return /^\/api\/answer-images\/\d+$/.test(s)
          ? "\n![" + (n.alt || "ảnh").replace(/[\[\]()]/g, "") + "](" + s + ")\n"
          : "";
      }
      if (!kids.trim()) return kids;
      function wrap(a, b) {
        var m = kids.match(/^(\s*)([\s\S]*?)(\s*)$/);
        return m[1] + a + m[2] + b + m[3];
      }
      if (tag === "B" || tag === "STRONG" || /font-weight:\s*(bold|[6-9]00)/.test(st))
        kids = wrap("**", "**");
      if (tag === "I" || tag === "EM" || /font-style:\s*italic/.test(st)) kids = wrap("*", "*");
      if (tag === "U" || /text-decoration[^;]*underline/.test(st)) kids = wrap("++", "++");
      if (tag === "A" && /^https?:\/\//.test(n.getAttribute("href") || ""))
        kids =
          "[" +
          kids.replace(/[\[\]]/g, "") +
          "](" +
          n.getAttribute("href").replace(/\s|\)/g, "") +
          ")";
      return kids;
    }
    function block(n) {
      if (n.nodeType !== 1) {
        cur += inline(n);
        return;
      }
      var tag = n.tagName;
      if (tag === "UL" || tag === "OL") {
        blockStart();
        var i = 0;
        Array.prototype.forEach.call(n.children, function (li) {
          if (li.tagName !== "LI") return;
          var t = inline(li).replace(/\n+/g, " ").trim();
          if (!t) return;
          lines.push((tag === "UL" ? "- " : ++i + ". ") + t);
        });
        lines.push("");
        return;
      }
      if (/^(DIV|P|H[1-6]|BLOCKQUOTE|LI|PRE|SECTION|ARTICLE|TABLE|TR)$/.test(tag)) {
        blockStart();
        Array.prototype.forEach.call(n.childNodes, block);
        if (cur.trim()) brk();
        if (tag === "P" || /^H/.test(tag)) lines.push("");
        return;
      }
      cur += inline(n);
    }
    Array.prototype.forEach.call(root.childNodes, block);
    if (cur.trim()) brk();
    return lines
      .join("\n")
      .split("\n")
      .map(function (l) {
        return l.replace(/[ \t]+$/, "");
      })
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function edInit(scope) {
    // gắn .value (đọc/ghi Markdown) và .placeholder cho mọi ô soạn
    $$(".ed-area:not([data-init])", scope).forEach(function (el) {
      el.dataset.init = "1";
      Object.defineProperty(el, "value", {
        configurable: true,
        get: function () {
          return edToMd(el);
        },
        set: function (v) {
          el.innerHTML = v ? mdToEd(v) : "";
          edEmpty(el);
        },
      });
      Object.defineProperty(el, "placeholder", {
        configurable: true,
        get: function () {
          return el.dataset.ph || "";
        },
        set: function (v) {
          el.dataset.ph = v;
        },
      });
      edEmpty(el);
    });
  }

  function edEmpty(el) {
    el.classList.toggle("is-empty", !el.textContent.trim() && !$("img,li", el));
  }

  function edCount(ta) {
    var ed = ta && ta.closest && ta.closest(".editor");
    if (!ed) return;
    var c = $(".ed-count", ed) || (ta.id === "lsReply" ? $("#lsCount") : null);
    if (!c) return;
    var max = +(ed.dataset.max || 5000),
      n = ta.value.length;
    c.textContent = n + "/" + max;
    c.classList.toggle("over", n > max);
  }

  function edInsert(html) {
    document.execCommand("insertHTML", false, html);
  }

  function edApply(area, k) {
    if (!area) return;
    area.focus();
    try {
      document.execCommand("styleWithCSS", false, false);
    } catch (e) {
      /* trình duyệt cũ */
    }
    if (k === "b") document.execCommand("bold");
    else if (k === "i") document.execCommand("italic");
    else if (k === "u") document.execCommand("underline");
    else if (k === "ul") document.execCommand("insertUnorderedList");
    else if (k === "ol") document.execCommand("insertOrderedList");
    else if (k === "link") {
      var s = window.getSelection(),
        range = s.rangeCount ? s.getRangeAt(0).cloneRange() : null,
        text = s.toString();
      var url = prompt("Nhập địa chỉ liên kết (bắt đầu bằng https://)", "https://");
      if (!url || !/^https?:\/\/\S+$/.test(url.trim())) {
        if (url && url !== "https://")
          toast("Liên kết phải bắt đầu bằng http:// hoặc https://", "error");
        return;
      }
      url = url.trim();
      area.focus();
      if (range) {
        s.removeAllRanges();
        s.addRange(range);
      }
      if (text) document.execCommand("createLink", false, url);
      else
        edInsert(
          '<a href="' +
            esc(url) +
            '" target="_blank" rel="noopener noreferrer">' +
            esc(url) +
            "</a>&nbsp;",
        );
    } else if (k === "img") {
      var sel = window.getSelection(),
        saved =
          sel.rangeCount && area.contains(sel.anchorNode) ? sel.getRangeAt(0).cloneRange() : null;
      var inp = document.createElement("input");
      inp.type = "file";
      inp.accept = "image/png,image/jpeg,image/webp,image/gif";
      inp.onchange = async function () {
        var f = inp.files[0];
        if (!f) return;
        if (f.size > 5 * 1024 * 1024) {
          toast("Ảnh vượt quá 5 MB", "error");
          return;
        }
        try {
          var fd = new FormData();
          fd.append("class_id", window.__edClassId);
          fd.append("file", f);
          var r = await API.form("/api/answer-images", fd);
          area.focus();
          var s2 = window.getSelection();
          s2.removeAllRanges();
          if (saved) s2.addRange(saved);
          else {
            var rg = document.createRange();
            rg.selectNodeContents(area);
            rg.collapse(false);
            s2.addRange(rg);
          }
          edInsert(
            '<img class="ans-img" alt="' +
              esc(f.name.replace(/[\[\]()]/g, "")) +
              '" data-auth-src="' +
              esc(r.url) +
              '"><br>',
          );
          area.dispatchEvent(new Event("input", { bubbles: true }));
          toast("Đã chèn ảnh vào câu trả lời");
        } catch (err) {
          fail(err);
        }
      };
      inp.click();
      return;
    }
    area.dispatchEvent(new Event("input", { bubbles: true }));
    edTools();
  }

  function edTools() {
    // nút đang bật (đậm/nghiêng/…) theo vị trí con trỏ
    var a = document.activeElement;
    if (!a || !a.classList || !a.classList.contains("ed-area")) return;
    var ed = a.closest(".editor");
    if (!ed) return;
    [
      ["b", "bold"],
      ["i", "italic"],
      ["u", "underline"],
      ["ul", "insertUnorderedList"],
      ["ol", "insertOrderedList"],
    ].forEach(function (x) {
      var b = $('[data-ed="' + x[0] + '"]', ed);
      var on = false;
      try {
        on = document.queryCommandState(x[1]);
      } catch (e) {
        /* bỏ qua */
      }
      if (b) b.classList.toggle("on", on);
    });
  }

  document.addEventListener("selectionchange", edTools);

  document.addEventListener("mousedown", function (e) {
    if (e.target.closest("[data-ed]")) e.preventDefault();
  });
  // giữ vùng chữ đang chọn
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-ed]");
    if (b) {
      e.preventDefault();
      edInit();
      edApply($(".ed-area", b.closest(".editor")), b.dataset.ed);
    }
  });

  document.addEventListener("input", function (e) {
    if (e.target.classList && e.target.classList.contains("ed-area")) {
      edEmpty(e.target);
      edCount(e.target);
    }
  });

  document.addEventListener("paste", function (e) {
    // dán: chỉ giữ đậm/nghiêng/gạch chân/danh sách/liên kết, bỏ màu, cỡ chữ, font lạ
    var area = e.target.closest && e.target.closest(".ed-area");
    if (!area) return;
    e.preventDefault();
    var cd = e.clipboardData,
      html = cd.getData("text/html"),
      text = cd.getData("text/plain"),
      out;
    if (html) {
      var tmp = document.createElement("div");
      tmp.innerHTML = html
        .replace(/<!--[\s\S]*?-->/g, "")
        .replace(/<(style|script|meta|title|head)[\s\S]*?<\/\1>/gi, "");
      $$("img", tmp).forEach(function (im) {
        if (!/^\/api\/answer-images\/\d+$/.test(im.getAttribute("data-auth-src") || ""))
          im.remove();
      });
      out = mdToEd(edToMd(tmp));
    } else
      out = esc(text || "")
        .replace(/\r/g, "")
        .replace(/\n/g, "<br>");
    edInsert(out);
  });

  document.addEventListener("keydown", function (e) {
    // phím tắt Ctrl+B/I/U đã có sẵn; Tab trong danh sách → thụt lề không cần
    if (
      e.target.classList &&
      e.target.classList.contains("ed-area") &&
      (e.ctrlKey || e.metaKey) &&
      e.key.toLowerCase() === "k"
    ) {
      e.preventDefault();
      edApply(e.target, "link");
    }
  });

  function authFetch(url) {
    return fetch(url, {
      headers: { Authorization: "Bearer " + (localStorage.getItem("neu_token") || "") },
    });
  }

  function hydrateImgs() {
    $$("img[data-auth-src]:not([data-loaded])").forEach(function (img) {
      img.dataset.loaded = "1";
      authFetch(img.dataset.authSrc)
        .then(function (r) {
          return r.ok ? r.blob() : null;
        })
        .then(function (b) {
          if (b) img.src = URL.createObjectURL(b);
          else img.alt = "(Không tải được ảnh)";
        });
    });
  }

  new MutationObserver(function () {
    hydrateImgs();
    edInit();
  }).observe(document.documentElement, { childList: true, subtree: true });

  document.addEventListener("click", async function (e) {
    var d = e.target.closest("[data-dl]");
    if (d) {
      e.preventDefault();
      try {
        var r = await authFetch(d.dataset.dl);
        if (!r.ok) throw new Error("Không tải được tệp");
        var bl = await r.blob(),
          a = document.createElement("a");
        a.href = URL.createObjectURL(bl);
        a.download = d.dataset.name || "tep";
        a.click();
      } catch (err) {
        fail(err);
      }
    }
    var k = e.target.closest("[data-kebab]");
    $$(".pop-menu").forEach(function (m) {
      if (!k || m !== k.nextElementSibling) m.hidden = true;
    });
    if (k) {
      e.stopPropagation();
      k.nextElementSibling.hidden = !k.nextElementSibling.hidden;
    }
  });

  function fsize(b) {
    b = b || 0;
    return b >= 1048576
      ? (b / 1048576).toFixed(1) + " MB"
      : Math.max(1, Math.round(b / 1024)) + " KB";
  }

  function initLiveSearch() {
    if (!NEU.state.user || NEU.state.user.role === "admin") return;
    var inp = $(".topbar .search input");
    if (!inp) return;
    var pop = document.createElement("div");
    pop.className = "search-pop";
    pop.hidden = true;
    inp.closest(".search").appendChild(pop);
    var tm = null,
      seq = 0,
      L = NEU.state.user.role === "lecturer";
    async function run() {
      var q = inp.value.trim();
      if (q.length < 2) {
        pop.hidden = true;
        return;
      }
      var my = ++seq,
        r = await API.get("/api/search?q=" + encodeURIComponent(q));
      if (my !== seq) return;
      var h = "";
      if (r.classes.length)
        h +=
          "<h6>Lớp học</h6>" +
          r.classes
            .map(function (c) {
              return (
                '<a href="' +
                (L ? "lecturer-class.html" : "student-class.html") +
                "?class=" +
                c.id +
                '">' +
                esc(c.code + " · " + c.subject) +
                "<small>" +
                esc(c.semester) +
                "</small></a>"
              );
            })
            .join("");
      if (r.weeks.length)
        h +=
          "<h6>Tuần học</h6>" +
          r.weeks
            .map(function (w) {
              return (
                '<a href="' +
                (L ? "lecturer-week.html" : "student-week.html") +
                "?week=" +
                w.id +
                '">' +
                esc(w.class_code + " · " + w.unit_label + " " + w.number) +
                "<small>" +
                esc(w.title || "") +
                "</small></a>"
              );
            })
            .join("");
      if (r.materials.length)
        h +=
          "<h6>Tài liệu</h6>" +
          r.materials
            .map(function (m) {
              return (
                '<a href="' +
                (L
                  ? "lecturer-week.html?week=" + m.week_id + "&tab=docs"
                  : "student-week.html?week=" + m.week_id) +
                '">' +
                esc(m.filename) +
                "<small>" +
                esc(m.class_code) +
                (m.week_number ? " · Tuần " + m.week_number : "") +
                "</small></a>"
              );
            })
            .join("");
      pop.innerHTML = h || "<p>Không tìm thấy kết quả cho “" + esc(q) + "”</p>";
      pop.hidden = false;
    }
    inp.addEventListener("input", function () {
      clearTimeout(tm);
      tm = setTimeout(function () {
        run().catch(function () {});
      }, 250);
    });
    inp.addEventListener("focus", function () {
      if (inp.value.trim().length >= 2) run().catch(function () {});
    });
    inp.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        var a = $("a", pop);
        if (a) {
          e.preventDefault();
          location.href = a.href;
        }
      }
      if (e.key === "Escape") {
        pop.hidden = true;
        inp.blur();
      }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".topbar .search")) pop.hidden = true;
    });
  }

  function aiText(text) {
    // tách phần "Kiến thức bổ sung:" thành khối riêng có ghi chú rõ
    var t = String(text || ""),
      k = t.search(/Kiến thức bổ sung\s*:/i);
    if (k < 0) return NEU.md(t);
    var main = t.slice(0, k).trim(),
      extra = t
        .slice(k)
        .replace(/^Kiến thức bổ sung\s*:\s*/i, "")
        .trim();
    return (
      NEU.md(main) +
      '<div class="ai-extra"><div class="ax-head">Kiến thức bổ sung — không có trong tài liệu lớp</div>' +
      NEU.md(extra) +
      "</div>"
    );
  }
  NEU.ED_TOOLS = ED_TOOLS;
  NEU.aiText = aiText;
  NEU.edCount = edCount;
  NEU.edInit = edInit;
  NEU.fsize = fsize;
  NEU.hydrateImgs = hydrateImgs;
  NEU.initLiveSearch = initLiveSearch;
  NEU.mdToEd = mdToEd;
})((window.NEU = window.NEU || {}));
