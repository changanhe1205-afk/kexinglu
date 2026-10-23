(function () {
  var header = document.querySelector('.site-header');
  var onScroll = function () {
    if (!header) return;
    header.classList.toggle('is-scrolled', window.scrollY > 8);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = btn.getAttribute('data-copy') || '';
      var done = function () {
        var old = btn.textContent;
        btn.textContent = '已复制 ✓';
        setTimeout(function () { btn.textContent = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
      } else {
        fallback(text, done);
      }
    });
  });

  function fallback(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
    done();
  }

  if ('IntersectionObserver' in window &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var items = document.querySelectorAll('.section-head, .feature, .download-card, .privacy-grid article, .shot');
    items.forEach(function (el) { el.classList.add('reveal'); });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    items.forEach(function (el) { io.observe(el); });
  }
})();

// Native preview: no external runtime or image requests.
(function(){
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const dialog=document.createElement('dialog');dialog.className='image-preview';
 const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label','关闭预览 / Close preview');
 const img=document.createElement('img');dialog.append(close,img);document.body.append(dialog);
 close.onclick=()=>dialog.close();dialog.onclick=e=>{if(e.target===dialog)dialog.close();};
 document.querySelectorAll('.shot img').forEach(source=>{
  const button=document.createElement('button');button.className='preview-trigger';button.type='button';button.setAttribute('aria-label','查看大图 / Preview: '+source.alt);
  source.replaceWith(button);button.append(source);
  button.onclick=()=>{img.src=source.currentSrc||source.src;img.alt=source.alt;dialog.showModal();};
 });
 document.querySelectorAll('.hero-phone').forEach(el=>{
  el.addEventListener('pointermove',e=>{if(reduced.matches||e.pointerType!=='mouse')return;const box=el.getBoundingClientRect();el.style.transform='perspective(1000px) rotateY('+((e.clientX-box.left)/box.width-.5)*8+'deg) rotateX('+(-((e.clientY-box.top)/box.height-.5)*6)+'deg)';});
  el.addEventListener('pointerleave',()=>el.style.transform='');
 });
 const links=[...document.querySelectorAll('.site-nav a[href^="#"]')];
 if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)links.forEach(a=>{const active=a.hash==='#'+e.target.id;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}),{rootMargin:'-15% 0px -60% 0px'});links.forEach(a=>{const section=document.querySelector(a.hash);if(section)observer.observe(section);});}
})();
