# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
import io

import data
import db
import excel_utils

st.set_page_config(page_title="KAMTEK DEPO", layout="wide", initial_sidebar_state="collapsed")
db.init_db()

# ------------------------------------------------------------------
# Ortak stil
# ------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stToolbar"] {visibility: hidden;}

div[data-testid="column"]:nth-of-type(1) button {
    background-color: #E6F1FB !important; border: none !important; border-radius: 20px !important;
    height: 150px !important; font-size: 20px !important; font-weight: 600 !important; color: #0C447C !important;
}
div[data-testid="column"]:nth-of-type(2) button {
    background-color: #FAEEDA !important; border: none !important; border-radius: 20px !important;
    height: 150px !important; font-size: 20px !important; font-weight: 600 !important; color: #854F0B !important;
}
div[data-testid="column"]:nth-of-type(3) button {
    background-color: #EAF3DE !important; border: none !important; border-radius: 20px !important;
    height: 150px !important; font-size: 20px !important; font-weight: 600 !important; color: #27500A !important;
}
div[data-testid="column"]:nth-of-type(4) button {
    background-color: #FAECE7 !important; border: none !important; border-radius: 20px !important;
    height: 150px !important; font-size: 20px !important; font-weight: 600 !important; color: #993C1D !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Şifreli giriş (herkes için ortak şifre)
# ------------------------------------------------------------------
SIFRE = st.secrets.get("SITE_SIFRE", "kamtek2026")

if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

if not st.session_state.giris_yapildi:
    st.markdown("<h1 style='text-align:center; margin-top:80px;'>KAMTEK DEPO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        girilen = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if girilen == SIFRE:
                st.session_state.giris_yapildi = True
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


# ------------------------------------------------------------------
# ANA SAYFA
# ------------------------------------------------------------------
def sayfa_home():
    col_logo = st.columns([1, 2, 1])
    with col_logo[1]:
        st.markdown(
            "<div style='opacity:0.12; text-align:center; margin-bottom:-60px;'>",
            unsafe_allow_html=True,
        )
        try:
            st.image("assets/kamtek_logo.png", use_container_width=True)
        except Exception:
            pass
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h1 style='text-align:center; font-size:56px; margin-top:0;'>KAMTEK DEPO</h1>", unsafe_allow_html=True)
    st.write("")
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🗺️\n\nSevkiyat Planlama", use_container_width=True, key="kart1"):
            git("sevkiyat")
    with c2:
        if st.button("🚚\n\nKargo Takip", use_container_width=True, key="kart2"):
            git("kargotakip")
    with c3:
        if st.button("📦\n\nDepo", use_container_width=True, key="kart3"):
            git("depo")
    with c4:
        if st.button("🏷️\n\nKargo Fiyat Listesi", use_container_width=True, key="kart4"):
            git("fiyatlistesi")


# ------------------------------------------------------------------
# SEVKİYAT PLANLAMA
# ------------------------------------------------------------------
def sayfa_sevkiyat():
    geri_butonu()
    st.header("Sevkiyat Planlama")

    col_map, col_bosluk = st.columns([1, 1])
    with col_map:
        secili_il = st.selectbox("Varış İli", data.IL_LISTESI, index=data.IL_LISTESI.index("İZMİR"))
        try:
            import plotly.express as px
            import requests
            geojson_url = "https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/tr-cities-utf8.json"
            geojson = requests.get(geojson_url, timeout=5).json()
            df_map = pd.DataFrame({"il": data.IL_LISTESI})
            df_map["secili"] = df_map["il"].apply(lambda x: 1 if x == secili_il else 0)
            fig = px.choropleth(
                df_map, geojson=geojson, locations="il", featureidkey="properties.name",
                color="secili", color_continuous_scale=["#E6F1FB", "#378ADD"],
                scope=None,
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Harita görseli için internet bağlantısı gerekiyor (Streamlit Cloud'da otomatik yüklenecektir).")

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

    if st.button("Hesapla", type="primary"):
        gecerli_satirlar = [
            (row["Miktar"], row["Desi"]) for _, row in edited.iterrows()
            if pd.notna(row["Miktar"]) and pd.notna(row["Desi"]) and row["Miktar"] > 0 and row["Desi"] > 0
        ]
        if not gecerli_satirlar:
            st.warning("Lütfen en az bir satıra miktar ve desi girin.")
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
            else:
                st.markdown(f"**{secili_il} için hesaplanan fiyatlar:**")
                cols = st.columns(len(sonuclar))
                for col, (kargo, toplam) in zip(cols, sonuclar):
                    with col:
                        st.metric(kargo, f"{toplam:,.2f} TL (+ KDV)")


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
        st.dataframe(df_goster, use_container_width=True, height=450)
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
    secili_tarih = st.date_input("Sayım Tarihi", value=date.today(), key="sayim_tarih")

    yuklenen = st.file_uploader("Sayım Excel Dosyasını Yükleyin", type=["xls", "xlsx"], key="sayim_uploader")
    if yuklenen is not None:
        db.depo_sayim_kaydet(secili_tarih.isoformat(), yuklenen.name, yuklenen.getvalue())
        st.success(f"{yuklenen.name} kaydedildi.")

    kayitlar = db.depo_sayim_getir(secili_tarih.isoformat())
    if kayitlar:
        st.write(f"{secili_tarih.strftime('%d.%m.%Y')} tarihine ait kayıtlı sayım dosyaları:")
        for k in kayitlar:
            st.download_button(
                label=f"⬇ {k['dosya_adi']}",
                data=k["dosya_icerik"],
                file_name=k["dosya_adi"],
                key=f"indir_{k['id']}",
            )
    else:
        st.info("Bu tarih için henüz sayım dosyası yok.")


def depo_temizlik_bolumu():
    st.subheader("Depo Temizlik Çizelgesi")
    bugun = date.today()
    col1, col2 = st.columns(2)
    with col1:
        yil = st.number_input("Yıl", min_value=2024, max_value=2100, value=bugun.year, step=1)
    with col2:
        ay = st.selectbox("Ay", list(range(1, 13)), index=bugun.month - 1, format_func=lambda x: calendar.month_name[x])

    mevcut = db.temizlik_getir_ay(yil, ay)
    gun_sayisi = calendar.monthrange(yil, ay)[1]

    gunler = [f"{yil:04d}-{ay:02d}-{g:02d}" for g in range(1, gun_sayisi + 1)]
    df = pd.DataFrame({
        "Tarih": gunler,
        "Temizlik Yapan Personel": [mevcut.get(g, "") for g in gunler],
    })

    edited = st.data_editor(df, use_container_width=True, height=500, disabled=["Tarih"], key="temizlik_editor")

    if st.button("Kaydet", type="primary"):
        for _, row in edited.iterrows():
            db.temizlik_kaydet(row["Tarih"], row["Temizlik Yapan Personel"])
        st.success("Temizlik çizelgesi kaydedildi.")


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
            try:
                st.image(cfg["logo"], use_container_width=True)
            except Exception:
                st.write(f"**{kargo}**")
            tarife_df = pd.DataFrame(cfg["tiers"], columns=["Alt Desi", "Üst Desi", "Tutar (+ KDV)"])
            st.dataframe(tarife_df, use_container_width=True, hide_index=True)
            if cfg["artan_desi"] is not None:
                st.caption(f"Aralık üstü: desi başına +{cfg['artan_desi']} TL (+ KDV)")
            if cfg["iller"] != "ALL":
                st.caption("Sadece şu illere gönderim yapar: " + ", ".join(cfg["iller"]))
            else:
                st.caption("Tüm illere gönderim yapar.")


# ------------------------------------------------------------------
# YÖNLENDİRME
# ------------------------------------------------------------------
SAYFALAR = {
    "home": sayfa_home,
    "sevkiyat": sayfa_sevkiyat,
    "kargotakip": sayfa_kargotakip,
    "depo": sayfa_depo,
    "fiyatlistesi": sayfa_fiyatlistesi,
}

SAYFALAR[st.session_state.sayfa]()
