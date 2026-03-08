import pytest
import sqlite3
import os

import ide_yonetici

@pytest.fixture
def mock_db(monkeypatch, tmp_path):
    # Set a temporary database path for tests
    db_path = tmp_path / "test_ide_yonetici.db"
    monkeypatch.setattr(ide_yonetici, "VERITABANI_YOLU", str(db_path))
    
    # Create the tables in the mocked database path
    ide_yonetici.tablolari_olustur()
    
    yield str(db_path)

def test_proje_ekle_ve_getir(mock_db):
    veri = {
        "proje_adi": "Test Projesi",
        "ide_adi": "VS Code",
        "ide_turu": "Lokal",
        "ide_url": "",
        "hesap_adi": "Test Hesap",
        "hesap_email": "test@test.com",
        "durum": "Aktif",
        "notlar": "Bu bir test notudur",
        "etiketler": "test, ptest",
        "lokal_yol": "C:\\test\\dir"
    }
    
    # 1. Projeyi ekle
    ide_yonetici.proje_ekle(veri)
    
    # 2. Projeleri getir ve doğrula
    projeler = ide_yonetici.proje_listele()
    assert len(projeler) == 1
    assert projeler[0]["proje_adi"] == "Test Projesi"
    assert projeler[0]["ide_adi"] == "VS Code"
    assert projeler[0]["hesap_email"] == "test@test.com"
    assert projeler[0]["lokal_yol"] == "C:\\test\\dir"

def test_istatistikler(mock_db):
    veri1 = {"proje_adi": "Proje 1", "ide_adi": "IDE 1", "hesap_adi": "Hesap 1", "durum": "Aktif"}
    veri2 = {"proje_adi": "Proje 2", "ide_adi": "IDE 1", "hesap_adi": "Hesap 2", "durum": "Pasif"}
    
    ide_yonetici.proje_ekle(veri1)
    ide_yonetici.proje_ekle(veri2)
    
    istat = ide_yonetici.istatistikler()
    assert istat["toplam"] == 2
    assert istat["aktif"] == 1
    assert istat["ide_sayisi"] == 1
    assert istat["hesap_sayisi"] == 2

def test_proje_guncelle_ve_sil(mock_db):
    veri = {"proje_adi": "Silinecek Proje", "durum": "Aktif"}
    ide_yonetici.proje_ekle(veri)
    
    projeler = ide_yonetici.proje_listele()
    pid = projeler[0]["id"]
    
    # Güncelle
    ide_yonetici.proje_guncelle(pid, {"proje_adi": "Guncellenmis Proje", "durum": "Pasif"})
    projeler = ide_yonetici.proje_listele()
    assert projeler[0]["proje_adi"] == "Guncellenmis Proje"
    
    # Sil
    ide_yonetici.proje_sil(pid)
    assert len(ide_yonetici.proje_listele()) == 0

def test_tanimli_ideler_ve_hesaplar(mock_db):
    ide_yonetici.tanimli_ide_ekle({"ide_adi": "Cursor", "ide_turu": "Lokal"})
    ideler = ide_yonetici.tanimli_ide_listele()
    assert len(ideler) == 1
    assert ideler[0]["ide_adi"] == "Cursor"
    
    ide_yonetici.tanimli_hesap_ekle({"hesap_adi": "Ana", "hesap_email": "ana@mail.com"})
    hesaplar = ide_yonetici.tanimli_hesap_listele()
    assert len(hesaplar) == 1
    assert hesaplar[0]["hesap_email"] == "ana@mail.com"

