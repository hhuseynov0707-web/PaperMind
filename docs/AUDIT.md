# PaperMind — Forensic Audit (Phase 0)

**Tarix:** 2026-08-12 · **Metod:** statik oxu + test icrası + sxem/indeks yoxlaması
**Kod bazası:** 3 514 sətir Python (38 fayl), 1 997 sətir frontend, 5 n8n workflow

> **Yenilənmə (Phase 1 tamamlandı, Codespace-də doğrulandı).** Aşağıdakı auditin
> proqnozlarından ikisi real data ilə yoxlananda dəyişdi — hər ikisi bu sənədin
> müvafiq yerində qeyd olunub. Ölçülmüş nəticələr: [Phase 1 nəticələri](#phase-1-nəticələri-ölçülmüş).

## İcra edilə bilənlər / bilinməyənlər

| Yoxlama | Nəticə |
|---|---|
| Testlər (saf funksiyalar) | ✅ **39 test keçdi** lokal Python 3.13-də |
| Testlər (DB tələb edən) | ⏭ `test_dedup.py` — Postgres olmadığı üçün ötürüldü |
| Sistemin işə salınması | ❌ **Mümkün olmadı** — Docker daemon bu maşında işləmir (8 GB RAM problemi, iş Codespaces-ə köçürülüb) |
| Canlı benchmark | ❌ Mümkün olmadı — DB yoxdur |

> **Dürüstlük qeydi:** aşağıdakı retrieval rəqəmləri (MRR 0.900/0.800 və s.) **bu auditdə yenidən ölçülməyib** — onlar əvvəlki ölçmədən (n=60, korpus 1 047) gələn qeydlərdir. Phase 2-yə başlamazdan əvvəl Codespaces-də təkrar ölçülməlidir, çünki korpus o vaxtdan ~1 600-ə çatıb. Ölçülməmiş rəqəmə əsaslanaraq qərar verməyəcəyik.

---

## 1. Mövcud arxitektura

```
Brauzer ──▶ FastAPI (sync def, threadpool)
              ├─▶ retrieval_inputs()  ──▶ [az/ru üçün] Groq tərcümə  ──▶ Redis (7 gün)
              ├─▶ embed_texts()       ──▶ fastembed (lokal CPU, 384d)
              ├─▶ retrieve()          ──▶ Postgres pgvector, HNSW cosine
              ├─▶ ask_llm()           ──▶ Groq llama-3.3-70b
              └─▶ cache.get_or_set()  ──▶ Redis
n8n (3 cron) ──▶ POST /api/ingest/pull ──▶ sources/{arxiv,crossref,doaj,openalex}
                                        └─▶ upsert_papers() → dedup → chunk → embed → DB
```

**Data axını (ingest):** mənbə adapteri `fetch(field, since, limit, lang)` → `PaperIn` → `upsert_papers()` → 3 açarlı dedup → yeni sətir və ya `paper_sources`-a əlavə → `chunk_text()` → `embed_texts()` → `chunks`.

**Data axını (sorğu):** sorğu → `detect_lang()` → dilə görə (bəzən Groq tərcüməsi) → 1 və ya 2 vektor → `LEAST()` cosine → top-k chunk → Python-da paper üzrə dedup → (ask üçün) kontekst → Groq → cavab.

**Sxem (11 cədvəl):** `papers`, `paper_sources`, `authors`, `categories`, `chunks`, `qa_history`, `ingest_runs`, `error_logs`, `digests` + 2 M2M.

**İndekslər:** HNSW (`chunks.embedding`, cosine), GIN (`papers.field_keys`), B-tree (doi, title_key, arxiv_id unique, language, source, published_at).

---

## 2. Nə yaxşıdır — SAXLANILIR

Bunlar layihənin əsl dəyəridir; yenidən yazılmamalıdır.

| # | Komponent | Niyə saxlanılır |
|---|---|---|
| G1 ✅ | **Provenanslı kimlik sxemi** (`papers` + `paper_sources`, unique `(source, external_id)`) | §4-ün tələb etdiyi kanonik iş + provenans modeli **artıq doğru qurulub**. **Canlı data ilə təsdiqləndi** (`verify_dedup.py`): bazadakı 15 DOAJ DOI-su Crossref-dən birbaşa çəkiləndə Crossref-in tanıdığı **7-nin 7-si** də tək sətir + iki provenansla mövcud idi, tanımadığı 8-in hamısında yalnız `doaj`. Dublikat yaranmadı. |
| G2 | **Benchmark produksiya kodunu çağırır** (`retrieval_inputs()` həm API-də, həm benchmark-da) | Ölçülən davranışla istifadəçinin gördüyü davranışın ayrılması mümkün deyil. Bu, çox layihədə olmayan disiplindir — §20-nin təməlidir. |
| G3 | **Dil əlifbadan təyin olunur**, mənbə etiketindən yox (`common.detect_language`) | §2 üçün doğru qərar; rus jurnalları ingiliscə abstrakt dərc edir. |
| G4 | **Mənbə adapter registry-si** (`SOURCES` dict, hər modulda eyni `fetch()` imzası) | §3-ün «source-agnostic» tələbi arxitektura səviyyəsində **artıq ödənilib**. Yeni mənbə = yeni fayl. |
| G5 | **İki səviyyəli taksonomiya** (`fields.py`: 5 qrup / 19 sahə / 76 arXiv kateqoriyası) | §1-in fənn siyahısı üçün hazır skelet. |
| G6 | **Təhlükəsizlik qatı ictimai açılışdan ƏVVƏL yazılıb** (`security.py`) | Açar + IP limitləri + günlük tavan mövcuddur. |
| G7 | **İdempotent miqrasiyalar** (`migrate.py`, Alembic-siz) | Bu ölçüdə layihə üçün doğru seçim; sxem dəyişikliyi ucuzdur. |
| G8 | **Frontend-də `esc()` sistematik işlədilir**, LLM cavabı da escape olunur (`app.js:675`) | XSS-in əsas vektoru bağlıdır. |
| G9 | **Real i18n** (3 lüğət, `data-i18n` atributları, hardcoded sətir yoxdur) | §19-un i18n tələbi ödənilib. |
| G10 | **SSRF yoxdur** — `/api/ingest/pull` yalnız sabit registry-dən mənbə qəbul edir, ixtiyari URL yox | §17 üçün doğru dizayn. |
| G11 | **Chunk-larda `embedding_model` saxlanılır** | Model dəyişəndə bərpa oluna bilən reembed. |

---

## 3. Nə həqiqətən zəifdir

| # | Problem | Sübut | Təsir |
|---|---|---|---|
| W1 | **Leksik axtarış ümumiyyətlə yoxdur** | `migrate.py`-da nə `tsvector` sütunu, nə GIN text indeksi var | §5 hibrid retrieval sıfırdan qurulmalıdır |
| W2 | **Retrieval chunk qaytarır, məqalə yox** | `retriever.py:44` `limit(top_k)` chunk üzrədir; paper dedup **sonra**, Python-da (`search.py:35-43`) | Bir məqalənin 3 chunk-u top-5-i doldura bilər → istifadəçi 5 yerinə 2 nəticə görür |
| W3 | **Rerank / evidence selection / claim validation yoxdur** | `ask.py:63-83` — retrieve → birbaşa LLM | §8-in 8 mərhələsindən yalnız 3-ü var |
| W4 | **Məqalə səviyyəli intellekt yoxdur** | `models.Paper`-də metodologiya, nəticə, məhdudiyyət sahələri yoxdur | §7 tam çatışmır |
| W5 | **Müqayisə, ziddiyyət, landşaft, gap yoxdur** | Belə router/servis yoxdur | §9–§13 tam çatışmır |
| W6 | **Query understanding = yalnız dil aşkarlaması** | `translator.detect_lang()` | §6-nın intent/entity/tarix/müəllif hissəsi yoxdur |
| W7 | **NDCG ölçülmür**, RAG heç ölçülmür | `benchmark.py` MRR/Recall/P hesablayır | §20 tələbləri qismən |
| W8 | **Əlaqə (relationship) modeli yoxdur** | `cites`, `contradicts` cədvəli yoxdur | §15 çatışmır |
| W9 | **Korpus şəffaflığı UI-da yoxdur** | Cavabda «bu, indekslənmiş korpusa əsaslanır» qeydi yoxdur | §16 çatışmır |
| W10 | **Endpoint/inteqrasiya/təhlükəsizlik testi yoxdur** | `tests/` yalnız saf funksiyalar + 1 DB testi | §21 çatışmır; bir dəfə `500` bu boşluqdan keçib |

---

## 4. Kritik texniki borc

Bunlar **yeni funksiyadan əvvəl** həll olunmalıdır — çünki data korrupsiyası və xərc riski daşıyırlar.

### D1 🔴 Başlıq üzrə birləşmə ziddiyyətli DOI-ları da birləşdirir

`crud.py:_find_existing` üç açarı **`or_`** ilə birləşdirir:

```python
conditions = [Paper.doi == doi, Paper.arxiv_id == arxiv_id, Paper.title_key == tkey]
return db.scalars(select(Paper).where(or_(*conditions)).limit(1)).first()
```

Yəni gələn məqalənin DOI-su `10.1/A`, bazadakının DOI-su `10.2/B` olsa **və başlıqlar eyni olsa**, onlar birləşir. §4 açıq deyir: *«Never aggressively merge uncertain records.»*

Real ssenarilər: eyni adlı fərqli işlər, konfrans proceedings ön-materialı, «Introduction to …» tipli başlıqlar. `len(t) < 12` qorunması yalnız çox qısa başlıqları kəsir.

**Düzəliş:** mənfi sübut qaydası — hər iki tərəfdə DOI varsa və **fərqlidirsə**, başlıq üzrə birləşmə qadağandır. Eyni qayda fərqli arXiv ID-lər üçün.

### D2 🔴 `PaperIn`-də heç bir uzunluq limiti yoxdur

`schemas.py`: `title: str`, `abstract: str`, `authors: list[str]` — hamısı limitsiz. Bütün `schemas.py`-da cəmi **1** `max_length` var (o da `AskRequest`-də).

Nəticə: 50 MB-lıq abstract → chunker minlərlə chunk yaradır → fastembed CPU-nu doldurur → yaddaş. §17-nin «oversized documents» maddəsi ödənilmir.

### D3 🟠 `papers.doi`-də DB səviyyəsində unikallıq yoxdur

`arxiv_id` unique-dir, `doi` yalnız indekslidir. Dedup tam olaraq tətbiq qatındadır. Paralel ingest (W4 və W5 hər ikisi DOAJ işlədir) eyni DOI-nu iki sətir kimi yaza bilər.

### D4 🟠 Bütün endpoint-lər sinxrondur, `/api/ingest/pull` isə uzun sürür

`routers/*.py`-da **0 ədəd `async def`**. `pull` 19 sahə üzrə şəbəkə sorğusu + embedding edir — dəqiqələrlə davam edə bilər və bu müddətdə bir threadpool işçisini və DB sessiyasını tutur. FastAPI-nin standart threadpool-u 40-dır.

### D5 🟡 `_find_existing`-də `limit(1)` sıralamasızdır

`or_` bir neçə sətrə uyğun gələndə hansının qayıtdığı Postgres-in ixtiyarındadır → dedup hədəfi qeyri-deterministikdir.

### D6 🟡 Birləşmədə abstract zənginləşdirilmir

`_merge_source` DOI, arXiv ID, PDF, field_keys doldurur, amma `abstract`-a toxunmur. arXiv-in kəsik abstraktı Crossref-in tam abstraktını üstələyir və chunk-lar yenidən yaradılmır.

### D7 🟡 PMID və OpenAlex ID sütunları yoxdur

§4 birbaşa bu identifikatorları tələb edir; hazırda yalnız `arxiv_id`, `doi`, generik `external_id` var.

---

## 5. Retrieval problemləri

1. **Vektor-yeganə.** Leksik siqnal ümumiyyətlə yoxdur → nadir termin, model adı, identifikator axtarışı zəifdir. (§5)
2. **Chunk səviyyəsində limit** → nəticə sayı gözləniləndən az ola bilər, məqalə müxtəlifliyi yoxdur. (W2)
3. **Filtr yalnız `field_keys` üzrədir.** Dil, tarix aralığı, müəllif, identifikator filtri retrieval-a çıxarılmayıb — halbuki `papers.language` və `published_at` indekslidir. (§5 «temporal signals», «author matching»)
4. **Rerank yoxdur.** İlk 10 xam cosine sıralamasıdır.
5. **Ölçmədə NDCG yoxdur**, və `--compare` yalnız tərcümə strategiyalarını müqayisə edir — *vector vs lexical vs hybrid* müqayisəsi üçün skelet mövcud deyil. (§5, §20)
6. **Sorğu vaxtı embedding CPU-da hesablanır** (fastembed lokal) — sinxron endpoint-də bu, threadpool işçisini bloklayır.

---

## 6. RAG / evidence problemləri

1. 🔴 **Prompt injection açıqdır.** `llm.py:60-71` — məqalə mətni birbaşa **system prompt-un içinə** interpolyasiya olunur:
   ```python
   SYSTEM_PROMPT.format(context=context, answer_lang=...)
   ```
   Abstraktın içindəki *«Ignore previous instructions…»* sətri system səlahiyyəti ilə oxunur. Nə delimiter, nə sanitizasiya, nə də «kontekst datadır, əmr deyil» direktivi var. §17 bunu birbaşa qadağan edir.
2. **İstinad doğruluğu yoxlanılmır.** LLM `[10.1234/xyz]` yazsa, o DOI-nun həqiqətən kontekstdə olub-olmadığı **heç yerdə yoxlanılmır**. §8: *«Never fabricate citations»* — hazırda yalnız prompt qaydası ilə ümid edilir.
3. **Claim extraction / validation yoxdur.** §8-in 6-cı və 7-ci mərhələləri mövcud deyil.
4. **DIRECTLY STATED / SYNTHESIZED / AI INFERENCE fərqi yoxdur.** (§7)
5. **Evidence selection yoxdur** — retrieval nə qaytarsa, hamısı konteksti doldurur; uyğunluq həddi (threshold) yoxdur. Zəif nəticələr (score 0.2) da LLM-ə gedir və cavabı çirkləndirir.
6. **Korpus konteksti cavaba əlavə olunmur** (§16).

---

## 7. Data / mənbə məhdudiyyətləri

| Sahə | Vəziyyət | Boşluq |
|---|---|---|
| CS/AI, fizika, riyaziyyat | arXiv yaxşı örtür | — |
| **Tibb / biologiya** | `fields.py`-da `medicine` üçün arXiv kateqoriyası **boş siyahıdır**; yalnız Crossref/DOAJ mətn sorğusu | **PubMed / Europe PMC yoxdur** — bu sahə üçün əsas mənbə |
| **İqtisadiyyat / maliyyə** | `econ.*` arXiv-də zəif təmsil olunur | RePEc / SSRN yoxdur |
| **Fəlsəfə** | Ümumiyyətlə sahə kimi mövcud deyil | §1 fəlsəfəni tələb edir; `fields.py`-da yoxdur |
| **Psixologiya** | arXiv kateqoriyası boş | Yalnız mətn sorğusu |
| Sosial elmlər | Qismən (OpenAlex) | — |

Həmçinin: **yalnız abstraktlar indekslənir**, tam mətn yox → §7-nin metodologiya/dataset/məhdudiyyət çıxarışı abstraktın verdiyi ilə məhdud qalacaq. Bu, dürüst şəkildə etiketlənməlidir.

---

## 8. Çoxdilli problemlər

1. **RU korpus nazikdir** (~85 məqalə ölçmə anında) — «çoxdilli axtarış» iddiasını statistik olaraq zəif dayaqlayır.
2. **AZ aşkarlaması sözlük əsaslıdır** (`_AZ_ASCII_HINTS`, 24 söz) — diakritiksiz yazılan siyahıdankənar cümlə `en` sayılır və tərcümə mərhələsi ötürülür.
3. **Tərcümə sorğu yolundadır və LLM çağırışıdır** — hər yeni az/ru sorğu Groq xərcidir (keş 7 gün, amma unikal sorğu həmişə MISS).
4. **Retrieval dil üzrə filtrləyə/çəkiləndirə bilmir** — `papers.language` var, amma `retrieve()` onu işlətmir.
5. UI tərəfi **tamdır** (3 dil, 128 açar) — burada problem yoxdur.

---

## 9. Təhlükəsizlik riskləri

| # | Risk | Səviyyə | Yer |
|---|---|---|---|
| S1 | **Prompt injection** — məqalə mətni system prompt-da | 🔴 Yüksək | `rag/llm.py:60-71` |
| S2 | **Limitsiz giriş ölçüsü** — abstract/title/authors limitsiz | 🔴 Yüksək | `schemas.py: PaperIn` |
| S3 | **`/api/search` LLM xərci yaradır, amma günlük tavan yoxdur** — az/ru sorğu Groq tərcüməsi çağırır; `enforce_search_limits` yalnız IP üzrə 120/saat, qlobal büdcə yalnız `/api/ask`-dədır | 🟠 Orta-yüksək | `security.py:83`, `translator.py:76` |
| S4 | **URL sxemi yoxlanılmır** — `pdf_url` mənbədən gəlir və `href`-ə qoyulur; `esc()` `javascript:` sxemini bloklamır | 🟠 Orta | `app.js:690` |
| S5 | **`qa_history` bütün istifadəçi suallarını saxlayır** — ictimai rejimdə şəxsi məlumat düşə bilər, saxlama müddəti yoxdur | 🟡 Aşağı-orta | `crud.save_qa` |
| S6 | **Groq açarı söhbətdə açıq yazılıb** — hələ rotasiya edilməyib | 🟠 Orta | `.env` |
| S7 | SQL injection | ✅ Risk yoxdur — raw SQL yalnız `trends()`-dədir və orada dəyərlər bind olunur, `VALUES` cütləri isə `fields.py`-dan (istifadəçi girişi deyil) | `crud.trends` |
| S8 | CORS | ✅ Konfiqurasiya edilməyib = eyni-origin. Frontend backend-lə eyni serverdən verilir, ona görə düzgündür. Ayrı frontend deploy ediləcəksə şüurlu şəkildə açılmalıdır | `main.py` |

---

## 10. Performans riskləri

| # | Risk | İzah |
|---|---|---|
| P1 | **Sinxron endpoint + uzun ingest** | `/api/ingest/pull` dəqiqələrlə threadpool işçisi tutur (D4) |
| P2 | **Sorğu yolunda CPU embedding** | fastembed hər axtarışda çağırılır; sinxron kontekstdə bloklayır |
| P3 | **`ORDER BY random()`** | `crud.py:231,234` — tam cədvəl sortu; 1.6k sətirdə problem deyil, 100k+-da problemdir |
| P4 | **Chunk→paper dedup Python-da** | Verilənlər bazasından lazımsız sətir çəkilir (W2 ilə eyni kök) |
| P5 | **Analitika 6 saat keşlənir** | Doğru qərar; problem yoxdur |
| P6 | **HNSW parametrləri defolt** | `m`, `ef_construction` ayarlanmayıb; korpus böyüyəndə tənzimlənməlidir |

---

## 11. Çatışmayan yüksək dəyərli imkanlar

Brief-in tələbləri ilə üzbəüz:

| Bölmə | Tələb | Vəziyyət |
|---|---|---|
| §5 | Hybrid retrieval | ❌ yoxdur |
| §6 | Intent/entity/tarix/müəllif təyini | ❌ yoxdur (yalnız dil) |
| §7 | Məqalə intellekti (metod, nəticə, limitasiya) | ❌ yoxdur |
| §8 | Claim validation, citation doğrulaması | ❌ yoxdur |
| §9 | Müqayisə | ❌ yoxdur |
| §10 | Ziddiyyət təsnifatı | ❌ yoxdur |
| §11 | Research landscape | ❌ yoxdur |
| §12 | Trend təsnifatı (EMERGING/GROWING/…) | 🟡 xam say var, təsnifat yoxdur |
| §13 | Research gaps | ❌ yoxdur |
| §14 | Cross-disciplinary | 🟡 taksonomiya var, əlaqələndirmə yoxdur |
| §15 | Əlaqələr | ❌ yoxdur |
| §16 | Korpus şəffaflığı | ❌ yoxdur |
| §20 | RAG evaluation | ❌ yoxdur |

---

## 12. Hədəf arxitektura

Mövcud strukturu **saxlayaraq** aşağıdakı qatlar əlavə olunur. Yeni infrastruktur (graph DB, Elasticsearch, microservice) **əlavə edilmir** — §15 və §18 bunu açıq şəkildə istəmir və Postgres hər ikisini qarşılayır.

```
                    ┌──────────────── QUERY UNDERSTANDING ────────────────┐
 sorğu ────────────▶│ dil · intent · fənn · entity · tarix · müəllif      │
                    └────────────────────────┬────────────────────────────┘
                                             ▼
                    ┌──────────────── HYBRID RETRIEVAL ───────────────────┐
                    │  vektor (pgvector HNSW)   ⊕   leksik (tsvector GIN) │
                    │            RRF birləşməsi · məqalə səviyyəsində     │
                    │       filtrlər: fənn · dil · tarix · müəllif        │
                    └────────────────────────┬────────────────────────────┘
                                             ▼
                    ┌─ RERANK (yalnız ölçmə fayda göstərərsə) ────────────┐
                                             ▼
                    ┌──────────────── EVIDENCE SELECTION ─────────────────┐
                    │   həddən aşağı nəticələr atılır · budget · balans   │
                    └────────────────────────┬────────────────────────────┘
                                             ▼
                    ┌──────────────── SYNTHESIS (LLM) ────────────────────┐
                    │  kontekst DATA kimi ötürülür (system-də deyil)      │
                    └────────────────────────┬────────────────────────────┘
                                             ▼
                    ┌──────────────── CLAIM VALIDATION ───────────────────┐
                    │  hər istinad kontekstdə varmı? · dəstəklənməyən     │
                    │  iddia → çıxarılır / şərtləndirilir / etiketlənir   │
                    └────────────────────────┬────────────────────────────┘
                                             ▼
                              cavab + istinadlar + KORPUS KONTEKSTİ
```

**Provider abstraksiyası (§18):** `rag/providers/` — `LLMProvider`, `EmbeddingProvider`, `RerankProvider` protokolları; Groq/fastembed onların bir implementasiyası olur. Biznes məntiqi provayder adını bilmir.

**Sxem əlavələri (Postgres, yeni servis yox):**
- `papers`: `pmid`, `openalex_id`, `search_vector tsvector` (GENERATED), `updated_at`
- `paper_insights` — §7 çıxarışları + `evidence_type` (stated/synthesized/inferred) + mənbə chunk id-ləri
- `paper_relations` — `(from_paper, to_paper, relation, confidence, evidence)` (§15)
- `topics` / `paper_topics` — landşaft və trend üçün klasterlər (§11, §12)

---

## Phase 1 nəticələri (ölçülmüş)

Codespace, 1 596 məqaləlik korpus, `scripts/verify.sh`. **77 test keçir** (39 → 77).

### Auditin proqnozu ilə reallıq arasındakı iki fərq

| Audit nə demişdi | Reallıq | Nəticə |
|---|---|---|
| D1 bazada artıq data korrupsiyası yaratmış ola bilər | `uq_papers_doi` unikal indeksi **problemsiz quruldu** — təkrar DOI yox idi | Səhv vaxtında tutulub, təmizləmə lazım deyil |
| `sum(ingest_runs.merged)=0` → «dedup heç vaxt işə düşməyib» | **Yanlış oxu.** `merged` sütunu miqrasiyada sonradan əlavə olunub, köhnə yığımlar sıfır qalıb. Real yoxlama birləşmənin işlədiyini göstərdi | Sayğac köhnədir, mexanizm sağlamdır |

### Miqrasiya düzəlişinin faktiki təsiri

`migrate.py`-da backfill bloku `except`-in içində idi (HNSW uğurlu olanda heç vaxt işləmirdi). Çıxarıldıqdan sonra ilk icrada **7 məqaləyə çatışmayan provenans qeydi yazıldı** (1 601 → 1 608 sətir).

### Retrieval baza xətti — Phase 2 üçün müqayisə nöqtəsi

| Metrik | Dəyər |
|---|---|
| known-item MRR@10 (en) | 0.876 · Recall@10 97% |
| known-item MRR@10 (ru) | 0.794 · Recall@10 92% |
| Sahə dəqiqliyi P@10 | az 60% · en 59% · **ru 75%** |
| **Rusca sorğu → rusdilli nəticə payı** | **22%** |
| Median gecikmə | 37–67 ms (dilə görə: az 1 vektor, ru 2 vektor) |
| Korpus | 1 596 məqalə · 792 DOI-lu · 88 rusdilli |

Köhnə ölçmə ilə (korpus 1 047): en 0.900 → 0.876, ru 0.800 → 0.794. Düşüş gözləniləndir — korpus 50% böyüyəndə rəqib sənəd sayı artır, known-item tapmaq çətinləşir.

**Phase 2-nin əsas hədəfi buradan görünür:** rus dilində soruşan istifadəçi nəticələrin yalnız 22%-ini öz dilində alır.

### Mənbə strategiyası — həll olunmamış problem

Dedup mexanizmi işləyir, amma mənbələr bir-birini az kəsir:

| Mənbə | Say | Problem |
|---|---|---|
| arXiv | 793 | Yalnız 58-də DOI var → jurnal versiyası ilə bağlana bilmir |
| Crossref | 470 | — |
| DOAJ | 300 | — |
| OpenAlex | 33 | `fetch()` `lang != "ru"` olanda **boş qayıdır**; `arxiv_id` hardcoded `None` |

OpenAlex həm arXiv preprintlərini, həm jurnal nəşrlərini indeksləyən yeganə mənbədir — yəni təbii körpüdür, amma hazırda rusdilli işlərlə məhdudlaşdırılıb. Bu, §14 (fənlərarası) və §15 (əlaqələr) üçün təməldir və Phase 2 ilə paralel həll olunmalıdır.

## Phase 3 nəticələri (ölçülmüş)

### Genişləndirilmiş eval dəsti nə göstərdi

95 sorğu ilə (əvvəl 28) sahə dəqiqliyi aşağı düşdü:

| | 28 sorğu (8 sahə) | 95 sorğu (19 sahə) |
|---|---|---|
| P@10 az | 68% | **56%** |
| P@10 en | 63% | **50%** |
| P@10 ru | 62% | **51%** |
| rusdilli pay | 23% | **12%** |

**Bu, pisləşmə deyil.** Əvvəlki dəst yalnız texnologiya sahələrini ölçürdü —
korpusun ən güclü hissəsini. İndi tibb, fizika, iqtisadiyyat, psixologiya kimi
nazik təmsil olunan sahələr də ölçülür. 50% rəqəmi **əvvəllər görünməyən
reallıqdır**; köhnə 63% isə seçilmiş nümunənin nəticəsi idi.

### RAG evaluation — əsas tapıntı

İlk ölçmə (n=18, 2 sorğu Groq limitinə düşdü):

| Metrik | Dəyər |
|---|---|
| **groundedness** | **54.1%** |
| citation coverage | 30.0% |
| uydurulmuş istinadı olan cavab | 9/18 |
| istinadsız cavab | 1/18 |
| «tapılmadı» cavabı | 4/18 |
| median gecikmə | 8.8 san |

Groundedness 54% o deməkdir ki, LLM-in yazdığı istinadların təxminən yarısı
kontekstdə mövcud deyil. Doğrulama qatı onları silir (§8 işləyir), amma səbəb
araşdırıldı və **böyük hissəsi hallüsinasiya deyil**:

- İstinad etiketi kimi DOI işlədilirdi: `10.1080/10095020.2026.2712868`.
  Model bu uzunluqda sətri səhvsiz köçürə bilmir — bir simvol dəyişəndə etiket
  tanınmır və «uydurma» sayılır.
- Model bəzən onsuz da öz nömrələməsini (`[1]`) yazırdı; doğrulama isə onu
  naməlum etiket kimi oxuyurdu.

**Düzəliş:** kontekstdə qısa nömrəli etiketlər (`<doc id="1">`), serverdə geri
xəritələmə. Real identifikator cavabın `sources` siyahısında qalır, interfeysdə
isə `[1]` birbaşa həmin mənbəyə keçid olur. Keş açarı `ask:v2:`-ə keçirildi
(köhnə cavablarda DOI etiketləri var).

### Düzəlişdən sonra — ölçüldü

| Metrik | Əvvəl (DOI etiketi) | Sonra (nömrəli etiket) |
|---|---|---|
| **groundedness** | 54.1% | **91.4%** |
| citation coverage | 30.0% | **56.0%** |
| uydurulmuş istinadı olan cavab | 9/18 | **1/15** |
| median gecikmə | 8.8 san | 1.8 san |

Diaqnoz təsdiqləndi: problem hallüsinasiya deyil, **etiketin köçürülməsi** idi.

**Ölçmə qüsuru da düzəldildi:** istinad YAZMAYAN cavab (adətən «tapılmadı»)
ortalamada `0%` kimi sayılırdı və nəticəni haqsız aşağı çəkirdi. İstinad yazan
14 cavab arasında real rəqəm **97.9%**-dir. İndi groundedness yalnız istinad
yazan cavablar üzərində hesablanır, istinadsız cavabların payı isə ayrıca
metrikdir.

## 13. Prioritetləşdirilmiş yol xəritəsi

Ardıcıllıq brief-in §22-sinə uyğundur, amma **§23-ün qaydası** tətbiq olunur: təməl sabit olmadan yuxarı mərtəbə tikilmir.

### Phase 1 — Təməl ✅ (endpoint testlərindən başqa tamamlandı)
| # | İş | Vəziyyət |
|---|---|---|
| 1.1 | **D1: ziddiyyətli identifikatorlarda birləşməni qadağan et** + regression test | ✅ 16 test |
| 1.2 | **D2: `PaperIn`-ə uzunluq limitləri** | ✅ siyahılar rədd yox, kəsilir |
| 1.3 | **S1: prompt injection müdafiəsi** | ✅ kontekst `<evidence>` blokunda, 7 test |
| 1.4 | **S3: `/api/search` üçün qlobal LLM büdcəsi** | ✅ degrade, 429 yox |
| 1.5 | **Endpoint testləri** (`TestClient`) | ✅ 16 test — validasiya, 401, `SourceOut` regression-u |
| 1.6 | **D3/D5/D6/D7** | ✅ hamısı |
| 1.7 | **Benchmark baza xətti** | ✅ yuxarıda |
| 1.8 | `migrate.py`-da `except` bloku səhvi *(auditdə qaçırılmışdı)* | ✅ |

### Phase 2 — Hybrid retrieval (§5) — kod hazır, qərar ölçmədən asılıdır
| # | İş | Vəziyyət |
|---|---|---|
| 2.1 | `sv_en` / `sv_ru` tsvector sütunları + GIN indeks | ✅ GENERATED STORED |
| 2.2 | Leksik retriever (`ts_rank_cd`, `websearch_to_tsquery`) | ✅ |
| 2.3 | **Məqalə səviyyəli** retrieval — `DISTINCT ON` (W2 həlli) | ✅ |
| 2.4 | RRF ilə birləşmə | ✅ 9 test |
| 2.5 | Benchmark: NDCG@10 + `vector/lexical/hybrid` | ✅ |
| 2.6 | Başlığın vektor indeksinə daxil edilməsi | ✅ *(leakage düzəlişi, aşağıda)* |
| 2.7 | **Qərar: `RETRIEVAL_MODE`** | ✅ **`vector` qalır** — aşağıda |
| 2.8 | Rerank — yalnız 2.7 fayda göstərsə | ❌ açılmır: hibrid fayda vermədi |

#### İlk ölçmə etibarsız çıxdı — səbəb sənədləşdirilir

Leksik üsul `MRR@10 = 1.000`, `Recall = 100%` verdi. Bu, üsulun üstünlüyü deyil,
**leakage** idi: known-item testi məqalənin **başlığını** sorğu kimi verir,
`tsvector` isə başlığı `setweight(A)` ilə saxlayır — cavab açarı indeksin
içindədir. Vektor indeksində isə başlıq yox idi (yalnız abstrakt embed olunurdu).
Yəni müqayisə **üsulu deyil, indeksin məzmununu** ölçürdü.

Düzəliş məhsul üçün də doğrudur: istifadəçi başlıqla axtaranda semantik axtarış
onu tapmalıdır. İndi `chunker.embedding_text()` embed olunan mətnə başlıq əlavə
edir; saxlanılan `content` dəyişmir. `embedding_signature()` isə `model#title-v1`
qaytarır ki, təmsil dəyişəndə `reembed.py` köhnəlməni görsün.

#### `ru_share` metrikası yenidən çərçivələnir

Əvvəl bu metrik «nə qədər çox, o qədər yaxşı» kimi qoyulmuşdu — **səhv idi**.
Leksik onu 100% etdi, bu isə o deməkdir ki, rus dilində soruşan istifadəçi üçün
bütün ingiliscə korpus görünməz olur — məhsulun vədinin əksi (§2: *«retrieve
semantically relevant literature regardless of query language»*).

Sağlam hədəf **30–60% aralığıdır**: rusdilli işlər görünür, ingiliscə ədəbiyyat
bağlanmır. 22% aşağıdır, 100% nasazlıqdır.

### Phase 2 QƏRARI — ölçüldü, hibrid AÇILMADI

Korpus 1 596, n=60, 28 eval sorğusu. Known-item hər üç üsulda 1.000-ə doydu
(başlıq hər iki indeksdə olandan sonra), ona görə qərar `P@10`-a qaldı:

| Üsul | P@10 az | P@10 en | P@10 ru | ru payı | gecikmə |
|---|---|---|---|---|---|
| **vector** | **68%** | 63% | 62% | 23% | 61 ms |
| lexical | 40% | 75% | 100%* | 100%* | 5 ms |
| hybrid | 65% | 65% | 63% | 20% | 64 ms |

Hibridin təsiri: az −3%, en +2%, ru +2% → **orta +0.3%, yəni səs-küy**; gecikmə
isə artır. §5-ə görə mürəkkəblik saxlanılmır: `RETRIEVAL_MODE=vector`.

`*` Leksikin rus rəqəmləri **artefaktdır**: rusca sorğu `sv_ru`-ya gedir və
ingiliscə məqalələrdə rus kökləri olmadığı üçün yalnız rusdilli nəticə qayıda
bilər. Üstəlik rusdilli korpus elə `FIELD_TERMS_RU` terminləri ilə yığılıb, eval
sorğuları da onlara yaxındır — dairəvi ölçmə. Azərbaycancada isə leksik çökür
(68% → 40%), çünki tərcümə olunmuş sorğu dəqiq termin uyğunluğu tapmır.

**Metodoloji nəticə:** eval dəstində 28 sorğu var (18 en, 6 ru, 4 az). 4 az
sorğuda 3% fərq = sorğunun 0.12-si. **Bu ölçüdə fərqləri həll etmək üçün dəst
çox kiçikdir.** Növbəti qərarlar üçün lazım olan şey çəki tənzimləməsi deyil,
daha böyük eval dəstidir — əks halda 28 sorğuya overfit edərik.

Kod silinmir: test olunub, xərci yoxdur və sonrakı mərhələlərin təmelidir.

### Phase 3 — Evidence-grounded RAG (§8)
| # | İş | Vəziyyət |
|---|---|---|
| 3.1 | Evidence selection (mütləq + nisbi hədd) | ✅ zəif nəticələr LLM-ə getmir |
| 3.2 | Citation validation — uydurulmuş istinad silinir | ✅ 18 test |
| 3.3 | `citation_label()` tək mənbədə | ✅ kontekst və doğrulama eyni etiketi işlədir |
| 3.4 | `grounding` cavabda qaytarılır (§8, §20) | ✅ evidence_used, coverage, citations_removed |
| 3.5 | Korpus konteksti (§16) | ✅ `/api/ask` cavabında `corpus` bloku + UI-da 3 dildə qeyd |
| 3.6 | **Eval dəsti 28 → 95** | ✅ 19 sahənin hamısı; az 4 → 19, ru 6 → 19 |
| 3.7 | **RAG eval** (`scripts/rag_eval.py`) | ✅ groundedness, citation coverage, uydurma nisbəti |


### Phase 4 — Research intelligence (§7, §9, §10, §11, §12)
4.1 `paper_insights` + çıxarış · 4.2 müqayisə · 4.3 ziddiyyət təsnifatı · 4.4 landşaft · 4.5 trend təsnifatı

### Phase 5 — Cross-disciplinary (§14) · Phase 6 — Research gaps (§13)

### Ayrıca (paralel gedə bilər)
- **Mənbə genişlənməsi:** Europe PMC (tibb/biologiya) — ən yüksək dəyərli əlavə; `philosophy` sahəsinin `fields.py`-a əlavəsi (§1 tələb edir, hazırda yoxdur)
- **D4:** ingest-in fon işinə köçürülməsi

---

## Bu auditin nəticəsi — bir cümlə

PaperMind-ın **təməli gözlədiyimdən sağlamdır** (kimlik, provenans, mənbə abstraksiyası, ölçmə disiplini), amma **retrieval bir ayaq üstündədir** (yalnız vektor) və **RAG qatı sübut baxımından yoxlanılmır** (istinad doğruluğu, injection müdafiəsi). Ona görə Phase 1-də yeni funksiya yox, **korrektlik və təhlükəsizlik** düzəlişləri gedir — çünki §24-ün tələb etdiyi «ciddi platforma» hissi funksiya sayından yox, cavabın etibarlılığından gəlir.
