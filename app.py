# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import io
import base64
import html

import data
import db
import excel_utils
import stok_utils

st.set_page_config(page_title="KAMTEK DEPO", layout="wide", initial_sidebar_state="expanded")
db.init_db()

# ------------------------------------------------------------------
# PWA kurulumu (manifest + service worker + iOS/Android meta etiketleri)
# ------------------------------------------------------------------
# Streamlit'in kendi <head>'ine doğrudan erişim yok; bu component iframe'i
# Streamlit ile aynı origin'de çalıştığı için window.parent.document üzerinden
# manifest/meta/service-worker'ı ana sayfanın <head>'ine enjekte ediyoruz.
# Not: Streamlit websocket ile canlı çalıştığı için tam offline destek YOK -
# bu sadece "Ana Ekrana Ekle" ile gerçek bir uygulama gibi (adres çubuğu
# olmadan, kendi ikonuyla) açılmasını sağlıyor.
def _pwa_kurulum():
    components.html(
        """
        <script>
        (function () {
          var doc = window.parent.document;
          var win = window.parent;
          // Streamlit her etkileşimde bu script'i yeniden çalıştırır (rerun);
          // kurulum ve dinleyicilerin tek sefer eklenmesi için bayrak kullanıyoruz.
          if (win.__kamtekPwaInit) { return; }
          win.__kamtekPwaInit = true;

          var manifest = doc.createElement('link');
          manifest.rel = 'manifest';
          manifest.href = '/app/static/manifest.json';
          doc.head.appendChild(manifest);

          var themeColor = doc.createElement('meta');
          themeColor.name = 'theme-color';
          themeColor.content = '#378ADD';
          doc.head.appendChild(themeColor);

          var appleCapable = doc.createElement('meta');
          appleCapable.name = 'apple-mobile-web-app-capable';
          appleCapable.content = 'yes';
          doc.head.appendChild(appleCapable);

          var appleStatusBar = doc.createElement('meta');
          appleStatusBar.name = 'apple-mobile-web-app-status-bar-style';
          appleStatusBar.content = 'black-translucent';
          doc.head.appendChild(appleStatusBar);

          var appleTitle = doc.createElement('meta');
          appleTitle.name = 'apple-mobile-web-app-title';
          appleTitle.content = 'Kamtek Depo';
          doc.head.appendChild(appleTitle);

          var appleIcon = doc.createElement('link');
          appleIcon.rel = 'apple-touch-icon';
          appleIcon.href = '/app/static/icons/apple-touch-icon-180x180.png';
          doc.head.appendChild(appleIcon);

          if (!('serviceWorker' in navigator)) { return; }

          // ---- Güncelleme bildirimi banner'ı ----
          function bannerGoster(waitingWorker) {
            if (doc.getElementById('kamtek-pwa-update-banner')) { return; }
            var banner = doc.createElement('div');
            banner.id = 'kamtek-pwa-update-banner';
            banner.style.cssText =
              'position:fixed;left:0;right:0;bottom:0;z-index:999999;' +
              'background:#0C447C;color:#fff;padding:12px 16px;' +
              'display:flex;align-items:center;justify-content:center;gap:14px;' +
              'font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:14px;' +
              'box-shadow:0 -2px 8px rgba(0,0,0,.25);';
            banner.innerHTML =
              '<span>🔄 Yeni bir güncelleme var</span>' +
              '<button id="kamtek-pwa-update-btn" style="' +
              'background:#fff;color:#0C447C;border:none;border-radius:8px;' +
              'padding:8px 18px;font-weight:700;font-size:14px;">Güncelle</button>';
            doc.body.appendChild(banner);
            doc.getElementById('kamtek-pwa-update-btn').addEventListener('click', function () {
              banner.querySelector('span').textContent = '⏳ Güncelleniyor...';
              doc.getElementById('kamtek-pwa-update-btn').style.display = 'none';
              waitingWorker.postMessage({ type: 'SKIP_WAITING' });
            });
          }

          var yenilendi = false;
          navigator.serviceWorker.addEventListener('controllerchange', function () {
            if (yenilendi) { return; }
            yenilendi = true;
            win.location.reload();
          });

          navigator.serviceWorker.register('/app/static/service-worker.js').then(function (reg) {
            // Sayfa açıldığında zaten bekleyen bir güncelleme varsa hemen göster.
            if (reg.waiting && reg.active) {
              bannerGoster(reg.waiting);
            }
            reg.addEventListener('updatefound', function () {
              var yeniWorker = reg.installing;
              if (!yeniWorker) { return; }
              yeniWorker.addEventListener('statechange', function () {
                if (yeniWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  bannerGoster(yeniWorker);
                }
              });
            });
            // Kullanıcı uygulamayı açık bıraktığında da yeni sürüm var mı diye
            // periyodik kontrol et (her 30 dakikada bir).
            setInterval(function () { reg.update().catch(function () {}); }, 30 * 60 * 1000);
          }).catch(function () {});
        })();
        </script>
        """,
        height=0,
        width=0,
    )


_pwa_kurulum()

# ------------------------------------------------------------------
# Ortak stil
# ------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.st-key-kart1 button {
    background-color: #E6F1FB !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #0C447C !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart2 button {
    background-color: #FAEEDA !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #854F0B !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart3 button {
    background-color: #EAF3DE !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #27500A !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart4 button {
    background-color: #FAECE7 !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #993C1D !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart5 button {
    background-color: #F1E9FB !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #5B2A86 !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart6 button {
    background-color: #DFF4F1 !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #0F6B5C !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart7 button {
    background-color: #FBEAF0 !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #72243E !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart8 button {
    background-color: #FCEBEB !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #791F1F !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart9 button {
    background-color: #F1EFE8 !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #444441 !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart10 button {
    background-color: #FAEEDA !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #633806 !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart11 button {
    background-color: #E1F5EE !important; border: none !important; border-radius: 32px !important;
    height: 260px !important; font-weight: 700 !important; color: #0F6E56 !important;
    line-height: 1.5 !important; width: 100% !important;
}
.st-key-kart1 button, .st-key-kart1 button *,
.st-key-kart2 button, .st-key-kart2 button *,
.st-key-kart3 button, .st-key-kart3 button *,
.st-key-kart4 button, .st-key-kart4 button *,
.st-key-kart5 button, .st-key-kart5 button *,
.st-key-kart6 button, .st-key-kart6 button *,
.st-key-kart7 button, .st-key-kart7 button *,
.st-key-kart8 button, .st-key-kart8 button *,
.st-key-kart9 button, .st-key-kart9 button *,
.st-key-kart10 button, .st-key-kart10 button *,
.st-key-kart11 button, .st-key-kart11 button * {
    font-size: 40px !important;
}
.st-key-kartplan button {
    background-color: #F1E9FB !important; border: none !important; border-radius: 32px !important;
    height: 130px !important; font-weight: 700 !important; color: #5B2A86 !important;
    line-height: 1.4 !important; width: 100% !important; font-size: 30px !important;
}
.st-key-kartplan button * { font-size: 30px !important; }
.st-key-ik_kart_personel button, .st-key-ik_kart_puantaj button,
.st-key-pl_kart_gorevler button, .st-key-pl_kart_transfer button {
    background-color: #F1E9FB !important; border: none !important; border-radius: 24px !important;
    height: 110px !important; font-weight: 700 !important; color: #5B2A86 !important;
    line-height: 1.4 !important; width: 100% !important; font-size: 26px !important;
}
.st-key-ik_kart_personel button *, .st-key-ik_kart_puantaj button *,
.st-key-pl_kart_gorevler button *, .st-key-pl_kart_transfer button * { font-size: 26px !important; }
.st-key-kargo_radyo div[data-testid="stRadio"] label p {
    font-size: 19px !important;
}
.stApp {
    background-color: #F5F5F3 !important;
}
section[data-testid="stSidebar"] {
    background-color: #EDEDEA !important;
    border-right: 1px solid #DEDEDA !important;
}
section[data-testid="stSidebar"] button {
    background-color: transparent !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    color: #2C2C2A !important;
    font-weight: 500 !important;
    padding: 6px 10px !important;
}
section[data-testid="stSidebar"] button:hover {
    background-color: #FFFFFF !important;
}
div[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 10px !important;
    padding: 14px !important;
}
/* Ana sayfadaki KPI kutucukları artık tıklanabilir (button) - metrik kartı
   görünümünü koruyoruz. */
.st-key-kpi_kargo button, .st-key-kpi_iade button,
.st-key-kpi_transfer button, .st-key-kpi_bildirim button {
    background-color: #FFFFFF !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    min-height: 90px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    white-space: pre-line !important;
    color: #2C2C2A !important;
    font-weight: 600 !important;
    line-height: 1.6 !important;
}
.st-key-kpi_kargo button:hover, .st-key-kpi_iade button:hover,
.st-key-kpi_transfer button:hover, .st-key-kpi_bildirim button:hover {
    border-color: #378ADD !important;
}
[class*="st-key-kl_gun_kutu_"] button {
    background-color: #FFFFFF !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 8px !important;
    min-height: 52px !important;
    white-space: pre-line !important;
    font-size: 12px !important;
    padding: 4px !important;
}
/* Form alanları (metin/sayı/tarih girişi, seçim kutuları) arkaplanla aynı
   renkte kaybolup tıklanabilir/doldurulabilir olduğu belli olmuyordu.
   Not: bu Streamlit sürümünde selectbox/multiselect BaseWeb değil
   react-aria-components kullanıyor (data-baseweb değil .react-aria-ComboBox /
   .react-aria-ListBox slot class'ları) - gerçek kutunun kendi border'ı
   önceden vardı ama sayfa arkaplanıyla (#F5F5F3) birebir aynı renkteydi,
   bu yüzden görünmüyordu. Tarayıcıda inceleyip doğru elementi bulduk. */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
.react-aria-ComboBox > div,
.react-aria-Select > div {
    background-color: #FFFFFF !important;
    border: 1px solid #C9C9C4 !important;
    border-radius: 8px !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
.react-aria-ComboBox:focus-within > div,
.react-aria-Select:focus-within > div {
    border-color: #378ADD !important;
    box-shadow: 0 0 0 1px #378ADD !important;
}
/* Telefon ekranında sidebar tüm sayfayı kaplıyordu - genişliğini sınırla. */
@media (max-width: 640px) {
    section[data-testid="stSidebar"] {
        width: 76vw !important;
        min-width: 76vw !important;
        max-width: 300px !important;
    }
    /* Stok Sayım'daki filtre satırı, masaüstünde sütun genişliğine hizalamak
       için boş hizalama div'leri kullanıyor; telefonda st.columns alt alta
       yığılınca bu boş div'ler gereksiz boşluk yaratıyordu. */
    .sayim-filtre-bosluk {
        display: none !important;
    }
    /* Arama kutusu ve Kategori'nin mobildeki sırasını masaüstünden bağımsız
       olarak değiştiriyoruz: Kategori üstte, arama kutusu tabloya bitişik
       en altta - st.columns'un flex konteyneri mobilde dikey yığıldığı için
       CSS order burada çalışıyor. */
    [class*="_kategori_kutusu"] {
        order: 1 !important;
    }
    [class*="_arama_kutusu"] {
        order: 2 !important;
        margin-bottom: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Şifreli giriş (şimdilik tek ortak şifre - rol ayrımı ileride açılacak)
# ------------------------------------------------------------------
SIFRE = st.secrets.get("SITE_SIFRE", "kamtek2026")
ROL_ISIMLERI = {"depo": "Depo Personeli", "patron": "Patron", "gelistirici": "Geliştirici"}
# İK gibi hassas bölümleri görebilecek roller - şimdilik herkes görebiliyor (tek şifre var)
IK_GORME_YETKISI = {"depo", "patron", "gelistirici"}

if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
if "rol" not in st.session_state:
    st.session_state.rol = None

if not st.session_state.giris_yapildi:
    st.markdown("<h1 style='text-align:center; margin-top:80px;'>KAMTEK DEPO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        girilen = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if girilen == SIFRE:
                st.session_state.giris_yapildi = True
                st.session_state.rol = "gelistirici"
                st.rerun()
            else:
                st.error("Şifre hatalı.")
    st.stop()

# ------------------------------------------------------------------
# Sayfa yönlendirme
# ------------------------------------------------------------------
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "home"


def git(sayfa):
    st.session_state.sayfa = sayfa
    st.rerun()


def geri_butonu():
    if st.button("⬅ Ana Sayfa"):
        git("home")


def _img_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


@st.cache_data(ttl=20, show_spinner=False)
def _bildirim_verileri():
    """Bildirimle ilgili tüm veriyi TEK seferde çeker ve 20 saniye önbellekler.

    Eskiden hem sidebar'da hem ana sayfada hem de Bildirim sayfasında her
    bildirim için ayrı ayrı bildirim_okundu_mu() çağrılıyordu (N+1 istek) —
    bu, her sayfa geçişinde onlarca sıralı ağ isteğine (dolayısıyla belirgin
    bir bekleme süresine) sebep oluyordu. Artık 4 istek tek seferde yapılıp
    20 saniye boyunca tüm kullanıcılar/sayfalar arasında paylaşılıyor.
    """
    bugun_iso = date.today().isoformat()
    simdi_saat = datetime.now().strftime("%H:%M")
    try:
        gorevler = db.gorevler_getir_bekleyen_bildirim(bugun_iso, simdi_saat)
    except Exception:
        gorevler = []
    try:
        transferler = db.transfer_talepleri_getir("Bekliyor")
    except Exception:
        transferler = []
    try:
        dogumgunler = db.bugun_dogum_gunu_olanlar()
    except Exception:
        dogumgunler = []
    try:
        okunmus = db.bildirim_okundu_getir_gun(bugun_iso)
    except Exception:
        okunmus = set()
    return {"gorevler": gorevler, "transferler": transferler, "dogumgunler": dogumgunler, "okunmus": okunmus}


def _bildirim_sayisi(veri=None):
    veri = veri or _bildirim_verileri()
    okunmus = veri["okunmus"]
    sayac = sum(1 for g in veri["gorevler"] if ("gorev", str(g["id"])) not in okunmus)
    sayac += sum(1 for t in veri["transferler"] if ("transfer", str(t["id"])) not in okunmus)
    sayac += sum(1 for p in veri["dogumgunler"] if ("dogumgunu", str(p["id"])) not in okunmus)
    return sayac


def render_sidebar():
    with st.sidebar:
        b64 = _img_b64("kamtek_logo.png")
        if b64:
            st.markdown(
                f"<img src='data:image/png;base64,{b64}' style='width:100%;margin-bottom:4px;'>",
                unsafe_allow_html=True,
            )
        st.caption("KAMTEK DEPO")
        st.markdown("---")

        if st.button("🏠 Genel Bakış", use_container_width=True, key="nav_home"):
            git("home")

        st.markdown("**Sevkiyat ve Kargo**")
        if st.button("🗺️ Sevkiyat Planlama", use_container_width=True, key="nav_sevkiyat"):
            git("sevkiyat")
        if st.button("🚚 Kargo Takip", use_container_width=True, key="nav_kargotakip"):
            git("kargotakip")
        if st.button("🏷️ Kargo Fiyat Listesi", use_container_width=True, key="nav_fiyatlistesi"):
            git("fiyatlistesi")
        if st.button("✅ Tamamlanmış Kargolar", use_container_width=True, key="nav_tamamlanankargolar"):
            git("tamamlanankargolar")

        st.markdown("**Depo ve Stok**")
        if st.button("📦 Depo", use_container_width=True, key="nav_depo"):
            git("depo")
        if st.button("📊 Stok Takip", use_container_width=True, key="nav_stoktakip"):
            git("stoktakip")
        if st.button("🔁 Depolar Arası Transfer", use_container_width=True, key="nav_transfer"):
            git("depotransfer")
        if st.button("↩️ İade", use_container_width=True, key="nav_iade"):
            git("iade")
        if st.button("☑️ Kontrol Listesi", use_container_width=True, key="nav_kontrollistesi"):
            git("kontrollistesi")

        st.markdown("**Yönetim**")
        if st.session_state.rol in IK_GORME_YETKISI:
            if st.button("👥 Personel Yönetimi", use_container_width=True, key="nav_ik"):
                git("insankaynaklari")
        if st.button("🗓️ Planlama", use_container_width=True, key="nav_planlama"):
            git("planlama")
        bildirim_n = _bildirim_sayisi()
        bildirim_etiket = f"🔔 Bildirim 🔴{bildirim_n}" if bildirim_n > 0 else "🔔 Bildirim"
        if st.button(bildirim_etiket, use_container_width=True, key="nav_bildirim"):
            git("bildirim")


# ------------------------------------------------------------------
# ANA SAYFA
# ------------------------------------------------------------------
def sayfa_home():
    st.markdown(f"<div style='color:#8A8A85; font-size:12px;'>Kamtek Depo / genel bakış</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:22px; font-weight:600; margin-bottom:18px;'>Bugün, {date.today().strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)

    try:
        bugun_sevkiyat = len(db.tamamlanan_kargolar_getir_ay(date.today().year, date.today().month))
    except Exception:
        bugun_sevkiyat = 0
    try:
        bekleyen_iade = len([i for i in db.iadeler_getir() if i.get("durum") != "Kabul Edildi"])
    except Exception:
        bekleyen_iade = 0
    veri = _bildirim_verileri()
    bildirim_n = _bildirim_sayisi(veri)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(key="kpi_kargo"):
            if st.button(f"{bugun_sevkiyat}\n\nBu ay tamamlanan kargo", key="kpi_kargo_btn", use_container_width=True):
                git("tamamlanankargolar")
    with c2:
        with st.container(key="kpi_iade"):
            if st.button(f"{bekleyen_iade}\n\nBekleyen iade", key="kpi_iade_btn", use_container_width=True):
                git("iade")
    with c3:
        with st.container(key="kpi_transfer"):
            if st.button(f"{len(veri['transferler'])}\n\nBekleyen transfer talebi", key="kpi_transfer_btn", use_container_width=True):
                git("depotransfer")
    with c4:
        with st.container(key="kpi_bildirim"):
            if st.button(f"{bildirim_n}\n\nBekleyen bildirim", key="kpi_bildirim_btn", use_container_width=True):
                git("bildirim")

    st.write("")
    st.markdown("**Son bildirimler**")
    gosterildi = False
    for p in veri["dogumgunler"]:
        st.success(f"🎂 {p['ad_soyad']}'in bugün doğum günü!")
        gosterildi = True
    for g in veri["gorevler"]:
        st.warning(f"⏰ {g.get('saat') or ''} — {g['aciklama']}")
        gosterildi = True
    for t in veri["transferler"]:
        st.info(f"🔁 {t['talep_eden_depo']} → {t['hedef_depo']}: {t['urun_aciklama']} ({t.get('adet') or '?'} adet)")
        gosterildi = True
    if not gosterildi:
        st.caption("Şu an bekleyen bir bildirim yok.")


# ------------------------------------------------------------------
# SEVKİYAT PLANLAMA
# ------------------------------------------------------------------
# geojson'daki il isimleri bizim ALL-CAPS listemizle birebir eşleşmiyor
# (örn. "İstanbul", "Afyon"), bu yüzden normalize ederek eşleştiriyoruz.
# Modül seviyesinde tanımlı (nested/closure değil) çünkü _il_harita_verisi'nin
# döndürdüğü sözlüğün içine konursa st.cache_data pickle ile serialize
# edemiyor ("Cannot serialize the return value") - fonksiyonlar sadece
# modül seviyesinde tanımlıysa referansla picklenebilir.
_IL_EK_ESLESTIRME = {"AFYONKARAHİSAR": "AFYON", "MERSİN": "İÇEL"}


def _norm_il(s):
    s = _IL_EK_ESLESTIRME.get(s.upper(), s.upper())
    return excel_utils.norm(s)


@st.cache_data(ttl=None, show_spinner=False)
def _il_harita_verisi():
    """Türkiye il sınırları + il ismi eşleştirme haritalarını GitHub'dan bir
    kez çeker ve kalıcı önbellekler. Eskiden bu ağ isteği ve 81 ilin
    centroid/bbox hesaplaması Sevkiyat Planlama sayfasına HER girişte yeniden
    yapılıyordu — sayfa geçişini belirgin şekilde yavaşlatan asıl sebep
    buydu. Veri statik olduğu için süresiz önbellekleniyor (uygulama yeniden
    başlatılınca zaten temizlenir). Dönen sözlük yalnızca picklenebilir
    (dict/list/str/float) değerler içermeli - fonksiyon KONMAMALI."""
    import requests

    geojson_url = "https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/geo/tr-cities-utf8.json"
    geojson = requests.get(geojson_url, timeout=8).json()

    def _il_centroid_bbox(feature):
        geom = feature["geometry"]
        coords = geom["coordinates"]
        depth = 2 if geom["type"] == "Polygon" else 3
        pts = []

        def collect(c, d):
            if d == 0:
                pts.append(c)
            else:
                for cc in c:
                    collect(cc, d - 1)

        collect(coords, depth)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return sum(xs) / len(xs), sum(ys) / len(ys), max(xs) - min(xs), max(ys) - min(ys)

    geojson_isim_haritasi = {_norm_il(f["properties"]["name"]): f["properties"]["name"] for f in geojson["features"]}
    norm_to_il = {_norm_il(il): il for il in data.IL_LISTESI}

    lons, lats, texts, sizes = [], [], [], []
    for f in geojson["features"]:
        cx, cy, w, h = _il_centroid_bbox(f)
        lons.append(cx)
        lats.append(cy)
        texts.append(f["properties"]["name"])
        # küçük illerde küçük, büyük illerde biraz daha büyük yazı - sınırı taşmasın diye
        alan = w * h
        sizes.append(max(5, min(10, alan * 350)))

    return {
        "geojson": geojson,
        "geojson_isim_haritasi": geojson_isim_haritasi,
        "norm_to_il": norm_to_il,
        "tum_isimler": [f["properties"]["name"] for f in geojson["features"]],
        "lons": lons, "lats": lats, "texts": texts, "sizes": sizes,
    }


def sayfa_sevkiyat():
    geri_butonu()
    st.header("Sevkiyat Planlama")

    col_map, col_bosluk = st.columns([1, 1])
    with col_map:
        if "secili_il" not in st.session_state:
            st.session_state.secili_il = "İZMİR"

        # Haritadan bir önceki çalıştırmada il seçildiyse, selectbox oluşturulmadan
        # önce uygula (widget'ın değeri, oluşturulduktan sonra aynı çalıştırmada
        # değiştirilemiyor - bu yüzden bir sonraki rerun'da burada uyguluyoruz).
        if "harita_secim_bekliyor" in st.session_state:
            st.session_state.secili_il = st.session_state.pop("harita_secim_bekliyor")

        secili_il = st.selectbox("Varış İli", data.IL_LISTESI, key="secili_il")
        try:
            import plotly.graph_objects as go

            hv = _il_harita_verisi()
            geojson = hv["geojson"]
            norm_to_il = hv["norm_to_il"]
            gercek_isim = hv["geojson_isim_haritasi"].get(_norm_il(secili_il))

            if gercek_isim is None:
                st.info(f"{secili_il} haritada bulunamadı, sadece il seçimiyle devam edebilirsiniz.")
            else:
                df_map = pd.DataFrame({"il": hv["tum_isimler"]})
                df_map["secili"] = df_map["il"].apply(lambda x: 1 if x == gercek_isim else 0)
                lons, lats, texts, sizes = hv["lons"], hv["lats"], hv["texts"], hv["sizes"]

                fig = go.Figure()
                fig.add_trace(go.Choropleth(
                    geojson=geojson, locations=df_map["il"], z=df_map["secili"],
                    featureidkey="properties.name",
                    colorscale=[[0, "#E6F1FB"], [1, "#378ADD"]],
                    showscale=False, marker_line_color="#9DB8CC", marker_line_width=0.6,
                ))
                fig.add_trace(go.Scattergeo(
                    lon=lons, lat=lats, text=texts, mode="text",
                    textfont=dict(size=sizes, color="#1F2937"),
                    hoverinfo="skip", showlegend=False,
                ))
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0))

                event = st.plotly_chart(
                    fig, use_container_width=True, key="il_haritasi",
                    on_select="rerun", selection_mode="points",
                )
                st.caption("Haritadan bir ile tıklayarak da varış ilini seçebilirsiniz.")

                if event and event.get("selection", {}).get("points"):
                    tiklanan = event["selection"]["points"][0]
                    loc = tiklanan.get("location")
                    if not loc:
                        # Tıklama, il isimlerini gösteren metin katmanına denk gelmiş olabilir;
                        # bu durumda nokta indeksinden ilin adını buluyoruz.
                        pt_idx = tiklanan.get("point_index", tiklanan.get("pointIndex"))
                        if pt_idx is not None and 0 <= pt_idx < len(texts):
                            loc = texts[pt_idx]
                    if loc:
                        eslesen_il = norm_to_il.get(_norm_il(loc))
                        if eslesen_il and eslesen_il != st.session_state.secili_il:
                            st.session_state["harita_secim_bekliyor"] = eslesen_il
                            st.rerun()
        except Exception as e:
            st.info(f"Harita şu an yüklenemedi ({e}). İl seçimiyle devam edebilirsiniz.")

    with col_bosluk:
        with st.container(key="kartplan"):
            if st.button("📝\n\nPlanlanacak Kargolar", use_container_width=True):
                st.session_state.planlanan_goster = not st.session_state.get("planlanan_goster", False)

        if st.session_state.get("planlanan_goster", False):
            st.caption("Müşteri adı, alıcı adres, koli adedi ve planlanan tarihi buraya serbestçe yazabilirsiniz.")
            mevcut = db.planlanan_kargolar_getir()
            if mevcut:
                df_plan = pd.DataFrame(mevcut)[
                    ["musteri_adi", "alici_adresi", "aciklama", "siparis_tarihi", "koli_adedi", "planlanan_tarih"]
                ]
            else:
                df_plan = pd.DataFrame({"musteri_adi": [""] * 8, "alici_adresi": [""] * 8,
                                         "aciklama": [""] * 8, "siparis_tarihi": [""] * 8,
                                         "koli_adedi": [""] * 8, "planlanan_tarih": [""] * 8})
            df_plan.columns = ["Müşteri Adı", "Alıcı Adres", "Açıklama", "Sipariş Tarihi", "Koli Adedi", "Planlanan Tarih"]
            edited_plan = st.data_editor(
                df_plan, use_container_width=True, num_rows="dynamic", key="planlanan_editor", height=350,
            )
            if st.button("Kaydet", key="planlanan_kaydet"):
                satirlar = [
                    {
                        "musteri_adi": row["Müşteri Adı"], "alici_adresi": row["Alıcı Adres"],
                        "aciklama": row["Açıklama"], "siparis_tarihi": row["Sipariş Tarihi"],
                        "koli_adedi": row["Koli Adedi"], "planlanan_tarih": row["Planlanan Tarih"],
                    }
                    for _, row in edited_plan.iterrows()
                    if any(str(row[c]).strip() not in ("", "nan", "None") for c in edited_plan.columns)
                ]
                db.planlanan_kargolar_kaydet(satirlar)
                st.success("Planlanan kargolar kaydedildi.")

    st.markdown("---")
    st.subheader("Gönderi Hesapla")
    st.caption("Her satıra bir gönderi grubu için Miktar (adet) ve Desi bilgisini girin.")

    if "sevkiyat_df" not in st.session_state:
        st.session_state.sevkiyat_df = pd.DataFrame(
            {"Miktar": [None] * 15, "Desi": [None] * 15}
        )

    edited = st.data_editor(
        st.session_state.sevkiyat_df,
        num_rows="dynamic",
        use_container_width=True,
        key="sevkiyat_editor",
        column_config={
            "Miktar": st.column_config.NumberColumn("Miktar", min_value=0, step=1),
            "Desi": st.column_config.NumberColumn("Desi", min_value=0, step=1),
        },
    )

    col_hesapla, col_kargolastir = st.columns(2)
    hesapla_tiklandi = col_hesapla.button("Hesapla", type="primary", use_container_width=True)
    kargolastir_tiklandi = col_kargolastir.button("📦 Kargolaştır", use_container_width=True)

    if hesapla_tiklandi:
        gecerli_satirlar = [
            (row["Miktar"], row["Desi"]) for _, row in edited.iterrows()
            if pd.notna(row["Miktar"]) and pd.notna(row["Desi"]) and row["Miktar"] > 0 and row["Desi"] > 0
        ]
        if not gecerli_satirlar:
            st.warning("Lütfen en az bir satıra miktar ve desi girin.")
            st.session_state.hesap_sonuclari = None
        else:
            sonuclar = []
            for kargo in data.PRICING:
                if not data.carrier_ships_to(kargo, secili_il):
                    continue
                toplam = 0
                for miktar, desi in gecerli_satirlar:
                    birim = data.calc_unit_price(kargo, desi)
                    if birim is not None:
                        toplam += birim * miktar
                sonuclar.append((kargo, toplam))
            if not sonuclar:
                st.warning(f"{secili_il} iline gönderim yapan kargo firması bulunamadı.")
            st.session_state.hesap_sonuclari = sonuclar
            st.session_state.hesap_il = secili_il
            st.session_state.hesap_detay = gecerli_satirlar

    sonuclar = st.session_state.get("hesap_sonuclari")
    if sonuclar:
        st.markdown(f"**{st.session_state.hesap_il} için hesaplanan fiyatlar:**")
        en_ucuz_kargo = min(sonuclar, key=lambda x: x[1])[0]
        secenekler = [f"{kargo} — {toplam:,.2f} TL (+ KDV)" + ("  ✓ Önerilen" if kargo == en_ucuz_kargo else "")
                      for kargo, toplam in sonuclar]
        with st.container(key="kargo_radyo"):
            secim = st.radio("Kargo firması seçin:", secenekler, key="kargo_secim_radio")
        secilen_index = secenekler.index(secim)
        secilen_kargo, secilen_tutar = sonuclar[secilen_index]

        if kargolastir_tiklandi:
            detay_ozet = "; ".join(f"{m} adet x {d} desi" for m, d in st.session_state.hesap_detay)
            db.tamamlanan_kargo_kaydet(
                date.today().isoformat(), st.session_state.hesap_il, secilen_kargo, secilen_tutar, detay_ozet,
            )
            st.success(f"{secilen_kargo} ile kargolaştırıldı ({secilen_tutar:,.2f} TL). "
                       f"'Tamamlanmış Kargolar' sayfasından takip edebilirsiniz.")
            st.session_state.hesap_sonuclari = None
    elif kargolastir_tiklandi:
        st.warning("Önce 'Hesapla' ile bir fiyat hesaplaması yapıp kargo firması seçmeniz gerekiyor.")


# ------------------------------------------------------------------
# KARGO TAKİP
# ------------------------------------------------------------------
def sayfa_kargotakip():
    geri_butonu()
    st.header("Kargo Takip")

    col1, col2 = st.columns(2)
    with col1:
        secili_tarih = st.date_input("Gün Seçin", value=date.today())
    with col2:
        secili_kargo = st.selectbox("Excel Yüklenecek Kargo Firması", list(data.PRICING.keys()))

    yuklenen = st.file_uploader(f"{secili_kargo} için {secili_tarih.strftime('%d.%m.%Y')} tarihli Excel dosyasını yükleyin", type=["xls", "xlsx"])
    if yuklenen is not None:
        try:
            df = excel_utils.excel_oku(yuklenen)
            satirlar, mapping = excel_utils.standart_satirlara_donustur(df)
            db.kargo_takip_kaydet(secili_tarih.isoformat(), secili_kargo, satirlar)
            st.success(f"{len(satirlar)} satır kaydedildi ({secili_kargo}, {secili_tarih.strftime('%d.%m.%Y')}).")
            eksik = [f for f, c in mapping.items() if c is None]
            if eksik:
                st.caption(f"Bu dosyada bulunamayan alanlar boş bırakıldı: {', '.join(eksik)}")
        except Exception as e:
            st.error(f"Excel okunurken hata oluştu: {e}")

    st.markdown("---")
    kayitlar = db.kargo_takip_getir(secili_tarih.isoformat())
    if kayitlar:
        df_goster = pd.DataFrame(kayitlar)[
            ["kargo_firmasi", "gonderi_tarihi", "gonderi_no", "alici_adi", "alici_adresi", "varis_il", "odeme_sekli", "desi"]
        ]
        df_goster.columns = ["Kargo Firması", "Gönderi Tarihi", "Gönderi No", "Alıcı Adı", "Alıcı Adresi", "Varış İl", "Ödeme Şekli", "Desi"]
        df_goster["Sorgula"] = df_goster.apply(
            lambda r: data.tracking_url(r["Kargo Firması"], r["Gönderi No"]), axis=1
        )
        st.dataframe(
            df_goster, use_container_width=True, height=450,
            column_config={
                "Sorgula": st.column_config.LinkColumn("Sorgula", display_text="🔗 Kargo Durumu")
            },
        )
        st.caption(
            "\"Sorgula\" linki kargo firmasının kendi halka açık gönderi sorgulama sayfasını, "
            "takip numarası otomatik dolu şekilde açar."
        )
    else:
        st.info(f"{secili_tarih.strftime('%d.%m.%Y')} tarihi için henüz kayıt yok.")


# ------------------------------------------------------------------
# DEPO
# ------------------------------------------------------------------
def sayfa_depo():
    geri_butonu()
    st.header("Depo")

    if "depo_alt_sayfa" not in st.session_state:
        st.session_state.depo_alt_sayfa = None

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋\n\nDepo Sayım Fişleri", use_container_width=True):
            st.session_state.depo_alt_sayfa = "sayim"
            st.rerun()
    with c2:
        if st.button("🧹\n\nDepo Temizlik Çizelgesi", use_container_width=True):
            st.session_state.depo_alt_sayfa = "temizlik"
            st.rerun()

    st.markdown("---")

    if st.session_state.depo_alt_sayfa == "sayim":
        depo_sayim_bolumu()
    elif st.session_state.depo_alt_sayfa == "temizlik":
        depo_temizlik_bolumu()


def depo_sayim_bolumu():
    st.subheader("Depo Sayım Fişleri")
    st.caption("Depo sayımı haftalık programlanır — her gün deponun bir kısmı sayılır, hafta sonunda tüm depo sayılmış olur.")

    secili_tarih = st.date_input("Sayım Tarihi (Excel Yükleme)", value=date.today(), key="sayim_tarih")
    if "sayim_uploader_key" not in st.session_state:
        st.session_state.sayim_uploader_key = 0
    yuklenen = st.file_uploader(
        "Sayım Excel Dosyasını Yükleyin", type=["xls", "xlsx"],
        key=f"sayim_uploader_{st.session_state.sayim_uploader_key}",
    )
    if yuklenen is not None:
        db.depo_sayim_kaydet(secili_tarih.isoformat(), yuklenen.name, yuklenen.getvalue())
        st.session_state.sayim_uploader_key += 1
        st.session_state.sayim_basarili_mesaj = f"{yuklenen.name} kaydedildi ({secili_tarih.strftime('%d.%m.%Y')})."
        st.rerun()

    if st.session_state.get("sayim_basarili_mesaj"):
        st.success(st.session_state.sayim_basarili_mesaj)
        st.session_state.sayim_basarili_mesaj = None

    st.markdown("---")
    st.markdown("**Haftalık Sayım Takvimi**")

    # secili_tarih'in içinde bulunduğu haftanın Pazartesi-Pazar günlerini bul
    hafta_baslangic = secili_tarih - timedelta(days=secili_tarih.weekday())
    gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    hafta_gunleri = [hafta_baslangic + timedelta(days=i) for i in range(7)]

    notlar = db.sayim_notlari_getir([g.isoformat() for g in hafta_gunleri])

    if "sayim_secili_gun" not in st.session_state:
        st.session_state.sayim_secili_gun = None

    baslik_cols = st.columns(7)
    for col, isim in zip(baslik_cols, gun_isimleri):
        col.markdown(f"**{isim}**")

    gun_cols = st.columns(7)
    gun_dosyalari = {}
    gun_otomatik_sayimlar = {}
    for col, gun, isim in zip(gun_cols, hafta_gunleri, gun_isimleri):
        with col:
            kayitlar = db.depo_sayim_getir(gun.isoformat())
            gun_dosyalari[gun.isoformat()] = kayitlar
            tik = "✅" if kayitlar else "⬜"
            etiket = f"{tik}\n{gun.strftime('%d.%m')}"
            if st.button(etiket, key=f"gun_btn_{gun.isoformat()}", use_container_width=True):
                st.session_state.sayim_secili_gun = gun.isoformat()
                st.session_state.sayim_secili_tur = "excel"

            otomatik = db.stok_sayim_oturumlari_getir(gun.isoformat())
            gun_otomatik_sayimlar[gun.isoformat()] = otomatik
            otomatik_tik = "🟢" if otomatik else "⚪"
            if st.button(f"{otomatik_tik}\nOtomatik sayım", key=f"gun_oto_btn_{gun.isoformat()}", use_container_width=True):
                st.session_state.sayim_secili_gun = gun.isoformat()
                st.session_state.sayim_secili_tur = "otomatik"

            not_mevcut = notlar.get(gun.isoformat(), "")
            yeni_not = st.text_input("Not", value=not_mevcut, key=f"not_{gun.isoformat()}", label_visibility="collapsed",
                                      placeholder="Not ekle...")
            if yeni_not != not_mevcut:
                db.sayim_not_kaydet(gun.isoformat(), yeni_not)

    st.markdown("---")
    secili_gun = st.session_state.sayim_secili_gun
    secili_tur = st.session_state.get("sayim_secili_tur", "excel")

    if not secili_gun:
        st.info("Yukarıdaki takvimden bir güne tıklayarak o günün sayım detayını görebilirsiniz.")
        return

    gun_str = datetime.fromisoformat(secili_gun).strftime("%d.%m.%Y")

    if secili_tur == "otomatik":
        otomatik = gun_otomatik_sayimlar.get(secili_gun, db.stok_sayim_oturumlari_getir(secili_gun))
        if not otomatik:
            st.info(f"{gun_str} için Stok Sayım'dan gelen bir otomatik sayım yok.")
        else:
            st.markdown(f"**{gun_str} — Stok Sayım'dan gelen otomatik sayımlar:**")
            for oturum in otomatik:
                personel_str = f" — {oturum['personel_adi']}" if oturum.get("personel_adi") else ""
                st.caption(f"🔢 Sayım #{oturum['id']}{personel_str}")
                detaylar = db.stok_sayim_detay_getir(oturum["id"])
                if not detaylar:
                    st.write("Bu sayımda kayıtlı ürün yok.")
                else:
                    df_detay = pd.DataFrame(detaylar)[["urun_adi", "guncel_stok", "sayilan", "fark"]]
                    df_detay.columns = ["Ürün Adı", "Güncel Stok", "Sayılan", "Fark"]

                    def _fark_var_mi(f):
                        try:
                            return abs(float(str(f).replace(",", "."))) > 1e-9
                        except (ValueError, TypeError):
                            return False

                    df_farkli = df_detay[df_detay["Fark"].apply(_fark_var_mi)]
                    if df_farkli.empty:
                        st.write("Bu sayımda fark bulunan ürün yok (her şey stokla uyumlu).")
                    else:
                        st.dataframe(df_farkli, use_container_width=True, hide_index=True)

                    st.markdown("Sayılan tüm ürünler:")
                    st.dataframe(df_detay, use_container_width=True, hide_index=True)
        return

    kayitlar = gun_dosyalari.get(secili_gun, db.depo_sayim_getir(secili_gun))
    if not kayitlar:
        st.info(f"{gun_str} için henüz sayım dosyası yok.")
    else:
        st.markdown(f"**{gun_str} tarihli sayım — sadece 'Sayım' sütununda değer girilmiş satırlar:**")
        st.caption("🔴 Kırmızı satır: depodaki mevcut stok değeri ile sayım değeri birbirini tutmuyor.")
        for k in kayitlar:
            c_baslik, c_indir, c_sil = st.columns([6, 1, 1])
            c_baslik.caption(f"📄 {k['dosya_adi']}")
            c_indir.download_button(
                label="⬇ İndir", data=k["dosya_icerik"],
                file_name=k["dosya_adi"], key=f"indir_{k['id']}",
            )
            if c_sil.button("🗑 Sil", key=f"sil_{k['id']}"):
                db.depo_sayim_sil(k["id"])
                st.rerun()
            try:
                filtreli = excel_utils.sayim_satirlarini_filtrele(io.BytesIO(k["dosya_icerik"]))
                if filtreli.empty:
                    hata = filtreli.attrs.get("hata")
                    st.write(hata if hata else "Bu dosyada 'Sayım' sütunu bulunamadı ya da sayılmış satır yok.")
                else:
                    uyumsuz_maske = filtreli.attrs.get("uyumsuz_maske")
                    if uyumsuz_maske:
                        def _kirmizi_satir(row, _maske=uyumsuz_maske):
                            if _maske[row.name]:
                                return ["background-color: #FCA5A5"] * len(row)
                            return [""] * len(row)
                        st.dataframe(filtreli.style.apply(_kirmizi_satir, axis=1), use_container_width=True)
                    else:
                        st.dataframe(filtreli, use_container_width=True)
            except Exception as e:
                st.error(f"Dosya okunurken hata oluştu: {e}")


ODALAR = ["Sevk Odası", "Erkekler Tuvaleti", "Kadınlar Tuvaleti", "Mutfak",
          "Sinan Bey'in Odası", "Ofis 1", "Ofis 2", "Ofis 3"]


def _temizlik_kroki_svg(temizlenenler_bugun):
    def renk(oda):
        return "#BFE3C4" if oda in temizlenenler_bugun else "#ffffff"

    def isaret(oda):
        return "✓" if oda in temizlenenler_bugun else "+"

    def isaret_renk(oda):
        return "#1f7a33" if oda in temizlenenler_bugun else "#2f7d4f"

    html = f"""
<div style="display:flex;gap:24px;justify-content:center;flex-wrap:wrap;">
  <div style="text-align:center;">
    <div style="font-size:13px;font-weight:700;letter-spacing:1px;color:#8a6d3b;margin-bottom:6px;">ZEMİN KAT</div>
    <svg width="300" height="400" viewBox="0 0 480 640" style="background:#f7f5f0;border:1px solid #d9d2c0;border-radius:4px;">
      <rect x="10" y="10" width="460" height="620" fill="#fff" stroke="#26352c" stroke-width="4"/>
      <rect x="195" y="10" width="90" height="620" fill="#dfe6e2" stroke="#c3cdc7" stroke-width="1" stroke-dasharray="6,4"/>
      <rect x="205" y="600" width="70" height="20" fill="#fff" stroke="#26352c" stroke-width="2"/>
      <text x="240" y="614" font-size="10" text-anchor="middle" fill="#6b6355">GİRİŞ</text>

      <rect x="295" y="500" width="165" height="120" fill="{renk('Sevk Odası')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="377" y="558" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">SEVK ODASI</text>
      <text x="377" y="578" font-size="20" text-anchor="middle" fill="{isaret_renk('Sevk Odası')}">{isaret('Sevk Odası')}</text>

      <rect x="20" y="360" width="165" height="90" fill="{renk('Erkekler Tuvaleti')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="102" y="398" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">ERKEKLER TUVALETİ</text>
      <text x="102" y="420" font-size="20" text-anchor="middle" fill="{isaret_renk('Erkekler Tuvaleti')}">{isaret('Erkekler Tuvaleti')}</text>

      <rect x="20" y="260" width="165" height="90" fill="{renk('Kadınlar Tuvaleti')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="102" y="298" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">KADINLAR TUVALETİ</text>
      <text x="102" y="320" font-size="20" text-anchor="middle" fill="{isaret_renk('Kadınlar Tuvaleti')}">{isaret('Kadınlar Tuvaleti')}</text>

      <rect x="295" y="120" width="165" height="150" fill="{renk('Mutfak')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="377" y="190" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">MUTFAK</text>
      <text x="377" y="212" font-size="20" text-anchor="middle" fill="{isaret_renk('Mutfak')}">{isaret('Mutfak')}</text>

      <rect x="20" y="30" width="165" height="220" fill="#e4dcc8" stroke="#b8a97e" stroke-width="1.5" stroke-dasharray="4,3"/>
      <text x="102" y="145" font-size="11" font-style="italic" font-weight="600" text-anchor="middle" fill="#7a6a3f">KOLİ İSTİFİ</text>
      <rect x="295" y="30" width="165" height="80" fill="#e4dcc8" stroke="#b8a97e" stroke-width="1.5" stroke-dasharray="4,3"/>
      <text x="377" y="75" font-size="11" font-style="italic" font-weight="600" text-anchor="middle" fill="#7a6a3f">KOLİ İSTİFİ</text>
      <rect x="295" y="280" width="165" height="210" fill="#e4dcc8" stroke="#b8a97e" stroke-width="1.5" stroke-dasharray="4,3"/>
      <text x="377" y="385" font-size="11" font-style="italic" font-weight="600" text-anchor="middle" fill="#7a6a3f">KOLİ İSTİFİ</text>
    </svg>
  </div>

  <div style="text-align:center;">
    <div style="font-size:13px;font-weight:700;letter-spacing:1px;color:#8a6d3b;margin-bottom:6px;">ÜST KAT</div>
    <svg width="300" height="400" viewBox="0 0 480 640" style="background:#f7f5f0;border:1px solid #d9d2c0;border-radius:4px;">
      <rect x="10" y="10" width="460" height="620" fill="#fff" stroke="#26352c" stroke-width="4"/>
      <rect x="205" y="565" width="70" height="55" fill="#fff" stroke="#26352c" stroke-width="2"/>
      <text x="240" y="636" font-size="10" text-anchor="middle" fill="#6b6355">MERDİVEN</text>
      <rect x="150" y="230" width="180" height="180" fill="#eef1ef" stroke="#c3cdc7" stroke-width="1.5" stroke-dasharray="5,4"/>
      <text x="240" y="322" font-size="10" text-anchor="middle" fill="#6b6355">KARE BOŞLUK</text>

      <rect x="20" y="420" width="200" height="150" fill="{renk("Sinan Bey'in Odası")}" stroke="#8a6d3b" stroke-width="3"/>
      <text x="120" y="490" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">SİNAN BEY'İN ODASI</text>
      <text x="120" y="515" font-size="20" text-anchor="middle" fill="{isaret_renk("Sinan Bey'in Odası")}">{isaret("Sinan Bey'in Odası")}</text>

      <rect x="260" y="420" width="200" height="150" fill="{renk('Ofis 1')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="360" y="495" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">OFİS 1</text>
      <text x="360" y="518" font-size="20" text-anchor="middle" fill="{isaret_renk('Ofis 1')}">{isaret('Ofis 1')}</text>

      <rect x="20" y="70" width="200" height="150" fill="{renk('Ofis 2')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="120" y="145" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">OFİS 2</text>
      <text x="120" y="168" font-size="20" text-anchor="middle" fill="{isaret_renk('Ofis 2')}">{isaret('Ofis 2')}</text>

      <rect x="260" y="70" width="200" height="150" fill="{renk('Ofis 3')}" stroke="#26352c" stroke-width="2.5"/>
      <text x="360" y="145" font-size="13" font-weight="700" text-anchor="middle" fill="#1f2a24">OFİS 3</text>
      <text x="360" y="168" font-size="20" text-anchor="middle" fill="{isaret_renk('Ofis 3')}">{isaret('Ofis 3')}</text>
    </svg>
  </div>
</div>
"""
    # Markdown, 4+ boşlukla başlayan satırları "kod bloğu" sayıp düz metin olarak
    # bastığı için, HTML/SVG'yi render edebilmesi için her satır başındaki
    # girintiyi temizliyoruz.
    return "\n".join(line.strip() for line in html.strip().splitlines())


def depo_temizlik_bolumu():
    st.subheader("Depo Temizlik Çizelgesi")

    secili_tarih = st.date_input("Tarih", value=date.today(), key="temizlik_tarih")
    tarih_iso = secili_tarih.isoformat()

    kayitlar_bugun = db.temizlik_getir_gun_oda(tarih_iso)
    temizlenenler = set(kayitlar_bugun.keys())

    st.markdown(_temizlik_kroki_svg(temizlenenler), unsafe_allow_html=True)
    st.caption("✓ (yeşil) = seçili günde temizlendi olarak işaretlenmiş, + (beyaz) = henüz işaretlenmemiş.")

    st.markdown("---")
    secili_oda = st.selectbox("Bir alan seçin", ODALAR, key="temizlik_secili_oda")

    kayit = kayitlar_bugun.get(secili_oda)
    with st.form("temizlik_form", clear_on_submit=False):
        temizlendi = st.checkbox("Temizlendi", value=bool(kayit), key="temizlik_tik")
        personel_adi = st.text_input("Kim temizledi?", value=(kayit or {}).get("personel_adi") or "", key="temizlik_personel")
        if st.form_submit_button("Kaydet"):
            if temizlendi:
                db.temizlik_kaydet_oda(secili_oda, tarih_iso, personel_adi)
                st.success(f"{secili_oda} — {secili_tarih.strftime('%d.%m.%Y')} tarihinde temizlendi olarak kaydedildi.")
            st.rerun()

    st.markdown(f"**{secili_oda} — son 7 gün**")
    son_7_gun = [(secili_tarih - timedelta(days=i)).isoformat() for i in range(7)]
    gecmis = db.temizlik_getir_son_gunler(secili_oda, son_7_gun)
    if not gecmis:
        st.caption("Son 7 günde bu alan için kayıt yok.")
    else:
        for g in gecmis:
            g_fmt = datetime.fromisoformat(g["tarih"]).strftime("%d.%m.%Y")
            st.write(f"✓ {g_fmt} — {g.get('personel_adi') or 'isim belirtilmedi'}")

    st.markdown("---")
    st.markdown("**Haftalık Temizlik**")
    hafta_baslangic = secili_tarih - timedelta(days=secili_tarih.weekday())
    hafta_gunleri_iso = [(hafta_baslangic + timedelta(days=i)).isoformat() for i in range(7)]
    ozet_satirlari = []
    for oda in ODALAR:
        gecmis_oda = db.temizlik_getir_son_gunler(oda, hafta_gunleri_iso)
        if gecmis_oda:
            son = gecmis_oda[0]
            ozet_satirlari.append({
                "Alan": oda, "Son Temizlik": datetime.fromisoformat(son["tarih"]).strftime("%d.%m.%Y"),
                "Kim": son.get("personel_adi") or "-",
            })
        else:
            ozet_satirlari.append({"Alan": oda, "Son Temizlik": "Bu hafta temizlenmedi", "Kim": "-"})
    st.dataframe(pd.DataFrame(ozet_satirlari), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# TAMAMLANMIŞ KARGOLAR
# ------------------------------------------------------------------
def sayfa_tamamlanankargolar():
    geri_butonu()
    st.header("Tamamlanmış Kargolar")
    st.caption("'Sevkiyat Planlama' sayfasında 'Kargolaştır' ile tamamlanan gönderilerin dökümü — kargo faturası takibi için.")

    bugun = date.today()
    col1, col2 = st.columns(2)
    with col1:
        yil = st.number_input("Yıl", min_value=2024, max_value=2100, value=bugun.year, step=1, key="tk_yil")
    with col2:
        ay = st.selectbox("Ay", list(range(1, 13)), index=bugun.month - 1,
                           format_func=lambda x: calendar.month_name[x], key="tk_ay")

    kayitlar = db.tamamlanan_kargolar_getir_ay(yil, ay)
    if kayitlar:
        df = pd.DataFrame(kayitlar)[["tarih", "kargo_firmasi", "varis_il", "toplam_tutar", "detay"]]
        df.columns = ["Tarih", "Kargo Firması", "Varış İl", "Toplam Tutar (TL)", "Detay"]
        df["Toplam Tutar (TL)"] = pd.to_numeric(df["Toplam Tutar (TL)"], errors="coerce").fillna(0)
        df.insert(0, "Sil", False)

        edited = st.data_editor(
            df, use_container_width=True, height=450, key="tk_editor",
            disabled=["Tarih", "Kargo Firması", "Varış İl", "Toplam Tutar (TL)", "Detay"],
            column_config={"Sil": st.column_config.CheckboxColumn("Sil")},
        )
        if st.button("🗑 Seçili satırları sil"):
            silinecekler = [kayitlar[i]["id"] for i in edited.index[edited["Sil"]]]
            if not silinecekler:
                st.warning("Silmek için en az bir satırı işaretleyin.")
            else:
                for _id in silinecekler:
                    db.tamamlanan_kargo_sil(_id)
                st.success(f"{len(silinecekler)} kayıt silindi.")
                st.rerun()

        st.markdown("---")
        st.markdown("**Kargo firmasına göre toplam (bu ay):**")
        ozet = df.groupby("Kargo Firması")["Toplam Tutar (TL)"].sum().reset_index()
        cols = st.columns(len(ozet)) if len(ozet) > 0 else []
        for col, (_, row) in zip(cols, ozet.iterrows()):
            with col:
                st.metric(row["Kargo Firması"], f"{row['Toplam Tutar (TL)']:,.2f} TL")
    else:
        st.info(f"{calendar.month_name[ay]} {yil} için henüz kargolaştırılmış gönderi yok.")


# ------------------------------------------------------------------
# STOK TAKİP
# ------------------------------------------------------------------
STOK_CACHE_TTL_SANIYE = 7200  # kaynak ~2 saatte bir güncelleniyor - aynı sıklıkta önbellekle


@st.cache_data(ttl=STOK_CACHE_TTL_SANIYE, show_spinner=False)
def _stok_verisi_cache():
    return stok_utils.stok_verisini_getir()


def sayfa_stoktakip():
    geri_butonu()
    st.header("Stok Takip")
    st.caption(
        "Kamtek'in stok kaynağından beslenen ürün/stok verisi — kaynak yaklaşık 2 saatte bir "
        "güncelleniyor, burada da 2 saatte bir otomatik yenilenir. Hemen görmek için "
        "'Şimdi Güncelle'yi kullanabilirsiniz."
    )

    tab_liste, tab_sayim, tab_excel = st.tabs(["📋 Stok Listesi", "🔢 Stok Sayım", "📥 Excel ile Stok Sayım"])

    with tab_liste:
        _stok_listesi_bolumu()
    with tab_sayim:
        # "Excel ile Stok Sayım"a bir excel yüklendiyse, Stok Sayım ekranı
        # XML yerine HER ZAMAN en son yüklenen o excel'i kaynak olarak
        # kullanır (XML kaynağı sorunlu olduğunda uygulama genelinde tutarlı
        # kalması için).
        en_son_excel = db.excel_stok_sayim_getir_en_son()
        if en_son_excel is not None:
            try:
                urunler, _eslesme = _excel_stok_oku(io.BytesIO(en_son_excel["dosya_icerik"]))
            except Exception as e:
                st.error(f"En son yüklenen excel okunurken hata oluştu: {e}")
                urunler = None
            if urunler is not None:
                tarih_fmt = en_son_excel.get("tarih") or ""
                st.caption(
                    f"📥 Kaynak: {en_son_excel['dosya_adi']} ({tarih_fmt}, {en_son_excel.get('yuklenme_zamani') or ''}) "
                    "— 'Excel ile Stok Sayım' sekmesinden yüklenen en son dosya kullanılıyor."
                )
                _stok_sayim_bolumu(urunler, anahtar_onek="sayim")
        else:
            try:
                with st.spinner("Stok verisi çekiliyor..."):
                    urunler = _stok_verisi_cache()
            except Exception as e:
                st.error(f"Stok verisi alınamadı: {e}")
            else:
                st.caption("Ürünleri fiilen sayıp buraya girin. Yalnızca girdiğiniz sayım tutarları kaydedilir.")
                _stok_sayim_bolumu(urunler, anahtar_onek="sayim")
    with tab_excel:
        _excel_stok_sayim_bolumu()


def _stok_listesi_bolumu():
    col_ara, col_yenile = st.columns([4, 1])
    with col_yenile:
        if st.button("🔄 Şimdi Güncelle", use_container_width=True):
            _stok_verisi_cache.clear()
            st.rerun()

    try:
        with st.spinner("Stok verisi çekiliyor..."):
            urunler = _stok_verisi_cache()
    except Exception as e:
        st.error(f"Stok verisi alınamadı: {e}")
        return

    if not urunler:
        st.info("Stok verisi bulunamadı.")
        return

    df = pd.DataFrame(urunler)
    with col_ara:
        arama = st.text_input("Ürün adı, stok kodu veya marka ara", label_visibility="collapsed",
                               placeholder="Ürün adı, stok kodu veya marka ara...", key="stokliste_arama")
    if arama:
        mask = (
            df["Ürün Adı"].str.contains(arama, case=False, na=False)
            | df["Stok Kodu"].str.contains(arama, case=False, na=False)
            | df["Marka"].str.contains(arama, case=False, na=False)
        )
        df = df[mask]

    st.dataframe(
        df[["Stok Kodu", "Ürün Adı", "Marka", "Kategori", "Fiyat", "Para Birimi", "Stok", "Açıklama"]],
        use_container_width=True, height=600,
    )
    st.caption(f"Toplam {len(df)} ürün gösteriliyor.")


_TR_SESLILER = set("AaEeIıİiOoÖöUuÜü")


def _marka_kisalt(marka):
    """Marka sütununu daraltmak için sadece sessiz harfleri gösterir
    (örn. 'DAHUA' -> 'DH')."""
    if not marka:
        return ""
    sessizler = "".join(c for c in str(marka) if c.isalpha() and c not in _TR_SESLILER)
    return sessizler or str(marka)


def _personel_kisalt(ad_soyad):
    """Personel sütununu daraltmak için baş harfleri gösterir
    (örn. 'Sertaç Özcan' -> 'S.Ö.')."""
    if not ad_soyad:
        return ""
    parcalar = [p for p in str(ad_soyad).split() if p]
    if not parcalar:
        return ""
    return "".join(f"{p[0].upper()}." for p in parcalar)


def _stok_sayim_bolumu(urunler, anahtar_onek="sayim"):
    """Ürün listesini (XML'den ya da yüklenen excel'den) sayım arayüzüne
    dönüştürür. `anahtar_onek` iki farklı sayım akışının (XML / Excel)
    session_state ve widget key'lerinin çakışmamasını sağlar."""
    if not urunler:
        st.info("Stok verisi bulunamadı.")
        return

    girisler_key = f"{anahtar_onek}_girisler"
    editor_key_key = f"{anahtar_onek}_editor_key"
    if girisler_key not in st.session_state:
        st.session_state[girisler_key] = {}  # {urun_adi: {"Sayım":.., "Personel":..}}
    if editor_key_key not in st.session_state:
        st.session_state[editor_key_key] = 0
    girisler = st.session_state[girisler_key]

    df = pd.DataFrame(urunler)
    df["_stok_sayi"] = pd.to_numeric(df["Stok"], errors="coerce").fillna(0)
    df = df.sort_values("_stok_sayi", ascending=False).reset_index(drop=True)

    kategoriler = ["(Tümü)"] + sorted([k for k in df["Kategori"].dropna().unique() if k])

    # Filtreleri tablo başlıklarına bitişik, sütun genişlikleriyle hizalı şekilde yerleştiriyoruz
    # (Streamlit, Excel'deki gibi başlık içi filtre okunu desteklemiyor - buna en yakın görünüm bu).
    # Masaüstünde sütunlarla yan yana duran boş hizalama div'leri, telefonda
    # st.columns alt alta yığıldığında gereksiz boşluk yarattığı için
    # 'sayim-filtre-bosluk' class'ı ile mobilde gizleniyor (bkz. CSS). Arama
    # kutusu ve Kategori de "_arama_kutusu"/"_kategori_kutusu" class'larıyla
    # sarmalanıyor ki mobilde CSS order ile arama kutusu tabloya bitişik,
    # en altta çıksın (masaüstü sırası değişmiyor, order sadece mobilde geçerli).
    fc = st.columns([3, 1, 1.2, 1.3, 1.5])
    with fc[0]:
        with st.container(key=f"{anahtar_onek}_arama_kutusu"):
            arama = st.text_input("Ürün Adı", key=f"{anahtar_onek}_arama", placeholder="🔍 ara...", label_visibility="visible")
    fc[1].markdown("<div class='sayim-filtre-bosluk' style='padding-top:28px;'></div>", unsafe_allow_html=True)
    fc[2].markdown("<div class='sayim-filtre-bosluk' style='padding-top:28px;'></div>", unsafe_allow_html=True)
    with fc[3]:
        with st.container(key=f"{anahtar_onek}_kategori_kutusu"):
            secili_kategori = st.selectbox("Kategori", kategoriler, key=f"{anahtar_onek}_kategori")
    fc[4].markdown("<div class='sayim-filtre-bosluk' style='padding-top:28px;'></div>", unsafe_allow_html=True)

    # "Stok" sütunu kasıtlı olarak GÖSTERİLMİYOR - sayım yapan personel güncel
    # stok miktarını görüp ona göre yazmasın, gerçek sayımı yapsın. Fark
    # hesaplaması için gerçek stok değeri `df` üzerinden arka planda kullanılıyor.
    df_goster = df[["Ürün Adı", "Marka", "Kategori"]].copy()
    if arama:
        df_goster = df_goster[df_goster["Ürün Adı"].str.contains(arama, case=False, na=False)]
    if secili_kategori != "(Tümü)":
        df_goster = df_goster[df_goster["Kategori"] == secili_kategori]

    # Tabloda ARTIK SADECE Ürün Adı + Sayım var - Marka/Personel/Kategori
    # dahil edildiğinde daraltılsalar bile telefon ekranında hafif yatay
    # kaydırma kalıyordu ("hiç kıpırdamasın" istendi). Marka hâlâ arama/
    # kategori filtresinde kullanılıyor, sadece tablo sütunu olarak
    # gösterilmiyor. Personel ataması "Personeli Ata" düğmesinden yapılıyor.
    df_goster["Sayım"] = df_goster["Ürün Adı"].apply(lambda u: girisler.get(u, {}).get("Sayım", ""))
    df_goster = df_goster[["Ürün Adı", "Sayım"]]

    edited = st.data_editor(
        df_goster, use_container_width=True, height=450,
        key=f"stok_sayim_editor_{anahtar_onek}_{st.session_state[editor_key_key]}",
        disabled=["Ürün Adı"], hide_index=True,
        column_config={
            "Ürün Adı": st.column_config.TextColumn("Ürün Adı", width="medium"),
            "Sayım": st.column_config.TextColumn("Sayım", width="small"),
        },
    )

    # Kullanıcının bu görünümde girdiği Sayım değerlerini kalıcı sözlüğe geri
    # yaz. Personel tabloda hiç gösterilmiyor, sadece "Personeli Ata"
    # düğmesinden atanıyor - burada mevcut değeri koru.
    for _, row in edited.iterrows():
        urun = row["Ürün Adı"]
        sayim_deger = row["Sayım"]
        sayim_dolu = str(sayim_deger).strip() not in ("", "nan", "None")
        mevcut_personel = girisler.get(urun, {}).get("Personel", "")
        if sayim_dolu or mevcut_personel:
            girisler[urun] = {"Sayım": sayim_deger, "Personel": mevcut_personel}
        elif urun in girisler:
            del girisler[urun]

    st.markdown("---")
    personeller = db.personel_listele()
    personel_adlari = [p["ad_soyad"] for p in personeller]
    cp1, cp2 = st.columns([3, 1])
    secilen_personel = cp1.selectbox(
        "Sayan personeli seçin — sayım girilmiş tüm satırlara otomatik atanır",
        ["(Seçiniz)"] + personel_adlari, key=f"{anahtar_onek}_personel_secim",
    )
    if cp2.button("👤 Personeli Ata", use_container_width=True, key=f"{anahtar_onek}_personel_ata_btn"):
        if secilen_personel == "(Seçiniz)":
            st.warning("Önce bir personel seçin.")
        else:
            for urun, deger in girisler.items():
                if str(deger.get("Sayım", "")).strip() not in ("", "nan", "None"):
                    deger["Personel"] = secilen_personel
            st.session_state[editor_key_key] += 1
            st.rerun()

    if st.button("✅ Sayımı Tamamla", type="primary", key=f"{anahtar_onek}_tamamla_btn"):
        if not girisler:
            st.warning("Lütfen en az bir ürün için sayım miktarı girin.")
        else:
            stok_haritasi = {row["Ürün Adı"]: row["Stok"] for _, row in df.iterrows()}
            tum_sayilan = []
            fark_sayisi = 0
            personel_ozet_set = set()
            for urun, deger in girisler.items():
                sayim_deger = deger.get("Sayım")
                if str(sayim_deger).strip() in ("", "nan", "None"):
                    continue
                if deger.get("Personel"):
                    personel_ozet_set.add(str(deger["Personel"]))
                try:
                    guncel = float(str(stok_haritasi.get(urun, 0)).replace(",", "."))
                    sayilan_sayi = float(str(sayim_deger).replace(",", "."))
                    fark_deger = str(sayilan_sayi - guncel)
                    if abs(sayilan_sayi - guncel) > 1e-9:
                        fark_sayisi += 1
                except (ValueError, TypeError):
                    fark_deger = ""
                tum_sayilan.append({
                    "urun_adi": urun, "stok_kodu": None,
                    "guncel_stok": stok_haritasi.get(urun), "sayilan": sayim_deger,
                    "fark": fark_deger,
                })
            toplam_sayilan = len(tum_sayilan)
            personel_ozet = ", ".join(personel_ozet_set) if personel_ozet_set else None
            db.stok_sayim_oturumu_kaydet(date.today().isoformat(), personel_ozet, tum_sayilan)
            st.session_state[girisler_key] = {}
            st.session_state[editor_key_key] += 1
            st.success(
                f"Sayım kaydedildi ({toplam_sayilan} ürün sayıldı, {fark_sayisi} tanesinde fark var). "
                f"Depo Sayım Fişleri'ndeki haftalık takvimde de görünecek."
            )
            st.rerun()


def _excel_stok_oku(dosya):
    """Yüklenen bir stok/ürün excel'ini stok_utils ile aynı şekle
    (Ürün Adı/Stok Kodu/Marka/Kategori/Stok) çevirir - esnek sütun eşleştirme
    ile (XML kaynağı sorunlu olduğunda yedek olarak kullanılır)."""
    df = excel_utils.excel_oku(dosya)
    kw = {
        "Ürün Adı": ["URUN ADI", "STOK ADI", "ACIKLAMA"],
        "Stok Kodu": ["STOK KODU", "STOK KOD", "URUN KODU"],
        "Marka": ["MARKA"],
        "Kategori": ["KATEGORI"],
        "Stok": ["STOK MIKTARI", "STOK ADEDI", "GUNCEL STOK", "MEVCUT STOK", "STOK"],
    }
    eslesme = {}
    for alan, kelimeler in kw.items():
        haric = ["KOD"] if alan == "Stok" else None
        eslesme[alan] = excel_utils.bul_sutun(df.columns, kelimeler, haric=haric)

    if eslesme["Ürün Adı"] is None:
        raise ValueError(f"'Ürün Adı' sütunu bulunamadı. Dosyadaki sütunlar: {list(df.columns)}")

    urunler = []
    for _, row in df.iterrows():
        urun_adi = row[eslesme["Ürün Adı"]]
        if pd.isna(urun_adi) or not str(urun_adi).strip():
            continue

        def _al(alan):
            col = eslesme[alan]
            if col is None or pd.isna(row[col]):
                return ""
            return str(row[col]).strip()

        urunler.append({
            "Stok Kodu": _al("Stok Kodu"),
            "Ürün Adı": str(urun_adi).strip(),
            "Marka": _al("Marka"),
            "Kategori": _al("Kategori"),
            "Fiyat": "",
            "Para Birimi": "",
            "Stok": _al("Stok") or "0",
            "Açıklama": "",
        })
    return urunler, eslesme


def _excel_stok_sayim_bolumu():
    st.caption(
        "XML kaynağı sorunlu olduğunda yedek olarak kullanın: bilgisayardan bir stok/ürün excel'i "
        "yükleyin, kalıcı olarak saklanır - telefondan girip aynı günün dosyasıyla sayım yapabilirsiniz."
    )

    secili_tarih = st.date_input("Tarih", value=date.today(), key="excel_stok_tarih")
    tarih_iso = secili_tarih.isoformat()

    if "excel_stok_uploader_key" not in st.session_state:
        st.session_state.excel_stok_uploader_key = 0
    yuklenen = st.file_uploader(
        f"{secili_tarih.strftime('%d.%m.%Y')} için stok excel'i yükleyin", type=["xls", "xlsx"],
        key=f"excel_stok_uploader_{st.session_state.excel_stok_uploader_key}",
    )
    if yuklenen is not None:
        db.excel_stok_sayim_kaydet(tarih_iso, yuklenen.name, yuklenen.getvalue())
        st.session_state.excel_stok_uploader_key += 1
        st.success(f"{yuklenen.name} kaydedildi ({secili_tarih.strftime('%d.%m.%Y')}).")
        st.rerun()

    kayitlar = db.excel_stok_sayim_getir(tarih_iso)
    if not kayitlar:
        st.info(f"{secili_tarih.strftime('%d.%m.%Y')} için henüz excel yüklenmedi.")
        return

    if len(kayitlar) > 1:
        secenekler = [f"{k['dosya_adi']} ({k.get('yuklenme_zamani') or ''})" for k in kayitlar]
        secim = st.selectbox("Bu gün için birden fazla dosya var - hangisi kullanılsın?", secenekler, key="excel_stok_dosya_secim")
        secili_kayit = kayitlar[secenekler.index(secim)]
    else:
        secili_kayit = kayitlar[0]

    c1, c2 = st.columns([4, 1])
    c1.caption(f"📄 Kullanılan dosya: {secili_kayit['dosya_adi']} — {secili_kayit.get('yuklenme_zamani') or ''}")
    if c2.button("🗑 Sil", key=f"excel_stok_sil_{secili_kayit['id']}"):
        db.excel_stok_sayim_sil(secili_kayit["id"])
        st.rerun()

    try:
        urunler, eslesme = _excel_stok_oku(io.BytesIO(secili_kayit["dosya_icerik"]))
    except Exception as e:
        st.error(f"Excel okunurken hata oluştu: {e}")
        return
    eksik = [alan for alan, col in eslesme.items() if col is None and alan != "Fiyat"]
    if eksik:
        st.caption(f"Bu dosyada bulunamayan alanlar boş bırakıldı: {', '.join(eksik)}")

    st.success(f"{len(urunler)} ürün excel'den okundu.")
    _stok_sayim_bolumu(urunler, anahtar_onek=f"excel_sayim_{tarih_iso}")


# ------------------------------------------------------------------
# KARGO FİYAT LİSTESİ
# ------------------------------------------------------------------
def sayfa_fiyatlistesi():
    geri_butonu()
    st.header("Kargo Fiyat Listesi")
    st.caption("Tüm fiyatlar KDV hariçtir (+ KDV).")

    cols = st.columns(len(data.PRICING))
    for col, (kargo, cfg) in zip(cols, data.PRICING.items()):
        with col:
            b64 = _img_b64(cfg["logo"])
            ext = cfg["logo"].rsplit(".", 1)[-1]
            if b64:
                st.markdown(
                    f"""
                    <div style="height:130px; display:flex; align-items:center;
                                justify-content:center; margin-bottom:10px;">
                        <img src="data:image/{ext};base64,{b64}"
                             style="max-height:120px; max-width:100%; object-fit:contain;">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='height:130px; display:flex; align-items:center; "
                    f"justify-content:center;'><b>{kargo}</b></div>",
                    unsafe_allow_html=True,
                )
            tarife_df = pd.DataFrame(cfg["tiers"], columns=["Alt Desi", "Üst Desi", "Tutar (+ KDV)"])
            st.dataframe(tarife_df, use_container_width=True, hide_index=True)
            if cfg["artan_desi"] is not None:
                st.caption(f"Aralık üstü: desi başına +{cfg['artan_desi']} TL (+ KDV)")
            if cfg["iller"] != "ALL":
                st.caption("Sadece şu illere gönderim yapar: " + ", ".join(cfg["iller"]))
            else:
                st.caption("Tüm illere gönderim yapar.")


# ------------------------------------------------------------------
# İNSAN KAYNAKLARI
# ------------------------------------------------------------------
def sayfa_insankaynaklari():
    if st.session_state.rol not in IK_GORME_YETKISI:
        st.error("Bu bölümü görüntüleme yetkiniz yok.")
        geri_butonu()
        return
    geri_butonu()
    st.header("Personel Yönetimi")

    if "ik_alt_sayfa" not in st.session_state:
        st.session_state.ik_alt_sayfa = "personel"

    c1, c2 = st.columns(2)
    with c1:
        with st.container(key="ik_kart_personel"):
            if st.button("👤\n\nPersonel", use_container_width=True):
                st.session_state.ik_alt_sayfa = "personel"
    with c2:
        with st.container(key="ik_kart_puantaj"):
            if st.button("🕒\n\nPuantaj", use_container_width=True):
                st.session_state.ik_alt_sayfa = "puantaj"

    st.markdown("---")
    if st.session_state.ik_alt_sayfa == "personel":
        _personel_bolumu()
    else:
        _puantaj_bolumu()


def _personel_bolumu():
    st.subheader("Personel")
    with st.expander("➕ Yeni personel ekle"):
        ad_soyad = st.text_input("Ad Soyad", key="yeni_p_ad")
        dogum_tarihi = st.date_input("Doğum Tarihi", value=None, key="yeni_p_dogum",
                                      min_value=date(1950, 1, 1), max_value=date.today())
        cinsiyet = st.radio("Cinsiyet", ["Kadın", "Erkek"], key="yeni_p_cinsiyet", horizontal=True)
        telefon = st.text_input("Telefon", key="yeni_p_tel")
        foto = st.file_uploader("Fotoğraf", type=["jpg", "jpeg", "png"], key="yeni_p_foto")
        if st.button("Kaydet", key="yeni_p_kaydet"):
            if not ad_soyad:
                st.warning("Ad soyad girin.")
            else:
                db.personel_ekle(
                    ad_soyad, dogum_tarihi.isoformat() if dogum_tarihi else None,
                    telefon, foto.getvalue() if foto else None, cinsiyet,
                )
                st.success(f"{ad_soyad} eklendi.")
                st.rerun()

    personeller = db.personel_listele()
    if not personeller:
        st.info("Henüz personel eklenmedi.")
        return

    cols = st.columns(4)
    for i, p in enumerate(personeller):
        with cols[i % 4]:
            if p.get("foto_bytes"):
                b64 = base64.b64encode(p["foto_bytes"]).decode()
                st.markdown(
                    f"<div style='width:110px;height:110px;border-radius:50%;overflow:hidden;"
                    f"margin:0 auto;'><img src='data:image/png;base64,{b64}' "
                    f"style='width:100%;height:100%;object-fit:cover;'></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='width:110px;height:110px;border-radius:50%;background:#E6F1FB;"
                    "display:flex;align-items:center;justify-content:center;margin:0 auto;"
                    "font-size:32px;color:#0C447C;'>👤</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"<p style='text-align:center;font-weight:600;margin-top:6px;'>{p['ad_soyad']}</p>", unsafe_allow_html=True)
            dogum_str = "-"
            if p.get("dogum_tarihi"):
                try:
                    dogum_str = datetime.fromisoformat(p["dogum_tarihi"]).strftime("%d.%m.%Y")
                except Exception:
                    dogum_str = p["dogum_tarihi"]
            st.markdown(
                f"<p style='text-align:center;font-size:12px;color:#666;'>{dogum_str} · {p.get('telefon') or '-'}</p>",
                unsafe_allow_html=True,
            )
            with st.popover("📁 Özlük Sayfası", use_container_width=True):
                _ozluk_sayfasi(p["id"], p["ad_soyad"])
            with st.popover("✏️ Düzenle", use_container_width=True):
                _personel_duzenle_formu(p)
            if st.button("🗑 Sil", key=f"personel_sil_{p['id']}", use_container_width=True):
                db.personel_sil(p["id"])
                st.rerun()


def _personel_duzenle_formu(p):
    yeni_ad = st.text_input("Ad Soyad", value=p["ad_soyad"], key=f"duzenle_ad_{p['id']}")
    mevcut_dogum = None
    if p.get("dogum_tarihi"):
        try:
            mevcut_dogum = datetime.fromisoformat(p["dogum_tarihi"]).date()
        except Exception:
            mevcut_dogum = None
    yeni_dogum = st.date_input("Doğum Tarihi", value=mevcut_dogum, key=f"duzenle_dogum_{p['id']}",
                                min_value=date(1950, 1, 1), max_value=date.today())
    mevcut_cinsiyet = p.get("cinsiyet") or "Kadın"
    yeni_cinsiyet = st.radio("Cinsiyet", ["Kadın", "Erkek"], key=f"duzenle_cinsiyet_{p['id']}",
                              horizontal=True, index=0 if mevcut_cinsiyet == "Kadın" else 1)
    yeni_telefon = st.text_input("Telefon", value=p.get("telefon") or "", key=f"duzenle_tel_{p['id']}")
    yeni_foto = st.file_uploader("Fotoğrafı değiştir (opsiyonel)", type=["jpg", "jpeg", "png"], key=f"duzenle_foto_{p['id']}")
    if st.button("Güncelle", key=f"duzenle_kaydet_{p['id']}"):
        db.personel_guncelle(
            p["id"], yeni_ad, yeni_dogum.isoformat() if yeni_dogum else None,
            yeni_telefon, yeni_cinsiyet, yeni_foto.getvalue() if yeni_foto else None,
        )
        st.success("Güncellendi.")
        st.rerun()


def _ozluk_sayfasi(personel_id, ad_soyad):
    st.markdown(f"**{ad_soyad} — Özlük Sayfası**")
    belge_turu = st.selectbox(
        "Belge türü", ["Sağlık Raporu", "Sicil Kaydı Raporu", "İzin Raporu", "Diğer"],
        key=f"belge_turu_{personel_id}",
    )
    dosya = st.file_uploader("Belge yükle", key=f"belge_dosya_{personel_id}")
    if dosya is not None and st.button("Yükle", key=f"belge_yukle_{personel_id}"):
        db.ozluk_belgesi_ekle(personel_id, belge_turu, dosya.name, dosya.getvalue())
        st.success("Belge yüklendi.")
        st.rerun()

    belgeler = db.ozluk_belgeleri_getir(personel_id)
    if not belgeler:
        st.caption("Henüz belge yüklenmedi.")
    for b in belgeler:
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.caption(f"{b['belge_turu']}")
        c2.download_button("⬇", data=b["dosya_icerik"], file_name=b["dosya_adi"], key=f"belge_indir_{b['id']}")
        if c3.button("🗑", key=f"belge_sil_{b['id']}"):
            db.ozluk_belgesi_sil(b["id"])
            st.rerun()


GUN_ISIMLERI_KISA = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def _calisma_dakika_hesapla(giris, cikis, tarih_iso):
    """Giriş/çıkış saatlerinden, hafta içi ise 1 saatlik öğle molası düşülerek
    net çalışma süresini (dakika) hesaplar."""
    try:
        g = datetime.strptime(giris, "%H:%M")
        c = datetime.strptime(cikis, "%H:%M")
    except (ValueError, TypeError):
        return None
    fark_dk = int((c - g).total_seconds() // 60)
    if fark_dk <= 0:
        return None
    gun_no = datetime.fromisoformat(tarih_iso).weekday()  # 0=Pazartesi ... 5=Cumartesi, 6=Pazar
    if gun_no <= 4:  # hafta içi - öğle molası düş
        fark_dk = max(0, fark_dk - 60)
    return fark_dk


def _puantaj_bolumu():
    st.subheader("Puantaj")
    personeller = db.personel_listele()
    if not personeller:
        st.info("Puantaj tutabilmek için önce Personel bölümünden personel eklemelisiniz.")
        return

    secili_tarih = st.date_input("Tarih", value=date.today(), key="puantaj_tarih")
    tarih_iso = secili_tarih.isoformat()
    if data.is_resmi_tatil(tarih_iso):
        st.info(f"📅 {data.resmi_tatil_adi(tarih_iso)} — resmi tatil.")

    mevcut = db.puantaj_getir_gun(tarih_iso)
    for p in personeller:
        kayit = mevcut.get(p["id"], {})
        c1, c2, c3, c4, c5 = st.columns([1.6, 1, 1, 1, 1.6])
        c1.write(p["ad_soyad"])
        giris = c2.text_input("Giriş", value=kayit.get("giris_saati") or "", key=f"giris_{p['id']}_{tarih_iso}", placeholder="09:30")
        cikis = c3.text_input("Çıkış", value=kayit.get("cikis_saati") or "", key=f"cikis_{p['id']}_{tarih_iso}", placeholder="18:30")
        ek_mesai = c4.text_input("Ek Mesai (saat)", value=kayit.get("ek_mesai_saat") or "", key=f"ekmesai_{p['id']}_{tarih_iso}", placeholder="0")
        sebep = c5.text_input("Sebebi", value=kayit.get("sebep") or "", key=f"sebep_{p['id']}_{tarih_iso}")

        degisti = (
            giris != (kayit.get("giris_saati") or "") or cikis != (kayit.get("cikis_saati") or "")
            or ek_mesai != (kayit.get("ek_mesai_saat") or "") or sebep != (kayit.get("sebep") or "")
        )
        if degisti and (giris or cikis or ek_mesai or sebep):
            db.puantaj_kaydet(tarih_iso, p["id"], giris, cikis, ek_mesai, sebep)

    st.caption("Hafta içi günlerde 1 saatlik öğle molası, çalışma süresinden otomatik düşülür. Ek Mesai manuel girilir.")

    st.markdown("---")
    st.markdown("**Aylık görünüm**")
    col1, col2 = st.columns(2)
    yil = col1.number_input("Yıl", min_value=2024, max_value=2100, value=secili_tarih.year, key="puantaj_yil")
    ay = col2.selectbox("Ay", list(range(1, 13)), index=secili_tarih.month - 1,
                         format_func=lambda x: calendar.month_name[x], key="puantaj_ay")

    kayitlar_ay = db.puantaj_getir_ay(yil, ay)
    kayit_haritasi = {}
    for k in kayitlar_ay:
        kayit_haritasi.setdefault(k["tarih"], {})[k["personel_id"]] = k

    gun_sayisi = calendar.monthrange(yil, ay)[1]
    gun_renkleri = {5: "#EAF3DE", 6: "#FCEBEB"}  # Cumartesi yeşilimsi, Pazar somon

    satirlar_html = []
    for gun_no in range(1, gun_sayisi + 1):
        d = date(yil, ay, gun_no)
        d_iso = d.isoformat()
        haftanin_gunu = d.weekday()
        renk = gun_renkleri.get(haftanin_gunu, "#FFFFFF" if haftanin_gunu <= 4 else "#FFFFFF")
        hucre = f"<td style='padding:4px 8px;border:1px solid #ddd;white-space:nowrap;background:{renk}'>{d.strftime('%d.%m.%Y')}<br><span style='font-size:11px;color:#555'>{GUN_ISIMLERI_KISA[haftanin_gunu]}</span></td>"
        for p in personeller:
            k = kayit_haritasi.get(d_iso, {}).get(p["id"], {})
            g = k.get("giris_saati") or ""
            c = k.get("cikis_saati") or ""
            em = k.get("ek_mesai_saat") or ""
            sb = k.get("sebep") or ""
            hucre += (
                f"<td style='padding:4px 8px;border:1px solid #ddd;background:{renk}'>{g}</td>"
                f"<td style='padding:4px 8px;border:1px solid #ddd;background:{renk}'>{c}</td>"
                f"<td style='padding:4px 8px;border:1px solid #ddd;background:{renk}'>{em}</td>"
                f"<td style='padding:4px 8px;border:1px solid #ddd;background:{renk}'>{sb}</td>"
            )
        satirlar_html.append(f"<tr>{hucre}</tr>")

    baslik_ust = "<th style='padding:4px 8px;border:1px solid #ddd;background:#f5f5f5'>Tarih</th>"
    for p in personeller:
        baslik_ust += f"<th colspan='4' style='padding:4px 8px;border:1px solid #ddd;background:#378ADD;color:white;text-align:center'>{p['ad_soyad']}</th>"
    baslik_alt = "<th style='border:1px solid #ddd;background:#f5f5f5'></th>"
    for _ in personeller:
        baslik_alt += (
            "<th style='padding:4px 8px;border:1px solid #ddd;background:#E6F1FB;font-size:11px'>Giriş</th>"
            "<th style='padding:4px 8px;border:1px solid #ddd;background:#E6F1FB;font-size:11px'>Çıkış</th>"
            "<th style='padding:4px 8px;border:1px solid #ddd;background:#E6F1FB;font-size:11px'>Ek Mesai</th>"
            "<th style='padding:4px 8px;border:1px solid #ddd;background:#E6F1FB;font-size:11px'>Sebebi</th>"
        )

    tablo_html = (
        "<div style='overflow-x:auto'><table style='border-collapse:collapse;font-size:13px;width:100%'>"
        f"<thead><tr>{baslik_ust}</tr><tr>{baslik_alt}</tr></thead>"
        f"<tbody>{''.join(satirlar_html)}</tbody></table></div>"
    )
    st.markdown(tablo_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Aylık toplam**")
    personel_haritasi = {p["id"]: p["ad_soyad"] for p in personeller}
    toplamlar = {}
    for k in kayitlar_ay:
        net_dk = _calisma_dakika_hesapla(k.get("giris_saati"), k.get("cikis_saati"), k["tarih"])
        try:
            ek_dk = int(round(float(str(k.get("ek_mesai_saat") or 0).replace(",", ".")) * 60))
        except (ValueError, TypeError):
            ek_dk = 0
        ad = personel_haritasi.get(k["personel_id"], "?")
        toplam_dk, ekmesai_dk = toplamlar.get(ad, (0, 0))
        if net_dk:
            toplam_dk += net_dk
        ekmesai_dk += ek_dk
        toplamlar[ad] = (toplam_dk, ekmesai_dk)

    if not toplamlar:
        st.caption("Bu ay için kayıt yok.")
    else:
        cols = st.columns(min(4, len(toplamlar)))
        for i, (ad, (toplam_dk, ekmesai_dk)) in enumerate(toplamlar.items()):
            with cols[i % len(cols)]:
                st.metric(ad, f"{toplam_dk // 60}s {toplam_dk % 60}d", f"{ekmesai_dk // 60}s {ekmesai_dk % 60}d ek mesai")


# ------------------------------------------------------------------
# İADE
# ------------------------------------------------------------------
def _iade_bos_urun_df():
    return pd.DataFrame({"Ürün Adı": [""] * 5, "Adet": [""] * 5, "Seri Numaraları": [""] * 5})


def _iade_karti(iade):
    durum = iade.get("durum", "Bekliyor")
    yerlestirildi = bool(iade.get("yerlestirildi"))
    tarih_str = iade.get("tarih") or ""

    if durum == "Kabul Edildi":
        bg, fg = "#EAF3DE", "#27500A"
        durum_etiket = "Kabul Edildi"
    else:
        # Bekliyor durumundaki iade, girildiği tarihten geçen süreye göre
        # renklendirilir - personelin gözünden kaçmasın diye.
        gun_farki = None
        if tarih_str:
            try:
                gun_farki = (date.today() - date.fromisoformat(tarih_str)).days
            except ValueError:
                gun_farki = None
        if gun_farki is not None and gun_farki >= 21:
            bg, fg = "#FCEBEB", "#791F1F"
        elif gun_farki is not None and gun_farki >= 7:
            bg, fg = "#E6F1FB", "#0C447C"
        else:
            bg, fg = "#FAEEDA", "#854F0B"
        durum_etiket = "Bekliyor"

    baslik = f"{iade['firma_adi']} — {iade['urun_adi']} ({iade.get('adet') or '?'} adet) — {tarih_str}"
    guvenli_baslik = html.escape(baslik)
    cizgi = (
        "text-decoration:line-through;text-decoration-color:#111111;text-decoration-thickness:2px;"
        if yerlestirildi else ""
    )
    st.markdown(
        f"<div style='background:{bg};color:{fg};padding:12px 14px;border-radius:10px;"
        f"font-weight:600;margin-bottom:6px;{cizgi}'>{guvenli_baslik}"
        f"<div style='font-size:11px;font-weight:500;text-decoration:none;margin-top:4px;'>"
        f"{durum_etiket}{' · 📍 Yerleştirildi' if yerlestirildi else ''}</div></div>",
        unsafe_allow_html=True,
    )

    seriler = [s.strip() for s in (iade.get("seri_numaralari") or "").splitlines() if s.strip()]
    if seriler:
        st.caption("Seri numaraları: " + ", ".join(seriler))

    c1, c2, c3 = st.columns(3)
    if durum != "Kabul Edildi":
        if c1.button("✓ Kabul Edildi", key=f"iade_kabul_{iade['id']}", use_container_width=True):
            db.iade_durum_guncelle(iade["id"], "Kabul Edildi")
            st.rerun()
    else:
        if c1.button("↺ Bekliyor'a al", key=f"iade_bekliyor_{iade['id']}", use_container_width=True):
            db.iade_durum_guncelle(iade["id"], "Bekliyor")
            st.rerun()

    if not yerlestirildi:
        if c2.button("📍 Yerleştirildi", key=f"iade_yerlestir_{iade['id']}", use_container_width=True):
            db.iade_yerlestirildi_guncelle(iade["id"], True)
            st.rerun()
    else:
        if c2.button("↺ Yerleştirmeyi geri al", key=f"iade_yerlestir_geri_{iade['id']}", use_container_width=True):
            db.iade_yerlestirildi_guncelle(iade["id"], False)
            st.rerun()

    if c3.button("🗑 Sil", key=f"iade_sil_{iade['id']}", use_container_width=True):
        db.iade_sil(iade["id"])
        st.rerun()

    st.markdown("---")


@st.cache_data(ttl=60, show_spinner=False)
def _aktif_stok_urun_adlari():
    """İade'deki ürün arama filtresi için ürün adı listesi - Stok Sayım'ın
    kullandığı kaynakla birebir aynı (varsa en son yüklenen excel, yoksa XML)."""
    en_son_excel = db.excel_stok_sayim_getir_en_son()
    if en_son_excel is not None:
        try:
            urunler, _eslesme = _excel_stok_oku(io.BytesIO(en_son_excel["dosya_icerik"]))
        except Exception:
            urunler = []
    else:
        try:
            urunler = _stok_verisi_cache()
        except Exception:
            urunler = []
    return sorted({u["Ürün Adı"] for u in urunler if u.get("Ürün Adı")})


def sayfa_iade():
    geri_butonu()
    st.header("İade")
    st.caption("Firmalardan gelen iadeler faturası kabul edilene kadar burada takip edilir.")

    with st.expander("➕ Yeni iade ekle"):
        firma = st.text_input("Firma / Müşteri Adı", key="iade_firma")
        tarih_g = st.date_input("Tarih", value=date.today(), key="iade_tarih")
        st.caption("Aynı firmadan birden fazla ürün iade ediliyorsa hepsini aşağıdaki tabloya ekleyin.")
        if "iade_urun_df" not in st.session_state:
            st.session_state.iade_urun_df = _iade_bos_urun_df()

        c_ara, c_ara_ekle = st.columns([4, 1])
        secilen_urun = c_ara.selectbox(
            "Ürün ara ve seç", [""] + _aktif_stok_urun_adlari(), key="iade_urun_arama_secim",
            format_func=lambda v: "🔍 ürün ara..." if v == "" else v,
        )
        if c_ara_ekle.button("➕ Ekle", key="iade_urun_arama_ekle_btn", use_container_width=True):
            if not secilen_urun:
                st.warning("Önce listeden bir ürün seçin.")
            else:
                mevcut = st.session_state.iade_urun_df
                bos_maske = mevcut["Ürün Adı"].astype(str).str.strip() == ""
                if bos_maske.any():
                    mevcut.loc[bos_maske.idxmax(), "Ürün Adı"] = secilen_urun
                else:
                    yeni_satir = pd.DataFrame([{"Ürün Adı": secilen_urun, "Adet": "", "Seri Numaraları": ""}])
                    st.session_state.iade_urun_df = pd.concat([mevcut, yeni_satir], ignore_index=True)
                st.rerun()

        # Yanlışlıkla eklenen satırları kolayca çıkarabilmek için "Sil" onay
        # kutusu sütunu ekleniyor (Tamamlanmış Kargolar sayfasındaki aynı desen).
        df_duzenle = st.session_state.iade_urun_df.copy()
        df_duzenle.insert(0, "Sil", False)
        urun_df_duzenlenmis = st.data_editor(
            df_duzenle, num_rows="dynamic", use_container_width=True,
            key="iade_urun_editor", height=220,
            column_config={
                "Sil": st.column_config.CheckboxColumn("Sil"),
                "Seri Numaraları": st.column_config.TextColumn("Seri Numaraları (virgülle ayırın)"),
            },
        )
        if st.button("🗑 Seçili satırları sil", key="iade_urun_satir_sil_btn"):
            if not urun_df_duzenlenmis["Sil"].any():
                st.warning("Silmek için en az bir satırı işaretleyin.")
            else:
                st.session_state.iade_urun_df = (
                    urun_df_duzenlenmis[~urun_df_duzenlenmis["Sil"]].drop(columns=["Sil"]).reset_index(drop=True)
                )
                st.rerun()

        urun_df = urun_df_duzenlenmis.drop(columns=["Sil"])
        if st.button("Ekle", key="iade_ekle_btn"):
            satirlar = [
                row for _, row in urun_df.iterrows()
                if str(row["Ürün Adı"]).strip() not in ("", "nan", "None")
            ]
            if not firma or not satirlar:
                st.warning("Firma adı ve en az bir ürün satırı girin.")
            else:
                for row in satirlar:
                    seri_ham = str(row["Seri Numaraları"]) if str(row["Seri Numaraları"]) not in ("nan", "None") else ""
                    seri_coklu_satir = "\n".join(s.strip() for s in seri_ham.split(",") if s.strip())
                    db.iade_ekle(firma, row["Ürün Adı"], seri_coklu_satir, row["Adet"], tarih_g.isoformat())
                st.success(f"{firma} için {len(satirlar)} ürün eklendi.")
                st.session_state.iade_urun_df = _iade_bos_urun_df()
                st.rerun()

    iadeler = db.iadeler_getir()
    if not iadeler:
        st.info("Henüz iade kaydı yok.")
        return

    for iade in iadeler:
        _iade_karti(iade)


# ------------------------------------------------------------------
# PLANLAMA
# ------------------------------------------------------------------
def sayfa_planlama():
    geri_butonu()
    st.header("Planlama")
    _planlama_gorevler_bolumu()


def _planlama_gorevler_bolumu():
    secili_tarih = st.date_input("Tarih", value=date.today(), key="planlama_tarih")
    tarih_iso = secili_tarih.isoformat()

    with st.form("yeni_gorev_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 3])
        saat = c1.text_input("Saat", placeholder="09:00")
        aciklama = c2.text_input("İş açıklaması")
        if st.form_submit_button("➕ Ekle") and aciklama:
            db.gorev_ekle(tarih_iso, saat, aciklama)
            st.rerun()

    gorevler = db.gorevler_getir_gun(tarih_iso)
    if not gorevler:
        st.info(f"{secili_tarih.strftime('%d.%m.%Y')} için henüz iş eklenmedi.")
    for g in gorevler:
        c1, c2, c3 = st.columns([0.5, 4, 0.5])
        tik = c1.checkbox("", value=g.get("tamamlandi", False), key=f"gorev_tik_{g['id']}")
        if tik != g.get("tamamlandi", False):
            db.gorev_tamamla(g["id"], tik)
            st.rerun()
        etiket = f"{g.get('saat') or ''} — {g['aciklama']}"
        if g.get("tamamlandi"):
            c2.markdown(f"<span style='text-decoration:line-through;color:#888;'>{etiket}</span>", unsafe_allow_html=True)
        else:
            c2.write(etiket)
        if c3.button("🗑", key=f"gorev_sil_{g['id']}"):
            db.gorev_sil(g["id"])
            st.rerun()

    st.markdown("---")
    st.markdown("**Aylık döküm**")
    col1, col2 = st.columns(2)
    yil = col1.number_input("Yıl", min_value=2024, max_value=2100, value=secili_tarih.year, key="planlama_yil")
    ay = col2.selectbox("Ay", list(range(1, 13)), index=secili_tarih.month - 1,
                         format_func=lambda x: calendar.month_name[x], key="planlama_ay")
    gorevler_ay = db.gorevler_getir_ay(yil, ay)
    gun_bazinda = {}
    for g in gorevler_ay:
        if g.get("tamamlandi"):
            gun_bazinda.setdefault(g["tarih"], []).append(g["aciklama"])
    if not gun_bazinda:
        st.caption("Bu ay tamamlanmış iş yok.")
    else:
        for gun in sorted(gun_bazinda.keys()):
            gun_fmt = datetime.fromisoformat(gun).strftime("%d.%m.%Y")
            st.markdown(f"**{gun_fmt}**: " + ", ".join(gun_bazinda[gun]))


def _transfer_bos_sepet_df():
    return pd.DataFrame({"Ürün Adı": [], "Stok Kodu": [], "İstenen Adet": []})


def sayfa_depotransfer():
    geri_butonu()
    st.header("Depolar Arası Transfer")
    st.caption("Giriş Katı personeli, Alsancak deposundan istediği ürünler için burada bir talep açar.")
    c1, c2 = st.columns(2)
    talep_eden = c1.selectbox("Talep eden depo", ["Giriş Katı", "Alsancak"], key="transfer_talep_eden")
    hedef = c2.selectbox("Hedef depo (ürünün geleceği yer)", ["Alsancak", "Giriş Katı"], key="transfer_hedef")
    ne_zaman = st.text_input("Ne zaman gelmesini istiyorsunuz? (açıklama)", placeholder="Örn. bugün öğleden sonra", key="transfer_ne_zaman")

    try:
        with st.spinner("Stok verisi çekiliyor..."):
            urunler = _stok_verisi_cache()
    except Exception as e:
        st.error(f"Stok verisi alınamadı: {e}")
        return

    if not urunler:
        st.info("Stok verisi bulunamadı.")
        return

    df = pd.DataFrame(urunler)
    df["_stok_sayi"] = pd.to_numeric(df["Stok"], errors="coerce").fillna(0)
    df = df.sort_values("_stok_sayi", ascending=False).reset_index(drop=True)
    stok_kodu_map = dict(zip(df["Ürün Adı"], df["Stok Kodu"]))

    if "transfer_sepet_df" not in st.session_state:
        st.session_state.transfer_sepet_df = _transfer_bos_sepet_df()

    c_ara, c_ara_ekle = st.columns([4, 1])
    secilen_urun = c_ara.selectbox(
        "Ürün ara ve seç", [""] + sorted(df["Ürün Adı"].dropna().unique().tolist()), key="transfer_urun_arama_secim",
        format_func=lambda v: "🔍 ürün ara..." if v == "" else v,
    )
    if c_ara_ekle.button("➕ Ekle", key="transfer_urun_arama_ekle_btn", use_container_width=True):
        if not secilen_urun:
            st.warning("Önce listeden bir ürün seçin.")
        else:
            mevcut = st.session_state.transfer_sepet_df
            if secilen_urun in mevcut["Ürün Adı"].values:
                st.warning("Bu ürün zaten sepette.")
            else:
                yeni_satir = pd.DataFrame([{
                    "Ürün Adı": secilen_urun,
                    "Stok Kodu": stok_kodu_map.get(secilen_urun, ""),
                    "İstenen Adet": "",
                }])
                st.session_state.transfer_sepet_df = pd.concat([mevcut, yeni_satir], ignore_index=True)
            st.rerun()

    df_duzenle = st.session_state.transfer_sepet_df.copy()
    df_duzenle.insert(0, "Sil", False)
    sepet_duzenlenmis = st.data_editor(
        df_duzenle, use_container_width=True, height=280, key="transfer_sepet_editor",
        disabled=["Ürün Adı", "Stok Kodu"], hide_index=True,
        column_config={"Sil": st.column_config.CheckboxColumn("Sil")},
    )
    if st.button("🗑 Seçili satırları sil", key="transfer_sepet_satir_sil_btn"):
        if not sepet_duzenlenmis["Sil"].any():
            st.warning("Silmek için en az bir satırı işaretleyin.")
        else:
            st.session_state.transfer_sepet_df = (
                sepet_duzenlenmis[~sepet_duzenlenmis["Sil"]].drop(columns=["Sil"]).reset_index(drop=True)
            )
            st.rerun()

    sepet_df = sepet_duzenlenmis.drop(columns=["Sil"])
    st.session_state.transfer_sepet_df = sepet_df

    if st.button("📣 Çağır", type="primary"):
        secili_satirlar = sepet_df[sepet_df["İstenen Adet"].apply(lambda v: str(v).strip() not in ("", "nan", "None"))]
        if secili_satirlar.empty:
            st.warning("Lütfen en az bir ürün için istenen adet girin.")
        else:
            for _, row in secili_satirlar.iterrows():
                db.transfer_talebi_ekle(talep_eden, hedef, row["Ürün Adı"], row["İstenen Adet"], ne_zaman)
            st.success(f"{len(secili_satirlar)} ürün için talep oluşturuldu, Bildirim ekranına düştü.")
            st.session_state.transfer_sepet_df = _transfer_bos_sepet_df()
            st.rerun()

    st.markdown("---")
    st.markdown("**Bekleyen talepler**")
    talepler = db.transfer_talepleri_getir("Bekliyor")
    if not talepler:
        st.caption("Bekleyen talep yok.")
    for t in talepler:
        with st.expander(f"{t['talep_eden_depo']} → {t['hedef_depo']}: {t['urun_aciklama']} ({t.get('adet') or '?'} adet)"):
            if t.get("istenen_zaman_aciklama"):
                st.write(f"Not: {t['istenen_zaman_aciklama']}")
            c1, c2 = st.columns(2)
            if c1.button("✓ Ayarlandı", key=f"transfer_tamam_{t['id']}"):
                db.transfer_talebi_durum_guncelle(t["id"], "Tamamlandı")
                st.rerun()
            if c2.button("🗑 Sil", key=f"transfer_sil_{t['id']}"):
                db.transfer_talebi_sil(t["id"])
                st.rerun()


# ------------------------------------------------------------------
# BİLDİRİM
# ------------------------------------------------------------------
def _bildirim_satiri(tip, anahtar, metin, renk, okunmus, bugun_iso):
    """Bir bildirim satırını çizer. Okunmuşsa listeden KALDIRILMAZ — üzeri
    silik bir çizgiyle işaretlenir ama metin okunabilir kalır."""
    okundu = (tip, str(anahtar)) in okunmus
    c1, c2 = st.columns([5, 1])
    if okundu:
        guvenli_metin = html.escape(metin)
        c1.markdown(
            "<div style='padding:0.75rem 1rem;border-radius:0.5rem;background:#F5F5F3;"
            f"color:#8A8A85;text-decoration:line-through;text-decoration-color:#B8B8B4;'>{guvenli_metin}</div>",
            unsafe_allow_html=True,
        )
        c2.caption("✓ Okundu")
    else:
        getattr(c1, renk)(metin)
        if c2.button("✓ Okundu", key=f"bok_{tip}_{anahtar}"):
            db.bildirim_okundu_isaretle(tip, anahtar, bugun_iso)
            _bildirim_verileri.clear()
            st.rerun()


def sayfa_bildirim():
    geri_butonu()
    st.header("Bildirim")

    bugun_iso = date.today().isoformat()
    veri = _bildirim_verileri()
    okunmus = veri["okunmus"]

    gosterildi = False
    if veri["dogumgunler"]:
        st.markdown("**🎂 Bugün doğum günü olanlar**")
        for p in veri["dogumgunler"]:
            _bildirim_satiri("dogumgunu", p["id"], f"🎉 {p['ad_soyad']}'in bugün doğum günü!", "success", okunmus, bugun_iso)
            gosterildi = True

    if veri["gorevler"]:
        st.markdown("**⏰ Zamanı gelen planlanan işler**")
        for g in veri["gorevler"]:
            _bildirim_satiri("gorev", g["id"], f"{g.get('saat') or ''} — {g['aciklama']}", "warning", okunmus, bugun_iso)
            gosterildi = True

    if veri["transferler"]:
        st.markdown("**🔁 Bekleyen depo transfer çağrıları**")
        for t in veri["transferler"]:
            not_metni = f" ({t['istenen_zaman_aciklama']})" if t.get("istenen_zaman_aciklama") else ""
            metin = f"{t['talep_eden_depo']} → {t['hedef_depo']}: {t['urun_aciklama']} ({t.get('adet') or '?'} adet){not_metni}"
            _bildirim_satiri("transfer", t["id"], metin, "info", okunmus, bugun_iso)
            gosterildi = True

    if not gosterildi:
        st.info("Şu an bekleyen bir bildirim yok.")


# ------------------------------------------------------------------
# KONTROL LİSTESİ
# ------------------------------------------------------------------
def sayfa_kontrollistesi():
    geri_butonu()
    st.header("Kontrol Listesi")

    if "kl_secili_gun" not in st.session_state:
        st.session_state.kl_secili_gun = date.today().isoformat()

    col1, col2 = st.columns(2)
    yil = col1.number_input("Yıl", min_value=2024, max_value=2100, value=date.today().year, key="kl_yil")
    ay = col2.selectbox("Ay", list(range(1, 13)), index=date.today().month - 1,
                         format_func=lambda x: calendar.month_name[x], key="kl_ay")

    gun_sayisi = calendar.monthrange(yil, ay)[1]
    ilk_gun_haftasi = date(yil, ay, 1).weekday()  # 0=Pazartesi
    gun_isimleri = ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"]

    baslik_cols = st.columns(7)
    for col, isim in zip(baslik_cols, gun_isimleri):
        col.markdown(f"<div style='text-align:center;font-size:12px;color:#888;'>{isim}</div>", unsafe_allow_html=True)

    tum_maddeler_ay = db.kontrol_listesi_getir_ay(yil, ay)
    gun_sayaci = {}
    for m in tum_maddeler_ay:
        gun_sayaci.setdefault(m["tarih"], {"toplam": 0, "tamam": 0})
        gun_sayaci[m["tarih"]]["toplam"] += 1
        if m.get("tamamlandi"):
            gun_sayaci[m["tarih"]]["tamam"] += 1

    hafta = [None] * ilk_gun_haftasi
    haftalar = []
    for g in range(1, gun_sayisi + 1):
        hafta.append(g)
        if len(hafta) == 7:
            haftalar.append(hafta)
            hafta = []
    if hafta:
        while len(hafta) < 7:
            hafta.append(None)
        haftalar.append(hafta)

    for hafta in haftalar:
        cols = st.columns(7)
        for col, gun_no in zip(cols, hafta):
            if gun_no is None:
                col.write("")
                continue
            gun_iso = date(yil, ay, gun_no).isoformat()
            sayac = gun_sayaci.get(gun_iso)
            etiket = f"{gun_no}"
            if sayac:
                etiket += f"\n{sayac['tamam']}/{sayac['toplam']}"
            secili = gun_iso == st.session_state.kl_secili_gun
            with col:
                with st.container(key=f"kl_gun_kutu_{gun_iso}"):
                    if st.button(etiket, key=f"kl_gun_{gun_iso}", use_container_width=True):
                        st.session_state.kl_secili_gun = gun_iso
                        st.rerun()

    st.markdown("---")
    secili_gun = st.session_state.kl_secili_gun
    secili_gun_fmt = datetime.fromisoformat(secili_gun).strftime("%d.%m.%Y")
    st.markdown(f"**{secili_gun_fmt} kontrol listesi**")

    with st.form("yeni_kontrol_form", clear_on_submit=True):
        madde = st.text_input("Kontrol edilecek iş")
        if st.form_submit_button("➕ Ekle") and madde:
            db.kontrol_maddesi_ekle(secili_gun, madde)
            st.rerun()

    maddeler = db.kontrol_listesi_getir(secili_gun)
    if not maddeler:
        st.info(f"{secili_gun_fmt} için henüz madde eklenmedi.")
    for m in maddeler:
        c1, c2, c3 = st.columns([0.5, 4, 0.5])
        tik = c1.checkbox("", value=m.get("tamamlandi", False), key=f"kl_tik_{m['id']}")
        if tik != m.get("tamamlandi", False):
            db.kontrol_maddesi_tamamla(m["id"], tik)
            st.rerun()
        if m.get("tamamlandi"):
            c2.markdown(f"<span style='text-decoration:line-through;color:#888;'>{m['madde']}</span>", unsafe_allow_html=True)
        else:
            c2.write(m["madde"])
        if c3.button("🗑", key=f"kl_sil_{m['id']}"):
            db.kontrol_maddesi_sil(m["id"])
            st.rerun()


# ------------------------------------------------------------------
# YÖNLENDİRME
# ------------------------------------------------------------------
SAYFALAR = {
    "home": sayfa_home,
    "sevkiyat": sayfa_sevkiyat,
    "kargotakip": sayfa_kargotakip,
    "depo": sayfa_depo,
    "fiyatlistesi": sayfa_fiyatlistesi,
    "tamamlanankargolar": sayfa_tamamlanankargolar,
    "stoktakip": sayfa_stoktakip,
    "insankaynaklari": sayfa_insankaynaklari,
    "iade": sayfa_iade,
    "planlama": sayfa_planlama,
    "bildirim": sayfa_bildirim,
    "kontrollistesi": sayfa_kontrollistesi,
    "depotransfer": sayfa_depotransfer,
}

render_sidebar()
SAYFALAR[st.session_state.sayfa]()
