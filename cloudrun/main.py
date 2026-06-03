import os
import sys

_DOCKER_TMP = "/tmp/ide_yonetici"
os.makedirs(_DOCKER_TMP, exist_ok=True)
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("USERPROFILE", "/tmp")
os.environ.setdefault("TMPDIR", "/tmp")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ide_yonetici as _iy

_iy.UYGULAMA_KLASORU = _DOCKER_TMP
_iy.VERITABANI_YOLU = os.path.join(_DOCKER_TMP, "ide_yonetici.db")

from ide_yonetici import (
    IdeYoneticiHandler,
    tablolari_olustur,
    veritabani_kurtarmayi_dene,
    otomatik_yedek_al,
    sunucuyu_kapat,
    HTTPServer,
)


def _print_banner(url: str) -> None:
    print("=" * 55, flush=True)
    print("   IDE Proje Takip Sistemi (Cloud Run)", flush=True)
    print(f"   Adres: {url}", flush=True)
    print("=" * 55, flush=True)


if __name__ == "__main__":
    try:
        veritabani_kurtarmayi_dene()
        tablolari_olustur()
        otomatik_yedek_al("acilis")
    except Exception as exc:
        print(f"  [UYARI] Veritabanı başlatma hatası: {exc}", flush=True)

    port = int(os.environ.get("PORT", 8080))
    bind_host = "0.0.0.0"

    sunucu = None
    for deneme in range(10):
        try:
            sunucu = HTTPServer((bind_host, port), IdeYoneticiHandler)
            break
        except OSError:
            print(f"  Port {port} meşgul, {port + 1} deneniyor...", flush=True)
            port += 1

    if sunucu is None:
        print("  Uygun port bulunamadı!", flush=True)
        sys.exit(1)

    _iy.GLOBAL_SUNUCU = sunucu
    _print_banner(f"http://{bind_host}:{port}")

    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        sunucuyu_kapat()
        sys.exit(0)
