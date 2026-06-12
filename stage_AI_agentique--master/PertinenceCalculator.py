import pandas as pd
import json
import numpy as np
from collections import Counter

class PertinenceCalculator:

    def __init__(self, circuits_df=None, fichier_circuits_json=None):

        self.circuits = []

        if circuits_df is not None:
            self._charger_depuis_dataframe(circuits_df)
        elif fichier_circuits_json:
            self._charger_depuis_json(fichier_circuits_json)

        # Poids des différents critères (CORRIGÉ)
        self.poids = {
            'thematique': 0.35,      # Correspondance des époques/thèmes
            'types_preferes': 0.25,   # ← CORRIGÉ: 'types_preferes' au lieu de 'type_monument'
            'duree': 0.20,            # Respect de la durée max
            'budget': 0.15,           # Respect du budget
            'popularite': 0.05        # Score moyen du circuit
        }

    def _charger_depuis_dataframe(self, df):
        """Charge les circuits depuis un DataFrame"""
        for _, row in df.iterrows():
            circuit = {
                'circuit_id': row['circuit_id'],
                'indices': row['indices'],
                'noms': row['noms'],
                'nb_monuments': row['nb_monuments'],
                'duree_totale': row['duree_totale'],
                'score_moyen': row['score_moyen'],
                'cout_resident':   float(row.get('cout_resident',   0) or 0),
                'cout_etudiant':   float(row.get('cout_etudiant',   0) or 0),
                'cout_etranger':   float(row.get('cout_etranger',   0) or 0),
                'cout_enseignant': float(row.get('cout_enseignant', 0) or 0),
                'cout_retraite':   float(row.get('cout_retraite',   0) or 0),
                'cout_enfant':     float(row.get('cout_enfant',     0) or 0),
            }
            self.circuits.append(circuit)

    def _charger_depuis_json(self, fichier_json):
        """Charge les circuits depuis un fichier JSON"""
        try:
            with open(fichier_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for circuit_data in data:
                circuit = {
                    'circuit_id': circuit_data['circuit_id'],
                    'indices': circuit_data['indices'],
                    'noms': circuit_data['noms'],
                    'nb_monuments': circuit_data['nb_monuments'],
                    'duree_totale': circuit_data['duree_totale'],
                    'score_moyen': circuit_data['score_moyen'],
                    'tarifs': circuit_data['cout_par_categorie']
                }
                self.circuits.append(circuit)

        except FileNotFoundError:
            print(f"    Fichier non trouvé: {fichier_json}")

    def calculer_score_thematique(self, profil, circuit):

        # Vérifier si l'attribut existe
        if not hasattr(profil, 'preference_epoque') or not profil.preference_epoque:
            return 0.5  # Score neutre

        # Version simplifiée pour l'instant
        # Idéalement, il faudrait comparer avec les époques des monuments du circuit
        return 0.7

    def calculer_score_type(self, profil, circuit):

        # Vérifier si l'attribut existe
        if not hasattr(profil, 'types_preferes') or not profil.types_preferes:
            return 0.5

        # Version simplifiée pour l'instant
        # Idéalement, il faudrait comparer avec les types des monuments du circuit
        return 0.6

    def calculer_score_duree(self, profil, circuit):
        mobilite = (getattr(profil, 'mobilite', None) or 'normale').lower().strip()

        SEUILS = {
            'reduite':          120.0,
            'réduite':          120.0,
            'fauteuil roulant': 90.0,
        }
        seuil = SEUILS.get(mobilite)
        duree_circuit = float(circuit["duree_totale"])

        # Filtrage dur — mobilité incompatible
        if seuil and duree_circuit > seuil:
            return 0.0

        if not getattr(profil, 'duree_max', None) or profil.duree_max <= 0:
            return 1.0

        if duree_circuit <= profil.duree_max:
            score = 0.8 + 0.2 * (duree_circuit / profil.duree_max)
        else:
            dep = (duree_circuit - profil.duree_max) / profil.duree_max
            score = max(0.0, 0.8 - dep * 2) if dep <= 0.2 else 0.0

        # Bonus circuits courts pour mobilité réduite
        if mobilite in ('reduite', 'réduite', 'fauteuil roulant'):
            if duree_circuit <= profil.duree_max * 0.7:
                score = min(1.0, score + 0.1)

        return score

    def calculer_score_transport(self, profil, circuit):
        """
        Pas encore utilisé dans le score global (transport n'est pas dans les poids),
        mais retourne la durée de trajet réelle selon le moyen de transport
        pour l'affichage dans les cards terminal.
        """
        transport = getattr(profil, 'transport', 'voiture') or 'voiture'

        MAPPING_TRANSPORT = {
            'voiture':             'duree_voiture_min',
            'à pied':              'duree_pied_min',
            'vélo':                'duree_velo_min',
            'transport en commun': 'duree_voiture_min',  # approximation
        }
        return MAPPING_TRANSPORT.get(transport, 'duree_voiture_min')

    def calculer_score_budget(self, profil, circuit):

        if not hasattr(profil, 'budget_max') or not profil.budget_max or profil.budget_max <= 0:
            return 1.0

        # Récupérer le tarif correspondant au type du client
        type_tarif = (
            (profil.type_tarif or "resident").lower().strip()
            if hasattr(profil, "type_tarif") and profil.type_tarif
            else "resident"
        )

        # Mapping des types de tarif
        mapping_col = {
             'resident': 'cout_resident', 'résident': 'cout_resident',
             'etudiant': 'cout_etudiant', 'étudiant': 'cout_etudiant',
             'etranger': 'cout_etranger', 'étranger': 'cout_etranger',
             'enseignant': 'cout_enseignant',
             'retraite': 'cout_retraite', 'retraité': 'cout_retraite',
             'enfant': 'cout_enfant',
        }

        col = mapping_col.get(type_tarif, "cout_resident")
        cout_circuit = float(str(circuit.get(col, circuit.get('cout_etranger', 0))).replace(',', '.') or 0)
        try:
            cout_circuit = float(str(cout_circuit).replace(',', '.') or 0)
        except Exception:
            return 1.0

        if cout_circuit == 0:
            return 1.0

        if cout_circuit <= profil.budget_max:
            # Dans le budget
            return 0.7 + 0.3 * (1 - cout_circuit / profil.budget_max)
        else:
            return 0

    def calculer_score_popularite(self, profil, circuit):

        score_normalise = (circuit['score_moyen'] - 1) / 4
        return max(0, min(1, score_normalise))

    def calculer_pertinence(self, profil, circuit):
        circuit = {
            k: (
                float(v)
                if hasattr(v, "__float__") and not isinstance(v, (str, list, dict))
                else v
            )
            for k, v in circuit.items()
        }

        scores = {
            'thematique': self.calculer_score_thematique(profil, circuit),
            'types_preferes': self.calculer_score_type(profil, circuit),  # ← CORRIGÉ
            'duree': self.calculer_score_duree(profil, circuit),
            'budget': self.calculer_score_budget(profil, circuit),
            'popularite': self.calculer_score_popularite(profil, circuit)
        }

        # Score pondéré
        score_global = sum(
            scores[critere] * self.poids[critere] 
            for critere in self.poids.keys()
        )

        return {
            "circuit_id": circuit["circuit_id"],
            "score_global": round(score_global, 3),
            "details": scores,
            "duree": circuit["duree_totale"],
            "prix": circuit.get('cout_etranger', circuit.get('cout_resident', 0)),
        }

    def recommander(self, profil, n_recommandations=3, exclure_ids=None):

        if not self.circuits:
            print("⚠️ Aucun circuit disponible")
            return []

        exclure_ids = exclure_ids or []
        recommandations = []

        for circuit in self.circuits:
            if circuit['circuit_id'] in exclure_ids:
                continue

            resultat = self.calculer_pertinence(profil, circuit)
            recommandations.append(resultat)

        # Trier par score décroissant
        recommandations.sort(key=lambda x: x['score_global'], reverse=True)

        return recommandations[:n_recommandations]

    def expliquer_recommandation(self, resultat):
        """
        Génère une explication pour une recommandation
        """
        explication = f"\n📌 Circuit {resultat['circuit_id']} - Score: {resultat['score_global']:.2f}\n"
        explication += f"   ⏱️  Durée: {resultat['duree']:.1f} min | 💰 Prix: {resultat['prix']:.1f} DT\n"
        explication += f"   Détail du score:\n"

        for critere, score in resultat['details'].items():
            pourcentage = int(score * 100)
            barre = '█' * (pourcentage // 10) + '░' * (10 - pourcentage // 10)
            explication += f"      • {critere.capitalize():15} [{barre}] {pourcentage}%\n"

        return explication
