(function () {
  'use strict';
  var art = document.getElementById('text');
  var slug = art ? art.getAttribute('data-slug') : null;
  var sent = {};
  window.__goals = [];

  // Цель Метрики: один раз за просмотр страницы, с названием новеллы в параметрах
  function goal(name) {
    if (sent[name]) return;
    sent[name] = 1;
    window.__goals.push(name);
    var params = slug ? { novella: slug } : undefined;
    try { if (window.YM_ID && window.ym) window.ym(window.YM_ID, 'reachGoal', name, params); } catch (e) {}
    if (window.console) console.log('[goal]', name, slug || '');
  }
  window.siteGoal = goal;

  // Клики: Telegram, следующая новелла
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('[data-goal]') : null;
    if (a) { sent[a.getAttribute('data-goal')] = 0; goal(a.getAttribute('data-goal')); }
  });

  // Прокрутка текста и дочитывание
  if (art) {
    var bar = document.getElementById('bar');
    var paras = art.querySelectorAll('p');
    var last = paras[paras.length - 1];
    var minutes = +art.getAttribute('data-min') || 1;
    // Дочитал = последний абзац показался на экране и на странице провели
    // не меньше трети расчётного времени чтения (считается, только пока вкладка открыта)
    var needMs = Math.max(45, minutes * 60 * 0.33) * 1000;
    var activeMs = 0, since = document.hidden ? 0 : Date.now();
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { if (since) activeMs += Date.now() - since; since = 0; }
      else since = Date.now();
    });
    function spent() { return activeMs + (since ? Date.now() - since : 0); }

    var endSeen = false, ticking = false;
    function check() {
      ticking = false;
      var r = art.getBoundingClientRect();
      var vh = window.innerHeight || document.documentElement.clientHeight;
      // доля текста, которая уже показалась на экране
      var seen = Math.min(1, Math.max(0, (vh - r.top) / r.height));
      if (bar) bar.style.transform = 'scaleX(' + seen.toFixed(4) + ')';
      if (seen >= 0.25) goal('read_25');
      if (seen >= 0.5) goal('read_50');
      if (seen >= 0.75) goal('read_75');
      if (last) {
        var lr = last.getBoundingClientRect();
        if (lr.top < vh && lr.bottom > 0 && !endSeen) {
          endSeen = true;
          if (spent() >= needMs) goal('read_end'); else { goal('read_end_fast'); waitEnd(); }
        }
      }
    }
    // Долистал быстро, но остался на странице дольше порога: тоже засчитываем дочитывание
    function waitEnd() {
      var iv = setInterval(function () {
        if (spent() >= needMs) { clearInterval(iv); var lr = last.getBoundingClientRect();
          if (lr.top < (window.innerHeight || 0) * 1.5) goal('read_end'); }
      }, 5000);
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(check); } }, { passive: true });
    window.addEventListener('resize', check);
    check();
  }

  // Форма отзыва
  var fb = document.getElementById('fb');
  if (fb) {
    var shown = Date.now();
    fb.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = fb.querySelector('.btn'), ok = fb.querySelector('.fb-ok'), er = fb.querySelector('.fb-err');
      var data = new FormData(fb);
      if (!data.get('mood') && !String(data.get('text') || '').trim()) { fb.querySelector('textarea').focus(); return; }
      data.set('t', String(Date.now() - shown));
      btn.disabled = true; er.hidden = true;
      fetch(fb.action, { method: 'POST', body: data, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) throw new Error(j.error || 'err');
          goal('feedback_sent');
          ok.hidden = false; btn.hidden = true;
          fb.querySelectorAll('input,textarea').forEach(function (el) { el.disabled = true; });
        })
        .catch(function () { er.hidden = false; btn.disabled = false; });
    });
  }

  // Плашка о cookie: тонкая полоса внизу, не закрывает текст и не мешает читать
  var ck = document.getElementById('cookie');
  var seenCk = false;
  try { seenCk = localStorage.getItem('cookie_ok') === '1'; } catch (e) {}
  if (ck && !seenCk) {
    ck.hidden = false;
    document.body.classList.add('has-ck');
    document.getElementById('cookie-ok').addEventListener('click', function () {
      ck.hidden = true;
      document.body.classList.remove('has-ck');
      try { localStorage.setItem('cookie_ok', '1'); } catch (e) {}
    });
  }
})();
