# -*- coding: utf-8 -*-
"""Supabase (Postgres) tabanlı kalıcı depolama katmanı.
Streamlit Cloud'un dosya sistemi kalıcı olmadığı için (uygulama zaman zaman
yeniden başlatılır/uyandırılır) veriler artık gerçek bir bulut veritabanında
(Supabase) tutuluyor - böylece bugün girilen veriler yarın da görünür."""
import base64
import json
from datetime import date

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
