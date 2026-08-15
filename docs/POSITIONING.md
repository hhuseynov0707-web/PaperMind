# PaperMind — mövqe sənədi

> Daxili sənəd. Hər hansı mətn (post, landing, CV sətri, video) yazılmazdan əvvəl bura baxılır.
> Qayda sadədir: **burada sübutu olmayan iddia heç bir yerdə yazılmır.**

> ⚠️ **Həll olunmamış qərar — lisenziya.** Repo-da `LICENSE` faylı yoxdur. Lisenziyasız kod
> texniki cəhətdən «bütün hüquqlar qorunur» sayılır — yəni «açıq mənbədir» deyə bilmərik.
> MIT nəzərdə tutulur, amma bu, sənin qərarındır və geri qaytarılması çətindir (bir dəfə
> dərc olunandan sonra adamlar ona güvənərək istifadə edir). Qərar verəndə `LICENSE` faylı
> əlavə olunmalı və README-lərdəki sətir düzəldilməlidir.

> 📊 **2026-08-15 — mövqe SORĞU İLƏ DƏYİŞDİRİLDİ (n=40).** Əvvəlki vəd
> «öz dilində soruş, ingiliscə tap» idi. Data onu dəstəkləmədi: cavab
> verənlərin yalnız **10%-i** ingilis dilini çətinlik sayır və yalnız **10%-i**
> AZ/RU dil dəstəyini faydalı xüsusiyyət seçir — siyahıda sonuncu yer.
> Ətraflı: [sorğu nəticələri](#sorğu-nəticələri-n40).

## Bir cümlə

**AZ:** Cavab uydurmur — hər cümlə açıb oxuya biləcəyin məqaləyə bağlıdır.
**EN:** Answers you can check — every claim links to a paper you can open.
**RU:** Ответы, которые можно проверить — каждое утверждение ведёт к статье.

*(Çoxdillilik silinmir — vəd olmaqdan çıxıb xüsusiyyət olur.)*

## Mövqe bəyanatı (formal)

> Tədqiqat üçün **artıq ChatGPT işlədən** tələbə və gənc tədqiqatçılar üçün
> **PaperMind** — eyni rahatlığı verən, amma hər iddianı **açıb oxuya biləcəyin
> real məqaləyə bağlayan** açıq mənbəli axtarış köməkçisidir.
> ChatGPT-dən fərqi: istinadlar yoxlanılır (ölçülmüş groundedness **91.4%**),
> uydurulmuş istinad avtomatik silinir və nəticə hansı korpusa əsaslandığını
> açıq göstərir.

**Niyə ChatGPT ilə müqayisə:** sorğuda cavab verənlərin **67.5%-i** məqalə
axtaranda məhz ümumi AI chat işlədir, **0%-i** isə Elicit/Consensus/Semantic
Scholar kimi ixtisaslaşmış alət. Rəqib odur ki, insanlar faktiki olaraq
işlədirlər — bazarın adı ilə çağırdığımız alət yox.

## Kimə (prioritet sırası ilə)

| # | Seqment | Ağrı | Niyə biz |
|---|---|---|---|
| 1 | Tədqiqat üçün AI chat işlədən tələbə | ChatGPT cavab verir, amma mənbəni yoxlamaq mümkün deyil; məqalə tapmaq və uzun mətni oxumaq vaxt aparır | Eyni rahatlıq + hər iddia açıla bilən məqaləyə bağlı |
| 2 | Texniki işəgötürən / müsahib | CV-lərdə «AI layihəsi» çoxdur, ölçülmüş nəticə yoxdur | Benchmark, testlər, qərarların səbəbi yazılıb |
| 3 | Self-host sevən developer | SaaS-a data verməkdən çəkinir | Lokal embedding, öz Postgres-i, Docker ilə bir əmr |

Seqment 2 **indi** işə düşür (deploy tələb etmir). Seqment 1 deploydan sonra.

## Sorğu nəticələri (n=40)

**Nümunənin məhdudiyyəti əvvəlcə:** 40 cavab (hədəf 100+ idi) və **65%-i İT
sahəsindən**. Yəni bu, tələbələrin deyil, İT-yə yaxın tələbələrin mənzərəsidir.
Tibb və psixologiyadan **sıfır** cavab var. Xəta payı ~±15%.

### Ağrı harada — və harada deyil

| Problem | % |
|---|---|
| Məqalələr uzundur, vaxt aparır | **57.5%** |
| Doğru məqaləni tapmaq çətindir | **47.5%** |
| Giriş pulludur | 42.5% |
| Terminlər ağırdır | 37.5% |
| Hansının etibarlı olduğunu bilmirəm | 30% |
| **İngilis dilində anlamaq çətindir** | **10%** |

### Faktiki rəqib

| Hardan axtarır | % |
|---|---|
| Google / Scholar | 77.5% |
| **ChatGPT / Claude / Gemini** | **67.5%** |
| **Elicit / Consensus / Semantic Scholar** | **0%** |

42.5% birbaşa «ChatGPT-dən soruşuram» deyir — yəni AI chat artıq standart iş
axınıdır, bizim əlavə etdiyimiz şey **yoxlana bilənlikdir**.

### Ən çox istənilən xüsusiyyət

| Xüsusiyyət | % |
|---|---|
| Doğru məqaləni daha tez tapmaq | **80%** |
| Məqaləni AI ilə asan anlamaq | 57.5% |
| Cavabın hansı məqalələrə əsaslandığını görmək | **47.5%** |
| Müxtəlif məqalələrin nəticələrini tutuşdurmaq | 45% |
| Trendlər / fənlərarası | 35% |
| **AZ/RU dilində elm** | **10%** |

### Ödəniş — qırmızı

50% heç nə ödəməz (30% «pulsuz olmalıdır» + 20% «ödəməzdim»). Qalanı qiymət
*adlandırır*, bu isə ödəmə vədi deyil. ÷3 qaydası ilə real konversiya ~13%.
Üstəlik 30% yalnız imtahan/diplom dövründə işlədəcəyini deyir — mövsümi istifadə
abunə üçün ən pis haldır.

**Qeyd:** dizaynımdakı «Ayda 5 AZN olsaydı ödəyərdin?» konkret öhdəlik sualı və
e-poçt xanası formada yoxdur. Ən güclü iki siqnalı ölçmədik.

### Qərar

Əvvəlcədən yazılmış budaq: **ödəmə sətirləri qırmızı → istehlakçı abunəsindən
imtina.** Məhsul pulsuz buraxılır; ödənişli qat sonra, real istifadə görüləndən
sonra sınanır.

## Pulsuz / Pro sərhədi — QURULMUR, qeyd olunur

Qərar: **indi hər şey pulsuzdur.** Ödənişli qat real istifadə görüləndən sonra
sınanacaq. Amma sərhəd indidən aydındır, çünki **xərc onu özü çəkir**:

| İmkan | Xərc | Qat |
|---|---|---|
| Semantik axtarış | Postgres + lokal embedding, ~66 ms, xarici xərc **yoxdur** | **Pulsuz** — və qalmalıdır: 80% məhz bunu istəyir |
| Vərəqlənən dəst, trendlər, landşaft | yalnız SQL, LLM yox | **Pulsuz** |
| Mənbəli AI cavabı | hər sorğu Groq çağırışıdır | Pulsuz, amma **limitli** (indi 20/saat) |
| Müqayisə, ziddiyyət | hər çağırış ~1 500 token | Sonradan **Pro** |
| Toplu çıxarış, öz korpusun | minlərlə LLM çağırışı | Sonradan **Pro** |

Prinsip: **Postgres-də bitən hər şey pulsuz, Groq-a çıxan hər şey ölçülür.**
Bu, süni məhdudiyyət deyil — real xərcin şəklidir və istifadəçiyə izah etmək
asandır.

Limit infrastrukturu **artıq var** (`security.py`: IP üzrə saatlıq limit +
günlük qlobal tavan). Pro qatı üçün lazım olan şey yalnız istifadəçi hesabı və
ödəniş — hər ikisi bu mərhələdə erkəndir.

**Sorğu bunu dəstəkləyir:** 30% «yalnız imtahan/diplom dövründə» işlədəcəyini
deyir. Mövsümi istifadəçidən aylıq abunə almaq mümkün deyil; ondan yalnız
zirvə anında dəyər almaq mümkündür — yəni limitli pulsuz + lazım olanda
genişlənmə düzgün formadır.

## Sübutlu iddialar — yalnız bunları yazırıq

| İddia | Sübut | Harada göstərilir |
|---|---|---|
| Rusca sorğu ingiliscə məqaləni tapır | RU↔EN oxşarlıq **0.79**; əlaqəsiz mətnlə −0.05 | README benchmark bölməsi |
| Axtarış keyfiyyəti ölçülüb | known-item MRR@10 **1.000** (en) / **0.969** (ru), NDCG 1.000/0.977; P@10 az 56 · en 50 · ru 51 (95 sorğu, 19 sahə) | `scripts/benchmark.py` |
| **Cavab istinadları uydurulmur** | groundedness **91.4%** (əvvəl 54.1%); kontekstdə olmayan istinad avtomatik silinir | `scripts/rag_eval.py` |
| Eyni məqalə təkrarlanmır | 15 DOAJ DOI-su Crossref-dən çəkildi: Crossref-in tanıdığı **7-nin 7-si** tək sətir + iki provenans; dublikat yaranmadı | `scripts/verify_dedup.py` |
| Fakt ilə AI nəticəsi ayrılır | hər çıxarış sahəsi `stated` / `synthesized` / `inferred`; sitat abstraktda yoxlanılır, tapılmasa etiket endirilir | `rag/insights.py` |
| Ziddiyyət şəraitdən çıxarılır | fərqli populyasiya/metrik → şərti ziddiyyət; sistem hansının doğru olduğunu demir | `rag/compare.py` |
| **Mürəkkəblik ölçmə ilə rədd edilir** | hibrid axtarış +0.3% → açılmadı; rerank 2.99 GB yaddaş → açılmadı | `.env.example`, `docs/AUDIT.md` |
| 3 dilli interfeys | 128 açar × 3 dil, tam | `static/app.js` |
| İctimai deploya hazırdır | API açarı + IP limitləri + HTTPS + preflight yoxlaması | `security.py`, `DEPLOY.md` |
| Test əhatəsi | **214 test** — dedup, dil, chunking, sübut, ziddiyyət, endpoint, provider | `backend/tests/` |

## Yazmadığımız iddialar

Bunlar **doğru deyil** və ya **hələ doğru deyil** — heç bir materialda görünməməlidir:

- ❌ «Milyonlarla məqalə» / «bütün elmi ədəbiyyat» — korpus **~1 600 məqalədir**. Bunu gizlətmirik.
- ❌ «Elicit/Consensus alternativi» — onlarda 125M+ məqalə var; müqayisə bizi kiçildir, böyütmür.
- ❌ «Tam mətn analizi» — yalnız abstraktlar indekslənir.
- ❌ «Sitat şəbəkəsi / impact analizi» — yoxdur.
- ❌ «Tibb üzrə etibarlı» — tibb korpusu nazikdir, arXiv-dən gəlmir.
- ❌ «Real-time» — yığım gündə 3 dəfə cron ilə olur.
- ❌ «Sitat qrafiki var» — cədvəl var, amma korpusda yalnız 33 məqalənin OpenAlex ID-si olduğu üçün sitat əlaqəsi praktiki olaraq boşdur.
- ❌ «Rerank işləyir» — kod var, sönülüdür (yaddaş xərci hədəf serverə sığmır).

**Korpus ölçüsü haqqında qayda:** heç vaxt gizlətmirik, amma heç vaxt da ön plana çıxarmırıq. Söhbət açılanda cavab hazırdır: *«Korpus kiçikdir və bilərəkdən belədir — hədəf geniş əhatə deyil, retrieval keyfiyyətinin ölçülə bilməsidir. Miqyas mühəndislik problemi deyil, hostinq problemidir.»*

## Ən güclü hekayə (bütün materialların özəyi)

> Rusca axtarışın işlədiyini **fərz etmişdim**. Benchmark yazdım — məlum oldu ki, rusca sorğular rusdilli korpusu **ümumiyyətlə görmür**: tərcümə edilmiş sorğu vektorlaşdırılırdı, orijinal yox. Sonra benchmark-ın özünün də təkrarlanmadığı ortaya çıxdı — `ORDER BY` olmadan eyni konfiqurasiya 0.885 və 0.773 verirdi. Hər iki səhv gözlə görünməzdi.

Bu hekayə işləyir, çünki: (a) real səhvdir, (b) ölçmə ilə tapılıb, (c) hər developer özünü orada görür. Uğur hekayəsindən daha inandırıcıdır.

## Səs tonu

- **Sakit, ölçülü, rəqəmli.** Nida işarəsi yox. «Revolutionary», «game-changing», «powered by AI» yox.
- **Səhvi göstərmək güc əlamətidir.** Nə işləmədiyini yazan adama nə işlədiyi barədə də inanırlar.
- Hər böyük iddiadan sonra dərhal rəqəm və ya link gəlir.
- Azərbaycanca mətnlərdə süni tərcümə termini yox — «retrieval», «embedding», «benchmark» olduğu kimi qalır.

## Vizual identika

| Element | Dəyər |
|---|---|
| Fon | `#09090B` |
| Aksent | `#6366F1` → `#818CF8` |
| İşarə | Konsentrik yay + nöqtə (dalğa kimi yayılan bilik) — `static/index.html` içindəki `brand-mark` |
| Şrift | Sistem stack (Inter/Segoe/SF) |
| Sosial kart | `docs/assets/social-card.svg` → 1280×640 PNG |
