"""
Test manuel de cohérence des flags de session (Phase 0 - Tâche 3).
Simule le Scénario 1 : onboarding -> confirmation circuit -> guide GPS -> nouvel onboarding.
Vérifie que mode_guide_actif repasse bien à False.

Usage : python test_flags_coherence.py
"""

import asyncio
from orchestrateur import OrchestratorAgent
from session_memory import get_profile

SESSION_ID = "test-flags-scenario-1"

FLAGS_TO_WATCH = [
    "mode_onboarding",
    "attente_confirmation_circuit",
    "attente_validation_circuit",
    "attente_activation_guide",
    "mode_guide_actif",
]


def print_flags(step: str):
    profil = get_profile(SESSION_ID)
    print(f"\n--- État après: {step} ---")
    for flag in FLAGS_TO_WATCH:
        print(f"  {flag} = {profil.get(flag)}")
    return profil


async def main():
    orchestrateur = OrchestratorAgent()

    # Étape 1 : démarrer un onboarding (déclenché par une demande de circuit)
    reponse = await orchestrateur.handle_message(
        SESSION_ID, "je veux visiter Carthage et la Médina"
    )
    print(f"\n[Bot] {reponse}")
    print_flags("demande initiale de circuit (onboarding démarré)")

    # Étape 2 : répondre aux 8 questions d'onboarding avec les bons mots-clés
    reponses_onboarding = [
        "Je veux visiter Tunis.",  # destination
        "J'aime l'époque romaine et islamique.",  # epoques
        "Je préfère les sites culturels et historiques.",  # types
        "Ma mobilité est normale.",  # mobilite
        "3h30",  # duree
        "À pied",  # transport
        "100 DT",  # budget
        "Je suis étranger.",  # tarif
    ]
    for i, msg in enumerate(reponses_onboarding, 1):
        reponse = await orchestrateur.handle_message(SESSION_ID, msg)
        print(f"\n[Bot] (Q{i}) {reponse[:200]}...")

    profil = print_flags(
        "fin de l'onboarding (attente_validation_circuit attendu=True)"
    )

    # Étape 3 : confirmer un circuit
    # ⚠️ à ajuster si le format de confirmation attendu diffère
    reponse = await orchestrateur.handle_message(SESSION_ID, "le premier circuit")
    print(f"\n[Bot] {reponse[:200]}...")
    print_flags("confirmation du circuit (attente_activation_guide attendu=True)")

    # Étape 4 : activer le mode guide GPS
    reponse = await orchestrateur.handle_message(SESSION_ID, "oui active le guide")
    print(f"\n[Bot] {reponse[:200]}...")
    profil_guide = print_flags(
        "activation du mode guide (mode_guide_actif attendu=True)"
    )

    if profil_guide.get("mode_guide_actif") is not True:
        print(
            "\n⚠️  ATTENTION : mode_guide_actif n'a pas été activé — impossible de tester le reset."
        )
        print(
            "   Vérifie le format attendu pour confirmer le circuit et activer le guide."
        )
        return

    # Étape 5 : redemander un nouveau circuit -> DOIT réinitialiser mode_guide_actif
    reponse = await orchestrateur.handle_message(
        SESSION_ID, "en fait je veux plutôt un circuit à El Jem"
    )
    print(f"\n[Bot] {reponse[:200]}...")
    profil_final = print_flags(
        "nouvelle demande de circuit (le fix doit s'appliquer ici)"
    )

    # ── Vérification automatique ──────────────────────────────────
    print("\n" + "=" * 50)
    if profil_final.get("mode_guide_actif") is False:
        print("✅ TEST RÉUSSI : mode_guide_actif est bien repassé à False")
    else:
        print(
            f"❌ TEST ÉCHOUÉ : mode_guide_actif = {profil_final.get('mode_guide_actif')} (attendu False)"
        )
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
