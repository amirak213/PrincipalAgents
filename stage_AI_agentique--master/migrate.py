#!/usr/bin/env python3
"""
Migration Excel → PostgreSQL — table distance
Prérequis : pip install pandas openpyxl psycopg2-binary sqlalchemy
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# ── 1. Paramètres de connexion ──────────────────────────────
DB_USER     = "postgres"         # à adapter
DB_PASSWORD = "votre_mot_de_passe"
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "sig_dourbia"
EXCEL_FILE  = "distances.xlsx"    # chemin vers votre fichier
SHEET_NAME  = 0                    # 0 = première feuille, ou nom ex: "Sheet1"

# ── 2. Lecture du fichier Excel ──────────────────────────────
print("Lecture du fichier Excel...")
df = pd.read_csv("distances.csv", encoding="utf-8")

# Renommage des colonnes pour correspondre à la table SQL
df = df.rename(columns={
    df.columns[0]: "idx_original",
    "from":             "from_lieu",
    "to":               "to_lieu",
    "distance_m":       "distance_m",
    "distance_km":      "distance_km",
    "duree_pied_min":   "duree_pied_min",
    "duree_velo_min":   "duree_velo_min",
    "duree_voiture_min":"duree_voiture_min",
})

# Nettoyage : suppression des lignes vides, strip des noms de lieux
df = df.dropna(subset=["from_lieu", "to_lieu"])
df["from_lieu"] = df["from_lieu"].astype(str).str.strip()
df["to_lieu"]   = df["to_lieu"].astype(str).str.strip()

print(f"{len(df)} lignes chargées depuis Excel.")

# ── 3. Connexion PostgreSQL ──────────────────────────────────
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── 4. Insertion par batch (gestion des doublons) ────────────
print("Insertion en base...")
inserted = 0
skipped  = 0

with engine.begin() as conn:
    for _, row in df.iterrows():
        try:
            conn.execute(text("""
                INSERT INTO distance
                    (idx_original, from_lieu, to_lieu,
                     distance_m, distance_km,
                     duree_pied_min, duree_velo_min, duree_voiture_min)
                VALUES
                    (:idx, :from_lieu, :to_lieu,
                     :dist_m, :dist_km,
                     :pied, :velo, :voiture)
                ON CONFLICT (from_lieu, to_lieu) DO UPDATE SET
                    distance_m        = EXCLUDED.distance_m,
                    distance_km       = EXCLUDED.distance_km,
                    duree_pied_min    = EXCLUDED.duree_pied_min,
                    duree_velo_min    = EXCLUDED.duree_velo_min,
                    duree_voiture_min = EXCLUDED.duree_voiture_min,
                    date_import       = NOW()
            """), {
                "idx":      row.get("idx_original"),
                "from_lieu": row["from_lieu"],
                "to_lieu":   row["to_lieu"],
                "dist_m":    row.get("distance_m"),
                "dist_km":   row.get("distance_km"),
                "pied":      row.get("duree_pied_min"),
                "velo":      row.get("duree_velo_min"),
                "voiture":   row.get("duree_voiture_min"),
            })
            inserted += 1
        except Exception as e:
            print(f"  ⚠ Erreur ligne {_}: {e}")
            skipped += 1

print(f"✓ Migration terminée : {inserted} insérées, {skipped} ignorées.")

# ── 5. Vérification rapide ───────────────────────────────────
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM distance"))
    print(f"Total lignes en base : {result.scalar()}")