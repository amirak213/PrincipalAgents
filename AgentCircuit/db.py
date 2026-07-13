"""
╔══════════════════════════════════════════════════════════════╗
║          Couche d'accès PostgreSQL — sig_dourbia             ║
║  Remplace les lectures JSON par des requêtes SQL propres     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()
# ─────────────────────────────────────────────────────────────
# CONFIGURATION — modifie uniquement ces variables ou utilise
# des variables d'environnement (recommandé en prod)
# ─────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "dbname": os.environ.get("PG_DBNAME", "sig_dourbia"),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", ""),
    "client_encoding": "utf-8",
}


# ─────────────────────────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    """Context manager : ouvre, yield, ferme proprement."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def test_connexion() -> bool:
    """Retourne True si la base est joignable."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"  ✗ Connexion PostgreSQL impossible : {e}")
        return False


# ─────────────────────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────────────────────

def charger_tous_clients() -> dict:
    """
    Retourne un dict { user_id: profil_dict } depuis la table `clients`.
    La table est supposée avoir une colonne JSONB `data` OU des colonnes
    individuelles.  On tente d'abord la colonne `data` (format flexible),
    puis on construit un dict depuis les colonnes.
    """
    clients = {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM clients LIMIT 1")
                cols = [d.name for d in cur.description] if cur.description else []

                cur.execute("SELECT * FROM clients")
                rows = cur.fetchall()

        for row in rows:
            row = dict(row)
            # Déterminer la clé user_id
            uid = (row.get("user_id") or row.get("id") or
                   row.get("client_id") or str(row.get("id", "")))
            uid = str(uid).strip()

            # Si colonne JSONB `data` existe
            if "data" in row and isinstance(row["data"], (dict,)):
                profil = row["data"]
                profil.setdefault("user_id", uid)
            elif "data" in row and isinstance(row["data"], str):
                try:
                    profil = json.loads(row["data"])
                    profil.setdefault("user_id", uid)
                except Exception:
                    profil = dict(row)
            else:
                profil = dict(row)

            if uid:
                clients[uid] = profil

    except Exception as e:
        print(f"  ✗ Erreur chargement clients PG : {e}")

    return clients


def charger_client(user_id: str) -> dict | None:
    """Charge un seul client par son identifiant."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM clients WHERE user_id = %s OR id = %s",
                    (user_id, user_id)
                )
                row = cur.fetchone()
        if row is None:
            return None
        row = dict(row)
        uid = user_id
        if "data" in row and isinstance(row["data"], dict):
            profil = row["data"]
            profil.setdefault("user_id", uid)
            return profil
        if "data" in row and isinstance(row["data"], str):
            try:
                profil = json.loads(row["data"])
                profil.setdefault("user_id", uid)
                return profil
            except Exception:
                pass
        return row
    except Exception as e:
        print(f"  ✗ Erreur chargement client {user_id} : {e}")
        return None


# ─────────────────────────────────────────────────────────────
# CIRCUITS
# ─────────────────────────────────────────────────────────────

def charger_tous_circuits() -> list:
    """
    Retourne une liste de dicts depuis la table `circuits`.
    Même logique colonne `data` JSONB ou colonnes directes.
    """
    circuits = []
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM circuits")
                rows = cur.fetchall()

        for row in rows:
            row = dict(row)
            if "data" in row and isinstance(row["data"], dict):
                c = row["data"]
            elif "data" in row and isinstance(row["data"], str):
                try:
                    c = json.loads(row["data"])
                except Exception:
                    c = dict(row)
            else:
                c = dict(row)
            circuits.append(_fix_encoding(c))

    except Exception as e:
        print(f"  ✗ Erreur chargement circuits PG : {e}")

    return circuits


# ─────────────────────────────────────────────────────────────
# RECOMMANDATIONS
# ─────────────────────────────────────────────────────────────

def sauvegarder_feedback(user_id: str, circuit_id: str,
                          note: float, commentaire: str = "") -> bool:
    """
    Insère un feedback dans la table `recommandations`.
    Colonnes attendues : user_id, circuit_id, note, commentaire, created_at
    Si la table a une structure différente, adapter les noms de colonnes.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO recommandations
                        (user_id, circuit_id, note, commentaire)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, circuit_id, note, commentaire)
                )
            conn.commit()
        return True
    except Exception as e:
        print(f"  ✗ Erreur sauvegarde feedback : {e}")
        return False


def charger_recommandations(user_id: str | None = None) -> list:
    """Charge les recommandations/feedbacks, optionnellement filtrés."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if user_id:
                    cur.execute(
                        "SELECT * FROM recommandations WHERE user_id = %s ORDER BY created_at DESC",
                        (user_id,)
                    )
                else:
                    cur.execute("SELECT * FROM recommandations ORDER BY created_at DESC")
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"  ✗ Erreur chargement recommandations : {e}")
        return []


# ─────────────────────────────────────────────────────────────
# DISTANCES
# ─────────────────────────────────────────────────────────────

def charger_distances_circuit(monuments: list) -> list:
    """
    Retourne les distances entre lieux consécutifs d'un circuit.
    Cherche dans la table `distance` les paires (from_lieu, to_lieu)
    pour chaque étape consécutive de la liste monuments.
    Retourne une liste de dicts :
      { from_lieu, to_lieu, distance_m, distance_km,
        duree_pied_min, duree_velo_min, duree_voiture_min }
    """
    if not monuments or len(monuments) < 2:
        return []

    resultats = []
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                for i in range(len(monuments) - 1):
                    lieu_a = str(monuments[i]).strip()
                    lieu_b = str(monuments[i + 1]).strip()

                    # Cherche dans les deux sens (A→B ou B→A)
                    cur.execute("""
                        SELECT from_lieu, to_lieu,
                               distance_m, distance_km,
                               duree_pied_min, duree_velo_min, duree_voiture_min
                        FROM distance
                        WHERE (from_lieu ILIKE %s AND to_lieu ILIKE %s)
                           OR (from_lieu ILIKE %s AND to_lieu ILIKE %s)
                        LIMIT 1
                    """, (lieu_a, lieu_b, lieu_b, lieu_a))

                    row = cur.fetchone()
                    if row:
                        r = dict(row)
                        if r['from_lieu'].lower() == lieu_b.lower():
                            r['from_lieu'], r['to_lieu'] = lieu_a, lieu_b
                        resultats.append(r)
                    else:
                        # Pas trouvé → on insère un placeholder
                        resultats.append({
                            'from_lieu':        lieu_a,
                            'to_lieu':          lieu_b,
                            'distance_m':       None,
                            'distance_km':      None,
                            'duree_pied_min':   None,
                            'duree_velo_min':   None,
                            'duree_voiture_min': None,
                        })
    except Exception as e:
        print(f"  ✗ Erreur chargement distances : {e}")

    return resultats


def sauvegarder_client(profil: dict) -> bool:
    user_id = str(profil.get("user_id", "")).strip()
    if not user_id:
        print("  ✗ user_id manquant")
        return False
    try:
        import json as _json

        prefs = profil.get("epoques_preferees", [])
        prefs_jsonb = _json.dumps(
            {e: 1.0 for e in prefs} if isinstance(prefs, list) else prefs
        )
        types = profil.get("types_preferes", [])
        historique = profil.get("historique_circuits", [])
        notes_jsonb = _json.dumps(profil.get("historique_notes", {}))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clients (
                        user_id, preferences_thematiques, duree_max,
                        types_preferes, budget_max, mobilite,
                        zone_preferee, type_tarif, transport,
                        historique_circuits, historique_notes
                    ) VALUES (
                        %s, %s::jsonb, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s::jsonb
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        preferences_thematiques = EXCLUDED.preferences_thematiques,
                        duree_max               = EXCLUDED.duree_max,
                        types_preferes          = EXCLUDED.types_preferes,
                        budget_max              = EXCLUDED.budget_max,
                        mobilite                = EXCLUDED.mobilite,
                        zone_preferee           = EXCLUDED.zone_preferee,
                        type_tarif              = EXCLUDED.type_tarif,
                        transport               = EXCLUDED.transport,
                        historique_circuits     = EXCLUDED.historique_circuits,
                        historique_notes        = EXCLUDED.historique_notes
                """,
                    (
                        user_id,
                        prefs_jsonb,
                        profil.get("duree_max"),
                        types,
                        profil.get("budget_max"),
                        profil.get("mobilite", "normale"),
                        profil.get("destination", "Mixte"),
                        profil.get("tarif", "etranger"),
                        profil.get("transport", "voiture"),
                        historique,
                        notes_jsonb,
                    ),
                )
            conn.commit()
        return True
    except Exception as e:
        print(f"  ✗ Erreur sauvegarde client {user_id} : {e}")
        return False


def _fix_encoding(val):
    """Corrige les chaînes mal encodées Latin-1 → UTF-8."""
    if isinstance(val, str):
        try:
            return val.encode("latin-1").decode("utf-8")
        except Exception:
            return val
    if isinstance(val, list):
        return [_fix_encoding(i) for i in val]
    if isinstance(val, dict):
        return {k: _fix_encoding(v) for k, v in val.items()}
    return val
