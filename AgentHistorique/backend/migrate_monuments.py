"""
Migration de AgentCircuit/monuments.csv vers la table public.monuments
de la base dourbia_db (PostgreSQL, port 5432).

Mapping retenu :
    nom          -> name_fr
    latitude     -> latitude
    longitude    -> longitude
    popularite   -> priority   (échelle 1-5 du CSV, utilisée comme
                                 score de tri par _get_sorted_monument_options)

Colonnes absentes du CSV (laissées à NULL) :
    name_en, name_ar, status, importance, accessibility

id : pas de séquence/DEFAULT sur la colonne (numeric(10,2) NOT NULL) ->
     généré manuellement en partant de 1 puisque la table est vide.

Usage :
    pip install pandas sqlalchemy psycopg[binary]
    python migrate_monuments.py --csv monuments.csv --dry-run   # aperçu sans écrire
    python migrate_monuments.py --csv monuments.csv             # écrit réellement
"""

import argparse
import sys

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://dourbia:dourbia@localhost:5433/dourbia"


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", decimal=",")

    # Sécurité : latitude/longitude parfois lues comme str selon la
    # présence de valeurs mixtes -> on force la conversion en float.
    df["latitude"] = df["latitude"].astype(str).str.replace(",", ".").astype(float)
    df["longitude"] = df["longitude"].astype(str).str.replace(",", ".").astype(float)
    df["popularite"] = pd.to_numeric(df["popularite"], errors="coerce")

    # Lignes sans nom ou coordonnées valides -> exclues (comme le faisait
    # l'ancien load_circuit_data() qui `continue`-ait sur ValueError/KeyError)
    before = len(df)
    df = df.dropna(subset=["nom", "latitude", "longitude"])
    dropped = before - len(df)
    if dropped:
        print(
            f"[warn] {dropped} ligne(s) ignorée(s) (nom/latitude/longitude manquants)"
        )

    return df.reset_index(drop=True)


def build_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "id": idx + 1,  # génération manuelle, table vide -> 1..N
                "name_fr": str(row["nom"]).strip(),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "priority": (
                    float(row["popularite"]) if pd.notna(row["popularite"]) else None
                ),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="monuments.csv")
    parser.add_argument(
        "--dry-run", action="store_true", help="Affiche sans écrire en base"
    )
    args = parser.parse_args()

    df = load_csv(args.csv)
    rows = build_rows(df)

    print(
        f"{len(rows)} monument(s) prêt(s) à insérer dans public.monuments (dourbia_db)"
    )
    for r in rows[:5]:
        print("  ", r)
    if len(rows) > 5:
        print(f"   ... (+{len(rows) - 5} autres)")

    if args.dry_run:
        print("\n[dry-run] Aucune écriture effectuée.")
        return

    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM public.monuments")).scalar()
        if existing:
            print(
                f"\n[abort] public.monuments contient déjà {existing} ligne(s). "
                "Migration annulée pour éviter les doublons/collisions d'id. "
                "Vide la table d'abord si tu veux relancer ce script."
            )
            sys.exit(1)

        conn.execute(
            text("""
                INSERT INTO public.monuments (id, name_fr, latitude, longitude, priority)
                VALUES (:id, :name_fr, :latitude, :longitude, :priority)
                """),
            rows,
        )
        count = conn.execute(text("SELECT COUNT(*) FROM public.monuments")).scalar()
        print(
            f"\n[ok] {count} ligne(s) présentes dans public.monuments après migration."
        )


if __name__ == "__main__":
    main()
