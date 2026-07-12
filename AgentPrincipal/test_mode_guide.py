"""
test_mode_guide.py — Test end-to-end du flux mode guide GPS.

Simule :
1. Choix explicite d'un circuit par l'utilisateur
2. Appel GPS proche d'un monument du circuit
3. Confirmation "oui" → présentation narrative complète

Usage :
    python test_mode_guide.py
"""

import asyncio
from orchestrateur import OrchestratorAgent
from session_memory import get_active_circuit, get_profile
from geo_service import get_geo_service


async def main():
    orchestrateur = OrchestratorAgent()
    user_id = "test-guide-001"

    print("=" * 60)
    print("TEST 1 — Sélection explicite d'un circuit")
    print("=" * 60)

    # ⚠️ Adapte ce message pour matcher un vrai flux (demande circuit → onboarding → recommandations)
    # Ici on simule directement l'état "attente_validation_circuit" pour isoler le test du choix
    from session_memory import update_profile

    circuits_fake = {
        "circuits": [
            {"circuit_id": "1", "nom": "Circuit Carthage GIZ_pedestre"},
            {"circuit_id": "4", "nom": "Circuit la Marsa"},
        ]
    }
    update_profile(
        user_id,
        {
            "attente_validation_circuit": True,
            "derniers_circuits": circuits_fake,
        },
    )

    reponse = await orchestrateur.handle_message(user_id, "le premier")
    print(f"Réponse : {reponse}\n")

    circuit_actif = get_active_circuit(user_id)
    print(f"Circuit actif enregistré : {circuit_actif}")
    assert (
        circuit_actif == "1"
    ), f"ÉCHEC : circuit actif attendu '1', obtenu '{circuit_actif}'"
    print("✅ Circuit actif correctement enregistré\n")

    print("=" * 60)
    print("TEST 2 — Détection GPS proche d'un monument du circuit")
    print("=" * 60)

    geo = get_geo_service()

    # ⚠️ Remplace ces coordonnées par celles d'un vrai monument du circuit "1"
    # (ex: Colline de Byrsa, Carthage — à ajuster selon tes vraies données)
    lat_test = 36.8565
    lon_test = 10.3310

    nearby = await geo.get_nearby_monuments_for_circuit(
        lat=lat_test, lon=lon_test, circuit_id="1", rayon_override_m=300
    )

    print(f"Monuments trouvés : {len(nearby)}")
    for m in nearby:
        print(f"  - {m['nom']} ({m['distance_m']}m)")

    assert (
        len(nearby) > 0
    ), "ÉCHEC : aucun monument trouvé — vérifie les coordonnées GPS de test"
    print("✅ Monuments du circuit détectés à proximité\n")

    print("=" * 60)
    print("TEST 3 — handle_proximity_trigger() + confirmation utilisateur")
    print("=" * 60)

    monument_test = nearby[0]
    await orchestrateur.handle_proximity_trigger(
        user_id=user_id,
        monument_id=monument_test["id"],
        monument_nom=monument_test["nom"],
        langue="FR",
    )

    profil = get_profile(user_id)
    monument_en_attente = profil.get("monument_en_attente")
    print(f"Monument en attente : {monument_en_attente}")
    assert monument_en_attente is not None, "ÉCHEC : monument_en_attente non enregistré"
    print("✅ monument_en_attente correctement posé\n")

    reponse_finale = await orchestrateur.handle_message(user_id, "oui")
    print(f"Réponse narrative finale :\n{reponse_finale}\n")

    profil_apres = get_profile(user_id)
    assert (
        profil_apres.get("monument_en_attente") is None
    ), "ÉCHEC : monument_en_attente non nettoyé après réponse"
    print("✅ monument_en_attente nettoyé après présentation\n")

    print("=" * 60)
    print("TOUS LES TESTS SONT PASSÉS ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
