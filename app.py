# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import io
import base64

import data
import db
import excel_utils
import stok_utils

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
            st.image("kamtek_logo.png", use_container_width=True)
        except Exception:
            pass
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h1 style='text-align:center; font-size:56px; margin-top:0;'>KAMTEK DEPO</h1>", unsafe_allow_html=True)
    st.write("")

    st.markdown("<p style='color:var(--text-secondary,#666); font-size:13px; font-weight:500; margin-bottom:4px;'>Sevkiyat ve kargo</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(key="kart1"):
            if st.button("🗺️\n\nSevkiyat Planlama", use_container_width=True):
                git("sevkiyat")
    with c2:
        with st.container(key="kart2"):
            if st.button("🚚\n\nKargo Takip", use_container_width=True):
                git("kargotakip")
    with c3:
        with st.container(key="kart4"):
            if st.button("🏷️\n\nKargo Fiyat Listesi", use_container_width=True):
                git("fiyatlistesi")
    with c4:
        with st.container(key="kart5"):
            if st.button("✅\n\nTamamlanmış Kargolar", use_container_width=True):
                git("tamamlanankargolar")

    st.write("")
    st.markdown("<p style='color:var(--text-secondary,#666); font-size:13px; font-weight:500; margin-bottom:4px;'>Depo ve stok</p>", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        with st.container(key="kart3"):
            if st.button("📦\n\nDepo", use_container_width=True):
                git("depo")
    with c6:
        with st.container(key="kart6"):
            if st.button("📊\n\nStok Takip", use_container_width=True):
                git("stoktakip")
    with c7:
        with st.container(key="kart8"):
            if st.button("↩️\n\nİade", use_container_width=True):
                git("iade")
    with c8:
        with st.container(key="kart11"):
            if st.button("☑️\n\nKontrol Listesi", use_container_width=True):
                git("kontrollistesi")

    st.write("")
    st.markdown("<p style='color:var(--text-secondary,#666); font-size:13px; font-weight:500; margin-bottom:4px;'>Yönetim</p>", unsafe_allow_html=True)
    yonetim_kartlari = []
    if st.session_state.rol in IK_GORME_YETKISI:
        yonetim_kartlari.append(("kart7", "👥\n\nİnsan Kaynakları", "insankaynaklari"))
    yonetim_kartlari.append(("kart9", "🗓️\n\nPlanlama", "planlama"))
    yonetim_kartlari.append(("kart10", "🔔\n\nBildirim", "bildirim"))
    cols_y = st.columns(4)
    for col, (key, etiket, hedef) in zip(cols_y, yonetim_kartlari):
        with col:
            with st.container(key=key):
                if st.button(etiket, use_container_width=True):
                    git(hedef)


# ------------------------------------------------------------------
# SEVKİYAT PLANLAMA
# ------------------------------------------------------------------
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
            import requests
            import excel_utils as _eu

            geojson_url = "https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/geo/tr-cities-utf8.json"
            geojson = requests.get(geojson_url, timeout=8).json()

            # geojson'daki il isimleri bizim ALL-CAPS listemizle birebir eşleşmiyor
            # (örn. "İstanbul", "Afyon"), bu yüzden normalize ederek eşleştiriyoruz.
            EK_ESLESTIRME = {"AFYONKARAHİSAR": "AFYON", "MERSİN": "İÇEL"}

            def norm_il(s):
                s = EK_ESLESTIRME.get(s.upper(), s.upper())
                return _eu.norm(s)

            geojson_isim_haritasi = {norm_il(f["properties"]["name"]): f["properties"]["name"] for f in geojson["features"]}
            norm_to_il = {norm_il(il): il for il in data.IL_LISTESI}
            gercek_isim = geojson_isim_haritasi.get(norm_il(secili_il))

            if gercek_isim is None:
                st.info(f"{secili_il} haritada bulunamadı, sadece il seçimiyle devam edebilirsiniz.")
            else:
                tum_isimler = [f["properties"]["name"] for f in geojson["features"]]
                df_map = pd.DataFrame({"il": tum_isimler})
                df_map["secili"] = df_map["il"].apply(lambda x: 1 if x == gercek_isim else 0)

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

                lons, lats, texts, sizes = [], [], [], []
                for f in geojson["features"]:
                    cx, cy, w, h = _il_centroid_bbox(f)
                    lons.append(cx)
                    lats.append(cy)
                    texts.append(f["properties"]["name"])
                    # küçük illerde küçük, büyük illerde biraz daha büyük yazı - sınırı taşmasın diye
                    alan = w * h
                    sizes.append(max(5, min(10, alan * 350)))

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
                        eslesen_il = norm_to_il.get(norm_il(loc))
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
    for col, gun, isim in zip(gun_cols, hafta_gunleri, gun_isimleri):
        with col:
            kayitlar = db.depo_sayim_getir(gun.isoformat())
            gun_dosyalari[gun.isoformat()] = kayitlar
            tik = "✅" if kayitlar else "⬜"
            etiket = f"{tik}\n{gun.strftime('%d.%m')}"
            if st.button(etiket, key=f"gun_btn_{gun.isoformat()}", use_container_width=True):
                st.session_state.sayim_secili_gun = gun.isoformat()
            not_mevcut = notlar.get(gun.isoformat(), "")
            yeni_not = st.text_input("Not", value=not_mevcut, key=f"not_{gun.isoformat()}", label_visibility="collapsed",
                                      placeholder="Not ekle...")
            if yeni_not != not_mevcut:
                db.sayim_not_kaydet(gun.isoformat(), yeni_not)

    st.markdown("---")
    secili_gun = st.session_state.sayim_secili_gun
    if secili_gun:
        kayitlar = gun_dosyalari.get(secili_gun, db.depo_sayim_getir(secili_gun))
        gun_str = datetime.fromisoformat(secili_gun).strftime("%d.%m.%Y")
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
    else:
        st.info("Yukarıdaki takvimden bir güne tıklayarak o günün sayım detayını görebilirsiniz.")


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
@st.cache_data(ttl=1800, show_spinner=False)
def _stok_verisi_cache():
    return stok_utils.stok_verisini_getir()


def sayfa_stoktakip():
    geri_butonu()
    st.header("Stok Takip")
    st.caption(
        "DIA'dan internet satış sitesine beslenen ürün/stok verisi — kaynak yaklaşık 2 saatte bir "
        "güncelleniyor, burada en fazla 30 dakika önbelleklenir."
    )

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
                               placeholder="Ürün adı, stok kodu veya marka ara...")
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
    st.header("İnsan Kaynakları")

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
        yas = st.text_input("Yaş", key="yeni_p_yas")
        telefon = st.text_input("Telefon", key="yeni_p_tel")
        foto = st.file_uploader("Fotoğraf", type=["jpg", "jpeg", "png"], key="yeni_p_foto")
        if st.button("Kaydet", key="yeni_p_kaydet"):
            if not ad_soyad:
                st.warning("Ad soyad girin.")
            else:
                db.personel_ekle(ad_soyad, yas, telefon, foto.getvalue() if foto else None)
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
            st.markdown(
                f"<p style='text-align:center;font-size:12px;color:#666;'>Yaş: {p.get('yas') or '-'} · {p.get('telefon') or '-'}</p>",
                unsafe_allow_html=True,
            )
            with st.popover("📁 Özlük Sayfası", use_container_width=True):
                _ozluk_sayfasi(p["id"], p["ad_soyad"])
            if st.button("🗑 Sil", key=f"personel_sil_{p['id']}", use_container_width=True):
                db.personel_sil(p["id"])
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
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        c1.write(p["ad_soyad"])
        giris = c2.text_input("Giriş", value=kayit.get("giris_saati") or "", key=f"giris_{p['id']}_{tarih_iso}", placeholder="08:00")
        cikis = c3.text_input("Çıkış", value=kayit.get("cikis_saati") or "", key=f"cikis_{p['id']}_{tarih_iso}", placeholder="17:30")
        sure_str = "-"
        if giris and cikis:
            try:
                g = datetime.strptime(giris, "%H:%M")
                c = datetime.strptime(cikis, "%H:%M")
                fark_dk = int((c - g).total_seconds() // 60)
                if fark_dk > 0:
                    saat, dk = divmod(fark_dk, 60)
                    sure_str = f"{saat}s {dk}d"
                    if data.is_resmi_tatil(tarih_iso):
                        mesai_dk = fark_dk  # resmi tatilde çalışılan sürenin tamamı mesai sayılır
                    else:
                        mesai_dk = max(0, fark_dk - 9 * 60)
                    if mesai_dk > 0:
                        ms, md = divmod(mesai_dk, 60)
                        sure_str += f" (mesai {ms}s {md}d)"
            except ValueError:
                sure_str = "geçersiz saat"
        c4.write(sure_str)
        if giris != (kayit.get("giris_saati") or "") or cikis != (kayit.get("cikis_saati") or ""):
            if giris or cikis:
                db.puantaj_kaydet(tarih_iso, p["id"], giris, cikis)

    st.markdown("---")
    st.markdown("**Aylık toplam**")
    col1, col2 = st.columns(2)
    yil = col1.number_input("Yıl", min_value=2024, max_value=2100, value=secili_tarih.year, key="puantaj_yil")
    ay = col2.selectbox("Ay", list(range(1, 13)), index=secili_tarih.month - 1,
                         format_func=lambda x: calendar.month_name[x], key="puantaj_ay")
    kayitlar_ay = db.puantaj_getir_ay(yil, ay)
    personel_haritasi = {p["id"]: p["ad_soyad"] for p in personeller}
    toplamlar = {}
    for k in kayitlar_ay:
        if not (k.get("giris_saati") and k.get("cikis_saati")):
            continue
        try:
            g = datetime.strptime(k["giris_saati"], "%H:%M")
            c = datetime.strptime(k["cikis_saati"], "%H:%M")
            fark_dk = int((c - g).total_seconds() // 60)
        except ValueError:
            continue
        if fark_dk <= 0:
            continue
        ad = personel_haritasi.get(k["personel_id"], "?")
        toplam_dk, mesai_dk_toplam = toplamlar.get(ad, (0, 0))
        toplam_dk += fark_dk
        if data.is_resmi_tatil(k["tarih"]):
            mesai_dk_toplam += fark_dk
        else:
            mesai_dk_toplam += max(0, fark_dk - 9 * 60)
        toplamlar[ad] = (toplam_dk, mesai_dk_toplam)

    if not toplamlar:
        st.caption("Bu ay için kayıt yok.")
    else:
        cols = st.columns(min(4, len(toplamlar)))
        for i, (ad, (toplam_dk, mesai_dk)) in enumerate(toplamlar.items()):
            with cols[i % len(cols)]:
                st.metric(ad, f"{toplam_dk // 60} saat", f"{mesai_dk // 60} saat mesai")


# ------------------------------------------------------------------
# İADE
# ------------------------------------------------------------------
def sayfa_iade():
    geri_butonu()
    st.header("İade")
    st.caption("Firmalardan gelen iadeler faturası kabul edilene kadar burada takip edilir.")

    with st.expander("➕ Yeni iade ekle"):
        firma = st.text_input("Firma / Müşteri Adı", key="iade_firma")
        urun = st.text_input("Ürün Adı", key="iade_urun")
        adet = st.text_input("Adet", key="iade_adet")
        tarih_g = st.date_input("Tarih", value=date.today(), key="iade_tarih")
        seri_no = st.text_area("Seri Numaraları (her satıra bir tane)", key="iade_seri", height=120)
        if st.button("Ekle", key="iade_ekle_btn"):
            if not firma or not urun:
                st.warning("Firma ve ürün adı girin.")
            else:
                db.iade_ekle(firma, urun, seri_no, adet, tarih_g.isoformat())
                st.success("İade eklendi.")
                st.rerun()

    iadeler = db.iadeler_getir()
    if not iadeler:
        st.info("Henüz iade kaydı yok.")
        return

    for iade in iadeler:
        durum = iade.get("durum", "Bekliyor")
        renk = "#EAF3DE" if durum == "Kabul Edildi" else "#FAEEDA"
        yazi_renk = "#27500A" if durum == "Kabul Edildi" else "#854F0B"
        with st.expander(f"{iade['firma_adi']} — {iade['urun_adi']} ({iade.get('adet') or '?'} adet) — {iade.get('tarih') or ''}"):
            st.markdown(
                f"<span style='background:{renk};color:{yazi_renk};font-size:12px;padding:3px 8px;border-radius:6px;'>{durum}</span>",
                unsafe_allow_html=True,
            )
            seriler = [s.strip() for s in (iade.get("seri_numaralari") or "").splitlines() if s.strip()]
            if seriler:
                st.markdown("**Seri numaraları:**")
                st.write(", ".join(seriler))
            c1, c2 = st.columns(2)
            if durum != "Kabul Edildi":
                if c1.button("✓ Kabul Edildi olarak işaretle", key=f"iade_kabul_{iade['id']}"):
                    db.iade_durum_guncelle(iade["id"], "Kabul Edildi")
                    st.rerun()
            else:
                if c1.button("↺ Bekliyor'a al", key=f"iade_bekliyor_{iade['id']}"):
                    db.iade_durum_guncelle(iade["id"], "Bekliyor")
                    st.rerun()
            if c2.button("🗑 Sil", key=f"iade_sil_{iade['id']}"):
                db.iade_sil(iade["id"])
                st.rerun()


# ------------------------------------------------------------------
# PLANLAMA
# ------------------------------------------------------------------
def sayfa_planlama():
    geri_butonu()
    st.header("Planlama")

    if "planlama_alt_sayfa" not in st.session_state:
        st.session_state.planlama_alt_sayfa = "gorevler"
    c1, c2 = st.columns(2)
    with c1:
        with st.container(key="pl_kart_gorevler"):
            if st.button("📝\n\nGünlük İşler", use_container_width=True):
                st.session_state.planlama_alt_sayfa = "gorevler"
    with c2:
        with st.container(key="pl_kart_transfer"):
            if st.button("🔁\n\nDepolar Arası Transfer", use_container_width=True):
                st.session_state.planlama_alt_sayfa = "transfer"

    st.markdown("---")
    if st.session_state.planlama_alt_sayfa == "gorevler":
        _planlama_gorevler_bolumu()
    else:
        _depo_transfer_bolumu()


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


def _depo_transfer_bolumu():
    st.caption("Giriş Katı personeli, Alsancak deposundan istediği ürünler için burada bir talep açar.")
    with st.form("yeni_transfer_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        talep_eden = c1.selectbox("Talep eden depo", ["Giriş Katı", "Alsancak"])
        hedef = c2.selectbox("Hedef depo (ürünün geleceği yer)", ["Alsancak", "Giriş Katı"])
        urun = st.text_input("Ürün / açıklama")
        adet = st.text_input("Adet")
        ne_zaman = st.text_input("Ne zaman gelmesini istiyorsunuz? (açıklama)", placeholder="Örn. bugün öğleden sonra")
        if st.form_submit_button("📣 Çağrıda bulun") and urun:
            db.transfer_talebi_ekle(talep_eden, hedef, urun, adet, ne_zaman)
            st.success("Talep oluşturuldu, Bildirim ekranına düştü.")
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
def sayfa_bildirim():
    geri_butonu()
    st.header("Bildirim")

    bugun_iso = date.today().isoformat()
    simdi_saat = datetime.now().strftime("%H:%M")

    bekleyen_gorevler = db.gorevler_getir_bekleyen_bildirim(bugun_iso, simdi_saat)
    if bekleyen_gorevler:
        st.markdown("**⏰ Zamanı gelen planlanan işler**")
        for g in bekleyen_gorevler:
            st.warning(f"{g.get('saat') or ''} — {g['aciklama']}")

    transfer_talepleri = db.transfer_talepleri_getir("Bekliyor")
    if transfer_talepleri:
        st.markdown("**🔁 Bekleyen depo transfer çağrıları**")
        for t in transfer_talepleri:
            not_metni = f" ({t['istenen_zaman_aciklama']})" if t.get("istenen_zaman_aciklama") else ""
            st.info(f"{t['talep_eden_depo']} → {t['hedef_depo']}: {t['urun_aciklama']} ({t.get('adet') or '?'} adet){not_metni}")

    if not bekleyen_gorevler and not transfer_talepleri:
        st.info("Şu an bekleyen bir bildirim yok.")


# ------------------------------------------------------------------
# KONTROL LİSTESİ
# ------------------------------------------------------------------
def sayfa_kontrollistesi():
    geri_butonu()
    st.header("Kontrol Listesi")

    secili_tarih = st.date_input("Tarih", value=date.today(), key="kl_tarih")
    tarih_iso = secili_tarih.isoformat()

    with st.form("yeni_kontrol_form", clear_on_submit=True):
        madde = st.text_input("Kontrol edilecek iş")
        if st.form_submit_button("➕ Ekle") and madde:
            db.kontrol_maddesi_ekle(tarih_iso, madde)
            st.rerun()

    maddeler = db.kontrol_listesi_getir(tarih_iso)
    if not maddeler:
        st.info(f"{secili_tarih.strftime('%d.%m.%Y')} için henüz madde eklenmedi.")
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
}

SAYFALAR[st.session_state.sayfa]()
