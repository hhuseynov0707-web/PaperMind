"""Mətnin parçalanması.

Chunk sərhədləri retrieval keyfiyyətinə birbaşa təsir edir: söz ortasından
kəsilmiş parça vektorlaşdıranda mənasını itirir, üst-üstə düşmə isə sərhəddə
qalan cümlələrin tapılmasını təmin edir.
"""

from app.config import settings
from app.rag.chunker import chunk_text


def test_qisa_metn_tek_parca_qalir():
    text = "Bu, bir chunk-a sığan qısa abstraktdır."
    assert chunk_text(text) == [text]


def test_bosh_metn_parca_vermir():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_artiq_bosluqlar_yigilir():
    assert chunk_text("iki    boşluq\n\nvə   sətir") == ["iki boşluq və sətir"]


def test_uzun_metn_bolunur():
    text = "söz " * 2000                      # ~8000 simvol
    parts = chunk_text(text)
    assert len(parts) > 1
    assert all(len(p) <= settings.chunk_size for p in parts)


def test_soz_ortasindan_kesilmir():
    """Sərhəd ən yaxın boşluqda olmalıdır — yarımçıq söz vektoru pozur."""
    text = " ".join(f"kelime{i}" for i in range(500))
    for part in chunk_text(text):
        assert not part.startswith(" ") and not part.endswith(" ")
        # hər parça tam sözlərdən ibarət olmalıdır
        assert all(w.startswith("kelime") for w in part.split())


def test_parcalar_ust_uste_dusur():
    """Üst-üstə düşmə olmasa, sərhəddə qalan cümlə heç bir parçada tam qalmaz."""
    text = " ".join(f"w{i}" for i in range(1500))
    parts = chunk_text(text)
    assert len(parts) >= 2
    son = set(parts[0].split()[-15:])
    evvel = set(parts[1].split()[:15])
    assert son & evvel, "ardıcıl parçalar arasında ortaq söz yoxdur"


def test_butun_metn_ehate_olunur():
    text = " ".join(f"t{i}" for i in range(900))
    birlesmis = " ".join(chunk_text(text))
    for token in ("t0", "t450", "t899"):
        assert token in birlesmis
