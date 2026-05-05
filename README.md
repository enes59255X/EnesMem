# EnesMem — Python Bellek Tarayıcı / Düzenleyici

> Python + PyQt6 ile yazılmış, üretim düzeyinde bir Cheat Engine klonu.
> Saf `ctypes` — pymem bağımlılığı yok.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](CHANGELOG.md)

🇬🇧 [İngilizce için tıklayın](README_EN.md)

---

## Özellikler

| Özellik | Durum | Aşama |
|---------|-------|-------|
| İşlem listeleme ve bağlanma | ✅ | Temel |
| Çoklu tür bellek okuma/yazma (Int8/16/32/64, Float, Double, String, Bytes) | ✅ | Temel |
| İlk Tarama (tüm bellek bölgeleri) | ✅ | Temel |
| Sonraki Tarama (sonuçları daraltma) | ✅ | Temel |
| Tarama modları: Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown | ✅ | Temel |
| Değer dondurma (arka plan thread'i) | ✅ | Temel |
| Canlı yenilemeli izleme listesi | ✅ | Temel |
| Pointer zinciri çözümleme | ✅ | Temel |
| Koyu tema PyQt6 arayüzü | ✅ | Temel |
| UAC yetki yükseltme | ✅ | Temel |
| **Aşama 1 - Gelişmiş Özellikler** | | |
| Global Kısayol Sistemi | ✅ | Aşama 1 |
| İzleme Listesi Grupları ve Klasörleri | ✅ | Aşama 1 |
| AOB Gelişmiş Tarama | ✅ | Aşama 1 |
| **Aşama 2 - Profesyonel Araçlar** | | |
| Değer Grafik Sistemi | ✅ | Aşama 2 |
| CT Dosya İçe/Dışa Aktarma | ✅ | Aşama 2 |
| Lua Betik Çerçevesi | ✅ | Aşama 2 |
| Karşılaştırma/Fark Tarama | ✅ | Aşama 2 |
| **Aşama 3 - Uzman Özellikleri** | | |
| Bellek Haritası Görüntüleyici | ✅ | Aşama 3 |
| Gelişmiş Tarama Filtreleri | ✅ | Aşama 3 |
| Kod Enjeksiyon Çerçevesi | ✅ | Aşama 3 |

---

## Gereksinimler

- Windows 10/11 (64-bit)
- Yönetici yetkileri (EXE'yi çalıştırmak için gerekli)

---

## 🚀 Hızlı Başlangıç

1. GitHub Releases'dan `EnesMem-v1.0.0.zip` indirin
2. ZIP'i istediğiniz klasöre çıkarın  
3. `EnesMem.exe` dosyasına çift tıklayın (Yönetici olarak çalıştırın)
4. Tamamlandı! Kurulum gerekmez.

> **Önemli:** Her zaman **Yönetici** olarak çalıştırın.

---


---

## 📁 Proje Yapısı

```
EnesMem/
├── EnesMem.exe              # Çalıştırılabilir uygulama
├── README.md                # Türkçe dokümantasyon
├── TUTORIAL.md              # Kullanım kılavuzu (TR/EN)
└── LICENSE                 # MIT lisansı
```
