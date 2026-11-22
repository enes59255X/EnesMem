# EnesMem v1.2.0 - Python Bellek Tarayıcısı / Düzenleyici

> Python + PyQt6 ile yazılmış, üretim düzeyinde bir Cheat Engine alternatifi.
> Saf `ctypes`; pymem veya harici runtime gerekmez.

## İndir

| Dosya | Boyut | Açıklama |
|---|---:|---|
| **EnesMem.exe** | 48.5 MB | Tek dosya; kurulum gerektirmez |
| **EnesMem-1.2.0-win64.zip** | 34.9 MB | Taşınabilir klasör; daha hızlı açılış |

`EnesMem.exe` tek başına çalışır. Zip sürümünü indirirseniz klasörü çıkartıp
`EnesMem\EnesMem.exe` dosyasını çalıştırın; `_internal` klasörünü exe'den ayırmayın.

> **Yönetici:** Normal kullanıcı süreçleri için yönetici gerekmez. Korumalı veya
> yönetici olarak çalışan hedefler için **Yönetici olarak çalıştır** kullanın.

## Öne çıkanlar

- Süreç listeleme ve bağlanma
- Int8/16/32/64, UInt, Float, Double, String ve Bytes okuma/yazma
- First scan, next scan, AOB/wildcard, unknown-value (UIV) taramaları
- Exact, Bigger, Smaller, Between, Increased, Decreased, Changed, Unchanged,
  Increased/Decreased By ve Float tolerance modları
- Değer dondurma, canlı watchlist, pointer zinciri çözümleme
- Hex ve x64 assembly bellek görüntüleyici
- "What writes here" donanım breakpoint'leri
- Speedhack (NtDelayExecution detour)
- Modern koyu/açık arayüz, Türkçe/İngilizce dil, UAC yükseltme

## v1.2.0 arayüz yenilemesi

- Üç bölmeli, yeniden boyutlandırılabilir çalışma alanı: tarama rayı, sonuç
  çalışma alanı ve pointer denetçisi.
- Komut çubuğunda süreç durumu, bağlan/kes, yenileme hızı, tema ve yardım.
- Sonuç tablosunda arama, sayfalama, sayaçlar, boş durum ve izleme listesi
  eylemleri artık çakışmıyor.
- Pointer panelindeki çift başlık ve kırpılan etiketler giderildi.
- Koyu ve açık tema için ortak tasarım tokenları; mono yazı tipi yalnızca
  adres/değerlerde.
- Emoji yerine okunabilir metin ve standart Qt ikonları.

## Hızlı başlangıç

1. `EnesMem\EnesMem.exe` dosyasını çalıştırın.
2. **İşleme Bağlan** ile hedefi seçin.
3. Veri türünü ve değeri girin, **İlk Tarama** (F5) çalıştırın.
4. Oyunda değeri değiştirip **Sonraki Tarama** (F6) ile daraltın.
5. Sonucu çift tıklayıp izleme listesine ekleyin.

## Doğrulama

- 121 Python testi, 20 Rust testi
- GUI smoke: bağlan, tara, ayır, kapat
- Frozen onedir ve onefile `--smoke-test` başarılı
