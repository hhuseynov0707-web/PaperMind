/* PaperMind — Scientific Intelligence Platform
   Vanilla JS. Every value rendered here comes from the backend API. */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* chart series — validated for CVD separation on the #111113 surface */
const SERIES = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'];
const CHART_INK = '#A1A1AA';
const CHART_GRID = '#27272A';
const CHART_SURFACE = '#151518';

/* Deltas are only trustworthy once ingestion has run continuously for several
   weeks. Below this, the first week is truncated by the backfill window, so a
   week-over-week percentage would be an artefact — we show share instead. */
const MIN_WEEKS_FOR_DELTA = 4;

/* ------------------------------------------------------------------ i18n */

const I18N = {
  az: {
    product_kicker: 'Elmi İntellekt Platforması',
    skip_to_content: 'Əsas məzmuna keç',
    nav_discover: 'Kəşf', nav_search: 'Axtarış', nav_trends: 'Trendlər', nav_digest: 'İcmal',
    m_papers: 'Məqalə', m_chunks: 'Fraqment', m_updated: 'Yeniləndi',
    hero_eyebrow: 'Araşdırmanı kəşf et',
    hero_title: 'Az axtar. Çox anla.',
    hero_sub: 'Elmi ədəbiyyatı məna üzrə axtar və ya süni intellektdən araşdırmaların nə dediyini ümumiləşdirməsini istə — hər cavab dörd akademik mənbədən gələn real məqalələrə əsaslanır.',
    mode_search: 'Axtar', mode_ask: 'AI-dan soruş',
    mode_hint_search: 'Açar söz yox — məna üzrə vektor axtarışı',
    mode_hint_ask: 'Mənbəli cavab: retrieval + Groq LLM',
    query_label: 'Araşdırma sorğusu',
    ph_search: 'Nəyi araşdırırsan? Məs.: dil modellərində hallüsinasiyaların aşkarlanması',
    ph_ask: 'Sual ver. Məs.: RAG sistemlərində retrieval-ı necə yaxşılaşdırırlar?',
    submit_search: 'Axtar', submit_ask: 'Soruş',
    scope_prefix: 'Sahə:',
    res_search: 'Axtarış nəticələri', res_ask: 'AI cavabı',
    sources_head: 'Mənbələr', relevance: 'uyğunluq', rel_short: 'uyğun',
    grounded: 'papers', grounded_pre: 'Əsaslanır:', grounded_post: 'məqalə',
    cached: 'Optimallaşdırılıb', cached_hint: 'Cavab Redis keşindən verildi',
    processing: 'Hesablandı', live_hint: 'Cavab yenidən hesablandı və keşə yazıldı',
    translated_as: 'İngiliscə axtarıldı:',
    act_read: 'Oxu', act_ask: 'Bu barədə soruş',
    ask_about: '«{t}» məqaləsi nə təklif edir?',
    loading_search: 'Elmi ədəbiyyat axtarılır…',
    loading_ask: 'Uyğun araşdırmalar analiz edilir…',
    loading_trends: 'Araşdırma trendləri yüklənir…',
    empty_title: 'Uyğun məqalə tapılmadı',
    empty_sub: 'Bu sorğu üçün bazada kifayət qədər yaxın nəticə yoxdur.',
    empty_1: 'Sorğunu bir az genişləndir',
    empty_2: 'Başqa terminologiya sına',
    empty_3: 'Digər araşdırma sahəsini seç',
    err_ai_title: 'Süni intellekt xidmətinə çıxış yoxdur',
    err_ai_sub: 'Bir azdan yenidən cəhd et.',
    err_net_title: 'Serverlə əlaqə kəsildi',
    err_net_sub: 'Backend işləmir və ya şəbəkə problemi var.',
    err_req_title: 'Sorğu qəbul olunmadı',
    err_req_sub: 'Sorğunu dəyişib yenidən cəhd et.',
    err_limit_title: 'Sorğu limiti doldu',
    err_limit_sub: 'Bir azdan yenidən cəhd et. Limit hər saat yenilənir.',
    err_generic_title: 'Nəsə düzgün getmədi',
    err_generic_sub: 'Bir azdan yenidən cəhd et.',
    details: 'Texniki detallar',
    trends_title: 'Araşdırma dinamikası',
    insight_leads: '{f} son həftədə {n} məqalə ilə öndədir ({p}% pay).',
    insight_none: 'Trend üçün hələ kifayət qədər data yoxdur.',
    note_share: 'Korpus {w} həftəni əhatə edir. Həftələrarası faiz dəyişimi {m} tam həftə davamlı yığımdan sonra aktivləşir — indi göstərilsə, backfill pəncərəsinin artefaktı olardı.',
    note_delta: 'Keçən həftə ilə müqayisə.',
    share_of_week: 'pay',
    digest_title: 'Həftəlik icmal',
    digest_sub: 'n8n avtomatlaşdırması hər bazar günü Groq ilə yaradır.',
    digest_empty: 'Hələ icmal yaradılmayıb. n8n-dəki weekly_digest workflow-u bazar günü 20:00-da işə düşür.',
    panel_title: 'Araşdırma paneli',
    areas_title: 'Araşdırma sahələri', area_all: 'Bütün araşdırmalar',
    spot_title: 'Kəşf et', spot_sub: 'Oxumağa dəyər bir şey',
    authors_title: 'Ən aktiv müəlliflər', papers_word: 'məqalə',
    status_title: 'Sistem statusu',
    st_ingest: 'arXiv yığımı', st_search: 'Semantik axtarış', st_vector: 'Vektor bazası',
    st_cache: 'Redis keşi', st_ai: 'AI mühərriki', st_workflow: 'Workflow xətaları',
    st_ok: 'İşləyir', st_bad: 'Əlçatmaz', st_configured: 'Qoşulub', st_missing: 'Açar yoxdur',
    st_none: 'Yoxdur', st_errors: 'xəta',
    open_panel: 'Paneli aç', close_panel: 'Paneli bağla', refresh: 'Yenilə',
    api_docs: 'API sənədləri',
    no_data: 'Data yoxdur',
    lang_of_paper: 'Məqalənin dili', lang_match: 'Sənin interfeys dilində',
    sources_title: 'Mənbələr', sources_word: 'mənbə',
    merged_hint: 'Eyni iş bir neçə mənbədə tapılıb — bir dəfə göstərilir',
    dedup_found: 'Birdən çox mənbədə tapılıb birləşdirilmiş: {n} məqalə. Təkrar nəticə göstərilmir.',
    dedup_none: 'Mənbələr arasında hələ üst-üstə düşən məqalə tapılmayıb.',
    months: ['yan','fev','mar','apr','may','iyn','iyl','avq','sen','okt','noy','dek'],
    fields: {
      ai: 'Süni intellekt', cv: 'Kompüter görməsi', security: 'Kibertəhlükəsizlik',
      robotics: 'Robototexnika', software: 'Proqram mühəndisliyi', data: 'Data sistemləri',
      networks: 'Şəbəkə və sistemlər', hci: 'İnsan-kompüter', other: 'Digər',
    },
    examples: ['hallüsinasiyaların aşkarlanması', 'federated learning', 'robot təhlükəsizliyi'],
  },

  ru: {
    product_kicker: 'Платформа научного интеллекта',
    skip_to_content: 'Перейти к содержимому',
    nav_discover: 'Обзор', nav_search: 'Поиск', nav_trends: 'Тренды', nav_digest: 'Дайджест',
    m_papers: 'Статей', m_chunks: 'Фрагментов', m_updated: 'Обновлено',
    hero_eyebrow: 'Исследуйте науку',
    hero_title: 'Меньше искать. Больше понимать.',
    hero_sub: 'Ищите научную литературу по смыслу или попросите ИИ обобщить, что говорят исследования — каждый ответ опирается на реальные статьи из четырёх академических источников.',
    mode_search: 'Поиск', mode_ask: 'Спросить ИИ',
    mode_hint_search: 'Не по ключевым словам — векторный поиск по смыслу',
    mode_hint_ask: 'Ответ с источниками: retrieval + Groq LLM',
    query_label: 'Исследовательский запрос',
    ph_search: 'Что вы исследуете? Напр.: обнаружение галлюцинаций в языковых моделях',
    ph_ask: 'Задайте вопрос. Напр.: как улучшают retrieval в RAG-системах?',
    submit_search: 'Искать', submit_ask: 'Спросить',
    scope_prefix: 'Область:',
    res_search: 'Результаты поиска', res_ask: 'Ответ ИИ',
    sources_head: 'Источники', relevance: 'релевантность', rel_short: 'сходство',
    grounded_pre: 'На основе', grounded_post: 'статей',
    cached: 'Оптимизировано', cached_hint: 'Ответ выдан из кэша Redis',
    processing: 'Вычислено', live_hint: 'Ответ вычислен заново и записан в кэш',
    translated_as: 'Поиск выполнен на английском:',
    act_read: 'Читать', act_ask: 'Спросить об этом',
    ask_about: 'О чём статья «{t}»?',
    loading_search: 'Поиск научной литературы…',
    loading_ask: 'Анализ релевантных исследований…',
    loading_trends: 'Загрузка трендов…',
    empty_title: 'Подходящих статей не найдено',
    empty_sub: 'В базе нет достаточно близких результатов по этому запросу.',
    empty_1: 'Сформулируйте запрос шире',
    empty_2: 'Попробуйте другую терминологию',
    empty_3: 'Выберите другую область',
    err_ai_title: 'Нет доступа к сервису ИИ',
    err_ai_sub: 'Повторите попытку через момент.',
    err_net_title: 'Нет связи с сервером',
    err_net_sub: 'Backend не отвечает или проблема с сетью.',
    err_req_title: 'Запрос не принят',
    err_req_sub: 'Измените запрос и попробуйте снова.',
    err_limit_title: 'Лимит запросов исчерпан',
    err_limit_sub: 'Повторите попытку позже — лимит обновляется каждый час.',
    err_generic_title: 'Что-то пошло не так',
    err_generic_sub: 'Повторите попытку через момент.',
    details: 'Технические детали',
    trends_title: 'Динамика исследований',
    insight_leads: '{f} лидирует за последнюю неделю: {n} статей ({p}%).',
    insight_none: 'Пока недостаточно данных для тренда.',
    note_share: 'Корпус охватывает {w} нед. Процентное изменение между неделями включится после {m} полных недель непрерывного сбора — сейчас это был бы артефакт окна backfill.',
    note_delta: 'Сравнение с предыдущей неделей.',
    share_of_week: 'доля',
    digest_title: 'Еженедельный дайджест',
    digest_sub: 'Создаётся автоматизацией n8n каждое воскресенье.',
    digest_empty: 'Дайджест ещё не создан. Workflow weekly_digest запускается в воскресенье в 20:00.',
    panel_title: 'Панель исследований',
    areas_title: 'Области исследований', area_all: 'Все области',
    spot_title: 'Обзор', spot_sub: 'Стоит прочитать',
    authors_title: 'Самые активные авторы', papers_word: 'статей',
    status_title: 'Статус системы',
    st_ingest: 'Сбор с arXiv', st_search: 'Семантический поиск', st_vector: 'Векторная база',
    st_cache: 'Кэш Redis', st_ai: 'Движок ИИ', st_workflow: 'Ошибки workflow',
    st_ok: 'Работает', st_bad: 'Недоступно', st_configured: 'Подключён', st_missing: 'Нет ключа',
    st_none: 'Нет', st_errors: 'ошибок',
    open_panel: 'Открыть панель', close_panel: 'Закрыть панель', refresh: 'Обновить',
    api_docs: 'Документация API',
    no_data: 'Нет данных',
    lang_of_paper: 'Язык статьи', lang_match: 'На языке вашего интерфейса',
    sources_title: 'Источники', sources_word: 'источн.',
    merged_hint: 'Одна и та же работа найдена в нескольких источниках — показана один раз',
    dedup_found: 'Объединено из нескольких источников: {n} статей. Дубликаты не показываются.',
    dedup_none: 'Пересечений между источниками пока не найдено.',
    months: ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'],
    fields: {
      ai: 'Искусственный интеллект', cv: 'Компьютерное зрение', security: 'Кибербезопасность',
      robotics: 'Робототехника', software: 'Программная инженерия', data: 'Системы данных',
      networks: 'Сети и системы', hci: 'Человек-компьютер', other: 'Другое',
    },
    examples: ['обнаружение галлюцинаций', 'federated learning', 'безопасность роботов'],
  },

  en: {
    product_kicker: 'Scientific Intelligence Platform',
    skip_to_content: 'Skip to content',
    nav_discover: 'Discover', nav_search: 'Search', nav_trends: 'Trends', nav_digest: 'Digest',
    m_papers: 'Papers', m_chunks: 'Chunks', m_updated: 'Updated',
    hero_eyebrow: 'Discover research',
    hero_title: 'Search less. Understand more.',
    hero_sub: 'Search scientific literature by meaning, or ask AI to synthesise what the research says — every answer grounded in real papers from four academic sources.',
    mode_search: 'Search', mode_ask: 'Ask AI',
    mode_hint_search: 'Not keywords — vector search over meaning',
    mode_hint_ask: 'Source-grounded answer: retrieval + Groq LLM',
    query_label: 'Research query',
    ph_search: 'What are you researching? E.g. hallucination detection in language models',
    ph_ask: 'Ask a question. E.g. how is retrieval improved in RAG systems?',
    submit_search: 'Search', submit_ask: 'Ask',
    scope_prefix: 'Area:',
    res_search: 'Search results', res_ask: 'AI answer',
    sources_head: 'Sources', relevance: 'relevance', rel_short: 'match',
    grounded_pre: 'Grounded in', grounded_post: 'papers',
    cached: 'Optimized', cached_hint: 'Response served from Redis cache',
    processing: 'Processed', live_hint: 'Computed fresh and written to cache',
    translated_as: 'Searched in English as:',
    act_read: 'Read', act_ask: 'Ask about this',
    ask_about: 'What does the paper “{t}” propose?',
    loading_search: 'Searching scientific literature…',
    loading_ask: 'Analyzing relevant research…',
    loading_trends: 'Loading research trends…',
    empty_title: 'No relevant papers found',
    empty_sub: 'Nothing in the corpus is close enough to this query.',
    empty_1: 'Try a broader question',
    empty_2: 'Try different terminology',
    empty_3: 'Switch to another research area',
    err_ai_title: 'Unable to reach the AI service',
    err_ai_sub: 'Please try again in a moment.',
    err_net_title: 'Cannot reach the server',
    err_net_sub: 'The backend is down or the network failed.',
    err_req_title: 'That request was not accepted',
    err_req_sub: 'Adjust the query and try again.',
    err_limit_title: 'Request limit reached',
    err_limit_sub: 'Try again shortly — the limit resets every hour.',
    err_generic_title: 'Something went wrong',
    err_generic_sub: 'Please try again in a moment.',
    details: 'Technical details',
    trends_title: 'Research momentum',
    insight_leads: '{f} leads the last week with {n} papers ({p}% share).',
    insight_none: 'Not enough data yet to describe a trend.',
    note_share: 'Corpus spans {w} week(s). Week-over-week percentages unlock after {m} full weeks of continuous ingestion — shown now they would be an artefact of the backfill window.',
    note_delta: 'Compared with the previous week.',
    share_of_week: 'share',
    digest_title: 'Weekly digest',
    digest_sub: 'Generated every Sunday by the n8n automation pipeline.',
    digest_empty: 'No digest yet. The weekly_digest workflow runs on Sunday at 20:00.',
    panel_title: 'Research panel',
    areas_title: 'Research areas', area_all: 'All research',
    spot_title: 'Discover', spot_sub: 'Something worth reading',
    authors_title: 'Most active authors', papers_word: 'papers',
    status_title: 'System status',
    st_ingest: 'arXiv ingestion', st_search: 'Semantic search', st_vector: 'Vector database',
    st_cache: 'Redis cache', st_ai: 'AI inference', st_workflow: 'Workflow errors',
    st_ok: 'Healthy', st_bad: 'Unreachable', st_configured: 'Connected', st_missing: 'No API key',
    st_none: 'None', st_errors: 'errors',
    open_panel: 'Open panel', close_panel: 'Close panel', refresh: 'Refresh',
    api_docs: 'API reference',
    no_data: 'No data',
    lang_of_paper: 'Language of the paper', lang_match: 'In your interface language',
    sources_title: 'Sources', sources_word: 'sources',
    merged_hint: 'The same work was found in several sources — shown once',
    dedup_found: 'Merged across sources: {n} papers. Duplicates are not shown.',
    dedup_none: 'No overlap between sources found yet.',
    months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
    fields: {
      ai: 'Artificial intelligence', cv: 'Computer vision', security: 'Cybersecurity',
      robotics: 'Robotics', software: 'Software engineering', data: 'Data systems',
      networks: 'Networks & systems', hci: 'Human-computer', other: 'Other',
    },
    examples: ['hallucination detection', 'federated learning', 'robot safety'],
  },
};

const GLYPH = {
  '': '◉', ai: '✦', cv: '◈', security: '⌁', robotics: '⬡',
  software: '⌘', data: '▤', networks: '⋔', hci: '◇', other: '·',
};

/* mənbə identifikasiyası — ad və rəng (data seriyalarından ayrı) */
const SOURCE_META = {
  arxiv:    { label: 'arXiv',    color: '#d95926' },
  crossref: { label: 'Crossref', color: '#3987e5' },
  doaj:     { label: 'DOAJ',     color: '#199e70' },
};
const sourceLabel = (s) => SOURCE_META[s]?.label ?? s;
const sourceColor = (s) => SOURCE_META[s]?.color ?? '#71717A';

/* arXiv category codes -> readable names (code kept as tooltip) */
const CAT_NAMES = {
  az: { 'cs.AI':'Süni intellekt','cs.LG':'Maşın öyrənməsi','cs.CL':'Dil emalı (NLP)','cs.NE':'Neyroşəbəkələr','stat.ML':'Statistik öyrənmə','cs.CV':'Kompüter görməsi','eess.IV':'Şəkil emalı','cs.CR':'Təhlükəsizlik','cs.RO':'Robototexnika','cs.SY':'İdarəetmə sistemləri','eess.SY':'İdarəetmə sistemləri','cs.SE':'Proqram mühəndisliyi','cs.PL':'Proqramlaşdırma dilləri','cs.DB':'Verilənlər bazası','cs.IR':'İnformasiya axtarışı','cs.DC':'Paylanmış sistemlər','cs.NI':'Şəbəkələr','cs.OS':'Əməliyyat sistemləri','cs.AR':'Kompüter arxitekturası','cs.HC':'İnsan-kompüter','cs.CY':'Texnologiya və cəmiyyət' },
  ru: { 'cs.AI':'Искусственный интеллект','cs.LG':'Машинное обучение','cs.CL':'Обработка языка (NLP)','cs.NE':'Нейросети','stat.ML':'Статистическое обучение','cs.CV':'Компьютерное зрение','eess.IV':'Обработка изображений','cs.CR':'Безопасность','cs.RO':'Робототехника','cs.SY':'Системы управления','eess.SY':'Системы управления','cs.SE':'Программная инженерия','cs.PL':'Языки программирования','cs.DB':'Базы данных','cs.IR':'Информационный поиск','cs.DC':'Распределённые системы','cs.NI':'Сети','cs.OS':'Операционные системы','cs.AR':'Архитектура компьютеров','cs.HC':'Человек-компьютер','cs.CY':'Технологии и общество' },
  en: { 'cs.AI':'Artificial intelligence','cs.LG':'Machine learning','cs.CL':'Language processing (NLP)','cs.NE':'Neural computing','stat.ML':'Statistical learning','cs.CV':'Computer vision','eess.IV':'Image processing','cs.CR':'Security','cs.RO':'Robotics','cs.SY':'Control systems','eess.SY':'Control systems','cs.SE':'Software engineering','cs.PL':'Programming languages','cs.DB':'Databases','cs.IR':'Information retrieval','cs.DC':'Distributed systems','cs.NI':'Networks','cs.OS':'Operating systems','cs.AR':'Computer architecture','cs.HC':'Human-computer','cs.CY':'Tech and society' },
};

/* ------------------------------------------------------------------ state */

let LANG = localStorage.getItem('pm_lang') || 'az';
if (!I18N[LANG]) LANG = 'az';
let FIELD = localStorage.getItem('pm_field') || '';
let MODE = 'search';

let fields = [];          // [{key, count, categories[]}]
let catToField = {};      // 'cs.LG' -> 'ai'
let totalPapers = null;   // distinct total; field counts overlap via cross-listing
let trendChart = null;

const t = (k) => I18N[LANG][k] ?? I18N.en[k] ?? k;
const fieldName = (k) => I18N[LANG].fields[k] ?? I18N.en.fields[k] ?? k;
const catName = (c) => (c ? CAT_NAMES[LANG][c] ?? c : '—');

/* ------------------------------------------------------------------ utils */

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const nf = () => new Intl.NumberFormat(LANG === 'en' ? 'en-US' : LANG === 'ru' ? 'ru-RU' : 'az-AZ');
const num = (n) => nf().format(n);

function hhmm(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}
function dmy(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${d.getDate()} ${t('months')[d.getMonth()]} ${d.getFullYear()}`;
}
function dm(iso) {
  const d = new Date(iso);
  return `${d.getDate()} ${t('months')[d.getMonth()]}`;
}
function ms(v) { return v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`; }

class ApiError extends Error {
  constructor(status, detail) { super(detail || `HTTP ${status}`); this.status = status; this.detail = detail; }
}

async function api(path, opts = {}) {
  const t0 = performance.now();
  let resp;
  try {
    resp = await fetch(path, opts);
  } catch (e) {
    throw new ApiError(0, e.message);
  }
  const took = Math.round(performance.now() - t0);
  if (!resp.ok) {
    let detail;
    try { detail = (await resp.json()).detail; } catch { detail = resp.statusText; }
    throw new ApiError(resp.status, typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return { data: await resp.json(), took, cache: resp.headers.get('X-Cache') };
}

let toastTimer;
function toast(msg) {
  const el = $('#toast');
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 5500);
}

/* ------------------------------------------------------------------ i18n apply */

function applyI18n() {
  document.documentElement.lang = LANG;
  $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$('[data-i18n-ph]').forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  $$('[data-i18n-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  $$('#lang-switch button').forEach((b) => b.classList.toggle('on', b.dataset.lang === LANG));
  syncMode();
  renderAreas();
  renderExamples();
}

function setLang(l) {
  LANG = l;
  localStorage.setItem('pm_lang', l);
  applyI18n();
  $('#results').innerHTML = '';
  loadAll();
}

/* ------------------------------------------------------------------ console */

function syncMode() {
  const ask = MODE === 'ask';
  $('#query-form').classList.toggle('ask', ask);
  $$('.mode').forEach((b) => {
    const on = b.dataset.mode === MODE;
    b.classList.toggle('on', on);
    b.setAttribute('aria-selected', String(on));
  });
  $('#mode-hint').textContent = t(ask ? 'mode_hint_ask' : 'mode_hint_search');
  $('#q').placeholder = t(ask ? 'ph_ask' : 'ph_search');
  $('#submit-btn').firstElementChild.textContent = t(ask ? 'submit_ask' : 'submit_search');
  renderScope();
}

function setMode(m) { MODE = m; syncMode(); }

function renderScope() {
  const el = $('#scope-chip');
  if (!FIELD) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `<span aria-hidden="true">${GLYPH[FIELD] || '◉'}</span> ${t('scope_prefix')} ${esc(fieldName(FIELD))}`;
}

function renderExamples() {
  $('#examples').innerHTML = t('examples')
    .map((x) => `<button type="button" class="example">${esc(x)}</button>`).join('');
}

/* ------------------------------------------------------------------ areas */

async function loadFields() {
  try {
    const { data } = await api('/api/fields');
    fields = data;
    catToField = {};
    data.forEach((f) => (f.categories || []).forEach((c) => { catToField[c] = f.key; }));
    renderAreas();
  } catch (e) { toast(errTitle(e)); }
}

function renderAreas() {
  /* Field counts overlap (a paper can be cross-listed), so "all" uses the
     distinct total from /api/analytics/summary rather than their sum. */
  const rows = [{ key: '', name: t('area_all'), count: totalPapers }]
    .concat([...fields].sort((a, b) => b.count - a.count)
      .map((f) => ({ key: f.key, name: fieldName(f.key), count: f.count })));

  $('#areas').innerHTML = rows.map((r) => `
    <button type="button" class="area ${FIELD === r.key ? 'on' : ''}" data-field="${esc(r.key)}"
            role="option" aria-selected="${FIELD === r.key}">
      <span class="glyph" aria-hidden="true">${GLYPH[r.key] || '·'}</span>
      <span class="nm">${esc(r.name)}</span>
      <span class="ct">${r.count == null ? '' : num(r.count)}</span>
    </button>`).join('');
}

function setField(k) {
  FIELD = k;
  localStorage.setItem('pm_field', k);
  renderAreas();
  renderScope();
}

/* ------------------------------------------------------------------ metrics */

async function loadSummary() {
  try {
    const { data } = await api('/api/analytics/summary');
    totalPapers = data.total_papers;
    renderAreas();
    renderSources(data);
    $('#metrics').innerHTML = `
      <div><dt>${t('m_papers')}</dt><dd>${num(data.total_papers)}</dd></div>
      <div><dt>${t('m_chunks')}</dt><dd>${num(data.total_chunks)}</dd></div>
      <div><dt>${t('m_updated')}</dt><dd>${hhmm(data.last_ingest)}</dd></div>`;
  } catch (e) { /* header metrics are non-critical */ }
}

function renderSources(summary) {
  const rows = summary.by_source || [];
  $('#srclist').innerHTML = rows.length
    ? rows.map((r) => `
        <li>
          <span class="sdot" style="background:${sourceColor(r.source)}"></span>
          <span class="sn">${esc(sourceLabel(r.source))}</span>
          <span class="sc">${num(r.count)}</span>
        </li>`).join('')
    : `<li class="sn">${t('no_data')}</li>`;

  const n = summary.multi_source || 0;
  $('#dedup-note').textContent = n > 0
    ? t('dedup_found').replace('{n}', num(n))
    : t('dedup_none');
}

/* ------------------------------------------------------------------ query */

function errTitle(e) {
  if (e.status === 0) return t('err_net_title');
  if (e.status === 429) return t('err_limit_title');     // sürət limiti — öz qorumamız
  if (e.status === 503 || e.status === 502) return t('err_ai_title');
  if (e.status === 422 || e.status === 400) return t('err_req_title');
  return t('err_generic_title');
}
function errSub(e) {
  if (e.status === 0) return t('err_net_sub');
  if (e.status === 429) return e.detail || t('err_limit_sub');
  if (e.status === 503 || e.status === 502) return t('err_ai_sub');
  if (e.status === 422 || e.status === 400) return t('err_req_sub');
  return t('err_generic_sub');
}

function renderError(e) {
  $('#results').innerHTML = `
    <div class="state err">
      <h3>${esc(errTitle(e))}</h3>
      <p>${esc(errSub(e))}</p>
      ${e.detail ? `<details><summary>${t('details')}</summary><pre>${esc(e.detail)}</pre></details>` : ''}
    </div>`;
}

function renderEmpty() {
  $('#results').innerHTML = `
    <div class="state">
      <h3>${t('empty_title')}</h3>
      <p>${t('empty_sub')}</p>
      <ul><li>· ${t('empty_1')}</li><li>· ${t('empty_2')}</li><li>· ${t('empty_3')}</li></ul>
    </div>`;
}

function skeleton(kind) {
  const r = $('#results');
  r.classList.toggle('ai', kind === 'ask');
  r.setAttribute('aria-busy', 'true');
  const note = `<div class="loading-note"><span class="spinner"></span>${t(kind === 'ask' ? 'loading_ask' : 'loading_search')}</div>`;
  const card = `<div class="skel-card"><div class="sk circle"></div><div>
      <div class="sk title"></div><div class="sk line"></div>
      <div class="sk line short" style="margin-top:8px"></div></div></div>`;
  r.innerHTML = note + `<div class="skel">${card.repeat(kind === 'ask' ? 2 : 3)}</div>`;
}

/* Məqalənin dili — istifadəçinin interfeys dili ilə üst-üstə düşəndə vurğulanır */
function langChip(p) {
  const lang = p.language || 'en';
  const label = lang === 'ru' ? 'Рус' : 'Eng';
  const match = lang === LANG;
  return `<span class="lang-chip ${match ? 'match' : ''}" title="${esc(t(match ? 'lang_match' : 'lang_of_paper'))}">${label}</span>`;
}

/* Məqalənin kanonik istinadı — arXiv ID varsa o, yoxsa DOI */
function paperRef(p) {
  if (p.arxiv_id) return `arXiv:${p.arxiv_id}`;
  if (p.doi) return `DOI:${p.doi}`;
  return '';
}

/* Mənbə nişanları; birdən çox mənbə varsa dedup-un işlədiyi görünür */
function sourceChips(p) {
  const list = p.sources && p.sources.length ? p.sources : (p.source ? [p.source] : []);
  if (!list.length) return '';
  const chips = list.map((s) =>
    `<span class="src" style="color:${sourceColor(s)}"><i></i>${esc(sourceLabel(s))}</span>`).join('');
  const merged = list.length > 1
    ? `<span class="src merged" title="${esc(t('merged_hint'))}">⧉ ${list.length} ${esc(t('sources_word'))}</span>`
    : '';
  return chips + merged;
}

function relevanceRing(score) {
  const C = 2 * Math.PI * 15.5;
  const pct = Math.max(0, Math.min(1, score));
  return `<div class="ring" title="${(pct * 100).toFixed(1)}% ${esc(t('relevance'))}">
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <circle class="track" cx="18" cy="18" r="15.5"></circle>
        <circle class="arc" cx="18" cy="18" r="15.5"
                stroke-dasharray="${(pct * C).toFixed(1)} ${C.toFixed(1)}"></circle>
      </svg>
      <b>${Math.round(pct * 100)}%</b>
    </div><span class="ring-label">${esc(t('rel_short'))}</span>`;
}

async function runSearch(q) {
  skeleton('search');
  const fp = FIELD ? `&field=${encodeURIComponent(FIELD)}` : '';
  const { data, took } = await api(`/api/search?q=${encodeURIComponent(q)}&top_k=6${fp}`);
  const r = $('#results');
  r.setAttribute('aria-busy', 'false');

  if (!data.hits.length) return renderEmpty();

  const head = `
    <div class="res-head">
      <h2>${t('res_search')}</h2>
      <div class="res-meta">
        <span class="badge">${data.hits.length} · ${esc(t('grounded_post'))}</span>
        <span class="badge live"><span class="dot"></span>${ms(took)}</span>
      </div>
    </div>
    ${data.query_en ? `<p class="translated">${t('translated_as')} <code>${esc(data.query_en)}</code></p>` : ''}`;

  r.innerHTML = head + data.hits.map((h) => {
    const p = h.paper;
    const authors = p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '');
    return `
      <article class="paper">
        <div>${relevanceRing(h.score)}</div>
        <div>
          <a class="paper-title" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">${esc(p.title)}</a>
          <div class="paper-meta">
            <span class="field" title="${esc(p.primary_category || '')}">${esc(catName(p.primary_category))}</span>
            <span class="sep">·</span><span>${p.published_at ? dmy(p.published_at) : ''}</span>
            <span class="sep">·</span><span class="aid">${esc(paperRef(p))}</span>
            ${authors ? `<span class="sep">·</span><span>${esc(authors)}</span>` : ''}
            ${langChip(p)}${sourceChips(p)}
          </div>
          <p class="paper-abs">${esc(p.abstract)}</p>
          <div class="paper-actions">
            <a class="act" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">
              <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M5 2H2.5v9.5H12V9M8 2h4v4M12 2 6.5 7.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
              ${t('act_read')}</a>
            <button type="button" class="act ai" data-ask="${esc(p.title)}">
              <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.4l1.3 3.3L11.6 6 8.3 7.3 7 10.6 5.7 7.3 2.4 6l3.3-1.3z" fill="currentColor"/></svg>
              ${t('act_ask')}</button>
          </div>
        </div>
      </article>`;
  }).join('');
}

async function runAsk(q) {
  skeleton('ask');
  const { data } = await api('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q, top_k: 5, field: FIELD || null }),
  });
  const r = $('#results');
  r.setAttribute('aria-busy', 'false');

  const cacheBadge = data.from_cache
    ? `<span class="badge cached" title="${esc(t('cached_hint'))}">⚡ ${t('cached')} · ${ms(data.latency_ms)}</span>`
    : `<span class="badge live" title="${esc(t('live_hint'))}"><span class="dot"></span>${t('processing')} · ${ms(data.latency_ms)}</span>`;

  // arXiv ID (2608.01234) və DOI (10.1145/xxx) istinadlarının hər ikisi vurğulanır
  const answer = esc(data.answer)
    .replace(/\[(\d{4}\.\d{4,5}(?:v\d+)?)\]/g, '<span class="cite">[$1]</span>')
    .replace(/\[(10\.\d{4,9}\/[^\]\s]+)\]/g, '<span class="cite">[$1]</span>');

  r.innerHTML = `
    <div class="answer-panel">
      <div class="answer-head">
        <h2><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.4l1.3 3.3L11.6 6 8.3 7.3 7 10.6 5.7 7.3 2.4 6l3.3-1.3z" fill="currentColor"/></svg>${t('res_ask')}</h2>
        <div class="res-meta">
          <span class="badge ai">${t('grounded_pre')} ${data.sources.length} ${t('grounded_post')}</span>
          ${cacheBadge}
        </div>
      </div>
      ${data.query_en ? `<p class="translated" style="margin-bottom:14px">${t('translated_as')} <code>${esc(data.query_en)}</code></p>` : ''}
      <div class="answer-body">${answer}</div>
      ${data.sources.length ? `
        <div class="sources-head">${t('sources_head')}</div>
        <div class="sources">
          ${data.sources.map((s, i) => `
            <a class="source" href="${esc(s.pdf_url || '#')}" target="_blank" rel="noopener">
              <span class="idx">${i + 1}</span>
              <span class="st"><b>${esc(s.title)}</b><span>${esc(paperRef(s))}</span></span>
              <span class="sc">${Math.round(s.score * 100)}% ${esc(t('rel_short'))}</span>
            </a>`).join('')}
        </div>` : ''}
    </div>`;
}

async function onSubmit(ev) {
  ev.preventDefault();
  const q = $('#q').value.trim();
  if (q.length < 2) return;
  const btn = $('#submit-btn');
  btn.disabled = true;
  try {
    if (MODE === 'ask') await runAsk(q); else await runSearch(q);
    $('#results').scrollIntoView({ block: 'start', behavior: 'smooth' });
  } catch (e) {
    $('#results').setAttribute('aria-busy', 'false');
    renderError(e);
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------------ trends */

function weeklyByField(rows) {
  const weeks = [...new Set(rows.map((r) => r.week))].sort();
  const map = {};                       // field -> {week: count}
  rows.forEach((r) => {
    // Backend artıq sahə açarı qaytarır (əvvəl arXiv kateqoriyası idi)
    const f = r.category in I18N.en.fields ? r.category : 'other';
    (map[f] ||= {})[r.week] = (map[f][r.week] || 0) + r.count;
  });
  return { weeks, map };
}

async function loadTrends() {
  const note = $('#trend-insight');
  note.textContent = t('loading_trends');
  try {
    const { data, took, cache } = await api('/api/analytics/trends?weeks=8');
    const perf = $('#trend-perf');
    perf.hidden = false;
    perf.textContent = cache === 'HIT' ? `⚡ ${t('cached')} · ${ms(took)}` : `${t('processing')} · ${ms(took)}`;
    perf.title = cache === 'HIT' ? t('cached_hint') : t('live_hint');

    if (!data.length) {
      note.textContent = t('insight_none');
      $('#trend-deltas').innerHTML = '';
      $('#trend-note').textContent = '';
      return;
    }

    const { weeks, map } = weeklyByField(data);
    const totals = Object.entries(map)
      .map(([k, byWeek]) => [k, Object.values(byWeek).reduce((a, b) => a + b, 0)])
      .sort((a, b) => b[1] - a[1]);

    /* palette holds 5 validated hues -> top 4 fields + Other, never cycled */
    const top = totals.slice(0, 4).map(([k]) => k);
    const series = [...top, 'other'];
    const bucket = (f) => (top.includes(f) ? f : 'other');

    const stacks = {};
    series.forEach((s) => (stacks[s] = weeks.map(() => 0)));
    Object.entries(map).forEach(([f, byWeek]) => {
      const s = bucket(f);
      weeks.forEach((w, i) => { stacks[s][i] += byWeek[w] || 0; });
    });

    const last = weeks[weeks.length - 1];
    const lastTotal = Object.values(map).reduce((sum, bw) => sum + (bw[last] || 0), 0);
    const lastByField = Object.entries(map)
      .map(([f, bw]) => [f, bw[last] || 0])
      .filter(([, n]) => n > 0)
      .sort((a, b) => b[1] - a[1]);

    if (lastByField.length && lastTotal) {
      const [f, n] = lastByField[0];
      note.textContent = t('insight_leads')
        .replace('{f}', fieldName(f)).replace('{n}', num(n))
        .replace('{p}', ((n / lastTotal) * 100).toFixed(1));
    } else {
      note.textContent = t('insight_none');
    }

    renderDeltas(weeks, map, lastByField, lastTotal);
    drawChart(weeks, series, stacks);
  } catch (e) {
    note.textContent = t('insight_none');
    toast(errTitle(e));
  }
}

function renderDeltas(weeks, map, lastByField, lastTotal) {
  const useDelta = weeks.length >= MIN_WEEKS_FOR_DELTA;
  const prev = weeks[weeks.length - 2];
  const last = weeks[weeks.length - 1];

  const rows = lastByField.slice(0, 6).map(([f, n], i) => {
    const colour = SERIES[i % SERIES.length];
    let val, cls = '';
    if (useDelta && prev) {
      const before = map[f][prev] || 0;
      if (before > 0) {
        const pct = ((n - before) / before) * 100;
        cls = pct >= 0 ? 'up' : 'down';
        val = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
      } else { val = '—'; }
    } else {
      val = `${((n / lastTotal) * 100).toFixed(1)}%`;
    }
    return `<div class="delta">
        <span class="dn"><i style="background:${colour}"></i><span>${esc(fieldName(f))}</span></span>
        <span class="dv ${cls}">${val}</span>
      </div>`;
  });

  $('#trend-deltas').innerHTML = rows.join('');
  $('#trend-note').textContent = useDelta
    ? t('note_delta')
    : t('note_share').replace('{w}', weeks.length).replace('{m}', MIN_WEEKS_FOR_DELTA);
}

function drawChart(weeks, series, stacks) {
  if (typeof Chart === 'undefined') return;
  const datasets = series.map((s, i) => ({
    label: fieldName(s),
    data: stacks[s],
    backgroundColor: SERIES[i % SERIES.length],
    borderColor: CHART_SURFACE,
    borderWidth: 2,
    borderRadius: 3,
    maxBarThickness: 46,
    stack: 'w',
  }));

  if (trendChart) trendChart.destroy();
  trendChart = new Chart($('#trend-chart'), {
    type: 'bar',
    data: { labels: weeks.map(dm), datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 220 },
      scales: {
        x: { stacked: true, grid: { display: false }, border: { color: CHART_GRID },
             ticks: { color: CHART_INK, font: { size: 11 } } },
        y: { stacked: true, border: { display: false },
             grid: { color: CHART_GRID, drawTicks: false },
             ticks: { color: CHART_INK, font: { size: 11 }, padding: 8 } },
      },
      plugins: {
        legend: { position: 'bottom',
          labels: { color: CHART_INK, boxWidth: 9, boxHeight: 9, usePointStyle: true,
                    pointStyle: 'rectRounded', padding: 14, font: { size: 11.5 } } },
        tooltip: { backgroundColor: '#0d0d10', borderColor: CHART_GRID, borderWidth: 1,
                   titleColor: '#fafafa', bodyColor: '#a1a1aa', padding: 10, cornerRadius: 8,
                   displayColors: true, boxPadding: 4 },
      },
    },
  });
}

/* ------------------------------------------------------------------ discover */

let spot = [], spotIdx = 0, spotTimer = null, spotStart = 0, spotPaused = false, spotRaf = null;
const SPOT_MS = 15000;

async function loadSpotlight() {
  try {
    const { data } = await api('/api/papers/featured?limit=6');
    if (!data.length) return;
    spot = data; spotIdx = 0;
    $('#discover-card').hidden = false;
    renderSpot();
    clearInterval(spotTimer);
    spotStart = performance.now();
    spotTimer = setInterval(() => {
      if (spotPaused || spot.length < 2) return;
      spotIdx = (spotIdx + 1) % spot.length;
      spotStart = performance.now();
      renderSpot();
    }, SPOT_MS);
    cancelAnimationFrame(spotRaf);
    tickSpot();
  } catch { /* discovery panel is optional */ }
}

function tickSpot() {
  const arc = $('#spot-arc');
  if (arc) {
    const C = 2 * Math.PI * 8;
    const p = spotPaused ? null : Math.min(1, (performance.now() - spotStart) / SPOT_MS);
    if (p !== null) arc.setAttribute('stroke-dasharray', `${(p * C).toFixed(2)} ${C.toFixed(2)}`);
  }
  spotRaf = requestAnimationFrame(tickSpot);
}

function renderSpot() {
  const p = spot[spotIdx];
  if (!p) return;
  $('#spot-body').innerHTML = `
    <div class="spot-item">
      <span class="spot-field" title="${esc(p.primary_category || '')}">${esc(catName(p.primary_category))}</span>
      <a class="spot-title" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">${esc(p.title)}</a>
      <p class="spot-abs">${esc(p.abstract)}</p>
      <a class="act" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">
        <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M5 2H2.5v9.5H12V9M8 2h4v4M12 2 6.5 7.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
        ${t('act_read')}</a>
    </div>`;
}

/* ------------------------------------------------------------------ authors / digest / status */

async function loadAuthors() {
  try {
    const { data } = await api('/api/analytics/top-authors?limit=6');
    const max = Math.max(...data.map((a) => a.count), 1);
    $('#authors').innerHTML = data.map((a) => `
      <li>
        <span class="row"><span>${esc(a.name)}</span><span>${num(a.count)} ${t('papers_word')}</span></span>
        <span class="bar" style="width:${(a.count / max) * 100}%"></span>
      </li>`).join('') || `<li class="row"><span>${t('no_data')}</span></li>`;
  } catch { /* non-critical */ }
}

async function loadDigest() {
  try {
    const { data } = await api('/api/digests/latest');
    const body = $('#digest-body'), date = $('#digest-date');
    if (data) {
      body.innerHTML = `<div class="digest-text">${esc(data.content)}</div>`;
      date.hidden = false;
      date.textContent = dmy(data.week_start);
    } else {
      date.hidden = true;
      body.innerHTML = `<div class="state"><p>${t('digest_empty')}</p></div>`;
    }
  } catch (e) { $('#digest-body').innerHTML = ''; }
}

async function loadStatus() {
  const led = (ok) => `<span class="led ${ok ? 'ok' : 'bad'}"></span>`;
  try {
    const [{ data: h }, errs] = await Promise.all([
      api('/health/services'),
      api('/api/logs/errors?limit=5').catch(() => ({ data: [] })),
    ]);
    const nErr = errs.data.length;
    const ingestOk = h.last_ingest_status === 'success';

    $('#status').innerHTML = `
      <li>${led(ingestOk)}${t('st_ingest')}<span class="val">${h.last_ingest_at ? hhmm(h.last_ingest_at) : t('st_none')}</span></li>
      <li>${led(h.postgres)}${t('st_search')}<span class="val">${h.postgres ? t('st_ok') : t('st_bad')}</span></li>
      <li>${led(h.pgvector)}${t('st_vector')}<span class="val">${h.pgvector ? t('st_ok') : t('st_bad')}</span></li>
      <li>${led(h.redis)}${t('st_cache')}<span class="val">${h.redis ? t('st_ok') : t('st_bad')}</span></li>
      <li>${led(h.groq_configured)}${t('st_ai')}<span class="val">${h.groq_configured ? t('st_configured') : t('st_missing')}</span></li>
      <li>${led(nErr === 0)}${t('st_workflow')}<span class="val">${nErr === 0 ? t('st_none') : `${nErr} ${t('st_errors')}`}</span></li>`;
    $('#status-note').textContent = '';
  } catch (e) {
    $('#status').innerHTML = '';
    $('#status-note').textContent = errTitle(e);
  }
}

/* ------------------------------------------------------------------ chrome */

function initNav() {
  const links = $$('.nav a');
  const secs = links.map((a) => $(a.getAttribute('href')));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      links.forEach((a) => a.classList.toggle('on', $(a.getAttribute('href')) === en.target));
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  secs.forEach((s) => s && io.observe(s));
}

function initDrawer() {
  const side = $('#side'), scrim = $('#scrim'), btn = $('#drawer-toggle');
  const set = (open) => {
    side.classList.toggle('open', open);
    scrim.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    if (open) side.querySelector('button')?.focus();
  };
  btn.addEventListener('click', () => set(!side.classList.contains('open')));
  $('#drawer-close').addEventListener('click', () => set(false));
  scrim.addEventListener('click', () => set(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && side.classList.contains('open')) set(false);
  });
  return set;
}

/* ------------------------------------------------------------------ init */

function loadAll() {
  loadSummary();
  loadTrends();
  loadAuthors();
  loadDigest();
  loadStatus();
  loadSpotlight();
}

document.addEventListener('DOMContentLoaded', () => {
  applyI18n();
  const setDrawer = initDrawer();
  initNav();

  $('#query-form').addEventListener('submit', onSubmit);
  $('#lang-switch').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-lang]');
    if (b) setLang(b.dataset.lang);
  });
  $$('.mode').forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));
  $('#examples').addEventListener('click', (e) => {
    const b = e.target.closest('.example');
    if (!b) return;
    $('#q').value = b.textContent;
    $('#query-form').requestSubmit();
  });
  $('#areas').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-field]');
    if (!b) return;
    setField(b.dataset.field);
    if (window.matchMedia('(max-width: 960px)').matches) setDrawer(false);
  });
  $('#results').addEventListener('click', (e) => {
    const b = e.target.closest('[data-ask]');
    if (!b) return;
    setMode('ask');
    $('#q').value = t('ask_about').replace('{t}', b.dataset.ask);
    $('#q').focus();
    $('#query-form').requestSubmit();
  });
  $('#trend-refresh').addEventListener('click', loadTrends);

  const card = $('#discover-card');
  card.addEventListener('mouseenter', () => { spotPaused = true; });
  card.addEventListener('mouseleave', () => { spotPaused = false; spotStart = performance.now(); });
  card.addEventListener('focusin', () => { spotPaused = true; });
  card.addEventListener('focusout', () => { spotPaused = false; spotStart = performance.now(); });

  loadFields();
  loadAll();
});
