"""RRF birləşdirməsi — Phase 2 (§5 hibrid retrieval).

Niyə RRF, niyə xal cəmi yox: cosine oxşarlığı [0,1] aralığındadır, `ts_rank_cd`
isə qeyri-məhduddur və paylanması sorğudan-sorğuya dəyişir. Onları toplamaq
üçün normallaşdırma lazımdır, normallaşdırma isə sürüşür. RRF yalnız SIRAdan
istifadə edir, ona görə miqyas problemi yaranmır.

Testlər DB və embedding modeli tələb etmir.
"""

from app.rag.retriever import RRF_K, rrf_fuse


def _v(pid, score, chunk=None):
    return {"paper_id": pid, "chunk_id": chunk, "score": score}


def test_document_in_both_rankings_wins():
    """RRF-in bütün mənası budur: iki üsulun razılaşdığı sənəd önə çıxır."""
    vector = [_v(1, 0.95, 10), _v(2, 0.90, 20)]
    lexical = [_v(3, 8.0), _v(2, 7.0)]

    out = rrf_fuse([vector, lexical], top_k=3)

    # 2 heç bir siyahıda birinci deyil, amma hər ikisindədir → birinci olmalıdır
    assert out[0]["paper_id"] == 2


def test_score_matches_rrf_formula():
    out = rrf_fuse([[_v(1, 0.9)], [_v(1, 5.0)]], top_k=1)
    expected = 1.0 / (RRF_K + 1) * 2
    # Xal 6 onluğa yuvarlaqlaşdırılır (sıralama yuvarlaqlaşdırmadan ƏVVƏL
    # aparılır, ona görə bu, nəticəyə təsir etmir — yalnız çıxışı təmizləyir).
    assert abs(out[0]["score"] - expected) < 1e-6


def test_scale_difference_does_not_matter():
    """Leksik xal 1000 dəfə böyük olsa da nəticəyə təsir etməməlidir."""
    small = [_v(1, 0.01), _v(2, 0.009)]
    huge = [_v(1, 9999.0), _v(2, 9000.0)]

    a = rrf_fuse([small, huge], top_k=2)
    b = rrf_fuse([[_v(1, 0.5), _v(2, 0.4)], [_v(1, 0.6), _v(2, 0.5)]], top_k=2)

    assert [x["paper_id"] for x in a] == [x["paper_id"] for x in b]
    assert [x["score"] for x in a] == [x["score"] for x in b]


def test_chunk_id_preserved_from_vector_ranking():
    """Leksik nəticələrdə chunk yoxdur — vektordan gələn saxlanılmalıdır,
    çünki LLM konteksti mətn tələb edir."""
    out = rrf_fuse([[_v(7, 0.9, 42)], [_v(7, 3.0, None)]], top_k=1)
    assert out[0]["chunk_id"] == 42


def test_chunk_id_stays_none_when_only_lexical():
    out = rrf_fuse([[_v(7, 3.0, None)]], top_k=1)
    assert out[0]["chunk_id"] is None


def test_top_k_respected():
    ranking = [_v(i, 1.0 / i) for i in range(1, 21)]
    assert len(rrf_fuse([ranking], top_k=5)) == 5


def test_empty_rankings():
    assert rrf_fuse([], top_k=5) == []
    assert rrf_fuse([[], []], top_k=5) == []


def test_single_ranking_preserves_order():
    """Bir üsul verilibsə RRF sıralamanı dəyişməməlidir."""
    ranking = [_v(3, 0.9), _v(1, 0.8), _v(2, 0.7)]
    out = rrf_fuse([ranking], top_k=3)
    assert [x["paper_id"] for x in out] == [3, 1, 2]


def test_lower_rank_contributes_less():
    """Sıra artdıqca töhfə azalmalıdır — monoton azalma."""
    first = rrf_fuse([[_v(1, 0.9)]], top_k=1)[0]["score"]
    tenth = rrf_fuse([[_v(9, 0.9) for _ in range(9)] + [_v(1, 0.1)]], top_k=10)
    last = [x for x in tenth if x["paper_id"] == 1][0]["score"]
    assert last < first
