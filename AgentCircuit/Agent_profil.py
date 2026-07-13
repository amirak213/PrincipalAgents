import json
from datetime import datetime


class AgentProfil:

    def __init__(self, systeme_recommandation):

        self.systeme = systeme_recommandation
        self.nom = "Agent Profil"
        self.version = "1.0"
        self.historique_analyses = []  # Pour tracer les analyses effectuées

    def analyser_preferences(self, user_id):

        # Récupérer le client
        client = self.systeme.get_client(user_id)
        if not client:
            print(f"❌ Client {user_id} non trouvé")
            return None

        # Construire le rapport d'analyse
        rapport = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "profil_actuel": {
                "epoques": getattr(client, "preference_epoque", []),
                "types": getattr(client, "types_preferes", []),
                "budget": getattr(client, "budget_max", None),
                "duree": getattr(client, "duree_max", None),
                "transport": getattr(client, "transport", None),
                "mobilite": getattr(client, "mobilite", None),
            },
            "analyse": {},
            "recommandations_profil": [],
            "stats": {},
        }

        # 1. Analyser la complétude du profil
        champs_renseignes = 0
        if rapport['profil_actuel']['epoques']:
            champs_renseignes += 1
        if rapport['profil_actuel']['types']:
            champs_renseignes += 1
        if rapport['profil_actuel']['budget']:
            champs_renseignes += 1
        if rapport['profil_actuel']['duree']:
            champs_renseignes += 1

        rapport['stats']['completude'] = f"{champs_renseignes}/6 champs renseignés"

        if champs_renseignes < 2:
            rapport['analyse']['completude'] = "Profil très incomplet"
            rapport['recommandations_profil'].append(
                "Compléter votre profil pour des recommandations plus précises"
            )
        elif champs_renseignes < 4:
            rapport['analyse']['completude'] = "Profil partiellement complet"
        else:
            rapport['analyse']['completude'] = "Profil complet"

        # 2. Analyser la cohérence des préférences
        if rapport['profil_actuel']['epoques'] and rapport['profil_actuel']['types']:
            # Exemple d'analyse de cohérence
            if len(rapport['profil_actuel']['epoques']) > 3 and len(rapport['profil_actuel']['types']) < 2:
                rapport['analyse']['coherence'] = "Beaucoup d'époques mais peu de types - profil éclectique"
            else:
                rapport['analyse']['coherence'] = "Profil équilibré"
        else:
            rapport['analyse']['coherence'] = "Cohérence non évaluable (préférences manquantes)"

        # 3. Suggérer des enrichissements
        # Suggestions basées sur les époques
        if len(rapport['profil_actuel']['epoques']) < 2:
            rapport['recommandations_profil'].append(
                "Ajoutez plus d'époques historiques pour diversifier les recommandations"
            )
        elif len(rapport['profil_actuel']['epoques']) > 5:
            rapport['recommandations_profil'].append(
                "Beaucoup d'époques - pensez à prioriser vos préférées"
            )

        # Suggestions basées sur les types
        if len(rapport['profil_actuel']['types']) < 2:
            rapport['recommandations_profil'].append(
                "Spécifiez plus de types de monuments (culturel, religieux, nature...)"
            )

        # Suggestions basées sur le budget
        if rapport['profil_actuel']['budget']:
            if rapport['profil_actuel']['budget'] < 30:
                rapport['recommandations_profil'].append(
                    "💰 Budget limité - nous privilégierons les circuits économiques"
                )
            elif rapport['profil_actuel']['budget'] > 100:
                rapport['recommandations_profil'].append(
                    "💎 Budget confortable - des circuits premium vous seront suggérés"
                )
        else:
            rapport['recommandations_profil'].append(
                "Ajoutez votre budget pour des suggestions adaptées"
            )

        # Suggestions basées sur la durée
        if not rapport['profil_actuel']['duree']:
            rapport['recommandations_profil'].append(
                "Précisez la durée souhaitée pour vos circuits"
            )

        # 4. Statistiques supplémentaires
        rapport['stats']['nb_recommandations'] = len(rapport['recommandations_profil'])

        # Enregistrer dans l'historique
        self.historique_analyses.append({
            'user_id': user_id,
            'timestamp': rapport['timestamp'],
            'completude': rapport['stats']['completude']
        })

        return rapport

    def enrichir_profil(self, user_id, nouvelles_preferences):

        client = self.systeme.get_client(user_id)
        if not client:
            print(f"❌ Client {user_id} non trouvé")
            return False

        modifications = []

        # Enrichir les époques
        if 'epoques' in nouvelles_preferences:
            anciennes = list(client.preference_epoque)
            client.preference_epoque = list(set(
                client.preference_epoque + nouvelles_preferences['epoques']
            ))
            nouvelles = set(client.preference_epoque) - set(anciennes)
            if nouvelles:
                modifications.append(f"+{len(nouvelles)} époque(s)")

        # Enrichir les types
        if 'types' in nouvelles_preferences:
            anciens = list(client.types_preferes)
            client.types_preferes = list(set(
                client.types_preferes + nouvelles_preferences['types']
            ))
            nouveaux = set(client.types_preferes) - set(anciens)
            if nouveaux:
                modifications.append(f"+{len(nouveaux)} type(s)")

        # Mettre à jour le budget si fourni
        if 'budget' in nouvelles_preferences:
            client.budget_max = nouvelles_preferences['budget']
            modifications.append("budget mis à jour")

        # Mettre à jour la durée si fournie
        if 'duree' in nouvelles_preferences:
            client.duree_max = nouvelles_preferences['duree']
            modifications.append("durée mise à jour")

        if 'transport' in nouvelles_preferences:
            client.transport = nouvelles_preferences['transport']
            modifications.append("transport mis à jour")

        if 'mobilite' in nouvelles_preferences:
            client.mobilite = nouvelles_preferences['mobilite']
            modifications.append("mobilité mise à jour")

        if modifications:
            print(f"✅ Profil {user_id} enrichi : {', '.join(modifications)}")
        else:
            print(f"ℹ️ Aucune modification pour {user_id}")

        return True

    def suggerer_completion_profil(self, user_id):

        client = self.systeme.get_client(user_id)
        if not client:
            return None

        suggestions = {
            'champs_manquants': [],
            'questions': [],
            'priorite': 'moyenne'
        }

        # Vérifier chaque champ
        if not client.preference_epoque:
            suggestions['champs_manquants'].append('epoques')
            suggestions['questions'].append(
                "Quelles époques historiques préférez-vous ? (antique, médiévale, moderne...)"
            )

        if not client.types_preferes:
            suggestions['champs_manquants'].append('types')
            suggestions['questions'].append(
                "Quels types de monuments aimez-vous ? (culturel, religieux, nature...)"
            )

        if not client.budget_max:
            suggestions['champs_manquants'].append('budget')
            suggestions['questions'].append(
                "Quel est votre budget approximatif par circuit ?"
            )

        if not client.duree_max:
            suggestions['champs_manquants'].append('duree')
            suggestions['questions'].append(
                "Quelle durée souhaitez-vous pour vos circuits ?"
            )
        if not getattr(client, 'transport', None):
            suggestions['champs_manquants'].append('transport')
            suggestions['questions'].append(
                "Quel est votre moyen de transport ? (voiture, à pied, vélo, transport en commun)"
            )

        if not getattr(client, 'mobilite', None):
            suggestions['champs_manquants'].append('mobilite')
            suggestions['questions'].append(
                "Quelle est votre mobilité ? (normale, réduite, fauteuil roulant)"
            )
        # Définir la priorité
        if len(suggestions['champs_manquants']) >= 3:
            suggestions['priorite'] = 'haute'
        elif len(suggestions['champs_manquants']) == 0:
            suggestions['priorite'] = 'basse'
            suggestions['message'] = "Profil déjà complet !"

        return suggestions

    def get_statistiques(self):

        return {
            'nom': self.nom,
            'version': self.version,
            'nb_analyses_effectuees': len(self.historique_analyses),
            'dernieres_analyses': self.historique_analyses[-5:] if self.historique_analyses else [],
            'clients_analyses': len(set(a['user_id'] for a in self.historique_analyses))
        }
