/**
 * PaperMind — tələbə sorğusunu Google Forms-da avtomatik qurur.
 *
 * İSTİFADƏ:
 *   1. script.google.com → New project
 *   2. bu faylın hamısını yapışdır
 *   3. yuxarıdan createPaperMindSurvey seç → Run → icazə ver
 *   4. Execution log-da redaktə və paylaşım linkləri çıxacaq
 *
 * DİZAYN QEYDİ: məhsul yalnız 5-ci bölmədə təsvir olunur. Əvvəldə açılsa,
 * bütün ağrı sualları bizim xeyrimizə əyilir. Sıranı dəyişmə.
 */

function createPaperMindSurvey() {
  var form = FormApp.create('Tələbələr elmi məqalələri necə oxuyur?');

  form.setDescription(
    '5 dəqiqə · Anonimdir · Heç nə satmıram.\n\n' +
    'Universitet layihəm üçün real vərdişləri öyrənməyə çalışıram. ' +
    'Burada düzgün cavab yoxdur — "heç vaxt oxumamışam" da tam dəyərli cavabdır, ' +
    'elə ona görə soruşuram.\n\n' +
    'Nəticələri hazır olanda hamıya göndərəcəyəm.'
  );

  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setLimitOneResponsePerUser(false);

  // ── kömkəçi funksiyalar ────────────────────────────────────────────────
  function section(title, help) {
    var p = form.addPageBreakItem().setTitle(title);
    if (help) p.setHelpText(help);
    return p;
  }
  function radio(title, choices, required, help) {
    var q = form.addMultipleChoiceItem().setTitle(title).setChoiceValues(choices);
    q.setRequired(required !== false);
    if (help) q.setHelpText(help);
    return q;
  }
  function checks(title, choices, required, help) {
    var q = form.addCheckboxItem().setTitle(title).setChoiceValues(choices);
    q.setRequired(required !== false);
    if (help) q.setHelpText(help);
    return q;
  }
  function scale(title, low, high, help) {
    var q = form.addScaleItem().setTitle(title).setBounds(1, 5).setLabels(low, high).setRequired(true);
    if (help) q.setHelpText(help);
    return q;
  }

  // ── 1. PROFİL ──────────────────────────────────────────────────────────
  section('Sən kimsən', 'Cavabları qruplara ayıra bilmək üçün — şəxsi məlumat soruşulmur.');

  radio('Təhsil pilləsi', [
    'Bakalavr, 1–2-ci kurs',
    'Bakalavr, 3–4-cü kurs',
    'Magistratura',
    'Doktorantura',
    'Məzunam / işləyirəm',
    'Tələbə deyiləm'
  ]);

  radio('Sahən hansına daha yaxındır?', [
    'İT / kompüter elmləri / mühəndislik',
    'Təbiət elmləri (fizika, kimya, biologiya, geologiya)',
    'Riyaziyyat / statistika',
    'Tibb və sağlamlıq',
    'İqtisadiyyat / biznes',
    'Sosial elmlər (psixologiya, sosiologiya, hüquq)',
    'Humanitar elmlər (dil, tarix, ədəbiyyat)'
  ]).showOtherOption(true);

  form.addTextItem()
    .setTitle('Universitetin (istəyə bağlı)')
    .setRequired(false);

  // ── 2. VƏRDİŞ (keçmiş davranış) ────────────────────────────────────────
  section('Oxu vərdişin',
    'Burada "elmi məqalə" dedikdə jurnalda və ya arXiv kimi bazalarda dərc olunan ' +
    'tədqiqat işi nəzərdə tutulur — xəbər saytındakı və ya bloqdakı yazı yox.');

  radio('Sonuncu dəfə nə vaxt elmi məqalə oxumusan?', [
    'Bu həftə',
    'Bu ay',
    'Son 3 ay ərzində',
    'Bu il, amma çoxdan',
    'Heç vaxt oxumamışam',
    'Dəqiq bilmirəm / fərqini bilmirəm'
  ], true, 'Ən vacib sual budur — səmimi cavab ver.');

  radio('Adətən ayda neçə elmi məqalə açırsan?', [
    '0',
    '1–2',
    '3–5',
    '6–10',
    '10-dan çox'
  ]);

  checks('Sonuncu dəfə niyə oxumuşdun?', [
    'Kurs işi / diplom işi',
    'Müəllim tapşırmışdı',
    'Öz tədqiqatım / məqalə yazırdım',
    'İmtahana hazırlıq',
    'Şəxsi maraq',
    'Oxumamışam'
  ]).showOtherOption(true);

  radio('Birini axıra kimi oxumaq üçün adətən neçə məqalə açırsan?', [
    '1–2',
    '3–5',
    '6–10',
    '10-dan çox',
    'Axıra kimi oxumuram / bilmirəm'
  ], true, 'Yəni: neçəsini açıb "bu, mənə lazım deyilmiş" deyib bağlayırsan?');

  // ── 3. AĞRI ────────────────────────────────────────────────────────────
  section('Prosesin özü', 'Nə işləyir, nə işləmir.');

  checks('Məqaləni adətən hardan tapırsan?', [
    'Adi Google axtarışı',
    'Google Scholar',
    'ChatGPT / Claude / Gemini və b.',
    'Sci-Hub',
    'Telegram kanalları / qrupları',
    'Universitet kitabxanası və ya elektron bazası',
    'Müəllim və ya rəhbər verir',
    'YouTube / bloq / xülasə saytları',
    'Tapa bilmirəm'
  ]).showOtherOption(true);

  checks('Ən çox nə çətinlik yaradır?', [
    'İngilis dili — mətni anlamaq çətindir',
    'Pulludur, məqaləyə çata bilmirəm',
    'Nə axtaracağımı, hansı sözü yazacağımı bilmirəm',
    'Çox uzundur, vaxt aparır',
    'Terminlər ağırdır',
    'Hansının etibarlı olduğunu ayırd edə bilmirəm',
    'Ciddi çətinlik çəkmirəm'
  ], true, 'Bir neçəsini seçə bilərsən.').showOtherOption(true);

  scale('İngiliscə elmi mətn oxumaq sənə nə qədər çətindir?',
    'Heç çətin deyil', 'Çox çətindir');

  radio('Bir məqaləni anlamağa orta hesabla nə qədər vaxt sərf edirsən?', [
    '15 dəqiqədən az',
    '15–30 dəqiqə',
    '30–60 dəqiqə',
    '1–2 saat',
    '2 saatdan çox',
    'Oxumuram'
  ]);

  // ── 4. ALƏT VƏ PUL (indiki davranış) ───────────────────────────────────
  section('Alətlər və xərclər',
    'Bu bölmə ideya haqqında deyil — indiki vərdişlərin haqqındadır.');

  checks('Tədqiqat və ya oxu üçün hansılardan istifadə edirsən?', [
    'ChatGPT / Claude / Gemini — pulsuz versiya',
    'ChatGPT Plus / Gemini Advanced və b. — pullu versiya',
    'Google Scholar',
    'Elicit / Consensus / SciSpace / Semantic Scholar',
    'Connected Papers / ResearchRabbit',
    'Zotero / Mendeley (istinad menecerləri)',
    'Google Translate / DeepL',
    'Heç birindən'
  ]).showOtherOption(true);

  checks('Hazırda hansı rəqəmsal xidmətlərə PUL ÖDƏYİRSƏN?', [
    'Spotify / Apple Music / YouTube Premium',
    'Netflix / Amediateka / oxşar',
    'ChatGPT Plus və ya başqa AI abunəsi',
    'Oyun abunəsi və ya oyundaxili alışlar',
    'Onlayn kurs (Udemy, Coursera, yerli kurslar)',
    'VPN',
    'Bulud yaddaşı (Google One, iCloud)',
    'Heç birinə ödəmirəm'
  ], true, 'Səmimi ol — bu, ödəmə vərdişini anlamaq üçündür, mühakimə üçün yox.');

  radio('Son 12 ayda TƏHSİL və ya TƏDQİQAT üçün pul ödəmisən?', [
    'Bəli, dəfələrlə',
    'Bəli, bir-iki dəfə',
    'Yox',
    'Valideynim / universitet ödəyib, mən yox'
  ], true, 'Kurs, kitab, məqaləyə giriş, tərcümə, redaktə, AI abunəsi və s.');

  form.addTextItem()
    .setTitle('Ödəmisənsə — təxminən nəyə və nə qədər? (istəyə bağlı)')
    .setHelpText('Məsələn: "Udemy kursu, 20 AZN" və ya "ChatGPT Plus, ayda 20$"')
    .setRequired(false);

  // ── 5. KONSEPT (məhsul yalnız İNDİ açılır) ─────────────────────────────
  section('Bir ideya haqqında fikrin',
    'İndi üzərində işlədiyim ideyanı qısa təsvir edirəm.\n\n' +
    'Azərbaycanca və ya rusca sual verirsən. Sistem dörd akademik bazadan ' +
    '(arXiv, Crossref, DOAJ, OpenAlex) açar sözlə yox, məna ilə axtarır və ' +
    'cavabı sənin dilində, hansı məqalələrə əsaslandığını göstərərək qaytarır. ' +
    'Uydurmur: mənbə tapılmayanda "tapılmadı" deyir.\n\n' +
    'Səmimi cavab ver — "lazım deyil" cavabı mənim üçün ən faydalısıdır.');

  scale('Belə bir alət sənin işinə yarayardı?',
    'Ümumiyyətlə yox', 'Çox yarayardı');

  checks('Hansı hissəsi sənə daha çox lazımdır?', [
    'Öz dilimdə sual verə bilmək',
    'Cavabın hansı məqaləyə əsaslandığını görmək',
    'Ümumiyyətlə uyğun məqaləni tapa bilmək',
    'Uzun məqalənin qısa xülasəsi',
    'Sahədəki trendləri görmək',
    'Heç biri lazım deyil'
  ]).showOtherOption(true);

  radio('Bu alət TAM PULSUZ olsaydı, nə qədər tez-tez işlədərdin?', [
    'Demək olar hər gün',
    'Həftədə bir neçə dəfə',
    'Ayda bir neçə dəfə',
    'Yalnız imtahan / diplom dövründə',
    'İşlətməzdim'
  ]);

  radio('Ayda 5 AZN olsaydı?', [
    'Ödəyərdim',
    'Yalnız imtahan / diplom dövründə ödəyərdim',
    'Ödəməzdim — pulsuz alternativ axtarardım',
    'Ödəməzdim, ümumiyyətlə lazım deyil'
  ]);

  radio('Sənə görə belə bir alət üçün ayda nə qədər ədalətli qiymətdir?', [
    '0 — belə şey pulsuz olmalıdır',
    '1–3 AZN',
    '4–7 AZN',
    '8–15 AZN',
    '15 AZN-dən çox'
  ]);

  radio('Sənə görə kim ödəməlidir?', [
    'Tələbə özü',
    'Universitet',
    'Kafedra / elmi rəhbər / laboratoriya',
    'Heç kim — reklamla və ya qrantla pulsuz qalmalıdır'
  ]);

  // ── 6. ƏLAQƏ ───────────────────────────────────────────────────────────
  section('Son', 'Bu bölmənin hamısı istəyə bağlıdır.');

  checks('Maraqlanırsansa (istəyə bağlı)', [
    '15 dəqiqəlik söhbətə hazıram — suallarını cavablandıra bilərəm',
    'Hazır olanda xəbər ver, sınamaq istəyirəm',
    'Sorğunun nəticələrini mənə göndər'
  ], false);

  form.addTextItem()
    .setTitle('E-poçt (yuxarıdakılardan birini seçmisənsə)')
    .setHelpText('Yalnız bu üç səbəb üçün istifadə olunacaq. Reklam göndərilməyəcək.')
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('Əlavə demək istədiyin bir şey varsa (istəyə bağlı)')
    .setHelpText('Bu xana çox vaxt bütün cədvəldən daha faydalı olur.')
    .setRequired(false);

  // ── nəticə ─────────────────────────────────────────────────────────────
  // Yeni Google Forms hesablarında forma ayrıca "publish" tələb edir.
  // Köhnə hesablarda bu metod yoxdur, ona görə qorunub çağırılır.
  try {
    if (typeof form.setPublished === 'function') form.setPublished(true);
  } catch (e) {
    Logger.log('Qeyd: formanı əl ilə "Publish" etmək lazım ola bilər (' + e + ')');
  }

  Logger.log('✅ Forma hazırdır');
  Logger.log('Redaktə:  ' + form.getEditUrl());
  Logger.log('Paylaşım: ' + form.getPublishedUrl());
  return form.getPublishedUrl();
}
