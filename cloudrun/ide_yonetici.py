#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║               IDE PROJE TAKİP SİSTEMİ v2.5                  ║
║  Bulut ve lokal IDE'lerdeki projeleri takip etmek için       ║
║  tarayıcı tabanlı modern bir yönetim arayüzü.               ║
║                                                              ║
║  Tüm bilgiler tek bir proje formu içinde yönetilir:          ║
║  Proje adı, IDE, hesap, URL, durum ve notlar.                ║
╚══════════════════════════════════════════════════════════════╝

Kullanım: Bu dosyaya çift tıklayın veya terminalde çalıştırın.
Tarayıcınızda otomatik olarak açılacaktır.
"""

import sqlite3
import json
import os
import sys
import zlib
import base64
import webbrowser
import threading
import subprocess
import shutil
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from contextlib import contextmanager

# ============================================================
# VERİTABANI AYARLARI
# ============================================================
UYGULAMA_KLASORU = os.path.dirname(os.path.abspath(__file__))
VERITABANI_YOLU = os.path.join(UYGULAMA_KLASORU, "ide_yonetici.db")
YEDEK_KLASORU = os.path.join(UYGULAMA_KLASORU, "yedekler")
SON_YEDEK_JSON = os.path.join(UYGULAMA_KLASORU, "ide_yonetici_son_yedek.json")
BULUT_AYARLAR_YOLU = os.path.join(UYGULAMA_KLASORU, "firebase_ayarlar.json")
OTOMATIK_YEDEK_LIMITI = 60
BULUT_TIMEOUT = 25
SUNUCU_PORT = 8888  # Varsayılan port numarası
GLOBAL_SUNUCU = None
GLOBAL_BULUT_SONUC = {"durum": "Henüz çalışmadı"}
GLOBAL_FIREBASE_KULLANICI = None
GLOBAL_FIREBASE_ID_TOKEN = ""


@contextmanager
def veritabani_baglantisi():
    """SQLite veritabanına güvenli bağlantı sağlar."""
    baglanti = sqlite3.connect(VERITABANI_YOLU, timeout=10)
    baglanti.row_factory = sqlite3.Row
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA synchronous=FULL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    try:
        yield baglanti
    finally:
        baglanti.close()


def tablolari_olustur():
    """Veritabanı tablolarını ve gerekli sütunları oluşturur."""
    with veritabani_baglantisi() as baglanti:
        # Ana tablo
        baglanti.execute("""
            CREATE TABLE IF NOT EXISTS projeler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proje_adi TEXT NOT NULL,
                ide_adi TEXT DEFAULT '',
                ide_turu TEXT DEFAULT 'Lokal',
                ide_url TEXT DEFAULT '',
                hesap_adi TEXT DEFAULT '',
                hesap_email TEXT DEFAULT '',
                durum TEXT DEFAULT 'Aktif',
                notlar TEXT DEFAULT '',
                son_guncelleme TEXT DEFAULT (datetime('now','localtime')),
                olusturma_tarihi TEXT DEFAULT (datetime('now','localtime')),
                etiketler TEXT DEFAULT '',
                lokal_yol TEXT DEFAULT ''
            )
        """)

        # Migration: Yeni sütunları güvenli bir şekilde ekle
        mevcut_sutunlar = [row['name'] for row in baglanti.execute("PRAGMA table_info(projeler)").fetchall()]
        if 'etiketler' not in mevcut_sutunlar:
            baglanti.execute("ALTER TABLE projeler ADD COLUMN etiketler TEXT DEFAULT ''")
        if 'lokal_yol' not in mevcut_sutunlar:
            baglanti.execute("ALTER TABLE projeler ADD COLUMN lokal_yol TEXT DEFAULT ''")
        if 'deploy_url' not in mevcut_sutunlar:
            baglanti.execute("ALTER TABLE projeler ADD COLUMN deploy_url TEXT DEFAULT ''")
        if 'kart_rengi' not in mevcut_sutunlar:
            baglanti.execute("ALTER TABLE projeler ADD COLUMN kart_rengi TEXT DEFAULT ''")
        if 'kart_gorseli' not in mevcut_sutunlar:
            baglanti.execute("ALTER TABLE projeler ADD COLUMN kart_gorseli TEXT DEFAULT ''")

        # Tanımlı IDE ve Hesap tabloları
        baglanti.execute("""
            CREATE TABLE IF NOT EXISTS tanimli_ideler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ide_adi TEXT NOT NULL,
                ide_turu TEXT DEFAULT 'Lokal',
                ide_url TEXT DEFAULT ''
            )
        """)
        baglanti.execute("""
            CREATE TABLE IF NOT EXISTS tanimli_hesaplar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hesap_adi TEXT NOT NULL,
                hesap_email TEXT DEFAULT ''
            )
        """)
        baglanti.commit()


def tum_verileri_al():
    """Veritabanındaki tüm ana veriyi yedeklenebilir formatta döndürür."""
    with veritabani_baglantisi() as bag:
        return {
            "projeler": [dict(s) for s in bag.execute("SELECT * FROM projeler ORDER BY son_guncelleme DESC").fetchall()],
            "tanimli_ideler": [dict(s) for s in bag.execute("SELECT * FROM tanimli_ideler ORDER BY ide_adi").fetchall()],
            "tanimli_hesaplar": [dict(s) for s in bag.execute("SELECT * FROM tanimli_hesaplar ORDER BY hesap_adi").fetchall()]
        }


def _atomik_json_yaz(yol, veri):
    """JSON dosyasını önce geçici dosyaya yazıp sonra değiştirir."""
    gecici_yol = f"{yol}.tmp"
    with open(gecici_yol, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)
    os.replace(gecici_yol, yol)


def _yedek_adi_temizle(neden):
    temiz = "".join(ch if ch.isalnum() else "_" for ch in str(neden)).strip("_")
    return (temiz or "otomatik")[:40]


def _eski_yedekleri_temizle():
    """Yedek klasörünü makul boyutta tutar."""
    if not os.path.isdir(YEDEK_KLASORU):
        return
    for desen in ("ide_yedek_*.json", "ide_yonetici_*.db"):
        dosyalar = sorted(
            (os.path.join(YEDEK_KLASORU, ad) for ad in os.listdir(YEDEK_KLASORU) if ad.startswith(desen.split("*")[0]) and ad.endswith(desen.split("*")[-1])),
            key=os.path.getmtime,
            reverse=True
        )
        for eski in dosyalar[OTOMATIK_YEDEK_LIMITI:]:
            try:
                os.remove(eski)
            except OSError:
                pass


def otomatik_yedek_al(neden="otomatik"):
    """Her önemli değişiklikten sonra JSON ve DB yedeği alır."""
    try:
        os.makedirs(YEDEK_KLASORU, exist_ok=True)
        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        temiz_neden = _yedek_adi_temizle(neden)
        veri = tum_verileri_al()
        yedek = {
            "meta": {
                "olusturma_zamani": datetime.now().isoformat(timespec="seconds"),
                "neden": neden,
                "veritabani": VERITABANI_YOLU,
                "proje_sayisi": len(veri["projeler"])
            },
            **veri
        }

        json_yolu = os.path.join(YEDEK_KLASORU, f"ide_yedek_{zaman}_{temiz_neden}.json")
        db_yolu = os.path.join(YEDEK_KLASORU, f"ide_yonetici_{zaman}_{temiz_neden}.db")
        _atomik_json_yaz(json_yolu, yedek)
        _atomik_json_yaz(SON_YEDEK_JSON, yedek)
        if os.path.exists(VERITABANI_YOLU):
            kaynak = sqlite3.connect(VERITABANI_YOLU)
            hedef = sqlite3.connect(db_yolu)
            try:
                kaynak.backup(hedef)
            finally:
                hedef.close()
                kaynak.close()
        _eski_yedekleri_temizle()
        ayarlar = firebase_ayarlari_oku()
        if ayarlar.get("aktif") and ayarlar.get("otomatik_yedek", True):
            bulut_yedekle(neden)
        return json_yolu
    except Exception:
        return None


def firebase_varsayilan_ayarlar():
    return {
        "aktif": False,
        "database_url": "",
        "auth_token": "",
        "web_api_key": "",
        "google_client_id": "",
        "kok_yol": "ide_yonetici",
        "otomatik_yedek": True
    }


def firebase_ayarlari_oku():
    """Firebase ayarlarını okur; dosya yoksa bulutu kapalı kabul eder."""
    ayarlar = firebase_varsayilan_ayarlar()
    if not os.path.exists(BULUT_AYARLAR_YOLU):
        return ayarlar
    try:
        with open(BULUT_AYARLAR_YOLU, "r", encoding="utf-8") as dosya:
            okunan = json.load(dosya)
        if isinstance(okunan, dict):
            ayarlar.update(okunan)
    except Exception:
        pass
    return ayarlar


def _firebase_adres(ayarlar, yol):
    database_url = (ayarlar.get("database_url") or "").rstrip("/")
    kok_yol = (ayarlar.get("kok_yol") or "ide_yonetici").strip("/")
    parcalar = [p for p in f"{kok_yol}/{yol.strip('/')}".split("/") if p]
    adres = f"{database_url}/{'/'.join(quote(p, safe='') for p in parcalar)}.json"
    token = ayarlar.get("auth_token") or GLOBAL_FIREBASE_ID_TOKEN or ""
    if token:
        adres = f"{adres}?{urlencode({'auth': token})}"
    return adres


def _firebase_istek(metod, yol, veri=None):
    ayarlar = firebase_ayarlari_oku()
    if not ayarlar.get("aktif"):
        return {"ok": False, "hata": "Firebase kapalı"}
    if not ayarlar.get("database_url") or "PROJE_ID" in ayarlar.get("database_url", ""):
        return {"ok": False, "hata": "Firebase database_url eksik"}

    govde = None
    if veri is not None:
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
    istek = Request(
        _firebase_adres(ayarlar, yol),
        data=govde,
        method=metod,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urlopen(istek, timeout=BULUT_TIMEOUT) as yanit:
            metin = yanit.read().decode("utf-8")
            return {"ok": True, "veri": json.loads(metin) if metin else None}
    except HTTPError as hata:
        detay = hata.read().decode("utf-8", errors="ignore")
        return {"ok": False, "hata": f"HTTP {hata.code}: {detay}"}
    except URLError as hata:
        return {"ok": False, "hata": str(hata.reason)}
    except Exception as hata:
        return {"ok": False, "hata": str(hata)}


def google_ile_firebase_giris(google_credential):
    """Google kimlik bilgisini Firebase Auth ID token'a çevirir."""
    global GLOBAL_FIREBASE_KULLANICI, GLOBAL_FIREBASE_ID_TOKEN
    ayarlar = firebase_ayarlari_oku()
    api_key = ayarlar.get("web_api_key") or ""
    if not api_key:
        return {"ok": False, "hata": "Firebase web_api_key eksik"}
    if not google_credential:
        return {"ok": False, "hata": "Google credential eksik"}

    adres = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?{urlencode({'key': api_key})}"
    payload = {
        "postBody": urlencode({"id_token": google_credential, "providerId": "google.com"}),
        "requestUri": "http://localhost",
        "returnIdpCredential": True,
        "returnSecureToken": True
    }
    istek = Request(
        adres,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urlopen(istek, timeout=BULUT_TIMEOUT) as yanit:
            veri = json.loads(yanit.read().decode("utf-8"))
        GLOBAL_FIREBASE_ID_TOKEN = veri.get("idToken", "")
        GLOBAL_FIREBASE_KULLANICI = {
            "email": veri.get("email", ""),
            "displayName": veri.get("displayName", ""),
            "photoUrl": veri.get("photoUrl", ""),
            "localId": veri.get("localId", "")
        }
        return {"ok": True, "kullanici": GLOBAL_FIREBASE_KULLANICI}
    except HTTPError as hata:
        detay = hata.read().decode("utf-8", errors="ignore")
        return {"ok": False, "hata": f"HTTP {hata.code}: {detay}"}
    except Exception as hata:
        return {"ok": False, "hata": str(hata)}


def google_cikis():
    global GLOBAL_FIREBASE_KULLANICI, GLOBAL_FIREBASE_ID_TOKEN
    GLOBAL_FIREBASE_KULLANICI = None
    GLOBAL_FIREBASE_ID_TOKEN = ""
    return {"ok": True}


def _veriyi_sikistir(veri_dict):
    """
    Veriyi Firebase için sıkıştırır.
    - kart_gorseli (Base64 görsel) Firebase'e gönderilmez — lokal DB'de kalır.
    - Kalan veri JSON → zlib compress (level 9) → base64 → tek string.
    Tipik tasarruf: %60-75.
    """
    # Görselleri çıkar, sadece meta bilgiyi tut
    projeler_temiz = []
    for p in veri_dict.get("projeler", []):
        p_kopya = dict(p)
        if p_kopya.get("kart_gorseli"):
            p_kopya["kart_gorseli"] = ""   # Firebase'e gönderilmez
        projeler_temiz.append(p_kopya)

    temiz_veri = {**veri_dict, "projeler": projeler_temiz}
    ham = json.dumps(temiz_veri, ensure_ascii=False, separators=(',', ':')).encode("utf-8")
    sikistirilmis = zlib.compress(ham, level=9)
    return {
        "v": 1,                                              # format versiyonu
        "z": base64.b64encode(sikistirilmis).decode("ascii"),
        "boyut_ham": len(ham),
        "boyut_sikis": len(sikistirilmis),
        "oran": round(len(sikistirilmis) / max(len(ham), 1) * 100, 1)
    }


def _veriyi_ac(paket):
    """Sıkıştırılmış Firebase paketini açar."""
    if not isinstance(paket, dict):
        return None
    # Eski format (sıkıştırılmamış) — geriye dönük uyumluluk
    if "projeler" in paket:
        return paket
    # Yeni format
    if paket.get("v") == 1 and "z" in paket:
        try:
            sikistirilmis = base64.b64decode(paket["z"])
            ham = zlib.decompress(sikistirilmis)
            return json.loads(ham.decode("utf-8"))
        except Exception:
            return None
    return None


def bulut_yedekle(neden="otomatik"):
    """Güncel veriyi sıkıştırarak Firebase Realtime Database'e gönderir."""
    global GLOBAL_BULUT_SONUC
    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    veri = tum_verileri_al()
    meta = {
        "olusturma_zamani": datetime.now().isoformat(timespec="seconds"),
        "neden": neden,
        "kaynak": "ide_yonetici",
        "proje_sayisi": len(veri["projeler"])
    }
    # Sıkıştırılmış paket (görseller hariç)
    sikis = _veriyi_sikistir({**meta, **veri})
    paket = {"meta": meta, "sikis": sikis}

    son_yedek = _firebase_istek("PUT", "son_yedek", paket)
    if not son_yedek.get("ok"):
        GLOBAL_BULUT_SONUC = {
            "durum": "Hata", "hata": son_yedek.get("hata"),
            "zaman": datetime.now().isoformat(timespec="seconds")
        }
        return GLOBAL_BULUT_SONUC

    tarihli = _firebase_istek("PUT", f"yedekler/{zaman}_{_yedek_adi_temizle(neden)}", paket)
    GLOBAL_BULUT_SONUC = {
        "durum": "Tamam" if tarihli.get("ok") else "Kısmi",
        "hata": tarihli.get("hata"),
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "proje_sayisi": len(veri["projeler"]),
        "boyut_kb": round(sikis.get("boyut_sikis", 0) / 1024, 1),
        "oran": sikis.get("oran", 0)
    }
    return GLOBAL_BULUT_SONUC


def bulut_son_yedegi_oku():
    sonuc = _firebase_istek("GET", "son_yedek")
    if not sonuc.get("ok"):
        return sonuc
    ham_veri = sonuc.get("veri")
    if not isinstance(ham_veri, dict):
        return {"ok": False, "hata": "Bulutta geçerli son_yedek bulunamadı"}

    # Sıkıştırılmış format
    if "sikis" in ham_veri:
        veri = _veriyi_ac(ham_veri["sikis"])
    else:
        # Eski format (geriye dönük uyumluluk)
        veri = ham_veri

    if not isinstance(veri, dict) or "projeler" not in veri:
        return {"ok": False, "hata": "Bulut verisi çözümlenemedi"}
    return {"ok": True, "veri": veri}


def buluttan_geri_yukle():
    """Firebase'deki son yedeği yerel veritabanına geri yükler."""
    sonuc = bulut_son_yedegi_oku()
    if not sonuc.get("ok"):
        return sonuc
    otomatik_yedek_al("buluttan_geri_yukleme_oncesi")
    yedek_verisini_veritabanina_yaz(sonuc["veri"], mevcutlari_sil=True)
    otomatik_yedek_al("buluttan_geri_yukleme")
    return {"ok": True, "mesaj": "Bulut yedeği geri yüklendi", "proje_sayisi": len(sonuc["veri"].get("projeler", []))}


def bulut_durumu():
    ayarlar = firebase_ayarlari_oku()
    database_url = ayarlar.get("database_url") or ""
    son = GLOBAL_BULUT_SONUC
    return {
        "aktif": bool(ayarlar.get("aktif")),
        "hazir": bool(database_url and "PROJE_ID" not in database_url),
        "google_giris_hazir": bool(ayarlar.get("web_api_key") and ayarlar.get("google_client_id")),
        "google_client_id": ayarlar.get("google_client_id") or "",
        "kullanici": GLOBAL_FIREBASE_KULLANICI,
        "giris_yapildi": bool(GLOBAL_FIREBASE_ID_TOKEN),
        "ayar_dosyasi": BULUT_AYARLAR_YOLU,
        "kok_yol": ayarlar.get("kok_yol") or "ide_yonetici",
        "otomatik_yedek": bool(ayarlar.get("otomatik_yedek", True)),
        "son_sonuc": son,
        "son_boyut_kb": son.get("boyut_kb"),
        "son_oran": son.get("oran"),
    }


def yedek_durumu():
    """Yedek sisteminin kısa durum bilgisini döndürür."""
    json_yedekleri = []
    db_yedekleri = []
    if os.path.isdir(YEDEK_KLASORU):
        json_yedekleri = [ad for ad in os.listdir(YEDEK_KLASORU) if ad.startswith("ide_yedek_") and ad.endswith(".json")]
        db_yedekleri = [ad for ad in os.listdir(YEDEK_KLASORU) if ad.startswith("ide_yonetici_") and ad.endswith(".db")]
    son_yedek_tarihi = None
    if os.path.exists(SON_YEDEK_JSON):
        son_yedek_tarihi = datetime.fromtimestamp(os.path.getmtime(SON_YEDEK_JSON)).isoformat(timespec="seconds")
    return {
        "yedek_klasoru": YEDEK_KLASORU,
        "son_yedek_json": SON_YEDEK_JSON,
        "son_yedek_tarihi": son_yedek_tarihi,
        "json_yedek_sayisi": len(json_yedekleri),
        "db_yedek_sayisi": len(db_yedekleri)
    }


def _toplu_ekle(bag, tablo, liste, sutunlar):
    if not liste:
        return True
    mevcut_sutunlar = {row["name"] for row in bag.execute(f"PRAGMA table_info({tablo})").fetchall()}
    aktif_sutunlar = [s for s in sutunlar if s in mevcut_sutunlar]
    if not aktif_sutunlar:
        return False
    placeholder = ",".join(["?"] * len(aktif_sutunlar))
    sorgu = f"INSERT OR REPLACE INTO {tablo} ({','.join(aktif_sutunlar)}) VALUES ({placeholder})"
    try:
        for item in liste:
            values = tuple(item.get(c) for c in aktif_sutunlar)
            bag.execute(sorgu, values)
        return True
    except sqlite3.Error:
        return False


def yedek_verisini_veritabanina_yaz(veri, mevcutlari_sil=False):
    """JSON yedeğini veritabanına yazar."""
    if isinstance(veri, list):
        veri = {"projeler": veri}
    with veritabani_baglantisi() as bag:
        if mevcutlari_sil:
            bag.execute("DELETE FROM projeler")
            bag.execute("DELETE FROM tanimli_ideler")
            bag.execute("DELETE FROM tanimli_hesaplar")
        sonuc_p = _toplu_ekle(
            bag,
            "projeler",
            veri.get("projeler"),
            ["id", "proje_adi", "ide_adi", "ide_turu", "ide_url", "hesap_adi", "hesap_email", "durum", "notlar", "son_guncelleme", "olusturma_tarihi", "etiketler", "lokal_yol", "deploy_url", "kart_rengi", "kart_gorseli"]
        )
        sonuc_i = _toplu_ekle(bag, "tanimli_ideler", veri.get("tanimli_ideler"), ["id", "ide_adi", "ide_turu", "ide_url"])
        sonuc_h = _toplu_ekle(bag, "tanimli_hesaplar", veri.get("tanimli_hesaplar"), ["id", "hesap_adi", "hesap_email"])
        bag.commit()
    return sonuc_p and sonuc_i and sonuc_h


def _son_json_yedegini_bul():
    adaylar = []
    if os.path.exists(SON_YEDEK_JSON):
        adaylar.append(SON_YEDEK_JSON)
    if os.path.isdir(YEDEK_KLASORU):
        adaylar.extend(
            os.path.join(YEDEK_KLASORU, ad)
            for ad in os.listdir(YEDEK_KLASORU)
            if ad.startswith("ide_yedek_") and ad.endswith(".json")
        )
    return max(adaylar, key=os.path.getmtime) if adaylar else None


def _son_db_yedegini_bul():
    if not os.path.isdir(YEDEK_KLASORU):
        return None
    adaylar = [
        os.path.join(YEDEK_KLASORU, ad)
        for ad in os.listdir(YEDEK_KLASORU)
        if ad.startswith("ide_yonetici_") and ad.endswith(".db")
    ]
    return max(adaylar, key=os.path.getmtime) if adaylar else None


def veritabani_saglam_mi():
    if not os.path.exists(VERITABANI_YOLU):
        return True
    try:
        bag = sqlite3.connect(VERITABANI_YOLU)
        sonuc = bag.execute("PRAGMA integrity_check").fetchone()[0]
        bag.close()
        return sonuc == "ok"
    except sqlite3.DatabaseError:
        return False


def veritabani_kurtarmayi_dene():
    """Bozuk veya boş DB durumunda son yedekten otomatik toparlamayı dener."""
    if not veritabani_saglam_mi():
        os.makedirs(YEDEK_KLASORU, exist_ok=True)
        bozuk_yol = os.path.join(YEDEK_KLASORU, f"bozuk_ide_yonetici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        try:
            shutil.move(VERITABANI_YOLU, bozuk_yol)
        except OSError:
            pass
        db_yedegi = _son_db_yedegini_bul()
        if db_yedegi:
            shutil.copy2(db_yedegi, VERITABANI_YOLU)

    try:
        with veritabani_baglantisi() as bag:
            proje_sayisi = bag.execute("SELECT COUNT(*) FROM projeler").fetchone()[0]
        if proje_sayisi > 0:
            return False
    except sqlite3.DatabaseError:
        return False

    json_yedegi = _son_json_yedegini_bul()
    if not json_yedegi:
        return False
    try:
        with open(json_yedegi, "r", encoding="utf-8") as dosya:
            yedek_verisini_veritabanina_yaz(json.load(dosya), mevcutlari_sil=True)
        otomatik_yedek_al("kurtarma_sonrasi")
        return True
    except Exception:
        return False


# ============================================================
# VERİTABANI İŞLEMLERİ (CRUD)
# Tek tablo üzerinde ekleme, listeleme, güncelleme, silme
# ============================================================

def proje_listele():
    """Tüm proje kayıtlarını son güncellemeye göre sıralayıca döndürür."""
    with veritabani_baglantisi() as bag:
        satirlar = bag.execute("SELECT * FROM projeler ORDER BY son_guncelleme DESC").fetchall()
        return [dict(s) for s in satirlar]


def _lokal_yol_temizle(yol):
    """Windows 'Yol olarak kopyala' tırnaklarını temizler."""
    return (yol or "").strip().strip('"\'')


def _proje_verisi_hazirla(veri):
    """Proje verisini standart formata getirir."""
    return (
        veri.get("proje_adi"),
        veri.get("ide_adi", ""),
        veri.get("ide_turu", "Lokal"),
        veri.get("ide_url", ""),
        veri.get("hesap_adi", ""),
        veri.get("hesap_email", ""),
        veri.get("durum", "Bitti"),
        veri.get("notlar", ""),
        veri.get("etiketler", ""),
        _lokal_yol_temizle(veri.get("lokal_yol", "")),
        veri.get("deploy_url", ""),
        veri.get("kart_rengi", ""),
        veri.get("kart_gorseli", ""),
    )


def proje_ekle(veri):
    """Yeni bir proje kaydı ekler."""
    if not str(veri.get("proje_adi", "")).strip():
        return {"hata": "Proje adı gerekli"}
    with veritabani_baglantisi() as bag:
        sorgu = """
            INSERT INTO projeler (
                proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email,
                durum, notlar, etiketler, lokal_yol, deploy_url, kart_rengi, kart_gorseli
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        bag.execute(sorgu, _proje_verisi_hazirla(veri))
        bag.commit()
    otomatik_yedek_al("proje_ekle")
    return {"mesaj": "Proje eklendi"}


def proje_guncelle(proje_id, veri):
    """Mevcut bir proje kaydını günceller."""
    if not str(veri.get("proje_adi", "")).strip():
        return {"hata": "Proje adı gerekli"}
    with veritabani_baglantisi() as bag:
        sorgu = """
            UPDATE projeler SET
                proje_adi=?, ide_adi=?, ide_turu=?, ide_url=?,
                hesap_adi=?, hesap_email=?, durum=?, notlar=?,
                etiketler=?, lokal_yol=?, deploy_url=?, kart_rengi=?, kart_gorseli=?,
                son_guncelleme=datetime('now','localtime')
            WHERE id=?
        """
        cursor = bag.execute(sorgu, _proje_verisi_hazirla(veri) + (proje_id,))
        bag.commit()
        if cursor.rowcount == 0:
            return {"hata": "Proje bulunamadı"}
    otomatik_yedek_al("proje_guncelle")
    return {"mesaj": "Proje güncellendi"}


def proje_sil(proje_id):
    """Bir proje kaydını siler."""
    otomatik_yedek_al("proje_silmeden_once")
    with veritabani_baglantisi() as bag:
        cursor = bag.execute("DELETE FROM projeler WHERE id=?", (proje_id,))
        bag.commit()
        if cursor.rowcount == 0:
            return {"hata": "Proje bulunamadı"}
    otomatik_yedek_al("proje_sil")
    return {"mesaj": "Proje silindi"}


def istatistikler():
    """Özet istatistikleri döndürür."""
    with veritabani_baglantisi() as bag:
        toplam = bag.execute("SELECT COUNT(*) FROM projeler").fetchone()[0]
        aktif = bag.execute("SELECT COUNT(*) FROM projeler WHERE durum IN ('Aktif', 'Yarım Kaldı', 'Bitmedi ama çalışıyor')").fetchone()[0]
        bitti = bag.execute("SELECT COUNT(*) FROM projeler WHERE durum='Bitti'").fetchone()[0]
        bulut = bag.execute("SELECT COUNT(*) FROM projeler WHERE ide_turu='Bulut'").fetchone()[0]
        benzersiz_ide = bag.execute("SELECT COUNT(DISTINCT ide_adi) FROM projeler WHERE ide_adi != ''").fetchone()[0]
        benzersiz_hesap = bag.execute("SELECT COUNT(DISTINCT hesap_adi) FROM projeler WHERE hesap_adi != ''").fetchone()[0]

    return {
        "toplam": toplam, "aktif": aktif, "bitti": bitti, "bulut": bulut,
        "lokal": toplam - bulut, "ide_sayisi": benzersiz_ide, "hesap_sayisi": benzersiz_hesap
    }


def otomatik_tamamla():
    """Öneri listelerini birleştirir."""
    with veritabani_baglantisi() as bag:
        def get_set(sorgu): return {r[0] for r in bag.execute(sorgu).fetchall() if r[0]}

        ideler = get_set("SELECT ide_adi FROM projeler") | get_set("SELECT ide_adi FROM tanimli_ideler")
        hesaplar = get_set("SELECT hesap_adi FROM projeler") | get_set("SELECT hesap_adi FROM tanimli_hesaplar")
        emailler = get_set("SELECT hesap_email FROM projeler") | get_set("SELECT hesap_email FROM tanimli_hesaplar")

    return {
        "ideler": sorted(ideler),
        "hesaplar": sorted(hesaplar),
        "emailler": sorted(emailler)
    }


def veritabani_durumu():
    """Veritabanı sağlığını kontrol eder."""
    try:
        with veritabani_baglantisi() as bag:
            return {
                "status": "Healthy",
                "counts": {
                    "projeler": bag.execute("SELECT COUNT(*) FROM projeler").fetchone()[0],
                    "ideler": bag.execute("SELECT COUNT(*) FROM tanimli_ideler").fetchone()[0],
                    "hesaplar": bag.execute("SELECT COUNT(*) FROM tanimli_hesaplar").fetchone()[0]
                }
            }
    except Exception as e:
        return {"status": "Error", "message": str(e)}


# ============================================================
# TANIMLI IDE VE HESAP İŞLEMLERİ
# ============================================================

def tanimli_ide_listele():
    with veritabani_baglantisi() as bag:
        return [dict(r) for r in bag.execute("SELECT * FROM tanimli_ideler ORDER BY ide_adi").fetchall()]


def tanimli_ide_ekle(veri):
    with veritabani_baglantisi() as bag:
        bag.execute("INSERT INTO tanimli_ideler (ide_adi, ide_turu, ide_url) VALUES (?,?,?)",
                    (veri["ide_adi"], veri.get("ide_turu", "Lokal"), veri.get("ide_url", "")))
        bag.commit()
    otomatik_yedek_al("ide_ekle")


def tanimli_ide_guncelle(tid, veri):
    with veritabani_baglantisi() as bag:
        bag.execute("UPDATE tanimli_ideler SET ide_adi=?, ide_turu=?, ide_url=? WHERE id=?",
                    (veri["ide_adi"], veri.get("ide_turu", "Lokal"), veri.get("ide_url", ""), tid))
        bag.commit()
    otomatik_yedek_al("ide_guncelle")


def tanimli_ide_sil(tid):
    otomatik_yedek_al("ide_silmeden_once")
    with veritabani_baglantisi() as bag:
        cursor = bag.execute("DELETE FROM tanimli_ideler WHERE id=?", (tid,))
        bag.commit()
        if cursor.rowcount == 0:
            return {"hata": "IDE bulunamadı"}
    otomatik_yedek_al("ide_sil")
    return {"mesaj": "IDE silindi"}


def tanimli_hesap_listele():
    with veritabani_baglantisi() as bag:
        return [dict(r) for r in bag.execute("SELECT * FROM tanimli_hesaplar ORDER BY hesap_adi").fetchall()]


def tanimli_hesap_ekle(veri):
    with veritabani_baglantisi() as bag:
        bag.execute("INSERT INTO tanimli_hesaplar (hesap_adi, hesap_email) VALUES (?,?)",
                    (veri["hesap_adi"], veri.get("hesap_email", "")))
        bag.commit()
    otomatik_yedek_al("hesap_ekle")


def tanimli_hesap_guncelle(tid, veri):
    with veritabani_baglantisi() as bag:
        bag.execute("UPDATE tanimli_hesaplar SET hesap_adi=?, hesap_email=? WHERE id=?",
                    (veri["hesap_adi"], veri.get("hesap_email", ""), tid))
        bag.commit()
    otomatik_yedek_al("hesap_guncelle")


def tanimli_hesap_sil(tid):
    otomatik_yedek_al("hesap_silmeden_once")
    with veritabani_baglantisi() as bag:
        cursor = bag.execute("DELETE FROM tanimli_hesaplar WHERE id=?", (tid,))
        bag.commit()
        if cursor.rowcount == 0:
            return {"hata": "Hesap bulunamadı"}
    otomatik_yedek_al("hesap_sil")
    return {"mesaj": "Hesap silindi"}


# ============================================================
# HTTP SUNUCU — İstekleri karşılar, API ve arayüz sunar
# ============================================================

class IdeYoneticiHandler(BaseHTTPRequestHandler):
    """HTTP isteklerini karşılayan ve API uç noktalarını yöneten sunucu sınıfı."""

    def log_message(self, format, *args):  # noqa: W0622
        """Sunucu loglarını sessizleştir."""
        pass

    def _guvenlik_basliklari(self):
        """Güvenlik başlıklarını ekler."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https://lh3.googleusercontent.com; script-src 'self' 'unsafe-inline' https://accounts.google.com; frame-src https://accounts.google.com; connect-src 'self' https://identitytoolkit.googleapis.com;"
        }
        for k, v in headers.items():
            self.send_header(k, v)

    def _cache_engelleme_basliklari(self):
        """Tarayıcının eski API cevaplarını göstermesini engeller."""
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _json_yanit(self, veri, durum=200):
        """JSON yanıtı döner."""
        self.send_response(durum)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self._cache_engelleme_basliklari()
        self._guvenlik_basliklari()
        self.end_headers()
        self.wfile.write(json.dumps(veri, ensure_ascii=False).encode("utf-8"))

    def _html_yanit(self, icerik):
        """HTML yanıtı döner."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cache_engelleme_basliklari()
        self._guvenlik_basliklari()
        self.end_headers()
        self.wfile.write(icerik.encode("utf-8"))

    def _govde_oku(self):
        """İstek gövdesini okur."""
        uzunluk = int(self.headers.get("Content-Length", 0))
        if uzunluk < 0 or uzunluk > 10 * 1024 * 1024:
            return {}
        try:
            govde = self.rfile.read(uzunluk).decode("utf-8")
        except (OSError, ValueError):
            return {}
        try:
            return json.loads(govde) if govde else {}
        except (json.JSONDecodeError, ValueError):
            return {}

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self._cache_engelleme_basliklari()
        self.end_headers()

    def do_GET(self):
        yol = urlparse(self.path).path
        if yol == "/" or yol == "":
            return self._html_yanit(ARAYUZ_HTML)

        # Basit Router
        routes = {
            "/api/projeler": proje_listele,
            "/api/istatistikler": istatistikler,
            "/api/otomatik": otomatik_tamamla,
            "/api/tanimli/ideler": tanimli_ide_listele,
            "/api/tanimli/hesaplar": tanimli_hesap_listele,
            "/api/diagnostic": lambda: {
                "server": "Active",
                "database": veritabani_durumu(),
                "backups": yedek_durumu(),
                "cloud": bulut_durumu(),
                "environment": {"os": sys.platform, "python": sys.version}
            },
            "/api/bulut/durum": bulut_durumu,
            "/api/export": self._export_verisi
        }

        if yol in routes:
            self._json_yanit(routes[yol]())
        else:
            self._json_yanit({"hata": "Bulunamadı"}, 404)

    def _export_verisi(self):
        return {"meta": {"olusturma_zamani": datetime.now().isoformat(timespec="seconds")}, **tum_verileri_al()}

    def do_POST(self):
        yol = urlparse(self.path).path
        veri = self._govde_oku()

        if yol == "/api/kapat":
            self._json_yanit({"mesaj": "Sunucu kapatma istegi alindi"})
            threading.Thread(target=sunucuyu_kapat, daemon=True).start()
            return

        if yol == "/api/yedek-al":
            yedek_yolu = otomatik_yedek_al("manuel")
            return self._json_yanit({"mesaj": "Yedek alındı", "yedek": yedek_yolu, "durum": yedek_durumu()})

        if yol == "/api/bulut/yedekle":
            # Yavaş Firebase çağrısı ana thread'i bloklamasın — arka planda çalıştır
            global GLOBAL_BULUT_SONUC
            GLOBAL_BULUT_SONUC = {"durum": "Devam ediyor", "zaman": datetime.now().isoformat(timespec="seconds")}
            threading.Thread(target=lambda: bulut_yedekle("manuel"), daemon=True).start()
            return self._json_yanit({"durum": "Devam ediyor", "mesaj": "Bulut yedeklemesi arka planda başlatıldı"})

        if yol == "/api/bulut/geri-yukle":
            sonuc = buluttan_geri_yukle()
            return self._json_yanit(sonuc, 200 if sonuc.get("ok") else 400)

        if yol == "/api/auth/google":
            sonuc = google_ile_firebase_giris(veri.get("credential", ""))
            return self._json_yanit(sonuc, 200 if sonuc.get("ok") else 400)

        if yol == "/api/auth/cikis":
            return self._json_yanit(google_cikis())

        if yol == "/api/projeler":
            sonuc = proje_ekle(veri)
            return self._json_yanit(sonuc, 200 if "hata" not in sonuc else 400)

        if yol == "/api/tanimli/ideler":
            tanimli_ide_ekle(veri)
            return self._json_yanit({"mesaj": "IDE eklendi"})

        if yol == "/api/tanimli/hesaplar":
            tanimli_hesap_ekle(veri)
            return self._json_yanit({"mesaj": "Hesap eklendi"})

        if yol == "/api/import":
            self._import_islemi(veri)
            return self._json_yanit({"mesaj": "İçe aktarım tamamlandı"})

        if yol == "/api/ac":
            return self._klasor_ac(veri.get("yol", ""))

        self._json_yanit({"hata": "Geçersiz"}, 404)

    def _import_islemi(self, veri):
        otomatik_yedek_al("ice_aktarma_oncesi")
        yedek_verisini_veritabanina_yaz(veri)
        otomatik_yedek_al("ice_aktarma")

    def _klasor_ac(self, yol_str):
        yol_str = (yol_str or "").strip().strip('"\'')  # Windows tırnak temizleme
        if not yol_str:
            return self._json_yanit({"hata": "Yol belirtilmedi"}, 400)
        try:
            gercek_yol = os.path.realpath(yol_str)
        except (OSError, ValueError):
            return self._json_yanit({"hata": "Geçersiz yol"}, 400)
        # Executable dosya engeli — sadece dizin aç
        uzanti = os.path.splitext(gercek_yol)[1].lower()
        if uzanti in ('.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', '.msi', '.com'):
            return self._json_yanit({"hata": "Sadece dizin açılabilir, çalıştırılabilir dosya reddedildi"}, 400)
        if not os.path.isdir(gercek_yol):
            return self._json_yanit({"hata": "Yol bir dizin değil veya bulunamadı"}, 400)
        try:
            if sys.platform == 'win32': os.startfile(gercek_yol)
            elif sys.platform == 'darwin': subprocess.call(['open', gercek_yol])
            else: subprocess.call(['xdg-open', gercek_yol])
            return self._json_yanit({"mesaj": "Dizin açıldı"})
        except Exception as e:
            return self._json_yanit({"hata": str(e)}, 500)

    def do_PUT(self):
        yol = urlparse(self.path).path
        veri = self._govde_oku()
        parcalar = yol.split("/")

        try:
            target_id = int(parcalar[-1])
            if "/api/projeler/" in yol:
                sonuc = proje_guncelle(target_id, veri)
                return self._json_yanit(sonuc, 200 if "hata" not in sonuc else 400)
            if "/api/tanimli/ideler/" in yol:
                tanimli_ide_guncelle(target_id, veri)
                return self._json_yanit({"mesaj": "IDE güncellendi"})
            if "/api/tanimli/hesaplar/" in yol:
                tanimli_hesap_guncelle(target_id, veri)
                return self._json_yanit({"mesaj": "Hesap güncellendi"})
        except (ValueError, IndexError):
            pass

        self._json_yanit({"hata": "Geçersiz"}, 404)

    def do_DELETE(self):
        yol = urlparse(self.path).path
        parcalar = yol.split("/")

        try:
            target_id = int(parcalar[-1])
            if "/api/projeler/" in yol:
                sonuc = proje_sil(target_id)
                return self._json_yanit(sonuc, 200 if "hata" not in sonuc else 404)
            if "/api/tanimli/ideler/" in yol:
                sonuc = tanimli_ide_sil(target_id)
                return self._json_yanit(sonuc, 200 if "hata" not in sonuc else 404)
            if "/api/tanimli/hesaplar/" in yol:
                sonuc = tanimli_hesap_sil(target_id)
                return self._json_yanit(sonuc, 200 if "hata" not in sonuc else 404)
        except (ValueError, IndexError):
            pass

        self._json_yanit({"hata": "Geçersiz"}, 404)


# ============================================================
# GÖMÜLÜ HTML ARAYÜZÜ
# Tüm HTML, CSS ve JavaScript kodu aşağıdaki string içindedir.
# Tarayıcıda modern, koyu temalı tek sayfalık bir uygulama açılır.
# ============================================================

ARAYUZ_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>IDE Proje Takip Sistemi v2.5</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ===== SIFIRLAMA VE TEMA DEĞİŞKENLERİ ===== */
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#090b14;--bg2:#0f1224;--bg3:rgba(255,255,255,0.03);
  --bg-hover:rgba(255,255,255,0.06);--bg-modal:#111428;
  --text:#e4e4ef;--text2:#7b849e;--text3:#4a546a;
  --accent:#0ea5e9;--accent2:#38bdf8;--glow:rgba(14,165,233,0.25);
  --green:#10b981;--yellow:#f59e0b;--orange:#f97316;--red:#ef4444;--blue:#3b82f6;--purple:#a855f7;
  --border:rgba(255,255,255,0.06);--border2:rgba(14,165,233,0.4);
  --r:14px;--rs:10px;--tr:all .25s cubic-bezier(.4,0,.2,1);
}
[data-theme="light"]{
  --bg:#f8f9fc;--bg2:#ffffff;--bg3:rgba(0,0,0,0.03);
  --bg-hover:rgba(0,0,0,0.06);--bg-modal:#ffffff;
  --text:#1a1a2e;--text2:#5a5a75;--text3:#8a8a9e;
  --border:rgba(0,0,0,0.1);--border2:rgba(124,106,239,0.5);
}
html{scroll-behavior:smooth}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 20% 0%,rgba(14,165,233,0.08) 0%,transparent 60%),
  radial-gradient(ellipse at 80% 100%,rgba(16,185,129,0.05) 0%,transparent 60%);
  pointer-events:none;z-index:-1}

/* ===== HEADER ===== */
.header{padding:28px 40px;display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid var(--border);backdrop-filter:blur(20px);
  position:sticky;top:0;z-index:50;background:rgba(9,9,22,0.85)}
.brand{display:flex;align-items:center;gap:14px}
.brand-icon{width:44px;height:44px;border-radius:14px;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--accent),#38bdf8);font-size:22px;
  box-shadow:0 4px 20px var(--glow)}
.brand h1{font-size:18px;font-weight:700;letter-spacing:-.5px}
.brand p{font-size:11px;color:var(--text2);margin-top:2px;font-weight:400}
.header-actions{display:flex;gap:10px;align-items:center}

/* ===== BUTONLAR ===== */
.btn{padding:10px 22px;border-radius:var(--rs);font-size:13px;font-weight:600;cursor:pointer;
  border:1px solid transparent;font-family:inherit;display:inline-flex;align-items:center;
  gap:8px;transition:var(--tr);user-select:none;white-space:nowrap}
.btn-primary{background:linear-gradient(135deg,var(--accent),#8b7cf0);color:#fff;
  box-shadow:0 4px 16px var(--glow)}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 6px 24px rgba(124,106,239,0.35)}
.btn-success{background:linear-gradient(135deg,#10b981,#22c55e);color:#fff;
  box-shadow:0 4px 14px rgba(16,185,129,0.3)}
.btn-success:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(16,185,129,0.45)}
.btn-ghost{background:var(--bg3);color:var(--text2);border-color:var(--border)}
.btn-ghost:hover{color:var(--text);background:var(--bg-hover);border-color:var(--text3)}
.btn-sm{padding:7px 14px;font-size:12px;border-radius:8px}
.btn-icon{width:34px;height:34px;padding:0;display:flex;align-items:center;justify-content:center;
  border-radius:8px;background:var(--bg3);border:1px solid var(--border);color:var(--text2);
  cursor:pointer;transition:var(--tr);font-size:15px}
.btn-icon:hover{color:var(--text);background:var(--bg-hover)}
.btn-icon.danger:hover{color:var(--red);background:rgba(239,107,94,0.1);border-color:rgba(239,107,94,0.2)}
.btn-icon.edit:hover{color:var(--blue);background:rgba(91,168,245,0.1);border-color:rgba(91,168,245,0.2)}
.btn-danger{background:rgba(239,107,94,0.15);color:var(--red);border-color:rgba(239,107,94,0.3)}
.btn-danger:hover{background:rgba(239,107,94,0.25);border-color:rgba(239,107,94,0.5)}

/* ===== ARAMA VE FİLTRE ===== */
.controls{padding:20px 40px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:240px;max-width:400px}
.search-wrap::before{content:'🔍';position:absolute;left:14px;top:50%;transform:translateY(-50%);
  font-size:14px;opacity:.5;pointer-events:none}
.search-input{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:var(--rs);
  padding:11px 16px 11px 40px;color:var(--text);font-size:13px;font-family:inherit;outline:none;
  transition:var(--tr)}
.search-input:focus{border-color:var(--border2);box-shadow:0 0 0 3px var(--glow)}
.search-input::placeholder{color:var(--text3)}
.filter-sel{background:var(--bg3);border:1px solid var(--border);border-radius:var(--rs);
  padding:11px 34px 11px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;
  cursor:pointer;transition:var(--tr);appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%237b7b9e' d='M5 7L1 3h8z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center}
.filter-sel:focus{border-color:var(--border2)}
.filter-sel option{background:var(--bg2);color:var(--text)}

/* ===== İSTATİSTİK KARTLARI ===== */
.stats{display:flex;gap:8px;padding:12px 40px 4px;flex-wrap:wrap}
.stat{background:var(--bg3);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;transition:var(--tr);position:relative;overflow:hidden;
  display:flex;align-items:center;gap:12px;flex:1;min-width:110px;cursor:default}
.stat:hover{transform:translateY(-1px);border-color:var(--border2);
  box-shadow:0 4px 16px rgba(124,106,239,0.1)}
.stat-icon{font-size:18px;flex-shrink:0;line-height:1}
.stat-info{display:flex;flex-direction:column;min-width:0}
.stat-val{font-size:20px;font-weight:800;line-height:1}
.stat-lbl{font-size:10px;color:var(--text2);text-transform:uppercase;
  letter-spacing:.6px;font-weight:600;margin-top:2px;white-space:nowrap}
/* Alt çizgi — hover'da görünür */
.stat::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  opacity:0;transition:var(--tr)}
.stat:hover::after{opacity:1}
/* Her stat için renk — val ve after ayrı ayrı */
.stat:nth-child(1) .stat-val{color:var(--accent2)}
.stat:nth-child(1)::after{background:var(--accent2)}
.stat:nth-child(2) .stat-val{color:var(--green)}
.stat:nth-child(2)::after{background:var(--green)}
.stat:nth-child(3) .stat-val{color:var(--orange)}
.stat:nth-child(3)::after{background:var(--orange)}
.stat:nth-child(4) .stat-val{color:var(--blue)}
.stat:nth-child(4)::after{background:var(--blue)}
.stat:nth-child(5) .stat-val{color:var(--yellow)}
.stat:nth-child(5)::after{background:var(--yellow)}
.stat:nth-child(6) .stat-val{color:var(--purple)}
.stat:nth-child(6)::after{background:var(--purple)}

/* ===== PROJE KARTLARI ===== */
.grid{padding:16px 40px 40px;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:18px;align-items:start}
/* 3:4 dikey kart — aspect-ratio ile yükseklik otomatik */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);
  padding:0;transition:transform .28s cubic-bezier(.4,0,.2,1),box-shadow .28s,
  border-color .25s;position:relative;overflow:hidden;user-select:none;
  aspect-ratio:3/4;display:flex;flex-direction:column;will-change:transform}
.card:hover{border-color:var(--border2);box-shadow:0 18px 44px rgba(0,0,0,0.45),
  0 0 0 1px rgba(14,165,233,0.15);
  transform:translateY(-8px) scale(1.025);z-index:5}
/* Arka plan görseli — cover ile kartı tamamen doldurur, kırpar ama boşluk bırakmaz */
.kart-bg-gorsel{position:absolute;inset:0;border-radius:inherit;
  background-size:cover;background-position:center;background-repeat:no-repeat;
  opacity:0.28;z-index:0;pointer-events:none}
/* Üst gradient — butonlar okunabilsin */
.kart-overlay-ust{position:absolute;top:0;left:0;right:0;height:70px;
  background:linear-gradient(to bottom,rgba(0,0,0,0.6) 0%,transparent 100%);
  z-index:0;pointer-events:none}
/* Alt gradient — başlık/bilgi okunabilsin */
.kart-overlay-alt{position:absolute;bottom:0;left:0;right:0;height:70%;
  background:linear-gradient(to top,rgba(0,0,0,0.82) 0%,rgba(0,0,0,0.5) 55%,transparent 100%);
  z-index:0;pointer-events:none}
/* İçerik elementleri z-index:1 — overlay'lerin (z-index:0) üstünde */
.card-actions-bar,.card-content,.kart-renk-popup,.kart-renk-btn{
  position:relative;z-index:1}
.drag-handle{position:absolute;top:8px;left:8px;width:22px;height:22px;
  display:none;align-items:center;justify-content:center;z-index:2;
  cursor:grab;color:rgba(255,255,255,0.7);font-size:13px;
  background:rgba(0,0,0,0.35);border-radius:5px;transition:var(--tr)}
.drag-handle:hover{color:#fff;background:rgba(0,0,0,0.55)}
.kanban-container .card{aspect-ratio:3/4}
.kanban-container .drag-handle{display:flex}
/* Üst aksiyon çubuğu */
.card-actions-bar{display:flex;justify-content:flex-end;align-items:center;
  gap:6px;padding:10px 10px 0;flex-shrink:0}
/* Alt içerik alanı — başlık butonların hemen altında */
.card-content{display:flex;flex-direction:column;flex:1;justify-content:flex-start;
  padding:8px 14px 12px;gap:8px;min-height:0}
/* Başlık — her zaman kart rengi (çerçeve rengi) ile aynı */
.card-title{font-size:14px;font-weight:700;letter-spacing:-.2px;line-height:1.3;
  color:var(--kart-renk,var(--text));transition:color .25s;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card.has-bg .card-title{color:var(--kart-renk);text-shadow:0 1px 4px rgba(0,0,0,0.7)}
/* Etiketler */
.kart-etiketler{display:flex;gap:5px;flex-wrap:nowrap;overflow:hidden;flex-shrink:0}
.kart-etiketler .tag{flex-shrink:0;font-size:9px;padding:2px 7px}
.card.has-bg .kart-etiketler .tag{background:rgba(255,255,255,0.15);color:rgba(255,255,255,0.9)}
/* Bilgi satırları */
.card-body{display:flex;flex-direction:column;gap:5px;flex-shrink:0}
.card-row{display:flex;align-items:center;gap:6px;font-size:12px;flex-shrink:0}
.card-row .icon{width:16px;text-align:center;font-size:12px;flex-shrink:0;opacity:0.75}
.card-row .value{color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card.has-bg .card-row .value{color:rgba(255,255,255,0.8);text-shadow:0 1px 3px rgba(0,0,0,0.5)}
.card-row a{color:var(--blue);text-decoration:none}
.card.has-bg .card-row a{color:rgba(255,255,255,0.8)}
.card-row a:hover{text-decoration:underline}
/* Not */
.card-note{font-size:11px;color:var(--text2);line-height:1.45;white-space:pre-wrap;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  flex-shrink:0;word-break:break-word;margin-bottom:6px}
.card.has-bg .card-note{color:rgba(255,255,255,0.65);text-shadow:0 1px 3px rgba(0,0,0,0.5)}
.card-note.acik{-webkit-line-clamp:unset;display:block}
.devamini-oku{font-size:10px;color:var(--accent2);cursor:pointer;
  display:block;background:none;border:none;padding:4px 0 0;font-family:inherit;
  transition:opacity .2s;margin-top:4px;border-top:1px dashed var(--border);
  opacity:.85}
.card.has-bg .devamini-oku{color:rgba(255,255,255,0.65)}
.devamini-oku:hover{opacity:1;text-decoration:underline}
/* Footer */
.card-footer{display:flex;justify-content:space-between;align-items:center;
  gap:6px;padding-top:6px;border-top:1px solid var(--border);flex-shrink:0;min-width:0}
.card-footer > .tag{max-width:62%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:9px;padding:2px 7px}
.card.has-bg .card-footer{border-top-color:rgba(255,255,255,0.12)}
.card-date{font-size:8px;color:var(--kart-renk,var(--text3));opacity:0.8;transition:color .25s}
.card.has-bg .card-date{color:var(--kart-renk);opacity:0.7}
/* Renk butonu — kart hover'da görünür */
/* ===== ETİKETLER ===== */
.tag{display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;
  font-size:11px;font-weight:600;letter-spacing:.3px}
.tag-bitti{background:rgba(16,185,129,0.12);color:var(--green)}
.tag-yarim{background:rgba(249,115,22,0.12);color:var(--orange)}
.tag-calisiyor{background:rgba(59,130,246,0.12);color:var(--blue)}
.tag-pasif{background:rgba(74,74,106,0.2);color:var(--text3)}
.tag-arsiv{background:rgba(240,194,70,0.12);color:var(--yellow)}
.tag-bulut{background:rgba(91,168,245,0.12);color:var(--blue)}
.tag-lokal{background:rgba(157,143,252,0.12);color:var(--accent2)}
.tag-custom{background:rgba(255,255,255,0.05);color:var(--text)}
[data-theme="light"] .tag-custom{background:rgba(0,0,0,0.05);}
.sleep-warning{color:var(--yellow);font-weight:600;font-size:11px;display:inline-flex;align-items:center;gap:4px}

/* ===== KANBAN GÖRÜNÜMÜ ===== */
.kanban-container{display:none;grid-template-columns:repeat(3,1fr);gap:20px;padding:12px 40px 40px;align-items:flex-start}
.kanban-column{background:rgba(255,255,255,0.02);border-radius:var(--r);padding:16px;min-height:400px;
  border:1px solid var(--border);display:flex;flex-direction:column;gap:12px}
.kanban-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;padding:0 8px}
.kanban-title{font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px}
.kanban-count{font-size:11px;background:var(--bg3);padding:2px 8px;border-radius:10px;color:var(--text2)}

/* ===== ARAMA VURGULAMA ===== */
mark{background:var(--yellow);color:#000;border-radius:2px;padding:0 2px}
.card[draggable="true"]{cursor:default}
.card.dragging{opacity:0.4;cursor:grabbing}
.kanban-cards{min-height:100px;transition:var(--tr);border-radius:var(--rs)}
.kanban-cards.drag-over{background:rgba(124,106,239,0.06);box-shadow:inset 0 0 10px rgba(0,0,0,0.1)}

/* ===== BOŞ DURUM ===== */
.empty{text-align:center;padding:80px 40px;color:var(--text3)}
.empty-icon{font-size:56px;margin-bottom:16px;opacity:.4}
.empty-text{font-size:15px;margin-bottom:24px;line-height:1.6}

/* ===== MODAL ===== */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,0.65);backdrop-filter:blur(10px);
  display:none;align-items:center;justify-content:center;z-index:1000;padding:20px}
.overlay.show{display:flex}
.modal{background:var(--bg-modal);border:1px solid var(--border);border-radius:18px;
  width:100%;max-width:560px;max-height:92vh;overflow-y:auto;
  box-shadow:0 24px 80px rgba(0,0,0,0.5);animation:modalIn .3s ease}
@keyframes modalIn{from{opacity:0;transform:translateY(16px) scale(.98)}to{opacity:1;transform:none}}
.modal-head{padding:24px 28px 18px;display:flex;justify-content:space-between;align-items:center;
  border-bottom:1px solid var(--border)}
.modal-head h2{font-size:18px;font-weight:700}
.modal-close{background:none;border:none;color:var(--text3);font-size:24px;cursor:pointer;
  padding:4px 8px;transition:var(--tr);border-radius:6px}
.modal-close:hover{color:var(--text);background:var(--bg3)}
.modal-body{padding:24px 28px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form-group{margin-bottom:18px}
.form-group label{display:block;font-size:11px;font-weight:600;color:var(--text2);
  margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;
  background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:var(--rs);
  padding:11px 14px;color:var(--text);font-size:14px;font-family:inherit;outline:none;
  transition:var(--tr)}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{
  border-color:var(--border2);box-shadow:0 0 0 3px var(--glow)}
.form-group textarea{resize:vertical;min-height:80px}
.form-group select{cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%237b7b9e' d='M5 7L1 3h8z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center}
.form-group select option{background:var(--bg2);color:var(--text)}
.form-sep{border:none;border-top:1px solid var(--border);margin:6px 0 18px}
.form-sep-label{font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;
  letter-spacing:1px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.form-sep-label::after{content:'';flex:1;height:1px;background:var(--border)}
.modal-foot{padding:14px 28px 24px;display:flex;gap:10px;justify-content:flex-end}

/* ===== TOAST (BİLDİRİM) ===== */
.toast{position:fixed;bottom:28px;right:28px;background:var(--bg2);border:1px solid var(--border);
  border-radius:var(--rs);padding:14px 22px;font-size:13px;font-weight:500;z-index:2000;
  box-shadow:0 8px 32px rgba(0,0,0,0.4);transform:translateY(100px);opacity:0;
  transition:all .4s cubic-bezier(.4,0,.2,1);display:flex;align-items:center;gap:10px}
.toast.show{transform:translateY(0);opacity:1}
.toast.ok{border-left:3px solid var(--green)}
.toast.err{border-left:3px solid var(--red)}

/* ===== DATALIST STİL ===== */
input::-webkit-calendar-picker-indicator{filter:invert(.7)}

/* ===== AYARLAR PANELİ ===== */
.ayar-modal .modal{max-width:700px}
.ayar-tabs{display:flex;gap:4px;margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:0}
.ayar-tab{padding:10px 20px;font-size:13px;font-weight:600;cursor:pointer;color:var(--text3);
  border-bottom:2px solid transparent;transition:var(--tr);background:none;border-top:none;
  border-left:none;border-right:none;font-family:inherit}
.ayar-tab:hover{color:var(--text)}
.ayar-tab.active{color:var(--accent2);border-bottom-color:var(--accent2)}
.ayar-sec{display:none}
.ayar-sec.active{display:block}
.ayar-list{display:flex;flex-direction:column;gap:8px;margin-bottom:16px;max-height:300px;overflow-y:auto}
.ayar-item{display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--bg3);
  border:1px solid var(--border);border-radius:var(--rs);transition:var(--tr)}
.ayar-item:hover{border-color:var(--border2)}
.ayar-item .ai-info{flex:1;min-width:0}
.ayar-item .ai-name{font-size:14px;font-weight:600}
.ayar-item .ai-detail{font-size:12px;color:var(--text2);margin-top:2px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.ayar-empty{text-align:center;padding:30px;color:var(--text3);font-size:13px}
.ayar-add-row{display:flex;gap:8px;flex-wrap:wrap}
.ayar-add-row input,.ayar-add-row select{flex:1;min-width:120px;background:rgba(255,255,255,0.03);
  border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;color:var(--text);
  font-size:13px;font-family:inherit;outline:none;transition:var(--tr)}
.ayar-add-row input:focus,.ayar-add-row select:focus{border-color:var(--border2);box-shadow:0 0 0 3px var(--glow)}
.ayar-add-row select{appearance:none;cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%237b7b9e' d='M5 7L1 3h8z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center}
.ayar-add-row select option{background:var(--bg2)}

.ayar-add-row select option{background:var(--bg2)}

/* ===== HIZLI IDE VE TASLAK STİLLERİ ===== */
.quick-ide-list{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
.quick-ide-btn{background:var(--bg3);border:1px solid var(--border);border-radius:20px;
  padding:5px 12px;font-size:12px;font-weight:500;cursor:pointer;transition:var(--tr);
  display:flex;align-items:center;gap:6px;user-select:none;color:var(--text2)}
.quick-ide-btn:hover{background:var(--bg-hover);border-color:var(--accent);color:var(--text);transform:translateY(-1px)}
.quick-ide-btn.active{background:rgba(124,106,239,0.15);border-color:var(--accent);color:var(--accent2)}
.draft-badge{display:none;background:rgba(240,194,70,0.1);color:var(--yellow);padding:3px 8px;
  border-radius:6px;font-size:11px;font-weight:600;margin-left:auto;border:1px solid rgba(240,194,70,0.2)}
.draft-badge.show{display:inline-block}

/* ===== UYGULAMA ARKA PLANI ===== */
#app-bg-katman{position:fixed;inset:0;z-index:-2;
  background-size:cover;background-position:center;
  filter:blur(14px) brightness(0.35);opacity:0;
  pointer-events:none;transition:opacity 0.5s}
#app-bg-katman.aktif{opacity:1}

/* ===== HIZLI EKLEME PANELİ ===== */
.hizli-ekle-panel{background:rgba(14,165,233,0.06);border:1px solid var(--border2);
  border-radius:var(--rs);padding:12px 14px;margin-top:8px;display:none;
  animation:modalIn .2s ease}
.hizli-ekle-panel.acik{display:block}
.hizli-ekle-panel .hep-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.hizli-ekle-panel input,.hizli-ekle-panel select{flex:1;min-width:100px;
  background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:8px;
  padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:var(--tr)}
.hizli-ekle-panel input:focus,.hizli-ekle-panel select:focus{border-color:var(--border2);box-shadow:0 0 0 2px var(--glow)}
.hizli-ekle-panel select{appearance:none;cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%237b7b9e' d='M5 7L1 3h8z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center}
.hizli-ekle-panel select option{background:var(--bg2)}
.btn-mini-ekle{width:28px;height:28px;border-radius:50%;background:rgba(14,165,233,0.15);
  border:1px solid var(--border2);color:var(--accent2);font-size:16px;font-weight:700;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
  transition:var(--tr);flex-shrink:0;line-height:1}
.btn-mini-ekle:hover{background:rgba(14,165,233,0.3);transform:scale(1.1)}

/* ===== RENK SEÇİCİ ===== */
.renk-secici-wrap{display:flex;flex-direction:column;gap:8px}
.renk-secici-ust{display:flex;align-items:center;gap:10px}
.renk-secici-wrap input[type="color"]{width:44px;height:36px;border:1px solid var(--border);
  border-radius:8px;cursor:pointer;background:none;padding:2px;transition:var(--tr)}
.renk-secici-wrap input[type="color"]:hover{border-color:var(--border2)}
.renk-sifirla{font-size:11px;color:var(--text3);cursor:pointer;padding:4px 8px;
  border-radius:6px;border:1px solid var(--border);background:var(--bg3);transition:var(--tr)}
.renk-sifirla:hover{color:var(--text);border-color:var(--text3)}
.renk-rastgele{font-size:11px;color:var(--accent2);cursor:pointer;padding:4px 8px;
  border-radius:6px;border:1px solid rgba(14,165,233,0.3);background:rgba(14,165,233,0.08);transition:var(--tr)}
.renk-rastgele:hover{background:rgba(14,165,233,0.18);border-color:var(--accent2)}
/* Hızlı renk paleti */
.renk-palet{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.renk-palet-btn{width:22px;height:22px;border-radius:50%;border:2px solid transparent;
  cursor:pointer;transition:var(--tr);flex-shrink:0;outline:none}
.renk-palet-btn:hover{transform:scale(1.25);border-color:rgba(255,255,255,0.5)}
.renk-palet-btn.aktif{border-color:#fff;transform:scale(1.2);box-shadow:0 0 0 2px rgba(255,255,255,0.3)}

/* ===== KART ÜZERİ RENK POPUP ===== */
.kart-renk-popup{position:absolute;top:8px;left:8px;z-index:10;
  background:var(--bg2);border:1px solid var(--border);border-radius:10px;
  padding:8px;display:none;flex-direction:column;gap:6px;
  box-shadow:0 8px 24px rgba(0,0,0,0.4);animation:modalIn .15s ease}
.kart-renk-popup.goster{display:flex}
.kart-renk-popup-palet{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}
.kart-renk-popup-btn{width:20px;height:20px;border-radius:50%;border:2px solid transparent;
  cursor:pointer;transition:var(--tr)}
.kart-renk-popup-btn:hover{transform:scale(1.3);border-color:rgba(255,255,255,0.6)}
.kart-renk-popup-btn.aktif{border-color:#fff;box-shadow:0 0 0 2px rgba(255,255,255,0.3)}
.kart-renk-popup-alt{display:flex;gap:4px;align-items:center;justify-content:space-between}
.kart-renk-popup input[type="color"]{width:28px;height:24px;border:1px solid var(--border);
  border-radius:5px;cursor:pointer;background:none;padding:1px}
.kart-renk-popup-sifirla{font-size:10px;color:var(--text3);cursor:pointer;padding:3px 6px;
  border-radius:5px;border:1px solid var(--border);background:var(--bg3);white-space:nowrap;transition:var(--tr)}
.kart-renk-popup-sifirla:hover{color:var(--text)}
/* Kart üzeri renk butonu */
.kart-renk-btn{position:absolute;bottom:8px;right:8px;z-index:5;
  width:22px;height:22px;border-radius:50%;border:2px solid rgba(255,255,255,0.2);
  cursor:pointer;transition:var(--tr);opacity:0;box-shadow:0 2px 6px rgba(0,0,0,0.3)}
.card:hover .kart-renk-btn{opacity:1}
.kart-renk-btn:hover{transform:scale(1.2);border-color:rgba(255,255,255,0.6)}

/* ===== GÖRSEL ÖNİZLEME ===== */
.gorsel-onizleme-wrap{display:none;margin-top:8px;position:relative}
.gorsel-onizleme-wrap.goster{display:block}
.gorsel-onizleme{width:100%;height:80px;border-radius:var(--rs);background-size:cover;
  background-position:center;border:1px solid var(--border);opacity:0.7}
.gorsel-kaldir-btn{position:absolute;top:6px;right:6px;background:rgba(239,68,68,0.8);
  color:#fff;border:none;border-radius:6px;padding:3px 8px;font-size:11px;
  cursor:pointer;transition:var(--tr)}
.gorsel-kaldir-btn:hover{background:var(--red)}

/* ===== RESPONSIVE ===== */
@media(max-width:900px){
  .kanban-container{grid-template-columns:1fr;gap:30px}
}
@media(max-width:640px){
  .header{flex-direction:column;align-items:flex-start;gap:15px;padding:20px 20px 0}
  .header-actions{width:100%;overflow-x:auto;padding-bottom:10px;justify-content:flex-start}
  .header-actions .btn{flex-shrink:0}
  .controls,.stats,.grid,.kanban-container{padding-left:16px;padding-right:16px}
  .grid{grid-template-columns:1fr}
  .form-row{grid-template-columns:1fr}
  .stats{grid-template-columns:repeat(2,1fr);padding-bottom:15px}
  .ayar-add-row{flex-direction:column}
  .modal{border-radius:0;max-height:100vh}
}
</style>
</head>
<body>

<!-- ===== UYGULAMA ARKA PLAN KATMANI ===== -->
<div id="app-bg-katman"></div>

<!-- ===== HEADER ===== -->
<header class="header">
  <div class="brand">
    <div class="brand-icon">🛠</div>
    <div><h1>IDE Proje Takip</h1><p>Projelerini, IDE'lerini ve hesaplarını tek yerden yönet</p></div>
  </div>
  <div class="header-actions">
    <button class="btn btn-icon" onclick="gorunumDegistir()" title="Görünüm Değiştir / Kanban" id="btn-view">📦</button>
    <button class="btn btn-icon" onclick="temaDegistir()" title="Temayı Değiştir" id="btn-tema">🌓</button>
    <button class="btn btn-ghost" onclick="ayarlarAc()">⚙ Ayarlar</button>
    <button class="btn btn-primary" onclick="modalAc()">+ Yeni Proje</button>
  </div>
</header>

<!-- ===== İSTATİSTİKLER ===== -->
<div class="stats" style="margin-top:16px">
  <div class="stat"><div class="stat-icon">📁</div><div class="stat-info"><div class="stat-val" id="s-toplam">0</div><div class="stat-lbl">Toplam</div></div></div>
  <div class="stat"><div class="stat-icon">⚡</div><div class="stat-info"><div class="stat-val" id="s-aktif">0</div><div class="stat-lbl">Devam Eden</div></div></div>
  <div class="stat"><div class="stat-icon">✅</div><div class="stat-info"><div class="stat-val" id="s-bitti">0</div><div class="stat-lbl">Bitti</div></div></div>
  <div class="stat"><div class="stat-icon">☁</div><div class="stat-info"><div class="stat-val" id="s-bulut">0</div><div class="stat-lbl">Bulut</div></div></div>
  <div class="stat"><div class="stat-icon">🛠</div><div class="stat-info"><div class="stat-val" id="s-ide">0</div><div class="stat-lbl">Farklı IDE</div></div></div>
  <div class="stat"><div class="stat-icon">👤</div><div class="stat-info"><div class="stat-val" id="s-hesap">0</div><div class="stat-lbl">Hesap</div></div></div>
</div>

<!-- ===== ARAMA VE FİLTRE ===== -->
<div class="controls">
  <div class="search-wrap">
    <input class="search-input" id="ara" placeholder="Proje, IDE veya hesap ara..." oninput="goster()">
  </div>
  <select class="filter-sel" id="f-durum" onchange="goster()">
    <option value="">Tüm Durumlar</option>
    <option value="Bitti">Bitti</option>
    <option value="Yarım Kaldı">Yarım Kaldı</option>
    <option value="Bitmedi ama çalışıyor">Bitmedi ama çalışıyor</option>
    <option value="Pasif">Pasif</option>
    <option value="Arşiv">Arşiv</option>
  </select>
  <select class="filter-sel" id="f-tur" onchange="goster()">
    <option value="">Tüm Türler</option><option value="Bulut">☁ Bulut</option>
    <option value="Lokal">🖥 Lokal</option>
  </select>
  <select class="filter-sel" id="f-ide" onchange="goster()">
    <option value="">Tüm IDE'ler</option>
  </select>
</div>

<!-- ===== PROJE KARTLARI ===== -->
<div class="grid" id="kartlar"></div>

<!-- ===== KANBAN GÖRÜNÜMÜ ===== -->
<div class="kanban-container" id="kanban">
  <div class="kanban-column" id="col-progress">
    <div class="kanban-head">
      <div class="kanban-title"><span style="color:var(--blue)">⏳</span> Devam Edenler</div>
      <div class="kanban-count" id="count-progress">0</div>
    </div>
    <div class="kanban-cards" id="cards-progress" ondragover="onDragOver(event)" ondragenter="onDragEnter(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, 'Yarım Kaldı')"></div>
  </div>
  <div class="kanban-column" id="col-done">
    <div class="kanban-head">
      <div class="kanban-title"><span style="color:var(--green)">✅</span> Tamamlananlar</div>
      <div class="kanban-count" id="count-done">0</div>
    </div>
    <div class="kanban-cards" id="cards-done" ondragover="onDragOver(event)" ondragenter="onDragEnter(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, 'Bitti')"></div>
  </div>
  <div class="kanban-column" id="col-other">
    <div class="kanban-head">
      <div class="kanban-title"><span style="color:var(--text3)">📦</span> Diğer / Arşiv</div>
      <div class="kanban-count" id="count-other">0</div>
    </div>
    <div class="kanban-cards" id="cards-other" ondragover="onDragOver(event)" ondragenter="onDragEnter(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, 'Pasif')"></div>
  </div>
</div>

<!-- ===== PROJE EKLEME/DÜZENLEME MODAL ===== -->
<div class="overlay" id="modal">
<div class="modal">
  <div class="modal-head">
    <div style="display:flex;align-items:center;gap:10px">
      <h2 id="modal-baslik">Yeni Proje</h2>
      <span class="draft-badge" id="draft-badge">📝 Taslak Yüklendi</span>
    </div>
    <button class="modal-close" onclick="modalKapat()">&times;</button>
  </div>
  <div class="modal-body">
    <input type="hidden" id="f-id">

    <!-- Proje Bilgileri -->
    <div class="form-group">
      <label>Proje Adı *</label>
      <input id="f-proje" placeholder="Projenizin adını girin" autofocus>
    </div>

    <div class="form-sep-label">💻 IDE Bilgileri</div>
    <div class="form-group" style="margin-bottom:12px">
      <div id="ide-quick-select" class="quick-ide-list"></div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>IDE Adı</label>
        <div style="display:flex;gap:6px;align-items:center">
          <input id="f-ide-adi" list="dl-ide" placeholder="Örn: Cursor, Firebase Studio..." style="flex:1">
          <button type="button" class="btn-mini-ekle" onclick="hizliIdeAc()" title="Hızlı IDE Ekle">+</button>
        </div>
        <datalist id="dl-ide"></datalist>
        <!-- Hızlı IDE Ekleme Paneli -->
        <div class="hizli-ekle-panel" id="hizli-ide-panel">
          <div style="font-size:11px;font-weight:600;color:var(--accent2);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Yeni IDE Ekle</div>
          <div class="hep-row">
            <input id="hi-adi" placeholder="IDE Adı">
            <select id="hi-turu"><option value="Lokal">🖥 Lokal</option><option value="Bulut">☁ Bulut</option></select>
            <input id="hi-url" placeholder="URL (opsiyonel)">
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button type="button" class="btn btn-primary btn-sm" onclick="hizliIdeKaydet()">Kaydet</button>
            <button type="button" class="btn btn-ghost btn-sm" onclick="hizliIdeKapat()">İptal</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>IDE Türü</label>
        <select id="f-ide-tur" onchange="turGuncelle()">
          <option value="Lokal">🖥 Lokal</option><option value="Bulut">☁ Bulut</option>
        </select>
      </div>
    </div>
    <div class="form-group" id="alan-url">
      <label>IDE URL (Bulut IDE için)</label>
      <input id="f-url" placeholder="https://...">
    </div>
    <div class="form-group" id="alan-lokal" style="display:none">
      <label>Lokal Dizin Yolu</label>
      <input id="f-lokal-yol" placeholder='örn: C:\Projeler\App  (tırnak işareti otomatik temizlenir)'>
    </div>
    <div class="form-group">
      <label>Deploy URL (Yayınlanan Site)</label>
      <input id="f-deploy-url" placeholder="https://myapp.vercel.app">
    </div>

    <div class="form-sep-label">👤 Hesap Bilgileri</div>
    <div class="form-row">
      <div class="form-group">
        <label>Hesap Adı</label>
        <div style="display:flex;gap:6px;align-items:center">
          <input id="f-hesap" list="dl-hesap" placeholder="Örn: Ana Hesap, Yedek..." style="flex:1">
          <button type="button" class="btn-mini-ekle" onclick="hizliHesapAc()" title="Hızlı Hesap Ekle">+</button>
        </div>
        <datalist id="dl-hesap"></datalist>
        <!-- Hızlı Hesap Ekleme Paneli -->
        <div class="hizli-ekle-panel" id="hizli-hesap-panel">
          <div style="font-size:11px;font-weight:600;color:var(--accent2);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Yeni Hesap Ekle</div>
          <div class="hep-row">
            <input id="hh-adi" placeholder="Hesap Adı">
            <input id="hh-email" placeholder="E-posta (opsiyonel)">
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button type="button" class="btn btn-primary btn-sm" onclick="hizliHesapKaydet()">Kaydet</button>
            <button type="button" class="btn btn-ghost btn-sm" onclick="hizliHesapKapat()">İptal</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>E-posta</label>
        <input id="f-email" list="dl-email" placeholder="ornek@email.com">
        <datalist id="dl-email"></datalist>
      </div>
    </div>

    <div class="form-sep-label">📋 Durum & Notlar</div>
    <div class="form-group">
      <label>Durum</label>
      <select id="f-durum-sec">
        <option value="Bitti">✅ Bitti</option>
        <option value="Yarım Kaldı">🚧 Yarım Kaldı</option>
        <option value="Bitmedi ama çalışıyor">⚙️ Bitmedi ama çalışıyor</option>
        <option value="Pasif">⏸ Pasif</option>
        <option value="Arşiv">📦 Arşiv</option>
      </select>
    </div>
    <div class="form-group">
      <label>Etiketler (Virgülle ayırın)</label>
      <input id="f-etiketler" placeholder="backend, api, yarımkaldı">
    </div>
    <div class="form-group">
      <label>Notlar</label>
      <textarea id="f-notlar" placeholder="Proje hakkında not, limit bilgisi, devredilecek vb..."></textarea>
    </div>

    <div class="form-sep-label">🎨 Görsel Kişiselleştirme</div>
    <div class="form-row">
      <div class="form-group">
        <label>Kart Çerçeve Rengi</label>
        <div class="renk-secici-wrap">
          <div class="renk-secici-ust">
            <input type="color" id="f-kart-rengi" value="#0ea5e9" title="Kart çerçeve rengi seç" oninput="this.dataset.auto='0';paletAktifGuncelle(this.value)">
            <button type="button" class="renk-rastgele" onclick="kartRengiRastgele()">🎲 Rastgele</button>
            <button type="button" class="renk-sifirla" onclick="kartRengiSifirla()">↺ Otomatik</button>
          </div>
          <div class="renk-palet" id="renk-palet-form"></div>
        </div>
      </div>
      <div class="form-group">
        <label>Kart Arka Plan Görseli</label>
        <div style="display:flex;gap:8px">
          <button type="button" class="btn btn-ghost btn-sm" onclick="kartGorseliSec()">🖼 Görsel Seç</button>
          <button type="button" class="btn btn-ghost btn-sm" id="btn-gorsel-kaldir" onclick="kartGorseliKaldir()" style="display:none">✕ Kaldır</button>
        </div>
        <input type="hidden" id="f-kart-gorseli">
        <div class="gorsel-onizleme-wrap" id="gorsel-onizleme-wrap">
          <div class="gorsel-onizleme" id="gorsel-onizleme"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="modal-foot">
    <button class="btn btn-ghost" onclick="taslakFormuTemizle()" id="btn-reset" style="margin-right:auto;display:none">Formu Sıfırla</button>
    <button class="btn btn-sm btn-danger" id="btn-modal-sil" onclick="modalSil()" style="display:none">🗑 Sil</button>
    <button class="btn btn-ghost" onclick="modalKapat()">İptal</button>
    <button class="btn btn-primary" onclick="kaydet()">Kaydet</button>
  </div>
</div>
</div>

<!-- ===== SİLME ONAY MODAL ===== -->
<div class="overlay" id="sil-modal">
<div class="modal" style="max-width:420px">
  <div class="modal-head"><h2>⚠ Silme Onayı</h2>
    <button class="modal-close" onclick="silKapat()">&times;</button></div>
  <div class="modal-body">
    <p id="sil-mesaj" style="font-size:14px;line-height:1.7"></p>
  </div>
  <div class="modal-foot">
    <button class="btn btn-ghost" onclick="silKapat()">İptal</button>
    <button class="btn btn-sm btn-danger" id="sil-btn">Evet, Sil</button>
  </div>
</div>
</div>

<!-- ===== AYARLAR MODAL ===== -->
<div class="overlay ayar-modal" id="ayar-modal">
<div class="modal">
  <div class="modal-head"><h2>⚙ IDE ve Hesap Yönetimi</h2>
    <button class="modal-close" onclick="ayarlarKapat()">&times;</button></div>
  <div class="modal-body">
    <p style="font-size:13px;color:var(--text2);margin-bottom:16px">Burada IDE ve hesaplarınızı önceden tanımlayabilirsiniz. Proje eklerken otomatik tamamlama olarak önerileceklerdir.</p>
    <div class="ayar-tabs">
      <button class="ayar-tab active" onclick="ayarSekme(0)">💻 IDE'ler</button>
      <button class="ayar-tab" onclick="ayarSekme(1)">👤 Hesaplar</button>
      <button class="ayar-tab" onclick="ayarSekme(2)">💾 Yedekleme</button>
      <button class="ayar-tab" onclick="ayarSekme(3)">🎨 Görünüm</button>
    </div>
    <!-- IDE Bölümü -->
    <div class="ayar-sec active" id="ayar-ide">
      <div class="ayar-add-row" style="margin-bottom:14px">
        <input id="ai-ide-adi" placeholder="IDE Adı (örn: Cursor)">
        <select id="ai-ide-tur"><option value="Lokal">🖥 Lokal</option><option value="Bulut">☁ Bulut</option></select>
        <input id="ai-ide-url" placeholder="URL (opsiyonel)">
        <button class="btn btn-primary btn-sm" onclick="ideEkleTanimli()">+ Ekle</button>
      </div>
      <div class="ayar-list" id="ayar-ide-list"></div>
    </div>
    <!-- Hesap Bölümü -->
    <div class="ayar-sec" id="ayar-hesap">
      <div class="ayar-add-row" style="margin-bottom:14px">
        <input id="ai-hesap-adi" placeholder="Hesap Adı (örn: Ana Hesap)">
        <input id="ai-hesap-email" placeholder="E-posta (opsiyonel)">
        <button class="btn btn-primary btn-sm" onclick="hesapEkleTanimli()">+ Ekle</button>
      </div>
      <div class="ayar-list" id="ayar-hesap-list"></div>
    </div>
    <!-- Yedekleme Bölümü -->
    <div class="ayar-sec" id="ayar-yedek">
      <div style="padding:10px;text-align:center">
        <p style="font-size:13px;color:var(--text2);margin-bottom:20px;line-height:1.6">Her değişiklikten sonra otomatik yedek alınır. Buradan ayrıca elle yedek alabilir, JSON olarak indirebilir veya eski yedeği yükleyebilirsiniz.</p>
        <button class="btn btn-primary" onclick="manuelYedekAl()">💾 Şimdi Yedekle</button>
        <br><br>
        <button class="btn btn-primary" onclick="disaAktar()">⬇ Yedeği İndir (Export)</button>
        <br><br>
        <button class="btn btn-primary" onclick="bulutaYedekle()">☁ Buluta Yedekle</button>
        <br><br>
        <button class="btn btn-ghost" onclick="buluttanGeriYukle()">☁ Buluttan Geri Yükle</button>
        <br><br>
        <div id="google-login-box" style="display:flex;justify-content:center;margin-bottom:14px"></div>
        <button class="btn btn-ghost" id="google-cikis-btn" onclick="googleCikis()" style="display:none">Google Çıkış</button>
        <br><br>
        <div style="position:relative;display:inline-block">
            <button class="btn btn-ghost">⬆ Yedek Yükle (Import)</button>
            <input type="file" id="f-import" accept=".json" onchange="iceAktar(event)" style="opacity:0;position:absolute;inset:0;cursor:pointer" title="JSON yedeği seç">
        </div>
        <div id="yedek-durum" style="font-size:12px;color:var(--text3);margin-top:16px"></div>
        <div id="bulut-durum" style="font-size:12px;color:var(--text3);margin-top:8px"></div>
      </div>
    </div>
    <!-- Görünüm Bölümü -->
    <div class="ayar-sec" id="ayar-gorunum">
      <div style="padding:10px">
        <p style="font-size:13px;color:var(--text2);margin-bottom:20px;line-height:1.6">Uygulamanın genel arka planına bir görsel veya logo ekleyebilirsiniz. Görsel bulanık ve soluk görünür.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:16px">
          <button class="btn btn-primary" onclick="appBgSec()">🖼 Arka Plan Görseli Seç</button>
          <button class="btn btn-ghost" onclick="appBgKaldir()">✕ Arka Planı Kaldır</button>
        </div>
        <div id="app-bg-onizleme" style="display:none;width:100%;height:100px;border-radius:var(--rs);background-size:cover;background-position:center;border:1px solid var(--border);opacity:0.6;margin-bottom:12px"></div>
        <p style="font-size:11px;color:var(--text3);text-align:center">Maksimum dosya boyutu: 2MB • JPG, PNG, GIF, WebP, SVG</p>
      </div>
    </div>
  </div>
</div>
</div>

<!-- ===== TOAST ===== -->
<div class="toast" id="toast"></div>

<script>
/* ===============================================
   GLOBAL VERİ (App objesinin içinde yönetilir)
   =============================================== */

/* ===============================================
   RENK PALETİ — Hızlı seçim için hazır renkler
   =============================================== */
const RENK_PALETI = [
  '#ef4444','#f97316','#f59e0b','#eab308','#84cc16',
  '#22c55e','#10b981','#14b8a6','#06b6d4','#0ea5e9',
  '#3b82f6','#6366f1','#8b5cf6','#a855f7','#d946ef',
  '#ec4899','#f43f5e','#64748b','#94a3b8','#ffffff'
];

function rastgeleRenk() {
  return RENK_PALETI[Math.floor(Math.random() * (RENK_PALETI.length - 2))]; // son 2 (gri/beyaz) hariç
}

/* ===============================================
   UYGULAMA DURUMU (STATE)
   =============================================== */
const App = {
  projeler: [],
  oneriVeri: {},
  tanimliIdeler: [],
  tanimliHesaplar: [],
  kanbanModu: false,
  taslakTimer: null,
  overlayTiklamaBaslangic: null,
  aktifRenkPopup: null,

  // UI Elementleri (Cache)
  get el() {
    return {
      ara: document.getElementById('ara'),
      kartlar: document.getElementById('kartlar'),
      kanban: document.getElementById('kanban'),
      modal: document.getElementById('modal'),
      ist: {
        toplam: document.getElementById('s-toplam'),
        aktif: document.getElementById('s-aktif'),
        bitti: document.getElementById('s-bitti'),
        bulut: document.getElementById('s-bulut'),
        ide: document.getElementById('s-ide'),
        hesap: document.getElementById('s-hesap')
      }
    };
  }
};

/* ===============================================
   YARDIMCI FONKSİYONLAR
   =============================================== */
const Utils = {
  getIdeIcon(adi) {
    if (!adi) return '🛠';
    const a = adi.toLowerCase();
    const icons = {
      cursor: '🔵', code: '🟦', vs: '🟦', replit: '🌀',
      firebase: '🔥', github: '🐙', codespace: '🐙',
      colab: '🔶', intellij: '🏮', pycharm: '🏮'
    };
    for (const key in icons) if (a.includes(key)) return icons[key];
    return '🛠';
  },

  esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
    ));
  },

  highlight(metin, ara) {
    if (!ara) return this.esc(metin);
    const re = new RegExp(`(${ara.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
    return this.esc(metin).replace(re, '<mark>$1</mark>');
  },

  async api(yol, metod = 'GET', veri = null) {
    const options = {
      method: metod,
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
    };
    if (veri) options.body = JSON.stringify(veri);
    const res = await fetch(yol, options);
    return res.json();
  },

  bildirim(msg, tip = 'ok') {
    const t = document.getElementById('toast');
    t.textContent = (tip === 'ok' ? '✅ ' : '❌ ') + msg;
    t.className = `toast ${tip} show`;
    setTimeout(() => t.classList.remove('show'), 2500);
  }
};

/* ===============================================
   VERİ YÜKLEME — Projeleri ve istatistikleri çeker
   =============================================== */
// In-flight promise cache — aynı anda birden fazla yukle() çağrısı sunucuyu ezmesin
let _yuklePromise = null;
let _yuklePromiseZaman = 0;
const YUKLE_THROTTLE_MS = 200;

async function yukle() {
  // 200ms içinde tekrar çağrıldıysa, aynı promise'ı paylaş
  const simdi = Date.now();
  if (_yuklePromise && (simdi - _yuklePromiseZaman) < YUKLE_THROTTLE_MS) {
    return _yuklePromise;
  }
  _yuklePromiseZaman = simdi;
  _yuklePromise = _yukleImpl();
  try { return await _yuklePromise; }
  finally { setTimeout(() => { _yuklePromise = null; }, YUKLE_THROTTLE_MS); }
}

async function _yukleImpl() {
  const sonuclar = await Promise.allSettled([
    Utils.api('/api/projeler'),
    Utils.api('/api/otomatik'),
    Utils.api('/api/tanimli/ideler'),
    Utils.api('/api/tanimli/hesaplar'),
    Utils.api('/api/istatistikler')
  ]);
  const hataVar = sonuclar.some(s => s.status === 'rejected');
  if (hataVar) {
    const ilkHata = sonuclar.find(s => s.status === 'rejected');
    console.error('Yükleme hatası:', ilkHata.reason);
    Utils.bildirim('Veri yüklenemedi, tekrar deneniyor...', 'err');
  }
  [App.projeler, App.oneriVeri, App.tanimliIdeler, App.tanimliHesaplar] = sonuclar.slice(0, 4).map(s => s.status === 'fulfilled' ? s.value : (s.status === 'fulfilled' ? s.value : []));
  // Eksik veriler için boş fallback
  if (!Array.isArray(App.projeler)) App.projeler = [];
  if (!App.oneriVeri || typeof App.oneriVeri !== 'object') App.oneriVeri = { ideler: [], hesaplar: [], emailler: [] };
  if (!Array.isArray(App.tanimliIdeler)) App.tanimliIdeler = [];
  if (!Array.isArray(App.tanimliHesaplar)) App.tanimliHesaplar = [];
  const ist = sonuclar[4].status === 'fulfilled' ? sonuclar[4].value : { toplam: 0, aktif: 0, bitti: 0, bulut: 0, ide_sayisi: 0, hesap_sayisi: 0 };
  const elements = App.el;

  elements.ist.toplam.textContent = ist.toplam;
  elements.ist.aktif.textContent = ist.aktif;
  elements.ist.bitti.textContent = ist.bitti;
  elements.ist.bulut.textContent = ist.bulut;
  elements.ist.ide.textContent = ist.ide_sayisi;
  elements.ist.hesap.textContent = ist.hesap_sayisi;

  const fi = document.getElementById('f-ide');
  const secili = fi.value;
  fi.innerHTML = '<option value="">Tüm IDE\'ler</option>' +
    App.oneriVeri.ideler.map(i => `<option value="${Utils.esc(i)}">${Utils.esc(i)}</option>`).join('');
  fi.value = secili;

  document.getElementById('dl-ide').innerHTML = App.oneriVeri.ideler.map(i => `<option value="${Utils.esc(i)}">`).join('');
  document.getElementById('dl-hesap').innerHTML = App.oneriVeri.hesaplar.map(h => `<option value="${Utils.esc(h)}">`).join('');
  document.getElementById('dl-email').innerHTML = App.oneriVeri.emailler.map(e => `<option value="${Utils.esc(e)}">`).join('');

  hizliIdeGoster();
  goster();
}

function goster() {
  const elements = App.el;
  const ara = elements.ara.value.toLowerCase();
  const fDurum = document.getElementById('f-durum').value;
  const fTur = document.getElementById('f-tur').value;
  const fIde = document.getElementById('f-ide').value;

  const liste = App.projeler.filter(p => {
    const metin = `${p.proje_adi} ${p.ide_adi} ${p.hesap_adi} ${p.notlar} ${p.hesap_email}`.toLowerCase();
    if (ara && !metin.includes(ara)) return false;
    if (fDurum && p.durum !== fDurum) return false;
    if (fTur && p.ide_turu !== fTur) return false;
    if (fIde && (p.ide_adi || '').toLowerCase() !== fIde.toLowerCase()) return false;
    return true;
  });

  elements.kartlar.style.display = App.kanbanModu ? 'none' : 'grid';
  elements.kanban.style.display = App.kanbanModu ? 'grid' : 'none';

  if (liste.length === 0) {
    elements.kartlar.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">📂</div>
      <div class="empty-text">${App.projeler.length === 0 ? 'Henüz hiç proje eklenmemiş.' : 'Filtreye uygun proje bulunamadı.'}</div>
    </div>`;
    return;
  }

  if (!App.kanbanModu) {
    elements.kartlar.innerHTML = liste.map(p => kartUret(p, ara)).join('');
  } else {
    const gruplar = {
      progress: liste.filter(p => p.durum === 'Yarım Kaldı' || p.durum === 'Bitmedi ama çalışıyor'),
      done: liste.filter(p => p.durum === 'Bitti'),
      other: liste.filter(p => p.durum === 'Pasif' || p.durum === 'Arşiv')
    };
    Object.keys(gruplar).forEach(key => {
      document.getElementById(`cards-${key}`).innerHTML = gruplar[key].map(p => kartUret(p, ara)).join('');
      document.getElementById(`count-${key}`).textContent = gruplar[key].length;
    });
  }
}

function kartUret(p, ara) {
  const statusMap = {
    'Bitti': 'tag-bitti', 'Yarım Kaldı': 'tag-yarim', 'Bitmedi ama çalışıyor': 'tag-calisiyor',
    'Pasif': 'tag-pasif', 'Arşiv': 'tag-arsiv'
  };
  const durumKisalt = {
    'Bitti': '✓ Bitti', 'Yarım Kaldı': '⏸ Yarım', 'Bitmedi ama çalışıyor': '⚙ Çalışıyor',
    'Pasif': '⏸ Pasif', 'Arşiv': '📦 Arşiv'
  };
  const durumClass = statusMap[p.durum] || 'tag-pasif';
  const durumGosterim = durumKisalt[p.durum] || p.durum;
  const color = durumClass.split('-')[1];
  const etiketler = p.etiketler
    ? `<div class="kart-etiketler">${p.etiketler.split(',').map(e => `<span class="tag tag-custom">#${Utils.highlight(e.trim(), ara)}</span>`).join('')}</div>`
    : '';

  const acBtn = p.ide_turu === 'Bulut'
    ? (p.ide_url ? `<button class="btn btn-primary btn-sm" onclick="window.open('${Utils.esc(p.ide_url)}', '_blank')">🚀</button>` : '')
    : (p.lokal_yol ? `<button class="btn btn-primary btn-sm" onclick="lokalAc('${Utils.esc(p.lokal_yol).replace(/\\/g, '\\\\')}')">💻</button>` : '');

  // Deploy butonu — deploy_url varsa göster
  const deployBtn = p.deploy_url
    ? `<button class="btn btn-success btn-sm" onclick="window.open('${Utils.esc(p.deploy_url)}', '_blank')" title="Deploy edilen siteyi aç">🌐</button>`
    : '';

  const archiveIcon = p.durum === 'Arşiv' ? '♻️' : '📦';
  const nextStatus = p.durum === 'Arşiv' ? 'Bitti' : 'Arşiv';

  // Kart çerçeve rengi ve başlık rengi: kullanıcı seçimi varsa onu kullan, yoksa durum rengine göre
  let borderStyle, renkDegiskeni;
  if (p.kart_rengi) {
    // Kullanıcı özel renk seçmişse
    borderStyle = `border: 2px solid ${p.kart_rengi}`;
    renkDegiskeni = `--kart-renk:${p.kart_rengi};`;
  } else {
    // Durum rengini kullan (hem border hem başlık için)
    const durumRenkleri = {
      'bitti': '#10b981', 'yarim': '#f97316', 'calisiyor': '#3b82f6',
      'pasif': '#4a546a', 'arsiv': '#f59e0b'
    };
    const durumRenk = durumRenkleri[color] || '#4a546a';
    borderStyle = `border: 2px solid ${durumRenk}`;
    renkDegiskeni = `--kart-renk:${durumRenk};`;
  }

  // Kart arka plan görseli
  const bgGorsel = p.kart_gorseli
    ? `<div class="kart-bg-gorsel" style="background-image:url('${p.kart_gorseli}')"></div>`
    : '';

  // Kart üzeri renk popup
  const mevcutRenk = p.kart_rengi || '';
  const paletHtml = RENK_PALETI.map(r =>
    `<button class="kart-renk-popup-btn ${r === mevcutRenk ? 'aktif' : ''}" style="background:${r}" title="${r}" onclick="kartRengiUygula(${p.id},'${r}',this)" type="button"></button>`
  ).join('');

  // Not: 120 karakterden uzunsa kırp, "devamını oku" butonu ekle
  const NOT_LIMIT = 120;
  let notHtml = '';
  if (p.notlar) {
    const uzun = p.notlar.length > NOT_LIMIT;
    const notId = `not-${p.id}`;
    notHtml = `
      <div class="card-note" id="${notId}">${Utils.highlight(p.notlar, ara)}</div>
      ${uzun ? `<button class="devamini-oku" onclick="notToggle('${notId}', this)" type="button">▾ devamını oku</button>` : ''}`;
  }

  return `
    <div class="card${p.kart_gorseli ? ' has-bg' : ''}" data-durum="${Utils.esc(p.durum || '')}" style="${renkDegiskeni}${borderStyle}" draggable="true" ondragstart="onDragStart(event, ${p.id})" ondragend="onDragEnd(event)" id="kart-${p.id}">
      ${bgGorsel}
      <div class="kart-overlay-ust"></div>
      <div class="kart-overlay-alt"></div>
      <div class="drag-handle" title="Sürüklemek için tutun">⠿</div>
      <div class="kart-renk-popup" id="renk-popup-${p.id}">
        <div class="kart-renk-popup-palet">${paletHtml}</div>
        <div class="kart-renk-popup-alt">
          <input type="color" value="${mevcutRenk || '#0ea5e9'}" title="Özel renk" onchange="kartRengiUygula(${p.id},this.value,null)">
          <button class="kart-renk-popup-sifirla" onclick="kartRengiUygula(${p.id},'',null)" type="button">↺ Otomatik</button>
        </div>
      </div>
      <div class="card-actions-bar">
        ${acBtn}
        ${deployBtn}
        <button class="btn-icon" onclick="hizliDurum(${p.id}, '${nextStatus}')" title="${nextStatus}">${archiveIcon}</button>
        <button class="btn-icon edit" onclick="duzenle(${p.id})">✏️</button>
        <button class="btn-icon danger" onclick="silOnay(${p.id}, '${Utils.esc(p.proje_adi).replace(/'/g, "&apos;")}')" title="Projeyi sil">🗑️</button>
      </div>
      <div class="card-content">
        <div class="card-title">${Utils.highlight(p.proje_adi, ara)}</div>
        ${etiketler}
        <div class="card-body">
          <div class="card-row">
            <span class="icon">${Utils.getIdeIcon(p.ide_adi)}</span>
            <span class="value" title="${Utils.esc(p.ide_adi)}">${Utils.highlight(p.ide_adi, ara)} <span class="tag ${p.ide_turu === 'Bulut' ? 'tag-bulut' : 'tag-lokal'}">${p.ide_turu === 'Bulut' ? '☁' : '🖥'}</span></span>
          </div>
          ${p.hesap_adi ? `<div class="card-row"><span class="icon">👤</span><span class="value" title="${Utils.esc(p.hesap_adi)}">${Utils.highlight(p.hesap_adi, ara)}</span></div>` : ''}
          ${notHtml}
        </div>
        <div class="card-footer">
          <span class="tag ${durumClass}" title="${Utils.esc(p.durum)}">${Utils.esc(durumGosterim)}</span>
          <span class="card-date">🕐 ${Utils.esc((p.son_guncelleme || '').split(' ')[0])}</span>
        </div>
      </div>
      <button class="kart-renk-btn" style="background:${mevcutRenk || 'rgba(128,128,128,0.35)'}" title="Renk değiştir" onclick="kartRenkPopupAc(event,${p.id})" type="button"></button>
    </div>`;
}

/* Not genişlet/daralt */
function notToggle(notId, btn) {
  const el = document.getElementById(notId);
  if (!el) return;
  const acik = el.classList.toggle('acik');
  btn.textContent = acik ? '▴ kapat' : '▾ devamını oku';
  // Kart yüksekliğini geçici olarak auto yap, sonra geri al
  const kart = el.closest('.card');
  if (kart) {
    if (acik) {
      kart.style.height = 'auto';
      kart.style.zIndex = '2';
    } else {
      kart.style.height = '';
      kart.style.zIndex = '';
    }
  }
}

async function hizliDurum(id, yeniDurum) {
  const p = App.projeler.find(x => x.id === id);
  if (!p) return;
  await Utils.api(`/api/projeler/${id}`, 'PUT', { ...p, durum: yeniDurum });
  Utils.bildirim(`Durum: ${yeniDurum}`);
  yukle();
}

/* KANBAN DRAG & DROP */
function onDragStart(e, id) {
  e.dataTransfer.setData('text/plain', String(id));
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.classList.add('dragging');
}

function onDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
  document.querySelectorAll('.kanban-cards').forEach(c => c.classList.remove('drag-over'));
}

function onDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const target = e.currentTarget;
  if (target.classList.contains('kanban-cards')) target.classList.add('drag-over');
}

function onDragEnter(e) {
  e.preventDefault();
  const target = e.currentTarget;
  if (target.classList.contains('kanban-cards')) target.classList.add('drag-over');
}

function onDragLeave(e) {
  // Sadece gerçek çıkışta (alt elemanlara geçişte değil) efekti kaldır
  if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) return;
  e.currentTarget.classList.remove('drag-over');
}

async function onDrop(e, yeniDurum) {
  e.preventDefault();
  const target = e.currentTarget;
  target.classList.remove('drag-over');
  const idStr = e.dataTransfer.getData('text/plain');
  const id = parseInt(idStr);
  if (!isNaN(id)) hizliDurum(id, yeniDurum);
}

/* ===============================================
   MODAL — Proje ekleme/düzenleme formu
   =============================================== */
function hizliIdeGoster() {
  const kutu = document.getElementById('ide-quick-select');
  if (!kutu || App.tanimliIdeler.length === 0) { if(kutu) kutu.style.display = 'none'; return; }
  kutu.style.display = 'flex';
  const secili = document.getElementById('f-ide-adi').value;
  kutu.innerHTML = App.tanimliIdeler.map(i => `
    <button type="button" class="quick-ide-btn ${i.ide_adi === secili ? 'active' : ''}" 
      onclick="ideHizliSec('${Utils.esc(i.ide_adi).replace(/'/g, "\\'")}', '${i.ide_turu}', '${Utils.esc(i.ide_url || '').replace(/'/g, "\\'")}')">
      ${i.ide_turu === 'Bulut' ? '☁' : '🖥'} ${Utils.esc(i.ide_adi)}
    </button>`).join('');
}

function ideHizliSec(adi, turu, url) {
  document.getElementById('f-ide-adi').value = adi;
  document.getElementById('f-ide-tur').value = turu;
  document.getElementById('f-url').value = url;
  turGuncelle();
  hizliIdeGoster();
  taslakKaydet();
}

function taslakFormuTemizle() {
  if (confirm('Taslağı silmek istediğinize emin misiniz?')) {
    localStorage.removeItem('proje_taslak');
    modalAc();
    Utils.bildirim('Form temizlendi');
  }
}

function taslakKaydet(manuel = false) {
  if (document.getElementById('f-id').value) return;
  clearTimeout(App.taslakTimer);
  App.taslakTimer = setTimeout(() => {
    if (!App.el.modal.classList.contains('show') && !manuel) return;
    const t = {
      proje_adi: document.getElementById('f-proje').value.trim(),
      ide_adi: document.getElementById('f-ide-adi').value.trim(),
      ide_turu: document.getElementById('f-ide-tur').value,
      ide_url: document.getElementById('f-url').value.trim(),
      hesap_adi: document.getElementById('f-hesap').value.trim(),
      hesap_email: document.getElementById('f-email').value.trim(),
      durum: document.getElementById('f-durum-sec').value,
      notlar: document.getElementById('f-notlar').value.trim(),
      etiketler: document.getElementById('f-etiketler').value.trim(),
      lokal_yol: document.getElementById('f-lokal-yol').value.trim(),
      deploy_url: document.getElementById('f-deploy-url').value.trim(),
      kart_rengi: renkKayitDegeri(),
    };
    if (!Object.values(t).some(v => v !== '' && v !== 'Lokal' && v !== 'Bitti')) return;
    try {
      localStorage.setItem('proje_taslak', JSON.stringify(t));
    } catch (quotaErr) {
      console.warn('Taslak kaydedilemedi (depolama dolu):', quotaErr);
    }
  }, 300);
}

function taslakYukle() {
  try {
    const raw = localStorage.getItem('proje_taslak');
    if (!raw) return false;
    const t = JSON.parse(raw);
    const sets = {
      'f-proje': t.proje_adi, 'f-ide-adi': t.ide_adi, 'f-ide-tur': t.ide_turu,
      'f-url': t.ide_url, 'f-hesap': t.hesap_adi, 'f-email': t.hesap_email,
      'f-durum-sec': t.durum, 'f-notlar': t.notlar, 'f-etiketler': t.etiketler,
      'f-lokal-yol': t.lokal_yol, 'f-deploy-url': t.deploy_url,
      'f-kart-rengi': t.kart_rengi || otomatikRenkDegeri()
    };
    Object.keys(sets).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = sets[id] || '';
    });
    renkInputDurumAyarla(t.kart_rengi || '');
    return true;
  } catch (e) { return false; }
}

function modalAc(id = null) {
  const formIds = ['f-id', 'f-proje', 'f-ide-adi', 'f-ide-tur', 'f-url', 'f-deploy-url', 'f-hesap', 'f-email', 'f-durum-sec', 'f-notlar', 'f-etiketler', 'f-lokal-yol'];
  // Hızlı panelleri kapat
  hizliIdeKapat(); hizliHesapKapat();
  if (id) {
    const p = App.projeler.find(x => x.id === id);
    if (!p) return;
    document.getElementById('modal-baslik').textContent = 'Proje Düzenle';
    document.getElementById('f-id').value = id;
    document.getElementById('f-proje').value = p.proje_adi;
    document.getElementById('f-ide-adi').value = p.ide_adi || '';
    document.getElementById('f-ide-tur').value = p.ide_turu || 'Lokal';
    document.getElementById('f-url').value = p.ide_url || '';
    document.getElementById('f-hesap').value = p.hesap_adi || '';
    document.getElementById('f-email').value = p.hesap_email || '';
    document.getElementById('f-durum-sec').value = p.durum || 'Bitti';
    document.getElementById('f-notlar').value = p.notlar || '';
    document.getElementById('f-etiketler').value = p.etiketler || '';
    document.getElementById('f-lokal-yol').value = p.lokal_yol || '';
    document.getElementById('f-deploy-url').value = p.deploy_url || '';
    // Renk ve görsel
    renkInputDurumAyarla(p.kart_rengi || '');
    document.getElementById('f-kart-gorseli').value = p.kart_gorseli || '';
    gorselOnizlemeGuncelle(p.kart_gorseli || '');
    document.getElementById('draft-badge').classList.remove('show');
    document.getElementById('btn-reset').style.display = 'none';
    document.getElementById('btn-modal-sil').style.display = 'inline-flex';
  } else {
    document.getElementById('modal-baslik').textContent = 'Yeni Proje';
    formIds.forEach(fid => {
        const el = document.getElementById(fid);
        if(el) el.value = fid === 'f-ide-tur' ? 'Lokal' : (fid === 'f-durum-sec' ? 'Bitti' : '');
    });
    renkInputDurumAyarla('');
    document.getElementById('f-kart-gorseli').value = '';
    gorselOnizlemeGuncelle('');
    const restored = taslakYukle();
    document.getElementById('draft-badge').classList.toggle('show', restored);
    document.getElementById('btn-reset').style.display = restored ? 'inline-flex' : 'none';
    document.getElementById('btn-modal-sil').style.display = 'none';
  }
  App.el.modal.classList.add('show');
  turGuncelle();
  hizliIdeGoster();
  paletOlustur();
  setTimeout(() => document.getElementById('f-proje').focus(), 150);
}

function turGuncelle() {
  const tur = document.getElementById('f-ide-tur').value;
  document.getElementById('alan-url').style.display = tur === 'Bulut' ? 'block' : 'none';
  document.getElementById('alan-lokal').style.display = tur === 'Lokal' ? 'block' : 'none';
}

function duzenle(id) { modalAc(id); }
function modalKapat() { App.el.modal.classList.remove('show'); }
function modalSil() {
  const id = document.getElementById('f-id').value;
  const adi = document.getElementById('f-proje').value.trim() || 'Bu proje';
  if (!id) return;
  modalKapat();
  silOnay(parseInt(id, 10), adi);
}

async function kaydet() {
  const adi = document.getElementById('f-proje').value.trim();
  if (!adi) { Utils.bildirim('Proje adı gerekli!', 'err'); return; }

  // Çift tıklama koruması — butonu geçici olarak kilitle
  const kaydetBtn = document.querySelector('#modal .modal-foot .btn-primary');
  if (kaydetBtn && kaydetBtn.disabled) return;
  if (kaydetBtn) kaydetBtn.disabled = true;
  const orijinalMetin = kaydetBtn ? kaydetBtn.textContent : '';

  const veri = {
    proje_adi: adi,
    ide_adi: document.getElementById('f-ide-adi').value.trim(),
    ide_turu: document.getElementById('f-ide-tur').value,
    ide_url: document.getElementById('f-url').value.trim(),
    hesap_adi: document.getElementById('f-hesap').value.trim(),
    hesap_email: document.getElementById('f-email').value.trim(),
    durum: document.getElementById('f-durum-sec').value,
    notlar: document.getElementById('f-notlar').value.trim(),
    etiketler: document.getElementById('f-etiketler').value.trim(),
    lokal_yol: document.getElementById('f-lokal-yol').value.trim(),
    deploy_url: document.getElementById('f-deploy-url').value.trim(),
    kart_rengi: renkKayitDegeri(),
    kart_gorseli: document.getElementById('f-kart-gorseli').value || '',
  };

  const id = document.getElementById('f-id').value;
  try {
    if (kaydetBtn) kaydetBtn.textContent = '⏳ Kaydediliyor...';
    if (id) await Utils.api(`/api/projeler/${id}`, 'PUT', veri);
    else {
      await Utils.api('/api/projeler', 'POST', veri);
      localStorage.removeItem('proje_taslak');
    }
    Utils.bildirim(id ? 'Proje güncellendi' : 'Proje eklendi');
    modalKapat();
    yukle();
  } catch (e) { Utils.bildirim('Hata oluştu!', 'err'); }
  finally {
    if (kaydetBtn) {
      kaydetBtn.disabled = false;
      kaydetBtn.textContent = orijinalMetin || 'Kaydet';
    }
  }
}

/* ===============================================
   SİLME — Onay penceresiyle proje silme
   =============================================== */
/* ===============================================
   SİLME — Onay penceresiyle proje silme
   =============================================== */
function silOnay(id, ad) {
  document.getElementById('sil-mesaj').innerHTML = `<strong>"${ad}"</strong> projesini silmek istediğinize emin misiniz?`;
  document.getElementById('sil-btn').onclick = async () => {
    await Utils.api(`/api/projeler/${id}`, 'DELETE');
    Utils.bildirim('Silindi');
    silKapat();
    yukle();
  };
  document.getElementById('sil-modal').classList.add('show');
}

function silKapat() { document.getElementById('sil-modal').classList.remove('show'); }

/* ===============================================
   AYARLAR PANELİ
   =============================================== */
async function ayarlarAc() {
  document.getElementById('ayar-modal').classList.add('show');
  // Açılışta sekme içeriklerine loading state göster
  ['ayar-ide-list', 'ayar-hesap-list', 'yedek-durum', 'bulut-durum'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.dataset.loading = '1';
  });
  try {
    await ayarVerileriYukle();
  } finally {
    ['ayar-ide-list', 'ayar-hesap-list', 'yedek-durum', 'bulut-durum'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.dataset.loading = '0';
    });
  }
  // Görünüm sekmesi önizlemesini güncelle
  const bg = localStorage.getItem('app_bg_image');
  const onizleme = document.getElementById('app-bg-onizleme');
  if (onizleme) {
    if (bg) { onizleme.style.backgroundImage = `url(${bg})`; onizleme.style.display = 'block'; }
    else onizleme.style.display = 'none';
  }
}

function ayarlarKapat() { document.getElementById('ayar-modal').classList.remove('show'); }

function ayarSekme(idx) {
  document.querySelectorAll('.ayar-tab').forEach((t, i) => t.classList.toggle('active', i === idx));
  document.querySelectorAll('.ayar-sec').forEach((s, i) => s.classList.toggle('active', i === idx));
}

async function ayarVerileriYukle() {
  const sonuclar = await Promise.allSettled([
    Utils.api('/api/tanimli/ideler'),
    Utils.api('/api/tanimli/hesaplar'),
    Utils.api('/api/diagnostic')
  ]);
  const [idelerR, hesaplarR, diagnosticR] = sonuclar;
  if (idelerR.status === 'rejected' || hesaplarR.status === 'rejected' || diagnosticR.status === 'rejected') {
    Utils.bildirim('Ayar verileri yüklenemedi', 'err');
  }
  App.tanimliIdeler = idelerR.status === 'fulfilled' ? idelerR.value : [];
  App.tanimliHesaplar = hesaplarR.status === 'fulfilled' ? hesaplarR.value : [];
  ayarListGoster('ide');
  ayarListGoster('hesap');
  if (diagnosticR.status === 'fulfilled') {
    const diagnostic = diagnosticR.value;
    const durum = diagnostic.backups || {};
    const kutu = document.getElementById('yedek-durum');
    if (kutu) {
      kutu.textContent = `Son yedek: ${durum.son_yedek_tarihi || 'henüz yok'} • JSON: ${durum.json_yedek_sayisi || 0} • DB: ${durum.db_yedek_sayisi || 0}`;
    }
    bulutDurumGoster(diagnostic.cloud || {});
  }
}

function bulutDurumGoster(cloud) {
  const kutu = document.getElementById('bulut-durum');
  if (!kutu) return;
  const son = cloud.son_sonuc || {};
  const hazirlik = cloud.aktif && cloud.hazir ? 'aktif' : 'kapalı/ayar bekliyor';
  const giris = cloud.giris_yapildi ? ` • Google: ${cloud.kullanici?.email || 'giriş yapıldı'}` : (cloud.google_giris_hazir ? ' • Google: giriş bekliyor' : ' • Google: ayar bekliyor');
  let sonIslem = '';
  if (son.zaman) {
    const boyut = son.boyut_kb ? ` ${son.boyut_kb}KB` : '';
    const oran = son.oran ? ` (%${100 - son.oran} tasarruf)` : '';
    sonIslem = ` • Son: ${son.durum} (${son.zaman})${boyut}${oran}`;
  }
  kutu.textContent = `Bulut: ${hazirlik} • Yol: ${cloud.kok_yol || 'ide_yonetici'}${giris}${sonIslem}`;
  googleButonHazirla(cloud);
}

function googleButonHazirla(cloud) {
  const kutu = document.getElementById('google-login-box');
  const cikis = document.getElementById('google-cikis-btn');
  if (!kutu || !cikis) return;
  cikis.style.display = cloud.giris_yapildi ? 'inline-flex' : 'none';
  kutu.style.display = cloud.giris_yapildi ? 'none' : 'flex';
  if (!cloud.google_giris_hazir) {
    kutu.innerHTML = '<span style="font-size:12px;color:var(--text3)">Google giriş için Firebase Web API Key gerekli</span>';
    return;
  }
  if (!window.google || kutu.dataset.ready === '1') return;
  google.accounts.id.initialize({
    client_id: cloud.google_client_id,
    callback: googleGirisTamamlandi
  });
  google.accounts.id.renderButton(kutu, { theme: 'outline', size: 'large', text: 'signin_with', shape: 'rectangular' });
  kutu.dataset.ready = '1';
}

async function googleGirisTamamlandi(response) {
  const sonuc = await Utils.api('/api/auth/google', 'POST', { credential: response.credential });
  if (sonuc.ok) {
    Utils.bildirim('Google girişi tamamlandı');
    const cloud = await Utils.api('/api/bulut/durum');
    bulutDurumGoster(cloud);
  } else {
    Utils.bildirim('Google girişi tamamlanamadı', 'err');
  }
}

async function googleCikis() {
  await Utils.api('/api/auth/cikis', 'POST', {});
  const kutu = document.getElementById('google-login-box');
  if (kutu) {
    kutu.innerHTML = '';
    kutu.dataset.ready = '0';
  }
  const cloud = await Utils.api('/api/bulut/durum');
  bulutDurumGoster(cloud);
  Utils.bildirim('Google çıkışı yapıldı');
}

function ayarListGoster(tip) {
  const isIde = tip === 'ide';
  const liste = isIde ? App.tanimliIdeler : App.tanimliHesaplar;
  const kutu = document.getElementById(`ayar-${tip}-list`);
  if (liste.length === 0) { 
    kutu.innerHTML = `<div class="ayar-empty">Henüz ${isIde ? 'IDE' : 'hesap'} tanımlanmamış</div>`; 
    return; 
  }
  kutu.innerHTML = liste.map(item => `
    <div class="ayar-item">
      <span style="font-size:20px">${isIde ? (item.ide_turu === 'Bulut' ? '☁' : '🖥') : '👤'}</span>
      <div class="ai-info">
        <div class="ai-name">${Utils.esc(isIde ? item.ide_adi : item.hesap_adi)} 
          ${isIde ? `<span class="tag ${item.ide_turu === 'Bulut' ? 'tag-bulut' : 'tag-lokal'}" style="margin-left:4px">${item.ide_turu}</span>` : ''}
        </div>
        <div class="ai-detail">${Utils.esc(isIde ? item.ide_url : item.hesap_email)}</div>
      </div>
      <button class="btn-icon danger" onclick="${isIde ? 'ideSil' : 'hesapSil'}Tanimli(${item.id})">🗑️</button>
    </div>`).join('');
}

async function ideEkleTanimli() {
  const adi = document.getElementById('ai-ide-adi').value.trim();
  if(!adi) { Utils.bildirim('Ad gerekli!','err'); return; }
  await Utils.api('/api/tanimli/ideler', 'POST', { 
    ide_adi: adi, 
    ide_turu: document.getElementById('ai-ide-tur').value, 
    ide_url: document.getElementById('ai-ide-url').value.trim() 
  });
  document.getElementById('ai-ide-adi').value = ''; 
  yukle(); 
  ayarVerileriYukle();
}

async function ideSilTanimli(id) { await Utils.api(`/api/tanimli/ideler/${id}`, 'DELETE'); yukle(); ayarVerileriYukle(); }

async function hesapEkleTanimli() {
  const adi = document.getElementById('ai-hesap-adi').value.trim();
  if(!adi) { Utils.bildirim('Ad gerekli!','err'); return; }
  await Utils.api('/api/tanimli/hesaplar', 'POST', { 
    hesap_adi: adi, 
    hesap_email: document.getElementById('ai-hesap-email').value.trim() 
  });
  document.getElementById('ai-hesap-adi').value = ''; 
  yukle(); 
  ayarVerileriYukle();
}

async function hesapSilTanimli(id) { await Utils.api(`/api/tanimli/hesaplar/${id}`, 'DELETE'); yukle(); ayarVerileriYukle(); }

/* ===============================================
   KART RENGİ VE GÖRSELİ
   =============================================== */
function otomatikRenkDegeri() {
  return '#0ea5e9';
}

function renkInputDurumAyarla(renk) {
  const input = document.getElementById('f-kart-rengi');
  if (!input) return;
  input.dataset.auto = renk ? '0' : '1';
  input.value = renk || otomatikRenkDegeri();
  paletAktifGuncelle(renk || '');
}

function renkKayitDegeri() {
  const input = document.getElementById('f-kart-rengi');
  if (!input || input.dataset.auto === '1') return '';
  return input.value || '';
}

function kartRengiSifirla() {
  // Boş string göndererek DB'de kart_rengi temizlenir; kart durum rengine döner
  renkInputDurumAyarla('');
}

function kartRengiRastgele() {
  const renk = rastgeleRenk();
  const input = document.getElementById('f-kart-rengi');
  input.dataset.auto = '0';
  input.value = renk;
  paletAktifGuncelle(renk);
}

/* Form içi palet oluştur ve aktif rengi işaretle */
function paletOlustur() {
  const kutu = document.getElementById('renk-palet-form');
  if (!kutu) return;
  const mevcutRenk = document.getElementById('f-kart-rengi').value;
  kutu.innerHTML = RENK_PALETI.map(r =>
    `<button type="button" class="renk-palet-btn ${r === mevcutRenk ? 'aktif' : ''}"
      style="background:${r}" title="${r}"
      onclick="paletRenkSec('${r}')"></button>`
  ).join('');
}

function paletRenkSec(renk) {
  const input = document.getElementById('f-kart-rengi');
  input.dataset.auto = '0';
  input.value = renk;
  paletAktifGuncelle(renk);
}

function paletAktifGuncelle(renk) {
  document.querySelectorAll('#renk-palet-form .renk-palet-btn').forEach(btn => {
    btn.classList.toggle('aktif', btn.title === renk);
  });
}

/* Kart üzeri popup aç/kapat */
function kartRenkPopupAc(e, id) {
  e.stopPropagation();
  // Açık başka popup varsa kapat
  if (App.aktifRenkPopup && App.aktifRenkPopup !== id) {
    const eski = document.getElementById(`renk-popup-${App.aktifRenkPopup}`);
    if (eski) eski.classList.remove('goster');
  }
  const popup = document.getElementById(`renk-popup-${id}`);
  if (!popup) return;
  const acik = popup.classList.contains('goster');
  popup.classList.toggle('goster', !acik);
  App.aktifRenkPopup = acik ? null : id;
}

/* Kart üzerinden rengi anında kaydet */
async function kartRengiUygula(id, renk, buton) {
  const p = App.projeler.find(x => x.id === id);
  if (!p) return;
  // Popup'taki aktif butonu güncelle
  const popup = document.getElementById(`renk-popup-${id}`);
  if (popup && buton) {
    popup.querySelectorAll('.kart-renk-popup-btn').forEach(b => b.classList.remove('aktif'));
    if (renk) buton.classList.add('aktif');
  }
  // Kart border, başlık rengi ve renk butonunu anında güncelle (yeniden render beklemeden)
  const kart = document.getElementById(`kart-${id}`);
  if (kart) {
    // data-durum attribute'tan durum bilgisi al (kırılgan className araması yerine)
    const durumRenkleri = { 'Bitti': '#10b981', 'Yarım Kaldı': '#f97316', 'Bitmedi ama çalışıyor': '#3b82f6', 'Pasif': '#4a546a', 'Arşiv': '#f59e0b' };
    const durumRenk = durumRenkleri[kart.dataset.durum] || '#4a546a';
    if (renk) {
      kart.style.border = `2px solid ${renk}`;
    } else {
      kart.style.border = `2px solid ${durumRenk}`;
    }
    // Başlık ve tarih rengini CSS değişkeniyle güncelle
    kart.style.setProperty('--kart-renk', renk || durumRenk);
    const renkBtn = kart.querySelector('.kart-renk-btn');
    if (renkBtn) renkBtn.style.background = renk || 'rgba(255,255,255,0.15)';
  }
  // Popup'u kapat
  if (popup) popup.classList.remove('goster');
  App.aktifRenkPopup = null;
  // API'ye kaydet
  await Utils.api(`/api/projeler/${id}`, 'PUT', { ...p, kart_rengi: renk });
  // Lokal state güncelle (tam reload yapmadan)
  const idx = App.projeler.findIndex(x => x.id === id);
  if (idx !== -1) App.projeler[idx] = { ...App.projeler[idx], kart_rengi: renk };
}

function gorselOnizlemeGuncelle(dataUrl) {
  const wrap = document.getElementById('gorsel-onizleme-wrap');
  const onizleme = document.getElementById('gorsel-onizleme');
  const kaldirBtn = document.getElementById('btn-gorsel-kaldir');
  if (dataUrl) {
    onizleme.style.backgroundImage = `url(${dataUrl})`;
    wrap.classList.add('goster');
    kaldirBtn.style.display = 'inline-flex';
  } else {
    onizleme.style.backgroundImage = '';
    wrap.classList.remove('goster');
    kaldirBtn.style.display = 'none';
  }
}

function kartGorseliSec() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.onchange = (e) => {
    const dosya = e.target.files[0];
    if (!dosya) return;
    if (dosya.size > 2 * 1024 * 1024) {
      Utils.bildirim('Görsel 2MB\'dan büyük olamaz!', 'err');
      return;
    }
    if (dosya.size > 500 * 1024) {
      Utils.bildirim('Görsel büyük, yükleme yavaş olabilir', 'ok');
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      document.getElementById('f-kart-gorseli').value = ev.target.result;
      gorselOnizlemeGuncelle(ev.target.result);
    };
    reader.readAsDataURL(dosya);
  };
  input.click();
}

function kartGorseliKaldir() {
  document.getElementById('f-kart-gorseli').value = '';
  gorselOnizlemeGuncelle('');
}

/* ===============================================
   UYGULAMA ARKA PLANI
   =============================================== */
function appBgSec() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.onchange = (e) => {
    const dosya = e.target.files[0];
    if (!dosya) return;
    if (dosya.size > 2 * 1024 * 1024) {
      Utils.bildirim('Görsel 2MB\'dan büyük olamaz!', 'err');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        localStorage.setItem('app_bg_image', ev.target.result);
        appBgUygula(ev.target.result);
        Utils.bildirim('Arka plan güncellendi');
      } catch (quotaErr) {
        // QuotaExceededError veya benzer — büyük görsel
        Utils.bildirim('Arka plan görseli kaydedilemedi (depolama dolu)', 'err');
      }
    };
    reader.readAsDataURL(dosya);
  };
  input.click();
}

function appBgUygula(dataUrl) {
  const katman = document.getElementById('app-bg-katman');
  if (dataUrl) {
    katman.style.backgroundImage = `url(${dataUrl})`;
    katman.classList.add('aktif');
    // Ayarlar önizlemesi
    const onizleme = document.getElementById('app-bg-onizleme');
    if (onizleme) {
      onizleme.style.backgroundImage = `url(${dataUrl})`;
      onizleme.style.display = 'block';
    }
  } else {
    katman.style.backgroundImage = '';
    katman.classList.remove('aktif');
    const onizleme = document.getElementById('app-bg-onizleme');
    if (onizleme) onizleme.style.display = 'none';
  }
}

function appBgKaldir() {
  localStorage.removeItem('app_bg_image');
  appBgUygula('');
  Utils.bildirim('Arka plan kaldırıldı');
}

/* ===============================================
   HIZLI IDE / HESAP EKLEME (FORM İÇİ)
   =============================================== */
function hizliIdeAc() {
  const panel = document.getElementById('hizli-ide-panel');
  const acik = panel.classList.contains('acik');
  hizliHesapKapat();
  panel.classList.toggle('acik', !acik);
  if (!acik) setTimeout(() => document.getElementById('hi-adi').focus(), 50);
}

function hizliIdeKapat() {
  const panel = document.getElementById('hizli-ide-panel');
  if (panel) {
    panel.classList.remove('acik');
    document.getElementById('hi-adi').value = '';
    document.getElementById('hi-url').value = '';
    document.getElementById('hi-turu').value = 'Lokal';
  }
}

async function hizliIdeKaydet() {
  const adi = document.getElementById('hi-adi').value.trim();
  if (!adi) { Utils.bildirim('IDE adı gerekli!', 'err'); return; }
  await Utils.api('/api/tanimli/ideler', 'POST', {
    ide_adi: adi,
    ide_turu: document.getElementById('hi-turu').value,
    ide_url: document.getElementById('hi-url').value.trim()
  });
  await yukle();
  document.getElementById('f-ide-adi').value = adi;
  hizliIdeKapat();
  Utils.bildirim(`"${adi}" IDE eklendi`);
}

function hizliHesapAc() {
  const panel = document.getElementById('hizli-hesap-panel');
  const acik = panel.classList.contains('acik');
  hizliIdeKapat();
  panel.classList.toggle('acik', !acik);
  if (!acik) setTimeout(() => document.getElementById('hh-adi').focus(), 50);
}

function hizliHesapKapat() {
  const panel = document.getElementById('hizli-hesap-panel');
  if (panel) {
    panel.classList.remove('acik');
    document.getElementById('hh-adi').value = '';
    document.getElementById('hh-email').value = '';
  }
}

async function hizliHesapKaydet() {
  const adi = document.getElementById('hh-adi').value.trim();
  if (!adi) { Utils.bildirim('Hesap adı gerekli!', 'err'); return; }
  await Utils.api('/api/tanimli/hesaplar', 'POST', {
    hesap_adi: adi,
    hesap_email: document.getElementById('hh-email').value.trim()
  });
  await yukle();
  document.getElementById('f-hesap').value = adi;
  hizliHesapKapat();
  Utils.bildirim(`"${adi}" hesabı eklendi`);
}

/* ===============================================
   DİĞER ÖZELLİKLER
   =============================================== */
function temaKontrol() {
  const isLight = localStorage.getItem('ide_tema') === 'light';
  if (isLight) {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  document.getElementById('btn-tema').textContent = isLight ? '🌙' : '🌓';
}

function temaDegistir() {
  const current = localStorage.getItem('ide_tema');
  localStorage.setItem('ide_tema', current === 'light' ? 'dark' : 'light');
  temaKontrol();
}

function sistemiSifirla() {
  if (confirm('DİKKAT: Tüm taslaklar ve tema ayarları temizlenecek. Kayıtlı projeleriniz silinmez.')) {
    localStorage.clear();
    location.reload();
  }
}

async function lokalAc(yol) {
  const res = await Utils.api('/api/ac', 'POST', { yol });
  Utils.bildirim(res.hata ? 'Dizin açılamadı!' : 'Dizin açıldı', res.hata ? 'err' : 'ok');
}

async function disaAktar() {
  const data = await Utils.api('/api/export');
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `ide_yedek_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
}

async function manuelYedekAl() {
  const sonuc = await Utils.api('/api/yedek-al', 'POST', {});
  const durum = sonuc.durum || {};
  const kutu = document.getElementById('yedek-durum');
  if (kutu) {
    kutu.textContent = `Son yedek: ${durum.son_yedek_tarihi || 'az önce'} • JSON: ${durum.json_yedek_sayisi || 0} • DB: ${durum.db_yedek_sayisi || 0}`;
  }
  Utils.bildirim('Yedek alındı');
}

async function bulutaYedekle() {
  const sonuc = await Utils.api('/api/bulut/yedekle', 'POST', {});
  const cloud = await Utils.api('/api/bulut/durum');
  bulutDurumGoster(cloud);
  if (sonuc.durum === 'Tamam' || sonuc.durum === 'Kısmi') {
    Utils.bildirim('Bulut yedeği alındı');
  } else {
    Utils.bildirim('Bulut ayarı eksik veya bağlantı hatası', 'err');
  }
}

async function buluttanGeriYukle() {
  if (!confirm('Buluttaki son yedek yerel verilerin üzerine yazılacak. Devam edilsin mi?')) return;
  const sonuc = await Utils.api('/api/bulut/geri-yukle', 'POST', {});
  if (sonuc.ok) {
    Utils.bildirim('Bulut yedeği geri yüklendi');
    ayarVerileriYukle();
    yukle();
  } else {
    Utils.bildirim('Buluttan geri yüklenemedi', 'err');
  }
}

async function iceAktar(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (event) => {
    try {
      await Utils.api('/api/import', 'POST', JSON.parse(event.target.result));
      Utils.bildirim('Yükleme başarılı');
      ayarlarKapat(); 
      yukle();
    } catch (err) { Utils.bildirim('Hata: Geçersiz dosya', 'err'); }
  };
  reader.readAsText(file);
}

function gorunumDegistir() { 
  App.kanbanModu = !App.kanbanModu; 
  document.getElementById('btn-view').textContent = App.kanbanModu ? '🔲' : '📦'; 
  goster(); 
}

/* ===============================================
   EVENT LISTENERS VE BAŞLANGIÇ
   =============================================== */
window.addEventListener('input', e => {
  if (e.target.closest('.modal-body')) {
    taslakKaydet();
    if (['f-ide-adi', 'f-proje'].includes(e.target.id)) hizliIdeGoster();
    if (e.target.id === 'f-kart-rengi') paletAktifGuncelle(e.target.value);
  }
});

window.addEventListener('change', e => { if (e.target.closest('.modal-body')) taslakKaydet(); });

// Kart renk popup'unu dışarı tıklayınca kapat
document.addEventListener('click', e => {
  if (App.aktifRenkPopup !== null) {
    const popup = document.getElementById(`renk-popup-${App.aktifRenkPopup}`);
    if (popup && !popup.contains(e.target) && !e.target.classList.contains('kart-renk-btn')) {
      popup.classList.remove('goster');
      App.aktifRenkPopup = null;
    }
  }
});

// Lokal dizin yolu — tırnak temizleme (Windows "Yol olarak kopyala" uyumluluğu)
document.addEventListener('DOMContentLoaded', () => {
  const lokalYolInput = document.getElementById('f-lokal-yol');
  if (lokalYolInput) {
    lokalYolInput.addEventListener('paste', function(e) {
      e.preventDefault();
      const yapistirilan = (e.clipboardData || window.clipboardData).getData('text');
      this.value = yapistirilan.trim().replace(/^["']+|["']+$/g, '');
    });
    lokalYolInput.addEventListener('input', function() {
      const temiz = this.value.replace(/^["']+|["']+$/g, '');
      if (temiz !== this.value) this.value = temiz;
    });
  }
});

document.querySelectorAll('.overlay').forEach(o => {
  o.addEventListener('mousedown', e => App.overlayTiklamaBaslangic = e.target);
  o.addEventListener('click', e => {
    if (e.target === o && App.overlayTiklamaBaslangic === o) {
      if (o.id === 'modal') modalKapat();
      else if (o.id === 'sil-modal') silKapat();
      else if (o.id === 'ayar-modal') ayarlarKapat();
    }
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') ['modal', 'sil-modal', 'ayar-modal'].forEach(id => document.getElementById(id).classList.remove('show'));
});

// Başlangıç
temaKontrol();
yukle();

// Uygulama arka planını localStorage'dan yükle
(function() {
  const bg = localStorage.getItem('app_bg_image');
  if (bg) appBgUygula(bg);
})();

window.addEventListener('unload', () => {
  try {
    navigator.sendBeacon('/api/kapat', '');
  } catch (err) {}
});
</script>
</body>
</html>"""


def sunucuyu_kapat():
    """Arka planda çalışan HTTP sunucusunu güvenli biçimde kapatır."""
    if GLOBAL_SUNUCU is not None:
        GLOBAL_SUNUCU.shutdown()


# ============================================================
# ANA GİRİŞ NOKTASI — Sunucuyu başlat ve tarayıcıyı aç
# ============================================================

if __name__ == "__main__":
    # Açılışta DB'yi kontrol et, gerekiyorsa son yedekten toparla.
    veritabani_kurtarmayi_dene()
    tablolari_olustur()
    otomatik_yedek_al("acilis")

    port = SUNUCU_PORT
    sunucu = None

    # Port meşgulse bir sonrakini dene (en fazla 10 deneme)
    for deneme in range(10):
        try:
            sunucu = HTTPServer(("127.0.0.1", port), IdeYoneticiHandler)
            break
        except OSError:
            print(f"  Port {port} meşgul, {port + 1} deneniyor...")
            port += 1

    if sunucu is None:
        print("  Uygun port bulunamadı!")
        # .pyw konsolsuz çalışır — input() takılır. 3 sn bekle ve çık.
        try:
            import time
            time.sleep(3)
        except Exception:
            pass
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    tarayici_url = f"{url}/?v={datetime.now().strftime('%Y%m%d%H%M%S')}"
    GLOBAL_SUNUCU = sunucu
    print("=" * 55)
    print("   IDE Proje Takip Sistemi başlatıldı!")
    print(f"   Adres: {url}")
    print("   Kapatmak için: Ctrl+C veya bu pencereyi kapatın")
    print("=" * 55)

    # Tarayıcıyı kısa bir gecikmeyle aç (sunucunun hazır olmasını bekle)
    threading.Timer(0.5, lambda: webbrowser.open(tarayici_url)).start()

    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\n  Sunucu kapatılıyor...")
        sunucu.shutdown()


