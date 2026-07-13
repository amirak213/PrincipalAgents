"""
ingest_historical.py — Ingestion unifiée des données historiques Carthage

Adapté depuis ingest_excel.py + chunk_documents.py + generate_embeddings.py
de l'agent externe.

Changements majeurs vs l'original :
- Cible sig_dourbia:5432 (pas historical_guide:5433)
- Stocke FLOAT[] (pas pgvector Vector)
- Utilise paraphrase-multilingual-MiniLM-L12-v2 (déjà dans Dourbia)
- Script standalone Windows-compatible

Usage :
    python scripts/ingest_historical.py --source data/raw/excel/
    python scripts/ingest_historical.py --source data/raw/excel/ --clear
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ingest] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/sig_dourbia",
)

# INTEGRATION NOTE: Même modèle que Dourbia (déjà téléchargé, pas de nouveau download)
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DIM = 384
CHUNK_SIZE = 400  # tokens approx
CHUNK_OVERLAP = 50
BATCH_SIZE = 32


# ─── Connexion DB ─────────────────────────────────────────────────────────────
def get_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DB_URL, options="-c client_encoding=UTF8")
    conn.autocommit = False
    return conn


# ─── Chargement du modèle d'embedding ─────────────────────────────────────────
def load_embedding_model():
    from sentence_transformers import SentenceTransformer

    logger.info("Chargement du modèle : %s", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info("Modèle chargé (dim=%s)", EMBEDDING_DIM)
    return model


def embed_texts(model, texts: list[str]) -> list[list[float]]:
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return [v.tolist() for v in vectors]


# ─── Chunking ─────────────────────────────────────────────────────────────────
def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Découpe un texte en chunks avec overlap."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


# ─── Lecture Excel ─────────────────────────────────────────────────────────────
def load_monuments(excel_path: Path) -> list[dict[str, Any]]:
    """
    Charge Monuments.xlsx avec les vraies colonnes Dourbia.
    Génère 3 chunks par monument (FR, EN, AR) si les descriptions existent.
    """
    logger.info("Lecture : %s", excel_path)
    df = pd.read_excel(excel_path, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    logger.info("Colonnes : %s", list(df.columns))

    records = []
    for _, row in df.iterrows():
        raw_id = row.get("ID_monument")
        try:
            source_id = float(raw_id)
            if source_id != source_id:  # NaN check
                continue
        except (TypeError, ValueError):
            continue
        if source_id == 0:
            continue

        periode_dominante = str(row.get("epoque_dominante") or "")
        periode_secondaire = str(row.get("epoque_secondaire") or "")
        accessibilite = str(row.get("accessibilite_monument") or "")
        duree = str(row.get("duree_visite(en min)") or "")
        statut = str(row.get("statut_monument") or "")
        adresse = str(row.get("adresse_monument") or "")

        # Tarifs
        tarifs = (
            f"Tarif résident: {row.get('Tarif_resident', '')} DT | "
            f"Étudiant: {row.get('Tarif_Étudiant', '')} DT | "
            f"Étranger: {row.get('Tarif_Étranger', '')} DT"
        )

        metadata = {
            "destination_name": "Carthage",
            "dominant_period": periode_dominante,
            "secondary_period": periode_secondaire,
            "is_site_root": True,
            "site_id": int(source_id) if source_id == source_id else 0,
            "duree_visite_min": duree,
            "statut": statut,
            "accessibilite": accessibilite,
        }

        # ── Chunk FR ──────────────────────────────────────────────────────
        nom_fr = str(row.get("nom_monument_FR") or "Monument")
        desc_fr = str(row.get("description_FR") or "")
        if nom_fr and len(desc_fr.strip()) >= 20:
            full_fr = (
                f"{nom_fr}. {desc_fr} "
                f"Époque : {periode_dominante}. "
                f"Durée de visite : {duree} minutes. "
                f"Adresse : {adresse}. "
                f"Accessibilité : {accessibilite}. "
                f"{tarifs}"
            )
            records.append(
                {
                    "source_type": "monument",
                    "source_id": source_id,
                    "title": nom_fr,
                    "language": "fr",
                    "text": full_fr.strip(),
                    "metadata": metadata,
                }
            )

        # ── Chunk EN ──────────────────────────────────────────────────────
        nom_en = str(row.get("nom_monument_EN") or nom_fr)
        desc_en = str(row.get("description_EN") or "")
        if nom_en and len(desc_en.strip()) >= 20:
            full_en = (
                f"{nom_en}. {desc_en} "
                f"Period: {periode_dominante}. "
                f"Visit duration: {duree} minutes. "
                f"Address: {adresse}."
            )
            records.append(
                {
                    "source_type": "monument",
                    "source_id": source_id,
                    "title": nom_en,
                    "language": "en",
                    "text": full_en.strip(),
                    "metadata": metadata,
                }
            )

        # ── Chunk AR ──────────────────────────────────────────────────────
        nom_ar = str(row.get("nom_monument_AR") or nom_fr)
        desc_ar = str(row.get("description_AR") or "")
        if nom_ar and len(desc_ar.strip()) >= 20:
            full_ar = f"{nom_ar}. {desc_ar} الحقبة: {periode_dominante}."
            records.append(
                {
                    "source_type": "monument",
                    "source_id": source_id,
                    "title": nom_ar,
                    "language": "ar",
                    "text": full_ar.strip(),
                    "metadata": metadata,
                }
            )

    logger.info("Monuments chargés : %d", len(records))
    return records


def load_circuits(excel_path: Path) -> list[dict[str, Any]]:
    """Charge Tab_circuit.xlsx avec les vraies colonnes Dourbia."""
    if not excel_path.exists():
        return []
    logger.info("Lecture : %s", excel_path)
    df = pd.read_excel(excel_path, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    logger.info("Colonnes circuits : %s", list(df.columns))

    records = []
    for _, row in df.iterrows():
        # Colonnes possibles — on teste plusieurs variantes
        source_id = float(row.get("ID_circuit") or row.get("id") or row.get("ID") or 0)
        if source_id == 0:
            continue

        nom = str(
            row.get("nom_circuit_FR")
            or row.get("nom_circuit")
            or row.get("nom")
            or row.get("Nom")
            or "Circuit"
        )
        desc = str(
            row.get("description_FR")
            or row.get("description")
            or row.get("Description")
            or ""
        )
        duree = str(row.get("duree_circuit") or row.get("duree") or "")
        transport = str(row.get("transport") or "")

        full_text = " ".join(
            filter(None, [nom, desc, f"Durée: {duree}", f"Transport: {transport}"])
        )
        if len(full_text.strip()) < 20:
            continue

        records.append(
            {
                "source_type": "circuit",
                "source_id": source_id,
                "title": nom,
                "language": "fr",
                "text": full_text.strip(),
                "metadata": {
                    "circuit_name": nom,
                    "duree": duree,
                    "transport": transport,
                },
            }
        )

    logger.info("Circuits chargés : %d", len(records))
    return records


# ─── Insertion en base ─────────────────────────────────────────────────────────
def clear_historical_data(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM historical_chunks")
    conn.commit()
    logger.info("Table historical_chunks vidée.")


def insert_chunks(
    conn: psycopg2.extensions.connection,
    chunks: list[dict[str, Any]],
) -> int:
    """
    Insère les chunks avec leurs embeddings.
    Utilise FLOAT[] (pas pgvector).
    """
    inserted = 0
    with conn.cursor() as cur:
        for chunk in chunks:
            embedding = chunk["embedding"]
            # Convertir en liste Python standard si numpy array
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()

            cur.execute(
                """
                INSERT INTO historical_chunks
                    (source_type, source_id, title, language, chunk_text, metadata_json, embedding)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk["source_type"],
                    chunk["source_id"],
                    chunk["title"],
                    chunk["language"],
                    chunk["chunk_text"],
                    json.dumps(chunk["metadata"], ensure_ascii=False),
                    embedding,  # FLOAT[] accepte une liste Python directement
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


# ─── Pipeline principal ────────────────────────────────────────────────────────
def run_ingestion(source_dir: Path, *, clear: bool = False) -> None:
    conn = get_conn()

    if clear:
        clear_historical_data(conn)

    model = load_embedding_model()

    all_records: list[dict[str, Any]] = []

    # Monuments
    monuments_file = source_dir / "Monuments.xlsx"
    if monuments_file.exists():
        all_records.extend(load_monuments(monuments_file))
    else:
        logger.warning("Monuments.xlsx non trouvé dans %s", source_dir)

    # Circuits
    circuits_file = source_dir / "Tab_circuit.xlsx"
    if circuits_file.exists():
        all_records.extend(load_circuits(circuits_file))

    if not all_records:
        logger.error("Aucun document à ingérer. Vérifier le chemin --source.")
        sys.exit(1)

    # Découper en chunks et embedder
    all_chunks: list[dict[str, Any]] = []
    for record in all_records:
        text_chunks = chunk_text(record["text"])
        for i, chunk_text_content in enumerate(text_chunks):
            all_chunks.append(
                {
                    "source_type": record["source_type"],
                    "source_id": record["source_id"],
                    "title": record["title"],
                    "language": record["language"],
                    "chunk_text": chunk_text_content,
                    "metadata": {**record["metadata"], "chunk_index": i},
                    "embedding": None,  # sera rempli ci-dessous
                }
            )

    logger.info("Total chunks à embedder : %d", len(all_chunks))

    # Embedding par batch
    texts = [c["chunk_text"] for c in all_chunks]
    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[batch_start : batch_start + BATCH_SIZE]
        batch_vecs = embed_texts(model, batch_texts)
        for j, vec in enumerate(batch_vecs):
            all_chunks[batch_start + j]["embedding"] = vec
        logger.info("Batch %d/%d embeddé", batch_start + len(batch_texts), len(texts))

    # Insertion
    inserted = insert_chunks(conn, all_chunks)
    logger.info("✅ %d chunks insérés dans historical_chunks (sig_dourbia)", inserted)
    conn.close()


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingestion des données historiques Carthage dans sig_dourbia"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/raw/excel"),
        help="Dossier contenant les fichiers Excel (défaut: data/raw/excel)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Vider historical_chunks avant l'ingestion",
    )
    args = parser.parse_args()

    if not args.source.exists():
        logger.error("Dossier source introuvable : %s", args.source)
        sys.exit(1)

    run_ingestion(args.source, clear=args.clear)
