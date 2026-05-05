# EnesMem — Python Bellek Tarayıcı / Düzenleyici

> Python + PyQt6 ile yazılmış, üretim düzeyinde bir Cheat Engine klonu.
> Saf `ctypes` — pymem bağımlılığı yok.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.1-brightgreen.svg)](CHANGELOG.md)

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
- Python 3.11+
- Yönetici yetkileri (`ReadProcessMemory` için gerekli)

---

## Hızlı Başlangıç

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Yönetici olarak çalıştır
python main.py
```

> **Önemli:** Her zaman Yönetici olarak çalıştırın. Aksi halde sadece mevcut
> kullanıcı hesabınıza ait işlemleri tarayabilirsiniz.

---

## Testleri Çalıştırma

```bash
# Yönetici yetkisi gerekir — önce yükseltilmiş terminal açın
python -m pytest tests/ -v
```

---

## Proje Yapısı

```
EnesMem/
├── main.py                    # Giriş noktası (UAC yükseltme)
├── requirements.txt           # Bağımlılıklar
├── TUTORIAL.md                # Detaylı kullanım kılavuzu (TR/EN)
├── walkthrough.md             # Özellik anlatımı
├── README_EN.md               # İngilizce README
│
├── core/                      # Temel motor modülleri
│   ├── process_manager.py     # İşlem listeleme, handle yaşam döngüsü
│   ├── memory_io.py           # Okuma/yazma + bölge listeleme
│   ├── scanner.py             # İlk/Sonraki tarama motoru
│   ├── freezer.py             # Arka plan dondurma thread'i
│   ├── pointer_scanner.py     # Pointer zinciri çözümleme
│   ├── aob_scanner.py         # AOB/Desen tarama
│   ├── hotkey_manager.py      # Global kısayol sistemi
│   ├── value_graph.py         # Değer geçmişi takibi
│   ├── ct_manager.py          # Cheat Engine CT dosya desteği
│   ├── lua_engine.py          # Lua betik çerçevesi
│   ├── compare_scanner.py     # Karşılaştırma/Fark tarama
│   ├── memory_map.py          # Bellek bölge haritalama
│   ├── code_injector.py       # Kod enjeksiyon çerçevesi
│   └── advanced_filters.py    # Gelişmiş tarama filtreleri
│
├── gui/                       # Arayüz bileşenleri
│   ├── main_window.py         # Ana QMainWindow
│   ├── process_selector.py    # İşlem seçim diyaloğu
│   ├── scan_panel.py          # Tarama kontrolleri (sol panel)
│   ├── results_table.py       # Bulunan adresler + izleme listesi
│   ├── pointer_panel.py       # Pointer tarayıcı dock
│   ├── memory_viewer.py       # Hex bellek görüntüleyici
│   ├── memory_map_dialog.py   # Bellek haritası görüntüleyici
│   ├── graph_dialog.py        # Değer grafik görüntüleyici
│   ├── aob_dialog.py          # AOB tarayıcı diyaloğu
│   ├── hotkey_dialog.py       # Kısayol yapılandırma
│   ├── settings_dialog.py     # Ayarlar paneli
│   └── watchlist_groups.py    # Grup yönetimi
│
├── utils/                     # Yardımcı araçlar
│   ├── winapi.py              # Saf ctypes WinAPI tanımlamaları
│   ├── converters.py          # bytes ↔ yazılı değerler
│   ├── logger.py              # Yapılandırılmış loglama
│   ├── patterns.py            # Enum'lar, sabitler
│   ├── i18n.py                # Uluslararasılaştırma (TR/EN)
│   ├── settings.py            # Ayarlar yöneticisi
│   └── watchlist_groups.py    # Grup veri yönetimi
│
├── resources/                 # Varlıklar
│   └── lang/                  # Dil dosyaları
│       ├── tr.json            # Türkçe çeviriler
│       └── en.json            # İngilizce çeviriler
│
├── data/                      # Kullanıcı verisi (gitignored)
│   └── watchlist_groups.json  # Kaydedilen gruplar
│
└── tests/                     # Test paketi
    ├── test_memory_io.py
    ├── test_scanner.py
    ├── test_converters.py
    ├── test_watchlist_groups.py
    └── test_performance.py
```

---

## Mimari Notları

- **Saf ctypes**: Tüm Windows API çağrıları `utils/winapi.py` üzerinden. pymem yok.
- **Toplu okumalar**: Tarayıcı belleği 4MB parçalar halinde okur, `memoryview` ile sıfır-kopya dilimleme yapar.
- **QThread**: Tarama ana thread'den ayrı çalışır. İlerleme Qt sinyalleri ile raporlanır.
- **Tek dondurma thread'i**: Tek daemon thread 50ms aralıklarla tüm dondurulmuş adresleri yazar.

---

## Hakkında

**EnesMem v1.0.1** - Python ile geliştirilmiş, üretim düzeyinde bir bellek tarayıcısı ve düzenleyicisi.

### 🎯 Misyon
Cheat Engine'in özelliklerini Python ekosisteminde sunmak ve modern bir alternatif sağlamak.

### 🌟 Öne Çıkan Özellikler
- **Çok Dilli Destek**: Türkçe ve İngilizce arayüz
- **Gelişmiş Çeviri Sistemi**: Anlık dil değiştirme ve otomatik yükleme
- **Modern Arayüz**: PyQt5 ile geliştirilmiş, koyu/açık tema desteği
- **Global Kısayollar**: Klavye kısayolları ile hızlı erişim
- **Gerçek Zamanlı**: Bellek değerlerini anlık olarak izleme

### 📊 Versiyon Bilgileri
- **Versiyon**: v1.0.1
- **Yayın Tarihi**: 2026
- **Geliştirici**: Enes
- **Lisans**: MIT
- **Platform**: Windows 10/11 (64-bit)

### 🚀 Teknoloji
- **Python 3.11+**: Modern Python sürümü
- **PyQt5**: Güçlü ve stabil GUI kütüphanesi
- **ctypes**: Saf Windows API entegrasyonu
- **Threading**: Çoklu işlem desteği

### 📞 İletişim
- **GitHub**: https://github.com/enes59255X/EnesMem
- **Issues**: https://github.com/enes59255X/EnesMem/issues
- **Discussions**: https://github.com/enes59255X/EnesMem/discussions

### 🙏 Teşekkür
Bu proje, açık kaynak topluluğuna katkıda bulunan tüm geliştiricilere teşekkür eder.
- **64/32-bit uyumlu**: Hedef mimariyi `IsWow64Process` ile algılar. Pointer okumaları otomatik ayarlanır.

---

## Ekran Görüntüleri

> _Ana arayüz ve temel özelliklerin ekran görüntüleri buraya eklenecek._

<!-- 
![Ana Pencere](screenshots/main_window.png)
![Bellek Görüntüleyici](screenshots/memory_viewer.png)
![Pointer Tarayıcı](screenshots/pointer_scanner.png)
![Değer Grafiği](screenshots/value_graph.png)
-->

---

## Klavye Kısayolları

| Kısayol | Aksiyon |
|---------|---------|
| `Ctrl + O` | İşleme Bağlan |
| `Ctrl + Q` | Çıkış |
| `Ctrl + P` | Pointer Tarayıcı |
| `Ctrl + B` | AOB Tarayıcı |
| `Ctrl + G` | Değer Grafikleri |
| `Ctrl + M` | Bellek Haritası |
| `Ctrl + H` | Global Kısayollar |
| `Enter` | İlk/Sonraki Tarama |
| `Delete` | Seçili Adresi Sil |

---

## Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen bir Pull Request göndermekten çekinmeyin.

1. Repoyu forklayın
2. Feature branch oluşturun (`git checkout -b feature/HarikaOzellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'HarikaOzellik eklendi'`)
4. Branch'e push edin (`git push origin feature/HarikaOzellik`)
5. Pull Request açın

### Geliştirme Kurulumu

```bash
# Repoyu klonla
git clone https://github.com/enes59255/EnesMem.git
cd EnesMem

# Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate  # Windows

# Geliştirme bağımlılıklarını yükle
pip install -r requirements.txt
pip install pytest pytest-cov

# Testleri çalıştır (Yönetici gerekir)
python -m pytest tests/ -v
