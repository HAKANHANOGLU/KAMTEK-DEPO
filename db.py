# -*- coding: utf-8 -*-
"""Supabase (Postgres) tabanlı kalıcı depolama katmanı.
Streamlit Cloud'un dosya sistemi kalıcı olmadığı için (uygulama zaman zaman
yeniden başlatılır/uyandırılır) veriler artık gerçek bir bulut veritabanında
(Supabase) tutuluyor - böylece bugün girilen veriler yarın da görünür."""
import base64
import json
from datetime import date, datetime

import requests
import streamlit as st

# Varsayılan değerler (proje oluşturulurken alındı). İstenirse Streamlit Cloud'da
# Settings > Secrets kısmına SUPABASE_URL / SUPABASE_KEY eklenerek override edilebilir.
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://zfmfmqaqkeuvxkrafxoe.supabase.co")
SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmbWZtcWFxa2V1dnhrcmFmeG9lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMjA5MjYsImV4cCI6MjEwMTU5NjkyNn0.c0tJ2ghgqt57Wrq9otW7wQdGDwQFKxw_zs62XS1bHvw",
)

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}
_REST = f"{SUPABASE_URL}/rest/v1"


def init_db():
    """Tablolar Supabase tarafında zaten oluşturuldu, burada yapılacak bir şey yok."""
    pass


# ---------- Kargo Takip ----------

def kargo_takip_kaydet(tarih: str, kargo_firmasi: str, satirlar: list):
    now = date.today().isoformat()
    rows = [
        {
            "tarih": tarih,
            "kargo_firmasi": kargo_firmasi,
            "gonderi_tarihi": s.get("gonderi_tarihi"),
            "gonderi_no": s.get("gonderi_no"),
            "alici_adi": s.get("alici_adi"),
            "alici_adresi": s.get("alici_adresi"),
            "varis_il": s.get("varis_il"),
            "odeme_sekli": s.get("odeme_sekli"),
            "desi": s.get("desi"),
            "yuklenme_zamani": now,
        }
        for s in satirlar
    ]
    if not rows:
        return
    r = requests.post(f"{_REST}/kargo_takip", headers=_HEADERS, data=json.dumps(rows), timeout=15)
    r.raise_for_status()


def kargo_takip_getir(tarih: str):
    params = {"tarih": f"eq.{tarih}", "order": "kargo_firmasi,id"}
    r = requests.get(f"{_REST}/kargo_takip", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ---------- Depo Sayım ----------

def depo_sayim_kaydet(tarih: str, dosya_adi: str, dosya_bytes: bytes):
    now = date.today().isoformat()
    row = {
        "tarih": tarih,
        "dosya_adi": dosya_adi,
        "dosya_icerik_b64": base64.b64encode(dosya_bytes).decode(),
        "yuklenme_zamani": now,
    }
    r = requests.post(f"{_REST}/depo_sayim", headers=_HEADERS, data=json.dumps(row), timeout=30)
    r.raise_for_status()


def depo_sayim_getir(tarih: str):
    params = {
        "tarih": f"eq.{tarih}",
        "select": "id,dosya_adi,dosya_icerik_b64,yuklenme_zamani",
        "order": "id",
    }
    r = requests.get(f"{_REST}/depo_sayim", headers=_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    sonuc = []
    for row in r.json():
        sonuc.append({
            "id": row["id"],
            "dosya_adi": row["dosya_adi"],
            "dosya_icerik": base64.b64decode(row["dosya_icerik_b64"]),
            "yuklenme_zamani": row.get("yuklenme_zamani"),
        })
    return sonuc


def depo_sayim_getir_coklu(gunler: list):
    """depo_sayim_getir'in haftalık versiyonu - 7 ayrı istek yerine TEK
    istekle tüm günlerin dosyalarını çekip {tarih: [kayıt, ...]} olarak
    gruplar. Haftalık Durum Matrisi'ndeki her checkbox tıklamasında sayfa
    yeniden çalıştığı için bu tek istek gecikmeyi belirgin şekilde azaltır."""
    if not gunler:
        return {}
    tarih_listesi = ",".join(gunler)
    params = {
        "tarih": f"in.({tarih_listesi})",
        "select": "id,tarih,dosya_adi,dosya_icerik_b64,yuklenme_zamani",
        "order": "id",
    }
    r = requests.get(f"{_REST}/depo_sayim", headers=_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    sonuc = {g: [] for g in gunler}
    for row in r.json():
        sonuc.setdefault(row["tarih"], []).append({
            "id": row["id"],
            "dosya_adi": row["dosya_adi"],
            "dosya_icerik": base64.b64decode(row["dosya_icerik_b64"]),
            "yuklenme_zamani": row.get("yuklenme_zamani"),
        })
    return sonuc


def depo_sayim_sil(kayit_id: int):
    r = requests.delete(f"{_REST}/depo_sayim", headers=_HEADERS, params={"id": f"eq.{kayit_id}"}, timeout=15)
    r.raise_for_status()


# ---------- Depo Temizlik ----------

def temizlik_kaydet(tarih: str, personel_adi: str):
    row = {"tarih": tarih, "personel_adi": personel_adi}
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/depo_temizlik", headers=headers,
        params={"on_conflict": "tarih"}, data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def temizlik_getir_ay(yil: int, ay: int):
    prefix = f"{yil:04d}-{ay:02d}"
    params = {"tarih": f"like.{prefix}%", "select": "tarih,personel_adi"}
    r = requests.get(f"{_REST}/depo_temizlik", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {row["tarih"]: row["personel_adi"] for row in r.json()}


# ---------- Depo Sayım Notları (haftalık program için gün bazlı not) ----------

def sayim_not_kaydet(tarih: str, not_metni: str):
    row = {"tarih": tarih, "not_metni": not_metni}
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/depo_sayim_notlar", headers=headers,
        params={"on_conflict": "tarih"}, data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def sayim_notlari_getir(gunler: list):
    if not gunler:
        return {}
    tarih_listesi = ",".join(gunler)
    params = {"tarih": f"in.({tarih_listesi})", "select": "tarih,not_metni"}
    r = requests.get(f"{_REST}/depo_sayim_notlar", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {row["tarih"]: row["not_metni"] for row in r.json()}


# ---------- Depo Sayım Blok Durumu (haftalık blok/bölge sayıldı matrisi) ----------

def depo_sayim_blok_durumlari_getir(gunler: list):
    """{(tarih, blok_adi): {sayildi, personel_adi, isaretlenme_zamani}} döner."""
    if not gunler:
        return {}
    tarih_listesi = ",".join(gunler)
    params = {
        "tarih": f"in.({tarih_listesi})",
        "select": "tarih,blok_adi,sayildi,personel_adi,isaretlenme_zamani",
    }
    r = requests.get(f"{_REST}/depo_sayim_blok_durum", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {
        (row["tarih"], row["blok_adi"]): {
            "sayildi": row["sayildi"],
            "personel_adi": row.get("personel_adi"),
            "isaretlenme_zamani": row.get("isaretlenme_zamani"),
        }
        for row in r.json()
    }


def depo_sayim_blok_durumu_isaretle(tarih: str, blok_adi: str, sayildi: bool, personel_adi: str = None):
    row = {
        "tarih": tarih,
        "blok_adi": blok_adi,
        "sayildi": sayildi,
        "personel_adi": personel_adi if sayildi else None,
        "isaretlenme_zamani": datetime.now().isoformat() if sayildi else None,
    }
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/depo_sayim_blok_durum", headers=headers,
        params={"on_conflict": "tarih,blok_adi"}, data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


# ---------- Planlanan Kargolar (serbest not tablosu) ----------

def planlanan_kargolar_getir():
    params = {"order": "id"}
    r = requests.get(f"{_REST}/planlanan_kargolar", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def planlanan_kargolar_kaydet(satirlar: list):
    """Tabloyu tamamen yeni haliyle değiştirir (silinenler DB'den de silinir)."""
    r = requests.delete(f"{_REST}/planlanan_kargolar", headers=_HEADERS, params={"id": "gte.0"}, timeout=15)
    r.raise_for_status()
    if not satirlar:
        return
    now = date.today().isoformat()
    rows = [
        {
            "musteri_adi": s.get("musteri_adi") or "",
            "alici_adresi": s.get("alici_adresi") or "",
            "aciklama": s.get("aciklama") or "",
            "siparis_tarihi": s.get("siparis_tarihi") or "",
            "koli_adedi": s.get("koli_adedi") or "",
            "planlanan_tarih": s.get("planlanan_tarih") or "",
            "olusturma_zamani": now,
        }
        for s in satirlar
    ]
    r = requests.post(f"{_REST}/planlanan_kargolar", headers=_HEADERS, data=json.dumps(rows), timeout=15)
    r.raise_for_status()


# ---------- Tamamlanan Kargolar (Kargolaştır ile eklenir) ----------

def tamamlanan_kargo_kaydet(tarih: str, varis_il: str, kargo_firmasi: str, toplam_tutar: float, detay: str):
    now_dt = date.today().isoformat()
    row = {
        "tarih": tarih, "varis_il": varis_il, "kargo_firmasi": kargo_firmasi,
        "toplam_tutar": toplam_tutar, "detay": detay, "olusturma_zamani": now_dt,
    }
    r = requests.post(f"{_REST}/tamamlanan_kargolar", headers=_HEADERS, data=json.dumps(row), timeout=15)
    r.raise_for_status()


def tamamlanan_kargolar_getir_ay(yil: int, ay: int):
    prefix = f"{yil:04d}-{ay:02d}"
    params = {"tarih": f"like.{prefix}%", "order": "tarih.desc,id.desc"}
    r = requests.get(f"{_REST}/tamamlanan_kargolar", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def tamamlanan_kargo_sil(kayit_id: int):
    r = requests.delete(f"{_REST}/tamamlanan_kargolar", headers=_HEADERS, params={"id": f"eq.{kayit_id}"}, timeout=15)
    r.raise_for_status()


# ---------- İnsan Kaynakları: Personel ----------

def personel_ekle(ad_soyad, dogum_tarihi, telefon, foto_bytes, cinsiyet=None):
    row = {
        "ad_soyad": ad_soyad, "dogum_tarihi": dogum_tarihi, "telefon": telefon, "cinsiyet": cinsiyet,
        "foto_b64": base64.b64encode(foto_bytes).decode() if foto_bytes else None,
        "olusturma_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/personel", headers=_HEADERS, data=json.dumps(row), timeout=20)
    r.raise_for_status()


def personel_guncelle(personel_id, ad_soyad, dogum_tarihi, telefon, cinsiyet, foto_bytes=None):
    row = {"ad_soyad": ad_soyad, "dogum_tarihi": dogum_tarihi, "telefon": telefon, "cinsiyet": cinsiyet}
    if foto_bytes:
        row["foto_b64"] = base64.b64encode(foto_bytes).decode()
    r = requests.patch(
        f"{_REST}/personel", headers=_HEADERS, params={"id": f"eq.{personel_id}"},
        data=json.dumps(row), timeout=20,
    )
    r.raise_for_status()


def personel_listele():
    r = requests.get(f"{_REST}/personel", headers=_HEADERS, params={"order": "ad_soyad"}, timeout=15)
    r.raise_for_status()
    sonuc = []
    for row in r.json():
        row = dict(row)
        row["foto_bytes"] = base64.b64decode(row["foto_b64"]) if row.get("foto_b64") else None
        sonuc.append(row)
    return sonuc


def bugun_dogum_gunu_olanlar():
    """Bugünün ay-gününe denk gelen doğum tarihi olan personelleri döndürür."""
    bugun = date.today()
    ay_gun = f"-{bugun.month:02d}-{bugun.day:02d}"
    sonuc = []
    for p in personel_listele():
        dt = p.get("dogum_tarihi")
        if dt and dt.endswith(ay_gun) and len(dt) == 10:
            sonuc.append(p)
    return sonuc


def personel_sil(personel_id: int):
    r = requests.delete(f"{_REST}/personel", headers=_HEADERS, params={"id": f"eq.{personel_id}"}, timeout=15)
    r.raise_for_status()


def ozluk_belgesi_ekle(personel_id, belge_turu, dosya_adi, dosya_bytes):
    row = {
        "personel_id": personel_id, "belge_turu": belge_turu, "dosya_adi": dosya_adi,
        "dosya_icerik_b64": base64.b64encode(dosya_bytes).decode(),
        "yuklenme_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/ozluk_belgeleri", headers=_HEADERS, data=json.dumps(row), timeout=30)
    r.raise_for_status()


def ozluk_belgeleri_getir(personel_id):
    params = {"personel_id": f"eq.{personel_id}", "order": "id"}
    r = requests.get(f"{_REST}/ozluk_belgeleri", headers=_HEADERS, params=params, timeout=20)
    r.raise_for_status()
    sonuc = []
    for row in r.json():
        sonuc.append({
            "id": row["id"], "belge_turu": row["belge_turu"], "dosya_adi": row["dosya_adi"],
            "dosya_icerik": base64.b64decode(row["dosya_icerik_b64"]),
            "yuklenme_zamani": row.get("yuklenme_zamani"),
        })
    return sonuc


def ozluk_belgesi_sil(belge_id: int):
    r = requests.delete(f"{_REST}/ozluk_belgeleri", headers=_HEADERS, params={"id": f"eq.{belge_id}"}, timeout=15)
    r.raise_for_status()


# ---------- İnsan Kaynakları: Puantaj ----------

def puantaj_kaydet(tarih, personel_id, giris_saati, cikis_saati, ek_mesai_saat=None, sebep=None):
    row = {
        "tarih": tarih, "personel_id": personel_id, "giris_saati": giris_saati, "cikis_saati": cikis_saati,
        "ek_mesai_saat": ek_mesai_saat, "sebep": sebep,
    }
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/puantaj", headers=headers, params={"on_conflict": "tarih,personel_id"},
        data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def puantaj_getir_gun(tarih):
    params = {"tarih": f"eq.{tarih}"}
    r = requests.get(f"{_REST}/puantaj", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {row["personel_id"]: row for row in r.json()}


def puantaj_getir_ay(yil, ay):
    prefix = f"{yil:04d}-{ay:02d}"
    params = {"tarih": f"like.{prefix}%"}
    r = requests.get(f"{_REST}/puantaj", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ---------- İade ----------

def iade_ekle(firma_adi, urun_adi, seri_numaralari, adet, tarih):
    row = {
        "firma_adi": firma_adi, "urun_adi": urun_adi, "seri_numaralari": seri_numaralari,
        "adet": adet, "tarih": tarih, "durum": "Bekliyor",
        "olusturma_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/iadeler", headers=_HEADERS, data=json.dumps(row), timeout=15)
    r.raise_for_status()


def iadeler_getir():
    r = requests.get(f"{_REST}/iadeler", headers=_HEADERS, params={"order": "id.desc"}, timeout=15)
    r.raise_for_status()
    return r.json()


def iade_durum_guncelle(iade_id, durum):
    r = requests.patch(
        f"{_REST}/iadeler", headers=_HEADERS, params={"id": f"eq.{iade_id}"},
        data=json.dumps({"durum": durum}), timeout=15,
    )
    r.raise_for_status()


def iade_yerlestirildi_guncelle(iade_id, yerlestirildi):
    r = requests.patch(
        f"{_REST}/iadeler", headers=_HEADERS, params={"id": f"eq.{iade_id}"},
        data=json.dumps({"yerlestirildi": bool(yerlestirildi)}), timeout=15,
    )
    r.raise_for_status()


def iade_sil(iade_id):
    r = requests.delete(f"{_REST}/iadeler", headers=_HEADERS, params={"id": f"eq.{iade_id}"}, timeout=15)
    r.raise_for_status()


# ---------- Planlama: günlük görevler ----------

def gorev_ekle(tarih, saat, aciklama):
    row = {
        "tarih": tarih, "saat": saat, "aciklama": aciklama, "tamamlandi": False,
        "olusturma_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/planlama_gorevler", headers=_HEADERS, data=json.dumps(row), timeout=15)
    r.raise_for_status()


def gorevler_getir_gun(tarih):
    params = {"tarih": f"eq.{tarih}", "order": "saat"}
    r = requests.get(f"{_REST}/planlama_gorevler", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def gorevler_getir_ay(yil, ay):
    prefix = f"{yil:04d}-{ay:02d}"
    params = {"tarih": f"like.{prefix}%"}
    r = requests.get(f"{_REST}/planlama_gorevler", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def gorevler_getir_bekleyen_bildirim(bugun_iso, simdi_saat):
    """Bugün, saati gelmiş veya geçmiş ama henüz tamamlanmamış görevleri döndürür."""
    params = {"tarih": f"eq.{bugun_iso}", "tamamlandi": "eq.false", "order": "saat"}
    r = requests.get(f"{_REST}/planlama_gorevler", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    tumu = r.json()
    return [g for g in tumu if g.get("saat") and g["saat"] <= simdi_saat]


def gorev_tamamla(gorev_id, tamamlandi=True):
    r = requests.patch(
        f"{_REST}/planlama_gorevler", headers=_HEADERS, params={"id": f"eq.{gorev_id}"},
        data=json.dumps({"tamamlandi": tamamlandi}), timeout=15,
    )
    r.raise_for_status()


def gorev_sil(gorev_id):
    r = requests.delete(f"{_REST}/planlama_gorevler", headers=_HEADERS, params={"id": f"eq.{gorev_id}"}, timeout=15)
    r.raise_for_status()


# ---------- Planlama: Depolar arası transfer talepleri ----------

def transfer_talebi_ekle(talep_eden_depo, hedef_depo, urun_aciklama, adet, istenen_zaman_aciklama):
    row = {
        "talep_eden_depo": talep_eden_depo, "hedef_depo": hedef_depo, "urun_aciklama": urun_aciklama,
        "adet": adet, "istenen_zaman_aciklama": istenen_zaman_aciklama, "durum": "Bekliyor",
        "olusturma_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/depo_transfer_talepleri", headers=_HEADERS, data=json.dumps(row), timeout=15)
    r.raise_for_status()


def transfer_talepleri_getir(durum=None):
    params = {"order": "id.desc"}
    if durum:
        params["durum"] = f"eq.{durum}"
    r = requests.get(f"{_REST}/depo_transfer_talepleri", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def transfer_talebi_durum_guncelle(talep_id, durum):
    r = requests.patch(
        f"{_REST}/depo_transfer_talepleri", headers=_HEADERS, params={"id": f"eq.{talep_id}"},
        data=json.dumps({"durum": durum}), timeout=15,
    )
    r.raise_for_status()


def transfer_talebi_sil(talep_id):
    r = requests.delete(
        f"{_REST}/depo_transfer_talepleri", headers=_HEADERS, params={"id": f"eq.{talep_id}"}, timeout=15
    )
    r.raise_for_status()


# ---------- Kontrol Listesi ----------

def kontrol_maddesi_ekle(tarih, madde):
    row = {
        "tarih": tarih, "madde": madde, "tamamlandi": False,
        "olusturma_zamani": date.today().isoformat(),
    }
    r = requests.post(f"{_REST}/kontrol_listesi", headers=_HEADERS, data=json.dumps(row), timeout=15)
    r.raise_for_status()


def kontrol_listesi_getir(tarih):
    params = {"tarih": f"eq.{tarih}", "order": "id"}
    r = requests.get(f"{_REST}/kontrol_listesi", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def kontrol_listesi_getir_ay(yil, ay):
    prefix = f"{yil:04d}-{ay:02d}"
    params = {"tarih": f"like.{prefix}%", "select": "tarih,tamamlandi"}
    r = requests.get(f"{_REST}/kontrol_listesi", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def kontrol_maddesi_tamamla(madde_id, tamamlandi=True):
    r = requests.patch(
        f"{_REST}/kontrol_listesi", headers=_HEADERS, params={"id": f"eq.{madde_id}"},
        data=json.dumps({"tamamlandi": tamamlandi}), timeout=15,
    )
    r.raise_for_status()


def kontrol_maddesi_sil(madde_id):
    r = requests.delete(f"{_REST}/kontrol_listesi", headers=_HEADERS, params={"id": f"eq.{madde_id}"}, timeout=15)
    r.raise_for_status()


# ---------- Bildirim okundu takibi ----------

def bildirim_okundu_isaretle(tip, anahtar, tarih):
    row = {"tip": tip, "anahtar": str(anahtar), "tarih": tarih}
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/bildirim_okundu", headers=headers, params={"on_conflict": "tip,anahtar,tarih"},
        data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def bildirim_okundu_mu(tip, anahtar, tarih):
    params = {"tip": f"eq.{tip}", "anahtar": f"eq.{anahtar}", "tarih": f"eq.{tarih}"}
    r = requests.get(f"{_REST}/bildirim_okundu", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return len(r.json()) > 0


def bildirim_okundu_getir_gun(tarih):
    """Bir güne ait TÜM okundu işaretlerini tek istekte döndürür ({(tip, anahtar), ...}).

    bildirim_okundu_mu'yu her bildirim için ayrı ayrı çağırmak yerine (N+1 istek,
    sayfa açılışını yavaşlatıyordu) bu fonksiyonla tek seferde çekilip yerelde
    üyelik kontrolü yapılır.
    """
    params = {"tarih": f"eq.{tarih}", "select": "tip,anahtar"}
    r = requests.get(f"{_REST}/bildirim_okundu", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {(row["tip"], row["anahtar"]) for row in r.json()}


# ---------- Stok Sayım ----------

def stok_sayim_oturumu_kaydet(tarih, personel_adi, satirlar):
    """satirlar: [{urun_adi, stok_kodu, guncel_stok, sayilan, fark}, ...] - sayılan tüm ürünler"""
    row = {"tarih": tarih, "personel_adi": personel_adi, "olusturma_zamani": date.today().isoformat()}
    headers = dict(_HEADERS)
    headers["Prefer"] = "return=representation"
    r = requests.post(f"{_REST}/stok_sayim_oturumlari", headers=headers, data=json.dumps(row), timeout=20)
    r.raise_for_status()
    sonuc = r.json()
    oturum = sonuc[0] if isinstance(sonuc, list) else sonuc
    oturum_id = oturum["id"]
    if satirlar:
        detay_rows = [{**s, "oturum_id": oturum_id} for s in satirlar]
        r2 = requests.post(f"{_REST}/stok_sayim_detay", headers=_HEADERS, data=json.dumps(detay_rows), timeout=20)
        r2.raise_for_status()
    return oturum_id


def stok_sayim_oturumlari_getir(tarih):
    params = {"tarih": f"eq.{tarih}", "order": "id"}
    r = requests.get(f"{_REST}/stok_sayim_oturumlari", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def stok_sayim_oturumlari_getir_coklu(gunler: list):
    """stok_sayim_oturumlari_getir'in haftalık versiyonu - tek istekle
    {tarih: [oturum, ...]} döner (bkz. depo_sayim_getir_coklu)."""
    if not gunler:
        return {}
    tarih_listesi = ",".join(gunler)
    params = {"tarih": f"in.({tarih_listesi})", "order": "id"}
    r = requests.get(f"{_REST}/stok_sayim_oturumlari", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    sonuc = {g: [] for g in gunler}
    for row in r.json():
        sonuc.setdefault(row["tarih"], []).append(row)
    return sonuc


def stok_sayim_oturumu_sil(oturum_id):
    """Oturumu siler - stok_sayim_detay satırları FK ON DELETE CASCADE ile otomatik silinir."""
    params = {"id": f"eq.{oturum_id}"}
    r = requests.delete(f"{_REST}/stok_sayim_oturumlari", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()


def stok_sayim_detay_getir(oturum_id):
    params = {"oturum_id": f"eq.{oturum_id}", "order": "id"}
    r = requests.get(f"{_REST}/stok_sayim_detay", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ---------- Stok Sayım Taslağı ----------
# Sayım sırasında telefon çalıp Streamlit bağlantısı koptuğunda (mobil
# tarayıcı sekmeyi arka planda öldürüyor) session_state tamamen sıfırlanıyor
# ve o ana kadar girilen tüm sayımlar kayboluyordu. Artık her hücre
# değiştiğinde satır tek tek burada da (veritabanında) upsert ediliyor,
# sayfa yeniden açıldığında session_state boşsa buradan geri yükleniyor.
def stok_sayim_taslak_kaydet(oturum_anahtari, urun_adi, sayim, personel=None):
    row = {
        "oturum_anahtari": oturum_anahtari, "urun_adi": urun_adi,
        "sayim": None if sayim in (None, "") else str(sayim), "personel": personel,
        "guncellenme_zamani": datetime.now().isoformat(),
    }
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/stok_sayim_taslak", headers=headers,
        params={"on_conflict": "oturum_anahtari,urun_adi"}, data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def stok_sayim_taslak_getir(oturum_anahtari):
    params = {"oturum_anahtari": f"eq.{oturum_anahtari}"}
    r = requests.get(f"{_REST}/stok_sayim_taslak", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def stok_sayim_taslak_temizle(oturum_anahtari):
    params = {"oturum_anahtari": f"eq.{oturum_anahtari}"}
    r = requests.delete(f"{_REST}/stok_sayim_taslak", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()


# ---------- Depo Temizlik (kroki bazlı) ----------

def temizlik_kaydet_oda(oda, tarih, personel_adi):
    row = {"oda": oda, "tarih": tarih, "personel_adi": personel_adi}
    headers = dict(_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(
        f"{_REST}/depo_temizlik_kayitlari", headers=headers, params={"on_conflict": "oda,tarih"},
        data=json.dumps(row), timeout=15,
    )
    r.raise_for_status()


def temizlik_getir_gun_oda(tarih):
    params = {"tarih": f"eq.{tarih}"}
    r = requests.get(f"{_REST}/depo_temizlik_kayitlari", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return {row["oda"]: row for row in r.json()}


def temizlik_getir_son_gunler(oda, gun_listesi):
    tarih_listesi = ",".join(gun_listesi)
    params = {"oda": f"eq.{oda}", "tarih": f"in.({tarih_listesi})", "order": "tarih.desc"}
    r = requests.get(f"{_REST}/depo_temizlik_kayitlari", headers=_HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ---------- Aras Kargo Entegrasyonu ----------
# Aras'ın GetQueryJSON SOAP servisi (WCF) - kimlik bilgileri (kullanıcı adı,
# şifre, müşteri kodu) ASLA koda yazılmıyor, sadece Streamlit Cloud'un
# Settings > Secrets kısmına ARAS_USERNAME / ARAS_PASSWORD / ARAS_CUSTOMER_CODE
# olarak eklenmesi gerekiyor. Kimlik bilgileri girilmemişse tüm fonksiyonlar
# sessizce boş/None döner - site bu entegrasyon olmadan da çalışmaya devam eder.
import xml.etree.ElementTree as _ET

_ARAS_URL = "https://customerservices.araskargo.com.tr/ArasCargoCustomerIntegrationService/ArasCargoIntegrationService.svc"
_ARAS_SOAP_ACTION = "http://tempuri.org/IArasCargoIntegrationService/GetQueryJSON"


def _aras_ayarli_mi():
    return bool(
        st.secrets.get("ARAS_USERNAME") and st.secrets.get("ARAS_PASSWORD") and st.secrets.get("ARAS_CUSTOMER_CODE")
    )


def _aras_sorgu(query_info_xml):
    """Aras Kargo GetQueryJSON servisine tek bir SOAP isteği gönderir, ayrıştırılmış JSON (dict) döner."""
    import xml.sax.saxutils as xmlsax

    login_xml = (
        f"<LoginInfo><UserName>{xmlsax.escape(st.secrets['ARAS_USERNAME'])}</UserName>"
        f"<Password>{xmlsax.escape(st.secrets['ARAS_PASSWORD'])}</Password>"
        f"<CustomerCode>{xmlsax.escape(st.secrets['ARAS_CUSTOMER_CODE'])}</CustomerCode></LoginInfo>"
    )
    zarf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">'
        "<soap:Body><tem:GetQueryJSON>"
        f"<tem:loginInfo>{xmlsax.escape(login_xml)}</tem:loginInfo>"
        f"<tem:queryInfo>{xmlsax.escape(query_info_xml)}</tem:queryInfo>"
        "</tem:GetQueryJSON></soap:Body></soap:Envelope>"
    )
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": _ARAS_SOAP_ACTION}
    r = requests.post(_ARAS_URL, headers=headers, data=zarf.encode("utf-8"), timeout=15)
    r.raise_for_status()
    kok = _ET.fromstring(r.text)
    sonuc_el = kok.find(".//{http://tempuri.org/}GetQueryJSONResult")
    if sonuc_el is None or not sonuc_el.text:
        return None
    return json.loads(sonuc_el.text)


@st.cache_data(ttl=3600, show_spinner=False)  # her sevkiyatın durumu ayrı bir ağ isteği - kısa TTL sık sık uzun beklemeye sebep oluyordu
def aras_gunluk_sevkiyatlar(tarih_gg_aa_yyyy):
    """Verilen günde (GG/AA/YYYY formatında) çıkışı yapılmış tüm Aras gönderilerini döner."""
    if not _aras_ayarli_mi():
        return []
    query_info = f"<QueryInfo><QueryType>2</QueryType><Date>{tarih_gg_aa_yyyy}</Date></QueryInfo>"
    try:
        veri = _aras_sorgu(query_info)
    except Exception:
        return []
    kargo = ((veri or {}).get("QueryResult") or {}).get("Cargo")
    if not kargo:
        return []
    return kargo if isinstance(kargo, list) else [kargo]


@st.cache_data(ttl=3600, show_spinner=False)
def aras_kargo_durumu(takip_no):
    """Tek bir Aras takip numarasının güncel teslimat durumunu (DURUMU, DURUM_EN vb.) döner."""
    if not _aras_ayarli_mi() or not takip_no:
        return None
    query_info = f"<QueryInfo><QueryType>1</QueryType><TrackingNumber>{takip_no}</TrackingNumber></QueryInfo>"
    try:
        veri = _aras_sorgu(query_info)
    except Exception:
        return None
    return ((veri or {}).get("QueryResult") or {}).get("Cargo")
