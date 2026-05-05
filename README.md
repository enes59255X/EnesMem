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
