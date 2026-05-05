# EnesMem v1.0.0 - Sürüm Notları

## 🚀 Hızlı Başlangıç

**Kullanıcılar:**
1. GitHub Releases'dan `EnesMem-v1.0.0.zip` indirin
2. ZIP'i herhangi bir klasöre çıkarın
3. `EnesMem.exe` dosyasına çift tıklayın (Yönetici olarak çalıştırın)
4. Tamamlandı! Kurulum gerekmez.

**Not:** Kaynak kodu geliştirme hakları şu an sadece yetkili kişilere açıktır.

## 📋 Özellikler

### Temel Özellikler
- ✅ Bellek tarama (İlk/Sonraki tarama)
- ✅ Çoklu veri türleri (Int8/16/32/64, Float, Double, String, Bytes)
- ✅ Tarama modları (Tam, Büyük, Küçük, Artan, Azalan, Değişen, Değişmeyen, Bilinmeyen)
- ✅ Değer dondurma (arka plan thread'i)
- ✅ Hex görüntüleyicili bellek görüntüleyici
- ✅ Pointer zinciri çözümleme (manuel ve otomatik)
- ✅ İzleme listesi yönetimi

### Aşama 1 - Gelişmiş Özellikler
- ✅ Global kısayol sistemi
- ✅ İzleme listesi grupları ve klasörleri
- ✅ AOB (Byte Dizisi) tarama
- ✅ Modern PyQt6 koyu arayüz

### Aşama 2 - Profesyonel Araçlar
- ✅ CSV dışa aktarımlı değer grafik sistemi
- ✅ Cheat Engine CT dosya içe/dışa aktarma
- ✅ Şablonlu Lua betik motoru
- ✅ Anlık görüntüler arası karşılaştırma/fark tarama

### Aşama 3 - Uzman Özellikleri
- ✅ Filtrelemeli bellek haritası görüntüleyici
- ✅ Gelişmiş tarama filtreleri (hizalama, aralık, modül, koruma)
- ✅ Kod enjeksiyon çerçevesi

### Uluslararasılaştırma
- ✅ Türkçe dil desteği
- ✅ İngilizce dil desteği
- ✅ Kolay dil değiştirme

## 🛡️ Teknik Detaylar

- **Çerçeve:** PyQt6 (modern, yerel widget'lar)
- **Bellek Erişimi:** Saf ctypes (pymem bağımlılığı yok)
- **Performans:** Memoryview optimizasyonlu 4MB toplu okumalar
- **Threading:** QThread ile engellemesiz arayüz
- **Mimari:** Otomatik algılamalı 64/32-bit uyumlu
- **Güvenlik:** Yönetici yetkileri için UAC yükseltme

## 🔧 Gereksinimler

- **İS:** Windows 10/11 (64-bit)
- **Python:** 3.11+ (geliştirme için)
- **Yetkiler:** Yönetici (bellek erişimi için gerekli)

## 📁 Dosya Yapısı

```
EnesMem/
├── main.py                 # UAC ile giriş noktası
├── requirements.txt          # Çalışma zamanı bağımlılıkları
├── README.md               # Türkçe dokümantasyon
├── README_EN.md            # İngilizce dokümantasyon
├── TUTORIAL.md             # Kullanım kılavuzu (TR/EN)
├── LICENSE                 # MIT lisansı
├── .gitignore              # Git kuralları
│
├── core/                  # Temel motor (13 modül)
├── gui/                   # Kullanıcı arayüzü (12 modül)
├── utils/                  # Yardımcılar (6 modül)
├── resources/lang/         # Diller (2 dosya)
└── data/                   # Kullanıcı verisi (gitignored)
```

## ⚠️ Önemli Notlar

### Kullanıcılar İçin
- **Her zaman Yönetici olarak çalıştırın** - Bellek erişimi için gerekli
- **Antivirüs uyarıları** - Yanlış pozitif uyarılar verebilir
- **Tek dosya** - Kurulum gerekmez, taşınabilir


## 🎯 Sırada Ne Var?

### v1.0.1 (Planlanan)
- [ ] Daha küçük EXE için UPX sıkıştırma
- [ ] Bellek tarama performans iyileştirmeleri
- [ ] Ek tarama filtreleri

### v1.1.0 (Gelecek)
- [ ] Eklenti sistemi
- [ ] Ağ tarama yetenekleri
- [ ] Gelişmiş kod enjeksiyon özellikleri

## 📞 Destek

- **Sorunlar:** https://github.com/enes59255X/EnesMem/issues
- **Dokümantasyon:** TUTORIAL.md dosyasına bakın
- **Topluluk:** Pull Request'lerle katkıda bulunabilirsiniz

---

**EnesMem v1.0.0** - Windows için profesyonel bellek tarayıcı
*EnesMem tarafından ❤️ ile geliştirildi*
