# 📚 EnesMem Kullanım Kılavuzu / User Guide

> 🇹🇷 Türkçe ve 🇬🇧 İngilizce kullanım rehberi

---

## 🚀 Hızlı Başlangıç / Quick Start

### Kurulum / Installation

```bash
# 1. Repoyu klonlayın / Clone the repo
git clone https://github.com/enes59255/EnesMem.git
cd EnesMem

# 2. Bağımlılıkları yükleyin / Install dependencies
pip install -r requirements.txt

# 3. Yönetici olarak çalıştırın / Run as Administrator
python main.py
```

### Temel Kullanım / Basic Usage

1. **İşlem Bağlama / Attach Process**
   - "İşleme Bağlan" butonuna tıklayın
   - Hedef işlemi seçin (örn: `REPO.exe`, `notepad.exe`)
   - PID gözükecektir

2. **İlk Tarama / First Scan**
   - Değer türü seçin (INT32, FLOAT, vb.)
   - Tarama modu seçin (Exact, Bigger, vb.)
   - Değer girin ve "İlk Tarama" basın

3. **Sonraki Tarama / Next Scan**
   - Oyunda değeri değiştirin
   - Yeni değeri girin ve "Sonraki Tarama" basın
   - Sonuçlar daralacaktır

4. **İzleme Listesi / Watchlist**
   - Sonuca çift tıklayın
   - Değeri düzenleyin (çift tıklayın)
   - Dondurma: Sağ tık → Dondur

---

## 🎯 Özellikler / Features

### 1. Bellek Görüntüleyici / Memory Viewer (Ctrl+M)
- **Hex Editör**: Ham bellek baytlarını görüntüleyin
- **Canlı Yenileme**: Değişen baytlar kırmızı renkte
- **ASCII Görünüm**: Yan yana hex ve ASCII
- **Navigasyon**: Ok tuşları, Page Up/Down

### 2. Pointer Tarayıcı / Pointer Scanner (Ctrl+P)
- **Manuel Çözümleme**: Base + offset zincirleri
- **Otomatik Tarama**: Çok seviyeli pointer zincirleri bulur
- **Modül Bazlı**: DLL base adreslerini kullanır

### 3. AOB Tarayıcı / AOB Scanner (Ctrl+B)
- **Byte Desenleri**: `55 8B EC ?? ?? 8B` formatı
- **Joker Karakter**: `??` bilinmeyen baytlar için
- **Hazır Desenler**: Unity, Unreal Engine desenleri

### 4. Değer Grafikleri / Value Graphs (Ctrl+G)
- **Zaman Çizelgesi**: Değer değişimini görselleştirin
- **İstatistikler**: Min, Max, Ortalama
- **CSV Dışa Aktar**: Verileri kaydedin

### 5. Bellek Haritası / Memory Map (Ctrl+M)
- **Bölge Görünümü**: Tüm bellek bölgeleri
- **Koruma Bayrakları**: Okunabilir/Yazılabilir/Çalıştırılabilir
- **Filtreleme**: Boyut ve koruma bazlı filtrele

### 6. Global Kısayollar / Global Hotkeys (Ctrl+H)
- **Özel Tuşlar**: Freeze/Unfreeze için global hotkey'ler
- **Aksiyonlar**: Toggle freeze all, detach, vb.

### 7. Watchlist Grupları / Watchlist Groups
- **Klasör Sistemi**: Adresleri gruplandırın
- **Renkler**: Her grup için özel renk
- **Daralt/Genişlet**: Hiyerarşik görünüm

### 8. CT Dosya Desteği / CT File Support
- **Cheat Engine**: `.ct` dosyalarını içe/dışa aktar
- **Uyumluluk**: Cheat Engine ile paylaşım

### 9. Lua Betikleri / Lua Scripting
- **Basit Lua**: Bellek okuma/yazma betikleri
- **Şablonlar**: Hazır betik şablonları
- **Otomasyon**: Tekrarlayan işlemler için

### 10. Karşılaştır Tarama / Compare Scan
- **Anlık Görüntü**: Bellek durumunu kaydet
- **Değişim Tespiti**: Artan/Azalan/Değişen değerler

---

## ⌨️ Klavye Kısayolları / Keyboard Shortcuts

| Kısayol / Shortcut | Aksiyon / Action |
|-------------------|------------------|
| `Ctrl + O` | İşlem Seç / Select Process |
| `Ctrl + Q` | Çıkış / Exit |
| `Ctrl + P` | Pointer Tarayıcı / Pointer Scanner |
| `Ctrl + B` | AOB Tarayıcı / AOB Scanner |
| `Ctrl + G` | Değer Grafikleri / Value Graphs |
| `Ctrl + M` | Bellek Haritası / Memory Map |
| `Ctrl + H` | Global Kısayollar / Global Hotkeys |
| `Enter` | İlk/Sonraki Tarama / First/Next Scan |
| `Delete` | Seçili adresi sil / Delete selected |

---

## 🛠️ Gelişmiş Kullanım / Advanced Usage

### String Arama / String Search
```
1. Değer türü: String (UTF-8) veya String (UTF-16LE)
2. Metni girin: "Health"
3. Tarama yapın
4. Sonuçları inceleyin
```

### Float Toleransı / Float Tolerance
```
1. Değer türü: Float
2. Tarama modu: Float Tolerance (±)
3. Değer: 100.0
4. Tolerans: 0.1  (99.9 - 100.1 arası)
```

### Bilinmeyen Değer / Unknown Value
```
1. Tarama modu: Unknown Initial Value
2. İlk Tarama (tüm değerleri kaydeder)
3. Oyunda değeri değiştirin
4. Tarama modu: Decreased Value
5. Sonraki Tarama
```

### Pointer Zinciri / Pointer Chain
```
Pointer Formatı:
Module.exe + BaseOffset
-> Offset1
-> Offset2
-> ...
-> FinalAddress

Örnek:
game.exe+0x123456
-> 0x80
-> 0x20
-> Health Address
```

---

## ⚠️ Sık Karşılaşılan Sorunlar / Troubleshooting

| Sorun / Problem | Çözüm / Solution |
|----------------|------------------|
| "Erişim engellendi" | Yönetici olarak çalıştırın |
| Sonuç bulunamadı | Değer türünü kontrol edin (INT vs FLOAT) |
| Tarama çok yavaş | Daha spesifik değerler kullanın |
| Oyun çöküyor | "Güvenli Tarama Modu"nı açın |
| Pointer çözümlenemedi | Modül adını kontrol edin |

---

## 📖 Örnek Senaryolar / Example Scenarios

### Can (Health) Değeri Bulma
```
1. Oyuna girin, can değerini not edin (örn: 100)
2. EnesMem'i açın, işleme bağlanın
3. INT32, Exact, 100 → İlk Tarama
4. Oyunda hasar alın (can: 80)
5. Exact, 80 → Sonraki Tarama
6. Tekrarlayın ta ki 1-5 sonuç kalana kadar
7. Adresi izleme listesine ekleyin
```

### Para/Money Değeri
```
1. Mevcut parayı not edin (örn: 1500)
2. INT32 veya INT64, Exact, 1500
3. Parayı değiştirin (satın alma/satma)
4. Yeni değer ile Sonraki Tarama
5. İzleme listesine ekleyin ve düzenleyin
```

---

## 🔒 Yasal Uyarı / Legal Notice

> **TR**: Bu araç yalnızca eğitim amaçlı ve yetkili kullanım içindir. Sahibi olmadığınız veya analiz izninizin olmadığı yazılımlarda kullanmayın.

> **EN**: This tool is for educational purposes and authorized use only. Do not use on software you do not own or have permission to analyze.

---

## 📞 Destek / Support

- GitHub Issues: [github.com/enes59255/EnesMem/issues](https://github.com/enes59255/EnesMem/issues)
- E-posta: (email adresi eklenebilir)

---

**EnesMem v1.0** - Python Bellek Tarayıcı & Düzenleyici
