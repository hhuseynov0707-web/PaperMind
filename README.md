# PaperMind — Scientific Intelligence Platform

> **Search less. Understand more.**
>
> *English version: [README.en.md](README.en.md)*

**Çoxmənbəli elmi axtarış və trend analitikası.** Sistem hər gün dörd akademik mənbədən — **arXiv, Crossref, DOAJ və OpenAlex** — yeni məqalələri avtomatik yığır, təkrarları birləşdirir, onların üzərində semantik axtarış, mənbəli sual-cavab (RAG) və trend analitikası təqdim edir. Korpus **ingiliscə və rusca** məqalələri əhatə edir. Hər şey lokal Docker mühitində işləyir.

Məhsul dörd əsas imkan üzərində qurulub: **Discover** (kəşf), **Search** (məna üzrə axtarış), **Understand** (mənbəli AI cavabı), **Track** (trend analitikası).

## Nə edir?

- 💬 **Söhbət, tək sual yox:** cavabın altından davam edirsən — «bəs ikincisi?», «bunu sadə izah et». Sistem əvvəlki növbələri yadda saxlayır; qısa follow-up sualda axtarış üçün əvvəlki kontekst də işlədilir
- 🤖 **Sual-cavab (RAG):** sual verirsən → sistem öz bazasından ən uyğun abstraktları tapır (pgvector cosine axtarışı) → Groq LLM mənbəli cavab qaytarır. Uyğun material zəifdirsə **«tapılmadı» deyib dayanmır** — ən yaxın işləri göstərir və məhdudiyyəti açıq deyir
- 🔎 **Semantik axtarış:** açar söz yox, *məna* üzrə axtarış
- 📈 **Trend analitikası:** həftələr üzrə **5 fənn qrupunun** paylanması, ən aktiv müəlliflər (Redis-də keşlənir)
- 🔄 **Avtomatik yenilənmə:** n8n hər gün üç dəfə yığım aparır — arXiv (09:00), Crossref+DOAJ (10:30), rusdilli mənbələr (11:30). Hamısında retry + error handling
- 📰 **Həftəlik AI icmalı:** n8n bazar günləri həftənin statistikasını Groq-a verib icmal yazdırır
- 🌐 **3 dilli interfeys (AZ / RU / EN)** və **həqiqi çoxdilli axtarış:** çoxdilli embedding modeli sayəsində rusca sorğu ingiliscə məqalələri də tapır (RU↔EN oxşarlıq testdə 0.79). Cavab həmişə sənin dilində qayıdır — **diakritikasız yazsan da** («mene oxumaqa ne vere bilersen» → azərbaycanca cavab), çünki dil funksiya sözləri və şəkilçilərlə tanınır, təkcə hərflərlə yox
- 🇷🇺 **Rusdilli korpus:** rus interfeysini seçən istifadəçi öz dilində məqalələr də tapır. Mənbənin dil etiketinə güvənilmir — mətnin **öz əlifbası** yoxlanılır, çünki rus jurnalları çox vaxt ingiliscə abstrakt dərc edir
- 🗂 **19 elm sahəsi, 5 fənn qrupu:** texnologiya, təbiət elmləri (fizika, biologiya, kimya, astronomiya, Yer elmləri), formal elmlər (riyaziyyat, statistika), tibb və sağlamlıq, sosial elmlər — yan paneldən sahə seçəndə axtarış, sual-cavab və vərəqlənən dəst yalnız orada işləyir
- 📖 **Vərəqlənən məqalə dəsti:** son həftənin məqalələri bir-bir göstərilir; ox düymələri, klaviatura və ya sürüşdürmə ilə vərəqləyirsən, xoşuna gələni açırsan
- ✨ **"Discover" paneli:** bazadan təsadüfi seçmə məqalələr yanda sakit şəkildə fırlanır (15 saniyəlik interval, kursor üstünə gələndə dayanır)
- 🩺 **Sistem statusu:** Postgres, pgvector, Redis, Groq açarı və son ingest — hamısı `/health/services`-dən real yoxlanır, heç bir status fərz edilmir
- 🧠 **Məqalə intellekti:** hər məqalədən problem, metodologiya, dataset, nəticə, məhdudiyyət çıxarılır — və hər biri **sübut tipi** ilə işarələnir: *məqalədə yazılıb* / *sintez* / *AI nəticəsi*. Yalnız abstrakt indeksləndiyi üçün bu fərq gizlədilmir
- ⚖️ **Müqayisə və ziddiyyət:** iki-beş məqalə 7 ox üzrə müqayisə olunur; ziddiyyət isə əks sözlərdən yox, **şəraitdən** çıxarılır (fərqli populyasiya/metrik = birbaşa ziddiyyət deyil). Sistem heç vaxt hansının doğru olduğunu demir
- 🗺 **Tədqiqat landşaftı:** mövzu üzrə klasterlər, aktiv müəlliflər, fənlərarası əlaqələr — hamısı real indekslənmiş məqalələrdən sayılır, nümayəndə məqalələrlə birlikdə
- 📊 **Trend təsnifatı:** hər fənn qrupu üçün *yeni yaranır / artır / sabit / azalır / data kifayət etmir* — və **səbəbi**. LLM yox, deterministik arifmetika
- 🔍 **Tədqiqat boşluqları:** təkrarlanan məhdudiyyətlərdən çıxarılır və açıq şəkildə «AI nəticəsi» kimi etiketlənir. Sistem heç vaxt «bu mövzuda tədqiqat yoxdur» demir — yalnız «indeksdə məhdud sübut var»
- 🎯 **Sorğunu anlayır (§6):** «transformer ilə RNN arasındakı fərq» → müqayisə, «hansı boşluqlar var» → boşluq analizi. `author:"Yann LeCun"` və «son 3 il» filtr kimi işlədilir, axtarış mətnindən isə çıxarılır. LLM işlədilmir — sabit ifadə nümunələri, 3 dildə, diakritikasız yazılış da tanınır
- 🕸 **Məqalələr arası əlaqələr:** sitat, ortaq müəllif, oxşarlıq — hər biri **etibarlılıq dərəcəsi ilə**. Sitat xarici reyestrdən gələn faktdır (1.0), oxşarlıq isə ölçmədir (~0.6); interfeys onları qarışdırmır
- 🔗 **Çoxmənbəli yığım + deduplikasiya:** arXiv (preprint), Crossref (nəşr olunmuş), DOAJ (açıq giriş), OpenAlex (çoxdilli). Eyni iş bir neçə mənbədə varsa **bir dəfə** göstərilir, mənbələrin hamısı isə qeyd olunur

## Arxitektura

```
                 ┌──────────────────── LOKAL DOCKER MÜHİTİ ────────────────────┐
                 │                                                             │
 İstifadəçi ─────┼─▶ Frontend ──▶ FastAPI ────▶ PostgreSQL 16 + pgvector       │
 (brauzer)       │   (static)      │  │          (cədvəllər + vektor axtarış)  │
                 │                 │  └────────▶ Redis 7 (cache)               │
                 │                 │                                           │
                 │                 └───────────────────▶ Groq LLM API ─────────┼──▶ internet
                 │                                                             │
                 │   n8n ──(3 gündəlik cron)                                   │
                 │    │                                                        │
                 │    └──▶ FastAPI /api/ingest/pull ──┬──▶ arXiv ──────────────┼──▶ internet
                 │             │                      ├──▶ Crossref            │
                 │             │                      ├──▶ DOAJ                │
                 │             │                      └──▶ OpenAlex (RU)       │
                 │             ↓                                               │
                 │        dedup (DOI / arXiv ID / başlıq)                      │
                 │             ↓                                               │
                 │        chunking + çoxdilli embedding ──▶ DB                 │
                 └─────────────────────────────────────────────────────────────┘
```

| Komponent | Texnologiya |
|---|---|
| Backend API | FastAPI + Pydantic |
| Data qatı | PostgreSQL 16 + pgvector, SQLAlchemy 2.0 |
| Cache | Redis 7 (analitika + LLM cavabları + tərcümələr) |
| Embeddings | fastembed — `paraphrase-multilingual-MiniLM-L12-v2` (384d, **çoxdilli**, lokal, pulsuz) |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Mənbələr | arXiv · Crossref · DOAJ · OpenAlex |
| Avtomatlaşdırma | n8n — 5 workflow (arXiv, çoxmənbəli, rusdilli, həftəlik icmal, error handler) |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |
| Provider-lər | LLM / embedding / rerank `.env`-dən seçilir (§18) — biznes məntiqi adı bilmir |

## Qurulum

**Tələblər:** Docker Desktop + [Groq API açarı](https://console.groq.com/keys) (pulsuz).

> **Kompüterin zəifdirsə** (8 GB RAM və ya az): layihədə [.devcontainer](.devcontainer/devcontainer.json) var — GitHub-da **Code → Codespaces → Create codespace** ilə brauzerdə 8 GB-lıq mühit açılır və bütün stack orada işləyir. Aylıq 60 saat pulsuzdur.
>
> Lokal işləmək istəyirsənsə: `docker compose up -d` **n8n-i başlatmır** (o, ~400 MB tutur və yalnız cron orkestrasiyası edir). Qalan üç servis birlikdə ~1.4 GB-dır. Avtomatlaşdırma lazım olanda:
> ```bash
> docker compose --profile automation up -d
> ```
> Windows-da WSL2 həddini `%USERPROFILE%\.wslconfig`-də təyin et (`memory=2600MB`), və Oracle/Postgres kimi lazımsız avtomatik xidmətləri `Manual`-a keçir — onlar 8 GB-lıq maşında Docker-ə yer qoymur.

```bash
# 1. .env faylını doldur (GROQ_API_KEY sətrini)
cp .env.example .env

# 2. Bütün mühiti qaldır (ilk dəfə 3-5 dəq çəkə bilər)
docker compose up -d --build

# 3. İlk datanı yüklə — bütün mənbələrdən (~15-20 dəq, mənbələrin rate limit-i üzündən)
docker compose exec backend python scripts/backfill_multi.py --days 14 --limit 80

# Təbiət və formal elmlər (arXiv-də güclü təmsil olunur):
docker compose exec backend python scripts/backfill_multi.py --sources arxiv \
  --fields physics,astronomy,biology,math,chemistry,earth,statistics,economics --days 14 --limit 50

# Tibb və psixologiya (arXiv-də yoxdur, mətn sorğusu ilə):
docker compose exec backend python scripts/backfill_multi.py --sources crossref,doaj \
  --fields medicine,psychology --days 30 --limit 40

# Rusdilli korpus:
docker compose exec backend python scripts/backfill_multi.py --sources openalex,doaj --lang ru --days 30

# 4. Məqalə çıxarışları (landşaft və boşluq analizi bunun üzərində işləyir).
#    Bərpa olunandır: kəsilsə qaldığı yerdən davam edir.
docker compose exec -d backend sh -c "python scripts/extract_insights.py > /tmp/ins.log 2>&1"
docker compose exec backend tail -5 /tmp/ins.log
```

> **Embedding modelini dəyişsən** bütün vektorları yenidən hesablamaq lazımdır — fərqli
> modellərin vektorları müqayisə oluna bilməz. Skript bərpa olunandır (kəsilsə davam edir):
> ```bash
> docker compose exec -d backend sh -c "python scripts/reembed.py > /tmp/reembed.log 2>&1"
> docker compose exec backend tail -3 /tmp/reembed.log
> ```

Sonra:
- **Dashboard:** http://localhost:8000
- **API sənədləri (Swagger):** http://localhost:8000/docs
- **n8n:** http://localhost:5679
- **DataGrip:** `localhost:5433`, db/user/parol: `elmradari` *(layihənin ilk adından qalıb — baza həcmi ilə birlikdə saxlanılıb ki, mövcud volume itməsin)*

### n8n workflow-larının qurulması (bir dəfəlik)

```bash
# 1. Beş workflow-u import et
docker compose exec n8n n8n import:workflow --separate --input=/workflows

# 2. Dördünü aktivləşdir (W3 error handler-dir, aktiv olmamalıdır)
for w in W1dailyIngest001 W2weeklyDigest01 W4multiSourceIng W5russianIngest; do
  docker compose exec -T n8n n8n update:workflow --id=$w --active=true
done
docker compose restart n8n

# 3. Yoxla
docker compose exec -T n8n n8n list:workflow --active=true
```

Workflow fayllarında **sabit ID** və `errorWorkflow` bağlantısı var, ona görə interfeysdə əl ilə heç nə seçmək lazım deyil. `X-API-Key` başlığı da `.env`-dəki `ADMIN_API_KEY`-dən avtomatik oxunur.

İnterfeysi görmək istəsən: http://localhost:5679 (ilk dəfə owner hesabı yaradılır). `W1`-də **Execute Workflow** basıb yoxlaya bilərsən — dashboard-da "Son ingest-lər"də yeni sətir görünəcək.

> **Reverse proxy arxasında** (Codespaces, Caddy) n8n interfeysi «connection lost» verə bilər — compose-da `N8N_PUSH_BACKEND=sse` məhz bunun üçündür. Aktivləşdirmə onsuz da CLI ilə işləyir.

## Redis cache-in fərqini görmək

```bash
# Birinci çağırış — DB-dən hesablanır (MISS)
curl -i "http://localhost:8000/api/analytics/trends?weeks=8"

# İkinci çağırış — Redis-dən gəlir (HIT, dəfələrlə sürətli)
curl -i "http://localhost:8000/api/analytics/trends?weeks=8"
```

`X-Cache: MISS` → `X-Cache: HIT` header-inə bax. Dashboard-dakı trend kartında da göstərilir. Eyni sual iki dəfə veriləndə `/api/ask` da eyni cür işləyir: birinci dəfə ~2-5 saniyə (Groq), ikinci dəfə <100 ms (Redis) — cavabda `from_cache` və `latency_ms` sahələri var. İngest-dən sonra `analytics:*` açarları avtomatik silinir (invalidasiya).

## API xülasəsi

| Metod | Yol | Nə edir |
|---|---|---|
| POST | `/api/ingest` | n8n/backfill batch göndərir; dedup + chunk + embed |
| GET | `/api/papers` | Filter + səhifələmə ilə siyahı |
| GET | `/api/papers/featured` | "Kəşf et" paneli üçün təsadüfi seçmələr |
| POST | `/api/ingest/pull` | Server özü mənbədən çəkir (`source`, `lang`, `fields`, `days`) |
| GET | `/api/fields` | 19 sahə + qrup + say + kateqoriya siyahısı (keşli) |
| GET | `/api/papers?field=&days=` | Sahə üzrə süzülmüş siyahı (vərəqlənən dəst bunu işlədir) |
| GET | `/health` · `/health/services` | Sadə health · Postgres/pgvector/Redis/Groq real yoxlaması |
| GET | `/api/search?q=&field=` | Semantik axtarış (pgvector), sahə üzrə daralda bilər |
| POST | `/api/ask` | RAG sual-cavab; `history` ilə söhbət davam edir, `field` ilə daralda bilər |
| GET | `/api/analytics/trends` | Həftəlik trend (keşli, X-Cache header) |
| GET | `/api/analytics/top-authors` | Ən aktiv müəlliflər (keşli) |
| GET | `/api/analytics/summary` | Ümumi statistika (keşli) |
| GET | `/api/papers/{id}/insights` | Məqalə çıxarışı + sübut tipləri (§7) |
| POST | `/api/compare` | 2–5 məqaləni 7 ox üzrə müqayisə (§9) |
| POST | `/api/conflicts` | Ziddiyyət təsnifatı: birbaşa / şərti / zahiri / yox (§10) |
| GET | `/api/landscape?q=` | Mövzu üzrə klasterlər və müəlliflər (§11) |
| GET | `/api/analytics/trend-classes` | Trend təsnifatı + səbəb (§12) |
| GET | `/api/gaps?q=` | Potensial tədqiqat imkanları (§13) |
| GET | `/api/cross-disciplinary?q=` | Sahələr arası əlaqələr (§14) |
| GET | `/api/papers/{id}/relations` | Məqalənin əlaqələri, etibarlılıqla (§15) |
| POST | `/api/digests` · GET `/api/digests/latest` | Həftəlik LLM icmalı |
| POST | `/api/logs/error` · GET `/api/logs/*` | n8n xəta logları, ingest tarixçəsi, son suallar |

## Mənbələr və deduplikasiya

| Mənbə | Nə verir | Qeyd |
|---|---|---|
| **arXiv** | Preprintlər — 76 kateqoriya (`cs.*`, `physics.*`, `math.*`, `q-bio.*`, `econ.*`, `stat.*`…) | Sahə **real təsnifatdan** çıxarılır |
| **Crossref** | Nəşr olunmuş jurnal məqalələri, DOI reyestri | Abstrakt JATS XML-dən təmizlənir |
| **DOAJ** | Açıq girişli, resenziyadan keçmiş məqalələr | Həm ingiliscə, həm rusca sorğu dəstəkləyir |
| **OpenAlex** | Çoxdilli akademik reyestr (240M+ iş) | **Rusdilli korpusun əsas mənbəyi** |

Yalnız **abstraktı olan** (≥200 simvol) qeydlər qəbul edilir — abstraktsız məqalə RAG üçün dəyərsizdir.

**Dil təyini mənbəyə görə deyil, mətnə görə aparılır.** Rus jurnalları çox vaxt metadatanı ikidilli verir və indekslərdə ingiliscə abstrakt qeydə alınır; OpenAlex isə bəzi ingiliscə işləri səhvən `ru` işarələyir. Ona görə [common.py](backend/app/sources/common.py)-dəki `detect_language()` kiril/latın hərflərinin nisbətinə baxır və yalnız həqiqətən istənilən dildə olan mətnləri qəbul edir.

> **Sınanmış, amma seçilməyən mənbə:** CyberLeninka (Rusiyanın ən böyük açıq elm kitabxanası) OAI-PMH interfeysi verir, lakin `dc:description` sahəsi boş qayıdır — yəni abstrakt yoxdur. Yalnız başlıqla RAG mümkün olmadığı üçün istifadə edilmədi.

### Eyni məqalə bir neçə mənbədə olanda

Üç açar, güclüdən zəifə doğru ([common.py](backend/app/sources/common.py)):

1. **DOI** — normallaşdırılır (`https://doi.org/` prefiksi atılır, kiçik hərf)
2. **arXiv ID** — versiya atılır (`2608.01234v2` → `2608.01234`)
3. **Başlıq açarı** — diakritika, durğu işarəsi və reqistrdən asılı olmayan SHA-1 hash

Uyğunluq tapılanda **yeni sətir yaradılmır**: mövcud sətrə `paper_sources`-da yeni mənbə bağlanır, çatışmayan sahələr (DOI, PDF linki, sahə açarları) digər mənbədən **zənginləşdirilir**. İnterfeysdə nəticə bir dəfə görünür, üzərində isə bütün mənbələr nişan kimi göstərilir (`Crossref · DOAJ · ⧉ 2 mənbə`).

Deduplikasiya həm **partiya daxilində**, həm də **bazaya qarşı** işləyir — yəni eyni iş iki mənbədən eyni anda gəlsə də təkrarlanmır.

### Yığım necə işə düşür

```bash
# əl ilə, bütün mənbələrdən
docker compose exec backend python scripts/backfill_multi.py --days 14 --limit 80

# tək mənbə
docker compose exec backend python scripts/backfill_multi.py --sources crossref --days 7
```

n8n tərəfdə üç yığım workflow-u var:

| Workflow | Vaxt | Nə edir |
|---|---|---|
| **W1** – daily_ingest | 09:00 | arXiv (XML→JSON transformasiyası n8n-də) |
| **W4** – multi_source_ingest | 10:30 | Crossref + DOAJ → `/api/ingest/pull` |
| **W5** – russian_ingest | 11:30 | OpenAlex + DOAJ, `lang=ru` |

Hər mənbə ayrıca item olduğu üçün biri xəta versə digəri dayanmır (`onError: continue`); hamısının Error Workflow-u **W3**-dür. Yazma endpoint-ləri açar tələb etdiyi üçün workflow-lar `X-API-Key` başlığını `{{ $env.ADMIN_API_KEY }}`-dən oxuyur.

> `CONTACT_EMAIL` dəyişənini `.env`-də doldursan, Crossref «nəzakətli hovuz»una düşürsən (daha sabit limitlər). Boş qalsa da işləyir.

## Sahələr necə işləyir?

[fields.py](backend/app/fields.py) iki səviyyəli taksonomiya saxlayır — **5 fənn qrupu, 19 sahə**:

| Qrup | Sahələr |
|---|---|
| Texnologiya | süni intellekt · kompüter görməsi · kibertəhlükəsizlik · robototexnika · proqram mühəndisliyi · data sistemləri · şəbəkələr · HCI |
| Təbiət elmləri | fizika · astronomiya · kimya · biologiya · Yer elmləri |
| Formal elmlər | riyaziyyat · statistika |
| Tibb və sağlamlıq | tibb · nevrologiya |
| Sosial elmlər | iqtisadiyyat · psixologiya |

76 arXiv kateqoriyası sahələrə xəritələnib (`quant-ph` → fizika, `q-bio.*` → biologiya, `econ.*` → iqtisadiyyat). arXiv-də qarşılığı olmayan sahələr (tibb, psixologiya) boş siyahı ilə qalır və yalnız mətn sorğusu ilə yığılır.

Süzgəc `field_keys` massivi üzərindən işləyir — o, **bütün mənbələr** üçün təyin olunur (`primary_category` isə yalnız arXiv-də doludur). arXiv məqalələrində sahə **real təsnifatdan** çıxarılır, ona görə cross-listing nəzərə alınır: əsas kateqoriyası `cs.LG` olan, amma `cs.CR`-ə də əlavə edilmiş məqalə kibertəhlükəsizlik axtarışında görünür.

Nümunə: eyni `attack detection` sorğusu kibertəhlükəsizlik sahəsində intrusion detection məqalələri, robototexnikada isə robot hijacking məqalələri qaytarır.

arXiv-in xam kodları (`cs.LG`, `cs.CV`, `quant-ph`...) interfeysdə oxunaqlı adlara çevrilir; kodun özü tooltip-də qalır ki, mütəxəssis üçün dəqiqlik itməsin.

> **Yeni sahə əlavə etmək:** `fields.py`-a bir sətir, `sources/__init__.py`-a ingiliscə terminlər, `openalex.py`-a rusca qarşılıqları, `app.js`-ə üç dildə ad. Retrieval, süzgəc və analitika kodu dəyişmir.

## Çoxdilli axtarış necə işləyir?

İki müstəqil mexanizm birlikdə işləyir:

**1. Çoxdilli embedding modeli (əsas).** `paraphrase-multilingual-MiniLM-L12-v2` 50+ dili eyni vektor fəzasına yerləşdirir, ona görə rusca sorğu birbaşa ingiliscə mətnlə uyğunlaşır — tərcüməyə ehtiyac qalmadan. Ölçülmüş nəticələr:

| Müqayisə | Oxşarlıq |
|---|---|
| «машинное обучение для обнаружения аномалий» ↔ *machine learning for anomaly detection* | **0.79** |
| eyni sorğu ↔ başqa mövzuda rusca mətn | 0.52 |
| eyni sorğu ↔ tamam əlaqəsiz mətn («çörək bişirmək») | −0.05 |

**2. Sorğu tərcüməsi (köməkçi).** Dil aşkarlanır ([translator.py](backend/app/rag/translator.py)) və az/ru sorğu Groq ilə ingiliscəyə də çevrilir; tərcümələr Redis-də 7 gün keşlənir. Bu, xüsusilə Azərbaycan dili üçün faydalıdır — model onu rus və ingilis dili qədər güclü dəstəkləmir. UI tərcüməni şəffaf göstərir: *"🔎 İngiliscə axtarıldı: ..."*

**Cavabın dili** LLM-in təxmininə buraxılmır: aşkarlanmış dil system prompt-a **məcburi direktiv** kimi yazılır ("CAVABIN DİLİ MÜTLƏQ BUDUR: ...").

Qeyd: diakritiksiz Azərbaycan mətni üçün birmənalı söz siyahısı işlədilir ("nedir", "ucun", "hansilardir"...) — siyahıya düşməyən nadir cümlələr ingiliscə sayıla bilər.

> **Model dəyişdirsən:** vektorların ölçüsü eyni qalsa belə (384), fərqli modellərin vektorları müqayisə oluna bilməz. `scripts/reembed.py` mütləq işlədilməlidir — hər chunk-da hansı modellə hesablandığı (`embedding_model`) saxlanıldığı üçün proses kəsilsə qaldığı yerdən davam edir.

## Keyfiyyət: testlər və benchmark

Sistemin ən kritik funksiyaları (dedup açarları, dil təyini, chunking) **heç vaxt xəta atmır** — səhv işləsələr sadəcə yanlış nəticə qaytarırlar. Ona görə onlar testlə qorunur:

```bash
docker compose exec backend python -m pytest tests/ -q
```

**230 test:** DOI/arXiv/başlıq normallaşdırması və dedup ekvivalentlikləri, əlifbaya görə dil təyini (qarışıq mətn daxil), JATS abstrakt təmizlənməsi, chunk sərhədləri və üst-üstə düşmə, və uçdan-uca yoxlama — eyni iş üç mənbədən gələndə bir sətir, üç provenans qeydi.

### Retrieval benchmark

«Axtarış yaxşı işləyir» gözlə təsdiqlənə bilməz. Ölçmə dörd şeyi hesablayır: **known-item MRR və NDCG** (məqalənin başlığı sorğu kimi verilir), **sahə dəqiqliyi** (95 sorğu, 19 sahə, 3 dil) və **çarpaz dilli əhatə**.

```bash
docker compose exec backend python scripts/benchmark.py                    # cari vəziyyət
docker compose exec backend python scripts/benchmark.py --compare-retrieval # vector / lexical / hybrid
docker compose exec backend python scripts/rag_eval.py                     # cavabın sübutla əlaqəsi
```

Cari nəticələr (n=60, korpus 1 596 məqalə, 95 eval sorğusu):

| | İngiliscə | Rusca | Azərbaycanca |
|---|---|---|---|
| known-item MRR@10 | 1.000 | 0.969 | — |
| NDCG@10 | 1.000 | 0.977 | — |
| Recall@10 | 100% | 100% | — |
| Sahə dəqiqliyi P@10 | 50% | 51% | 56% |
| Median gecikmə | | 62 ms | |

**RAG keyfiyyəti** (§20, `rag_eval.py`):

| Metrik | Dəyər |
|---|---|
| groundedness (istinadların düzgünlüyü) | **91.4%** (əvvəl 54.1%) |
| citation coverage | 56.0% |
| uydurulmuş istinadı olan cavab | 1/15 |

> **P@10 rəqəmi niyə 61%-dən 50%-ə düşdü?** Eval dəsti 28 sorğudan (yalnız 8
> texnologiya sahəsi) 95 sorğuya (19 sahə) genişləndi. Köhnə rəqəm korpusun ən
> güclü hissəsini ölçürdü; yeni rəqəm tibb, fizika, iqtisadiyyat kimi nazik
> təmsil olunan sahələri də əhatə edir. Bu, pisləşmə deyil — əvvəllər
> görünməyən reallıqdır.

**Retrieval strategiyası ölçmə ilə seçilib**, fərziyyə ilə deyil ([translator.py](backend/app/rag/translator.py)):

| Dil | Əsas vektor | Əlavə | Səbəb (ölçülmüş) |
|---|---|---|---|
| `en` | orijinal | — | tərcümə tətbiq olunmur |
| `ru` | orijinal | tərcümə | orijinal sahə dəqiqliyini 63%→72%, tərcümə MRR-i 0.70→0.80 qaldırır |
| `az` | tərcümə | — | azərbaycanca vektor səs-küy əlavə edir: tək tərcümə 60%, orijinal qoşulanda 52% |

Benchmark produksiya funksiyasının **özünü** çağırır — ölçülən davranışla istifadəçinin gördüyü davranış uzaqlaşa bilməz.

> Ölçmə iki gizli problemi üzə çıxardı: rusca sorğuların rusdilli korpusu tamamilə görməməsi, və benchmark-ın özünün təkrarlanmaması (`ORDER BY` olmadan eyni konfiqurasiya 0.885 və 0.773 verirdi). Hər ikisi gözlə görünməzdi.

## Prompt dizaynı

System prompt [backend/app/rag/llm.py](backend/app/rag/llm.py)-dədir. Əsas qaydalar: yalnız verilmiş kontekstə əsaslan, hər iddiaya mənbə istinadı, kontekstdə cavab yoxdursa **açıq etiraf et** (hallüsinasiya qadağası), cavab dili = sual dili.

İstinad etiketi `arxiv_id → doi → id:N` ardıcıllığı ilə seçilir. Bu vacibdir: korpusun yarıdan çoxu arXiv-dən kənardır, yalnız `arxiv_id`-yə güvənsək o məqalələr kontekstə `[None]` kimi düşür və LLM eyni etiketi bir neçə fərqli işə yapışdırır.

Yoxlanması: bazada olmayan mövzu soruş (məs. "aşpazlıq resepti") — sistem "tapılmadı" deməlidir, uydurmamalıdır.

## İctimai rejim və deploy

Lokal mühitdə bütün endpoint-lər açıqdır. Portu internetə açmazdan **əvvəl** `.env`-də ictimai rejimi qoşmaq lazımdır — əks halda hər kəs bazaya yaza və Groq balansını yandıra bilər:

```bash
PUBLIC_MODE=true
ADMIN_API_KEY=<uzun təsadüfi sətir>   # openssl rand -hex 32
TRUST_PROXY=true                      # yalnız Caddy/nginx arxasındasa
```

Bu rejimdə [security.py](backend/app/security.py):

| Qoruma | Dəyər | Harada |
|---|---|---|
| Yazma endpoint-ləri (`/api/ingest*`, `/api/digests`, `/api/logs/error`) | `X-API-Key` tələb olunur | `require_admin_key()` |
| LLM sualı | 20 / saat / IP | `ASK_RATE_LIMIT` |
| Günlük LLM tavanı (hamı üçün) | 500 | `ASK_DAILY_BUDGET` |
| Semantik axtarış | 120 / saat / IP | `SEARCH_RATE_LIMIT` |

Limit aşılanda `429` qayıdır və interfeys onu üç dildə ayrıca mesajla göstərir (ümumi «xəta baş verdi» yox).

Serverə çıxarma [DEPLOY.md](DEPLOY.md)-də addım-addım yazılıb: `scripts/server-setup.sh` (Docker + firewall + swap), `scripts/preflight.sh` (13 yoxlama — açar boşdursa, port açıqdırsa xəbərdarlıq verir), sonra `docker-compose.prod.yml` + `Caddyfile` ilə avtomatik HTTPS. **n8n prod-da `expose` ilə qalır, `ports` ilə yox** — admin panelinə yalnız SSH tuneli ilə girilir. `scripts/backup.sh` gündəlik `pg_dump` alır.

## Tez-tez çıxan problemlər

| Problem | Həll |
|---|---|
| `5432 portu məşğuldur` | Bizim compose onsuz da `5433` istifadə edir — DataGrip-də 5433 yaz |
| n8n niyə `5679`-da? | `5678`-i başqa (məs. kursdan qalan) n8n tutubsa konflikt olmasın deyə |
| İlk `/api/search` sorğusu yavaşdır | Normaldır: çoxdilli embedding modeli (~220 MB) ilk dəfə yüklənir, `model_cache` volume-da qalır |
| Axtarış nəticələri mənasızdır | Model dəyişdirilib, amma `reembed.py` işlədilməyib — vektorlar qarışıqdır |
| Docker 8 GB RAM-da çökür | `.wslconfig`-də `memory=3500MB` təyin et; ağır işləri (reembed) tək başına işlət |
| `/api/ask` → 503 | `.env`-də `GROQ_API_KEY` boşdur; doldur və `docker compose restart backend n8n` |
| n8n-dən backend-ə çatmır | URL `http://backend:8000` olmalıdır (`localhost` yox — docker network qaydası) |
| Backfill boş qayıdır | arXiv 3 san/sorğu limitini yoxla; internet bağlantısını yoxla |
| Backfill `401 Unauthorized` verir | `PUBLIC_MODE=true`-dur, amma `ADMIN_API_KEY` təyin olunmayıb — skript açarı mühitdən oxuyur |
| Trend paneli köhnə data göstərir | Analitika 6 saat keşlənir: `docker compose exec -T backend python -c "from app import cache; cache.invalidate('analytics:*')"` |
| n8n interfeysi «connection lost» | Reverse proxy arxasında WebSocket qırılır — compose-da `N8N_PUSH_BACKEND=sse` var; workflow-ları CLI ilə də aktivləşdirmək olar |

## 3 dəqiqəlik demo ssenarisi

1. **(0:00)** `docker compose ps` — 4 servis healthy. Brauzerdə dashboard: məqalə sayı, son yeniləmə görünür.
2. **(0:30)** Semantik axtarış: *"hallucination detection in LLMs"* — nəticələr oxşarlıq faizi ilə gəlir. Qeyd et: bu, keyword axtarışı deyil, məna axtarışıdır. Sonra yan paneldən **Fizika** seç və eyni sorğunu təkrarla — nəticələr tamam dəyişir.
3. **(1:00)** Sual ver: *"RAG sistemlərində retrieval-ı necə yaxşılaşdırırlar?"* — mənbəli cavab, `[arxiv_id]` istinadları. **Eyni sualı təkrar ver** → ⚡ cache badge, latency 2-5 saniyədən <100 ms-ə düşür. Bu, Redis-in canlı sübutudur.
4. **(1:30)** **RU** düyməsi → rusca sorğu ver (*"защита информации и криптография"*) — nəticələrdə həm rusca, həm ingiliscə məqalələr gəlir. Çoxdilli modelin canlı sübutudur.
5. **(2:00)** Trend qrafiki (5 fənn qrupu) + `curl -i` ilə `X-Cache: MISS→HIT` nümayişi. Yanında benchmark rəqəmlərini göstər: `docker compose exec backend python scripts/benchmark.py`
6. **(2:30)** n8n: `W1 - daily_ingest`-i əl ilə Execute et → dashboard-da "Son ingest-lər" yenilənir. Sonra **backend-i söndür** (`docker compose stop backend`), W1-i yenidən işlət → retry-lar işləyir, sonda W3 xətanı DB-yə yazır → backend-i qaldır, dashboard-da qırmızı xəta sətrini göstər. *(Bu hissə error handling-in canlı sübutudur.)*
7. **(3:00)** `/docs` səhifəsi: bütün Pydantic modelləri.

## Qovluq strukturu

```
papermind/
├── docker-compose.yml          # lokal: postgres(pgvector) + redis + n8n + backend
├── docker-compose.prod.yml     # ictimai deploy: + Caddy(HTTPS), yalnız 80/443 açıq
├── Caddyfile                   # avtomatik Let's Encrypt
├── .devcontainer/              # GitHub Codespaces (zəif kompüter üçün)
├── .env.example
├── DEPLOY.md                   # serverə çıxarma təlimatı (Oracle/VPS/tunel)
├── scripts/
│   ├── server-setup.sh         # Docker + firewall + swap (bir əmrlə)
│   ├── preflight.sh            # deploy-dan əvvəl 13 yoxlama
│   └── backup.sh               # gündəlik baza nüsxəsi
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── eval/queries.json       # benchmark sorğu dəsti (28 sorğu, 3 dil)
│   ├── tests/                  # 230 test: dedup, dil, sübut, ziddiyyət, endpoint, provider
│   ├── scripts/
│   │   ├── backfill.py         # yalnız arXiv (köhnə, sadə)
│   │   ├── backfill_multi.py   # bütün mənbələr + dil seçimi (--lang ru)
│   │   ├── benchmark.py        # retrieval: MRR, NDCG, P@10 + üsul müqayisəsi
│   │   ├── rag_eval.py         # §20: groundedness, istinad doğruluğu
│   │   ├── extract_insights.py # §7 çıxarışı (bərpa olunan)
│   │   ├── build_relations.py  # §15 əlaqələri (bərpa olunan)
│   │   ├── verify_dedup.py     # dedup-un real data ilə yoxlanması
│   │   └── reembed.py          # təmsil dəyişəndə vektorların bərpası
│   └── app/
│       ├── main.py             # FastAPI + lifespan + /health/services
│       ├── config.py           # pydantic-settings (DB URL SQLAlchemy ilə qurulur)
│       ├── migrate.py          # idempotent sxem miqrasiyası (Alembic-siz)
│       ├── security.py         # API açarı + IP limitləri (ictimai rejim)
│       ├── database.py         # SQLAlchemy engine/session
│       ├── models.py           # 11 cədvəl (papers, chunks+vector, paper_sources, M2M, loglar)
│       ├── schemas.py          # Pydantic modelləri
│       ├── crud.py             # dedup upsert, analitika SQL (trendlər fənn qrupları üzrə)
│       ├── cache.py            # Redis helper (get_or_set, invalidate, ping)
│       ├── fields.py           # 19 sahə / 5 qrup → 76 arXiv kateqoriyası
│       ├── trends.py           # trend təsnifatı (§12) — LLM yox, deterministik
│       ├── landscape.py        # tədqiqat landşaftı + boşluqlar (§11, §13)
│       ├── relations.py        # məqalələr arası əlaqələr (§15), etibarlılıqla
│       ├── providers/          # §18: LLM / embedding / rerank dəyişdirilə bilən
│       │   ├── base.py         #   protokollar (Protocol, ABC deyil)
│       │   ├── groq_provider.py
│       │   ├── fastembed_provider.py
│       │   └── rerank_provider.py   # sönülü — bax .env.example
│       ├── sources/            # arxiv, crossref, doaj, openalex + common (dedup açarları, dil, retry)
│       ├── routers/            # ingest, papers, search, ask, analytics, logs, digests, intelligence
│       ├── rag/
│       │   ├── chunker.py      # chunk + embed olunan mətn (başlıq daxil)
│       │   ├── retriever.py    # vektor / leksik / hibrid + filtrlər
│       │   ├── understanding.py# §6: niyyət, müəllif, tarix — LLM yox
│       │   ├── evidence.py     # §8: sübut seçimi, istinad doğrulaması
│       │   ├── insights.py     # §7: çıxarış + sübut tipi
│       │   ├── compare.py      # §9, §10: müqayisə və ziddiyyət
│       │   ├── llm.py · embedder.py · translator.py
│       └── static/             # frontend: 3 dilli konsol, vərəqlənən dəst, landşaft
└── n8n/workflows/              # W1 arXiv · W2 digest · W3 error · W4 çoxmənbəli · W5 rusdilli
```

## Bilinən məhdudiyyətlər

Sistemin nə **etmədiyini** bilmək, nə etdiyini bilmək qədər vacibdir:

- **Hibrid axtarış qurulub, amma sönülüdür.** Leksik `tsvector` indeksi və RRF birləşdirmə var; `RETRIEVAL_MODE=vector` qalır, çünki ölçmə fayda göstərmədi (az −3%, en +2%, ru +2% → orta +0.3%). Açmaq üçün: `--compare-retrieval`.
- **Rerank ölçüldü və rədd edildi.** Çoxdilli cross-encoder qoşulub; gecikməni 61 ms → 12 928 ms (212×) qaldırır və backend yaddaşını 2.99 GB-a çıxarır, yəni 4 GB-lıq serverə sığmır. Keyfiyyət qazancı isə xalis ~+0.7%.
- **Yalnız abstraktlar indekslənir**, tam mətn yox. Metod detalları çox vaxt abstraktda olmur — çıxarışın bir hissəsi məhz buna görə «sintez» kimi etiketlənir.
- **Azərbaycan dili tərcümə ilə işləyir.** Model azərbaycancanı rus/ingilis səviyyəsində dəstəkləmədiyi üçün az sorğularda orijinal vektor ölçmədə zərər verirdi (60% → 52%) və istifadə olunmur.
- **Tibb və psixologiya arXiv-dən gəlmir** — yalnız Crossref/DOAJ mətn sorğusu ilə, ona görə bu sahələrdə korpus daha nazikdir.
- **Sitat qrafiki praktiki olaraq boşdur.** `paper_relations` cədvəli var, amma sitat əlaqəsi yalnız hər iki tərəf korpusda olanda yaranır; korpusda isə cəmi 33 məqalənin OpenAlex ID-si var. `related_to` və `same_authors` işləyir.
- **Korpus ~1 600 məqalədir.** Bu, gündəlik yığımdan qurulan öz indeksimizdir, ədəbiyyatın güzgüsü deyil. Miqyas mühəndislik problemi deyil, hostinq problemidir.

Növbəti addımlar: OpenAlex-dən daha çox yığım (sitat qrafiki üçün), Europe PMC (tibb), və istifadəçi rəyindən gələn təkmilləşdirmələr.
