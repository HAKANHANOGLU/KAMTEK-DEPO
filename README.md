# KAMTEK DEPO

## Kurulum / Deploy adımları (FIFO uygulamasıyla aynı yöntem)

1. GitHub'da yeni bir repo oluştur (örn. `KAMTEK-DEPO`)
2. Bu klasördeki tüm dosyaları (app.py, data.py, db.py, excel_utils.py, requirements.txt, assets/) o repo'ya yükle
3. https://share.streamlit.io adresinden "New app" ile bu repo'yu seç, ana dosya olarak `app.py` göster, deploy et
4. Siteye giriş şifresi varsayılan olarak `kamtek2026` — değiştirmek istersen Streamlit Cloud'da "Settings > Secrets" kısmına şunu ekle:

```
SITE_SIFRE = "istediginsifre"
```

## Notlar
- Aras Kargo ve Yurtiçi Kargo'nun excel formatı tahmini olarak (esnek/otomatik sütun eşleştirme ile) ele alınıyor. Gerçek excel dosyaları eline geçtiğinde test edip gerekirse ince ayar yapabiliriz.
- Türkiye haritası internet bağlantısı gerektiriyor (Streamlit Cloud'da otomatik çalışır).
- Veriler kalıcı olarak `kamtek_depo.db` (SQLite) dosyasında saklanır.
