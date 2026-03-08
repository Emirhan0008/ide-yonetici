#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║               IDE PROJE TAKİP SİSTEMİ v2.0                  ║
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
import webbrowser
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ============================================================
# VERİTABANI AYARLARI
# Veritabanı dosyası, bu Python dosyasıyla aynı dizinde oluşturulur.
# ============================================================
VERITABANI_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ide_yonetici.db")
SUNUCU_PORT = 8700  # Varsayılan port numarası


def veritabani_baglantisi():
    """SQLite veritabanına bağlantı oluşturur ve döndürür."""
    baglanti = sqlite3.connect(VERITABANI_YOLU)
    baglanti.row_factory = sqlite3.Row  # Sütun ismiyle erişim için
    return baglanti


def tablolari_olustur():
    """
    Veritabanı tablolarını oluşturur:
    - projeler: Ana proje kayıtları
    - tanimli_ideler: Önceden tanımlanmış IDE listesi
    - tanimli_hesaplar: Önceden tanımlanmış hesap listesi
    """
    baglanti = veritabani_baglantisi()
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
    # Mevcut veritabanlarına yeni sütunları sorunsuz eklemek için (Migration)
    try: baglanti.execute("ALTER TABLE projeler ADD COLUMN etiketler TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass
    try: baglanti.execute("ALTER TABLE projeler ADD COLUMN lokal_yol TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass

    # Önceden tanımlı IDE'ler tablosu
    baglanti.execute("""
        CREATE TABLE IF NOT EXISTS tanimli_ideler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ide_adi TEXT NOT NULL,
            ide_turu TEXT DEFAULT 'Lokal',
            ide_url TEXT DEFAULT ''
        )
    """)
    # Önceden tanımlı hesaplar tablosu
    baglanti.execute("""
        CREATE TABLE IF NOT EXISTS tanimli_hesaplar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hesap_adi TEXT NOT NULL,
            hesap_email TEXT DEFAULT ''
        )
    """)
    baglanti.commit()
    baglanti.close()


# ============================================================
# VERİTABANI İŞLEMLERİ (CRUD)
# Tek tablo üzerinde ekleme, listeleme, güncelleme, silme
# ============================================================

def proje_listele():
    """Tüm proje kayıtlarını son güncellemeye göre sıralayarak döndürür."""
    bag = veritabani_baglantisi()
    satirlar = bag.execute("SELECT * FROM projeler ORDER BY son_guncelleme DESC").fetchall()
    sonuc = [dict(s) for s in satirlar]
    bag.close()
    return sonuc


def proje_ekle(veri):
    """Yeni bir proje kaydı ekler. Tüm bilgiler tek formdan gelir."""
    bag = veritabani_baglantisi()
    bag.execute("""
        INSERT INTO projeler (
            proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, 
            durum, notlar, etiketler, lokal_yol
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        veri["proje_adi"],
        veri.get("ide_adi", ""),
        veri.get("ide_turu", "Lokal"),
        veri.get("ide_url", ""),
        veri.get("hesap_adi", ""),
        veri.get("hesap_email", ""),
        veri.get("durum", "Aktif"),
        veri.get("notlar", ""),
        veri.get("etiketler", ""),
        veri.get("lokal_yol", "")
    ))
    bag.commit()
    bag.close()


def proje_guncelle(proje_id, veri):
    """Mevcut bir proje kaydını günceller. Son güncelleme tarihi otomatik ayarlanır."""
    bag = veritabani_baglantisi()
    bag.execute("""
        UPDATE projeler SET
            proje_adi=?, ide_adi=?, ide_turu=?, ide_url=?,
            hesap_adi=?, hesap_email=?, durum=?, notlar=?,
            etiketler=?, lokal_yol=?,
            son_guncelleme=datetime('now','localtime')
        WHERE id=?
    """, (
        veri["proje_adi"],
        veri.get("ide_adi", ""),
        veri.get("ide_turu", "Lokal"),
        veri.get("ide_url", ""),
        veri.get("hesap_adi", ""),
        veri.get("hesap_email", ""),
        veri.get("durum", "Aktif"),
        veri.get("notlar", ""),
        veri.get("etiketler", ""),
        veri.get("lokal_yol", ""),
        proje_id
    ))
    bag.commit()
    bag.close()


def proje_sil(proje_id):
    """Bir proje kaydını siler."""
    bag = veritabani_baglantisi()
    bag.execute("DELETE FROM projeler WHERE id=?", (proje_id,))
    bag.commit()
    bag.close()


def istatistikler():
    """Özet istatistikleri döndürür."""
    bag = veritabani_baglantisi()
    toplam = bag.execute("SELECT COUNT(*) FROM projeler").fetchone()[0]
    aktif = bag.execute("SELECT COUNT(*) FROM projeler WHERE durum='Aktif'").fetchone()[0]
    bulut = bag.execute("SELECT COUNT(*) FROM projeler WHERE ide_turu='Bulut'").fetchone()[0]
    # Benzersiz IDE ve hesap sayılarını hesapla
    benzersiz_ide = bag.execute("SELECT COUNT(DISTINCT ide_adi) FROM projeler WHERE ide_adi != ''").fetchone()[0]
    benzersiz_hesap = bag.execute("SELECT COUNT(DISTINCT hesap_adi) FROM projeler WHERE hesap_adi != ''").fetchone()[0]
    bag.close()
    return {
        "toplam": toplam, "aktif": aktif, "bulut": bulut,
        "lokal": toplam - bulut, "ide_sayisi": benzersiz_ide, "hesap_sayisi": benzersiz_hesap
    }


def otomatik_tamamla():
    """
    Hem önceden tanımlı hem de projelerden gelen IDE/hesap isimlerini birleştirir.
    Proje formundaki datalist'lerde öneri olarak gösterilir.
    """
    bag = veritabani_baglantisi()
    # Önceden tanımlı + projelerden gelen IDE'leri birleştir
    ideler_proje = {r[0] for r in bag.execute(
        "SELECT DISTINCT ide_adi FROM projeler WHERE ide_adi != ''").fetchall()}
    ideler_tanimli = {r[0] for r in bag.execute(
        "SELECT DISTINCT ide_adi FROM tanimli_ideler").fetchall()}
    # Önceden tanımlı + projelerden gelen hesapları birleştir
    hesaplar_proje = {r[0] for r in bag.execute(
        "SELECT DISTINCT hesap_adi FROM projeler WHERE hesap_adi != ''").fetchall()}
    hesaplar_tanimli = {r[0] for r in bag.execute(
        "SELECT DISTINCT hesap_adi FROM tanimli_hesaplar").fetchall()}
    emailler_proje = {r[0] for r in bag.execute(
        "SELECT DISTINCT hesap_email FROM projeler WHERE hesap_email != ''").fetchall()}
    emailler_tanimli = {r[0] for r in bag.execute(
        "SELECT DISTINCT hesap_email FROM tanimli_hesaplar WHERE hesap_email != ''").fetchall()}
    bag.close()
    return {
        "ideler": sorted(ideler_proje | ideler_tanimli),
        "hesaplar": sorted(hesaplar_proje | hesaplar_tanimli),
        "emailler": sorted(emailler_proje | emailler_tanimli)
    }


def veritabani_durumu():
    """Veritabanı sağlığını ve istatistiklerini kontrol eder."""
    try:
        bag = veritabani_baglantisi()
        prj_count = bag.execute("SELECT COUNT(*) FROM projeler").fetchone()[0]
        ide_count = bag.execute("SELECT COUNT(*) FROM tanimli_ideler").fetchone()[0]
        hsp_count = bag.execute("SELECT COUNT(*) FROM tanimli_hesaplar").fetchone()[0]
        bag.close()
        return {
            "status": "Healthy",
            "database_path": VERITABANI_YOLU,
            "counts": {"projeler": prj_count, "ideler": ide_count, "hesaplar": hsp_count}
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}


# ============================================================
# ÖNCEDEN TANIMLI IDE VE HESAP İŞLEMLERİ
# Kullanıcı proje eklemeden önce IDE ve hesaplarını tanımlayabilir.
# ============================================================

def tanimli_ide_listele():
    bag = veritabani_baglantisi()
    sonuc = [dict(r) for r in bag.execute("SELECT * FROM tanimli_ideler ORDER BY ide_adi").fetchall()]
    bag.close()
    return sonuc

def tanimli_ide_ekle(veri):
    bag = veritabani_baglantisi()
    bag.execute("INSERT INTO tanimli_ideler (ide_adi, ide_turu, ide_url) VALUES (?,?,?)",
                (veri["ide_adi"], veri.get("ide_turu","Lokal"), veri.get("ide_url","")))
    bag.commit(); bag.close()

def tanimli_ide_guncelle(tid, veri):
    bag = veritabani_baglantisi()
    bag.execute("UPDATE tanimli_ideler SET ide_adi=?, ide_turu=?, ide_url=? WHERE id=?",
                (veri["ide_adi"], veri.get("ide_turu","Lokal"), veri.get("ide_url",""), tid))
    bag.commit(); bag.close()

def tanimli_ide_sil(tid):
    bag = veritabani_baglantisi()
    bag.execute("DELETE FROM tanimli_ideler WHERE id=?", (tid,))
    bag.commit(); bag.close()

def tanimli_hesap_listele():
    bag = veritabani_baglantisi()
    sonuc = [dict(r) for r in bag.execute("SELECT * FROM tanimli_hesaplar ORDER BY hesap_adi").fetchall()]
    bag.close()
    return sonuc

def tanimli_hesap_ekle(veri):
    bag = veritabani_baglantisi()
    bag.execute("INSERT INTO tanimli_hesaplar (hesap_adi, hesap_email) VALUES (?,?)",
                (veri["hesap_adi"], veri.get("hesap_email","")))
    bag.commit(); bag.close()

def tanimli_hesap_guncelle(tid, veri):
    bag = veritabani_baglantisi()
    bag.execute("UPDATE tanimli_hesaplar SET hesap_adi=?, hesap_email=? WHERE id=?",
                (veri["hesap_adi"], veri.get("hesap_email",""), tid))
    bag.commit(); bag.close()

def tanimli_hesap_sil(tid):
    bag = veritabani_baglantisi()
    bag.execute("DELETE FROM tanimli_hesaplar WHERE id=?", (tid,))
    bag.commit(); bag.close()


# ============================================================
# HTTP SUNUCU — İstekleri karşılar, API ve arayüz sunar
# ============================================================

class IdeYoneticiHandler(BaseHTTPRequestHandler):
    """HTTP isteklerini karşılayan sunucu sınıfı."""

    def log_message(self, format, *args):
        """Sunucu loglarını sessizleştir (konsolu temiz tut)."""
        pass

    def _guvenlik_basliklari(self):
        """Web güvenliği için standart HTTP başlıklarını ekler."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("X-XSS-Protection", "1; mode=block")
        # Google Fonts ve data: URIs (select okları için) izin verilir
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; script-src 'self' 'unsafe-inline';")

    def _json_yanit(self, veri, durum=200):
        """JSON formatında yanıt gönderir."""
        self.send_response(durum)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self._guvenlik_basliklari()
        self.end_headers()
        self.wfile.write(json.dumps(veri, ensure_ascii=False).encode("utf-8"))

    def _html_yanit(self, icerik):
        """HTML formatında yanıt gönderir."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._guvenlik_basliklari()
        self.end_headers()
        self.wfile.write(icerik.encode("utf-8"))

    def _govde_oku(self):
        """İstek gövdesini JSON olarak okur ve döndürür."""
        uzunluk = int(self.headers.get("Content-Length", 0))
        govde = self.rfile.read(uzunluk).decode("utf-8")
        return json.loads(govde) if govde else {}

    def do_OPTIONS(self):
        """CORS preflight isteklerini karşılar."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """GET isteklerini yönlendirir."""
        yol = urlparse(self.path).path
        if yol == "/" or yol == "":
            self._html_yanit(ARAYUZ_HTML)
        elif yol == "/api/projeler":
            self._json_yanit(proje_listele())
        elif yol == "/api/istatistikler":
            self._json_yanit(istatistikler())
        elif yol == "/api/otomatik":
            self._json_yanit(otomatik_tamamla())
        elif yol == "/api/tanimli/ideler":
            self._json_yanit(tanimli_ide_listele())
        elif yol == "/api/tanimli/hesaplar":
            self._json_yanit(tanimli_hesap_listele())
        elif yol == "/api/diagnostic":
            self._json_yanit({
                "server": "Active",
                "database": veritabani_durumu(),
                "environment": {
                    "os": sys.platform,
                    "python": sys.version,
                    "cwd": os.getcwd()
                }
            })
        elif yol == "/api/export":
            bag = veritabani_baglantisi()
            ps = [dict(s) for s in bag.execute("SELECT * FROM projeler").fetchall()]
            ti = [dict(s) for s in bag.execute("SELECT * FROM tanimli_ideler").fetchall()]
            th = [dict(s) for s in bag.execute("SELECT * FROM tanimli_hesaplar").fetchall()]
            bag.close()
            self._json_yanit({"projeler": ps, "tanimli_ideler": ti, "tanimli_hesaplar": th})
        else:
            self._json_yanit({"hata": "Bulunamadı"}, 404)

    def do_POST(self):
        """POST — yeni proje ekleme."""
        yol = urlparse(self.path).path
        if yol == "/api/projeler":
            proje_ekle(self._govde_oku())
            self._json_yanit({"mesaj": "Proje eklendi"})
        elif yol == "/api/tanimli/ideler":
            tanimli_ide_ekle(self._govde_oku())
            self._json_yanit({"mesaj": "IDE eklendi"})
        elif yol == "/api/tanimli/hesaplar":
            tanimli_hesap_ekle(self._govde_oku())
            self._json_yanit({"mesaj": "Hesap eklendi"})
        elif yol == "/api/import":
            veri = self._govde_oku()
            bag = veritabani_baglantisi()
            # Projeler
            for p in veri.get("projeler", []):
                try:
                    bag.execute("INSERT OR REPLACE INTO projeler (id, proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, durum, notlar, son_guncelleme, olusturma_tarihi, etiketler, lokal_yol) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (p.get("id"), p.get("proje_adi",""), p.get("ide_adi",""), p.get("ide_turu","Lokal"), p.get("ide_url",""), p.get("hesap_adi",""), p.get("hesap_email",""), p.get("durum","Aktif"), p.get("notlar",""), p.get("son_guncelleme"), p.get("olusturma_tarihi"), p.get("etiketler",""), p.get("lokal_yol","")))
                except: pass
            # İdeler
            for ti in veri.get("tanimli_ideler", []):
                try: bag.execute("INSERT OR REPLACE INTO tanimli_ideler (id, ide_adi, ide_turu, ide_url) VALUES (?,?,?,?)", (ti.get("id"), ti.get("ide_adi",""), ti.get("ide_turu",""), ti.get("ide_url","")))
                except: pass
            # Hesaplar
            for th in veri.get("tanimli_hesaplar", []):
                try: bag.execute("INSERT OR REPLACE INTO tanimli_hesaplar (id, hesap_adi, hesap_email) VALUES (?,?,?)", (th.get("id"), th.get("hesap_adi",""), th.get("hesap_email","")))
                except: pass
            bag.commit()
            bag.close()
            self._json_yanit({"mesaj": "İçe aktarım tamamlandı"})
        elif yol == "/api/ac":
            veri = self._govde_oku()
            yol_str = veri.get("yol", "")
            if yol_str and os.path.exists(yol_str):
                try:
                    if sys.platform == 'win32':
                        os.startfile(yol_str)
                    elif sys.platform == 'darwin':
                        subprocess.call(['open', yol_str])
                    else:
                        subprocess.call(['xdg-open', yol_str])
                    self._json_yanit({"mesaj": "Dizin açıldı"})
                except Exception as e:
                    self._json_yanit({"hata": str(e)}, 500)
            else:
                self._json_yanit({"hata": "Geçersiz veya bulunamayan yol"}, 400)
        else:
            self._json_yanit({"hata": "Geçersiz"}, 404)

    def do_PUT(self):
        """PUT — proje güncelleme."""
        yol = urlparse(self.path).path
        if yol.startswith("/api/projeler/"):
            pid = int(yol.split("/")[-1])
            proje_guncelle(pid, self._govde_oku())
            self._json_yanit({"mesaj": "Güncellendi"})
        elif yol.startswith("/api/tanimli/ideler/"):
            tid = int(yol.split("/")[-1])
            tanimli_ide_guncelle(tid, self._govde_oku())
            self._json_yanit({"mesaj": "IDE güncellendi"})
        elif yol.startswith("/api/tanimli/hesaplar/"):
            tid = int(yol.split("/")[-1])
            tanimli_hesap_guncelle(tid, self._govde_oku())
            self._json_yanit({"mesaj": "Hesap güncellendi"})
        else:
            self._json_yanit({"hata": "Geçersiz"}, 404)

    def do_DELETE(self):
        """DELETE — proje silme."""
        yol = urlparse(self.path).path
        if yol.startswith("/api/projeler/"):
            pid = int(yol.split("/")[-1])
            proje_sil(pid)
            self._json_yanit({"mesaj": "Silindi"})
        elif yol.startswith("/api/tanimli/ideler/"):
            tid = int(yol.split("/")[-1])
            tanimli_ide_sil(tid)
            self._json_yanit({"mesaj": "IDE silindi"})
        elif yol.startswith("/api/tanimli/hesaplar/"):
            tid = int(yol.split("/")[-1])
            tanimli_hesap_sil(tid)
            self._json_yanit({"mesaj": "Hesap silindi"})
        else:
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
<title>IDE Proje Takip Sistemi</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ===== SIFIRLAMA VE TEMA DEĞİŞKENLERİ ===== */
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#090b14;--bg2:#0f1224;--bg3:rgba(255,255,255,0.03);
  --bg-hover:rgba(255,255,255,0.06);--bg-modal:#111428;
  --text:#e4e4ef;--text2:#7b849e;--text3:#4a546a;
  --accent:#0ea5e9;--accent2:#38bdf8;--glow:rgba(14,165,233,0.25);
  --green:#10b981;--yellow:#f59e0b;--red:#ef4444;--blue:#3b82f6;
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
.btn-ghost{background:var(--bg3);color:var(--text2);border-color:var(--border)}
.btn-ghost:hover{color:var(--text);background:var(--bg-hover);border-color:var(--text3)}
.btn-sm{padding:7px 14px;font-size:12px;border-radius:8px}
.btn-icon{width:34px;height:34px;padding:0;display:flex;align-items:center;justify-content:center;
  border-radius:8px;background:var(--bg3);border:1px solid var(--border);color:var(--text2);
  cursor:pointer;transition:var(--tr);font-size:15px}
.btn-icon:hover{color:var(--text);background:var(--bg-hover)}
.btn-icon.danger:hover{color:var(--red);background:rgba(239,107,94,0.1);border-color:rgba(239,107,94,0.2)}
.btn-icon.edit:hover{color:var(--blue);background:rgba(91,168,245,0.1);border-color:rgba(91,168,245,0.2)}

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
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;
  padding:0 40px 8px}
.stat{background:var(--bg3);border:1px solid var(--border);border-radius:var(--r);padding:18px 22px;
  transition:var(--tr);position:relative;overflow:hidden}
.stat:hover{transform:translateY(-2px);border-color:var(--border2);
  box-shadow:0 8px 24px rgba(124,106,239,0.08)}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;opacity:0;transition:var(--tr)}
.stat:hover::before{opacity:1}
.stat:nth-child(1)::before{background:var(--accent2)}
.stat:nth-child(2)::before{background:var(--green)}
.stat:nth-child(3)::before{background:var(--blue)}
.stat:nth-child(4)::before{background:var(--yellow)}
.stat-val{font-size:26px;font-weight:800;margin-bottom:2px}
.stat-lbl{font-size:11px;color:var(--text2);text-transform:uppercase;letter-spacing:.8px;font-weight:600}
.stat:nth-child(1) .stat-val{color:var(--accent2)}
.stat:nth-child(2) .stat-val{color:var(--green)}
.stat:nth-child(3) .stat-val{color:var(--blue)}
.stat:nth-child(4) .stat-val{color:var(--yellow)}

/* ===== PROJE KARTLARI ===== */
.grid{padding:12px 40px 40px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--bg3);border:1px solid var(--border);border-radius:var(--r);
  padding:22px 24px;transition:var(--tr);position:relative;overflow:hidden}
.card:hover{border-color:var(--border2);box-shadow:0 4px 20px rgba(124,106,239,0.06);
  transform:translateY(-2px)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
.card-title{font-size:16px;font-weight:700;letter-spacing:-.3px;line-height:1.3;flex:1;margin-right:10px}
.card-actions{display:flex;gap:6px;flex-shrink:0}
.card-body{display:flex;flex-direction:column;gap:10px}
.card-row{display:flex;align-items:center;gap:10px;font-size:13px}
.card-row .icon{width:20px;text-align:center;font-size:15px;flex-shrink:0}
.card-row .label{color:var(--text2);min-width:55px;font-weight:500;font-size:12px}
.card-row .value{color:var(--text);flex:1;word-break:break-word}
.card-row a{color:var(--blue);text-decoration:none;transition:var(--tr)}
.card-row a:hover{text-decoration:underline;opacity:.85}
.card-note{margin-top:6px;padding-top:12px;border-top:1px solid var(--border);
  font-size:12px;color:var(--text2);line-height:1.6;white-space:pre-wrap}
.card-footer{display:flex;justify-content:space-between;align-items:center;
  margin-top:12px;padding-top:10px;border-top:1px solid var(--border)}
.card-date{font-size:11px;color:var(--text3)}

/* ===== ETİKETLER ===== */
.tag{display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;
  font-size:11px;font-weight:600;letter-spacing:.3px}
.tag-aktif{background:rgba(45,212,160,0.12);color:var(--green)}
.tag-pasif{background:rgba(74,74,106,0.2);color:var(--text3)}
.tag-arsiv{background:rgba(240,194,70,0.12);color:var(--yellow)}
.tag-bulut{background:rgba(91,168,245,0.12);color:var(--blue)}
.tag-lokal{background:rgba(157,143,252,0.12);color:var(--accent2)}
.tag-custom{background:rgba(255,255,255,0.05);color:var(--text)}
[data-theme="light"] .tag-custom{background:rgba(0,0,0,0.05);}
.sleep-warning{color:var(--yellow);font-weight:600;font-size:11px;display:inline-flex;align-items:center;gap:4px}

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

/* ===== RESPONSIVE ===== */
@media(max-width:640px){
  .header,.controls,.stats,.grid{padding-left:16px;padding-right:16px}
  .grid{grid-template-columns:1fr}
  .form-row{grid-template-columns:1fr}
  .stats{grid-template-columns:repeat(2,1fr)}
  .ayar-add-row{flex-direction:column}
}
</style>
</head>
<body>

<!-- ===== HEADER ===== -->
<header class="header">
  <div class="brand">
    <div class="brand-icon">🛠</div>
    <div><h1>IDE Proje Takip</h1><p>Projelerini, IDE'lerini ve hesaplarını tek yerden yönet</p></div>
  </div>
  <div class="header-actions">
    <button class="btn btn-icon" onclick="temaDegistir()" title="Temayı Değiştir" id="btn-tema">🌓</button>
    <button class="btn btn-ghost" onclick="ayarlarAc()">⚙ Ayarlar</button>
    <button class="btn btn-primary" onclick="modalAc()">+ Yeni Proje</button>
  </div>
</header>

<!-- ===== İSTATİSTİKLER ===== -->
<div class="stats" style="margin-top:20px">
  <div class="stat"><div class="stat-val" id="s-toplam">0</div><div class="stat-lbl">Toplam Proje</div></div>
  <div class="stat"><div class="stat-val" id="s-aktif">0</div><div class="stat-lbl">Aktif</div></div>
  <div class="stat"><div class="stat-val" id="s-ide">0</div><div class="stat-lbl">Farklı IDE</div></div>
  <div class="stat"><div class="stat-val" id="s-hesap">0</div><div class="stat-lbl">Farklı Hesap</div></div>
</div>

<!-- ===== ARAMA VE FİLTRE ===== -->
<div class="controls">
  <div class="search-wrap">
    <input class="search-input" id="ara" placeholder="Proje, IDE veya hesap ara..." oninput="goster()">
  </div>
  <select class="filter-sel" id="f-durum" onchange="goster()">
    <option value="">Tüm Durumlar</option><option value="Aktif">Aktif</option>
    <option value="Pasif">Pasif</option><option value="Arşiv">Arşiv</option>
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
        <input id="f-ide-adi" list="dl-ide" placeholder="Örn: Cursor, Firebase Studio...">
        <datalist id="dl-ide"></datalist>
      </div>
      <div class="form-group">
        <label>IDE Türü</label>
        <select id="f-ide-tur">
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
      <input id="f-lokal-yol" placeholder="örn: C:\Projeler\App">
    </div>

    <div class="form-sep-label">👤 Hesap Bilgileri</div>
    <div class="form-row">
      <div class="form-group">
        <label>Hesap Adı</label>
        <input id="f-hesap" list="dl-hesap" placeholder="Örn: Ana Hesap, Yedek...">
        <datalist id="dl-hesap"></datalist>
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
        <option value="Aktif">✅ Aktif</option><option value="Pasif">⏸ Pasif</option>
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
  </div>
  <div class="modal-foot">
    <button class="btn btn-ghost" onclick="taslakFormuTemizle()" id="btn-reset" style="margin-right:auto;display:none">Formu Sıfırla</button>
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
    <button class="btn btn-sm" id="sil-btn"
      style="background:rgba(239,107,94,0.15);color:var(--red);border-color:rgba(239,107,94,0.3)">Evet, Sil</button>
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
        <p style="font-size:13px;color:var(--text2);margin-bottom:20px;line-height:1.6">Verilerinizi JSON formatında indirebilir veya daha önce indirdiğiniz bir yedeği sisteme yükleyebilirsiniz.</p>
        <button class="btn btn-primary" onclick="disaAktar()">⬇ Yedeği İndir (Export)</button>
        <br><br>
        <div style="position:relative;display:inline-block">
            <button class="btn btn-ghost">⬆ Yedek Yükle (Import)</button>
            <input type="file" id="f-import" accept=".json" onchange="iceAktar(event)" style="opacity:0;position:absolute;inset:0;cursor:pointer" title="JSON yedeği seç">
        </div>
      </div>
    </div>
  </div>
</div>
</div>

<!-- ===== TOAST ===== -->
<div class="toast" id="toast"></div>

<script>
/* ===============================================
   GLOBAL VERİ
   =============================================== */
let projeler = [];     // Tüm proje kayıtları
let oneriVeri = {};    // Otomatik tamamlama verisi (IDE, hesap, e-posta)
let tanimliIdeler = [];
let tanimliHesaplar = [];

/* ===============================================
   API YARDIMCILARI
   =============================================== */
// Sunucuya istek gönderir ve JSON yanıtı döndürür
async function api(yol, metod='GET', veri=null) {
  const a = {method:metod, headers:{'Content-Type':'application/json'}};
  if (veri) a.body = JSON.stringify(veri);
  return (await fetch(yol, a)).json();
}

// Kullanıcıya bildirim gösterir (yeşil = başarı, kırmızı = hata)
function bildirim(msg, tip='ok') {
  const t = document.getElementById('toast');
  t.textContent = (tip==='ok'?'✅ ':'❌ ') + msg;
  t.className = 'toast '+tip+' show';
  setTimeout(()=>t.classList.remove('show'), 2500);
}

// Metin içindeki HTML karakterlerini güvenli hale getirir
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/* ===============================================
   VERİ YÜKLEME — Projeleri ve istatistikleri çeker
   =============================================== */
async function yukle() {
  // Paralel olarak tüm verileri çek
  [projeler, oneriVeri, tanimliIdeler, tanimliHesaplar] = await Promise.all([
    api('/api/projeler'), 
    api('/api/otomatik'),
    api('/api/tanimli/ideler'), 
    api('/api/tanimli/hesaplar')
  ]);
  const ist = await api('/api/istatistikler');

  // İstatistik kartlarını güncelle
  document.getElementById('s-toplam').textContent = ist.toplam;
  document.getElementById('s-aktif').textContent = ist.aktif;
  document.getElementById('s-ide').textContent = ist.ide_sayisi;
  document.getElementById('s-hesap').textContent = ist.hesap_sayisi;

  // IDE filtre dropdown'unu güncelle (benzersiz IDE isimleri)
  const fi = document.getElementById('f-ide');
  const sec = fi.value;
  fi.innerHTML = '<option value="">Tüm IDE\'ler</option>' +
    oneriVeri.ideler.map(i=>`<option value="${esc(i)}">${esc(i)}</option>`).join('');
  fi.value = sec;

  // Datalist'leri güncelle (otomatik tamamlama önerileri)
  document.getElementById('dl-ide').innerHTML = oneriVeri.ideler.map(i=>`<option value="${esc(i)}">`).join('');
  document.getElementById('dl-hesap').innerHTML = oneriVeri.hesaplar.map(h=>`<option value="${esc(h)}">`).join('');
  document.getElementById('dl-email').innerHTML = oneriVeri.emailler.map(e=>`<option value="${esc(e)}">`).join('');

  hizliIdeGoster();
  goster();
}

/* ===============================================
   KARTLARI GÖSTER — Filtreleme ve arama uygular
   =============================================== */
function goster() {
  const arama = document.getElementById('ara').value.toLowerCase();
  const fDurum = document.getElementById('f-durum').value;
  const fTur = document.getElementById('f-tur').value;
  const fIde = document.getElementById('f-ide').value;

  // Filtreleme: arama metni, durum, tür ve IDE'ye göre
  const liste = projeler.filter(p => {
    const metin = (p.proje_adi+' '+p.ide_adi+' '+p.hesap_adi+' '+p.notlar+' '+p.hesap_email).toLowerCase();
    if (arama && !metin.includes(arama)) return false;
    if (fDurum && p.durum !== fDurum) return false;
    if (fTur && p.ide_turu !== fTur) return false;
    if (fIde && p.ide_adi !== fIde) return false;
    return true;
  });

  const kutu = document.getElementById('kartlar');

  // Boş durum mesajı
  if (liste.length === 0) {
    kutu.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">📂</div>
      <div class="empty-text">${projeler.length === 0
        ? 'Henüz hiç proje eklenmemiş.<br>İlk projenizi ekleyerek başlayın!'
        : 'Filtreye uygun proje bulunamadı.'}</div>
      ${projeler.length === 0 ? '<button class="btn btn-primary" onclick="modalAc()">+ İlk Projeyi Ekle</button>' : ''}
    </div>`;
    return;
  }

  // Proje kartlarını oluştur
  kutu.innerHTML = liste.map(p => {
    const durumClass = p.durum==='Aktif'?'tag-aktif':p.durum==='Pasif'?'tag-pasif':'tag-arsiv';
    const turClass = p.ide_turu==='Bulut'?'tag-bulut':'tag-lokal';
    const turIcon = p.ide_turu==='Bulut'?'☁':'🖥';

    let eHtml = '';
    if (p.etiketler) {
      eHtml = `<div style="margin-top:2px">` + p.etiketler.split(',').map(e=>e.trim()).filter(e=>e).map(e=>`<span class="tag tag-custom">#${esc(e)}</span>`).join(' ') + `</div>`;
    }

    let uykuUyari = '';
    if (p.son_guncelleme && p.durum === 'Aktif') {
      const g = Math.floor((new Date() - new Date(p.son_guncelleme)) / 86400000);
      if (g > 30) uykuUyari = `<div class="sleep-warning">⚠️ ${g} gündür işlem yapılmadı! Uyku riskine dikkat.</div>`;
    }

    let acBtn = '';
    if (p.ide_turu === 'Bulut' && p.ide_url) {
      acBtn = `<button class="btn btn-primary btn-sm" onclick="window.open('${esc(p.ide_url)}', '_blank')" title="Tarayıcıda Aç">🚀 Aç</button>`;
    } else if (p.ide_turu === 'Lokal' && p.lokal_yol) {
      acBtn = `<button class="btn btn-primary btn-sm" onclick="lokalAc('${esc(p.lokal_yol).replace(/\\/g,'\\\\')}')" title="Klasörü Aç">💻 Aç</button>`;
    }

    return `<div class="card">
      <div class="card-top">
        <div style="flex:1;margin-right:10px">
          <div class="card-title">${esc(p.proje_adi)}</div>
          ${eHtml}
        </div>
        <div class="card-actions">
          ${acBtn}
          <button class="btn-icon edit" onclick="duzenle(${p.id})" title="Düzenle">✏️</button>
          <button class="btn-icon danger" onclick="silOnay(${p.id},'${esc(p.proje_adi).replace(/'/g,"\\'")}')" title="Sil">🗑️</button>
        </div>
      </div>
      <div class="card-body">
        ${p.ide_adi ? `<div class="card-row">
          <span class="icon">💻</span>
          <span class="label">IDE</span>
          <span class="value">${esc(p.ide_adi)} <span class="tag ${turClass}" style="margin-left:6px">${turIcon} ${esc(p.ide_turu)}</span></span>
        </div>` : ''}
        ${p.ide_url ? `<div class="card-row">
          <span class="icon">🔗</span>
          <span class="label">URL</span>
          <span class="value"><a href="${esc(p.ide_url)}" target="_blank">${esc(p.ide_url)}</a></span>
        </div>` : ''}
        ${p.hesap_adi ? `<div class="card-row">
          <span class="icon">👤</span>
          <span class="label">Hesap</span>
          <span class="value">${esc(p.hesap_adi)}${p.hesap_email ? ' <span style="color:var(--text3);font-size:12px">('+esc(p.hesap_email)+')</span>' : ''}</span>
        </div>` : ''}
        ${p.lokal_yol && p.ide_turu === 'Lokal' ? `<div class="card-row">
          <span class="icon">📂</span>
          <span class="label">Dizin</span>
          <span class="value" style="font-family:monospace;font-size:11px">${esc(p.lokal_yol)}</span>
        </div>` : ''}
        ${p.notlar ? `<div class="card-note">📝 ${esc(p.notlar)}</div>` : ''}
        ${uykuUyari}
      </div>
      <div class="card-footer">
        <span class="tag ${durumClass}">${esc(p.durum)}</span>
        <span class="card-date">🕐 ${esc(p.son_guncelleme||'')}</span>
      </div>
    </div>`;
  }).join('');
}

/* ===============================================
   MODAL — Proje ekleme/düzenleme formu
   =============================================== */
function hizliIdeGoster() {
  const kutu = document.getElementById('ide-quick-select');
  if(!kutu) return;
  if (tanimliIdeler.length === 0) {
    kutu.style.display = 'none';
    return;
  }
  kutu.style.display = 'flex';
  const seciliIde = document.getElementById('f-ide-adi').value;
  kutu.innerHTML = tanimliIdeler.map(i => {
    const active = i.ide_adi === seciliIde ? 'active' : '';
    return `<button type="button" class="quick-ide-btn ${active}" onclick="ideHizliSec('${esc(i.ide_adi).replace(/'/g,"\\'")}', '${esc(i.ide_turu)}', '${esc(i.ide_url||'').replace(/'/g,"\\'")}')">
      ${i.ide_turu==='Bulut'?'☁':'🖥'} ${esc(i.ide_adi)}
    </button>`;
  }).join('');
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
  if (confirm('Taslağı silip formu temizlemek istediğinize emin misiniz?')) {
    localStorage.removeItem('proje_taslak');
    modalAc();
    bildirim('Form temizlendi');
  }
}

/* ===============================================
   TASLAK SİSTEMİ V6 — DEBOUNCED & GUARDED
   =============================================== */
let _taslakTimer = null;

function taslakKaydet(manuel = false) {
  // 1. Düzenleme modundaysak (id varsa) ASLA taslağa dokunma
  if (document.getElementById('f-id').value) return;

  clearTimeout(_taslakTimer);
  _taslakTimer = setTimeout(() => {
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
      lokal_yol: document.getElementById('f-lokal-yol').value.trim()
    };

    // KRİTİK KORUMA: Eğer modal kapalıysa veya form boşsa kaydetme!
    // Bu, "modal kapanırken boş verinin taslağı ezmesi" sorununu kökten çözer.
    if (!document.getElementById('modal').classList.contains('show') && !manuel) return;

    const hasContent = Object.values(t).some(v => v !== '' && v !== 'Lokal' && v !== 'Aktif');
    if (!hasContent) return; 

    localStorage.setItem('proje_taslak', JSON.stringify(t));
    console.log("💾 Taslak güvenle saklandı.");
  }, 300);
}

function taslakYukle() {
  try {
    const raw = localStorage.getItem('proje_taslak');
    if (!raw) return false;
    const t = JSON.parse(raw);
    
    // Veri kontrolü
    if (!t.proje_adi && !t.ide_adi && !t.notlar) return false;

    // Alanlara yerleştir
    document.getElementById('f-proje').value = t.proje_adi || '';
    document.getElementById('f-ide-adi').value = t.ide_adi || '';
    document.getElementById('f-ide-tur').value = t.ide_turu || 'Lokal';
    document.getElementById('f-url').value = t.ide_url || '';
    document.getElementById('f-hesap').value = t.hesap_adi || '';
    document.getElementById('f-email').value = t.hesap_email || '';
    document.getElementById('f-durum-sec').value = t.durum || 'Aktif';
    document.getElementById('f-notlar').value = t.notlar || '';
    document.getElementById('f-etiketler').value = t.etiketler || '';
    document.getElementById('f-lokal-yol').value = t.lokal_yol || '';
    
    return true;
  } catch(e) { return false; }
}

// Sadece modal içindeki gerçek kullanıcı hareketlerini dinle
window.addEventListener('input', e => {
  if (e.target.closest('.modal-body')) {
    taslakKaydet();
    if (e.target.id === 'f-ide-adi' || e.target.id === 'f-proje') hizliIdeGoster();
  }
});

// Dropdown seçimlerini dinle
window.addEventListener('change', e => {
  if (e.target.closest('.modal-body')) taslakKaydet();
});

function modalAc() {
  // Modal başlığını ayarla
  document.getElementById('modal-baslik').textContent = 'Yeni Proje';

  // SADECE ID'yi temizle (Yeni proje olduğunu anlamak için)
  document.getElementById('f-id').value = '';

  // Alanları varsayılanlara getir
  ['f-proje','f-ide-adi','f-url','f-hesap','f-email','f-notlar','f-etiketler','f-lokal-yol'].forEach(id=>{
    document.getElementById(id).value = '';
  });
  document.getElementById('f-ide-tur').value = 'Lokal';
  document.getElementById('f-durum-sec').value = 'Aktif';

  // Taslağı yükle (Eğer varsa yukarıdaki boşlukları doldurur)
  const restored = taslakYukle();
  
  // Modalı göster
  document.getElementById('modal').classList.add('show');
  
  // Badge durumunu güncelle
  document.getElementById('draft-badge').className = restored ? 'draft-badge show' : 'draft-badge';
  document.getElementById('btn-reset').style.display = restored ? 'inline-flex' : 'none';
  
  hizliIdeGoster();
  turGuncelle();
  setTimeout(()=>document.getElementById('f-proje').focus(), 150);
}

function turGuncelle() {
  const tur = document.getElementById('f-ide-tur').value;
  document.getElementById('alan-url').style.display = tur==='Bulut'?'block':'none';
  document.getElementById('alan-lokal').style.display = tur==='Lokal'?'block':'none';
}
document.getElementById('f-ide-tur').addEventListener('change', turGuncelle);

function duzenle(id) {
  const p = projeler.find(x=>x.id===id);
  if (!p) return;
  document.getElementById('modal-baslik').textContent = 'Proje Düzenle';
  document.getElementById('f-id').value = id;
  document.getElementById('f-proje').value = p.proje_adi;
  document.getElementById('f-ide-adi').value = p.ide_adi||'';
  document.getElementById('f-ide-tur').value = p.ide_turu||'Lokal';
  document.getElementById('f-url').value = p.ide_url||'';
  document.getElementById('f-hesap').value = p.hesap_adi||'';
  document.getElementById('f-email').value = p.hesap_email||'';
  document.getElementById('f-durum-sec').value = p.durum||'Aktif';
  document.getElementById('f-notlar').value = p.notlar||'';
  document.getElementById('f-etiketler').value = p.etiketler||'';
  document.getElementById('f-lokal-yol').value = p.lokal_yol||'';
  
  document.getElementById('draft-badge').className = 'draft-badge';
  document.getElementById('btn-reset').style.display = 'none';
  
  hizliIdeGoster();
  turGuncelle();
  document.getElementById('modal').classList.add('show');
}

function modalKapat() {
  // Kapatırken ASLA otomatik kaydetme TETİKLEME!
  // Sadece modalı gizle. Kayıt zaten kullanıcı yazarken anlık (input event) yapılıyor.
  document.getElementById('modal').classList.remove('show');
}

// Kaydet butonuna basılınca
async function kaydet() {
  const adi = document.getElementById('f-proje').value.trim();
  if (!adi) { bildirim('Proje adı gerekli!','err'); return; }
  
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
    lokal_yol: document.getElementById('f-lokal-yol').value.trim()
  };

  const id = document.getElementById('f-id').value;
  try {
    if (id) {
        await api('/api/projeler/'+id, 'PUT', veri);
        bildirim('Proje güncellendi');
    } else {
        await api('/api/projeler', 'POST', veri);
        bildirim('Proje eklendi');
        localStorage.removeItem('proje_taslak'); // Başarılı kayıttan sonra taslağı temizle
    }
    document.getElementById('modal').classList.remove('show'); // Doğrudan kapat
    yukle();
  } catch(e) {
    bildirim('Hata oluştu!','err');
  }
}

/* ===============================================
   SİLME — Onay penceresiyle proje silme
   =============================================== */
function silOnay(id, ad) {
  document.getElementById('sil-mesaj').innerHTML =
    `<strong>"${ad}"</strong> projesini silmek istediğinize emin misiniz?<br>
     <span style="color:var(--text3);font-size:12px">Bu işlem geri alınamaz.</span>`;
  document.getElementById('sil-btn').onclick = async()=>{
    await api('/api/projeler/'+id,'DELETE');
    bildirim('Proje silindi');
    silKapat();
    yukle();
  };
  document.getElementById('sil-modal').classList.add('show');
}
function silKapat() { document.getElementById('sil-modal').classList.remove('show'); }

/* ===============================================
   MODAL DIŞ TIKLAMA İLE KAPANMA (Gelişmiş Koruma)
   =============================================== */
let _overlayTiklamaBaslangic = null;

document.querySelectorAll('.overlay').forEach(o=>{
  // Mousedown anında hedefi kaydet
  o.addEventListener('mousedown', e => {
    _overlayTiklamaBaslangic = e.target;
  });
  
  // Sadece hem mousedown hem click overlay üzerinde ise kapat
  o.addEventListener('click', e => {
    if (e.target === o && _overlayTiklamaBaslangic === o) {
      if (o.id === 'modal') modalKapat();
      else if (o.id === 'sil-modal') silKapat();
      else if (o.id === 'ayar-modal') ayarlarKapat();
    }
    _overlayTiklamaBaslangic = null;
  });
});

// ESC tuşu ile modalı kapat
document.addEventListener('keydown', e=>{
  if(e.key==='Escape') {
    if(document.getElementById('modal').classList.contains('show')) modalKapat();
    if(document.getElementById('sil-modal').classList.contains('show')) silKapat();
    if(document.getElementById('ayar-modal').classList.contains('show')) ayarlarKapat();
  }
});

/* ===============================================
   AYARLAR PANELİ — Önceden tanımlı IDE ve hesap yönetimi
   =============================================== */

// Ayarlar modalını aç ve verileri yükle
async function ayarlarAc() {
  document.getElementById('ayar-modal').classList.add('show');
  await ayarVerileriYukle();
}
function ayarlarKapat() { document.getElementById('ayar-modal').classList.remove('show'); }

// Sekme geçişi
function ayarSekme(idx) {
  document.querySelectorAll('.ayar-tab').forEach((t,i) => t.classList.toggle('active', i===idx));
  document.querySelectorAll('.ayar-sec').forEach((s,i) => s.classList.toggle('active', i===idx));
}

// Tanımlı verileri sunucudan çek ve listele
async function ayarVerileriYukle() {
  [tanimliIdeler, tanimliHesaplar] = await Promise.all([
    api('/api/tanimli/ideler'), api('/api/tanimli/hesaplar')
  ]);
  ayarIdeGoster();
  ayarHesapGoster();
}

// IDE listesini göster
function ayarIdeGoster() {
  const kutu = document.getElementById('ayar-ide-list');
  if (tanimliIdeler.length === 0) {
    kutu.innerHTML = '<div class="ayar-empty">Henüz IDE tanımlanmamış</div>';
    return;
  }
  kutu.innerHTML = tanimliIdeler.map(i => `<div class="ayar-item">
    <span style="font-size:20px">${i.ide_turu==='Bulut'?'☁':'🖥'}</span>
    <div class="ai-info">
      <div class="ai-name">${esc(i.ide_adi)} <span class="tag ${i.ide_turu==='Bulut'?'tag-bulut':'tag-lokal'}" style="margin-left:4px">${esc(i.ide_turu)}</span></div>
      ${i.ide_url ? '<div class="ai-detail">'+esc(i.ide_url)+'</div>' : ''}
    </div>
    <button class="btn-icon danger" onclick="ideSilTanimli(${i.id})" title="Sil">🗑️</button>
  </div>`).join('');
}

// Hesap listesini göster
function ayarHesapGoster() {
  const kutu = document.getElementById('ayar-hesap-list');
  if (tanimliHesaplar.length === 0) {
    kutu.innerHTML = '<div class="ayar-empty">Henüz hesap tanımlanmamış</div>';
    return;
  }
  kutu.innerHTML = tanimliHesaplar.map(h => `<div class="ayar-item">
    <span style="font-size:20px">👤</span>
    <div class="ai-info">
      <div class="ai-name">${esc(h.hesap_adi)}</div>
      ${h.hesap_email ? '<div class="ai-detail">'+esc(h.hesap_email)+'</div>' : ''}
    </div>
    <button class="btn-icon danger" onclick="hesapSilTanimli(${h.id})" title="Sil">🗑️</button>
  </div>`).join('');
}

// Yeni IDE ekle
async function ideEkleTanimli() {
  const adi = document.getElementById('ai-ide-adi').value.trim();
  if (!adi) { bildirim('IDE adı gerekli!','err'); return; }
  await api('/api/tanimli/ideler', 'POST', {
    ide_adi: adi,
    ide_turu: document.getElementById('ai-ide-tur').value,
    ide_url: document.getElementById('ai-ide-url').value.trim()
  });
  document.getElementById('ai-ide-adi').value = '';
  document.getElementById('ai-ide-url').value = '';
  bildirim('IDE eklendi');
  await ayarVerileriYukle();
  yukle(); // Ana listeyi de güncelle (datalist)
}

// IDE sil
async function ideSilTanimli(id) {
  await api('/api/tanimli/ideler/'+id, 'DELETE');
  bildirim('IDE silindi');
  await ayarVerileriYukle();
  yukle();
}

// Yeni hesap ekle
async function hesapEkleTanimli() {
  const adi = document.getElementById('ai-hesap-adi').value.trim();
  if (!adi) { bildirim('Hesap adı gerekli!','err'); return; }
  await api('/api/tanimli/hesaplar', 'POST', {
    hesap_adi: adi,
    hesap_email: document.getElementById('ai-hesap-email').value.trim()
  });
  document.getElementById('ai-hesap-adi').value = '';
  document.getElementById('ai-hesap-email').value = '';
  bildirim('Hesap eklendi');
  await ayarVerileriYukle();
  yukle();
}

// Hesap sil
async function hesapSilTanimli(id) {
  await api('/api/tanimli/hesaplar/'+id, 'DELETE');
  bildirim('Hesap silindi');
  await ayarVerileriYukle();
  yukle();
}

/* ===============================================
   V3 EKSTRA ÖZELLİKLERİ (Tema, Yedekleme, Lokal Aç)
   =============================================== */
// Tema Değiştirme
function temaKontrol() {
  const mod = localStorage.getItem('ide_tema');
  if (mod === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    document.getElementById('btn-tema').textContent = '🌙';
  } else {
    document.documentElement.removeAttribute('data-theme');
    document.getElementById('btn-tema').textContent = '🌓';
  }
}
function temaDegistir() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  if (isLight) {
    localStorage.removeItem('ide_tema');
  } else {
    localStorage.setItem('ide_tema', 'light');
  }
  temaKontrol();
}
temaKontrol();

// Sistemi Sıfırla (LocalStorage temizle)
function sistemiSifirla() {
  if (confirm('DİKKAT: Tüm taslaklar, tema ayarları ve tarayıcı önbelleği temizlenecek. Kayıtlı projeleriniz SİLİNMEZ. Devam edilsin mi?')) {
    localStorage.clear();
    location.reload();
  }
}

// Lokal klasörü aç
async function lokalAc(yol) {
  if (!yol) return;
  const res = await api('/api/ac', 'POST', { yol: yol });
  if (res.hata) {
    bildirim('Lokal yol açılamadı veya bulunamadı!', 'err');
  } else {
    bildirim('Dizin açıldı');
  }
}

// Yedeği Dışa Aktar
async function disaAktar() {
  try {
    const data = await api('/api/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ide_yonetici_yedek_' + new Date().toISOString().slice(0,10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    bildirim('Yedek başarıyla indirildi');
  } catch(e) {
    bildirim('Yedek alınırken hata oluştu','err');
  }
}

// Yedeği İçe Aktar
async function iceAktar(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async function(e) {
    try {
      const gjson = JSON.parse(e.target.result);
      const res = await api('/api/import', 'POST', gjson);
      if (res.hata) throw new Error(res.hata);
      bildirim('Yedek başarıyla yüklendi!');
      ayarlarKapat();
      yukle();
    } catch (err) {
      bildirim('Hata: Geçersiz yedek dosyası.', 'err');
    }
    // file inputu sıfırla ki aynı dosyayı tekrar seçebilsin
    event.target.value = '';
  };
  reader.readAsText(file);
}

/* ===============================================
   SAYFA YÜKLEME — Tüm verileri çek ve göster
   =============================================== */
yukle();
</script>
</body>
</html>"""


# ============================================================
# ANA GİRİŞ NOKTASI — Sunucuyu başlat ve tarayıcıyı aç
# ============================================================

if __name__ == "__main__":
    # Veritabanı tablolarını oluştur (ilk çalıştırmada)
    tablolari_olustur()

    port = SUNUCU_PORT
    sunucu = None

    # Port meşgulse bir sonrakini dene (en fazla 10 deneme)
    for deneme in range(10):
        try:
            sunucu = HTTPServer(("127.0.0.1", port), IdeYoneticiHandler)
            break
        except OSError:
            print(f"  Port {port} mesgul, {port + 1} deneniyor...")
            port += 1

    if sunucu is None:
        print("  Uygun port bulunamadi!")
        input("Kapatmak icin Enter'a basin...")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    print("=" * 55)
    print("   IDE Proje Takip Sistemi baslatildi!")
    print(f"   Adres: {url}")
    print("   Kapatmak icin: Ctrl+C veya bu pencereyi kapatin")
    print("=" * 55)

    # Tarayıcıyı kısa bir gecikmeyle aç (sunucunun hazır olmasını bekle)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\n  Sunucu kapatiliyor...")
        sunucu.shutdown()
