/* PaperMind — hesab, plan və ödəniş interfeysi.
 *
 * app.js-dən AYRI saxlanılır: o, onsuz da 1400 sətirdir və bu modulun onunla
 * yeganə əlaqəsi iki hadisədir (`pm:auth-required`, `pm:upgrade-required`),
 * onları da `api()` tək yerdən göndərir.
 *
 * Öz i18n cədvəli var. Təkrar görünə bilər, amma modulu müstəqil saxlayır —
 * app.js-dəki I18N ixrac olunmur və onu ixrac etmək üçün bütün faylı
 * dəyişmək lazım gələrdi.
 */
(function () {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const LANG = () => localStorage.getItem('pm_lang') || 'az';

  const S = {
    az: {
      sign_in: 'Daxil ol', sign_up: 'Hesab yarat', sign_out: 'Çıxış',
      del_acct: 'Hesabı sil',
      del_title: 'Hesabı silmək',
      del_warn: 'Kitabxanan, yüklədiyin sənədlər və bütün tarixçən silinəcək. Bu, geri qaytarıla bilməz.',
      del_grace: 'Hesab {d} tarixində silinəcək. O vaxta qədər fikrini dəyişə bilərsən.',
      del_pw: 'Təsdiq üçün parolunu yaz',
      del_go: 'Silinməni başlat',
      del_undo: 'Silinməni ləğv et',
      del_sub: 'Əvvəlcə abunəliyi ləğv et — əks halda hesab silinər, ödəniş davam edər.',
      del_manage: 'Abunəliyi idarə et',
      email: 'E-poçt', password: 'Parol', name: 'Ad (istəyə görə)',
      login_title: 'Hesabına daxil ol', register_title: 'Yeni hesab',
      no_account: 'Hesabın yoxdur?', have_account: 'Artıq hesabın var?',
      account: 'Hesab', plan: 'Plan', credits: 'Kredit', library: 'Kitabxana',
      upgrade: 'Pro-ya keç', manage: 'Abunəni idarə et',
      pricing_title: 'Planlar', current: 'Cari plan',
      upgrade_needed: 'Bu imkan Pro planındadır.',
      out_of_credits: 'Bu ayın kreditləri bitdi.',
      library_full: 'Kitabxana doldu.',
      login_required: 'Bunun üçün hesab lazımdır — bir dəqiqəlik işdir.',
      working: 'Gözlə…', close: 'Bağla',
      pw_hint: 'Ən azı 10 simvol.',
      welcome: 'Xoş gəldin',
      pay_unavailable: 'Ödəniş hazırda aktiv deyil.',
      credits_left: '{n} kredit qalıb',
      free_forever: 'Həmişə pulsuz',
      why_account: 'Axtarış hesabsız işləyir. Hesab yalnız sual vermək, məqalə saxlamaq və PDF üçün lazımdır.',
    },
    en: {
      sign_in: 'Sign in', sign_up: 'Create account', sign_out: 'Sign out',
      del_acct: 'Delete account',
      del_title: 'Delete your account',
      del_warn: 'Your library, uploaded documents and all history will be removed. This cannot be undone.',
      del_grace: 'Your account will be deleted on {d}. You can change your mind until then.',
      del_pw: 'Enter your password to confirm',
      del_go: 'Start deletion',
      del_undo: 'Cancel deletion',
      del_sub: 'Cancel your subscription first — otherwise the account goes but billing continues.',
      del_manage: 'Manage subscription',
      email: 'Email', password: 'Password', name: 'Name (optional)',
      login_title: 'Sign in', register_title: 'Create your account',
      no_account: 'No account yet?', have_account: 'Already have an account?',
      account: 'Account', plan: 'Plan', credits: 'Credits', library: 'Library',
      upgrade: 'Upgrade to Pro', manage: 'Manage subscription',
      pricing_title: 'Plans', current: 'Current plan',
      upgrade_needed: 'This is a Pro feature.',
      out_of_credits: "You've used this month's credits.",
      library_full: 'Your library is full.',
      login_required: 'This needs an account — takes a minute.',
      working: 'Working…', close: 'Close',
      pw_hint: 'At least 10 characters.',
      welcome: 'Welcome',
      pay_unavailable: 'Payments are not enabled yet.',
      credits_left: '{n} credits left',
      free_forever: 'Free forever',
      why_account: 'Search works without an account. You only need one to ask questions, save papers and upload PDFs.',
    },
    ru: {
      sign_in: 'Войти', sign_up: 'Создать аккаунт', sign_out: 'Выйти',
      del_acct: 'Удалить аккаунт',
      del_title: 'Удаление аккаунта',
      del_warn: 'Библиотека, загруженные документы и вся история будут удалены. Отменить нельзя.',
      del_grace: 'Аккаунт будет удалён {d}. До этого можно передумать.',
      del_pw: 'Введите пароль для подтверждения',
      del_go: 'Начать удаление',
      del_undo: 'Отменить удаление',
      del_sub: 'Сначала отмените подписку — иначе аккаунт исчезнет, а списания продолжатся.',
      del_manage: 'Управление подпиской',
      email: 'Эл. почта', password: 'Пароль', name: 'Имя (необязательно)',
      login_title: 'Вход', register_title: 'Новый аккаунт',
      no_account: 'Нет аккаунта?', have_account: 'Уже есть аккаунт?',
      account: 'Аккаунт', plan: 'План', credits: 'Кредиты', library: 'Библиотека',
      upgrade: 'Перейти на Pro', manage: 'Управление подпиской',
      pricing_title: 'Планы', current: 'Текущий план',
      upgrade_needed: 'Это возможность плана Pro.',
      out_of_credits: 'Кредиты за этот месяц закончились.',
      library_full: 'Библиотека заполнена.',
      login_required: 'Для этого нужен аккаунт — это займёт минуту.',
      working: 'Подождите…', close: 'Закрыть',
      pw_hint: 'Минимум 10 символов.',
      welcome: 'Добро пожаловать',
      pay_unavailable: 'Оплата пока не подключена.',
      credits_left: 'Осталось кредитов: {n}',
      free_forever: 'Всегда бесплатно',
      why_account: 'Поиск работает без аккаунта. Он нужен только для вопросов, сохранения статей и PDF.',
    },
  };
  const t = (k) => (S[LANG()] || S.az)[k] ?? S.en[k] ?? k;

  let USER = null;
  let PLANS = [];

  /* --------------------------------------------------------------- şəbəkə */

  async function call(path, opts = {}) {
    const resp = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (resp.status === 204) return null;
    let body = null;
    try { body = await resp.json(); } catch { /* gövdəsiz cavab */ }
    if (!resp.ok) {
      const d = body && body.detail;
      const err = new Error(typeof d === 'string' ? d : (d && d.message) || resp.statusText);
      err.status = resp.status;
      err.detail = d;
      throw err;
    }
    return body;
  }

  async function refresh() {
    try {
      USER = await call('/api/auth/me');
    } catch {
      USER = null;          // 401 = girişsiz; bu, xəta deyil
    }
    renderHeader();
    /* Hadisə BURADA da atılır, təkcə giriş formasında yox.
       Səhifə yeniləndikdə sessiya mövcud olsa belə `pm:signed-in` heç
       düşməsəydi, ondan asılı olan hər şey (kitabxana vəziyyəti) yalnız
       yenidən giriş edəndən sonra işləyərdi. İndi hadisə «kimliyi ARTIQ
       bilirik» mənasını verir və hər iki yol üçün eynidir. */
    document.dispatchEvent(new CustomEvent(
      USER ? 'pm:signed-in' : 'pm:signed-out', { detail: USER }
    ));
    return USER;
  }

  /* ---------------------------------------------------------------- başlıq */

  function renderHeader() {
    const slot = $('#account-slot');
    if (!slot) return;

    if (!USER) {
      slot.innerHTML = `<button type="button" class="acct-btn" id="acct-signin">${esc(t('sign_in'))}</button>`;
      $('#acct-signin').addEventListener('click', () => openAuth('login'));
      return;
    }

    const pro = USER.plan === 'pro';
    slot.innerHTML = `
      <button type="button" class="acct-btn acct-user" id="acct-open" aria-haspopup="dialog">
        <span class="acct-chip ${pro ? 'pro' : ''}">${esc(USER.plan_label)}</span>
        <span class="acct-credits">${esc(String(USER.credits_left))}</span>
      </button>`;
    $('#acct-open').addEventListener('click', openAccount);
  }

  /* ----------------------------------------------------------------- modal */

  function modal(inner, { onClose } = {}) {
    closeModal();
    const wrap = document.createElement('div');
    wrap.className = 'pm-modal';
    wrap.id = 'pm-modal';
    wrap.innerHTML = `
      <div class="pm-modal-scrim" data-close="1"></div>
      <div class="pm-modal-box" role="dialog" aria-modal="true">
        <button type="button" class="pm-modal-x" data-close="1" aria-label="${esc(t('close'))}">&times;</button>
        ${inner}
      </div>`;
    document.body.appendChild(wrap);
    wrap.addEventListener('click', (e) => {
      if (e.target.dataset.close) { closeModal(); onClose && onClose(); }
    });
    document.addEventListener('keydown', escClose);
    const first = wrap.querySelector('input, button:not([data-close])');
    if (first) first.focus();
    return wrap;
  }

  function escClose(e) { if (e.key === 'Escape') closeModal(); }

  function closeModal() {
    const m = $('#pm-modal');
    if (m) m.remove();
    document.removeEventListener('keydown', escClose);
  }

  /* ------------------------------------------------------- giriş/qeydiyyat */

  function openAuth(mode = 'login', note = '') {
    const isLogin = mode === 'login';
    modal(`
      <h2 class="pm-modal-title">${esc(isLogin ? t('login_title') : t('register_title'))}</h2>
      ${note ? `<p class="pm-note">${esc(note)}</p>` : ''}
      <form id="auth-form" class="pm-form" novalidate>
        ${isLogin ? '' : `
          <label>${esc(t('name'))}
            <input name="display_name" type="text" maxlength="100" autocomplete="name">
          </label>`}
        <label>${esc(t('email'))}
          <input name="email" type="email" required maxlength="254" autocomplete="email">
        </label>
        <label>${esc(t('password'))}
          <input name="password" type="password" required minlength="10" maxlength="200"
                 autocomplete="${isLogin ? 'current-password' : 'new-password'}">
          ${isLogin ? '' : `<small>${esc(t('pw_hint'))}</small>`}
        </label>
        <p class="pm-err" id="auth-err" hidden></p>
        <button type="submit" class="pm-primary" id="auth-submit">
          ${esc(isLogin ? t('sign_in') : t('sign_up'))}
        </button>
      </form>
      <p class="pm-alt">
        ${esc(isLogin ? t('no_account') : t('have_account'))}
        <button type="button" class="pm-link" id="auth-switch">
          ${esc(isLogin ? t('sign_up') : t('sign_in'))}
        </button>
      </p>
      ${isLogin ? '' : `<p class="pm-why">${esc(t('why_account'))}</p>`}
    `);

    $('#auth-switch').addEventListener('click', () => openAuth(isLogin ? 'register' : 'login', note));

    $('#auth-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = $('#auth-submit');
      const err = $('#auth-err');
      const fd = new FormData(e.target);
      const payload = {
        email: (fd.get('email') || '').trim(),
        password: fd.get('password') || '',
      };
      if (!isLogin) payload.display_name = (fd.get('display_name') || '').trim() || null;

      btn.disabled = true;
      btn.textContent = t('working');
      err.hidden = true;
      try {
        USER = await call(isLogin ? '/api/auth/login' : '/api/auth/register', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        closeModal();
        renderHeader();
        document.dispatchEvent(new CustomEvent('pm:signed-in', { detail: USER }));
      } catch (ex) {
        err.textContent = ex.message;
        err.hidden = false;
        btn.disabled = false;
        btn.textContent = isLogin ? t('sign_in') : t('sign_up');
      }
    });
  }

  /* ------------------------------------------------------------ hesab paneli */

  /* Tarixi oxunaqlı formata salır. Server ISO qaytarır; günü frontend-də
     HESABLAMIRIQ — yalnız formatlayırıq, yoxsa möhlət dəyişəndə interfeys
     səssizcə yalan danışardı. */
  function fmtDate(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(
        LANG === 'en' ? 'en-GB' : LANG === 'ru' ? 'ru-RU' : 'az-AZ',
        { day: 'numeric', month: 'long', year: 'numeric' });
    } catch { return String(iso).slice(0, 10); }
  }

  async function openDeleteAccount() {
    modal(`
      <h2 class="pm-modal-title">${esc(t('del_title'))}</h2>
      <p class="pm-danger-text">${esc(t('del_warn'))}</p>
      <form id="del-form">
        <label class="pm-label">${esc(t('del_pw'))}
          <input type="password" id="del-pw" autocomplete="current-password" required>
        </label>
        <p class="pm-err" id="del-err" hidden></p>
        <div class="pm-actions">
          <button type="submit" class="pm-danger-btn">${esc(t('del_go'))}</button>
        </div>
      </form>
    `);

    $('#del-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = $('#del-err');
      err.hidden = true;
      try {
        USER = await call('/api/auth/account/delete', {
          method: 'POST',
          body: JSON.stringify({ password: $('#del-pw').value }),
        });
        renderHeader();
        openAccount();                       // möhlət zolağı ilə geri qayıdır
      } catch (ex) {
        // Aktiv abunəlik xüsusi haldır: sadəcə «alınmadı» demək faydasızdır,
        // istifadəçiyə NƏ etməli olduğunu və hara getməli olduğunu deyirik.
        const d = ex && ex.detail;
        if (d && d.error === 'subscription_active') {
          err.innerHTML = esc(t('del_sub')) +
            (d.manage_url ? ` <a href="${esc(d.manage_url)}" target="_blank" rel="noopener">${esc(t('del_manage'))}</a>` : '');
        } else {
          err.textContent = (d && d.message) || (typeof d === 'string' ? d : t('del_warn'));
        }
        err.hidden = false;
      }
    });
  }

  async function openAccount() {
    if (!USER) return openAuth('login');
    const pro = USER.plan === 'pro';
    const pct = USER.credits_total
      ? Math.round(((USER.credits_total - USER.credits_left) / USER.credits_total) * 100)
      : 0;

    modal(`
      <h2 class="pm-modal-title">${esc(t('account'))}</h2>
      <p class="pm-email">${esc(USER.email)}</p>
      <dl class="pm-stats">
        <div><dt>${esc(t('plan'))}</dt><dd><span class="acct-chip ${pro ? 'pro' : ''}">${esc(USER.plan_label)}</span></dd></div>
        <div><dt>${esc(t('credits'))}</dt><dd>${esc(String(USER.credits_left))} / ${esc(String(USER.credits_total))}</dd></div>
        <div><dt>${esc(t('library'))}</dt><dd>${esc(String(USER.library_used))} / ${esc(String(USER.library_limit))}</dd></div>
      </dl>
      <div class="pm-meter"><span style="width:${pct}%"></span></div>
      <div class="pm-actions">
        ${pro ? '' : `<button type="button" class="pm-primary" id="acct-upgrade">${esc(t('upgrade'))}</button>`}
        <button type="button" class="pm-ghost" id="acct-signout">${esc(t('sign_out'))}</button>
      </div>
      ${USER.deletion_requested_at ? `
        <div class="pm-danger-note">
          <p>${esc(t('del_grace').replace('{d}', fmtDate(USER.deletion_effective_at)))}</p>
          <button type="button" class="pm-ghost" id="acct-undel">${esc(t('del_undo'))}</button>
        </div>` : `
        <button type="button" class="pm-danger-link" id="acct-del">${esc(t('del_acct'))}</button>`}
    `);

    const up = $('#acct-upgrade');
    // Ox funksiyası VACİBDİR: `openPricing`-i birbaşa bağlasaq, o, ilk arqument
    // kimi hadisə obyektini alır və pəncərədə «[object PointerEvent]» görünür.
    if (up) up.addEventListener('click', () => openPricing());
    const del = $('#acct-del');
    if (del) del.addEventListener('click', openDeleteAccount);
    const undel = $('#acct-undel');
    if (undel) undel.addEventListener('click', async () => {
      USER = await call('/api/auth/account/delete/cancel', { method: 'POST' });
      renderHeader();
      openAccount();
    });
    $('#acct-signout').addEventListener('click', async () => {
      await call('/api/auth/logout', { method: 'POST' }).catch(() => {});
      USER = null;
      closeModal();
      renderHeader();
      document.dispatchEvent(new CustomEvent('pm:signed-out'));
    });
  }

  /* ----------------------------------------------------------- qiymət/upgrade */

  async function openPricing(reason = '') {
    if (!PLANS.length) {
      try { PLANS = await call(`/api/auth/plans?lang=${encodeURIComponent(LANG())}`); }
      catch { PLANS = []; }
    }
    const cards = PLANS.map((p) => {
      const isCurrent = USER && USER.plan === p.key;
      const isPro = p.key === 'pro';
      return `
        <div class="pm-plan ${isPro ? 'pro' : ''}">
          <h3>${esc(p.label)}</h3>
          ${isPro ? '' : `<p class="pm-plan-price">${esc(t('free_forever'))}</p>`}
          <ul>${p.features.map((f) => `<li>${esc(f)}</li>`).join('')}</ul>
          ${isCurrent
            ? `<span class="pm-current">${esc(t('current'))}</span>`
            : (isPro ? `<button type="button" class="pm-primary" id="do-upgrade">${esc(t('upgrade'))}</button>` : '')}
        </div>`;
    }).join('');

    modal(`
      <h2 class="pm-modal-title">${esc(t('pricing_title'))}</h2>
      ${reason ? `<p class="pm-note">${esc(reason)}</p>` : ''}
      <div class="pm-plans">${cards}</div>
      <p class="pm-err" id="pay-err" hidden></p>
    `);

    const btn = $('#do-upgrade');
    if (btn) btn.addEventListener('click', () => startCheckout(btn));
  }

  /* Paddle.js yalnız LAZIM OLANDA yüklənir — hər səhifə açılışında kənar
     skript çəkmək ilk yüklənməni yavaşladır və ödəniş etməyən istifadəçiyə
     heç bir fayda vermir. */
  function loadPaddle() {
    if (window.Paddle) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.paddle.com/paddle/v2/paddle.js';
      s.onload = resolve;
      s.onerror = () => reject(new Error('Paddle yüklənmədi'));
      document.head.appendChild(s);
    });
  }

  async function startCheckout(btn) {
    const err = $('#pay-err');
    btn.disabled = true;
    btn.textContent = t('working');
    try {
      const cfg = await call('/api/billing/checkout');
      await loadPaddle();
      if (cfg.environment === 'sandbox') window.Paddle.Environment.set('sandbox');
      window.Paddle.Initialize({ token: cfg.client_token });
      window.Paddle.Checkout.open({
        items: [{ priceId: cfg.price_id, quantity: 1 }],
        customer: { email: cfg.customer_email },
        customData: cfg.custom_data,
        settings: { successUrl: cfg.return_url },
      });
      closeModal();
    } catch (ex) {
      // Serverin öz mesajı DAHA DƏQİQdir — hansı konfiqurasiyanın çatmadığını
      // adı ilə deyir. Hamısını «ödəniş aktiv deyil»ə çevirmək səbəbi gizlədir
      // və nasazlığı tapmağı çətinləşdirir.
      err.textContent = ex.message || t('pay_unavailable');
      err.hidden = false;
      btn.disabled = false;
      btn.textContent = t('upgrade');
    }
  }

  /* ------------------------------------------------------------- hadisələr */

  document.addEventListener('pm:auth-required', () => {
    if (!$('#pm-modal')) openAuth('login', t('login_required'));
  });

  document.addEventListener('pm:upgrade-required', (e) => {
    const d = e.detail || {};
    // §20: səbəbə uyğun mesaj. «Upgrade to Pro» tək başına kontekstsizdir —
    // istifadəçi məhz nəyə görə dayandığını görməlidir.
    const reason =
      d.error === 'out_of_credits' ? t('out_of_credits')
      : d.error === 'library_full' ? t('library_full')
      : t('upgrade_needed');
    if (!$('#pm-modal')) openPricing(reason);
  });

  /* Sual cavabı kreditləri dəyişdirir — başlıqdakı rəqəm köhnə qalmasın. */
  document.addEventListener('pm:credits-changed', (e) => {
    if (USER && e.detail && typeof e.detail.left === 'number') {
      USER.credits_left = e.detail.left;
      renderHeader();
    }
  });

  window.PM_AUTH = {
    user: () => USER,
    refresh,
    openAuth,
    openAccount,
    openPricing,
  };

  document.addEventListener('DOMContentLoaded', () => {
    renderHeader();
    refresh();
    // Checkout-dan qayıdış: plan webhook ilə dəyişir, ona görə bir az gecikmə
    // ilə yenilənir — dərhal oxusaq hələ köhnə planı görə bilərik.
    if (new URLSearchParams(location.search).get('upgraded') === '1') {
      setTimeout(refresh, 2500);
      history.replaceState({}, '', location.pathname);
    }
  });
})();
