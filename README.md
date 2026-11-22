# EnesMem v1.1.0 — Python Bellek Tarayıcısı / Düzenleyici

> Python + PyQt6 ile yazılmış, üretim düzeyinde bir Cheat Engine alternatifi.
> Saf `ctypes`; pymem veya harici runtime gerekmez.

## İndir

| Dosya | Boyut | Açıklama |
|---|---:|---|
| **EnesMem.exe** | 48.5 MB | Tek dosya; kurulum gerektirmez |
| **EnesMem-1.1.0-win64.zip** | 34.9 MB | Taşınabilir klasör; daha hızlı açılış |

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
- Koyu tema, Türkçe/İngilizce arayüz, UAC yükseltme

## v1.1.0 yenilikleri

- Speedhack'te iki gerçek hata düzeltildi: 64-bit `VirtualAllocEx` adresinin
  kesilmesi ve hook'un ntdll talimatını ortadan bölmesi. Canlı hedef testi eklendi.
- UIV UNCHANGED bellek kullanımı ~4 GB'dan **~1.70 GiB** seviyesine indirildi.
- `scanner.py` 1707 satırdan **760 satıra** indirildi; first/next scan ayrı
  modüllere taşındı.
- 121 Python testi ve 20 Rust testi; canlı HWBP/speedhack testleri.
- Native `.pyd` için sürüm + SHA-256 bütünlük kontrolü.
- Tek dosya ve taşınabilir klasör çıktısı; ikisi de smoke testinden geçti.

## Doğrulama

- Python: **121/121 passed**
- Rust: **20/20 passed**
- GUI smoke: attach → scan → detach → close **OK**
- Paket: tek dosya ve klasör sürümü **OK**

SHA-256:

```text
09b2339c0e44dd69f26d31c09ede888418025e93961f81c32ede552002e63ff7  EnesMem-1.1.0-win64-onefile.exe
58505c292432e6ffc2b7be1614f146a73060a54aec3e4137dad7aadba0086033  EnesMem-1.1.0-win64.zip
```

## Lisans

MIT. Ayrıntılar için `LICENSE` dosyasına bakın.

Bu araç yalnızca eğitim ve yetkili test amacıyla kullanılmalıdır. Sahibi
olmadığınız veya analiz izniniz olmayan yazılımlarda kullanmayın.
