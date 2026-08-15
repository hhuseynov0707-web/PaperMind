# PaperMind — mövqe sənədi

> Daxili sənəd. Hər hansı mətn (post, landing, CV sətri, video) yazılmazdan əvvəl bura baxılır.
> Qayda sadədir: **burada sübutu olmayan iddia heç bir yerdə yazılmır.**

> ⚠️ **Həll olunmamış qərar — lisenziya.** Repo-da `LICENSE` faylı yoxdur. Lisenziyasız kod
> texniki cəhətdən «bütün hüquqlar qorunur» sayılır — yəni «açıq mənbədir» deyə bilmərik.
> MIT nəzərdə tutulur, amma bu, sənin qərarındır və geri qaytarılması çətindir (bir dəfə
> dərc olunandan sonra adamlar ona güvənərək istifadə edir). Qərar verəndə `LICENSE` faylı
> əlavə olunmalı və README-lərdəki sətir düzəldilməlidir.

## Bir cümlə

**AZ:** Rusca və ya azərbaycanca soruş — ingiliscə araşdırmaları tap.
**EN:** Ask in your language, find research in English.
**RU:** Спрашивайте на своём языке — находите исследования на английском.

## Mövqe bəyanatı (formal)

> Elmi ədəbiyyatı **ingilis dilində** oxumaq məcburiyyətində olan, amma rusca və ya azərbaycanca düşünən tələbə və gənc tədqiqatçılar üçün
> **PaperMind** — dörd akademik mənbə üzərində məna ilə axtaran və cavabı **öz dilində, mənbə göstərərək** verən açıq mənbəli tədqiqat köməkçisidir.
> Elicit və Consensus-dan fərqi: açıq mənbədir, öz serverində işləyir və **axtarış keyfiyyəti dərc olunub, təkrarlana bilir**.

## Kimə (prioritet sırası ilə)

| # | Seqment | Ağrı | Niyə biz |
|---|---|---|---|
| 1 | AZ/RU dilli bakalavr–magistr tələbə | İngiliscə açar söz seçə bilmir, ona görə axtarış boş qayıdır | Öz dilində soruşur, sistem tərcümə + məna ilə tapır |
| 2 | Texniki işəgötürən / müsahib | CV-lərdə «AI layihəsi» çoxdur, ölçülmüş nəticə yoxdur | Benchmark, testlər, qərarların səbəbi yazılıb |
| 3 | Self-host sevən developer | SaaS-a data verməkdən çəkinir | Lokal embedding, öz Postgres-i, Docker ilə bir əmr |

Seqment 2 **indi** işə düşür (deploy tələb etmir). Seqment 1 deploydan sonra.

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
