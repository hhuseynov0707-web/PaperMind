"""Sübut seçimi və istinad doğrulaması — Phase 3 (§8).

Auditdə tapılan boşluq: LLM `[10.1234/xyz]` yazanda həmin identifikatorun
kontekstdə həqiqətən olub-olmadığı HEÇ YERDƏ yoxlanılmırdı. Yalnız prompt
qaydası ilə ümid edilirdi. §8 isə açıq deyir: *«Never fabricate citations»* və
*«Citations must correspond to the actual evidence used»*.

Üç funksiya, üçü də saf (DB tələb etmir, ona görə test olunur):

  select_evidence()   — zəif nəticələr LLM-ə ümumiyyətlə getmir
  validate_citations()— cavabdakı hər istinad kontekstlə tutuşdurulur
  corpus_context()    — cavabın hansı korpusa əsaslandığı (§16)
"""

import re

# Kontekstə düşmək üçün minimum oxşarlıq. Bundan aşağısı mövzuya aid deyil və
# LLM-i çaşdırır: model kontekstdəki hər şeyi "uyğun" saymağa meyllidir.
# 0.25 korpusda ölçülüb — bundan aşağı nəticələr adətən tamam başqa sahədəndir.
MIN_EVIDENCE_SCORE = 0.25

# Ən yaxşı nəticəyə nisbətdə hədd: bir nəticə 0.8, digəri 0.3-dürsə, ikincisi
# mütləq həddi keçsə də kontekstdə yalnız səs-küydür.
RELATIVE_FLOOR = 0.55

# İstinad formatı: [arxiv_id] | [10.xxxx/yyy] | [id:123]
CITATION_RE = re.compile(r"\[([^\]\s]+)\]")


def citation_label(paper) -> str:
    """Bir məqalənin istinad etiketi: arXiv ID → DOI → id:N.

    TƏK MƏNBƏ olmalıdır: kontekst qurulanda (llm.py) və istinad doğrulananda
    (ask.py) eyni etiket hesablanmalıdır. İki fərqli tərif olsa, düzgün istinad
    "uydurma" sayılıb silinərdi.

    Korpusun yarıdan çoxu arXiv-dən kənardır — yalnız arxiv_id işlətsək həmin
    məqalələr kontekstə `[None]` kimi düşür və LLM eyni etiketi bir neçə fərqli
    işə yapışdırır.
    """
    return paper.arxiv_id or paper.doi or f"id:{paper.id}"


def select_evidence(blocks: list[dict], max_blocks: int = 8) -> tuple[list[dict], dict]:
    """Retrieval nəticələrindən LLM-ə HANSI-nın gedəcəyini seçir.

    Əvvəllər retrieval nə qaytarsa, hamısı konteksti doldururdu — zəif nəticə
    (score 0.2) da LLM-ə gedirdi və cavabı çirkləndirirdi.

    İki hədd tətbiq olunur:
      1. Mütləq: MIN_EVIDENCE_SCORE-dan aşağısı atılır
      2. Nisbi: ən yaxşıdan çox uzaq düşənlər atılır

    Ən azı bir blok həmişə saxlanılır — əks halda güclü nəticə olmayan sualda
    sistem susur, halbuki "zəif sübut var" demək daha faydalıdır.
    """
    if not blocks:
        return [], {"kept": 0, "dropped": 0, "top_score": 0.0, "weak": True}

    ordered = sorted(blocks, key=lambda b: b["score"], reverse=True)
    top = ordered[0]["score"]
    floor = max(MIN_EVIDENCE_SCORE, top * RELATIVE_FLOOR)

    kept = [b for b in ordered if b["score"] >= floor][:max_blocks]
    if not kept:
        kept = ordered[:1]

    return kept, {
        "kept": len(kept),
        "dropped": len(blocks) - len(kept),
        "top_score": round(top, 4),
        # Ən yaxşı nəticə də zəifdirsə, cavab "sübut zəifdir" kimi işarələnir
        "weak": top < MIN_EVIDENCE_SCORE,
    }


def validate_citations(answer: str, allowed: set[str]) -> tuple[str, dict]:
    """Cavabdakı istinadları kontekstlə tutuşdurur (§8).

    Kontekstdə olmayan istinad UYDURULMUŞ sayılır və mətndən çıxarılır —
    saxlamaq daha pisdir, çünki istifadəçi onu real mənbə kimi oxuyur.

    Silmə əvəzinə etiketləmək variantı da var idi; silmək seçildi, çünki
    interfeys istinadları vizual olaraq vurğulayır və saxta istinad orada
    həqiqi kimi görünür.

    Qaytarır: (təmizlənmiş cavab, statistika)
    """
    found = CITATION_RE.findall(answer)
    if not found:
        return answer, {"cited": 0, "valid": 0, "invented": [], "coverage": 0.0}

    invented = [c for c in found if c not in allowed]
    cleaned = answer
    for bad in set(invented):
        # Yalnız istinad forması silinir, ətrafındakı mətn qalır
        cleaned = cleaned.replace(f"[{bad}]", "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +([.,;:])", r"\1", cleaned)

    valid = [c for c in found if c in allowed]
    return cleaned.strip(), {
        "cited": len(found),
        "valid": len(valid),
        "invented": sorted(set(invented)),
        # İstifadə olunan sübutun neçə faizinə istinad edilib — §20
        # "citation completeness" metrikası
        "coverage": round(len(set(valid)) / len(allowed), 3) if allowed else 0.0,
    }


def corpus_context(total: int, sources: list[str], languages: list[str],
                   oldest=None, newest=None) -> dict:
    """Cavabın hansı korpusa əsaslandığı (§16).

    Sistem heç vaxt bütün elmi ədəbiyyatı təmsil etdiyini ima etməməlidir.
    Bu blok cavabla birlikdə qaytarılır ki, istifadəçi əhatənin sərhədini görsün.
    """
    return {
        "papers": total,
        "sources": sorted(sources),
        "languages": sorted(languages),
        "from": oldest,
        "to": newest,
    }
