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
.st-key-kart1 button, .st-key-kart1 button *,
.st-key-kart2 button, .st-key-kart2 button *,
.st-key-kart3 button, .st-key-kart3 button *,
.st-key-kart4 button, .st-key-kart4 button *,
.st-key-kart5 button, .st-key-kart5 button * {
    font-size: 48px !important;
}
.st-key-kartplan button {
    background-color: #F1E9FB !important; border: none !important; border-radius: 32px !important;
    height: 130px !important; font-weight: 700 !important; color: #5B2A86 !important;
    line-height: 1.4 !important; width: 100% !important; font-size: 30px !important;
}
.st-key-kartplan button * { font-size: 30px !important; }
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
    st.write("")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        with st.container(key="kart1"):
            if st.button("🗺️\n\nSevkiyat Planlama", use_container_width=True):
                git("sevkiyat")
    with c2:
        with st.container(key="kart2"):
            if st.button("🚚\n\nKargo Takip", use_container_width=True):
                git("kargotakip")
    with c3:
        with st.container(key="kart3"):
            if st.button("📦\n\nDepo", use_container_width=True):
                git("depo")
    with c4:
        with st.container(key="kart4"):
            if st.button("🏷️\n\nKargo Fiyat Listesi", use_container_width=True):
                git("fiyatlistesi")
    with c5:
        with st.container(key="kart5"):
            if st.button("✅\n\nTamamlanmış Kargolar", use_container_width=True):
                git("tamamlanankargolar")


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
                df_plan = pd.DataFrame(mevcut)[["musteri_adi", "alici_adresi", "koli_adedi", "planlanan_tarih"]]
            else:
                df_plan = pd.DataFrame({"musteri_adi": [""] * 8, "alici_adresi": [""] * 8,
                                         "koli_adedi": [""] * 8, "planlanan_tarih": [""] * 8})
            df_plan.columns = ["Müşteri Adı", "Alıcı Adres", "Koli Adedi", "Planlanan Tarih"]
            edited_plan = st.data_editor(
                df_plan, use_container_width=True, num_rows="dynamic", key="planlanan_editor", height=350,
            )
            if st.button("Kaydet", key="planlanan_kaydet"):
                satirlar = [
                    {
                        "musteri_adi": row["Müşteri Adı"], "alici_adresi": row["Alıcı Adres"],
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
    yuklenen = st.file_uploader("Sayım Excel Dosyasını Yükleyin", type=["xls", "xlsx"], key="sayim_uploader")
    if yuklenen is not None:
        db.depo_sayim_kaydet(secili_tarih.isoformat(), yuklenen.name, yuklenen.getvalue())
        st.success(f"{yuklenen.name} kaydedildi ({secili_tarih.strftime('%d.%m.%Y')}).")

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
            for k in kayitlar:
                st.caption(f"📄 {k['dosya_adi']}")
                try:
                    filtreli = excel_utils.sayim_satirlarini_filtrele(io.BytesIO(k["dosya_icerik"]))
                    if filtreli.empty:
                        hata = filtreli.attrs.get("hata")
                        st.write(hata if hata else "Bu dosyada 'Sayım' sütunu bulunamadı ya da sayılmış satır yok.")
                    else:
                        st.dataframe(filtreli, use_container_width=True)
                except Exception as e:
                    st.error(f"Dosya okunurken hata oluştu: {e}")
                st.download_button(
                    label=f"⬇ {k['dosya_adi']} indir", data=k["dosya_icerik"],
                    file_name=k["dosya_adi"], key=f"indir_{k['id']}",
                )
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
        st.dataframe(df, use_container_width=True, height=450)

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
# YÖNLENDİRME
# ------------------------------------------------------------------
SAYFALAR = {
    "home": sayfa_home,
    "sevkiyat": sayfa_sevkiyat,
    "kargotakip": sayfa_kargotakip,
    "depo": sayfa_depo,
    "fiyatlistesi": sayfa_fiyatlistesi,
    "tamamlanankargolar": sayfa_tamamlanankargolar,
}

SAYFALAR[st.session_state.sayfa]()
