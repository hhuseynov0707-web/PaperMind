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
/* Az sayda məqalə üzərində faiz mənasızdır: 1→8 məqalə «+700%» kimi görünür.
   Keçən həftədə bu qədər məqalə olmasa, pay rejimi göstərilir. */
const MIN_VOLUME_FOR_DELTA = 40;

/* ------------------------------------------------------------------ i18n */

const I18N = {
  az: {
    product_kicker: 'Elmi İntellekt Platforması',
    corpus_note: 'Bu cavab indekslənmiş korpusa əsaslanır: {n} məqalə · {src} · {langs}',
    chat_you: 'Sən',
    chat_placeholder: 'Davam et — sual ver...',
    chat_send: 'Göndər',
    chat_new: 'Yeni söhbət',
    intent_hint: 'Bu, «{i}» sualına oxşayır.',
    intent_go: 'Aç',
    intent_pick_papers: 'Müqayisə üçün nəticələrdən məqalə seç.',
    i_COMPARE: 'müqayisə',
    i_CONTRADICTION: 'ziddiyyətli sübut',
    i_TREND: 'trend',
    i_EMERGING_TOPIC: 'yeni yaranan mövzular',
    i_RESEARCH_GAP: 'tədqiqat boşluğu',
    i_CROSS_DISCIPLINARY: 'fənlərarası əlaqə',
    i_EXPLAIN: 'izah',
    filter_note: 'Süzgəc: {f}',
    f_author: 'müəllif',
    f_years: 'il',
    nav_landscape: 'Landşaft',
    landscape_title: 'Tədqiqat landşaftı',
    landscape_sub: 'Mövzu qrupları, aktiv müəlliflər və sahələr arasındakı əlaqələr — kitabxanadakı məqalələr üzərində qurulub.',
    landscape_empty: 'Landşaft üçün əvvəlcə axtarış et.',
    lx_clusters: 'Klasterlər',
    lx_authors: 'Ən aktiv müəlliflər',
    lx_cross: 'Fənlərarası əlaqələr',
    lx_papers: 'məqalə',
    trend_classes_title: 'Trend təsnifatı',
    tc_EMERGING: 'Yeni yaranır',
    tc_GROWING: 'Artır',
    tc_STABLE: 'Sabit',
    tc_DECLINING: 'Azalır',
    tc_INSUFFICIENT_DATA: 'Data kifayət etmir',
    skip_to_content: 'Əsas məzmuna keç',
    nav_discover: 'Kəşf', nav_search: 'Axtarış', nav_browse: 'Vərəqlə', nav_trends: 'Trendlər', nav_digest: 'İcmal',
    m_papers: 'Məqalə', m_chunks: 'Fraqment', m_updated: 'Yeniləndi',
    hero_eyebrow: 'Araşdırmanı kəşf et',
    hero_title: 'Az axtar. Çox anla.',
    hero_sub: 'Elmi ədəbiyyatı məna üzrə axtar və ya süni intellektdən araşdırmaların nə dediyini ümumiləşdirməsini istə — hər cavab dörd akademik mənbədən gələn real məqalələrə əsaslanır.',
    mode_search: 'Axtar', mode_ask: 'AI-dan soruş',
    mode_hint_search: 'Dəqiq sözü tapmaq lazım deyil — mənaya görə axtarır',
    mode_hint_ask: 'AI cavab verir, hər fikrin altında məqaləni göstərir',
    query_label: 'Araşdırma sorğusu',
    ph_search: 'Nəyi araşdırırsan? Məs.: dil modellərində hallüsinasiyaların aşkarlanması',
    ph_ask: 'Sual ver. Məs.: RAG sistemlərində retrieval-ı necə yaxşılaşdırırlar?',
    submit_search: 'Axtar', submit_ask: 'Soruş',
    scope_prefix: 'Sahə:',
    res_search: 'Axtarış nəticələri', res_ask: 'AI cavabı',
    sources_head: 'Mənbələr', relevance: 'uyğunluq', rel_short: 'uyğun',
    grounded_pre: 'Əsaslanır:', grounded_post: 'məqalə',
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
    browse_title: 'Bu həftənin araşdırmaları',
    browse_sub: 'Məqalələri vərəqlə, xoşuna gələni aç və oxu.',
    prev_paper: 'Əvvəlki məqalə', next_paper: 'Növbəti məqalə',
    deck_empty: 'Bu sahədə son bir həftədə məqalə yoxdur.',
    trends_title: 'Araşdırma dinamikası',
    insight_leads: '{f} son həftədə {n} məqalə ilə öndədir ({p}% pay).',
    insight_none: 'Trend üçün hələ kifayət qədər data yoxdur.',
    note_share: 'Korpus {w} həftəni əhatə edir. Həftələrarası faiz dəyişimi {m} tam həftə davamlı yığımdan sonra aktivləşir — indi göstərilsə, backfill pəncərəsinin artefaktı olardı.',
    note_delta: 'Keçən həftə ilə müqayisə.',
    share_of_week: 'pay',
    digest_title: 'Həftəlik icmal',
    digest_sub: 'Hər bazar günü avtomatik hazırlanır.',
    // §16 kitabxana
    nav_library: 'Kitabxanam',
    library_title: 'Kitabxanam',
    library_sub: 'Saxladığın, ulduzladığın və oxuduğun məqalələr.',
    lib_saved: 'Oxu siyahısına əlavə et',
    lib_starred: 'Ulduzla',
    lib_read: 'Oxundu işarələ',
    lib_tab_saved: 'Oxu siyahısı',
    lib_tab_starred: 'Ulduzlular',
    lib_tab_read: 'Oxunanlar',
    lib_added: 'Kitabxanana əlavə olundu',
    lib_login: 'Kitabxana şəxsidir — görmək üçün hesabına daxil ol.',
    lib_empty_saved: 'Oxu siyahın boşdur. Məqalə kartındakı əlfəcin düyməsi ilə sonraya saxla.',
    lib_empty_starred: 'Hələ ulduzladığın məqalə yoxdur. Ulduz — geri qayıtmaq istədiklərin üçündür.',
    lib_empty_read: 'Oxuduğun məqalə hələ qeyd olunmayıb. Bitirdiyin məqaləni işarələ, burada tarixçə yığılsın.',
    digest_empty: 'Hələlik icmal yoxdur. Növbəti icmal bazar günü axşam hazır olur.',
    panel_title: 'Araşdırma paneli',
    areas_title: 'Araşdırma sahələri', area_all: 'Bütün araşdırmalar',
    spot_title: 'Kəşf et', spot_sub: 'Oxumağa dəyər bir şey',
    authors_title: 'Ən aktiv müəlliflər', papers_word: 'məqalə',
    open_panel: 'Paneli aç', close_panel: 'Paneli bağla', refresh: 'Yenilə',
    no_data: 'Data yoxdur',
    lang_of_paper: 'Məqalənin dili', lang_match: 'Sənin interfeys dilində',
    sources_title: 'Mənbələr', sources_word: 'mənbə',
    merged_hint: 'Eyni iş bir neçə mənbədə tapılıb — bir dəfə göstərilir',
    months: ['yan','fev','mar','apr','may','iyn','iyl','avq','sen','okt','noy','dek'],
    groups: { tech: 'Texnologiya', natural: 'Təbiət elmləri', formal: 'Formal elmlər',
      health: 'Tibb və sağlamlıq', social: 'Sosial elmlər' },
    fields: {
      ai: 'Süni intellekt', cv: 'Kompüter görməsi', security: 'Kibertəhlükəsizlik',
      robotics: 'Robototexnika', software: 'Proqram mühəndisliyi', data: 'Data sistemləri',
      networks: 'Şəbəkə və sistemlər', hci: 'İnsan-kompüter', other: 'Digər',
      physics: 'Fizika', astronomy: 'Astronomiya', chemistry: 'Kimya',
      biology: 'Biologiya', earth: 'Yer elmləri', math: 'Riyaziyyat',
      statistics: 'Statistika', medicine: 'Tibb', neuroscience: 'Nevrologiya',
      economics: 'İqtisadiyyat', psychology: 'Psixologiya',
    },
    examples: ['hallüsinasiyaların aşkarlanması', 'federated learning', 'robot təhlükəsizliyi'],
  },

  ru: {
    product_kicker: 'Платформа научного интеллекта',
    corpus_note: 'Этот ответ основан на индексированном корпусе: {n} статей · {src} · {langs}',
    chat_you: 'Вы',
    chat_placeholder: 'Продолжить — задайте вопрос...',
    chat_send: 'Отправить',
    chat_new: 'Новый чат',
    intent_hint: 'Похоже на вопрос типа «{i}».',
    intent_go: 'Открыть',
    intent_pick_papers: 'Выберите статьи из результатов для сравнения.',
    i_COMPARE: 'сравнение',
    i_CONTRADICTION: 'противоречивые данные',
    i_TREND: 'тренд',
    i_EMERGING_TOPIC: 'новые темы',
    i_RESEARCH_GAP: 'пробел в исследованиях',
    i_CROSS_DISCIPLINARY: 'междисциплинарная связь',
    i_EXPLAIN: 'объяснение',
    filter_note: 'Фильтр: {f}',
    f_author: 'автор',
    f_years: 'годы',
    nav_landscape: 'Ландшафт',
    landscape_title: 'Ландшафт исследований',
    landscape_sub: 'Тематические группы, активные авторы и связи между областями — по статьям из библиотеки.',
    landscape_empty: 'Сначала выполните поиск.',
    lx_clusters: 'Кластеры',
    lx_authors: 'Самые активные авторы',
    lx_cross: 'Междисциплинарные связи',
    lx_papers: 'статей',
    trend_classes_title: 'Классификация трендов',
    tc_EMERGING: 'Зарождается',
    tc_GROWING: 'Растёт',
    tc_STABLE: 'Стабильно',
    tc_DECLINING: 'Снижается',
    tc_INSUFFICIENT_DATA: 'Недостаточно данных',
    skip_to_content: 'Перейти к содержимому',
    nav_discover: 'Обзор', nav_search: 'Поиск', nav_browse: 'Листать', nav_trends: 'Тренды', nav_digest: 'Дайджест',
    m_papers: 'Статей', m_chunks: 'Фрагментов', m_updated: 'Обновлено',
    hero_eyebrow: 'Исследуйте науку',
    hero_title: 'Меньше искать. Больше понимать.',
    hero_sub: 'Ищите научную литературу по смыслу или попросите ИИ обобщить, что говорят исследования — каждый ответ опирается на реальные статьи из четырёх академических источников.',
    mode_search: 'Поиск', mode_ask: 'Спросить ИИ',
    mode_hint_search: 'Точные слова не нужны — ищет по смыслу',
    mode_hint_ask: 'ИИ отвечает и под каждым утверждением показывает статью',
    query_label: 'Исследовательский запрос',
    ph_search: 'Что вы исследуете? Напр.: обнаружение галлюцинаций в языковых моделях',
    ph_ask: 'Задайте вопрос. Напр.: как улучшают retrieval в RAG-системах?',
    submit_search: 'Искать', submit_ask: 'Спросить',
    scope_prefix: 'Область:',
    res_search: 'Результаты поиска', res_ask: 'Ответ ИИ',
    sources_head: 'Источники', relevance: 'релевантность', rel_short: 'сходство',
    grounded_pre: 'На основе', grounded_post: 'статей',
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
    browse_title: 'Исследования этой недели',
    browse_sub: 'Листайте статьи и открывайте те, что заинтересовали.',
    prev_paper: 'Предыдущая статья', next_paper: 'Следующая статья',
    deck_empty: 'В этой области за последнюю неделю статей нет.',
    trends_title: 'Динамика исследований',
    insight_leads: '{f} лидирует за последнюю неделю: {n} статей ({p}%).',
    insight_none: 'Пока недостаточно данных для тренда.',
    note_share: 'Корпус охватывает {w} нед. Процентное изменение между неделями включится после {m} полных недель непрерывного сбора — сейчас это был бы артефакт окна backfill.',
    note_delta: 'Сравнение с предыдущей неделей.',
    share_of_week: 'доля',
    digest_title: 'Еженедельный дайджест',
    digest_sub: 'Готовится автоматически каждое воскресенье.',
    // §16 kitabxana
    nav_library: 'Библиотека',
    library_title: 'Моя библиотека',
    library_sub: 'Сохранённые, отмеченные звездой и прочитанные статьи.',
    lib_saved: 'В список чтения',
    lib_starred: 'В избранное',
    lib_read: 'Отметить прочитанным',
    lib_tab_saved: 'Список чтения',
    lib_tab_starred: 'Избранное',
    lib_tab_read: 'Прочитанные',
    lib_added: 'Добавлено в библиотеку',
    lib_login: 'Библиотека личная — войдите в аккаунт, чтобы её увидеть.',
    lib_empty_saved: 'Список чтения пуст. Сохраните статью закладкой на карточке.',
    lib_empty_starred: 'Пока нет избранных статей. Звезда — для тех, к которым вы вернётесь.',
    lib_empty_read: 'Прочитанные статьи ещё не отмечены. Отмечайте — здесь соберётся история.',
    digest_empty: 'Дайджеста пока нет. Следующий появится в воскресенье вечером.',
    panel_title: 'Панель исследований',
    areas_title: 'Области исследований', area_all: 'Все области',
    spot_title: 'Обзор', spot_sub: 'Стоит прочитать',
    authors_title: 'Самые активные авторы', papers_word: 'статей',
    open_panel: 'Открыть панель', close_panel: 'Закрыть панель', refresh: 'Обновить',
    no_data: 'Нет данных',
    lang_of_paper: 'Язык статьи', lang_match: 'На языке вашего интерфейса',
    sources_title: 'Источники', sources_word: 'источн.',
    merged_hint: 'Одна и та же работа найдена в нескольких источниках — показана один раз',
    months: ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'],
    groups: { tech: 'Технологии', natural: 'Естественные науки', formal: 'Формальные науки',
      health: 'Медицина и здоровье', social: 'Социальные науки' },
    fields: {
      ai: 'Искусственный интеллект', cv: 'Компьютерное зрение', security: 'Кибербезопасность',
      robotics: 'Робототехника', software: 'Программная инженерия', data: 'Системы данных',
      networks: 'Сети и системы', hci: 'Человек-компьютер', other: 'Другое',
      physics: 'Физика', astronomy: 'Астрономия', chemistry: 'Химия',
      biology: 'Биология', earth: 'Науки о Земле', math: 'Математика',
      statistics: 'Статистика', medicine: 'Медицина', neuroscience: 'Нейронауки',
      economics: 'Экономика', psychology: 'Психология',
    },
    examples: ['обнаружение галлюцинаций', 'federated learning', 'безопасность роботов'],
  },

  en: {
    product_kicker: 'Scientific Intelligence Platform',
    corpus_note: 'This answer is based on the indexed corpus: {n} papers · {src} · {langs}',
    chat_you: 'You',
    chat_placeholder: 'Keep going — ask a follow-up...',
    chat_send: 'Send',
    chat_new: 'New chat',
    intent_hint: 'This looks like a “{i}” question.',
    intent_go: 'Open',
    i_COMPARE: 'comparison',
    i_CONTRADICTION: 'conflicting evidence',
    i_TREND: 'trend',
    i_EMERGING_TOPIC: 'emerging topics',
    i_RESEARCH_GAP: 'research gap',
    i_CROSS_DISCIPLINARY: 'cross-disciplinary link',
    i_EXPLAIN: 'explanation',
    filter_note: 'Filter: {f}',
    f_author: 'author',
    f_years: 'years',
    nav_landscape: 'Landscape',
    landscape_title: 'Research landscape',
    landscape_sub: 'Topic groups, active authors and links between fields — drawn from the papers in the library.',
    landscape_empty: 'Run a search first to build the landscape.',
    lx_clusters: 'Clusters',
    lx_authors: 'Most active authors',
    lx_cross: 'Cross-disciplinary links',
    lx_papers: 'papers',
    trend_classes_title: 'Trend classification',
    tc_EMERGING: 'Emerging',
    tc_GROWING: 'Growing',
    tc_STABLE: 'Stable',
    tc_DECLINING: 'Declining',
    tc_INSUFFICIENT_DATA: 'Insufficient data',
    skip_to_content: 'Skip to content',
    nav_discover: 'Discover', nav_search: 'Search', nav_browse: 'Browse', nav_trends: 'Trends', nav_digest: 'Digest',
    m_papers: 'Papers', m_chunks: 'Chunks', m_updated: 'Updated',
    hero_eyebrow: 'Discover research',
    hero_title: 'Search less. Understand more.',
    hero_sub: 'Search scientific literature by meaning, or ask AI to synthesise what the research says — every answer grounded in real papers from four academic sources.',
    mode_search: 'Search', mode_ask: 'Ask AI',
    mode_hint_search: 'No exact wording needed — it searches by meaning',
    mode_hint_ask: 'AI answers, and every claim shows the paper behind it',
    query_label: 'Research query',
    ph_search: 'What are you researching? E.g. hallucination detection in language models',
    ph_ask: 'Ask a question. E.g. how is retrieval improved in RAG systems?',
    submit_search: 'Search', submit_ask: 'Ask',
    scope_prefix: 'Area:',
    res_search: 'Search results', res_ask: 'AI answer',
    sources_head: 'Sources', relevance: 'relevance', rel_short: 'match',
    grounded_pre: 'Grounded in', grounded_post: 'papers',
    intent_pick_papers: 'Pick papers from the results to compare.',
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
    browse_title: 'This week in research',
    browse_sub: 'Flip through recent papers and open the ones worth your time.',
    prev_paper: 'Previous paper', next_paper: 'Next paper',
    deck_empty: 'No papers in this area over the past week.',
    trends_title: 'Research momentum',
    insight_leads: '{f} leads the last week with {n} papers ({p}% share).',
    insight_none: 'Not enough data yet to describe a trend.',
    note_share: 'Corpus spans {w} week(s). Week-over-week percentages unlock after {m} full weeks of continuous ingestion — shown now they would be an artefact of the backfill window.',
    note_delta: 'Compared with the previous week.',
    share_of_week: 'share',
    digest_title: 'Weekly digest',
    digest_sub: 'Put together automatically every Sunday.',
    // §16 kitabxana
    nav_library: 'Library',
    library_title: 'My library',
    library_sub: 'Papers you saved, starred and read.',
    lib_saved: 'Add to reading list',
    lib_starred: 'Star',
    lib_read: 'Mark as read',
    lib_tab_saved: 'Reading list',
    lib_tab_starred: 'Starred',
    lib_tab_read: 'Read',
    lib_added: 'Added to your library',
    lib_login: 'Your library is private — sign in to see it.',
    lib_empty_saved: 'Your reading list is empty. Use the bookmark on a paper card to save it for later.',
    lib_empty_starred: 'Nothing starred yet. Stars are for the papers you want to come back to.',
    lib_empty_read: 'No papers marked read yet. Mark one when you finish it and your history builds up here.',
    digest_empty: 'No digest yet. The next one arrives Sunday evening.',
    panel_title: 'Research panel',
    areas_title: 'Research areas', area_all: 'All research',
    spot_title: 'Discover', spot_sub: 'Something worth reading',
    authors_title: 'Most active authors', papers_word: 'papers',
    open_panel: 'Open panel', close_panel: 'Close panel', refresh: 'Refresh',
    no_data: 'No data',
    lang_of_paper: 'Language of the paper', lang_match: 'In your interface language',
    sources_title: 'Sources', sources_word: 'sources',
    merged_hint: 'The same work was found in several sources — shown once',
    months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
    groups: { tech: 'Technology', natural: 'Natural sciences', formal: 'Formal sciences',
      health: 'Medicine & health', social: 'Social sciences' },
    fields: {
      ai: 'Artificial intelligence', cv: 'Computer vision', security: 'Cybersecurity',
      robotics: 'Robotics', software: 'Software engineering', data: 'Data systems',
      networks: 'Networks & systems', hci: 'Human-computer', other: 'Other',
      physics: 'Physics', astronomy: 'Astronomy', chemistry: 'Chemistry',
      biology: 'Biology', earth: 'Earth sciences', math: 'Mathematics',
      statistics: 'Statistics', medicine: 'Medicine', neuroscience: 'Neuroscience',
      economics: 'Economics', psychology: 'Psychology',
    },
    examples: ['hallucination detection', 'federated learning', 'robot safety'],
  },
};

const GLYPH = {
  '': '◉', ai: '✦', cv: '◈', security: '⌁', robotics: '⬡',
  software: '⌘', data: '▤', networks: '⋔', hci: '◇',
  physics: '⚛', astronomy: '✧', chemistry: '⬢', biology: '❋', earth: '◍',
  math: '∑', statistics: '⌗', medicine: '✚', neuroscience: '❂',
  economics: '⌸', psychology: '☉', other: '·',
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
let fieldToGroup = {};    // 'physics' -> 'natural'
let totalPapers = null;   // distinct total; field counts overlap via cross-listing
let trendChart = null;

const t = (k) => I18N[LANG][k] ?? I18N.en[k] ?? k;
const fieldName = (k) => I18N[LANG].fields[k] ?? I18N.en.fields[k] ?? k;
const groupName = (k) => (I18N[LANG].groups || {})[k] ?? (I18N.en.groups || {})[k] ?? fieldName(k);
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
    /* Gating cavabları BİR yerdə tutulur. Hər çağırış yerində 401/402 yoxlamaq
       lazım gəlsəydi, yeni endpoint əlavə edən adam onu unudardı və istifadəçi
       «xəta baş verdi» görərdi — nə giriş təklifi, nə yüksəltmə.
       auth.js bu hadisələri dinləyir və uyğun pəncərəni açır. */
    if (resp.status === 401) {
      document.dispatchEvent(new CustomEvent('pm:auth-required', { detail: { path } }));
    } else if (resp.status === 402) {
      document.dispatchEvent(new CustomEvent('pm:upgrade-required', { detail }));
    }
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
    data.forEach((f) => {
      (f.categories || []).forEach((c) => { catToField[c] = f.key; });
      if (f.group) fieldToGroup[f.key] = f.group;
    });
    renderAreas();
  } catch (e) { toast(errTitle(e)); }
}

function areaButton(key, name, count) {
  const on = FIELD === key;
  return `
    <button type="button" class="area ${on ? 'on' : ''}" data-field="${esc(key)}"
            role="option" aria-selected="${on}">
      <span class="glyph" aria-hidden="true">${GLYPH[key] || '·'}</span>
      <span class="nm">${esc(name)}</span>
      <span class="ct">${count == null ? '' : num(count)}</span>
    </button>`;
}

function renderAreas() {
  /* Sahə sayları üst-üstə düşür (məqalə bir neçə sahəyə aid ola bilər), ona görə
     «bütün araşdırmalar» sayı /api/analytics/summary-dən gələn distinct totaldır. */
  let html = areaButton('', t('area_all'), totalPapers);

  /* Fənn qrupları üzrə düzülüş. Boş sahələr göstərilmir — 20 sahədən yalnız
     korpusda mövcud olanlar görünsün deyə. */
  const byGroup = {};
  fields.forEach((f) => {
    if (!f.count) return;
    (byGroup[f.group || 'tech'] ||= []).push(f);
  });

  const order = ['tech', 'natural', 'formal', 'health', 'social'];
  const groups = t('groups') || {};
  order.filter((g) => byGroup[g]).forEach((g) => {
    html += `<div class="area-group">${esc(groups[g] || g)}</div>`;
    byGroup[g].sort((a, b) => b.count - a.count)
      .forEach((f) => { html += areaButton(f.key, fieldName(f.key), f.count); });
  });

  $('#areas').innerHTML = html;
}

function setField(k) {
  FIELD = k;
  localStorage.setItem('pm_field', k);
  renderAreas();
  renderScope();
  loadDeck();          // vərəqlənən dəst seçilmiş sahəyə uyğunlaşır
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

function skeleton(kind, keepHistory = false) {
  const r = $('#results');
  // Davam edən söhbətdə əvvəlki növbələr silinmir — ekran boşalsa,
  // istifadəçi kontekstin itdiyini düşünür.
  if (keepHistory) {
    const old = r.querySelector('.chat-history');
    const prev = old ? old.outerHTML : '';
    r.setAttribute('aria-busy', 'true');
    r.innerHTML = prev + `<div class="loading-note"><span class="spinner"></span>${t('loading_ask')}</div>`;
    return;
  }
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

  /* §6 + §19: sorğunun niyyəti tapılıbsa, uyğun imkan TƏKLİF olunur —
     istifadəçi ayrıca menyu axtarmır, amma əsas axın da dəyişmir.
     Süzgəclər (müəllif, il) də görünür ki, nəticənin niyə daraldığı aydın olsun. */
  const P = data.plan || {};
  const bits = [];
  if (P.authors && P.authors.length) bits.push(`${t('f_author')}: ${P.authors.join(', ')}`);
  if (P.year_from) bits.push(`${t('f_years')}: ${P.year_from}${P.year_to && P.year_to !== P.year_from ? '–' + P.year_to : ''}`);
  const planBar = (P.suggested_endpoint || bits.length) ? `
    <div class="plan-bar">
      ${P.suggested_endpoint ? `<span class="plan-intent">${esc(
          t('intent_hint').replace('{i}', t('i_' + P.intent) || P.intent))}</span>
        <button type="button" class="plan-go" data-intent="${esc(P.intent)}">${t('intent_go')}</button>` : ''}
      ${bits.length ? `<span class="plan-filters">${esc(t('filter_note').replace('{f}', bits.join(' · ')))}</span>` : ''}
    </div>` : '';

  // §11: axtarış nəticəsi hazır olan kimi landşaft da qurulur — istifadəçi
  // «hansı məqalələr var» sualından «bu sahə necə qurulub» sualına keçə bilsin.
  loadLandscape(q);

  const head = planBar + `
    <div class="res-head">
      <h2>${t('res_search')}</h2>
      <div class="res-meta">
        <span class="badge">${data.hits.length} · ${esc(t('grounded_post'))}</span>
      </div>
    </div>
    ${data.query_en ? `<p class="translated">${t('translated_as')} <code>${esc(data.query_en)}</code></p>` : ''}`;

  r.innerHTML = head + data.hits.map((h) => {
    const p = h.paper;
    const authors = p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '');
    return `
      <article class="paper" data-paper-id="${p.id}">
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
          ${paperActions(p)}
        </div>
      </article>`;
  }).join('');
}

/* Söhbət tarixçəsi. Backend son 6 növbəni işlədir, biz 10 saxlayırıq ki,
   ekranda görünən dialoq kəsilməsin. Sahə və ya dil dəyişəndə sıfırlanır —
   yeni kontekstdə köhnə növbələr yanıldıcı olur. */
let CHAT = [];

function resetChat() { CHAT = []; }

/* Söhbətin davamı: cavabın altındakı sahə. Əsas axtarış qutusu toxunulmur —
   ora yeni sorğu üçündür, bura isə eyni mövzunu davam etdirmək üçün. */
document.addEventListener('submit', (e) => {
  if (e.target && e.target.id === 'chat-next') {
    e.preventDefault();
    const input = document.querySelector('#chat-more');
    const text = (input?.value || '').trim();
    if (text.length < 1) return;
    input.value = '';
    runAsk(text).catch((err) => showError(err));
  }
});

document.addEventListener('click', (e) => {
  if (e.target && e.target.id === 'chat-reset') {
    resetChat();
    $('#results').innerHTML = '';
    $('#q')?.focus();
  }
});

async function runAsk(q) {
  const isFollowUp = CHAT.length > 0;
  skeleton('ask', isFollowUp);
  const { data } = await api('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: q, top_k: 5, field: FIELD || null,
      history: CHAT.slice(-10),
    }),
  });
  CHAT.push({ role: 'user', content: q });
  CHAT.push({ role: 'assistant', content: (data.answer || '').slice(0, 2000) });

  /* Başlıqdakı kredit rəqəmi cavabdan sonra köhnə qalmasın. Ayrıca /api/auth/me
     sorğusu atmırıq — cavabın özü qalığı gətirir. */
  if (typeof data.credits_left === 'number') {
    document.dispatchEvent(new CustomEvent('pm:credits-changed', {
      detail: { left: data.credits_left },
    }));
  }

  const r = $('#results');
  r.setAttribute('aria-busy', 'false');

  // İstinadlar nömrəlidir: [1], [2]... Nömrə mənbə siyahısındakı sıra ilə eynidir,
  // ona görə etiket birbaşa həmin mənbəyə keçid olur.
  // (Əvvəl DOI/arXiv ID işlədilirdi — model uzun DOI-nu səhvsiz köçürə bilmirdi.)
  const answer = esc(data.answer).replace(
    /\[(\d{1,2})\]/g,
    (m, n) => (Number(n) >= 1 && Number(n) <= data.sources.length
      ? `<a class="cite" href="#src-${n}">[${n}]</a>`
      : m)
  );

  /* Əvvəlki növbələr — sonuncu cütdən başqası. Söhbətin davam etdiyi
     görünməlidir, yoxsa istifadəçi hər dəfə sıfırdan başladığını düşünür. */
  const past = CHAT.slice(0, -2).map((turn) => `
    <div class="chat-turn ${turn.role}">
      <span class="chat-role">${turn.role === 'user' ? t('chat_you') : 'PaperMind'}</span>
      <div>${esc(turn.content)}</div>
    </div>`).join('');

  r.innerHTML = `
    ${past ? `<div class="chat-history">${past}</div>` : ''}
    <div class="answer-panel">
      <div class="chat-question">${esc(q)}</div>
      <div class="answer-head">
        <h2><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.4l1.3 3.3L11.6 6 8.3 7.3 7 10.6 5.7 7.3 2.4 6l3.3-1.3z" fill="currentColor"/></svg>${t('res_ask')}</h2>
        <div class="res-meta">
          <span class="badge ai">${t('grounded_pre')} ${data.sources.length} ${t('grounded_post')}</span>
        </div>
      </div>
      ${data.query_en ? `<p class="translated" style="margin-bottom:14px">${t('translated_as')} <code>${esc(data.query_en)}</code></p>` : ''}
      <div class="answer-body">${answer}</div>
      <form class="chat-next" id="chat-next">
        <input type="text" id="chat-more" autocomplete="off" maxlength="500"
               data-i18n-ph="chat_placeholder">
        <button type="submit">${t('chat_send')}</button>
        <button type="button" id="chat-reset" class="chat-reset">${t('chat_new')}</button>
      </form>
      ${data.corpus ? `<p class="corpus-note">${esc(
        t('corpus_note')
          .replace('{n}', nf().format(data.corpus.papers))
          .replace('{src}', data.corpus.sources.join(' · '))
          .replace('{langs}', data.corpus.languages.join('/'))
      )}</p>` : ''}
      ${data.sources.length ? `
        <div class="sources-head">${t('sources_head')}</div>
        <div class="sources">
          ${data.sources.map((s, i) => `
            <a class="source" id="src-${i + 1}" href="${esc(s.pdf_url || '#')}" target="_blank" rel="noopener">
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
  const map = {};                       // qrup -> {week: count}
  rows.forEach((r) => {
    /* Backend artıq FƏNN QRUPU qaytarır (distinct məqalə sayı ilə). 19 sahəni
       ayrıca çəkmək olmaz — palitrada 5 təsdiqlənmiş rəng var, qalanı «digər»ə
       yığılsaydı o, qrafikə hakim kəsilərdi. */
    (map[r.category] ||= {})[r.week] = (map[r.category][r.week] || 0) + r.count;
  });
  return { weeks, map };
}

/* ---------------------------------------------------------------- Phase 4
   Trend təsnifatı (§12) və tədqiqat landşaftı (§11).
   Hər ikisi serverdə hesablanır; burada yalnız göstərilir. Xüsusilə vacib:
   təsnifatın SƏBƏBİ də göstərilir — «artır» sözü tək başına heç nə demir. */

const TC_TONE = {
  EMERGING: 'up', GROWING: 'up', STABLE: 'flat',
  DECLINING: 'down', INSUFFICIENT_DATA: 'muted',
};

/* Niyyət təklifi: düyməyə basanda uyğun imkana aparır.
   Landşaft/boşluq/fənlərarası panel içindədir; müqayisə və ziddiyyət isə
   məqalə seçimi tələb edir, ona görə hələlik izah göstərilir. */
document.addEventListener('click', (e) => {
  const b = e.target.closest('.plan-go');
  if (!b) return;
  const intent = b.dataset.intent;
  if (intent === 'TREND' || intent === 'EMERGING_TOPIC') {
    document.querySelector('#trends')?.scrollIntoView({ behavior: 'smooth' });
  } else if (intent === 'CROSS_DISCIPLINARY' || intent === 'RESEARCH_GAP') {
    document.querySelector('#landscape')?.scrollIntoView({ behavior: 'smooth' });
  } else if (intent === 'EXPLAIN') {
    setMode('ask');
    $('#query-form').requestSubmit();
  } else {
    toast(t('intent_pick_papers'));
  }
});

async function loadTrendClasses() {
  const box = $('#trend-classes');
  if (!box) return;
  try {
    const { data } = await api('/api/analytics/trend-classes?weeks=16');
    const rows = (data.classes || []).filter((c) => c.classification !== 'INSUFFICIENT_DATA');
    if (!rows.length) { box.innerHTML = ''; return; }
    box.innerHTML = `
      <div class="tc-head">${t('trend_classes_title')}</div>
      ${rows.map((c) => `
        <div class="tc-row tc-${TC_TONE[c.classification] || 'flat'}">
          <span class="tc-badge">${esc(t('tc_' + c.classification))}</span>
          <b>${esc(groupName(c.label))}</b>
          <span class="tc-why">${esc(c.reason)}</span>
        </div>`).join('')}`;
  } catch (e) { box.innerHTML = ''; }
}

async function loadLandscape(query) {
  const panel = $('#landscape');
  const body = $('#landscape-body');
  if (!panel || !body || !query) return;
  panel.hidden = false;
  try {
    const [lxRes, crossRes] = await Promise.all([
      api('/api/landscape?q=' + encodeURIComponent(query)),
      api('/api/cross-disciplinary?q=' + encodeURIComponent(query)),
    ]);
    const lx = lxRes.data, cross = crossRes.data;
    const L = lx.landscape || {};
    const scope = $('#landscape-scope');
    if (scope) {
      scope.hidden = false;
      scope.textContent = `${nf().format(L.total || 0)} ${t('lx_papers')}`;
    }
    const clusters = (L.clusters || []).map((c) => `
      <div class="lx-cluster">
        <div class="lx-bar"><i style="width:${Math.round((c.share || 0) * 100)}%"></i></div>
        <b>${esc(fieldName(c.key))}</b>
        <span>${c.count} · ${Math.round((c.share || 0) * 100)}%</span>
      </div>`).join('');
    const authors = (L.authors || []).map((a) =>
      `<li><span>${esc(a.name)}</span><b>${a.count}</b></li>`).join('');
    const links = (cross.connections || []).slice(0, 6).map((c) =>
      `<li><span>${esc(fieldName(c.fields[0]))} ↔ ${esc(fieldName(c.fields[1]))}</span>
         <b>${c.papers}</b></li>`).join('');

    body.innerHTML = `
      <div class="lx-grid">
        <section><h3>${t('lx_clusters')}</h3>${clusters || '<p class="muted">—</p>'}</section>
        <section><h3>${t('lx_authors')}</h3><ol class="lx-list">${authors || ''}</ol></section>
        <section><h3>${t('lx_cross')}</h3><ol class="lx-list">${links || '<li class="muted">—</li>'}</ol></section>
      </div>
      ${lx.corpus ? `<p class="corpus-note">${esc(
        t('corpus_note')
          .replace('{n}', nf().format(lx.corpus.papers))
          .replace('{src}', lx.corpus.sources.join(' · '))
          .replace('{langs}', lx.corpus.languages.join('/'))
      )}</p>` : ''}`;
  } catch (e) {
    body.innerHTML = `<p class="muted">${esc(errTitle(e))}</p>`;
  }
}

async function loadTrends() {
  const note = $('#trend-insight');
  note.textContent = t('loading_trends');
  try {
    const { data } = await api('/api/analytics/trends?weeks=8');

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

    /* Backend fənn qrupu qaytarır və onlar 5-dir — palitradakı təsdiqlənmiş
       rəng sayı ilə eyni. Ona görə «top-N + digər» yığımına ehtiyac yoxdur:
       hər qrup öz seriyasını alır. (Əvvəlki versiyada 5-ci qrup mövcud olmayan
       'other' seriyasına yönləndirilirdi və qrafik çökürdü.) */
    const series = totals.slice(0, SERIES.length).map(([k]) => k);

    const stacks = {};
    series.forEach((s) => (stacks[s] = weeks.map(() => 0)));
    Object.entries(map).forEach(([f, byWeek]) => {
      if (!stacks[f]) return;          // palitradan kənarda qalan qrup (indi olmur)
      weeks.forEach((w, i) => { stacks[f][i] += byWeek[w] || 0; });
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
        .replace('{f}', groupName(f)).replace('{n}', num(n))
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
  const prev = weeks[weeks.length - 2];
  const last = weeks[weeks.length - 1];
  const prevTotal = prev
    ? Object.values(map).reduce((sum, bw) => sum + (bw[prev] || 0), 0) : 0;
  const useDelta = weeks.length >= MIN_WEEKS_FOR_DELTA && prevTotal >= MIN_VOLUME_FOR_DELTA;

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
        <span class="dn"><i style="background:${colour}"></i><span>${esc(groupName(f))}</span></span>
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

/* ------------------------------------------------------------------ deck */

let deck = [], deckIdx = 0;

async function loadDeck() {
  const box = $('#deck');
  try {
    const fp = FIELD ? `&field=${encodeURIComponent(FIELD)}` : '';
    const { data } = await api(`/api/papers?days=7&page_size=15${fp}`);
    deck = data.items || [];
    deckIdx = 0;
    if (!deck.length) {
      box.innerHTML = `<p class="muted">${t('deck_empty')}</p>`;
      $('#deck-dots').innerHTML = '';
      $('#deck-count').textContent = '';
      return;
    }
    renderDeck(1);
  } catch (e) {
    box.innerHTML = `<p class="muted">${esc(errTitle(e))}</p>`;
  }
}

function renderDeck(dir = 1) {
  const p = deck[deckIdx];
  if (!p) return;
  const authors = p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '');
  const field = (p.field_keys || [])[0];

  $('#deck').innerHTML = `
    <article class="deck-card" data-paper-id="${p.id}" style="--from:${dir > 0 ? '14px' : '-14px'}">
      <div class="deck-meta">
        ${field ? `<span class="deck-field">${esc(fieldName(field))}</span>` : ''}
        <span>${p.published_at ? dmy(p.published_at) : ''}</span>
        <span class="sep">·</span><span class="aid">${esc(paperRef(p))}</span>
        ${langChip(p)}${sourceChips(p)}
      </div>
      <a class="deck-title" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">${esc(p.title)}</a>
      ${authors ? `<div class="deck-meta">${esc(authors)}</div>` : ''}
      <p class="deck-abs">${esc(p.abstract)}</p>
      ${paperActions(p)}
    </article>`;

  paintLibrary($('#deck'));
  $('#deck-count').textContent = `${deckIdx + 1} / ${deck.length}`;
  $('#deck-dots').innerHTML = deck.map((_, i) => `<i class="${i === deckIdx ? 'on' : ''}"></i>`).join('');
}

function flip(step) {
  if (deck.length < 2) return;
  deckIdx = (deckIdx + step + deck.length) % deck.length;   // dövri: sonuncudan birinciyə
  renderDeck(step);
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

/* ================================================================ kitabxana

   Oxu siyahısı, ulduz və oxundu tarixçəsi.

   Vəziyyət BİR yerdə (LIB) saxlanılır, çünki eyni məqalə eyni anda üç yerdə
   görünə bilər: axtarış nəticəsində, vərəqləmə dəstində və kitabxana
   siyahısında. Ayrı-ayrı saxlansaydı, ulduza bir yerdə basanda qalan ikisi
   köhnə vəziyyətdə qalardı və istifadəçi eyni məqaləni həm ulduzlu, həm
   ulduzsuz görərdi.
*/

const LIB = { saved: new Set(), starred: new Set(), read: new Set() };

const LIB_ICON = {
  saved: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 1.6h7v10.8L7 9.9l-3.5 2.5z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>',
  starred: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.3l1.75 3.85 4.05.45-3.05 2.8.85 4.05L7 10.4l-3.6 2.05.85-4.05L1.2 5.6l4.05-.45z" fill="none" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/></svg>',
  read: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M2.6 7.4l2.9 2.9 5.9-6.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

/* Server sahələri fərqli adlanır: `read` bayraqdır, bazada `read_at` vaxtdır.
   Xəritə burada bir yerdədir ki, hər çağırışda yadda saxlamaq lazım olmasın. */
const LIB_FIELDS = ['saved', 'starred', 'read'];

async function loadLibraryState() {
  try {
    const { data } = await api('/api/library/state');
    LIB_FIELDS.forEach((k) => { LIB[k] = new Set(data[k] || []); });
  } catch {
    LIB_FIELDS.forEach((k) => LIB[k].clear());
  }
  paintLibrary();
}

function clearLibraryState() {
  LIB_FIELDS.forEach((k) => LIB[k].clear());
  libRows = [];
  const body = $('#library-body');
  if (body) body.innerHTML = `<p class="state-note">${esc(t('lib_login'))}</p>`;
  paintLibrary();
}

/* Hər iki kart növü (axtarış nəticəsi və vərəqləmə dəsti) eyni düymələri
   göstərir. Əvvəl bu blok iki yerdə hərfbəhərf təkrarlanırdı — üçüncü düymə
   əlavə edəndə birini unutmaq qaçılmaz idi. */
function paperActions(p) {
  const toggle = (field) => `
    <button type="button" class="act lib lib-${field}" data-lib="${field}" data-pid="${p.id}"
            aria-pressed="false" aria-label="${esc(t('lib_' + field))}" title="${esc(t('lib_' + field))}">
      ${LIB_ICON[field]}
    </button>`;

  return `
    <div class="paper-actions">
      <a class="act" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">
        <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M5 2H2.5v9.5H12V9M8 2h4v4M12 2 6.5 7.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
        ${t('act_read')}</a>
      <button type="button" class="act ai" data-ask="${esc(p.title)}">
        <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.4l1.3 3.3L11.6 6 8.3 7.3 7 10.6 5.7 7.3 2.4 6l3.3-1.3z" fill="currentColor"/></svg>
        ${t('act_ask')}</button>
      <span class="act-gap"></span>
      ${toggle('saved')}${toggle('starred')}${toggle('read')}
    </div>`;
}

/* Yalnız görünüşü yeniləyir — heç nə göndərmir. Hər render-dən və hər
   vəziyyət dəyişikliyindən sonra çağırılır. */
function paintLibrary(root = document) {
  root.querySelectorAll('[data-lib][data-pid]').forEach((b) => {
    const on = LIB[b.dataset.lib].has(Number(b.dataset.pid));
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  root.querySelectorAll('[data-paper-id]').forEach((card) => {
    card.classList.toggle('is-read', LIB.read.has(Number(card.dataset.paperId)));
  });
}

/* Serverin qaydaları burada TƏKRARLANIR (ulduz siyahıya salır, siyahıdan
   çıxmaq ulduzu götürür). Bu, şüurlu təkrardır: düymə dərhal reaksiya
   verməlidir, şəbəkəni gözləməməlidir. Serverin cavabı gələndə vəziyyət
   onunla əvəzlənir — yəni son söz həmişə serverindir, bu isə təxmindir. */
function guessLocal(id, field, on) {
  if (on) {
    LIB[field].add(id);
    if (field === 'starred') LIB.saved.add(id);
  } else {
    LIB[field].delete(id);
    if (field === 'saved') LIB.starred.delete(id);
  }
}

function applyServer(id, data) {
  LIB_FIELDS.forEach((k) => (data[k] ? LIB[k].add(id) : LIB[k].delete(id)));
}

async function toggleLibrary(id, field) {
  const before = LIB_FIELDS.map((k) => LIB[k].has(id));
  const next = !LIB[field].has(id);

  guessLocal(id, field, next);
  paintLibrary();

  try {
    const { data } = await api(`/api/library/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: next }),
    });
    applyServer(id, data);
    if (next && field !== 'read') toast(t('lib_added'));
  } catch (e) {
    // Təxmin səhv çıxdı — dəqiq əvvəlki vəziyyətə qaytarırıq.
    LIB_FIELDS.forEach((k, i) => (before[i] ? LIB[k].add(id) : LIB[k].delete(id)));
    // 401/402 artıq öz pəncərəsini açır (api() hadisə atır) — üstünə
    // «xəta» bildirişi qoysaq, istifadəçi eyni şeyi iki dəfə oxuyar.
    if (e.status !== 401 && e.status !== 402) toast(errTitle(e));
  }
  paintLibrary();
  if (libRows.length) {
    libRows = libRows.filter((r) => LIB[libView].has(r.paper.id));
    renderLibrary();
  }
}

/* ---------------------------------------------------------- kitabxana görünüşü

   Kitabxana uzun səhifənin ortasında sürüşülən blok DEYİL — ayrıca səhifə
   kimi açılır. Marşrut hash-dir (`#library`), ayrıca URL deyil: belədə
   brauzerin geri düyməsi və keçidin paylaşılması pulsuz gəlir, server
   tərəfində isə heç nə dəyişmir (SPA marşrutlaması üçün Caddy-də ayrıca
   qayda yazmaq lazım gəlmir).

   Görünüşü BODY-dəki sinif idarə edir, JS ayrı-ayrı bölmələri gizlətmir:
   yeni bölmə əlavə edən adam JS siyahısını yeniləməyi unudardı, CSS isə
   `body:not(.view-library) #library` şəklində özü tutur. */

const LIB_ROUTE = '#library';

function routeView() {
  const on = location.hash === LIB_ROUTE;
  document.body.classList.toggle('view-library', on);

  // Bölmə görünüşdən çıxanda IntersectionObserver işləmir, ona görə
  // naviqasiya işığı burada əl ilə qoyulur.
  $$('.nav a, .side-nav a').forEach((a) => {
    if (a.getAttribute('href') === LIB_ROUTE) a.classList.toggle('on', on);
    else if (on) a.classList.remove('on');
  });

  if (on) {
    window.scrollTo({ top: 0, behavior: 'auto' });
    loadLibrary();
  }
}

/* ---------------------------------------------------------- kitabxana bölməsi */

let libView = 'saved';
let libRows = [];

async function loadLibrary(view = libView) {
  libView = view;
  const body = $('#library-body');
  $$('#library-tabs button').forEach((b) => {
    const on = b.dataset.view === view;
    b.classList.toggle('on', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  body.innerHTML = `<div class="state"><span class="spinner"></span></div>`;
  try {
    const { data } = await api(`/api/library?view=${view}`);
    libRows = data;
    renderLibrary();
  } catch (e) {
    libRows = [];
    body.innerHTML = e.status === 401
      ? `<p class="state-note">${esc(t('lib_login'))}</p>`
      : `<p class="state-note">${esc(errTitle(e))}</p>`;
  }
}

function renderLibrary() {
  const body = $('#library-body');
  if (!body) return;
  if (!libRows.length) {
    body.innerHTML = `<p class="state-note">${esc(t('lib_empty_' + libView))}</p>`;
    return;
  }
  body.innerHTML = libRows.map((row) => {
    const p = row.paper;
    const when = libView === 'read' && row.read_at ? row.read_at : row.created_at;
    return `
      <article class="paper lib-row" data-paper-id="${p.id}">
        <div>
          <div class="paper-meta">
            <span class="field">${esc(catName(p.primary_category))}</span>
            <span class="sep">·</span><span>${when ? dmy(when) : ''}</span>
            <span class="sep">·</span><span class="aid">${esc(paperRef(p))}</span>
          </div>
          <a class="paper-title" href="${esc(p.pdf_url || '#')}" target="_blank" rel="noopener">${esc(p.title)}</a>
          <p class="paper-abs">${esc(p.abstract)}</p>
          ${paperActions(p)}
        </div>
      </article>`;
  }).join('');
  paintLibrary(body);
}

/* ------------------------------------------------------------------ chrome */

/* Başlıqdakı naviqasiya ≤960px-də gizlənir və telefonda heç bir bölməyə
   keçid qalmır — istifadəçi kitabxanaya çatmaq üçün 1400px sürüşməli olur.
   Siyahını sürüşən panelə ƏLLƏ ikinci dəfə yazmaq olardı, amma onda yeni
   bölmə əlavə edən adam iki yerdən birini unudardı və panel yalan danışardı.
   Ona görə eyni DOM-dan kopyalanır: mənbə birdir. */
function mirrorNavIntoDrawer(setDrawer) {
  const side = $('#side'), nav = $('#nav'), head = $('.side-head');
  if (!side || !nav || !head || side.querySelector('.side-nav')) return;

  const box = document.createElement('nav');
  box.className = 'side-nav';
  box.setAttribute('aria-label', 'Sections');
  box.innerHTML = nav.innerHTML;
  head.insertAdjacentElement('afterend', box);

  // Keçidə basanda panel bağlanmalıdır, yoxsa hədəf bölmə panelin altında qalır.
  box.addEventListener('click', (e) => { if (e.target.closest('a')) setDrawer(false); });
}

function initNav() {
  // Hər iki nüsxə eyni anda işıqlanır — hansının göründüyü ekran enindən asılıdır.
  const links = $$('.nav a, .side-nav a');
  const secs = [...new Set(links.map((a) => a.getAttribute('href')))].map((h) => $(h));
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
  loadSpotlight();
  loadDeck();
}

document.addEventListener('DOMContentLoaded', () => {
  applyI18n();
  const setDrawer = initDrawer();
  mirrorNavIntoDrawer(setDrawer);
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
  /* Kitabxana vəziyyəti YALNIZ kimlik bilinəndən sonra çəkilir.
     Səhifə açılan kimi çağırsaydıq, girişsiz istifadəçidə 401 düşər və
     `api()` avtomatik giriş pəncərəsini açardı — heç nə istəməyən adamın
     üzünə forma çıxardı. */
  document.addEventListener('pm:signed-in', () => {
    loadLibraryState();
    loadLibrary();
  });
  document.addEventListener('pm:signed-out', clearLibraryState);

  window.addEventListener('hashchange', routeView);
  routeView();               // səhifə birbaşa #library ilə açıla bilər

  // Düymələr sonradan render olunur, ona görə dinləyici sənəd səviyyəsindədir.
  document.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-lib][data-pid]');
    if (!b) return;
    toggleLibrary(Number(b.dataset.pid), b.dataset.lib);
  });

  $('#library-tabs').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-view]');
    if (b) loadLibrary(b.dataset.view);
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

  $('#deck-prev').addEventListener('click', () => flip(-1));
  $('#deck-next').addEventListener('click', () => flip(1));
  $('#deck').addEventListener('keydown', (ev) => {
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); flip(-1); }
    if (ev.key === 'ArrowRight') { ev.preventDefault(); flip(1); }
  });
  /* toxunma ilə vərəqləmə — mobil üçün */
  let touchX = null;
  $('#deck').addEventListener('touchstart', (ev) => { touchX = ev.touches[0].clientX; }, { passive: true });
  $('#deck').addEventListener('touchend', (ev) => {
    if (touchX === null) return;
    const dx = ev.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 45) flip(dx < 0 ? 1 : -1);
    touchX = null;
  }, { passive: true });
  $('#deck').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-ask]');
    if (!b) return;
    setMode('ask');
    $('#q').value = t('ask_about').replace('{t}', b.dataset.ask);
    $('#query-form').requestSubmit();
  });

  const card = $('#discover-card');
  card.addEventListener('mouseenter', () => { spotPaused = true; });
  card.addEventListener('mouseleave', () => { spotPaused = false; spotStart = performance.now(); });
  card.addEventListener('focusin', () => { spotPaused = true; });
  card.addEventListener('focusout', () => { spotPaused = false; spotStart = performance.now(); });

  /* loadAll trend qrafikini çəkir, o isə sahə→qrup xəritəsinə möhtacdır.
     Paralel buraxılsa trend keşdən daha tez qayıdır və hər şey «Digər» olur. */
  loadFields().then(loadAll).then(loadTrendClasses);
});
