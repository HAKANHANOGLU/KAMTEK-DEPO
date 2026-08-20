# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import concurrent.futures
import hashlib
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
/* Ana sayfadaki istatistik kutucukları - büyük rakam + etiket, görünmez bir
   buton tüm kartın üzerine bindirilip tıklanabilir hale getiriliyor (rakamın
   kendisi artık ayrı bir HTML elemanı olduğu için büyük/net yazılabiliyor). */
[class*="st-key-kpi_"] {
    position: relative !important;
    background-color: #FFFFFF !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 14px !important;
    padding: 12px 16px !important;
    min-height: 78px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    transition: border-color .15s ease, box-shadow .15s ease;
}
[class*="st-key-kpi_"]:hover {
    border-color: #378ADD !important;
    box-shadow: 0 4px 14px rgba(55, 138, 221, .15) !important;
}
/* Streamlit'in kendi buton metnini (iç <p>/<span>) CSS ile büyütme
   denemeleri güvenilir çalışmadı (Streamlit sürümüne göre farklı iç
   yapı kullanıyor). Bunun yerine ok işaretini KENDİ HTML'imizle
   (.kpi-ok-gorsel) çiziyoruz - bu, bu sayfadaki diğer tüm özel
   sınıflar gibi garanti render oluyor. Gerçek <button> tamamen
   görünmez bırakılıp sadece tıklama alanı olarak altta duruyor. */
[class*="st-key-kpi_"] div[data-testid="stButton"] {
    width: 100% !important;
    margin-top: 4px !important;
}
[class*="st-key-kpi_"] div[data-testid="stButton"] button {
    width: 100% !important;
    height: 34px !important;
    opacity: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    min-height: 0 !important;
}
[class*="st-key-kpi_"][class*="_kucuk_kpi"] div[data-testid="stButton"] button {
    height: 24px !important;
}
.kpi-ok-gorsel {
    color: #C0392B;
    font-weight: 900;
    line-height: 1;
    text-align: center;
    pointer-events: none;
    margin-top: 4px;
    font-size: 44px;
}
[class*="st-key-kpi_bildirim_panel"] .kpi-ok-gorsel { font-size: 48px; }
.kpi-stat-num {
    font-size: 30px; font-weight: 800; color: #2C2C2A; line-height: 1.1;
}
.kpi-stat-label {
    font-size: 14px; font-weight: 600; color: #6B6B66; margin-top: 4px;
}
[class*="st-key-kpi_bildirim_panel"] {
    min-height: 0 !important;
    text-align: center !important;
    align-items: center !important;
}
[class*="st-key-kpi_bildirim_panel"] .kpi-stat-num { font-size: 44px; }
[class*="st-key-kpi_bildirim_panel"] .kpi-stat-label { margin-bottom: 2px; }
/* Bekleyen iade / transfer talebi / bildirim kutucukları - kargo
   kutucuklarının yarısı boyutunda ama içindeki yazı/rakam daha büyük.
   Ok görselinin genişliği (dolayısıyla iç boşluğu) burada %50
   küçültülüyor. Streamlit'in eleman aralarına eklediği boşluk (margin)
   bu küçük kutularda orantısız kaldığı için sıfırlanıyor. */
[class*="st-key-kpi_"][class*="_kucuk_kpi"] {
    padding: 10px 16px !important;
    min-height: 0 !important;
    gap: 10px !important;
}
[class*="st-key-kpi_"][class*="_kucuk_kpi"] div[data-testid="stElementContainer"] {
    margin: 0 !important;
}
[class*="st-key-kpi_"][class*="_kucuk_kpi"] .kpi-stat-num { font-size: 32px; }
[class*="st-key-kpi_"][class*="_kucuk_kpi"] .kpi-stat-label { font-size: 16px; margin-top: 6px; }
[class*="st-key-kpi_"][class*="_kucuk_kpi"] .kpi-ok-gorsel {
    font-size: 26px;
    width: 50%;
    margin-left: auto;
    margin-right: auto;
}
[class*="st-key-kpi_bildirim_panel"][class*="_kucuk_kpi"] .kpi-stat-num { font-size: 32px; }
[class*="st-key-kl_gun_kutu_"] button {
    background-color: #FFFFFF !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 8px !important;
    min-height: 52px !important;
    white-space: pre-line !important;
    font-size: 12px !important;
    padding: 4px !important;
}
[class*="st-key-kl_gun_kutu_"][class*="_yesil"] button {
    background-color: #DCF3E0 !important;
    border-color: #8FD19E !important;
    color: #1F8A3B !important;
    font-weight: 700 !important;
}
/* Kontrol Listesi - yırtılabilir takvim yaprağı görünümü (Genel Bakış ile
   ortak - aynı CSS sınıfları, aynı görünüm, tek kaynak). */
[class*="st-key-kl_leaf_"] {
    position: relative;
    background: linear-gradient(180deg, #FFFFFF 0%, #FDFBF6 100%) !important;
    border: 1px solid #E4E4E0 !important;
    border-radius: 8px 8px 22px 22px !important;
    box-shadow: 0 12px 30px rgba(0,0,0,.12) !important;
    padding: 20px 28px 16px 28px !important;
    max-width: 640px !important;
    margin: 0 auto 8px auto !important;
    text-align: center !important;
    animation: klLeafIn .5s cubic-bezier(.2,.8,.2,1);
}
[class*="st-key-kl_leaf_"]::before {
    content: "";
    position: absolute; top: 0; left: 0; right: 0; height: 16px;
    background-image: radial-gradient(circle at 17px 0, transparent 8px, #F5F5F3 8.5px);
    background-size: 34px 16px;
    background-repeat: repeat-x;
}
[class*="st-key-kl_leaf_"]::after {
    content: "";
    position: absolute; top: 0; right: 0;
    width: 0; height: 0;
    border-style: solid;
    border-width: 0 40px 40px 0;
    border-color: transparent #EDE8DA transparent transparent;
    filter: drop-shadow(-3px 3px 4px rgba(0,0,0,.18));
}
[class*="st-key-kl_leaf_"][class*="_yesil"] {
    background: linear-gradient(180deg, #EAF7EC 0%, #DCF3E0 100%) !important;
    border-color: #8FD19E !important;
}
[class*="st-key-kl_leaf_"][class*="_yesil"]::after {
    border-color: transparent #C9EAD0 transparent transparent !important;
}
.kl-leaf-ay {
    font-size: 15px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
    color: #C0392B; text-align: right; padding-right: 30px; margin-bottom: 4px;
}
[class*="st-key-kl_leaf_"][class*="_yesil"] .kl-leaf-ay { color: #1F8A3B; }
.kl-leaf-gun-no { font-size: 76px; font-weight: 800; color: #2C2C2A; line-height: 1; }
[class*="st-key-kl_leaf_"][class*="_yesil"] .kl-leaf-gun-no { color: #1F8A3B; }
.kl-leaf-gun-adi { font-size: 20px; font-weight: 600; color: #6B6B66; margin-bottom: 10px; }
@keyframes klLeafIn {
    0% { opacity: 0; transform: translateY(44px) rotate(-3deg) scale(.96); }
    60% { opacity: 1; transform: translateY(-4px) rotate(.6deg) scale(1.01); }
    100% { opacity: 1; transform: translateY(0) rotate(0) scale(1); }
}
/* Genel Bakış'taki küçük "dünkü yaprak" varyantı - küçük ama madde listesi
   yine tam olarak görünüyor. */
[class*="st-key-kl_leaf_"][class*="_kucuk"] {
    max-width: 320px !important;
    padding: 12px 16px 10px 16px !important;
    margin-top: 4px !important;
    opacity: .9;
}
[class*="st-key-kl_leaf_"][class*="_kucuk"] .kl-leaf-gun-no { font-size: 40px; }
[class*="st-key-kl_leaf_"][class*="_kucuk"] .kl-leaf-gun-adi { font-size: 13px; margin-bottom: 6px; }
[class*="st-key-kl_leaf_"][class*="_kucuk"] .kl-leaf-ay { font-size: 11px; padding-right: 16px; }
/* Yaprak içindeki madde satırları (checkbox + metin + sil) Streamlit'in
   varsayılan eleman aralarıyla gereksiz yer kaplıyordu - sıkıştırıyoruz. */
[class*="st-key-kl_leaf_"] div[data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}
[class*="st-key-kl_leaf_"] div[data-testid="stHorizontalBlock"] {
    margin-bottom: -6px !important;
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

/* ------------------------------------------------------------------
   Koyu sidebar teması + yeni Genel Bakış tasarımı ("gb-" öneki)
   Kullanıcının onayladığı mockup'taki renk/tipografi değişkenleriyle
   birebir eşleşiyor.
   ------------------------------------------------------------------ */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
:root {
    --gb-bg-sidebar: #122036;
    --gb-bg-sidebar-active: #1B3355;
    --gb-accent: #1E7F72;
    --gb-accent-soft: #E4F1EE;
    --gb-text-dark: #1B2430;
    --gb-text-mid: #5B6472;
    --gb-text-soft: #8A93A0;
    --gb-border: #E7E3DA;
    --gb-warn: #C9862B;
    --gb-warn-soft: #FBF0DF;
    --gb-danger: #C24B3F;
    --gb-danger-soft: #FBEAE7;
    --gb-info: #3E6FA6;
    --gb-info-soft: #E3ECF4;
    --gb-violet: #6E5AA6;
    --gb-violet-soft: #ECE8F5;
}
section[data-testid="stSidebar"] {
    background-color: var(--gb-bg-sidebar) !important;
    border-right: none !important;
}
section[data-testid="stSidebar"] * {
    color: #DCE3EC !important;
}
/* stIconMaterial (sidebar'ı kapatma oku gibi) Streamlit'in kendi ikon
   fontuna (ligature -> glif) ihtiyaç duyuyor - buraya Inter zorlarsak
   "keyboard_double_arrow_left" gibi ligature adı düz metin olarak görünür. */
section[data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]) {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background: transparent !important; border: none !important; padding: 0 !important;
    min-height: 0 !important; box-shadow: none !important;
}
/* Streamlit sidebar içeriğinin üstünde/solunda varsayılan olarak geniş bir
   boşluk bırakıyor (kapatma oku için ayrılan alan + varsayılan yatay
   padding) - logo bloğu aşağı itiliyor, tüm satırlar da gereksiz sağa
   kaymış duruyordu. İkisini de küçülttük - içerik artık kenara yakın. */
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
section[data-testid="stSidebar"] > div {
    padding-top: 0.25rem !important;
    padding-left: 8px !important;
    padding-right: 8px !important;
}
/* GERÇEK sebep buradaydı: canlı sitede DOM'u inceleyince görüldü ki
   "KAMTEK DEPO" üstündeki boşluk padding'ten değil, Streamlit'in kendi
   stSidebarHeader bloğundan geliyordu - içinde biz hiç kullanmadığımız
   st.logo() için ayrılmış boş bir "stLogoSpacer" (32px) VE kapatma oku
   (36px) var, ikisi birlikte + 16px margin-bottom toplam ~76px flow
   yüksekliği kaplıyordu. Boş logo alanını gizleyip başlık bloğunu içeriğe
   göre küçülttük - kapatma oku olduğu gibi kalıyor. */
section[data-testid="stSidebar"] div[data-testid="stLogoSpacer"] {
    display: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
    height: auto !important; min-height: 0 !important; margin-bottom: 2px !important;
    padding: 2px 0 !important; justify-content: flex-end !important;
}
/* DÜZELTME: Kullanıcının bize gönderdiği orijinal mockup dosyasında (
   kamtek-depo-mockup.html) ritim aslında EŞİT değil, KASITLI olarak
   asimetrik: .nav-item'lar arası sadece 2px (margin-bottom:2px), ama
   kategori başlığından ÖNCE 14px (nav-label'ın kendi padding-top'u) -
   yani bir kategorinin maddeleri birbirine yakın dururken, kategoriler
   birbirinden belirgin şekilde ayrılıyor. Önceki "hepsini eşitle" denemem
   bu tasarım kararını yanlışlıkla düzleştirmişti. Taban gap küçültüldü,
   kategori başlığına kendi üst boşluğu (aşağıda margin-top) geri verildi. */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.3rem !important;
}
/* NOT: yukarıdaki "section[data-testid='stSidebar'] *" kuralı !important ile
   TÜM alt elemanları (iç metin p/div'leri dahil) #DCE3EC yapıyor. Sadece
   .gb-logo-alt / .gb-nav-baslik gibi class bazlı kuralların specificity'si
   (0,1,0) bu blanket kuralın (0,1,1) specificity'sinden DÜŞÜK olduğu için
   kaybediyorlardı - alt başlıklar olması gerekenden daha beyaz/soluk
   görünüyordu. Aşağıdaki renk kuralları artık "section[data-testid=...]"
   önekiyle scope'lanıp specificity'yi kasıtlı olarak yükseltiyor. */
.gb-logo-baslik {
    font-family: 'Space Grotesk', sans-serif !important; font-weight: 700; font-size: 20px;
    letter-spacing: .02em; padding: 0;
}
section[data-testid="stSidebar"] .gb-logo-baslik { color: #FFFFFF !important; }
.gb-logo-alt {
    font-size: 11.5px; letter-spacing: .04em;
    text-transform: uppercase; padding-top: 7px; margin: 0;
}
section[data-testid="stSidebar"] .gb-logo-alt { color: #7C8AA0 !important; }
/* Logo bloğunu (KAMTEK DEPO + alt yazı) nav listesinden ayırıp yukarıda
   tutan ayraç. NOT: margin YERİNE padding-top kullanılıyor - Streamlit
   her elemanı kendi sarmalayıcısına (stMarkdownContainer/stElementContainer)
   koyuyor ve bu sarmalayıcılar "auto" yükseklikte olduğu için child'ın
   margin'i sarmalayıcının İÇİNE değil, sarmalayıcıyla birlikte collapse
   olup görsel olarak üstteki elemanla üst üste biniyordu (canlıda DOM
   ölçülerek doğrulandı). Padding asla collapse olmaz, garanti çalışır. */
.gb-sidebar-divider {
    padding-top: 20px; margin: 0;
}
/* DÜZELTME 1: ".gb-nav-baslik:first-of-type" YANLIŞ bir varsayıma dayanıyordu
   - her kategori başlığı Streamlit'te kendi ayrı stElementContainer'ının
   TEK çocuğu olduğu için ":first-of-type" hepsine (3'üne de) eşleşiyordu,
   bu yüzden hiçbiri istenen üst boşluğu almıyordu.
   DÜZELTME 2: margin-top de aynı collapse sorununu yaşıyordu (yukarıdaki
   nota bakın) - kategori başlığı bir önceki maddenin hemen dibinde
   görünüyordu. İkisi de padding-top'a çevrildi. */
.gb-nav-baslik {
    font-size: 12px; text-transform: uppercase; letter-spacing: .08em;
    padding: 18px 0 8px 8px; margin: 0;
}
section[data-testid="stSidebar"] .gb-nav-baslik { color: #5E6C82 !important; }
/* Nav satırları artık gerçek, tıklanabilir bir st.button - önceki
   "görünmez buton üstte" tekniği Streamlit'in kendi stElementContainer'ına
   position:relative vermesi yüzünden tıklamaları hiç yakalamıyordu (buton
   görünür satırın üstünde değil, kendi küçük kutusunun içinde kalıyordu).
   Nokta artık butonun kendi ::before'u - tek DOM elemanı, tıklama garanti. */
[class*="st-key-navrow_"] {
    position: relative; margin: 0;
}
[class*="st-key-navrow_"] div[data-testid="stButton"] button {
    display: flex !important; align-items: center !important; gap: 10px !important;
    width: 100% !important; justify-content: flex-start !important;
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 8px 8px !important; border-radius: 8px !important; min-height: 0 !important;
    font-size: 16px !important; font-weight: 500 !important;
}
/* Etiket metni Streamlit'in kendi iç sarmalayıcısında ortalanıyordu -
   sola yasla ve genişliği içeriğe göre sıkıştır ki flex satırı ortalamasın.
   Renk de BURADA (iç p/div üzerinde) set ediliyor - "section[...] *" blanket
   kuralı doğrudan bu iç elemanı hedeflediği için, sadece butona renk vermek
   yetmiyordu (inheritance, elemanın kendi üzerindeki explicit kurala karşı
   kazanamıyor). font-weight de aynı sebeple burada tekrar zorlanıyor -
   Streamlit'in kendi buton metni CSS'i olduğundan daha kalın gösteriyordu. */
[class*="st-key-navrow_"] div[data-testid="stButton"] button div,
[class*="st-key-navrow_"] div[data-testid="stButton"] button p {
    text-align: left !important; width: auto !important; flex: none !important;
    color: #B7C1D1 !important; font-weight: 500 !important; font-size: 16px !important;
}
[class*="st-key-navrow_"] div[data-testid="stButton"] button::before {
    content: ""; width: 6px; height: 6px; border-radius: 50%; background: #3E4C63;
    flex-shrink: 0; display: inline-block;
}
[class*="st-key-navrow_"] div[data-testid="stButton"] button:hover div,
[class*="st-key-navrow_"] div[data-testid="stButton"] button:hover p {
    color: #FFFFFF !important;
}
[class*="st-key-navrow_"] div[data-testid="stButton"] button:hover {
    background: rgba(255,255,255,0.05) !important;
}
[class*="st-key-navrow_"][class*="_active"] div[data-testid="stButton"] button {
    background: var(--gb-bg-sidebar-active) !important;
}
[class*="st-key-navrow_"][class*="_active"] div[data-testid="stButton"] button div,
[class*="st-key-navrow_"][class*="_active"] div[data-testid="stButton"] button p {
    color: #FFFFFF !important; font-weight: 600 !important;
}
[class*="st-key-navrow_"][class*="_active"] div[data-testid="stButton"] button::before {
    background: var(--gb-accent) !important;
}
[class*="st-key-navrow_"][class*="_active"]::before {
    content: ""; position: absolute; left: 0; top: 6px; bottom: 6px; width: 3px;
    background: var(--gb-accent); border-radius: 2px;
}
.gb-sidebar-foot { padding: 14px 20px 6px 20px; font-size: 12px; color: #5E6C82; }

.gb-header-row { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 22px; }
.gb-eyebrow { color: var(--gb-text-soft); font-size: 12.5px; margin-top: 3px; }
.gb-title { font-family: 'Space Grotesk', sans-serif; font-size: 22px; font-weight: 600; color: var(--gb-text-dark); }
.gb-pill {
    background: #FFFFFF; border: 1px solid var(--gb-border); border-radius: 20px;
    padding: 6px 12px; font-size: 12px; font-weight: 500; color: var(--gb-text-mid); white-space: nowrap;
}
.gb-kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 26px; }
@media (max-width: 900px) { .gb-kpi-row { grid-template-columns: repeat(2, 1fr); } }
.gb-kpi-card {
    background: #FFFFFF; border: 1px solid var(--gb-border); border-left: 3px solid var(--gb-accent);
    border-radius: 10px; padding: 16px 16px 14px 16px;
}
.gb-kpi-card.warn { border-left-color: var(--gb-warn); }
.gb-kpi-card.danger { border-left-color: var(--gb-danger); }
.gb-kpi-label { font-size: 11.5px; color: var(--gb-text-soft); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }
.gb-kpi-num { font-family: 'IBM Plex Mono', monospace; font-size: 26px; font-weight: 600; color: var(--gb-text-dark); line-height: 1; }
.gb-kpi-sub { font-size: 11.5px; color: var(--gb-accent); margin-top: 6px; }
.gb-kpi-sub.warn { color: var(--gb-warn); }
.gb-kpi-sub.danger { color: var(--gb-danger); }
.gb-panel {
    background: #FFFFFF; border: 1px solid var(--gb-border); border-radius: 10px; padding: 18px 20px 8px 20px; margin-bottom: 16px;
}
.gb-panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.gb-panel-title { font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 600; color: var(--gb-text-dark); }
.gb-panel-link { font-size: 12px; color: var(--gb-accent); font-weight: 500; }
.gb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.gb-table th {
    text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .03em; color: var(--gb-text-soft);
    text-transform: uppercase; padding: 8px 6px; border-bottom: 1px solid var(--gb-border);
}
.gb-table td { padding: 11px 6px; border-bottom: 1px solid #F1EFE9; color: var(--gb-text-dark); }
.gb-table tr:last-child td { border-bottom: none; }
.gb-mono { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--gb-text-mid); }
.gb-tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 20px; }
.gb-tag.ok { background: var(--gb-accent-soft); color: var(--gb-accent); }
.gb-tag.warn { background: var(--gb-warn-soft); color: var(--gb-warn); }
.gb-tag.danger { background: var(--gb-danger-soft); color: var(--gb-danger); }
.gb-tag.notr { background: #EEEEEA; color: #5A5A54; }
.gb-kl-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; font-size: 12.5px; border-bottom: 1px solid #F1EFE9; }
.gb-kl-row:last-child { border-bottom: none; }
.gb-kl-check { width: 15px; height: 15px; border-radius: 4px; border: 1.5px solid var(--gb-border); flex-shrink: 0; }
.gb-kl-check.done { background: var(--gb-accent); border-color: var(--gb-accent); }
.gb-kl-row.done .gb-kl-text { color: var(--gb-text-soft); text-decoration: line-through; }
.gb-notif-row { display: flex; gap: 10px; padding: 11px 0; border-bottom: 1px solid #F1EFE9; }
.gb-notif-row:last-child { border-bottom: none; }
.gb-notif-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; background: var(--gb-accent); }
.gb-notif-dot.warn { background: var(--gb-warn); }
.gb-notif-dot.danger { background: var(--gb-danger); }
.gb-notif-text { font-size: 12.5px; color: var(--gb-text-dark); line-height: 1.45; }
.gb-notif-time { font-size: 11px; color: var(--gb-text-soft); margin-top: 2px; }
.stApp, .stMainBlockContainer { background-color: #F5F3EF !important; }
.st-key-kl_home_panel, .st-key-son_sevkiyat_panel {
    background: #FFFFFF; border: 1px solid var(--gb-border); border-radius: 10px; padding: 18px 20px 8px 20px;
}
.st-key-kl_home_panel div[data-testid="stButton"] button,
.st-key-son_sevkiyat_panel div[data-testid="stButton"] button {
    background: none !important; border: none !important; color: var(--gb-accent) !important;
    font-weight: 500 !important; font-size: 12px !important; padding: 6px 0 0 0 !important;
}
/* Son Sevkiyatlar / Bugünkü Kontrol Listesi / Bildirimler panelleri - KPI
   kartlarındaki gibi ince sol renk çizgisi + üstte kırmızı bir bar. */
.gb-panel, .st-key-kl_home_panel, .st-key-son_sevkiyat_panel {
    border-top: 3px solid var(--gb-danger) !important;
    border-left: 3px solid var(--gb-accent) !important;
}
/* Son Sevkiyatlar: görünürde ~5 satır yüksekliğinde, taşan (teslim edilmemiş)
   satırlar kaydırarak görülüyor - başlık satırı kaydırırken üstte sabit kalır. */
.gb-table-scroll { max-height: 268px; overflow-y: auto; }
.gb-table-scroll .gb-table th { position: sticky; top: 0; background: #FFFFFF; }

/* Kargo Takip - DHL/MNG panosundan ilham alan üst şablonlar + özet tablosu */
[class*="st-key-kt_tile_"] div[data-testid="stButton"] button {
    width: 100% !important; border: none !important; border-radius: 8px !important;
    padding: 24px 10px !important; font-weight: 700 !important; font-size: 16px !important;
    min-height: 64px !important;
}
[class*="st-key-kt_tile_"] div[data-testid="stButton"] button div,
[class*="st-key-kt_tile_"] div[data-testid="stButton"] button p {
    font-weight: 700 !important; font-size: 16px !important;
}
.st-key-kt_tile_sec div[data-testid="stButton"] button,
.st-key-kt_tile_sec div[data-testid="stButton"] button div,
.st-key-kt_tile_sec div[data-testid="stButton"] button p {
    background: #C3CE94 !important; color: #33421A !important;
}
.st-key-kt_tile_takip div[data-testid="stButton"] button,
.st-key-kt_tile_takip div[data-testid="stButton"] button div,
.st-key-kt_tile_takip div[data-testid="stButton"] button p {
    background: #93CBA6 !important; color: #163A25 !important;
}
.st-key-kt_tile_rapor div[data-testid="stButton"] button,
.st-key-kt_tile_rapor div[data-testid="stButton"] button div,
.st-key-kt_tile_rapor div[data-testid="stButton"] button p {
    background: #D7DAF0 !important; color: #262C52 !important;
}
.kt-banner {
    background: var(--gb-danger); color: #FFFFFF; border-radius: 8px; padding: 12px 18px;
    display: flex; justify-content: space-between; align-items: center; font-weight: 600;
    margin: 16px 0 14px 0;
}
.kt-banner-pill { background: #FFFFFF; color: var(--gb-danger); padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 13px; }
.kt-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; background: #FFFFFF; border: 1px solid var(--gb-border); border-radius: 10px; padding: 20px; }
@media (max-width: 900px) { .kt-grid { grid-template-columns: repeat(2, 1fr); } }
.kt-box-num { font-size: 28px; font-weight: 800; color: var(--gb-text-dark); }
.kt-box-lbl { font-size: 12px; color: var(--gb-text-mid); margin-top: 2px; }
.kt-box-bar { height: 6px; background: #EEEEEA; border-radius: 4px; margin-top: 8px; overflow: hidden; }
.kt-box-bar-fill { height: 100%; background: var(--gb-accent); }

/* Depo Sayım Fişleri - ERP tarzı (dashboard KPI kartları + panel + tablo
   diliyle aynı görsel dil): başlık, yükleme paneli, KPI şeridi, haftalık
   takvim, blok/bölge matrisi ve son işlemler paneli hepsi
   .gb-panel/.gb-kpi-card diliyle aynı görsel dili kullanıyor. */
.gb-kpi-row-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px; }
.gb-kpi-row-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px; }
@media (max-width: 900px) { .gb-kpi-row-3, .gb-kpi-row-4 { grid-template-columns: repeat(1, 1fr); } }
.gb-kpi-card.info { border-left-color: var(--gb-info); }
.gb-kpi-sub.info { color: var(--gb-info); }
.gb-kpi-card.violet { border-left-color: var(--gb-violet); }
.gb-kpi-sub.violet { color: var(--gb-violet); }
.st-key-ds_yukleme_panel, .st-key-ds_takvim_panel, .st-key-ds_matris_panel,
.st-key-ds_son_islemler_panel, .st-key-ds_rapor_panel {
    background: #FFFFFF !important; border: 1px solid var(--gb-border) !important;
    border-radius: 10px !important; padding: 18px 20px 14px 20px !important; margin-bottom: 16px !important;
}
.st-key-ds_yukleme_panel {
    border: 6px solid var(--gb-accent) !important;
    padding: 8px 14px 6px 14px !important;
}
/* Panel, KPI kartları satırıyla alttan aynı hizada bitsin diye elemanlar
   arası varsayılan boşluk (Streamlit'in dikey blok gap'i), etiketler ve
   yükleme kutusu olabildiğince sıkılaştırıldı. */
.st-key-ds_yukleme_panel .ds-panel-title { margin-bottom: 3px; font-size: 13px; }
.st-key-ds_yukleme_panel [data-testid="stVerticalBlock"] {
    gap: 0.1rem !important;
}
.st-key-ds_yukleme_panel [data-testid="stWidgetLabel"] {
    min-height: 0 !important;
}
.st-key-ds_yukleme_panel [data-testid="stWidgetLabel"] p {
    font-size: 10.5px !important; margin-bottom: 0 !important; line-height: 1.3 !important;
}
.st-key-ds_yukleme_panel [data-testid="stDateInput"] input {
    padding-top: 2px !important; padding-bottom: 2px !important; font-size: 13px !important;
}
.st-key-ds_yukleme_panel [data-testid="stFileUploaderDropzone"],
.st-key-ds_yukleme_panel [data-testid="stFileUploader"] section {
    padding: 2px 8px !important; min-height: 0 !important;
}
.st-key-ds_yukleme_panel [data-testid="baseButton-secondary"] {
    padding: 2px 10px !important; min-height: 0 !important;
}
.st-key-ds_yukleme_panel small {
    font-size: 9.5px !important;
}
/* Matris ve Son İşlemler panelleri aynı st.columns satırında, alt-üst
   hizalı dursun diye - flex satırının varsayılan "stretch" davranışından
   yararlanıp ikisini de %100 yükseklik yapıyoruz, içerik miktarı (13 blok
   satırı vs. birkaç log satırı) farklı olsa bile en uzun olana eşitleniyor. */
div[data-testid="stHorizontalBlock"]:has(.st-key-ds_matris_panel) > div[data-testid="stColumn"] {
    display: flex !important;
}
.st-key-ds_son_islemler_panel, .st-key-ds_matris_panel { height: 100% !important; width: 100%; }
.st-key-ds_matris_panel {
    border-top: 3px solid var(--gb-violet) !important; border-left: 3px solid var(--gb-accent) !important;
}
.ds-panel-title { font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 600; color: var(--gb-text-dark); margin-bottom: 10px; }
.ds-panel-sub { font-size: 12px; color: var(--gb-text-soft); margin-top: -6px; margin-bottom: 14px; }
.ds-gun-baslik { text-align: left; font-size: 12px; font-weight: 600; color: var(--gb-text-mid); }
.ds-gun-tarih { text-align: left; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--gb-text-soft); }
.ds-gun-excel { display: flex; justify-content: flex-start; margin-top: 3px; margin-bottom: 4px; height: 12px; }
.ds-blok-adi { font-size: 13px; color: var(--gb-text-dark); padding-top: 6px; }
/* Haftalık Sayım Takvimi - her gün kendi kartında; kart kenarı o günün
   durumuna göre renkleniyor (ikisi de tamamsa yeşil, biri tamamsa nötr).
   Butonlar rozet gibi soldan hizalı, durumuna göre yeşil/soluk renkleniyor -
   ama gerçek st.button olarak kalıyor, tıklanınca o günün detayı açılıyor. */
[class*="st-key-ds_takvim_kart_"] {
    border: 1.5px solid var(--gb-border); border-radius: 10px; padding: 10px 10px 8px 10px;
}
[class*="st-key-ds_takvim_kart_"][class*="_tam"] {
    border-color: var(--gb-accent); background: #F5F9F8;
}
.ds-takvim-baslik {
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 13px;
    color: var(--gb-text-dark); margin-bottom: 8px;
}
.ds-takvim-baslik .mono { font-size: 11px; font-weight: 500; color: var(--gb-text-soft); }
.st-key-ds_takvim_panel div[data-testid="stButton"] button {
    border: none !important; border-radius: 6px !important; font-size: 11px !important;
    justify-content: flex-start !important; text-align: left !important; padding: 4px 8px !important;
    min-height: 0 !important;
}
.st-key-ds_takvim_panel div[class*="_ok"] div[data-testid="stButton"] button {
    background: #E4F1EE !important; color: var(--gb-accent) !important; font-weight: 600 !important;
}
.st-key-ds_takvim_panel div[class*="_no"] div[data-testid="stButton"] button {
    background: #FAFAF8 !important; color: var(--gb-text-soft) !important;
}
/* Blok satırlarını gerçek bir tablo gibi göstermek için her satırın altına
   ince bir çizgi - Streamlit'in kendi element sarmalayıcısı üzerinden,
   anahtar öneki ile eşleştirilerek (bkz. .st-key-navrow_ deseni). */
[class*="st-key-ds_blokrow_"] {
    border-bottom: 1px solid #F1EFE9 !important; padding-bottom: 2px !important;
}
[class*="st-key-ds_blokrow_"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-ds_blokrow_"] [data-testid="stColumn"] {
    display: flex !important; align-items: center !important;
}
/* Checkbox'ların kendi doğal (soldan başlayan) konumunu değiştirmiyoruz -
   bunun yerine gün başlıklarını (Pzt/tarih/excel ikonu) checkbox'un doğal
   konumuyla aynı hizaya, sola yaslıyoruz. */
.st-key-ds_matris_panel [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    display: flex !important; flex-direction: column !important; align-items: flex-start !important;
}
.st-key-ds_matris_panel [data-testid="stCheckbox"] label [data-testid="stWidgetLabel"] {
    display: none !important; width: 0 !important; height: 0 !important;
}
.ds-log-row { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid #F1EFE9; }
.ds-log-row:last-child { border-bottom: none; }
.ds-log-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; background: var(--gb-accent); }
.ds-log-text { font-size: 12.5px; color: var(--gb-text-dark); line-height: 1.4; }
.ds-log-alt { font-size: 11px; color: var(--gb-text-soft); margin-top: 2px; }
/* Son İşlemler panelinin üstündeki "Haftalık Rapor" kutusu - gerçek bir
   st.button, tıklanınca sayfanın altında rapor tablosu açılıp kapanıyor.
   Son İşlemler paneliyle aynı genişlikte, kendi sütununda üstte duruyor. */
.st-key-ds_rapor_tile {
    background: #FFFFFF !important; border: 6px solid var(--gb-danger) !important;
    border-radius: 10px !important;
    padding: 0 !important; margin-bottom: 16px !important; box-sizing: border-box;
}
.st-key-ds_rapor_tile div[data-testid="stButton"] button {
    width: 100% !important; min-height: 90px !important;
    background: transparent !important; border: none !important; box-shadow: none !important;
    display: flex !important; flex-direction: column !important; align-items: flex-start !important;
    justify-content: center !important; padding: 16px !important; text-align: left !important;
    white-space: pre-line !important;
}
.st-key-ds_rapor_tile div[data-testid="stButton"] button p {
    font-family: 'Space Grotesk', sans-serif !important; font-size: 15px !important; font-weight: 600 !important;
    color: var(--gb-text-dark) !important; white-space: pre-line !important; text-align: left !important;
}

/* Sevkiyat Planlama - Varış İli / Planlanacak Kargolar / Gönderi Hesapla
   panelleri, Depo Sayım Fişleri'ndeki panel diliyle aynı görsel dil. */
.ptitle { font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 600; margin-bottom: 10px; color: var(--gb-text-dark); }
.psub { font-size: 12px; color: var(--gb-text-soft); }
.st-key-sevk_il_panel, .st-key-sevk_plan_panel, .st-key-sevk_hesap_panel {
    background: #FFFFFF !important; border: 1px solid var(--gb-border) !important;
    border-radius: 10px !important; padding: 18px 20px !important; margin-bottom: 16px !important;
}
.st-key-sevk_plan_panel { border-left: 3px solid var(--gb-violet) !important; }
.st-key-sevk_hesap_panel { border-left: 3px solid var(--gb-accent) !important; }
/* Kargo fiyat kartları - en ucuz/seçili olan yeşil dolgulu, diğerleri nötr. */
[class*="st-key-sevk_kargo_kart_"] {
    border: 1px solid var(--gb-border); border-radius: 8px; padding: 12px; margin-bottom: 8px;
}
[class*="st-key-sevk_kargo_kart_"][class*="_secili"] {
    border: 2px solid var(--gb-accent); background: var(--gb-accent-soft);
}
.sevk-rozet {
    display: inline-block; font-size: 9.5px; font-weight: 700; color: #fff; background: var(--gb-accent);
    padding: 2px 7px; border-radius: 10px; margin-bottom: 6px;
}
.sevk-kargo-ad { font-size: 12.5px; font-weight: 600; color: var(--gb-text-dark); }
.sevk-kargo-tutar { font-size: 19px; font-weight: 700; color: var(--gb-text-dark); margin: 6px 0 8px 0; }
[class*="st-key-sevk_kargo_kart_"][class*="_secili"] div[data-testid="stButton"] button {
    background: var(--gb-accent) !important; color: #fff !important; border-color: var(--gb-accent) !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Şifreli giriş (şimdilik tek ortak şifre - rol ayrımı ileride açılacak)
# ------------------------------------------------------------------
def _img_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


SIFRE = st.secrets.get("SITE_SIFRE", "kamtek2026")
ROL_ISIMLERI = {"depo": "Depo Personeli", "patron": "Patron", "gelistirici": "Geliştirici"}
# İK gibi hassas bölümleri görebilecek roller - şimdilik herkes görebiliyor (tek şifre var)
IK_GORME_YETKISI = {"depo", "patron", "gelistirici"}

def _gunluk_oturum_tokeni():
    """Şifreyle birlikte GÜNÜN tarihine bağlı bir belirteç - sayfa yenilendiğinde
    (F5) URL'deki bu belirteç sayesinde tekrar şifre sormuyoruz, ama belirteç
    her gün değiştiği için ertesi sabah / başka bir bilgisayarda yine sorulur."""
    return hashlib.sha256(f"{SIFRE}-{date.today().isoformat()}".encode()).hexdigest()[:20]


if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
if "rol" not in st.session_state:
    st.session_state.rol = None

# Sayfa yenilendiğinde (F5) Streamlit'in session_state'i sıfırlanıyor, ama
# URL'deki query param korunuyor - bu yüzden şifre yerine URL'deki günlük
# belirteci kontrol ediyoruz. Belirteç uyuşuyorsa tekrar şifre sormadan içeri alıyoruz.
if not st.session_state.giris_yapildi and st.query_params.get("g") == _gunluk_oturum_tokeni():
    st.session_state.giris_yapildi = True
    st.session_state.rol = "gelistirici"

if not st.session_state.giris_yapildi:
    _logo_b64 = _img_b64("kamtek_logo.png")
    st.markdown("""
    <style>
    html, body { margin: 0 !important; padding: 0 !important; height: 100% !important; overflow: hidden !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .stApp, [data-testid="stAppViewContainer"] {
        height: 100vh !important; max-height: 100vh !important; overflow: hidden !important;
        padding: 0 !important; margin: 0 !important;
    }
    [data-testid="stAppViewContainer"] > .main {
        height: 100vh !important; padding: 0 !important; margin: 0 !important; overflow: hidden !important;
    }
    .block-container, [data-testid="stMainBlockContainer"] {
        height: 100vh !important; padding: 0 !important; margin: 0 !important; max-width: 100% !important; overflow: hidden !important;
    }
    div[data-testid="stHorizontalBlock"] { gap: 0 !important; height: 100vh !important; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { height: 100vh !important; }
    .giris-marka-baslik { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)
    col_marka, col_form = st.columns([0.75, 1.45])
    with col_marka:
        logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="display:block;height:68px;width:auto;">' if _logo_b64 else '<div class="disp" style="font-size:20px;font-weight:700;color:#122036;">KAMTEK</div>'
        st.markdown(f"""
        <div style="background:#122036;height:100vh;display:flex;flex-direction:column;justify-content:center;padding:0 40px;position:relative;overflow:hidden;">
            <svg style="position:absolute;top:-40px;right:-60px;opacity:.5;" width="260" height="260" viewBox="0 0 24 24" fill="none" stroke="#1B3355" stroke-width="1"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            <div style="background:#fff;border-radius:12px;padding:16px 20px;display:inline-block;margin-bottom:22px;z-index:1;width:fit-content;">
                {logo_html}
            </div>
            <div class="giris-marka-baslik" style="font-family:'Space Grotesk',sans-serif;font-size:52px;font-weight:700;line-height:1.2;z-index:1;">DEPO YÖNETİM<br>PANELİ</div>
            <div style="font-size:13px;color:#7C8AA0;margin-top:10px;z-index:1;">Depo, sevkiyat ve kargo yönetimi<br>tek panelde.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_form:
        st.markdown("<div style='height:18vh;'></div>", unsafe_allow_html=True)
        _, form_orta, _ = st.columns([0.15, 1, 0.15])
        with form_orta:
            st.markdown('<div class="gb-title" style="font-size:20px;">Tekrar hoş geldiniz</div>', unsafe_allow_html=True)
            st.markdown('<div class="gb-eyebrow" style="margin-bottom:22px;">Devam etmek için şifrenizi girin</div>', unsafe_allow_html=True)
            girilen = st.text_input("Şifre", type="password", label_visibility="visible")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                if girilen == SIFRE:
                    st.session_state.giris_yapildi = True
                    st.session_state.rol = "gelistirici"
                    st.query_params["g"] = _gunluk_oturum_tokeni()
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


def _nav_item(anahtar, etiket, hedef_sayfa, aktif=False, rozet=None, depo_alt=None):
    """Mockup'taki .nav-item satırını gerçek bir st.button ile çizer - buton
    doğrudan tıklanabilir (görünmez üst-üste bindirme tekniği Streamlit'in
    kendi element sarmalayıcısı yüzünden çalışmıyordu). Nokta CSS ::before
    ile ekleniyor, aktif satırdaki sol vurgu çubuğu dış container'da."""
    row_key = f"navrow_{anahtar}" + ("_active" if aktif else "")
    etiket_goster = f"{etiket}   🔴{rozet}" if rozet else etiket
    with st.container(key=row_key):
        if st.button(etiket_goster, key=f"nav_{anahtar}", use_container_width=True):
            if depo_alt:
                st.session_state.depo_alt_sayfa = depo_alt
            git(hedef_sayfa)


def render_sidebar():
    with st.sidebar:
        aktif_sayfa = st.session_state.get("sayfa", "home")
        depo_alt = st.session_state.get("depo_alt_sayfa")

        st.markdown("<div class='gb-logo-baslik'>KAMTEK DEPO</div>", unsafe_allow_html=True)
        st.markdown("<div class='gb-logo-alt'>Depo Yönetim Paneli</div>", unsafe_allow_html=True)
        st.markdown("<div class='gb-sidebar-divider'></div>", unsafe_allow_html=True)

        _nav_item("home", "Genel Bakış", "home", aktif=aktif_sayfa == "home")

        st.markdown("<div class='gb-nav-baslik'>Sevkiyat &amp; Kargo</div>", unsafe_allow_html=True)
        _nav_item("sevkiyat", "Sevkiyat Planlama", "sevkiyat", aktif=aktif_sayfa == "sevkiyat")
        _nav_item("kargotakip", "Kargo Takip", "kargotakip", aktif=aktif_sayfa == "kargotakip")
        _nav_item("fiyatlistesi", "Kargo Fiyat Listesi", "fiyatlistesi", aktif=aktif_sayfa == "fiyatlistesi")
        _nav_item("tamamlanankargolar", "Tamamlanmış Kargolar", "tamamlanankargolar", aktif=aktif_sayfa == "tamamlanankargolar")

        st.markdown("<div class='gb-nav-baslik'>Depo &amp; Stok</div>", unsafe_allow_html=True)
        _nav_item("deposayim", "Depo Sayım Fişleri", "depo", aktif=(aktif_sayfa == "depo" and depo_alt == "sayim"), depo_alt="sayim")
        _nav_item("depotemizlik", "Depo Temizlik", "depo", aktif=(aktif_sayfa == "depo" and depo_alt == "temizlik"), depo_alt="temizlik")
        _nav_item("stoktakip", "Stok Takip", "stoktakip", aktif=aktif_sayfa == "stoktakip")
        _nav_item("transfer", "Depolar Arası Transfer", "depotransfer", aktif=aktif_sayfa == "depotransfer")
        _nav_item("iade", "İade", "iade", aktif=aktif_sayfa == "iade")

        st.markdown("<div class='gb-nav-baslik'>Yönetim</div>", unsafe_allow_html=True)
        if st.session_state.rol in IK_GORME_YETKISI:
            _nav_item("ik", "Personel Yönetimi", "insankaynaklari", aktif=aktif_sayfa == "insankaynaklari")
        _nav_item("planlama", "Planlama", "planlama", aktif=aktif_sayfa == "planlama")
        _nav_item("kontrollistesi", "Kontrol Listesi", "kontrollistesi", aktif=aktif_sayfa == "kontrollistesi")
        bildirim_n = _bildirim_sayisi()
        _nav_item("bildirim", "Bildirim", "bildirim", aktif=aktif_sayfa == "bildirim", rozet=bildirim_n if bildirim_n > 0 else None)


_KL_GUN_ISIMLERI_UZUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_KL_AY_ISIMLERI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
                    "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _kl_gun_ozet(gun_iso):
    """Bir günün Kontrol Listesi maddelerini ve tamamlanma durumunu döndürür.

    Genel Bakış'taki takvim yaprakları ile Kontrol Listesi sayfasının kendi
    yaprağı AYNI bu fonksiyonu kullanıyor - iki sayfa da aynı veriye
    bakıyor, birbirinden bağımsız kopya mantık yok."""
    maddeler = db.kontrol_listesi_getir(gun_iso)
    toplam = len(maddeler)
    tamam = sum(1 for m in maddeler if m.get("tamamlandi"))
    return {"maddeler": maddeler, "toplam": toplam, "tamam": tamam, "tumu_tamam": toplam > 0 and tamam == toplam}


def _kl_leaf_markup(gun_iso):
    g = date.fromisoformat(gun_iso)
    return (
        f'<div class="kl-leaf-ay">{_KL_AY_ISIMLERI[g.month - 1]} {g.year}</div>'
        f'<div class="kl-leaf-gun-no">{g.day}</div>'
        f'<div class="kl-leaf-gun-adi">{_KL_GUN_ISIMLERI_UZUN[g.weekday()]}</div>'
    )


def _kl_leaf_govde(ozet, anahtar_onek, duzenlenebilir=True):
    """Bir takvim yaprağının madde listesini çizer.

    Genel Bakış ve Kontrol Listesi AYNI bu fonksiyonu çağırıyor - ikisi de
    gerçek zamanlı aynı veriye bakıyor, kopya mantık yok. anahtar_onek
    farklı sayfalarda aynı madde id'si için widget key çakışmasını
    önlüyor. duzenlenebilir=False iken (Genel Bakış) sadece durum
    gösteriliyor - tik atma/silme sadece Kontrol Listesi sayfasında."""
    maddeler = ozet["maddeler"]
    if not maddeler:
        st.caption("Bu gün için henüz not eklenmedi.")
    for m in maddeler:
        if not duzenlenebilir:
            if m.get("tamamlandi"):
                st.markdown(
                    f"<div style='color:#1F8A3B;font-weight:700;'>✔ {html.escape(m['madde'])}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<div>☐ {html.escape(m['madde'])}</div>", unsafe_allow_html=True)
            continue
        c1, c2, c3 = st.columns([0.5, 4, 0.5])
        tik = c1.checkbox("", value=m.get("tamamlandi", False), key=f"{anahtar_onek}_tik_{m['id']}")
        if tik != m.get("tamamlandi", False):
            db.kontrol_maddesi_tamamla(m["id"], tik)
            st.rerun()
        if m.get("tamamlandi"):
            c2.markdown(
                f"<span style='color:#1F8A3B;font-weight:700;'>✔ {html.escape(m['madde'])}</span>",
                unsafe_allow_html=True,
            )
        else:
            c2.write(m["madde"])
        if c3.button("🗑", key=f"{anahtar_onek}_sil_{m['id']}"):
            db.kontrol_maddesi_sil(m["id"])
            st.rerun()


# ------------------------------------------------------------------
# ANA SAYFA
# ------------------------------------------------------------------
def _aras_durum_bilgisi(takip_no):
    """Bir Aras takip numarasının güncel durumunu (metin, rozet sınıfı, teslim
    edildi mi) döndürür - Genel Bakış ve Kargo Takip sayfaları ortak kullanıyor."""
    durum = db.aras_kargo_durumu(takip_no) or {}
    # Aras API bazen aynı takip no için TEK sözlük yerine bir LİSTE
    # döndürüyor (örn. birden fazla hareket kaydı olduğunda) - bu durumda
    # en güncel kaydı (listenin son elemanını) kullan.
    if isinstance(durum, list):
        durum = durum[-1] if durum else {}
    metni = durum.get("DURUMU") or "Bilgi bekleniyor"
    ustu = metni.upper()
    teslim_edildi = "TESLİM EDİL" in ustu
    if teslim_edildi:
        sinif = "ok"
    elif "İADE" in ustu or "GECİK" in ustu:
        sinif = "danger"
    else:
        sinif = "warn"
    return metni, sinif, teslim_edildi


def _aras_durum_bilgisi_toplu(takip_no_listesi):
    """_aras_durum_bilgisi'nin çoklu hâli - her takip no için Aras'a AYRI bir
    ağ isteği gerekiyor (API günlük listede durum vermiyor), bunları sırayla
    değil PARALEL çekerek toplam bekleme süresini kısaltır. Genel Bakış'ın
    (giriş sonrası ilk açılan sayfa) ve Kargo Takip'in yavaş açılmasının asıl
    sebebi buydu - 20-50 sevkiyatlı bir günde sırayla sorgulamak onlarca kat
    daha uzun sürüyordu."""
    benzersiz = list(dict.fromkeys(tn for tn in takip_no_listesi if tn))
    sonuc = {}
    if not benzersiz:
        return sonuc
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as havuz:
        gelecekler = {havuz.submit(_aras_durum_bilgisi, tn): tn for tn in benzersiz}
        for gelecek in concurrent.futures.as_completed(gelecekler):
            tn = gelecekler[gelecek]
            try:
                sonuc[tn] = gelecek.result()
            except Exception:
                sonuc[tn] = ("Bilgi bekleniyor", "warn", False)
    return sonuc


def _aras_satir_html(s, takip_no=None, durum_onceden=None):
    takip_no = takip_no or (s.get("TRACKINGNUMBER") or "—")
    metni, sinif, _ = durum_onceden or _aras_durum_bilgisi(takip_no)
    return (
        f"<tr><td class='gb-mono'>{html.escape(takip_no)}</td>"
        f"<td>{html.escape(s.get('ALICI_ADI') or '—')}</td>"
        f"<td>{html.escape(s.get('SEHIR') or '—')}</td>"
        f"<td>Aras</td>"
        f"<td><span class='gb-tag {sinif}'>{html.escape(metni.title())}</span></td></tr>"
    )


_KT_KATEGORILER = [
    "Gönderi Hazırlandı", "Transfer Aşamasında", "Varış Birimine Ulaştı",
    "Alıcı Adresine Yönlendirildi", "Teslim Edildi", "Teslim Edilemedi",
    "Geri Geliyor", "Destek Gerekiyor", "Gönderi İptal",
]


def _aras_durum_kategori(durumu):
    """Aras'ın serbest metin durumunu (DURUMU) MNG'nin gönderi durum
    dashboard'undaki 9 kategoriden birine eşler - Aras bu taksonomiyi
    doğrudan vermiyor, anahtar kelime eşleştirmesiyle yaklaşık olarak
    sınıflandırılıyor."""
    u = (durumu or "").upper()
    if "İPTAL" in u:
        return "Gönderi İptal"
    if "TESLİM EDİLEMEDİ" in u:
        return "Teslim Edilemedi"
    if "TESLİM EDİL" in u:
        return "Teslim Edildi"
    if "İADE" in u or "GERİ" in u:
        return "Geri Geliyor"
    if "DESTEK" in u:
        return "Destek Gerekiyor"
    if "ADRES" in u or "TESLİMATTA" in u or "DAĞITIM" in u:
        return "Alıcı Adresine Yönlendirildi"
    if "ŞUBE" in u and ("ULAŞ" in u or "VARIŞ" in u):
        return "Varış Birimine Ulaştı"
    if "TRANSFER" in u or "AKTARMA" in u:
        return "Transfer Aşamasında"
    return "Gönderi Hazırlandı"


def sayfa_home():
    bugun = date.today()
    bugun_iso = bugun.isoformat()
    dun = bugun - timedelta(days=1)
    dun_iso = dun.isoformat()

    aras_aktif = db._aras_ayarli_mi()
    if aras_aktif:
        aras_bugun = db.aras_gunluk_sevkiyatlar(bugun.strftime("%d/%m/%Y"))
        aras_dun = db.aras_gunluk_sevkiyatlar(dun.strftime("%d/%m/%Y"))
        kargo_bugun = len(aras_bugun)
        kargo_dun = len(aras_dun)
    else:
        aras_bugun = []
        try:
            kargolar_ay = db.tamamlanan_kargolar_getir_ay(bugun.year, bugun.month)
        except Exception:
            kargolar_ay = []
        kargo_bugun = sum(1 for k in kargolar_ay if k.get("tarih") == bugun_iso)
        if dun.month == bugun.month:
            kargo_dun = sum(1 for k in kargolar_ay if k.get("tarih") == dun_iso)
        else:
            try:
                kargolar_dun_ay = db.tamamlanan_kargolar_getir_ay(dun.year, dun.month)
            except Exception:
                kargolar_dun_ay = []
            kargo_dun = sum(1 for k in kargolar_dun_ay if k.get("tarih") == dun_iso)

    try:
        iadeler = db.iadeler_getir()
    except Exception:
        iadeler = []
    bekleyen_iade = len([i for i in iadeler if i.get("durum") != "Kabul Edildi"])

    veri = _bildirim_verileri()

    bugun_ozet = _kl_gun_ozet(bugun_iso)
    kl_tamam, kl_toplam = bugun_ozet["tamam"], bugun_ozet["toplam"]

    if aras_aktif:
        # Her sevkiyatın durumu Aras'tan AYRI bir istekle geliyor - bunları
        # sırayla değil paralel çekiyoruz (bkz. _aras_durum_bilgisi_toplu).
        aras_durum_haritasi = _aras_durum_bilgisi_toplu(
            [s.get("TRACKINGNUMBER") for s in aras_bugun]
        )
        # Teslim edilmemiş (yolda / aktarmada / dağıtımda) TÜM sevkiyatlar -
        # panel görünürde 5 satır yüksekliğinde ama kaydırınca hepsi görünür.
        son_sevkiyatlar = []
        for s in reversed(aras_bugun):
            takip_no = s.get("TRACKINGNUMBER")
            _, _, teslim_edildi = aras_durum_haritasi.get(takip_no, ("Bilgi bekleniyor", "warn", False))
            if not teslim_edildi:
                son_sevkiyatlar.append(s)
    else:
        try:
            son_sevkiyatlar = db.kargo_takip_getir(bugun_iso)
        except Exception:
            son_sevkiyatlar = []
        if not son_sevkiyatlar:
            try:
                son_sevkiyatlar = db.kargo_takip_getir(dun_iso)
            except Exception:
                son_sevkiyatlar = []
        son_sevkiyatlar = list(reversed(son_sevkiyatlar))[:5]

    # ---- Başlık ----
    st.markdown(
        f"""<div class="gb-header-row">
            <div>
                <div class="gb-title">Genel Bakış</div>
                <div class="gb-eyebrow">{bugun.day} {_KL_AY_ISIMLERI[bugun.month - 1]} {bugun.year}, {_KL_GUN_ISIMLERI_UZUN[bugun.weekday()]}</div>
            </div>
            <div class="gb-pill">Bugün · Tüm Depolar</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- KPI kartları ----
    # (kart_sinif, alt_sinif): "" = normal (yeşil vurgu), "warn" = amber, "danger" = kırmızı
    kpiler = [
        ("BUGÜNKÜ SEVKİYAT", str(kargo_bugun), f"{'↑' if kargo_bugun >= kargo_dun else '↓'} dün {kargo_dun}",
         "" if kargo_bugun >= kargo_dun else "warn"),
        ("BEKLEYEN SAYIM", "—", "veri bağlanmadı", "warn"),
        ("AÇIK İADE", str(bekleyen_iade), "kabul bekliyor", ""),
        ("STOK UYARISI", "—", "veri bağlanmadı", "danger"),
        ("KONTROL LİSTESİ", f"{kl_tamam}/{kl_toplam}", "bugün tamamlanan", ""),
    ]
    kart_html = "<div class='gb-kpi-row'>"
    for etiket, sayi, alt, sinif in kpiler:
        kart_sinif = f"gb-kpi-card {sinif}".strip()
        kart_html += (
            f"<div class='{kart_sinif}'>"
            f"<div class='gb-kpi-label'>{etiket}</div>"
            f"<div class='gb-kpi-num'>{sayi}</div>"
            f"<div class='gb-kpi-sub {sinif}'>{alt}</div>"
            f"</div>"
        )
    kart_html += "</div>"
    st.markdown(kart_html, unsafe_allow_html=True)

    ana_col, yan_col = st.columns([2.2, 1], gap="large")

    with ana_col:
        rows_html = ""
        if aras_aktif:
            for s in son_sevkiyatlar:
                rows_html += _aras_satir_html(s, durum_onceden=aras_durum_haritasi.get(s.get("TRACKINGNUMBER")))
        else:
            for s in son_sevkiyatlar:
                rows_html += (
                    f"<tr><td class='gb-mono'>{html.escape(s.get('gonderi_no') or '—')}</td>"
                    f"<td>{html.escape(s.get('alici_adi') or '—')}</td>"
                    f"<td>{html.escape(s.get('varis_il') or '—')}</td>"
                    f"<td>{html.escape(s.get('kargo_firmasi') or '—')}</td>"
                    f"<td><span class='gb-tag notr'>Yüklendi</span></td></tr>"
                )
        if not rows_html:
            rows_html = "<tr><td colspan='5' style='color:#9A9A94;'>Henüz kargo takip kaydı yok.</td></tr>"
        with st.container(key="son_sevkiyat_panel"):
            st.markdown(
                f"""<div class="gb-panel-head">
                    <div class="gb-panel-title">Son Sevkiyatlar</div>
                </div>
                <div class="gb-table-scroll">
                    <table class="gb-table">
                        <tr><th>Takip No</th><th>Alıcı</th><th>Varış İli</th><th>Kargo</th><th>Durum</th></tr>
                        {rows_html}
                    </table>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("Kargo Takip →", key="son_sevkiyat_git"):
                git("kargotakip")

        kl_rows = ""
        for m in bugun_ozet["maddeler"]:
            tamam = m.get("tamamlandi")
            sinif = "done" if tamam else ""
            check_sinif = "gb-kl-check done" if tamam else "gb-kl-check"
            kl_rows += (
                f"<div class='gb-kl-row {sinif}'><div class='{check_sinif}'></div>"
                f"<div class='gb-kl-text'>{html.escape(m['madde'])}</div></div>"
            )
        if not kl_rows:
            kl_rows = "<div style='color:#9A9A94; font-size:13.5px;'>Bugün için henüz madde eklenmedi.</div>"
        with st.container(key="kl_home_panel"):
            st.markdown(
                f"""<div class="gb-panel-head">
                    <div class="gb-panel-title">Bugünkü Kontrol Listesi</div>
                </div>{kl_rows}""",
                unsafe_allow_html=True,
            )
            if st.button("Kontrol Listesini Aç", key="kl_home_bugun_btn"):
                st.session_state.kl_secili_gun = bugun_iso
                git("kontrollistesi")

    with yan_col:
        notif_html = ""
        for t in veri["transferler"]:
            notif_html += (
                f"<div class='gb-notif-row'><div class='gb-notif-dot warn'></div>"
                f"<div><div class='gb-notif-text'><b>{html.escape(t['talep_eden_depo'])}</b> deposundan "
                f"<b>{html.escape(t['hedef_depo'])}</b> için {html.escape(t['urun_aciklama'])} "
                f"({t.get('adet') or '?'} adet) talebi çağrıldı.</div></div></div>"
            )
        for g in veri["gorevler"]:
            notif_html += (
                f"<div class='gb-notif-row'><div class='gb-notif-dot warn'></div>"
                f"<div><div class='gb-notif-text'>⏰ {html.escape(g.get('saat') or '')} — {html.escape(g['aciklama'])}</div></div></div>"
            )
        for p in veri["dogumgunler"]:
            notif_html += (
                f"<div class='gb-notif-row'><div class='gb-notif-dot'></div>"
                f"<div><div class='gb-notif-text'>Bugün <b>{html.escape(p['ad_soyad'])}</b>'nin doğum günü 🎂</div>"
                f"<div class='gb-notif-time'>bugün</div></div></div>"
            )
        if not notif_html:
            notif_html = "<div style='color:#9A9A94; font-size:13.5px;'>Şu an bekleyen bir bildirim yok.</div>"
        st.markdown(
            f"""<div class="gb-panel">
                <div class="gb-panel-head">
                    <div class="gb-panel-title">Bildirimler</div>
                    <div class="gb-panel-link">Tümü →</div>
                </div>
                {notif_html}
            </div>""",
            unsafe_allow_html=True,
        )


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

    col_map, col_bosluk = st.columns([3, 1])
    with col_map, st.container(key="sevk_il_panel"):
        st.markdown('<div class="ptitle">Varış İli</div>', unsafe_allow_html=True)
        if "secili_il" not in st.session_state:
            st.session_state.secili_il = "İZMİR"

        # Haritadan bir önceki çalıştırmada il seçildiyse, selectbox oluşturulmadan
        # önce uygula (widget'ın değeri, oluşturulduktan sonra aynı çalıştırmada
        # değiştirilemiyor - bu yüzden bir sonraki rerun'da burada uyguluyoruz).
        if "harita_secim_bekliyor" in st.session_state:
            st.session_state.secili_il = st.session_state.pop("harita_secim_bekliyor")

        secili_il = st.selectbox("Varış İli", data.IL_LISTESI, key="secili_il", label_visibility="collapsed")
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

    with col_bosluk, st.container(key="sevk_plan_panel"):
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
    with st.container(key="sevk_hesap_panel"):
        st.markdown('<div class="ptitle">Gönderi Hesapla</div>', unsafe_allow_html=True)
        st.caption("Her satıra bir gönderi grubu için Miktar (adet) ve Desi bilgisini girin.")

        if "sevkiyat_df" not in st.session_state:
            st.session_state.sevkiyat_df = pd.DataFrame(
                {"Satır": [f"Satır {i + 1}" for i in range(5)], "Miktar": [float("nan")] * 5, "Desi": [float("nan")] * 5}
            )

        edited = st.data_editor(
            st.session_state.sevkiyat_df,
            num_rows="fixed",
            use_container_width=True,
            key="sevkiyat_editor",
            column_config={
                "Satır": st.column_config.TextColumn("Satır", disabled=True),
                "Miktar": st.column_config.NumberColumn("Miktar", min_value=0, step=1),
                "Desi": st.column_config.NumberColumn("Desi", min_value=0, step=1),
            },
        )
        st.session_state.sevkiyat_df = edited

        with st.popover("➕ Satır Ekle"):
            ek_sayi = st.number_input("Eklenecek satır sayısı", min_value=1, max_value=50, value=1, key="sevk_satir_ekle_sayi")
            if st.button("Ekle", key="sevk_satir_ekle_btn"):
                mevcut_sayi = len(edited)
                ek_df = pd.DataFrame({
                    "Satır": [f"Satır {mevcut_sayi + i + 1}" for i in range(ek_sayi)],
                    "Miktar": [float("nan")] * ek_sayi, "Desi": [float("nan")] * ek_sayi,
                })
                st.session_state.sevkiyat_df = pd.concat([edited, ek_df], ignore_index=True)
                st.rerun()

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
                    st.session_state.hesap_sonuclari = None
                else:
                    sonuclar.sort(key=lambda x: x[1])
                    st.session_state.hesap_sonuclari = sonuclar
                    st.session_state.hesap_il = secili_il
                    st.session_state.hesap_detay = gecerli_satirlar
                    st.session_state.kargo_secilen = sonuclar[0][0]

        sonuclar = st.session_state.get("hesap_sonuclari")
        if sonuclar:
            en_ucuz_kargo = sonuclar[0][0]
            if st.session_state.get("kargo_secilen") not in dict(sonuclar):
                st.session_state.kargo_secilen = en_ucuz_kargo

            st.markdown(f'<div class="psub" style="margin-top:14px;">{st.session_state.hesap_il} için hesaplanan fiyatlar — en ucuz otomatik önerilip seçili geliyor</div>', unsafe_allow_html=True)
            kargo_kolonlari = st.columns(len(sonuclar))
            for j, (kol, (kargo, toplam)) in enumerate(zip(kargo_kolonlari, sonuclar)):
                secili_mi = st.session_state.kargo_secilen == kargo
                onerilen_mi = kargo == en_ucuz_kargo
                durum = "secili" if secili_mi else "no"
                with kol, st.container(key=f"sevk_kargo_kart_{j}_{durum}"):
                    if onerilen_mi:
                        st.markdown('<div class="sevk-rozet">ÖNERİLEN</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="sevk-kargo-ad">{kargo}</div>'
                        f'<div class="sevk-kargo-tutar mono">{toplam:,.2f} TL</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("✓ Seçili" if secili_mi else "Seç", key=f"sevk_kargo_sec_{j}", use_container_width=True):
                        st.session_state.kargo_secilen = kargo
                        st.rerun()

            secilen_kargo = st.session_state.kargo_secilen
            secilen_tutar = dict(sonuclar)[secilen_kargo]

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

    if "kt_view" not in st.session_state:
        st.session_state.kt_view = "sec"
    if "kt_firma" not in st.session_state:
        st.session_state.kt_firma = "Aras Kargo"
    if "kt_tarih" not in st.session_state:
        st.session_state.kt_tarih = date.today()

    t1, t2, t3 = st.columns(3)
    with t1:
        with st.container(key="kt_tile_sec"):
            if st.button("Kargo Seç", key="kt_btn_sec", use_container_width=True):
                st.session_state.kt_view = "sec"
    with t2:
        with st.container(key="kt_tile_takip"):
            if st.button("Takip Et", key="kt_btn_takip", use_container_width=True):
                st.session_state.kt_view = "takip"
    with t3:
        with st.container(key="kt_tile_rapor"):
            if st.button("Kargo Raporları", key="kt_btn_rapor", use_container_width=True):
                st.session_state.kt_view = "rapor"

    kargo_firmalari = ["Tüm Kargolar", "Aras Kargo"]  # MNG Kargo API'si hazır olunca eklenecek

    if st.session_state.kt_view == "sec":
        c1, c2 = st.columns(2)
        with c1:
            varsayilan_dizin = kargo_firmalari.index(st.session_state.kt_firma) if st.session_state.kt_firma in kargo_firmalari else 0
            st.session_state.kt_firma = st.selectbox("Kargo Firması", kargo_firmalari, index=varsayilan_dizin, key="kt_firma_secim")
        with c2:
            st.session_state.kt_tarih = st.date_input("Gün Seçin", value=st.session_state.kt_tarih, key="kt_tarih_secim")

    firma = st.session_state.kt_firma
    tarih = st.session_state.kt_tarih

    # ---- Veriyi topla (şu an sadece Aras canlı entegre - "Tüm Kargolar" da
    # bu yüzden Aras'la aynı; başka firmaların API'si eklenince buraya katılacak) ----
    aras_liste = []
    if firma in ("Aras Kargo", "Tüm Kargolar") and db._aras_ayarli_mi():
        aras_liste = db.aras_gunluk_sevkiyatlar(tarih.strftime("%d/%m/%Y"))

    # Her sevkiyatın durumu Aras'tan ayrı bir istek gerektiriyor - paralel çekiyoruz.
    kt_durum_haritasi = _aras_durum_bilgisi_toplu([s.get("TRACKINGNUMBER") for s in aras_liste])
    durumlu = []  # (s, takip_no, metni, sinif, kategori)
    for s in aras_liste:
        takip_no = s.get("TRACKINGNUMBER") or "—"
        metni, sinif, _ = kt_durum_haritasi.get(takip_no, ("Bilgi bekleniyor", "warn", False))
        durumlu.append((s, takip_no, metni, sinif, _aras_durum_kategori(metni)))

    if st.session_state.kt_view == "takip":
        st.subheader("Gönderi Ara")
        arama = st.text_input("Takip no veya alıcı adı ile ara", key="kt_arama")
        sonuc = [d for d in durumlu if not arama or arama.lower() in f"{d[1]} {d[0].get('ALICI_ADI') or ''}".lower()]
        if not db._aras_ayarli_mi():
            st.info("Aras Kargo API bağlantısı henüz yapılandırılmadı (Streamlit Cloud Secrets).")
        elif not sonuc:
            st.caption("Sonuç bulunamadı.")
        else:
            rows_html = "".join(
                f"<tr><td class='gb-mono'>{html.escape(takip_no)}</td>"
                f"<td>{html.escape(s.get('ALICI_ADI') or '—')}</td>"
                f"<td>{html.escape(s.get('SEHIR') or '—')}</td>"
                f"<td>Aras</td>"
                f"<td><span class='gb-tag {sinif}'>{html.escape(metni.title())}</span></td></tr>"
                for s, takip_no, metni, sinif, _kat in sonuc
            )
            st.markdown(
                f"""<div class="gb-panel"><table class="gb-table">
                    <tr><th>Takip No</th><th>Alıcı</th><th>Varış İli</th><th>Kargo</th><th>Durum</th></tr>
                    {rows_html}
                </table></div>""",
                unsafe_allow_html=True,
            )
            st.caption(f"{len(sonuc)} / {len(durumlu)} gönderi gösteriliyor.")

    elif st.session_state.kt_view == "rapor":
        st.subheader("Kargo Raporları")
        if not db._aras_ayarli_mi():
            st.info("Aras Kargo API bağlantısı henüz yapılandırılmadı (Streamlit Cloud Secrets).")
        else:
            st.caption(f"Kargo firması: **{firma}**")
            donem = st.radio(
                "Dönem", ["Günlük", "Haftalık", "Aylık", "Tüm Zamanlar (son 90 gün)"],
                horizontal=True, key="kt_rapor_donem",
            )
            bugun = date.today()
            if donem == "Günlük":
                gunler = [tarih]
            elif donem == "Haftalık":
                hafta_baslangic = bugun - timedelta(days=bugun.weekday())
                gunler = [hafta_baslangic + timedelta(days=i) for i in range(7) if hafta_baslangic + timedelta(days=i) <= bugun]
            elif donem == "Aylık":
                ay_baslangic = bugun.replace(day=1)
                gunler = [ay_baslangic + timedelta(days=i) for i in range((bugun - ay_baslangic).days + 1)]
            else:
                gunler = [bugun - timedelta(days=i) for i in range(90)]

            with st.spinner(f"{len(gunler)} günlük veri toplanıyor..."):
                donem_sevkiyatlar = []
                for g in gunler:
                    donem_sevkiyatlar.extend(db.aras_gunluk_sevkiyatlar(g.strftime("%d/%m/%Y")))

            if not donem_sevkiyatlar:
                st.info("Bu dönemde gönderi bulunamadı.")
            else:
                toplam_tutar = sum(float(s.get("TUTAR") or 0) for s in donem_sevkiyatlar)
                ort_tutar = toplam_tutar / len(donem_sevkiyatlar)
                r1, r2, r3 = st.columns(3)
                r1.metric("Toplam Gönderi", len(donem_sevkiyatlar))
                r2.metric("Toplam Tutar", f"{toplam_tutar:,.2f} ₺")
                r3.metric("Ortalama Tutar", f"{ort_tutar:,.2f} ₺")

                # Gönderici/Alıcı ödemeli ayrımı Aras'ın toplu günlük listesinde
                # YOK - her gönderi için ayrı bir sorgu gerektiriyor. Kısa
                # dönemlerde (Günlük/Haftalık) otomatik hesaplanıyor, uzun
                # dönemlerde (Aylık/Tüm Zamanlar) çok sayıda istek anlamına
                # geldiği için kullanıcı onayıyla (buton) tetikleniyor - site
                # daha önce tam bu yüzden (çok sayıda ardışık sorgu) yavaşlamıştı.
                st.markdown("---")
                st.markdown("**Ödeme Tipi Dağılımı** (fiyatlandırma için: gönderici ödemeli = bize maliyeti olan gönderiler)")
                otomatik_hesapla = donem in ("Günlük", "Haftalık")
                hesapla_tetik = otomatik_hesapla
                if not otomatik_hesapla:
                    hesapla_tetik = st.button(
                        f"💰 Ödeme tipi dağılımını hesapla ({len(donem_sevkiyatlar)} gönderi, biraz sürebilir)",
                        key="kt_odeme_tipi_hesapla",
                    )
                if hesapla_tetik:
                    with st.spinner("Her gönderinin ödeme tipi sorgulanıyor..."):
                        gonderici_tutar, alici_tutar, bilinmeyen_tutar = [], [], []
                        for s in donem_sevkiyatlar:
                            detay = db.aras_kargo_durumu(s.get("TRACKINGNUMBER")) or {}
                            if isinstance(detay, list):
                                detay = detay[-1] if detay else {}
                            odeme = (detay.get("ODEME_TIPI") or "").upper()
                            tutar = float(s.get("TUTAR") or 0)
                            if odeme == "ÜG":
                                gonderici_tutar.append(tutar)
                            elif odeme == "ÜA":
                                alici_tutar.append(tutar)
                            else:
                                bilinmeyen_tutar.append(tutar)
                    o1, o2, o3 = st.columns(3)
                    o1.metric("Gönderici Ödemeli (ÜG)", f"{len(gonderici_tutar)} gönderi", f"{sum(gonderici_tutar):,.2f} ₺")
                    o2.metric("Alıcı Ödemeli (ÜA)", f"{len(alici_tutar)} gönderi", f"{sum(alici_tutar):,.2f} ₺")
                    if bilinmeyen_tutar:
                        o3.metric("Bilinmiyor", f"{len(bilinmeyen_tutar)} gönderi", f"{sum(bilinmeyen_tutar):,.2f} ₺")
                    if gonderici_tutar:
                        st.caption(f"Gönderici ödemeli gönderilerde ortalama tutar: {sum(gonderici_tutar) / len(gonderici_tutar):,.2f} ₺")
                elif not otomatik_hesapla:
                    st.caption("Bu dönem için ödeme tipi dağılımı henüz hesaplanmadı - yukarıdaki butona basın.")

    # ---- Genel özet - her zaman görünür ----
    kategori_sayilari = {ad: 0 for ad in _KT_KATEGORILER}
    for _s, _t, _m, _sinif, kategori in durumlu:
        kategori_sayilari[kategori] = kategori_sayilari.get(kategori, 0) + 1
    toplam = len(durumlu)

    st.markdown(
        f"""<div class="kt-banner">
            <div>{tarih.strftime('%d.%m.%Y')} · {firma}</div>
            <div class="kt-banner-pill">Toplam Gönderi: {toplam} Adet</div>
        </div>""",
        unsafe_allow_html=True,
    )
    if not db._aras_ayarli_mi():
        st.info("Aras Kargo API bağlantısı henüz yapılandırılmadı (Streamlit Cloud Secrets).")
    else:
        kutu_html = "<div class='kt-grid'>"
        for ad in _KT_KATEGORILER:
            sayi = kategori_sayilari.get(ad, 0)
            oran = (sayi / toplam * 100) if toplam else 0
            kutu_html += (
                f"<div class='kt-box'><div class='kt-box-num'>{sayi}</div><div class='kt-box-lbl'>{html.escape(ad)}</div>"
                f"<div class='kt-box-bar'><div class='kt-box-bar-fill' style='width:{oran:.0f}%;'></div></div></div>"
            )
        kutu_html += "</div>"
        st.markdown(kutu_html, unsafe_allow_html=True)

    st.markdown("---")

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

    # Depo Temizlik'e sidebar'daki kendi ayrı bağlantısından gelinir - burada
    # "Depo Sayım Fişleri" şablonuna gerek yok, bu yüzden sadece diğer
    # görünümlerde gösteriliyor.
    if st.session_state.depo_alt_sayfa not in ("temizlik", "sayim"):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📋\n\nDepo Sayım Fişleri", use_container_width=True):
                st.session_state.depo_alt_sayfa = "sayim"
                st.rerun()
        with c2:
            if st.button("🗓️\n\nHaftalık Depo Kontrol Şablonu", use_container_width=True):
                st.session_state.depo_alt_sayfa = "haftalik_kontrol"
                st.rerun()

        st.markdown("---")

    if st.session_state.depo_alt_sayfa == "sayim":
        depo_sayim_bolumu()
    elif st.session_state.depo_alt_sayfa == "temizlik":
        depo_temizlik_bolumu()
    elif st.session_state.depo_alt_sayfa == "haftalik_kontrol":
        haftalik_kontrol_bolumu()


def _fark_var_mi(f):
    try:
        return abs(float(str(f).replace(",", "."))) > 1e-9
    except (ValueError, TypeError):
        return False


def _sayim_ozet_df(oturumlar, stok_override=None):
    """Bir güne ait TÜM otomatik sayım oturumlarını (kronolojik id sırasıyla)
    birleştirip her ürün için SON sayım sonucunu hesaplar. Bir ürün birden
    fazla oturumda sayılmışsa (önce yanlış çıkıp personel tekrar saymışsa)
    son sayım esas alınır ve öncesinde yanlış varsa "Düzeltildi" olarak
    işaretlenir.

    stok_override verilirse (bkz. _depo_sayim_gun_stok_haritasi) güncel_stok/fark
    kaydedilmiş haliyle DEĞİL, o günün Depo Sayım Fişleri excel'indeki stok
    değerleriyle yeniden hesaplanır - otomatik sayım o günkü resmi stok
    kaynağıyla eşleşsin diye."""
    urun_gecmisi = {}
    for oturum in oturumlar:
        for d in db.stok_sayim_detay_getir(oturum["id"]):
            urun_gecmisi.setdefault(d["urun_adi"], []).append(dict(d))

    if stok_override:
        for urun, gecmis in urun_gecmisi.items():
            guncel = stok_override.get(urun)
            if guncel is None:
                continue
            for kayit in gecmis:
                kayit["guncel_stok"] = guncel
                try:
                    kayit["fark"] = str(
                        float(str(kayit.get("sayilan")).replace(",", ".")) - float(str(guncel).replace(",", "."))
                    )
                except (ValueError, TypeError):
                    pass

    satirlar = []
    for urun, gecmis in urun_gecmisi.items():
        son = gecmis[-1]
        son_yanlis = _fark_var_mi(son.get("fark"))
        onceden_yanlis = any(_fark_var_mi(g.get("fark")) for g in gecmis[:-1])
        if son_yanlis:
            durum = "Yanlış"
        elif onceden_yanlis:
            durum = "Düzeltildi"
        else:
            durum = "Doğru"
        satirlar.append({
            "Ürün Adı": urun, "Güncel Stok": son.get("guncel_stok"),
            "Sayım": son.get("sayilan"), "Fark": son.get("fark"), "Durum": durum,
        })
    return pd.DataFrame(satirlar)


def _sayim_ozet_renklendir(row):
    renk = {"Doğru": "#DCF3E0", "Yanlış": "#FBE1E1", "Düzeltildi": "#DBEAFB"}.get(row["Durum"], "")
    return [f"background-color: {renk}"] * len(row) if renk else [""] * len(row)


def _excel_sayim_verisi(dosya_icerik_bytes):
    """Bir 'Depo Sayım Fişleri > Excel Yükleme' dosyasından {urun_adi: {'Sayım':.., 'Fark':..}}
    döner - otomatik (Stok Sayım) akışıyla aynı şekle getirilir ki haftalık
    kontrol tablosunda iki kaynak da birlikte gösterilebilsin."""
    try:
        filtreli = excel_utils.sayim_satirlarini_filtrele(io.BytesIO(dosya_icerik_bytes))
    except Exception:
        return {}
    if filtreli.empty:
        return {}
    urun_col = excel_utils.bul_sutun(filtreli.columns, ["AÇIKLAMA", "ÜRÜN ADI", "MALZEME ADI", "STOK ADI", "TANIM"])
    sayim_col = excel_utils.bul_sutun(filtreli.columns, ["SAYIM ADEDI", "SAYIM MIKTARI", "SAYILAN", "SAYIM"])
    if urun_col is None or sayim_col is None:
        return {}
    stok_col = filtreli.attrs.get("stok_col")
    sonuc = {}
    for _, row in filtreli.iterrows():
        urun = row.get(urun_col)
        if not urun or str(urun).strip() == "":
            continue
        sayim_deger = row.get(sayim_col)
        fark = ""
        if stok_col is not None:
            try:
                fark = str(float(str(sayim_deger).replace(",", ".")) - float(str(row.get(stok_col)).replace(",", ".")))
            except (ValueError, TypeError):
                fark = ""
        sonuc[str(urun).strip()] = {"Sayım": sayim_deger, "Fark": fark}
    return sonuc


def _depo_sayim_gun_stok_haritasi(tarih_iso):
    """O güne 'Depo Sayım Fişleri > Excel Yükleme'den yüklenmiş dosya(lar)daki
    TÜM ürünlerin güncel stok değerlerini {Ürün Adı: Stok} olarak döner (excel
    içindeki 'Sayım' sütunu dolu olsun olmasın, tüm satırlar). Otomatik
    Sayım'ın karşılaştırma kaynağı bu olsun diye - personelin o gün fiilen
    elindeki resmi stok listesiyle eşleşsin. O gün için excel yoksa None döner."""
    kayitlar = db.depo_sayim_getir(tarih_iso)
    if not kayitlar:
        return None
    harita = {}
    for k in kayitlar:
        try:
            df = pd.read_excel(io.BytesIO(k["dosya_icerik"]))
        except Exception:
            continue
        urun_col = excel_utils.bul_sutun(df.columns, ["AÇIKLAMA", "ÜRÜN ADI", "MALZEME ADI", "STOK ADI", "TANIM"])
        sayim_col = excel_utils.bul_sutun(df.columns, ["SAYIM ADEDI", "SAYIM MIKTARI", "SAYILAN", "SAYIM"])
        if urun_col is None or sayim_col is None:
            continue
        kolon_listesi = list(df.columns)
        sayim_idx = kolon_listesi.index(sayim_col)
        stok_col = kolon_listesi[sayim_idx - 1] if sayim_idx > 0 else None
        if stok_col is None:
            continue
        for _, row in df.iterrows():
            urun_adi = row.get(urun_col)
            if not urun_adi or str(urun_adi).strip() == "":
                continue
            harita[str(urun_adi).strip()] = row.get(stok_col)
    return harita or None


def _depo_sayim_gun_urun_listesi(tarih_iso):
    """_depo_sayim_gun_stok_haritasi'ni _stok_sayim_bolumu'nun beklediği
    {'Ürün Adı', 'Stok', 'Marka', 'Kategori'} satır şekline çevirir."""
    harita = _depo_sayim_gun_stok_haritasi(tarih_iso)
    if not harita:
        return None
    return [{"Ürün Adı": u, "Stok": s, "Marka": "", "Kategori": ""} for u, s in harita.items()]


def _detaylar_override_uygula(detaylar, stok_override):
    """Sayım detay satırlarındaki güncel_stok/fark değerlerini (kaydedilmiş
    haliyle DEĞİL, sadece görüntüde) verilen gün-bazlı stok haritasıyla
    yeniden hesaplar - bkz. _depo_sayim_gun_stok_haritasi."""
    if not stok_override:
        return detaylar
    sonuc = []
    for d in detaylar:
        d = dict(d)
        guncel = stok_override.get(d.get("urun_adi"))
        if guncel is not None:
            d["guncel_stok"] = guncel
            try:
                d["fark"] = str(float(str(d.get("sayilan")).replace(",", ".")) - float(str(guncel).replace(",", ".")))
            except (ValueError, TypeError):
                pass
        sonuc.append(d)
    return sonuc


def haftalik_kontrol_bolumu():
    st.subheader("Haftalık Depo Kontrol Şablonu")
    st.caption(
        "Bu haftanın (Pazartesi–Pazar) hem Excel yükleme hem otomatik (Stok Sayım) yoluyla "
        "yapılan TÜM sayımları, güncel ürün listesiyle birleştirilerek gösterilir - hiç "
        "sayılmamış ürünler de dahildir."
    )
    _haftalik_rapor_icerik()


def _haftalik_rapor_icerik():
    bugun = date.today()
    hafta_baslangic = bugun - timedelta(days=bugun.weekday())
    gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    hafta_gunleri = [hafta_baslangic + timedelta(days=i) for i in range(7)]

    urun_sayim = {}
    for gun, isim in zip(hafta_gunleri, gun_isimleri):
        for oturum in db.stok_sayim_oturumlari_getir(gun.isoformat()):
            for d in db.stok_sayim_detay_getir(oturum["id"]):
                urun_sayim[d["urun_adi"]] = {"Sayım": d.get("sayilan"), "Fark": d.get("fark"), "Gün": isim}
        for kayit in db.depo_sayim_getir(gun.isoformat()):
            for urun_adi, bilgi in _excel_sayim_verisi(kayit["dosya_icerik"]).items():
                urun_sayim[urun_adi] = {"Sayım": bilgi["Sayım"], "Fark": bilgi["Fark"], "Gün": isim}

    try:
        en_son_excel = db.excel_stok_sayim_getir_en_son()
        if en_son_excel is not None:
            urunler, _eslesme = _excel_stok_oku(io.BytesIO(en_son_excel["dosya_icerik"]))
        else:
            urunler = _stok_verisi_cache()
    except Exception as e:
        st.error(f"Ürün listesi alınamadı: {e}")
        urunler = []

    satirlar = []
    urun_adlari_bilinen = set()
    for u in urunler:
        urun_adi = u.get("Ürün Adı")
        if not urun_adi:
            continue
        urun_adlari_bilinen.add(urun_adi)
        bilgi = urun_sayim.get(urun_adi)
        satirlar.append({
            "Ürün Adı": urun_adi, "Güncel Stok": u.get("Stok"),
            "Sayım": bilgi["Sayım"] if bilgi else "", "Fark": bilgi["Fark"] if bilgi else "",
            "Sayıldığı Gün": bilgi["Gün"] if bilgi else "Sayılmadı",
            "_sayildi": 1 if bilgi else 0,
        })
    # Ürün listesinde (XML/excel kaynağında) hiç yer almayan ama Excel sayım
    # dosyasında sayılmış ürünler (ör. farklı bir isimlendirme/kaynak) de
    # kaybolmasın diye ayrıca ekleniyor.
    for urun_adi, bilgi in urun_sayim.items():
        if urun_adi in urun_adlari_bilinen:
            continue
        satirlar.append({
            "Ürün Adı": urun_adi, "Güncel Stok": "",
            "Sayım": bilgi["Sayım"], "Fark": bilgi["Fark"], "Sayıldığı Gün": bilgi["Gün"], "_sayildi": 1,
        })
    if not satirlar:
        st.info("Ürün listesi bulunamadı.")
        return

    df = pd.DataFrame(satirlar)

    f1, f2 = st.columns([2, 1])
    with f1:
        siralama = st.radio(
            "Sıralama", ["Varsayılan", "Sayılmayanlar Önce", "Sayılanlar Önce"],
            horizontal=True, key="hk_siralama",
        )
    with f2:
        sadece_sayilmayan = st.checkbox("Sadece sayılmayanları göster", key="hk_sadece_sayilmayan")

    if sadece_sayilmayan:
        df = df[df["_sayildi"] == 0]
    if siralama == "Sayılmayanlar Önce":
        df = df.sort_values("_sayildi", ascending=True)
    elif siralama == "Sayılanlar Önce":
        df = df.sort_values("_sayildi", ascending=False)
    df = df.drop(columns=["_sayildi"]).reset_index(drop=True)

    def _renklendir(row):
        renk = "#DCF3E0" if row["Sayıldığı Gün"] != "Sayılmadı" else "#FBE1E1"
        return [f"background-color: {renk}"] * len(row)

    if df.empty:
        st.caption("Filtreye uyan ürün yok.")
        return

    styler = df.style.apply(_renklendir, axis=1)
    st.dataframe(styler, use_container_width=True, height=520, hide_index=True)
    sayilan_adet = int((df["Sayıldığı Gün"] != "Sayılmadı").sum())
    st.caption(f"🟢 Sayıldı: {sayilan_adet} · 🔴 Sayılmadı: {len(df) - sayilan_adet} · Sütun başlıklarına tıklayarak sıralayabilirsiniz.")

    # Excel indirme - ekrandaki İLE BİREBİR AYNI sütunlar ve renkler (aynı
    # styler nesnesi kullanılıyor, pandas openpyxl motoruyla hücre
    # arkaplanlarını da xlsx'e yazıyor).
    excel_buffer = io.BytesIO()
    styler.to_excel(excel_buffer, index=False, engine="openpyxl", sheet_name="Haftalık Kontrol")
    st.download_button(
        "⬇ Excel olarak indir", data=excel_buffer.getvalue(),
        file_name=f"haftalik_depo_kontrol_{bugun.isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="hk_excel_indir",
    )


# Excel'de blok bilgisi yok, bu yüzden hangi bölgenin sayıldığı bu listeye
# göre personel tarafından elle işaretlenir. Her blok haftada bir kez
# sayılıyor (hangi gün sayıldığı önemli değil, sayım işi haftanın
# günlerine bölünüyor) - bu yüzden tamamlanma oranı hücre sayısına değil,
# en az bir gün işaretlenmiş DİSTİNCT blok sayısına göre hesaplanıyor.
DEPO_BLOK_LISTESI = [
    "Ip",
    "Analog",
    "Intercom",
    "Alarm",
    "Kablo",
    "Monitör",
    "Raf",
    "Speed Dome",
    "Araç Cam",
    "Honeywell",
    "Tplink",
    "Mutlusan",
    "Reçber",
]


DEPO_GUN_KISALTMA = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def _depo_sayim_toplam_fark(gun_dosyalari):
    """Bu hafta yüklenen TÜM excel'lerdeki ürün bazlı farkların toplamı."""
    toplam = 0.0
    for kayitlar in gun_dosyalari.values():
        for k in kayitlar:
            for bilgi in _excel_sayim_verisi(k["dosya_icerik"]).values():
                try:
                    f = float(str(bilgi.get("Fark")).replace(",", "."))
                except (ValueError, TypeError):
                    continue
                if abs(f) > 1e-9:
                    toplam += f
    return toplam


def _depo_sayim_kpi_seridi(kolonlar, hafta_gunleri, gun_dosyalari, blok_durumlari):
    """3 KPI kartını verilen 3 Streamlit sütununa çizer."""
    toplam_blok = len(DEPO_BLOK_LISTESI)
    # Blok listesi ileride yeniden adlandırılırsa DB'de eski isimle kalmış
    # "yetim" kayıtlar burada sayılmasın diye güncel listeyle kesişim alınıyor.
    bloklar_sayildi = {
        blok for (g, blok), v in blok_durumlari.items()
        if v.get("sayildi") and blok in DEPO_BLOK_LISTESI
    }
    tamamlanma = round(len(bloklar_sayildi) / toplam_blok * 100) if toplam_blok else 0
    toplam_fark = _depo_sayim_toplam_fark(gun_dosyalari)

    kartlar = [
        ("", "Bu Hafta Sayılan Blok", f"{len(bloklar_sayildi)} / {toplam_blok}", "En az bir kez işaretlenen blok", ""),
        ("info", "Tamamlanma Oranı", f"%{tamamlanma}", f"{len(bloklar_sayildi)} / {toplam_blok} blok sayıldı", "info"),
        ("warn", "Toplam Fark", f"{toplam_fark:+.0f}", "Bu hafta yüklenen excel'lere göre", "warn"),
    ]
    for kol, (kart_sinif, etiket, deger, alt, alt_sinif) in zip(kolonlar, kartlar):
        with kol:
            st.markdown(f"""
            <div class="gb-kpi-card {kart_sinif}" style="height:100%;">
                <div class="gb-kpi-label">{etiket}</div>
                <div class="gb-kpi-num">{deger}</div>
                <div class="gb-kpi-sub {alt_sinif}">{alt}</div>
            </div>
            """, unsafe_allow_html=True)


def _depo_sayim_son_islemler(gun_isolari, gun_dosyalari, blok_durumlari):
    olaylar = []
    for gun_iso in gun_isolari:
        for k in gun_dosyalari.get(gun_iso, []):
            olaylar.append({
                "zaman": k.get("yuklenme_zamani") or gun_iso,
                "metin": f"{k['dosya_adi']} yüklendi",
                "alt": datetime.fromisoformat(gun_iso).strftime("%d.%m.%Y"),
            })
    for (gun_iso, blok), durum in blok_durumlari.items():
        if not durum.get("sayildi") or blok not in DEPO_BLOK_LISTESI:
            continue
        zaman = durum.get("isaretlenme_zamani") or gun_iso
        kim = durum.get("personel_adi") or "Bilinmiyor"
        olaylar.append({
            "zaman": zaman,
            "metin": f"{blok} sayıldı olarak işaretlendi",
            "alt": f"{kim} · {datetime.fromisoformat(gun_iso).strftime('%d.%m.%Y')}",
        })
    olaylar.sort(key=lambda o: o["zaman"], reverse=True)
    olaylar = olaylar[:10]

    with st.container(key="ds_son_islemler_panel"):
        st.markdown('<div class="ds-panel-title">Son İşlemler</div>', unsafe_allow_html=True)
        if not olaylar:
            st.caption("Bu hafta için henüz bir işlem yok.")
        else:
            satirlar = "".join(
                f'<div class="ds-log-row"><div class="ds-log-dot"></div>'
                f'<div><div class="ds-log-text">{o["metin"]}</div>'
                f'<div class="ds-log-alt">{o["alt"]}</div></div></div>'
                for o in olaylar
            )
            st.markdown(satirlar, unsafe_allow_html=True)


_EXCEL_YUKLENDI_IKON = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#1E7F72" stroke-width="2.4">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<path d="M14 2v6h6"/><path d="M9 15l2 2 4-4"/></svg>'
)


def _depo_blok_matrisi(hafta_gunleri, durumlar, gun_dosyalari):
    """Blok/bölge x gün matrisi - excel'den bağımsız, personelin elle
    işaretlediği 'bu blok bu gün sayıldı' durumunu gösterir/günceller."""
    with st.container(key="ds_matris_panel"):
        st.markdown('<div class="ds-panel-title">Haftalık Durum Matrisi</div>', unsafe_allow_html=True)
        st.markdown('<div class="ds-panel-sub">Excel\'de blok bilgisi olmadığı için, hangi bölgenin sayıldığını personel burada işaretler. Miktar/fark kontrolü excel detayından yapılır.</div>', unsafe_allow_html=True)

        gun_isolari = [g.isoformat() for g in hafta_gunleri]

        baslik_cols = st.columns([2.2] + [1] * 7)
        baslik_cols[0].markdown("&nbsp;", unsafe_allow_html=True)
        for col, kisaltma, gun, gun_iso in zip(baslik_cols[1:], DEPO_GUN_KISALTMA, hafta_gunleri, gun_isolari):
            with col:
                excel_ikon = _EXCEL_YUKLENDI_IKON if gun_dosyalari.get(gun_iso) else ""
                st.markdown(
                    f'<div class="ds-gun-baslik">{kisaltma}</div>'
                    f'<div class="ds-gun-tarih">{gun.strftime("%d.%m")}</div>'
                    f'<div class="ds-gun-excel">{excel_ikon}</div>',
                    unsafe_allow_html=True,
                )

        for i, blok in enumerate(DEPO_BLOK_LISTESI):
            with st.container(key=f"ds_blokrow_{i}"):
                satir_cols = st.columns([2.2] + [1] * 7)
                with satir_cols[0]:
                    st.markdown(f'<div class="ds-blok-adi">{blok}</div>', unsafe_allow_html=True)
                for col, gun_iso in zip(satir_cols[1:], gun_isolari):
                    durum = durumlar.get((gun_iso, blok), {})
                    sayildi_mevcut = bool(durum.get("sayildi"))
                    with col:
                        yeni_deger = st.checkbox(
                            blok, value=sayildi_mevcut, key=f"blok_durum_{gun_iso}_{blok}",
                            label_visibility="collapsed",
                        )
                    if yeni_deger != sayildi_mevcut:
                        # st.rerun() gerekmiyor: checkbox tıklandığı an Streamlit
                        # zaten otomatik olarak yeniden çalıştırıyor ve yukarıda
                        # (depo_sayim_bolumu) session_state'ten okunan değer bu
                        # değişikliği anında yansıtıyor - veritabanı yazması
                        # arka planda, ekranı bekletmeden tamamlanıyor.
                        db.depo_sayim_blok_durumu_isaretle(gun_iso, blok, yeni_deger, None)


def depo_sayim_bolumu():
    ds_baslik_kolon, ds_yukleme_kolon = st.columns([1.4, 1])
    with ds_baslik_kolon:
        st.markdown("""
        <div class="gb-header-row">
            <div>
                <div class="gb-title">Depo Sayım Fişleri</div>
                <div class="gb-eyebrow">Depo sayımı haftalık programlanır — her gün deponun bir kısmı sayılır, hafta sonunda tüm depo sayılmış olur.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Panel'i bir kere oluşturup nesnesini saklıyoruz - aşağıda hafta/KPI
    # verisi hesaplandıktan SONRA bu panele dosya yükleyiciyi ekleyeceğiz
    # (tarih seçici burada, yükleyici ise KPI kartlarından sonra render
    # edilecek - böylece başlık sütununa KPI'ları da bu panelle AYNI satırda,
    # ayrı bir satıra taşmadan ekleyebiliyoruz - alttaki gereksiz boşluğun
    # sebebi buydu).
    ds_panel = ds_yukleme_kolon.container(key="ds_yukleme_panel")
    with ds_panel:
        st.markdown('<div class="ds-panel-title">Günlük Sayım Excel Yükleme</div>', unsafe_allow_html=True)
        secili_tarih = st.date_input("Sayım Tarihi", value=date.today(), key="sayim_tarih")

    # secili_tarih'in içinde bulunduğu haftanın Pazartesi-Pazar günlerini bul
    hafta_baslangic = secili_tarih - timedelta(days=secili_tarih.weekday())
    gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    hafta_gunleri = [hafta_baslangic + timedelta(days=i) for i in range(7)]
    gun_isolari = [g.isoformat() for g in hafta_gunleri]

    notlar = db.sayim_notlari_getir(gun_isolari)
    blok_durumlari_db = db.depo_sayim_blok_durumlari_getir(gun_isolari)
    gun_dosyalari = db.depo_sayim_getir_coklu(gun_isolari)

    # Bir checkbox'a tıklandığında Streamlit onun son değerini kendi
    # session_state'inde (widget key'i üzerinden) hemen, veritabanı
    # yazması bitmeden ÖNCE saklar. KPI'ları veritabanından TEKRAR
    # okunan (henüz güncellenmemiş olabilecek) veriyle hesaplamak, hızlı
    # art arda tıklamada görünen kutu ile üstteki sayılarn tutmamasına
    # sebep oluyordu. Bu yüzden her hücre için - varsa - checkbox'ın
    # kendi session_state değeri esas alınıyor, veritabanı sadece o
    # hücre hiç render edilmemişse (ilk yükleme) kaynak oluyor.
    blok_durumlari = {}
    for gun_iso in gun_isolari:
        for blok in DEPO_BLOK_LISTESI:
            widget_key = f"blok_durum_{gun_iso}_{blok}"
            if widget_key in st.session_state:
                eski = blok_durumlari_db.get((gun_iso, blok), {})
                blok_durumlari[(gun_iso, blok)] = {**eski, "sayildi": bool(st.session_state[widget_key])}
            elif (gun_iso, blok) in blok_durumlari_db:
                blok_durumlari[(gun_iso, blok)] = blok_durumlari_db[(gun_iso, blok)]

    if "sayim_secili_gun" not in st.session_state:
        st.session_state.sayim_secili_gun = None

    if "ds_rapor_acik" not in st.session_state:
        st.session_state.ds_rapor_acik = False

    # KPI kartları başlık sütununa (ds_baslik_kolon) EKLENİYOR - ayrı bir
    # satır olarak değil, başlığın hemen altına akışta devam ediyor.
    with ds_baslik_kolon:
        kpi_kolonlari = st.columns(3)
        _depo_sayim_kpi_seridi(kpi_kolonlari, hafta_gunleri, gun_dosyalari, blok_durumlari)

    # Yükleme paneline (aynı container nesnesi) şimdi dosya yükleyiciyi ekle.
    with ds_panel:
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

    col_matris, col_son_islemler = st.columns([2.4, 1])
    with col_matris:
        _depo_blok_matrisi(hafta_gunleri, blok_durumlari, gun_dosyalari)
    with col_son_islemler:
        with st.container(key="ds_rapor_tile"):
            if st.button("Haftalık Rapor\nDetaylı tabloyu aç/kapat", key="ds_rapor_ac_btn", use_container_width=True):
                st.session_state.ds_rapor_acik = not st.session_state.ds_rapor_acik
        _depo_sayim_son_islemler(gun_isolari, gun_dosyalari, blok_durumlari)

    if st.session_state.ds_rapor_acik:
        with st.container(key="ds_rapor_panel"):
            st.markdown('<div class="ds-panel-title">Haftalık Rapor</div>', unsafe_allow_html=True)
            _haftalik_rapor_icerik()

    with st.container(key="ds_takvim_panel"):
        st.markdown('<div class="ds-panel-title">Haftalık Sayım Takvimi</div>', unsafe_allow_html=True)
        gun_otomatik_sayimlar = db.stok_sayim_oturumlari_getir_coklu(gun_isolari)
        gun_cols = st.columns(7)
        for i, (col, gun, isim) in enumerate(zip(gun_cols, hafta_gunleri, gun_isimleri)):
            gun_iso = gun.isoformat()
            kayitlar = gun_dosyalari[gun_iso]
            excel_var = bool(kayitlar)
            otomatik = gun_otomatik_sayimlar[gun_iso]
            oto_var = bool(otomatik)
            durum_sinif = "tam" if (excel_var and oto_var) else ("kismi" if (excel_var or oto_var) else "yok")

            with col, st.container(key=f"ds_takvim_kart_{i}_{durum_sinif}"):
                st.markdown(
                    f'<div class="ds-takvim-baslik"><span>{isim[:3]}</span>'
                    f'<span class="mono">{gun.strftime("%d.%m")}</span></div>',
                    unsafe_allow_html=True,
                )
                excel_etiket = f"{'✅' if excel_var else '⬜'} {'Excel yüklendi' if excel_var else 'Excel yok'}"
                if st.button(excel_etiket, key=f"gun_btn_{gun_iso}_{'ok' if excel_var else 'no'}", use_container_width=True):
                    st.session_state.sayim_secili_gun = gun_iso
                    st.session_state.sayim_secili_tur = "excel"

                oto_etiket = f"{'🟢' if oto_var else '⚪'} {'Otomatik sayıldı' if oto_var else 'Sayılmadı'}"
                if st.button(oto_etiket, key=f"gun_oto_btn_{gun_iso}_{'ok' if oto_var else 'no'}", use_container_width=True):
                    st.session_state.sayim_secili_gun = gun_iso
                    st.session_state.sayim_secili_tur = "otomatik"

                not_mevcut = notlar.get(gun_iso, "")
                yeni_not = st.text_input("Not", value=not_mevcut, key=f"not_{gun_iso}", label_visibility="collapsed",
                                          placeholder="Not ekle...")
                if yeni_not != not_mevcut:
                    db.sayim_not_kaydet(gun_iso, yeni_not)

    st.markdown("---")
    secili_gun = st.session_state.sayim_secili_gun
    secili_tur = st.session_state.get("sayim_secili_tur", "excel")

    if not secili_gun:
        st.info("Yukarıdaki takvimden bir güne tıklayarak o günün sayım detayını görebilirsiniz.")
        return

    gun_str = datetime.fromisoformat(secili_gun).strftime("%d.%m.%Y")

    c_detay_baslik, c_detay_kapat = st.columns([6, 1])
    c_detay_baslik.markdown(f"**{gun_str} — Sayım Detayı**")
    if c_detay_kapat.button("✕ Kapat", key="sayim_detay_kapat_btn"):
        st.session_state.sayim_secili_gun = None
        st.rerun()

    if secili_tur == "otomatik":
        otomatik = gun_otomatik_sayimlar.get(secili_gun, db.stok_sayim_oturumlari_getir(secili_gun))
        if not otomatik:
            st.info(f"{gun_str} için Stok Sayım'dan gelen bir otomatik sayım yok.")
        else:
            # O gün Depo Sayım Fişleri'ne excel yüklenmişse, otomatik sayımın
            # güncel stok/fark değerleri o excel'deki stok kaynağıyla
            # eşleştirilir (görüntüde - kayıtlı veri değişmiyor).
            gun_stok_override = _depo_sayim_gun_stok_haritasi(secili_gun)
            if gun_stok_override:
                st.caption(f"📊 Karşılaştırma kaynağı: {gun_str} tarihinde Depo Sayım Fişleri'ne yüklenen excel'deki stok değerleri.")

            st.markdown(f"**{gun_str} — Sayım Özeti**")
            ozet_df = _sayim_ozet_df(otomatik, stok_override=gun_stok_override)
            if not ozet_df.empty:
                st.dataframe(
                    ozet_df.style.apply(_sayim_ozet_renklendir, axis=1),
                    use_container_width=True, height=320, hide_index=True,
                )
                st.caption("🟢 Doğru sayıldı · 🔴 Sayım stokla uyuşmuyor · 🔵 Önce yanlış sayılıp sonra düzeltildi")

            st.markdown(f"**{gun_str} — Stok Sayım'dan gelen otomatik sayımlar:**")
            for oturum in otomatik:
                personel_str = f" — {oturum['personel_adi']}" if oturum.get("personel_adi") else ""
                c_baslik, c_sil = st.columns([6, 1])
                c_baslik.caption(f"🔢 Sayım #{oturum['id']}{personel_str}")
                if c_sil.button("🗑 Sil", key=f"oto_sayim_sil_{oturum['id']}"):
                    db.stok_sayim_oturumu_sil(oturum["id"])
                    st.rerun()
                detaylar = _detaylar_override_uygula(db.stok_sayim_detay_getir(oturum["id"]), gun_stok_override)
                if not detaylar:
                    st.write("Bu sayımda kayıtlı ürün yok.")
                else:
                    df_detay = pd.DataFrame(detaylar)[["urun_adi", "guncel_stok", "sayilan", "fark"]]
                    df_detay.columns = ["Ürün Adı", "Güncel Stok", "Sayılan", "Fark"]

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
        # Kaynak önceliği: 1) BUGÜN Depo Sayım Fişleri'ne yüklenen excel varsa
        # o (otomatik sayım, o günkü resmi stok kaynağıyla eşleşsin diye),
        # 2) yoksa "Excel ile Stok Sayım"dan en son yüklenen dosya,
        # 3) o da yoksa canlı XML kaynağı.
        bugun_iso = date.today().isoformat()
        gunluk_urunler = _depo_sayim_gun_urun_listesi(bugun_iso)
        if gunluk_urunler is not None:
            st.caption(
                f"📥 Kaynak: bugün ({date.today().strftime('%d.%m.%Y')}) Depo Sayım Fişleri'ne yüklenen excel "
                "— güncel stok karşılaştırması bu dosyadaki değerlerden yapılıyor."
            )
            _stok_sayim_bolumu(gunluk_urunler, anahtar_onek="sayim")
        else:
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

    # Aynı gün içindeki taslağı veritabanında tutan anahtar - sayım sırasında
    # telefon çalıp Streamlit bağlantısı kopup session_state sıfırlansa bile
    # (mobilde sekme arka planda öldürülünce olan buydu) sayfa yeniden
    # açıldığında bu anahtardan kaldığı yerden devam edilebiliyor.
    oturum_anahtari = f"{anahtar_onek}_{date.today().isoformat()}"

    girisler_key = f"{anahtar_onek}_girisler"
    editor_key_key = f"{anahtar_onek}_editor_key"
    if girisler_key not in st.session_state:
        # Önce veritabanındaki taslağı geri yükle (bağlantı kopması sonrası
        # kurtarma) - hiç taslak yoksa (ilk kez sayım başlıyor) boş sözlük.
        try:
            taslak_satirlar = db.stok_sayim_taslak_getir(oturum_anahtari)
        except Exception:
            taslak_satirlar = []
        st.session_state[girisler_key] = {
            t["urun_adi"]: {"Sayım": t.get("sayim") or "", "Personel": t.get("personel") or ""}
            for t in taslak_satirlar if t.get("sayim") not in (None, "")
        }
        if taslak_satirlar:
            st.info(f"Kaydedilmemiş {len(st.session_state[girisler_key])} ürünlük bir sayım taslağı bulundu, kaldığınız yerden devam edebilirsiniz.")
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
    # düğmesinden atanıyor - burada mevcut değeri koru. Değişen her satır
    # AYNI ANDA veritabanına da (taslak olarak) yazılıyor ki bağlantı kopsa
    # bile veri kaybolmasın - sadece GERÇEKTEN değişen satırlar için (her
    # sayfa yenilemesinde tüm satırları yeniden yazmamak için).
    for _, row in edited.iterrows():
        urun = row["Ürün Adı"]
        sayim_deger = row["Sayım"]
        sayim_dolu = str(sayim_deger).strip() not in ("", "nan", "None")
        mevcut_personel = girisler.get(urun, {}).get("Personel", "")
        onceki_sayim = girisler.get(urun, {}).get("Sayım")
        degisti = (sayim_dolu and sayim_deger != onceki_sayim) or (not sayim_dolu and urun in girisler)
        if sayim_dolu or mevcut_personel:
            girisler[urun] = {"Sayım": sayim_deger, "Personel": mevcut_personel}
        elif urun in girisler:
            del girisler[urun]
        if degisti:
            try:
                db.stok_sayim_taslak_kaydet(oturum_anahtari, urun, sayim_deger if sayim_dolu else None, mevcut_personel)
            except Exception:
                pass

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
                    try:
                        db.stok_sayim_taslak_kaydet(oturum_anahtari, urun, deger.get("Sayım"), secilen_personel)
                    except Exception:
                        pass
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
            try:
                db.stok_sayim_taslak_temizle(oturum_anahtari)
            except Exception:
                pass
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

    baslik = f"{iade['urun_adi']} ({iade.get('adet') or '?'} adet)"
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

    # Seri numaraları AYRI SATIRLARDA (virgülle değil) - kopyalayıp başka bir
    # programa yapıştırırken alt alta olması gerekiyor. st.code kutusunun
    # sağ üstünde otomatik bir kopyala düğmesi olduğu için bu amaca uygun.
    seriler = [s.strip() for s in (iade.get("seri_numaralari") or "").splitlines() if s.strip()]
    if seriler:
        st.caption(f"Seri numaraları ({len(seriler)} adet):")
        st.code("\n".join(seriler), language=None)

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

    # Firma bazlı grupla (her firma tıklanınca açılıp kapanan bir şablon),
    # firma içinde de tarihe göre (o firmadan hangi gün ne geldiği ayrı ayrı
    # görünsün diye) - "11 Ağustos'taki Algatech iadesi" gibi.
    firma_gruplari = {}
    for iade in iadeler:
        firma_gruplari.setdefault(iade["firma_adi"], {}).setdefault(iade.get("tarih") or "", []).append(iade)

    for firma, tarih_gruplari in firma_gruplari.items():
        tum_satirlar = [i for satirlar in tarih_gruplari.values() for i in satirlar]
        toplam_urun = len(tum_satirlar)
        bekleyen = sum(1 for i in tum_satirlar if i.get("durum") != "Kabul Edildi")
        baslik = f"🏢 {firma}  —  {toplam_urun} ürün" + (f", {bekleyen} bekliyor" if bekleyen else "")
        with st.expander(baslik):
            for tarih_iso in sorted(tarih_gruplari.keys(), reverse=True):
                satirlar = tarih_gruplari[tarih_iso]
                try:
                    g = date.fromisoformat(tarih_iso)
                    tarih_okunur = f"{g.day} {_KL_AY_ISIMLERI[g.month - 1]} {g.year}"
                except ValueError:
                    tarih_okunur = tarih_iso or "Tarihsiz"
                st.markdown(f"**{tarih_okunur} tarihli {firma} iadesi** ({len(satirlar)} ürün)")
                for iade in satirlar:
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

    secili_gun = st.session_state.kl_secili_gun
    secili_gun_obj = date.fromisoformat(secili_gun)

    # --- Gezinme: dün / bugün / tarihe git / yarın ---
    nav1, nav2, nav3, nav4 = st.columns([1, 1, 2, 1])
    if nav1.button("◀ Dün", key="kl_nav_dun", use_container_width=True):
        st.session_state.kl_secili_gun = (secili_gun_obj - timedelta(days=1)).isoformat()
        st.rerun()
    if nav2.button("Bugün", key="kl_nav_bugun", use_container_width=True):
        st.session_state.kl_secili_gun = date.today().isoformat()
        st.rerun()
    secilen_tarih = nav3.date_input(
        "Tarihe git", value=secili_gun_obj, key=f"kl_tarih_sec_{secili_gun}", label_visibility="collapsed",
    )
    if secilen_tarih.isoformat() != secili_gun:
        st.session_state.kl_secili_gun = secilen_tarih.isoformat()
        st.rerun()
    if nav4.button("Yarın ▶", key="kl_nav_yarin", use_container_width=True):
        st.session_state.kl_secili_gun = (secili_gun_obj + timedelta(days=1)).isoformat()
        st.rerun()

    ozet = _kl_gun_ozet(secili_gun)
    leaf_key = f"kl_leaf_{secili_gun}" + ("_yesil" if ozet["tumu_tamam"] else "")

    with st.container(key=leaf_key):
        st.markdown(_kl_leaf_markup(secili_gun), unsafe_allow_html=True)
        _kl_leaf_govde(ozet, anahtar_onek="kl")

    st.markdown("**Not ekle**")
    with st.form("kl_yeni_form", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        madde = c1.text_input("Kontrol edilecek iş / not")
        kapsam = c2.selectbox(
            "Hangi güne(lere) eklensin?",
            ["Sadece bu gün", "Bu haftanın her gününe ata", "Bu ayın her gününe ata"],
        )
        if st.form_submit_button("➕ Ekle") and madde:
            if kapsam == "Bu haftanın her gününe ata":
                hafta_baslangic = secili_gun_obj - timedelta(days=secili_gun_obj.weekday())
                gunler = [hafta_baslangic + timedelta(days=i) for i in range(7)]
            elif kapsam == "Bu ayın her gününe ata":
                gun_sayisi_ay = calendar.monthrange(secili_gun_obj.year, secili_gun_obj.month)[1]
                gunler = [date(secili_gun_obj.year, secili_gun_obj.month, g) for g in range(1, gun_sayisi_ay + 1)]
            else:
                gunler = [secili_gun_obj]
            for g in gunler:
                db.kontrol_maddesi_ekle(g.isoformat(), madde)
            st.rerun()

    st.markdown("---")
    st.markdown("**Aylık genel görünüm**")
    col1, col2 = st.columns(2)
    yil = col1.number_input("Yıl", min_value=2024, max_value=2100, value=secili_gun_obj.year, key="kl_yil")
    ay = col2.selectbox("Ay", list(range(1, 13)), index=secili_gun_obj.month - 1,
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
            tamam_mi = bool(sayac) and sayac["toplam"] > 0 and sayac["tamam"] == sayac["toplam"]
            kutu_key = f"kl_gun_kutu_{gun_iso}" + ("_yesil" if tamam_mi else "")
            with col:
                with st.container(key=kutu_key):
                    if st.button(etiket, key=f"kl_gun_{gun_iso}", use_container_width=True):
                        st.session_state.kl_secili_gun = gun_iso
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
