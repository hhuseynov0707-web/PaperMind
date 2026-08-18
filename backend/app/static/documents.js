/* PaperMind — şəxsi PDF sənədləri.
 *
 * Ayrıca modul: app.js axtarış və korpus üçündür, bu isə istifadəçinin öz
 * sənədləri. Aralarında ortaq vəziyyət yoxdur.
 *
 * Gating BURADA təkrarlanmır. Yükləmə Pro tələb edir, amma bunu server deyir
 * (402) və `api()` hadisəni göndərir, auth.js isə yüksəltmə pəncərəsini açır.
 * Frontend-də «istifadəçi Pro-dursa düyməni göstər» yazmaq iki mənbə yaradır
 * və biri yanılır.
 */
(function () {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const LANG = () => localStorage.getItem('pm_lang') || 'az';

  /* Serverdəki limitlə eyni olmalıdır (app/pdf.py MAX_BYTES).
     Burada yoxlamaq sırf nəzakətdir: 20 MB-lıq faylı yükləyib sonra rədd
     cavabı almaq istifadəçinin vaxtını və trafikini yandırır. */
  const MAX_BYTES = 20 * 1024 * 1024;
  const POLL_MS = 3000;
  const POLL_LIMIT = 60;          // ~3 dəqiqə

  const S = {
    az: {
      title: 'Sənədlərim', sub: 'Öz PDF məqalələrini yüklə və onlar haqqında sual ver',
      drop: 'PDF faylını bura sürüklə və ya seç', choose: 'Fayl seç',
      processing: 'hazırlanır', ready: 'hazır', failed: 'alınmadı',
      pages: 'səhifə', ask: 'Sual ver', del: 'Sil',
      empty: 'Hələ sənəd yoxdur.',
      too_big: 'Fayl çox böyükdür (limit 20 MB).',
      not_pdf: 'Yalnız PDF faylı yükləmək olar.',
      uploading: 'Yüklənir…', asking: 'Oxuyur…',
      q_ph: 'Bu sənəd haqqında nə soruşmaq istəyirsən?',
      page: 'səh.', del_confirm: 'Bu sənəd silinsin?',
      still: 'Sənəd hələ hazırlanır — bir az gözlə.',
      login_hint: 'Sənəd yükləmək üçün hesab lazımdır.',
    },
    en: {
      title: 'My documents', sub: 'Upload your own PDFs and ask questions about them',
      drop: 'Drag a PDF here, or choose a file', choose: 'Choose file',
      processing: 'processing', ready: 'ready', failed: 'failed',
      pages: 'pages', ask: 'Ask', del: 'Delete',
      empty: 'No documents yet.',
      too_big: 'File is too large (20 MB limit).',
      not_pdf: 'Only PDF files can be uploaded.',
      uploading: 'Uploading…', asking: 'Reading…',
      q_ph: 'What do you want to know about this document?',
      page: 'p.', del_confirm: 'Delete this document?',
      still: 'Still processing — give it a moment.',
      login_hint: 'You need an account to upload documents.',
    },
    ru: {
      title: 'Мои документы', sub: 'Загрузите свои PDF и задавайте по ним вопросы',
      drop: 'Перетащите PDF сюда или выберите файл', choose: 'Выбрать файл',
      processing: 'обрабатывается', ready: 'готов', failed: 'не удалось',
      pages: 'стр.', ask: 'Спросить', del: 'Удалить',
      empty: 'Документов пока нет.',
      too_big: 'Файл слишком большой (лимит 20 МБ).',
      not_pdf: 'Можно загружать только PDF.',
      uploading: 'Загрузка…', asking: 'Читает…',
      q_ph: 'Что вы хотите узнать об этом документе?',
      page: 'стр.', del_confirm: 'Удалить документ?',
      still: 'Документ ещё обрабатывается — подождите.',
      login_hint: 'Для загрузки нужен аккаунт.',
    },
  };
  const t = (k) => (S[LANG()] || S.az)[k] ?? S.en[k] ?? k;

  let DOCS = [];
  let polling = null;

  /* ------------------------------------------------------------- şəbəkə */

  async function call(path, opts = {}) {
    const resp = await fetch(path, opts);
    if (resp.status === 204) return null;
    let body = null;
    try { body = await resp.json(); } catch { /* gövdəsiz */ }
    if (!resp.ok) {
      const d = body && body.detail;
      /* Gating cavabları auth.js-in dinlədiyi hadisələrə çevrilir — həmin
         məntiq bir yerdə qalsın. */
      if (resp.status === 401) {
        document.dispatchEvent(new CustomEvent('pm:auth-required', { detail: { path } }));
      } else if (resp.status === 402) {
        document.dispatchEvent(new CustomEvent('pm:upgrade-required', { detail: d }));
      }
      const err = new Error(typeof d === 'string' ? d : (d && d.message) || resp.statusText);
      err.status = resp.status;
      throw err;
    }
    return body;
  }

  /* --------------------------------------------------------------- siyahı */

  function statusChip(doc) {
    const cls = doc.status === 'ready' ? 'ok' : doc.status === 'failed' ? 'bad' : 'wait';
    return `<span class="doc-status ${cls}">${esc(t(doc.status))}</span>`;
  }

  function render() {
    const box = $('#doc-list');
    if (!box) return;

    if (!DOCS.length) {
      box.innerHTML = `<p class="foot-note">${esc(t('empty'))}</p>`;
      return;
    }

    box.innerHTML = DOCS.map((d) => `
      <article class="doc" data-id="${d.id}">
        <div class="doc-head">
          <div class="doc-name">
            <b>${esc(d.title || d.filename)}</b>
            <small>${esc(d.filename)} · ${d.pages} ${esc(t('pages'))}</small>
          </div>
          ${statusChip(d)}
        </div>
        ${d.status === 'failed' && d.error
          ? `<p class="doc-error">${esc(d.error)}</p>` : ''}
        ${d.status === 'ready' ? `
          <form class="doc-ask" data-id="${d.id}">
            <input type="text" name="q" maxlength="500" required
                   placeholder="${esc(t('q_ph'))}">
            <button type="submit">${esc(t('ask'))}</button>
          </form>` : ''}
        <div class="doc-answer" id="doc-answer-${d.id}"></div>
        <button type="button" class="doc-del" data-id="${d.id}">${esc(t('del'))}</button>
      </article>`).join('');
  }

  async function load() {
    try {
      DOCS = await call('/api/documents') || [];
      render();
      schedulePoll();
    } catch (e) {
      /* 401 = girişsiz. Bölmə boş qalır, auth.js giriş pəncərəsini açmır —
         istifadəçi sadəcə bura baxıb keçə bilər. */
      if (e.status !== 401) console.error(e);
      DOCS = [];
      render();
    }
  }

  /* Emal fonda gedir, ona görə status özü dəyişmir — soruşmaq lazımdır.
     Yalnız «processing» varsa soruşulur və sayğac var: server ilişsə
     brauzer sonsuza qədər sorğu göndərməsin. */
  let polls = 0;
  function schedulePoll() {
    clearTimeout(polling);
    if (!DOCS.some((d) => d.status === 'processing')) { polls = 0; return; }
    if (polls++ >= POLL_LIMIT) return;
    polling = setTimeout(load, POLL_MS);
  }

  /* -------------------------------------------------------------- yükləmə */

  async function upload(file) {
    const note = $('#doc-note');
    const show = (msg, bad) => {
      note.textContent = msg;
      note.className = 'doc-note' + (bad ? ' bad' : '');
      note.hidden = false;
    };

    if (!file) return;
    if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') {
      return show(t('not_pdf'), true);
    }
    if (file.size > MAX_BYTES) return show(t('too_big'), true);

    show(t('uploading'));
    const fd = new FormData();
    fd.append('file', file);
    try {
      const doc = await call('/api/documents', { method: 'POST', body: fd });
      note.hidden = true;
      /* Siyahının başına qoyulur; təkrar yükləmədə server mövcudu qaytarır,
         ona görə dublikat yaranmasın deyə əvvəlcə süzülür. */
      DOCS = [doc, ...DOCS.filter((d) => d.id !== doc.id)];
      render();
      schedulePoll();
    } catch (e) {
      /* 401/402 üçün auth.js onsuz da pəncərə açır — burada mesaj
         təkrarlanmır, yalnız məzmun xətaları göstərilir. */
      if (e.status !== 401 && e.status !== 402) show(e.message, true);
      else note.hidden = true;
    }
  }

  /* ----------------------------------------------------------------- sual */

  async function ask(docId, question, form) {
    const out = $(`#doc-answer-${docId}`);
    const btn = form.querySelector('button');
    btn.disabled = true;
    out.innerHTML = `<p class="foot-note">${esc(t('asking'))}</p>`;

    try {
      const r = await call(`/api/documents/${docId}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 }),
      });

      /* İstinad etiketləri [1], [2] — mənbə siyahısındakı sıra ilə eyni.
         Səhifə nömrəsi məhz burada görünür: «Paper → Page → Passage». */
      const answer = esc(r.answer).replace(/\[(\d+)\]/g,
        '<sup class="cite">$1</sup>');

      const sources = r.sources.map((s, i) => `
        <li>
          <span class="cite">${i + 1}</span>
          <b>${esc(t('page'))} ${s.page}</b>
          <span class="doc-score">${Math.round(s.score * 100)}%</span>
          <p>${esc(s.excerpt)}…</p>
        </li>`).join('');

      const g = r.grounding || {};
      out.innerHTML = `
        <div class="doc-answer-body">${answer}</div>
        <ol class="doc-sources">${sources}</ol>
        <p class="foot-note">
          ${g.evidence_used} sübut · ${Math.round((g.coverage || 0) * 100)}%
          ${g.citations_removed && g.citations_removed.length
            ? ` · ${g.citations_removed.length} uydurma istinad silindi` : ''}
        </p>`;

      if (typeof r.credits_left === 'number') {
        document.dispatchEvent(new CustomEvent('pm:credits-changed', {
          detail: { left: r.credits_left },
        }));
      }
    } catch (e) {
      out.innerHTML = e.status === 409
        ? `<p class="foot-note">${esc(t('still'))}</p>`
        : (e.status === 401 || e.status === 402 ? ''
           : `<p class="pm-err">${esc(e.message)}</p>`);
    } finally {
      btn.disabled = false;
    }
  }

  /* ------------------------------------------------------------ hadisələr */

  function wire() {
    const zone = $('#doc-drop');
    const input = $('#doc-file');
    if (!zone || !input) return;

    input.addEventListener('change', () => {
      upload(input.files[0]);
      input.value = '';        // eyni faylı təkrar seçmək mümkün olsun
    });

    ['dragenter', 'dragover'].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.add('over');
      }));
    ['dragleave', 'drop'].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.remove('over');
      }));
    zone.addEventListener('drop', (e) => upload(e.dataTransfer.files[0]));

    $('#doc-list').addEventListener('submit', (e) => {
      const form = e.target.closest('.doc-ask');
      if (!form) return;
      e.preventDefault();
      const q = form.q.value.trim();
      if (q) ask(form.dataset.id, q, form);
    });

    $('#doc-list').addEventListener('click', async (e) => {
      const btn = e.target.closest('.doc-del');
      if (!btn) return;
      if (!confirm(t('del_confirm'))) return;
      await call(`/api/documents/${btn.dataset.id}`, { method: 'DELETE' }).catch(() => {});
      DOCS = DOCS.filter((d) => String(d.id) !== btn.dataset.id);
      render();
    });
  }

  function applyLang() {
    const set = (id, key) => { const el = $(id); if (el) el.textContent = t(key); };
    set('#doc-title', 'title');
    set('#doc-sub', 'sub');
    set('#doc-drop-text', 'drop');
    render();
  }

  document.addEventListener('DOMContentLoaded', () => {
    wire();
    applyLang();
    load();
    /* app.js dil hadisəsi göndərmir, ona görə düymələr birbaşa dinlənilir.
       Gecikmə lazımdır: app.js localStorage-ı bizdən sonra yazır. */
    const sw = $('#lang-switch');
    if (sw) sw.addEventListener('click', () => setTimeout(applyLang, 0));
  });
  /* Giriş və çıxışda siyahı yenilənməlidir — sənədlər istifadəçiyə bağlıdır. */
  document.addEventListener('pm:signed-in', load);
  document.addEventListener('pm:signed-out', () => { DOCS = []; render(); });
})();
