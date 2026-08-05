# -*- coding: utf-8 -*-
"""SQLite tabanlı basit kalıcı depolama katmanı."""
import sqlite3
import json
from datetime import date

DB_PATH = "kamtek_depo.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Kargo takip: her gün, her kargo firması için yüklenen excel'den çıkarılan satırlar
    c.execute("""
        CREATE TABLE IF NOT EXISTS kargo_takip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            kargo_firmasi TEXT NOT NULL,
            gonderi_tarihi TEXT,
            gonderi_no TEXT,
            alici_adi TEXT,
            alici_adresi TEXT,
            varis_il TEXT,
            odeme_sekli TEXT,
            desi TEXT,
            yuklenme_zamani TEXT
        )
    """)
    # Depo sayım fişleri: her gün yüklenen excel dosyasının ham içeriği (indirilebilmesi için)
    c.execute("""
        CREATE TABLE IF NOT EXISTS depo_sayim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dosya_adi TEXT NOT NULL,
            dosya_icerik BLOB NOT NULL,
            yuklenme_zamani TEXT
        )
    """)
    # Depo temizlik çizelgesi: gün -> personel adı
    c.execute("""
        CREATE TABLE IF NOT EXISTS depo_temizlik (
            tarih TEXT PRIMARY KEY,
            personel_adi TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------- Kargo Takip ----------

def kargo_takip_kaydet(tarih: str, kargo_firmasi: str, satirlar: list):
    conn = get_conn()
    c = conn.cursor()
    now = date.today().isoformat()
    for s in satirlar:
        c.execute("""
            INSERT INTO kargo_takip
            (tarih, kargo_firmasi, gonderi_tarihi, gonderi_no, alici_adi, alici_adresi, varis_il, odeme_sekli, desi, yuklenme_zamani)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tarih, kargo_firmasi,
            s.get("gonderi_tarihi"), s.get("gonderi_no"), s.get("alici_adi"),
            s.get("alici_adresi"), s.get("varis_il"), s.get("odeme_sekli"),
            s.get("desi"), now,
        ))
    conn.commit()
    conn.close()


def kargo_takip_getir(tarih: str):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM kargo_takip WHERE tarih = ? ORDER BY kargo_firmasi, id", (tarih,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Depo Sayım ----------

def depo_sayim_kaydet(tarih: str, dosya_adi: str, dosya_bytes: bytes):
    conn = get_conn()
    c = conn.cursor()
    now = date.today().isoformat()
    c.execute("""
        INSERT INTO depo_sayim (tarih, dosya_adi, dosya_icerik, yuklenme_zamani)
        VALUES (?, ?, ?, ?)
    """, (tarih, dosya_adi, dosya_bytes, now))
    conn.commit()
    conn.close()


def depo_sayim_getir(tarih: str):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT id, dosya_adi, dosya_icerik, yuklenme_zamani FROM depo_sayim WHERE tarih = ? ORDER BY id", (tarih,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Depo Temizlik ----------

def temizlik_kaydet(tarih: str, personel_adi: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO depo_temizlik (tarih, personel_adi) VALUES (?, ?)
        ON CONFLICT(tarih) DO UPDATE SET personel_adi = excluded.personel_adi
    """, (tarih, personel_adi))
    conn.commit()
    conn.close()


def temizlik_getir_ay(yil: int, ay: int):
    conn = get_conn()
    c = conn.cursor()
    prefix = f"{yil:04d}-{ay:02d}"
    rows = c.execute("SELECT tarih, personel_adi FROM depo_temizlik WHERE tarih LIKE ?", (prefix + "%",)).fetchall()
    conn.close()
    return {r["tarih"]: r["personel_adi"] for r in rows}
