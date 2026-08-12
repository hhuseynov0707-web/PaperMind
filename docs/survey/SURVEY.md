# Tələbə sorğusu — dizayn, qərar qaydaları, yayım planı

**Məqsəd:** PaperMind-ın biznes ideyasının davam etməyə dəyər olub-olmadığını 100+ tələbənin **real davranışı** üzərindən yoxlamaq.

**Nə yoxlanılır (3 sual):**
1. Tələbələr ümumiyyətlə elmi məqalə oxuyurmu? *(Oxumursa, məhsulun auditoriyası yoxdur.)*
2. Ağrı hardadır — tapmaqda, dildə, yoxsa girişdə (paywall)? *(Biz yalnız birincisini və ikincisini həll edirik.)*
3. Bu auditoriya rəqəmsal xidmətə **ümumiyyətlə** pul ödəyirmi? *(Ödəmirsə, abunə modeli ölüdür — universitet/qrant yolu qalır.)*

---

## Dizayn prinsipləri

| Prinsip | Səbəb |
|---|---|
| **Keçmiş davranış > gələcək niyyət** | «Ödəyərdinmi?» → nəzakət cavabı. «Son 12 ayda ödəmisən?» → fakt. |
| **Məhsul yalnız 5-ci bölmədə açılır** | Əvvəldə desək, bütün ağrı sualları bizim xeyrimizə əyilir (framing bias). |
| **«İşlətməzdim» cavabı hər yerdə var** | Çıxış yolu olmayan sual süni razılıq istehsal edir. |
| **Girişdə «oxumuram da normal cavabdır» yazılır** | Sosial arzuolunanlıq təsirini azaldır. |
| **E-poçt könüllü, sonda** | Ən dəyərli metrik budur: danışmaq ucuzdur, əlaqə vermək kiçik də olsa **xərcdir**. |
| **5 dəqiqə, 20 sual, əksəriyyəti bir klik** | 7 dəqiqədən sonra tamamlama sürətlə düşür. |

---

## Formanın strukturu

| Bölmə | Nə soruşulur | Niyə |
|---|---|---|
| 0. Giriş | — | Anonimlik, məqsəd, «düzgün cavab yoxdur» |
| 1. Profil | pillə, sahə, universitet | Seqmentləşdirmə: magistr/doktorant bakalavrdan tam fərqli davranır |
| 2. Vərdiş | sonuncu dəfə nə vaxt, ayda neçə, niyə, neçəsini axıra kimi | **Gatekeeper** — oxumayanları ayırırıq |
| 3. Ağrı | hardan tapır, nə çətindir, ingiliscə çətinlik, vaxt | Ağrının **yerini** tapmaq |
| 4. Alət və pul | hansı alətlər, hansı abunələr, son 12 ayda ödəniş | **Ödəmə qabiliyyəti** — ən vacib bölmə |
| 5. Konsept | *(indi məhsul təsvir olunur)* faydalılıq, hansı hissə, 5 AZN, kim ödəməli | Reaksiya |
| 6. Əlaqə | müsahibə + xəbərdarlıq üçün e-poçt, açıq şərh | Real maraq siqnalı |

---

## Qərar qaydaları — **datanı görməzdən əvvəl** təyin edilib

Bu cədvəl nəticələr gəlməmişdən yazılıb. Səbəb sadədir: rəqəmləri görəndən sonra hər nəticəyə uyğun izah tapmaq mümkündür. Ona görə həddi əvvəlcədən bağlayırıq.

| Metrik | 🟢 Yaşıl | 🟡 Sarı | 🔴 Qırmızı |
|---|---|---|---|
| Ayda ≥3 məqalə açanlar | >45% | 25–45% | <25% |
| «İngilis dili» ilk 2 ağrıda | >40% | 25–40% | <25% |
| Hər hansı rəqəmsal abunəyə ödəyənlər | >50% | 30–50% | <30% |
| Son 12 ayda təhsilə ödəniş edənlər | >35% | 20–35% | <20% |
| 5 AZN-ə «ödəyərdim» | >20% | 10–20% | <10% |
| E-poçt qoyanlar | >15% | 8–15% | <8% |

### Şərh qaydaları

1. **Deyilən niyyəti 3-ə böl.** 20% «ödəyərdim» deyirsə, real konversiya ~5–7%-dir. Bu, sənayedə sabit nisbətdir.
2. **E-poçt faizi «ödəyərdim» faizindən daha etibarlıdır.** Ziddiyyət olsa, e-poçta inan.
3. **Əgər «pulludur, çata bilmirəm» ilk ağrıdırsa və Sci-Hub/Telegram istifadəsi yüksəkdirsə** — bu bazar ödənişin **yanından keçir**. Onda istehlakçı abunəsi ölüdür; yol universitet lisenziyası və ya pulsuz+qrant modelidir. Bu, pis xəbər deyil, **vaxt qazandıran** xəbərdir.
4. **Sahə üzrə kəs.** 100 nəfərin ortalaması yanıldıcıdır: İT magistrləri ilə bakalavr 1-ci kurs eyni məhsulda deyil. Ən azı «ayda ≥3 məqalə oxuyanlar» alt qrupunu ayrıca hesabla.
5. **Ən çox oxunası sahə — açıq mətn sualları.** 100 sətir sərbəst cavabda bir cümlə bütün cədvəldən çox şey deyə bilər.

### Nəticəyə görə addım

- **Əksəriyyət yaşıl** → deploy et, pulsuz burax, ödənişli qatı sonra sına.
- **Qarışıq / əksəriyyət sarı** → pulsuz məhsul + e-poçt qoyanlarla 10 müsahibə. Qiymət qərarını təxirə sal.
- **Ödəmə sətirləri qırmızı** → istehlakçı abunəsindən imtina. Universitet/kafedra yolunu və ya portfolio məqsədini seç.
- **«Ayda ≥3 məqalə» qırmızı** → problem məhsulda deyil, auditoriyada. Hədəfi dəyiş (magistr/doktorant, müəllim) və ya ideyanı dəyiş.

---

## 100+ cavaba necə çatmaq

Tələbə sorğularında orta cavab faizi **8–15%**-dir. 100 cavab üçün mətni ~800–1200 nəfərə çatdırmaq lazımdır.

| Kanal | Gözlənilən | Qeyd |
|---|---|---|
| **Müəllimdən xahiş** (2–3 nəfər, dərs qrupuna göndərsin) | 30–60 | **Ən yüksək konversiya.** Bir müəllim = bir neçə onlarla cavab |
| Universitet qrup çatları (WhatsApp/Telegram) | 25–50 | Öz kursun + tanışların kursları |
| İT tələbə Discord/Telegram serverləri | 15–30 | Hədəfli auditoriya |
| Instagram story + 5 dostdan reshare | 10–25 | Ən sürətlisi |
| LinkedIn | 10–20 | Magistr/doktorant üçün ən yaxşı kanal |
| Facebook tələbə qrupları | 10–20 | Azalır, amma hələ işləyir |

**3 dalğa:** ilk paylaşım → 3 gün sonra xatırlatma → 7 gün sonra son çağırış. Xatırlatma adətən ilk dalğanın 40%-i qədər cavab gətirir.

**Stimul (pulsuz və işləyir):** *«Nəticələri hesabat şəklində hamıya göndərəcəyəm.»* Tələbələr öz qruplarının statistikasını görməyi sevir. Sözü tut — bu, sonradan həmin adamlara məhsulu təqdim etmək üçün qanuni səbəb yaradır.

### Paylaşım mətni (kopyala)

> Salam 👋 Universitet layihəm üçün kiçik bir sorğu keçirirəm: **tələbələr elmi məqalələri necə (və ümumiyyətlə) oxuyur.**
>
> 5 dəqiqə, anonimdir, heç nə satmıram. «Oxumuram» cavabı da mənim üçün tam dəyərlidir — elə ona görə soruşuram.
>
> Nəticələri hazır olanda hamıya göndərəcəyəm.
>
> 👉 [LİNK]

*(Qısa versiya — story/status üçün: «Elmi məqalə oxuyursan? Ya oxumursan? 5 dəqiqəlik anonim sorğu, nəticələri paylaşacağam 👇»)*

---

## Etik qaydalar

- Anonimdir; e-poçt **könüllü** və yalnız sonda.
- Məqsəd açıq yazılır — gizli məhsul reklamı deyil.
- Cavablar yalnız bu qərar üçün istifadə olunur, üçüncü tərəfə verilmir.
- E-poçt qoyanlara söz verilən nəticə hesabatı **mütləq** göndərilir.
- Eyni qrupa üçüncü dalğadan sonra yazılmır.

---

## Formanı yaratmaq

Google Forms-da 20 sualı əl ilə yığmaq ~40 dəqiqədir. [create-form.gs](create-form.gs) bunu 30 saniyəyə edir:

1. [script.google.com](https://script.google.com) → **New project**
2. `create-form.gs` faylının **bütün** məzmununu yapışdır
3. Yuxarıdan `createPaperMindSurvey` funksiyasını seç → **Run**
4. İlk dəfə icazə istəyəcək (öz hesabın, öz formun) → təsdiqlə
5. **Execution log**-da iki link çıxacaq: redaktə linki və paylaşım linki

Cavablar toplananda: forma → **Responses** → yaşıl Sheets ikonu → **File → Download → CSV**. Sonra mənə ver, analiz edim.
