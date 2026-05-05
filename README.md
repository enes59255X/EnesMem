# EnesMem — Python Bellek Tarayıcı / Düzenleyici

> Python + PyQt6 ile yazılmış, üretim düzeyinde bir Cheat Engine klonu.
> Saf `ctypes` — pymem bağımlılığı yok.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](CHANGELOG.md)

🇬🇧 [İngilizce için tıklayın](README_EN.md)

---

## İndir

[📥 EnesMem v1.0.0 İndir (Releases)](https://github.com/enes59255X/EnesMem/releases)

---

## Özellikler

- ✅ İşlem listeleme ve bağlanma
- ✅ Çoklu tür bellek okuma/yazma (Int8/16/32/64, Float, Double, String, Bytes)
- ✅ İlk Tarama ve Sonraki Tarama
- ✅ Tarama modları: Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown
- ✅ Değer dondurma (arka plan thread'i)
- ✅ Canlı yenilemeli izleme listesi
- ✅ Pointer zinciri çözümleme
- ✅ Koyu/açık tema desteği
- ✅ Global Kısayol Sistemi
- ✅ AOB Gelişmiş Tarama
- ✅ Değer Grafik Sistemi
- ✅ CT Dosya İçe/Dışa Aktarma
- ✅ Lua Betik Çerçevesi
- ✅ Bellek Haritası Görüntüleyici

---

## Gereksinimler

- Windows 10/11 (64-bit)
- Python 3.11+
- Yönetici yetkileri (`ReadProcessMemory` için gerekli)

---

## Kurulum ve Kullanım

1. **Releases** bölümünden `EnesMem.exe` dosyasını indir
2. Yönetici olarak çalıştır (sağ tık → Yönetici olarak çalıştır)
3. İşlem seç → Tarama yap → Değerleri değiştir

> **Önemli:** Her zaman Yönetici olarak çalıştırın. Aksi halde sadece mevcut kullanıcı hesabınıza ait işlemleri tarayabilirsiniz.

---

## Hakkında

**EnesMem v1.0.0** - Python ile geliştirilmiş, üretim düzeyinde bir bellek tarayıcısı ve düzenleyicisi.

### 🌟 Özellikler
- **Çok Dilli Destek**: Türkçe ve İngilizce arayüz
- **Modern Arayüz**: Koyu/açık tema desteği
- **Global Kısayollar**: Klavye kısayolları ile hızlı erişim
- **Gerçek Zamanlı**: Bellek değerlerini anlık olarak izleme

### 📊 Bilgiler
- **Versiyon**: v1.0.0
- **Lisans**: MIT
- **Platform**: Windows 10/11 (64-bit)

### � Destek
GitHub: https://github.com/enes59255X/EnesMem

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
