(function () {
  'use strict';

  /* ---------- theme ---------- */
  var root = document.documentElement;
  var THEME_KEY = 'rukazax-theme';
  var params = new URLSearchParams(location.search);

  function initialTheme() {
    var fromQuery = params.get('theme');
    if (fromQuery === 'light' || fromQuery === 'dark') return fromQuery;
    var saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    document.querySelectorAll('[data-theme-label]').forEach(function (el) {
      el.textContent = theme === 'dark' ? '\u2600' : '\u263E';
    });
    document.querySelectorAll('[data-theme-title]').forEach(function (el) {
      el.title = theme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
    });
  }

  applyTheme(initialTheme());
  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  });

  /* ---------- burger on scroll ---------- */

  var burger = document.getElementById('burgerBtn');
  if (burger) {
    burger.addEventListener('click', function () {
      var open = document.body.classList.toggle('menu-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.querySelectorAll('#mobileMenu a').forEach(function (link) {
      link.addEventListener('click', function () {
        document.body.classList.remove('menu-open');
        burger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- contact form ---------- */
  var ENDPOINT = 'https://formsubmit.co/ajax/rukazax@gmail.com';
  var modal = document.getElementById('formModal');
  var form = document.getElementById('contactForm');
  var status = document.getElementById('formStatus');
  var submitBtn = document.getElementById('formSubmit');
  var lastFocus = null;

  function openModal() {
    if (!modal) return;
    lastFocus = document.activeElement;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    var first = form && form.querySelector('input');
    if (first) setTimeout(function () { first.focus(); }, 60);
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.querySelectorAll('[data-open-form]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      openModal();
    });
  });
  document.querySelectorAll('[data-close]').forEach(function (el) {
    el.addEventListener('click', closeModal);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = new FormData(form);
      var name = String(data.get('name') || '').trim();
      var phone = String(data.get('phone') || '').trim();
      var email = String(data.get('email') || '').trim();
      var message = String(data.get('message') || '').trim();

      if (name.length < 2) return fail('Укажите имя');
      if (phone.replace(/\D/g, '').length < 10) return fail('Укажите телефон');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail('Укажите корректный e-mail');
      if (message.length < 5) return fail('Опишите задачу хотя бы в двух словах');

      function fail(text) {
        status.className = 'form-status err';
        status.textContent = text;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Отправляем…';
      status.className = 'form-status';
      status.textContent = '';

      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          _subject: 'Заявка с сайта rukazax.github.io',
          _template: 'table',
          _captcha: 'false',
          name: name,
          phone: phone,
          email: email,
          message: message
        })
      })
        .then(function (res) { return res.json().catch(function () { return {}; }); })
        .then(function (body) {
          if (body && (body.success === 'true' || body.success === true)) {
            form.reset();
            status.className = 'form-status ok';
            status.textContent = 'Спасибо! Заявка отправлена — отвечу в рабочее время.';
          } else {
            throw new Error((body && body.message) || 'send failed');
          }
        })
        .catch(function () {
          status.className = 'form-status err';
          status.innerHTML = 'Не удалось отправить. Напишите напрямую: ' +
            '<a href="mailto:rukazax@gmail.com">rukazax@gmail.com</a> или ' +
            '<a href="tel:+79998024040">+7 (999) 802-40-40</a>.';
        })
        .then(function () {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Отправить';
        });
    });
  }
})();
