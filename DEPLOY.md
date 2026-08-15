# PaperMind — internetə çıxarılması

Bu sənəd sistemi ictimai serverdə işə salmaq üçündür. Lokal işləmə [README.md](README.md)-dədir.

---

> **n8n haqqında:** development compose-unda n8n `automation` profilindədir və
> `docker compose up -d` onu başlatmır (zəif maşınlarda yer qazandırmaq üçün).
> **Prod compose-da belə deyil** — orada n8n hər zaman qalxır, çünki gündəlik
> yığım ondan asılıdır.

## Nə dəyişir ictimai rejimdə?

| | Lokal | İctimai (`docker-compose.prod.yml`) |
|---|---|---|
| Açıq portlar | 5433, 6379, 8000, 5679 | **yalnız 80 və 443** |
| Yazma endpoint-ləri | sərbəst | `X-API-Key` tələb edir |
| LLM sualı | limitsiz | IP üzrə 20/saat + günlük 500 tavan |
| Axtarış | limitsiz | IP üzrə 120/saat |
| HTTPS | yox | Caddy + avtomatik Let's Encrypt |
| n8n paneli | brauzerdən açıq | **bağlı** — yalnız SSH tuneli ilə |
| `/docs` | açıq | bağlı (Caddyfile-da 404) |

Bunlar olmadan açıq deploy təhlükəlidir: `/api/ask` hər çağırışda Groq kvotanı xərcləyir, `/api/ingest` isə bazana kənar məqalə yazmağa imkan verir.

---

## Minimum tələblər

- **2 GB RAM** (embedding modeli + Postgres + Redis + n8n). 1 GB-da backend OOM olur.
  Ölçülmüş rəqəmlər: backend tək başına ~700 MB, bütün stack ~1.4 GB.
  **Rerank açsan bu, 2.99 GB-a qalxır** (`BAAI/bge-reranker-base` 1.13 GB-dır) —
  yəni 4 GB-lıq serverdə stack ilə birlikdə sığmır. Ona görə `RERANK_PROVIDER`
  defolt olaraq boşdur; açmazdan əvvəl `docker stats` ilə yoxla.
- **10 GB disk** — Docker image-ləri ~3 GB, baza artdıqca böyüyür.
- **Domen** — A qeydi serverin IP-sinə yönəlmiş olmalıdır (Let's Encrypt bunu tələb edir).
- Docker və Docker Compose plugin.

---

## Addım-addım (VPS üçün)

### 1. Domeni yönləndir
DNS-də `A` qeydi yarat: `papermind.example.com → SERVER_IP`. Yayılmasını gözlə (`nslookup papermind.example.com`).

### 2. Faylları serverə köçür
```bash
scp -r papermind user@SERVER_IP:~/
ssh user@SERVER_IP
cd ~/papermind
```

### 3. `.env` faylını doldur
```bash
cp .env.example .env
nano .env
```
Mütləq doldurulmalı:
```
DOMAIN=papermind.example.com
GROQ_API_KEY=gsk_...
POSTGRES_PASSWORD=<güclü parol>
ADMIN_API_KEY=<openssl rand -hex 32 ilə yaradılan>
CONTACT_EMAIL=sənin@epoçtun        # Crossref nəzakətli hovuzu
```

Açar yaratmaq:
```bash
openssl rand -hex 32
```

### 4. Hazırlıq yoxlaması
```bash
bash scripts/preflight.sh
```
Bütün yoxlamalar `OK` olmalıdır. `XƏTA` varsa deploy etmə.

### 5. Qaldır
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```
İlk qalxma 2-4 dəqiqə çəkir (embedding modeli yüklənir). `Application startup complete` görünəndə hazırdır.

### 6. Bazanı doldur
```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/backfill_multi.py --days 14 --limit 80
```

### 7. n8n-i qur (SSH tuneli ilə)
n8n paneli internetə açıq deyil. Öz kompüterindən:
```bash
ssh -L 5679:localhost:5678 user@SERVER_IP
```
Sonra brauzerdə `http://localhost:5679` aç → owner hesabı yarat → 4 workflow-un hamısı artıq import olunub, W1/W2/W4-ü **Publish** et.

> Workflow-lar `X-API-Key` başlığını `{{ $env.ADMIN_API_KEY }}`-dən oxuyur — `.env`-dəki açar avtomatik işləyir.

### 8. Yoxla
```bash
curl -I https://papermind.example.com          # 200 + HTTPS
curl https://papermind.example.com/api/analytics/summary
curl -X POST https://papermind.example.com/api/ingest -d '{"papers":[]}' \
     -H 'Content-Type: application/json'       # 401 qaytarmalıdır
```

---

## Digər platformalar

### Oracle Cloud Always Free — pulsuz və 7/24

Ən yaxşı pulsuz variant: **VM.Standard.A1.Flex**, 2 OCPU / 12 GB RAM (Always Free hədd 4 OCPU / 24 GB-dır). Bizim stack 2 GB istədiyi üçün bol yer qalır.

**Uyğunluq yoxlanılıb** — bütün image-lər və Python paketləri arm64 dəstəkləyir:

| Komponent | ARM64 |
|---|---|
| pgvector/pgvector:pg16 · redis · caddy · n8n · python:3.11-slim | ✅ hamısı |
| onnxruntime (embedding) | ✅ `manylinux_aarch64` wheel |
| fastembed · psycopg2-binary | ✅ |

**Qurulum qeydləri:**

1. **Instans yaradarkən:** Shape → *Ampere* → `VM.Standard.A1.Flex`, 2 OCPU / 12 GB. Image: **Ubuntu 22.04**. SSH açarını yadda saxla.

2. *"Out of host capacity"* xətası — A1 populyar regionlarda tez-tez dolu olur. Fərqli **availability domain** seç və ya bir neçə saat sonra təkrar cəhd et. Region seçimini dəyişmək də kömək edir.

3. **Firewall — ən çox ilişilən yer.** Oracle-da İKİ səviyyə var, hər ikisini açmaq lazımdır:
   ```bash
   # (a) Konsolda: VCN → Security List → Ingress Rules
   #     0.0.0.0/0 üçün TCP 80 və 443 əlavə et
   #
   # (b) Serverin öz iptables-ı (Ubuntu image-də default olaraq bağlıdır):
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
   Yalnız (a)-nı edib (b)-ni unutmaq — ən çox rast gəlinən səhvdir; sayt açılmır, səbəbi görünmür.

4. **Serverin hazırlanması — bir əmr.** Docker qurur, iptables-ın hər iki portunu açır və qalıcı edir, 2 GB swap yaradır:
   ```bash
   bash scripts/server-setup.sh
   ```
   (Skript sonda Oracle konsolundakı Security List addımını da xatırladır.)

5. **İlk build uzun çəkir** (ARM-də ~8-12 dəqiqə) — `onnxruntime` böyük paketdir. Səbrli ol, `docker compose ... logs -f backend` ilə izlə.

6. **Boş qalma riski:** Oracle uzun müddət istifadəsiz qalan Always Free instanslarını geri ala bilər. Bizim cron-lar hər gün işlədiyi üçün risk azdır, amma xəbərdarlıq e-poçtlarını nəzarətsiz qoyma.

**Alternativ (Oracle alınmasa):** evdə həmişə açıq qalan kompüter + Cloudflare Tunnel. Tam pulsuz, az istifadəçi üçün kifayətdir.

**Cloudflare Tunnel (server olmadan):** kompüterində `PUBLIC_MODE=true` ilə işlət və tunel aç:
```bash
cloudflared tunnel --url http://localhost:8000
```
Domen və sertifikat lazım deyil, amma yalnız kompüter açıq olanda işləyir. Bu halda `.env`-ə `PUBLIC_MODE=true`, `ADMIN_API_KEY=...` əlavə et və lokal compose-u yenidən qaldır.

**Render / Fly.io pulsuz tier:** 512 MB RAM embedding modeli üçün azdır — tövsiyə etmirəm.

---

## İstismar

**Backup (vacib!)** — hazır skript, son 7 nüsxəni saxlayır:
```bash
bash scripts/backup.sh
```
Gündəlik avtomatlaşdır:
```bash
crontab -e
# əlavə et:
0 3 * * * cd ~/papermind && bash scripts/backup.sh >> ~/backup.log 2>&1
```

**Bərpa**
```bash
gunzip -c backup-2026-08-10.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U elmradari -d elmradari
```

**Loglar**
```bash
docker compose -f docker-compose.prod.yml logs --tail 100 backend
docker compose -f docker-compose.prod.yml exec caddy cat /data/access.log | tail -50
```

**Yeniləmə**
```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build backend
```

**Limitləri dəyişmək** — `.env`-də `ASK_RATE_LIMIT`, `ASK_DAILY_BUDGET`, `SEARCH_RATE_LIMIT`, `TRANSLATE_DAILY_BUDGET`, sonra `docker compose -f docker-compose.prod.yml up -d backend`.

**Data qatının yenilənməsi** — hər üçü bərpa olunandır (kəsilsə qaldığı yerdən davam edir):

```bash
P="docker compose -f docker-compose.prod.yml exec -d backend sh -c"

# Yeni məqalələr (n8n onsuz da gündə 3 dəfə edir — bu, əl ilə təkan üçündür)
$P "python scripts/backfill_multi.py --days 14 --limit 80 > /tmp/bf.log 2>&1"

# Məqalə çıxarışları (§7) — landşaft və boşluq analizi bunun üzərində işləyir
$P "python scripts/extract_insights.py > /tmp/ins.log 2>&1"

# Məqalələr arası əlaqələr (§15)
$P "python scripts/build_relations.py > /tmp/rel.log 2>&1"

# Gedişat
docker compose -f docker-compose.prod.yml exec backend tail -5 /tmp/ins.log
```

> Çıxarış Groq limitinə tabedir və `EXTRACT_MODEL` (kiçik model) işlədir.
> 1 600 məqalə üçün ~2 saat çəkir; bir seansda bitməsə eyni əmri təkrarla.

**Keyfiyyəti ölçmək** — dəyişiklikdən sonra rəqəmlər sürüşməyib?

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/benchmark.py
docker compose -f docker-compose.prod.yml exec backend python scripts/rag_eval.py --sample 12
```

**Analitika keşini təmizləmək** (trend/landşaft köhnə qalıbsa):

```bash
docker compose -f docker-compose.prod.yml exec -T backend   python -c "from app import cache; cache.invalidate('analytics:*')"
```

---

## Təhlükəsizlik yoxlama siyahısı

- [ ] `.env` git-ə düşməyib (`.gitignore`-da var)
- [ ] `ADMIN_API_KEY` ən azı 32 simvol, təsadüfi
- [ ] `POSTGRES_PASSWORD` default `elmradari` deyil
- [ ] `docker compose -f docker-compose.prod.yml config` yalnız 80/443 göstərir
- [ ] Açarsız `POST /api/ingest` → 401
- [ ] Limitə çatanda `/api/ask` → 429
- [ ] Server firewall-unda yalnız 22, 80, 443 açıqdır
- [ ] Groq konsolunda istifadə limiti/xəbərdarlığı qurulub
- [ ] Backup cron-u işləyir və bərpa bir dəfə sınanıb
