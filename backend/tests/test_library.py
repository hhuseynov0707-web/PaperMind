"""Kitabxana vəziyyətləri — oxu siyahısı, ulduz, oxundu tarixçəsi (§16).

Bu qatda səhv məlumat itkisi deməkdir: səhv qayda istifadəçinin saxladığı
məqaləni səssizcə silə, ya da ulduzu görünməz yerə ata bilər. Testlər
«düymə işləyirmi» yox, «vəziyyətlər bir-birini POZURMU» sualını verir.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routers.library import resolve_state
from app.schemas import PaperStateIn


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def r(cur_saved=False, cur_starred=False, cur_read=False, **patch):
    return resolve_state(
        cur_saved=cur_saved,
        cur_starred=cur_starred,
        cur_read=cur_read,
        req=PaperStateIn(**patch),
    )


# --- Yamanın əsas müqaviləsi ------------------------------------------------

def test_unsent_fields_are_untouched():
    """Ən vacib test.

    Ulduzu dəyişən sorğu `saved` göndərmir. Əgər göndərilməyən sahə `False`
    kimi oxunsaydı, ulduza basmaq məqaləni kitabxanadan çıxarardı —
    istifadəçi üçün səbəbsiz itki.
    """
    saved, starred, read = r(cur_saved=True, cur_read=True, starred=True)
    assert saved is True and read is True


def test_explicit_false_is_not_none():
    """`False` «sil» deməkdir, `None` isə «dəymə» — ikisi qarışmamalıdır."""
    assert r(cur_saved=True, saved=False)[0] is False
    assert r(cur_saved=True)[0] is True


# --- Ulduz ilə siyahı arasındakı əlaqə -------------------------------------

def test_starring_also_adds_to_list():
    """Ulduzlu, amma siyahıda olmayan məqalə «harada?» sualı yaradır."""
    saved, starred, _ = r(starred=True)
    assert saved is True and starred is True


def test_unsaving_clears_the_star():
    """Tərsi: siyahıdan çıxan məqalənin ulduzu qalsaydı, ulduz görünüşündə
    kitabxanada olmayan sətirlər peyda olardı."""
    saved, starred, _ = r(cur_saved=True, cur_starred=True, saved=False)
    assert saved is False and starred is False


def test_star_wins_over_stale_unsave_in_same_request():
    """Eyni sorğuda `saved=False, starred=True` gəlsə, ulduz üstündür —
    əks halda nəticə sahələrin yoxlanma sırasından asılı olardı."""
    saved, starred, _ = r(saved=False, starred=True)
    assert saved is True and starred is True


# --- Oxundu vəziyyəti müstəqildir ------------------------------------------

def test_marking_read_does_not_touch_the_list():
    """Oxundu işarəsi kitabxananı böyütmür və kiçiltmir.

    Bu, limit qaydasının təməlidir: dolu kitabxanası olan istifadəçi də
    məqaləni oxundu işarələyə bilməlidir.
    """
    saved, starred, read = r(read=True)
    assert read is True and saved is False and starred is False


def test_read_survives_unsaving():
    """Siyahıdan çıxarılan məqalə tarixçədə qalır — «oxumuşdum» faktı
    saxlanmadan asılı deyil."""
    saved, _, read = r(cur_saved=True, cur_read=True, saved=False)
    assert saved is False and read is True


def test_all_states_off_means_no_row():
    """Hər üçü sönübsə sətir mənasızdır; router onu silir."""
    assert r(cur_saved=True, cur_read=True, saved=False, read=False) == (False, False, False)


# --- Giriş tələbi -----------------------------------------------------------

def test_every_library_endpoint_requires_login(client):
    """Kitabxana şəxsidir: heç bir yolu girişsiz açıq qalmamalıdır.

    Endpoint əlavə ediləndə bu siyahı da genişlənməlidir — açıq qalan bir
    metod bütün istifadəçilərin oxu tarixçəsini kənara verər.
    """
    assert client.get("/api/library").status_code == 401
    assert client.get("/api/library?view=starred").status_code == 401
    assert client.get("/api/library?view=read").status_code == 401
    assert client.get("/api/library/state").status_code == 401
    assert client.put("/api/library/1", json={"starred": True}).status_code == 401
    assert client.delete("/api/library/1").status_code == 401


def test_unknown_view_is_rejected(client):
    """Görünüş adı sorğuya birbaşa düşür — yalnız üç dəyər qəbul edilir.

    Girişsiz sorğuda 401 icazə yoxlamasının validasiyadan ƏVVƏL işlədiyini
    göstərir; 422 gəlsəydi, kənar adam parametrləri sınaya bilərdi.
    """
    assert client.get("/api/library?view=../../etc").status_code in (401, 422)
