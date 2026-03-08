# Project Audit: Proje Baştan Kontrolü

Projenin mevcut durumunun, yeni Antigravity Kit protokollerine ve genel yazılım standartlarına göre denetlenmesi.

## Success Criteria
- [ ] Kod kalitesi ve standartlara uyum raporu
- [ ] Güvenlik taraması sonuçları
- [ ] UI/UX denetimi (GEMINI.md kuralları dahil)
- [ ] Eksik testlerin ve iyileştirme alanlarının tespiti

## Project Type
**WEB** (Python Backend + Embedded JS/HTML Frontend)

## Tech Stack
- **Backend:** Python `http.server`, `sqlite3`
- **Frontend:** Vanilla JS, CSS3, HTML5 (Embedded)
- **Protocol:** Antigravity Kit v2.0

## Task Breakdown

### Phase 1: Context & Survey (Analysis)
- [ ] **Task 1.1**: Sokratik Sorular ile kapsam belirleme (@project-planner)
- [ ] **Task 1.2**: Proje dosyalarının (Python, JS, CSS) genel mizanpaj ve bağımlılık kontrolü (@explorer-agent)
- [ ] **Task 1.3**: `ide_yonetici.py` içindeki gömülü JS ve CSS yapısının modülerlik açısından analizi (@frontend-specialist)

### Phase 2: Automated Audit (Verification)
- [ ] **Task 2.1**: Güvenlik taraması (`security_scan.py`) yürütülmesi (@security-auditor)
- [ ] **Task 2.2**: UX Denetimi (`ux_audit.py`) yürütülmesi (@frontend-specialist)
- [ ] **Task 2.3**: Test kapsama analizi ve mevcut testlerin (`test_ide_yonetici.py`) çalıştırılması (@test-engineer)

### Phase 3: Reporting & Action
- [ ] **Task 3.1**: Tespit edilen kritik sorunların listelenmesi
- [ ] **Task 3.2**: İyileştirme önerilerinin sunulması

## Phase X: Final Verification
- [ ] Checklist.py pass
- [ ] Security scan pass
- [ ] Manual UX verification
