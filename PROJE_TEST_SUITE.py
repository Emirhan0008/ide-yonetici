import unittest
import json
import os
import shutil
import tempfile
import sqlite3
import ide_yonetici

class TestIDERepo(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        ide_yonetici.VERITABANI_YOLU = self.db_path
        ide_yonetici.tablolari_olustur()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_database_creation(self):
        """Veritabanı ve tabloların doğru oluşturulduğunu test et."""
        self.assertTrue(os.path.exists(self.db_path))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        self.assertIn('projeler', tables)
        self.assertIn('tanimli_ideler', tables)
        self.assertIn('tanimli_hesaplar', tables)
        conn.close()

    def test_add_project_and_persistence(self):
        """Proje ekleme ve veri bütünlüğü testi."""
        project_data = {
            "proje_adi": "Alpha Projesi",
            "ide_adi": "VS Code",
            "ide_turu": "Lokal",
            "hesap_adi": "Work",
            "durum": "Aktif"
        }
        ide_yonetici.proje_ekle(project_data)
        
        projects = ide_yonetici.proje_listele()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['proje_adi'], "Alpha Projesi")

    def test_autotest_logic(self):
        """Otomatik tamamlama verilerinin birleştirme mantığını test et."""
        # IDE tanımla
        ide_yonetici.tanimli_ide_ekle({"ide_adi": "Cursor", "ide_turu": "Lokal"})
        # Proje ekle
        ide_yonetici.proje_ekle({"proje_adi": "P1", "ide_adi": "VS Code"})
        
        auto_data = ide_yonetici.otomatik_tamamla()
        self.assertIn("Cursor", auto_data['ideler'])
        self.assertIn("VS Code", auto_data['ideler'])

    def test_diagnostic_report(self):
        """Diagnostic API verisinin doğruluğunu test et."""
        report = ide_yonetici.veritabani_durumu()
        self.assertEqual(report['status'], "Healthy")
        self.assertIn('counts', report)

if __name__ == '__main__':
    unittest.main()
