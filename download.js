/* ============================================================
   Waylore · 客行录 — 下载页交互
   卡片渲染 + 3D 倾斜聚光 + 磁吸按钮 + 系统识别
   ============================================================ */
(function () {
  "use strict";

  var GH = "https://github.com/changanhe1205-afk/kexinglu";
  var DL = GH + "/releases/download";

  var ICONS = {
    windows: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="8" height="7.5" rx="1.6"/><rect x="13" y="4" width="8" height="7.5" rx="1.6"/><rect x="3" y="12.5" width="8" height="7.5" rx="1.6"/><rect x="13" y="12.5" width="8" height="7.5" rx="1.6"/></svg>',
    macos: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16.3 12.3c0 3.2-2.4 5.7-5.4 5.7s-5.4-2.5-5.4-5.7 2.4-5.7 5.4-5.7 5.4 2.5 5.4 5.7Z"/><path d="M14.6 5.3c.8-1 1.4-2.2 1.2-3.4-1.2.1-2.6.9-3.4 1.9-.7.8-1.3 2.1-1.1 3.2 1.3.1 2.6-.7 3.3-1.7Z"/></svg>',
    linux: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4.5" width="18" height="15" rx="2.4"/><path d="M7 9.5l3 2.8-3 2.8"/><path d="M12.5 15.5H17"/></svg>',
    android: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="8.5" width="12" height="9" rx="2.2"/><path d="M9.5 6.5v-2.2M14.5 6.5v-2.2"/><circle cx="9.6" cy="11.4" r="0.4" fill="currentColor"/><circle cx="14.4" cy="11.4" r="0.4" fill="currentColor"/></svg>',
    download: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12m0 0l-5-5m5 5l5-5"/><path d="M4 21h16"/></svg>',
    arrow: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m0 0l-6-6m6 6l-6 6"/></svg>'
  };

  /* 四个平台 · 各一个下载 */
  var PLATFORMS = [
    {
      id: "windows", name: "Windows", req: "Windows 10 / 11 · x64",
      size: "82.8 MB", date: "2026-10-22",
      file: "Kexinglu-Setup-1.0.0.exe",
      url: DL + "/v1.0.0-build32/Kexinglu-Setup-1.0.0.exe",
      sha: "5d3635e482540a5329b0d3b4ab511bc824e93e78bb4118f3f8d44458a939fd34"
    },
    {
      id: "android", name: "Android", req: "Android 8.0+ · 手机 / 平板",
      size: "44.6 MB", date: "2026-10-22",
      file: "Kexinglu-Android-1.0.0.apk",
      url: DL + "/v1.0.0-build32/Kexinglu-Android-1.0.0.apk",
      sha: "980125ad2f464a3697cca9bab0ee7ec2757d5cc040e665d4e28d96cc6312aa92"
    },
    {
      id: "macos", name: "macOS", req: "macOS 15 · Apple Silicon",
      size: "90.6 MB", date: "2026-10-23",
      file: "Kexinglu-macOS-1.0.0-arm64-unsigned.zip",
      url: DL + "/v1.0.0-macos-preview1/Kexinglu-macOS-1.0.0-arm64-unsigned.zip",
      sha: "501bff00bd9dbb035cbe6ee8cae4114fff7e085d49b0b58ef66d8423adbf4087",
      secondary: {
        label: "Intel 芯片（x86_64）版",
        file: "Kexinglu-macOS-1.0.0-x86_64-unsigned.zip",
        url: DL + "/v1.0.0-macos-preview1/Kexinglu-macOS-1.0.0-x86_64-unsigned.zip"
      }
    },
    {
      id: "linux", name: "Linux", req: "Ubuntu 22.04+ · x64",
      size: "84.2 MB", date: "2026-10-22",
      file: "Kexinglu-Linux-1.0.0-amd64.deb",
      url: DL + "/v1.0.0-build32/Kexinglu-Linux-1.0.0-amd64.deb",
      sha: "a9db713cf99de2b2d195ab2a73f7d2fa2fbbf3d03f2463ebf165ce3ba891e83c",
      secondary: {
        label: "便携版 TAR.GZ",
        file: "Kexinglu-Linux-1.0.0-x86_64.tar.gz",
        url: DL + "/v1.0.0-build32/Kexinglu-Linux-1.0.0-x86_64.tar.gz"
      }
    }
  ];

  var SCREENSHOTS = [
    { src: "assets/screenshots/home.webp", alt: "首页：问候、实时天气、每日一句与快捷记录", caption: "首页 · 天气与记录入口" },
    { src: "assets/screenshots/travel.webp", alt: "旅途：地图与故事", caption: "旅途 · 地图与故事" },
    { src: "assets/screenshots/tickets.webp", alt: "票夹：可翻面的票根", caption: "票夹 · 可翻面的票根" },
    { src: "assets/screenshots/collection.webp", alt: "收藏：影视与食光", caption: "收藏 · 影视与食光" },
    { src: "assets/screenshots/profile.webp", alt: "我的：旅人档案", caption: "我的 · 旅人档案" },
    { src: "assets/screenshots/search.webp", alt: "城市搜索：全国区县", caption: "城市搜索 · 全国区县" }
  ];

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  var toastTimer = null;
  function toast(msg) {
    var el = $("#toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("show"); }, 2400);
  }

  function copyText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }
  function fallbackCopy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    done();
  }

  function findPlatform(id) {
    for (var i = 0; i < PLATFORMS.length; i++) if (PLATFORMS[i].id === id) return PLATFORMS[i];
    return PLATFORMS[0];
  }

  function detectOS() {
    var ua = navigator.userAgent || "";
    if (/Windows/i.test(ua)) return "windows";
    if (/Android/i.test(ua)) return "android";
    if (/iPhone|iPad|iPod|Macintosh|Mac OS X/i.test(ua)) return "macos";
    if (/Linux/i.test(ua)) return "linux";
    return null;
  }

  /* ---------- 渲染四张平台卡片 ---------- */
  function renderCards() {
    var wrap = $("#pcards");
    if (!wrap) return;

    var html = "";
    PLATFORMS.forEach(function (p) {
      var sub = p.secondary
        ? '<a class="pcard-sub" href="' + p.secondary.url + '" data-download="' + p.secondary.file + '">' + p.secondary.label + ' ↗</a>'
        : "";

      html +=
        '<article class="pcard" data-id="' + p.id + '">' +
          '<span class="spot"></span><span class="glare"></span>' +
          '<div class="pcard-inner">' +
            '<div class="pcard-head">' +
              '<span class="picon">' + ICONS[p.id] + "</span>" +
              '<span class="phead-right">' +
                '<span class="match">✓ 匹配你的设备</span>' +
                '<span class="badge">1.0.0</span>' +
              "</span>" +
            "</div>" +
            '<h3 class="pname">' + p.name + "</h3>" +
            '<p class="preq">' + p.req + "</p>" +
            '<div class="pmeta">' +
              '<span class="psize">' + p.size + "</span>" +
              '<span class="dot">·</span>' +
              '<span class="pdate">' + p.date + "</span>" +
              '<button class="psha" type="button" data-copy="' + p.sha + '" title="复制 SHA256 校验值">SHA256</button>' +
            "</div>" +
            '<a class="dl" href="' + p.url + '" data-download="' + p.file + '">' +
              '<span class="dl-ico">' + ICONS.download + "</span>" +
              '<span class="dl-txt">下载 ' + p.name + " 版</span>" +
              '<span class="dl-arrow">' + ICONS.arrow + "</span>" +
            "</a>" +
            sub +
          "</div>" +
        "</article>";
    });

    wrap.innerHTML = html;
  }

  /* ---------- 卡片 3D 倾斜 + 聚光（lerp 平滑） ---------- */
  function setupCardFx() {
    var cards = $all(".pcard");
    if (!cards.length || reduced.matches) return;

    cards.forEach(function (card) {
      var f = { rx: 0, ry: 0, lift: 0, tx: 0, ty: 0, tlift: 0 };
      card._fx = f;

      card.addEventListener("pointerenter", function () { f.tlift = 1; });
      card.addEventListener("pointermove", function (e) {
        if (e.pointerType !== "mouse") return;
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        f.ty = (px - 0.5) * 14;
        f.tx = -(py - 0.5) * 12;
        card.style.setProperty("--mx", (px * 100) + "%");
        card.style.setProperty("--my", (py * 100) + "%");
      });
      card.addEventListener("pointerleave", function () {
        f.tx = 0; f.ty = 0; f.tlift = 0;
      });
    });

    (function tick() {
      cards.forEach(function (card) {
        var f = card._fx;
        if (!f) return;
        f.rx += (f.tx - f.rx) * 0.13;
        f.ry += (f.ty - f.ry) * 0.13;
        f.lift += (f.tlift - f.lift) * 0.14;
        card.style.transform =
          "perspective(900px) rotateX(" + f.rx.toFixed(2) + "deg) rotateY(" + f.ry.toFixed(2) + "deg) translateY(-" + (f.lift * 5).toFixed(2) + "px)";
      });
      requestAnimationFrame(tick);
    })();
  }

  /* ---------- 磁吸按钮 ---------- */
  function setupMagnetic() {
    var els = $all("[data-magnetic]");
    if (!els.length || reduced.matches) return;
    els.forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        if (e.pointerType !== "mouse") return;
        var r = el.getBoundingClientRect();
        var x = (e.clientX - r.left - r.width / 2) * 0.22;
        var y = (e.clientY - r.top - r.height / 2) * 0.36;
        el.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
      });
      el.addEventListener("pointerleave", function () { el.style.transform = ""; });
    });
  }

  /* ---------- 手机 mockup 倾斜 ---------- */
  function setupDeviceTilt() {
    var dev = $("#device");
    if (!dev || reduced.matches) return;
    dev.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      var r = dev.getBoundingClientRect();
      var rx = -((e.clientY - r.top) / r.height - 0.5) * 12;
      var ry = ((e.clientX - r.left) / r.width - 0.5) * 14;
      dev.style.transform = "rotate(2deg) perspective(1000px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg)";
    });
    dev.addEventListener("pointerleave", function () { dev.style.transform = ""; });
  }

  /* ---------- 滚动显现 ---------- */
  function setupReveal() {
    var targets = $all(".pcard-inner, .section-head, .feature-grid");
    if (!targets.length) return;
    if (!("IntersectionObserver" in window) || reduced.matches) {
      targets.forEach(function (t) { t.classList.add("is-visible"); });
      return;
    }
    var stagger = 0;
    targets.forEach(function (t) {
      t.classList.add("reveal");
      if (t.classList.contains("pcard-inner")) t.style.transitionDelay = (stagger++ * 70) + "ms";
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
          setTimeout(function () { entry.target.style.transitionDelay = ""; }, 1000);
        }
      });
    }, { threshold: 0.15 });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* ---------- 系统匹配 ---------- */
  function applyOS() {
    var os = detectOS();
    if (!os) return;
    var p = findPlatform(os);
    var label = $("#hero-cta-label");
    var cta = $("#hero-cta");
    if (label && p) label.textContent = "下载 " + p.name + " 版 · v1.0.0";
    if (cta && p) {
      cta.href = p.url;
      cta.setAttribute("data-download", p.file);
    }
    var card = $('.pcard[data-id="' + os + '"]');
    if (card) card.classList.add("matched");
  }

  /* ---------- 跑马灯 ---------- */
  function fillMarquee() {
    var el = $("#marquee");
    if (!el) return;
    var items = ["本地优先", "免费使用", "无需注册", "覆盖安装即可", "数据留在本机", "全平台 1.0.0"];
    var one = items.map(function (t) {
      return "<span>" + t + '</span><span class="sep">·</span>';
    }).join("");
    el.innerHTML = one + one;
  }

  /* ---------- 事件委托：复制 / 下载提示 ---------- */
  function setupDelegation() {
    document.addEventListener("click", function (e) {
      var sha = e.target.closest(".psha");
      if (sha) {
        copyText(sha.getAttribute("data-copy"), function () {
          sha.classList.add("copied");
          var old = sha.textContent;
          sha.textContent = "已复制 ✓";
          toast("SHA256 校验值已复制");
          setTimeout(function () { sha.classList.remove("copied"); sha.textContent = old; }, 1800);
        });
        return;
      }
      var dl = e.target.closest("[data-download]");
      if (dl) toast("正在下载 " + dl.getAttribute("data-download"));
    });
  }

  /* ---------- 导航滚动阴影 ---------- */
  function setupNavScroll() {
    var nav = $("#nav");
    if (!nav) return;
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- 应用截图：居中单张自动切换 + 大图预览 ---------- */
  function setupShowcase() {
    var imgA = $("#stage-img-a");
    var imgB = $("#stage-img-b");
    var caption = $("#stage-caption");
    var dotsWrap = $("#stage-dots");
    var bar = $("#stage-bar-fill");
    var prevBtn = $("#stage-prev");
    var nextBtn = $("#stage-next");
    var phone = $("#stage-phone");
    if (!imgA || !imgB) return;

    var SLIDE_MS = 4200;
    var index = 0;
    var layerA = true;
    var timer = null;

    SCREENSHOTS.forEach(function (s) { var im = new Image(); im.src = s.src; });

    dotsWrap.innerHTML = SCREENSHOTS.map(function (_, i) {
      return '<button class="stage-dot" type="button" data-i="' + i + '" aria-label="第 ' + (i + 1) + ' 张"></button>';
    }).join("");

    function currentImg() { return layerA ? imgA : imgB; }
    function otherImg() { return layerA ? imgB : imgA; }

    function apply(i) {
      index = (i + SCREENSHOTS.length) % SCREENSHOTS.length;
      var s = SCREENSHOTS[index];
      var to = otherImg();
      to.src = s.src;
      to.alt = s.alt;
      currentImg().classList.remove("is-active");
      to.classList.add("is-active");
      layerA = !layerA;
      caption.textContent = s.caption;
      $all(".stage-dot", dotsWrap).forEach(function (d, di) {
        d.classList.toggle("active", di === index);
      });
    }

    function restartBar() {
      bar.style.transition = "none";
      bar.style.width = "0";
      void bar.offsetWidth;
      bar.style.transition = "width " + SLIDE_MS + "ms linear";
      bar.style.width = "100%";
    }

    function schedule() {
      clearTimeout(timer);
      timer = setTimeout(function () { apply(index + 1); restartBar(); schedule(); }, SLIDE_MS);
    }

    function pause() {
      clearTimeout(timer);
      var w = bar.offsetWidth / bar.parentElement.offsetWidth * 100;
      bar.style.transition = "none";
      bar.style.width = w + "%";
    }

    prevBtn.addEventListener("click", function () { apply(index - 1); restartBar(); schedule(); });
    nextBtn.addEventListener("click", function () { apply(index + 1); restartBar(); schedule(); });
    dotsWrap.addEventListener("click", function (e) {
      var d = e.target.closest(".stage-dot");
      if (d) { apply(parseInt(d.getAttribute("data-i"), 10)); restartBar(); schedule(); }
    });

    var stageEl = $(".stage");
    if (stageEl && !reduced.matches) {
      stageEl.addEventListener("mouseenter", pause);
      stageEl.addEventListener("mouseleave", function () { restartBar(); schedule(); });
    }

    /* 大图预览 */
    var dialog = document.createElement("dialog");
    dialog.className = "lightbox";
    dialog.setAttribute("aria-label", "应用界面预览");
    var close = document.createElement("button");
    close.className = "lb-close"; close.type = "button"; close.textContent = "×";
    close.setAttribute("aria-label", "关闭预览");
    var dimg = document.createElement("img");
    var dcap = document.createElement("p"); dcap.className = "lb-caption";
    var nav = document.createElement("div"); nav.className = "lb-nav";
    var dprev = document.createElement("button"); dprev.type = "button"; dprev.textContent = "← 上一张";
    var dnext = document.createElement("button"); dnext.type = "button"; dnext.textContent = "下一张 →";
    nav.append(dprev, dnext);
    dialog.append(close, dimg, dcap, nav);
    document.body.appendChild(dialog);

    var lbi = 0;
    function openLightbox(i) {
      lbi = (i + SCREENSHOTS.length) % SCREENSHOTS.length;
      var s = SCREENSHOTS[lbi];
      dimg.src = s.src;
      dimg.alt = s.alt;
      dcap.textContent = s.caption + " · " + (lbi + 1) + " / " + SCREENSHOTS.length;
      dialog.showModal();
      document.body.classList.add("preview-open");
    }
    phone.addEventListener("click", function () { openLightbox(index); });
    dprev.addEventListener("click", function () { openLightbox(lbi - 1); });
    dnext.addEventListener("click", function () { openLightbox(lbi + 1); });
    close.addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener("close", function () { document.body.classList.remove("preview-open"); });
    dialog.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { e.preventDefault(); openLightbox(lbi - 1); }
      if (e.key === "ArrowRight") { e.preventDefault(); openLightbox(lbi + 1); }
    });

    $all(".stage-dot", dotsWrap).forEach(function (d, di) {
      d.classList.toggle("active", di === 0);
    });

    if (!reduced.matches) { restartBar(); schedule(); }
  }

  function init() {
    renderCards();
    fillMarquee();
    setupCardFx();
    setupMagnetic();
    setupDeviceTilt();
    setupReveal();
    setupShowcase();
    applyOS();
    setupDelegation();
    setupNavScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
