# Project Agent Knowledge Base: IDE Proje Takip Sistemi (v2.0+)

This document is the primary source of truth for AI agents taking over this project. It consolidates architectural decisions, core logic, and technical requirements.

## 1. Project Context
**Purpose:** A lightweight tool for developers to track projects across multiple cloud (Replit, Cursor, etc.) and local environments, specifically managing free-tier limits.
**Key Problem Solved:** Preventing data loss during incidental modal closures and managing project-IDE-account mapping.

## 2. Technical Stack
- **Backend:** Python 3 (Pure standard library: `http.server`, `sqlite3`, `webbrowser`). No external dependencies required for runtime.
- **Frontend:** Vanilla JS (SPA architecture), CSS3 (Modern Glassmorphism/Electric Blue theme).
- **Persistence:** Local SQLite database (`ide_yonetici.db`) and `localStorage` for drafts.

## 3. Core Logic & Architectures

### 3.1. Draft Persistence (V6 - Robust Strategy)
- **Logic:** Uses a debounced (300ms) save mechanism triggered by `input` events within the "New Project" modal.
- **Guards:** 
    - Saves ONLY if the modal is open and the `project_id` is empty (new projects).
    - Prevents overwriting valid drafts with empty data during modal closure by decoupling saving from the `modalKapat` function.
- **Loading:** `modalAc` reorders logic to prioritize `taslakYukle` after form reset but before display.

### 3.2. Modal Interaction Security
- **Overlay Protection:** Implements a `mousedown` trap to prevent accidental closure when a user finishes a text selection drag outside the modal. Both `mousedown` and `mouseup` (click) must target the overlay to close it.

## 4. API & Database

### 4.1. Key API Endpoints
- `GET /api/projeler`: List all projects.
- `POST /api/projeler`: Create project (clears draft on success).
- `GET /api/diagnostic`: Returns server, DB, and environment health.
- `POST /api/ac`: Opens local directory paths via `subprocess`.

### 4.2. Database Schema
- `projeler`: (id, proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, durum, notlar, etiketler, lokal_yol).
- `tanimli_ideler` & `tanimli_hesaplar`: Predefined values for autocomplete.

## 5. Maintenance & Build
- **Tests:** `PROJE_TEST_SUITE.py` (Unittest) covers backend/DB integrity.
- **Build:** `PyInstaller` command: `pyinstaller --onefile --name "IDE_Yonetici" --clean ide_yonetici.py`.
- **Troubleshooting:** The "Hafızayı Temizle" button in Settings/Backup clears `localStorage` and resets the UI state.

## 6. Project History (Critical Fixes)
- Fixed race condition in draft saving (V1-V5 failures).
- Resolved modal "phantom click" closure issue.
- Integrated Antigravity Kit protocols for security and modularity.
