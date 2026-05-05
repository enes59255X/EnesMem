# 🎮 EnesMem — Gelişmiş Memory Manipülasyon Aracı

> **Cheat Engine'e Modern Alternatif:** Python + PyQt6 ile yazılmış, oyun memory manipülasyonu için profesyonel araç.
> **Saf ctypes** — dış bağımlılık yok, **%100 Python**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Latest Release](https://img.shields.io/github/release/enes59255X/EnesMem.svg)](https://github.com/enes59255X/EnesMem/releases)
[![Downloads](https://img.shields.io/github/downloads/enes59255X/EnesMem/total.svg)](https://github.com/enes59255X/EnesMem/releases)

🇬🇧 [English Version](README_EN.md)

---

## 🎯 Memory Manipülasyon Özellikleri

### 🔍 **Bellek Tarama Motoru**
- **İlk Tarama:** Tüm bellek bölgelerini hızlı tara
- **Sonraki Tarama:** Sonuçları akıllıca daralt
- **8 Tarama Modu:** Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown
- **7 Veri Türü:** Int8/16/32/64, Float, Double, String, Bytes
- **AOB Tarama:** Array of Bytes desen arama

### 🎮 **Oyun Memory Manipülasyonu**
- **Değer Dondurma:** Sağlık, para, mermi gibi değerleri sabitle
- **Pointer Zinciri:** Kalıcı offset'ler ve pointer'lar bul
- **İzleme Listesi:** Bulunan adresleri organize et
- **Global Kısayollar:** Hızlı değer değiştirme
- **Değer Grafikleri:** Memory değişimlerini görselleştir

### 🛠️ **Gelişmiş Araçlar**
- **CT Dosya Desteği:** Cheat Engine tablolarını içe/dışa aktar
- **Lua Betik Motoru:** Otomasyon ve komplex script'ler
- **Bellek Haritası:** Memory bölgelerini analiz et
- **Kod Enjeksiyon:** Assembly kod enjekte et
- **Karşılaştırma Taraması:** Memory snapshot'ları karşılaştır

### 🎨 **Modern Arayüz**
- **PyQt6:** Hızlı ve modern GUI
- **Koyu Tema:** Göz yormayan tasarım
- **Grup Sistemi:** İzleme listesini organize et
- **Canlı Yenileme:** Anlık değer güncellemeleri
- **UAC Entegrasyonu:** Yönetici yetkileri

---

## 🆚 EnesMem vs Cheat Engine

| Özellik | EnesMem | Cheat Engine | Avantajı |
|---------|---------|-------------|----------|
| **Programlama Dili** | Python + PyQt6 | Delphi | Modern, esnek, geniş kütüphane desteği |
| **Bağımlılıklar** | Saf ctypes | Windows API | Daha hafif, daha güvenli |
| **Arayüz** | Modern PyQt6 | Klasik Win32 | Daha hızlı, daha responsive |
| **Multi-thread** | ✅ | ❌ | Arayüz donma sorunu yok |
| **Lua Betik** | ✅ | ✅ | Eşdeğer özellik |
| **CT Dosya** | ✅ | ✅ | Cheat Engine uyumlu |
| **AOB Tarama** | ✅ | ✅ | Daha optimize edilmiş |
| **Pointer Scan** | ✅ | ✅ | Daha hızlı sonuç |
| **Kurulum** | Portatif (EXE) | Kurulum gerekir | Kurulum gerektirmez |
| **Güncelleme** | GitHub Release | Manuel | Otomatik güncelleme |
| **Türkçe Destek** | ✅ | ❌ | Yerli dil desteği |
| **Açık Kaynak** | ✅ | ❌ | Şeffaf ve güvenli |

### 🎯 Neden EnesMem?

**🚀 Performans:**
- Modern multi-thread mimarisi
- Optimize edilmiş bellek okuma/yazma
- Hızlı tarama algoritmaları

**🔒 Güvenlik:**
- Açık kaynak kodu
- Saf Python implementasyonu
- Gizli kod veya backdoor yok

**🎨 Kullanım Kolaylığı:**
- Modern ve intuitive arayüz
- Türkçe dil desteği
- Kurulum gerektirmeyen portatif sürüm

**🔧 Gelişmiş Özellikler:**
- Lua betik motoru
- CT dosya uyumluluğu
- Gelişmiş pointer tarama
- Real-time değer grafikleri

---

## 💻 Sistem Gereksinimleri

- **Windows 10/11** (64-bit)
- **Yönetici yetkileri** (Memory erişimi için)
- **RAM:** Minimum 4GB, önerilen 8GB+
- **Depolama:** 50MB boş alan

---

## Hızlı Kurulum

### Adım 1: İndirme
1. [GitHub Releases](https://github.com/enes59255X/EnesMem/releases) sayfasına gidin
2. En son sürümü indirin

### Adım 2: Kurulum
1. ZIP dosyasını herhangi bir klasöre çıkarın
2. `EnesMem.exe` dosyasına sağ tıklayın
3. **"Yönetici olarak çalıştır"** seçeneğini seçin

### 🎮 Adım 3: Kullanım
1. Hedef oyunu başlatın
2. EnesMem'i açın ve oyun sürecini seçin
3. Memory tarama başlatın!

> ⚠️ **Önemli:** Memory manipülasyonu için her zaman **Yönetici** olarak çalıştırın!

---

## Kullanım Senaryoları

### Oyun Hileleri
- Sağlık/Kalkan: Sonsuz sağlık modu
- Para/Madde: Sınırsız kaynaklar
- Mermi/Cephane: Bitmeyen mermiler
- XP/Seviye: Hızlı seviye atlama
- Speed Hack: Oyun hızı ayarı

### Memory Analizi
- Reverse Engineering: Program memory'sini analiz et
- Offset Bulma: Kalıcı adresler keşfet
- Pointer Zinciri: Karmaşık adres yapıları çöz
- Pattern Matching: Assembly desenleri ara

### Geliştirme Araçları
- Debugging: Program davranışlarını izle
- Testing: Memory manipülasyon testleri
- Research: Memory yapıları hakkında öğrenme

---

## Dokümantasyon

- [Kullanım Kılavuzu](TUTORIAL.md) - Detaylı kullanım talimatları
- [Sürüm Notları](RELEASE_NOTES.md) - Güncellemeler ve yenilikler
- [Lisans](LICENSE) - MIT Lisansı

---

## Katkıda Bulunma

EnesMem açık kaynak bir projedir! Katkıda bulunmak için:

1. Repository'yi fork edin
2. Yeni bir branch oluşturun (git checkout -b feature/amazing-feature)
3. Değişikliklerinizi commit edin (git commit -m 'Add amazing feature')
4. Branch'inize push edin (git push origin feature/amazing-feature)
5. Pull Request oluşturun

---

## Yasal Uyarı

Bu araç eğitim ve araştırma amaçlıdır. Oyunlarda kullanımı oyunun hizmet şartlarını ihlal edebilir. Kullanıcı sorumluluğundadır.

---

## Proje Yapısı

```
EnesMem/
├── EnesMem.exe              # Çalıştırılabilir uygulama
├── README.md                # Türkçe dokümantasyon
├── TUTORIAL.md              # Detaylı kullanım kılavuzu
├── RELEASE_NOTES.md         # Sürüm notları
└── LICENSE                 # MIT lisansı
```

---

## Yıldız Bırakın!

Proje beğendiyseniz, GitHub'da yıldız bırakmayı unutmayın!

[![GitHub stars](https://img.shields.io/github/stars/enes59255X/EnesMem.svg?style=social&label=Star)](https://github.com/enes59255X/EnesMem)
[![GitHub forks](https://img.shields.io/github/forks/enes59255X/EnesMem.svg?style=social&label=Fork)](https://github.com/enes59255X/EnesMem)

---

 EnesMem - Memory Manipülasyonu Yeniden Tanımlandı!
