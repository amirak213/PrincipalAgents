

import json
import numpy as np
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics


class AgentFeedback:
    
    
    def __init__(self, systeme_recommandation):
       
        self.systeme = systeme_recommandation
        self.nom = "Agent Feedback"
        self.version = "1.0"
        
        # Stockage des feedbacks
        self.historique_feedbacks = []
        self.tendances = {}
        self.scores_confiance = {}
        
        # Statistiques d'apprentissage
        self.matrices_preferences = defaultdict(lambda: defaultdict(list))
        self.correlations = {}
        
        print(f"✅ AgentFeedback initialisé - Version {self.version}")
    
    def enregistrer_feedback(self, user_id, circuit_id, note, commentaire=""):
        
        
        # Validation de la note
        note = max(0, min(5, note))  # Entre 0 et 5
        
        # Création du feedback
        feedback = {
            'user_id': user_id,
            'circuit_id': circuit_id,
            'note': note,
            'commentaire': commentaire,
            'timestamp': datetime.now().isoformat(),
            'jour_semaine': datetime.now().strftime('%A'),
            'heure': datetime.now().hour,
            'analyse': self._analyser_feedback(user_id, circuit_id, note)
        }
        
        # Enrichir l'analyse
        feedback['analyse'].update({
            'comparaison_moyenne': self._comparer_a_la_moyenne(circuit_id, note),
            'tendance_temporelle': self._analyser_tendance_temporelle(user_id),
            'profil_compatibilite': self._evaluer_compatibilite_profil(user_id, circuit_id)
        })
        
        # Sauvegarder
        self.historique_feedbacks.append(feedback)
        self._mettre_a_jour_tendances(feedback)
        self._mettre_a_jour_matrices_preferences(feedback)
        
        # Mettre à jour le système principal
        self.systeme.simuler_feedback(user_id, circuit_id, note)
        
        # Calculer le score de confiance
        self._mettre_a_jour_score_confiance(user_id)
        
        print(f"✅ Feedback enregistré - User:{user_id} Circuit:{circuit_id} Note:{note}/5")
        
        return feedback
    
    def _analyser_feedback(self, user_id, circuit_id, note):
        
        analyse = {
            'sentiment': 'neutre',
            'intensite': 'moderee',
            'action_recommandee': 'observer',
            'confiance': 0.5
        }
        
        # Déterminer le sentiment
        if note >= 4:
            analyse['sentiment'] = 'positif'
            analyse['intensite'] = 'forte' if note == 5 else 'moderee'
            analyse['action_recommandee'] = 'renforcer_preferences_similaires'
            analyse['confiance'] = 0.9 if note == 5 else 0.7
            
        elif note <= 2:
            analyse['sentiment'] = 'negatif'
            analyse['intensite'] = 'forte' if note == 0 else 'moderee'
            analyse['action_recommandee'] = 'eviter_circuits_similaires'
            analyse['confiance'] = 0.9 if note == 0 else 0.7
            
        else:  # note = 3
            analyse['sentiment'] = 'neutre'
            analyse['action_recommandee'] = 'proposer_variantes'
            analyse['confiance'] = 0.4
        
        # Analyser le commentaire si présent
        if analyse.get('commentaire'):
            analyse['mots_cles'] = self._extraire_mots_cles(analyse['commentaire'])
        
        return analyse
    
    def _extraire_mots_cles(self, commentaire):
        """Extrait les mots clés d'un commentaire"""
        mots_importants = [
            'super', 'magnifique', 'beau', 'intéressant', 'culturel',
            'cher', 'long', 'fatigant', 'génial', 'décevant', 'parfait'
        ]
        
        mots_trouves = []
        commentaire_lower = commentaire.lower()
        
        for mot in mots_importants:
            if mot in commentaire_lower:
                mots_trouves.append(mot)
        
        return mots_trouves
    
    def _comparer_a_la_moyenne(self, circuit_id, note):
        """Compare une note à la moyenne du circuit"""
        # Récupérer toutes les notes de ce circuit
        notes_circuit = [
            f['note'] for f in self.historique_feedbacks 
            if f['circuit_id'] == circuit_id
        ]
        
        if not notes_circuit:
            return {
                'moyenne_actuelle': None,
                'ecart': None,
                'interpretation': 'premier feedback pour ce circuit'
            }
        
        moyenne = statistics.mean(notes_circuit)
        ecart = note - moyenne
        
        if ecart > 1:
            interpretation = 'bien mieux que la moyenne'
        elif ecart > 0.5:
            interpretation = 'mieux que la moyenne'
        elif ecart < -1:
            interpretation = 'bien moins bien que la moyenne'
        elif ecart < -0.5:
            interpretation = 'moins bien que la moyenne'
        else:
            interpretation = 'dans la moyenne'
        
        return {
            'moyenne_actuelle': round(moyenne, 2),
            'ecart': round(ecart, 2),
            'interpretation': interpretation
        }
    
    def _analyser_tendance_temporelle(self, user_id):
        """Analyse l'évolution des notes d'un utilisateur dans le temps"""
        feedbacks_user = [
            f for f in self.historique_feedbacks 
            if f['user_id'] == user_id
        ]
        
        if len(feedbacks_user) < 3:
            return {
                'tendance': 'insuffisant',
                'pente': None,
                'interpretation': "Pas assez de données"
            }
        
        # Trier par date
        feedbacks_user.sort(key=lambda x: x['timestamp'])
        notes = [f['note'] for f in feedbacks_user[-5:]]  # 5 derniers
        
        if len(notes) >= 2:
            # Calculer la tendance (simple)
            if notes[-1] > notes[0]:
                tendance = 'croissante'
                interpretation = "L'utilisateur apprécie de plus en plus"
            elif notes[-1] < notes[0]:
                tendance = 'décroissante'
                interpretation = "L'utilisateur est de plus en plus exigeant"
            else:
                tendance = 'stable'
                interpretation = "Préférences stables"
        else:
            tendance = 'stable'
            interpretation = "Pas assez de données"
        
        return {
            'tendance': tendance,
            'dernieres_notes': notes,
            'interpretation': interpretation
        }
    
    def _evaluer_compatibilite_profil(self, user_id, circuit_id):
        """Évalue la compatibilité d'un circuit avec le profil utilisateur"""
        client = self.systeme.get_client(user_id)
        circuit = None
        
        # Trouver le circuit
        for c in self.systeme.calculateur.circuits:
            if c.get('circuit_id') == circuit_id:
                circuit = c
                break
        
        if not client or not circuit:
            return {'score': 0.5, 'explication': 'Données insuffisantes'}
        
        score = 0.5  # Score de base
        explications = []
        
        # Compatibilité d'époque
        if hasattr(client, 'preference_epoque') and client.preference_epoque:
            # Logique à implémenter selon vos données
            score += 0.1
            explications.append("correspond aux époques")
        
        # Compatibilité de budget
        if hasattr(client, 'budget_max') and client.budget_max:
            prix = circuit.get('prix', 0)
            if prix <= client.budget_max:
                score += 0.2
                explications.append("dans le budget")
            else:
                score -= 0.1
                explications.append("hors budget")
        
        # Compatibilité de durée
        if hasattr(client, 'duree_max') and client.duree_max:
            duree = circuit.get('duree_totale', 0)
            if duree <= client.duree_max:
                score += 0.1
                explications.append("durée adaptée")
            else:
                score -= 0.1
                explications.append("trop long")
        
        return {
            'score': round(min(1, max(0, score)), 2),
            'explications': explications
        }
    
    def _mettre_a_jour_tendances(self, feedback):
        """Met à jour les tendances globales"""
        circuit_id = feedback['circuit_id']
        
        if circuit_id not in self.tendances:
            self.tendances[circuit_id] = {
                'total_notes': 0,
                'somme_notes': 0,
                'moyenne': 0,
                'feedbacks': [],
                'distribution_notes': {1:0, 2:0, 3:0, 4:0, 5:0},
                'premier_feedback': feedback['timestamp'],
                'dernier_feedback': feedback['timestamp']
            }
        
        # Mise à jour des stats
        self.tendances[circuit_id]['total_notes'] += 1
        self.tendances[circuit_id]['somme_notes'] += feedback['note']
        self.tendances[circuit_id]['moyenne'] = round(
            self.tendances[circuit_id]['somme_notes'] / 
            self.tendances[circuit_id]['total_notes'], 2
        )
        self.tendances[circuit_id]['feedbacks'].append(feedback)
        self.tendances[circuit_id]['distribution_notes'][int(feedback['note'])] += 1
        self.tendances[circuit_id]['dernier_feedback'] = feedback['timestamp']
    
    def _mettre_a_jour_matrices_preferences(self, feedback):
        """Met à jour les matrices de préférences pour l'apprentissage"""
        user_id = feedback['user_id']
        circuit_id = feedback['circuit_id']
        note = feedback['note']
        
        self.matrices_preferences[user_id][circuit_id] = note
        
        # Mettre à jour les corrélations (version simplifiée)
        if len(self.matrices_preferences[user_id]) > 1:
            # Logique de corrélation à implémenter
            pass
    
    def _mettre_a_jour_score_confiance(self, user_id):
        """Calcule le score de confiance pour un utilisateur"""
        feedbacks_user = [
            f for f in self.historique_feedbacks 
            if f['user_id'] == user_id
        ]
        
        if not feedbacks_user:
            self.scores_confiance[user_id] = 0.5
            return
        
        nb_feedbacks = len(feedbacks_user)
        regularite = min(1, nb_feedbacks / 10)  # Plus il y a de feedbacks, plus confiance
        coherence = self._calculer_coherence(feedbacks_user)
        
        self.scores_confiance[user_id] = round((regularite * 0.4 + coherence * 0.6), 2)
    
    def _calculer_coherence(self, feedbacks):
        """Calcule la cohérence des feedbacks d'un utilisateur"""
        if len(feedbacks) < 2:
            return 0.7
        
        notes = [f['note'] for f in feedbacks]
        variance = statistics.variance(notes) if len(notes) > 1 else 0
        
        # Moins de variance = plus de cohérence
        coherence = max(0, min(1, 1 - (variance / 5)))
        return coherence
    
    def analyser_tendances(self, periode_jours=30):
        
        rapport = {
            'periode_analyse': f"{periode_jours} derniers jours",
            'total_feedbacks': len(self.historique_feedbacks),
            'moyenne_generale': 0,
            'circuits_les_plus_apprecies': [],
            'circuits_a_revoir': [],
            'utilisateurs_les_plus_actifs': [],
            'distribution_globale': {1:0, 2:0, 3:0, 4:0, 5:0},
            'tendances_temporelles': {},
            'recommandations': []
        }
        
        if not self.historique_feedbacks:
            return rapport
        
        # Moyenne générale
        rapport['moyenne_generale'] = round(
            statistics.mean([f['note'] for f in self.historique_feedbacks]), 2
        )
        
        # Distribution globale
        for f in self.historique_feedbacks:
            rapport['distribution_globale'][int(f['note'])] += 1
        
        # Circuits les plus appréciés (min 3 feedbacks)
        circuits_stats = []
        for circuit_id, data in self.tendances.items():
            if data['total_notes'] >= 3:
                circuits_stats.append({
                    'circuit_id': circuit_id,
                    'moyenne': data['moyenne'],
                    'nb_feedbacks': data['total_notes'],
                    'dernier_feedback': data['dernier_feedback']
                })
        
        circuits_stats.sort(key=lambda x: x['moyenne'], reverse=True)
        rapport['circuits_les_plus_apprecies'] = circuits_stats[:5]
        
        # Circuits à revoir (moyenne < 2.5 et assez de feedbacks)
        a_revoir = [
            {'circuit_id': c['circuit_id'], 'moyenne': c['moyenne'], 'nb_feedbacks': c['nb_feedbacks']}
            for c in circuits_stats if c['moyenne'] < 2.5 and c['nb_feedbacks'] >= 3
        ]
        rapport['circuits_a_revoir'] = a_revoir[:3]
        
        # Utilisateurs les plus actifs
        user_counts = Counter([f['user_id'] for f in self.historique_feedbacks])
        rapport['utilisateurs_les_plus_actifs'] = [
            {'user_id': u, 'nb_feedbacks': c} 
            for u, c in user_counts.most_common(5)
        ]
        
        # Tendances temporelles (par jour)
        dates = {}
        for f in self.historique_feedbacks:
            date = f['timestamp'][:10]  # YYYY-MM-DD
            if date not in dates:
                dates[date] = {'notes': [], 'count': 0}
            dates[date]['notes'].append(f['note'])
            dates[date]['count'] += 1
        
        for date, data in list(dates.items())[-7:]:  # 7 derniers jours
            rapport['tendances_temporelles'][date] = {
                'nb_feedbacks': data['count'],
                'moyenne': round(statistics.mean(data['notes']), 2)
            }
        
        # Recommandations automatiques
        if rapport['moyenne_generale'] < 3.5:
            rapport['recommandations'].append(
                "La satisfaction générale est en baisse - revoir les circuits proposés"
            )
        
        if len(rapport['circuits_a_revoir']) > 2:
            rapport['recommandations'].append(
                "Plusieurs circuits sont mal notés - envisager des modifications"
            )
        
        if len(self.historique_feedbacks) < 50:
            rapport['recommandations'].append(
                "Encourager les utilisateurs à donner plus de feedbacks"
            )
        
        return rapport
    
    def get_recommandations_amelioration(self):
        """
        Génère des recommandations pour améliorer le système
        
        Returns:
            list: recommandations d'amélioration
        """
        recommandations = []
        tendances = self.analyser_tendances()
        
        # Basé sur les circuits à revoir
        if tendances['circuits_a_revoir']:
            circuits = [c['circuit_id'] for c in tendances['circuits_a_revoir']]
            recommandations.append({
                'type': 'circuits',
                'priorite': 'haute',
                'message': f"Revoir les circuits mal notés: {', '.join(circuits)}",
                'action': 'analyser_composition'
            })
        
        # Basé sur la distribution des notes
        if tendances['distribution_globale'][5] < tendances['distribution_globale'][3]:
            recommandations.append({
                'type': 'qualite',
                'priorite': 'moyenne',
                'message': "Peu de notes excellentes - chercher à améliorer la qualité",
                'action': 'enquete_satisfaction'
            })
        
        # Basé sur l'activité
        if tendances['total_feedbacks'] < 100:
            recommandations.append({
                'type': 'engagement',
                'priorite': 'basse',
                'message': "Encourager les feedbacks (gamification, récompenses)",
                'action': 'campagne_feedback'
            })
        
        return recommandations
    
    def get_circuits_populaires(self, n=5):
        """
        Retourne les circuits les plus populaires (basé sur nb de feedbacks)
        
        Args:
            n: nombre de circuits à retourner
        
        Returns:
            list: circuits les plus populaires
        """
        circuits_pop = []
        
        for circuit_id, data in self.tendances.items():
            circuits_pop.append({
                'circuit_id': circuit_id,
                'nb_feedbacks': data['total_notes'],
                'moyenne': data['moyenne']
            })
        
        circuits_pop.sort(key=lambda x: x['nb_feedbacks'], reverse=True)
        return circuits_pop[:n]
    
    def get_statistiques(self):
        
        return {
            'nom': self.nom,
            'version': self.version,
            'total_feedbacks': len(self.historique_feedbacks),
            'circuits_evalues': len(self.tendances),
            'utilisateurs_actifs': len(set(f['user_id'] for f in self.historique_feedbacks)),
            'moyenne_globale': round(
                statistics.mean([f['note'] for f in self.historique_feedbacks]), 2
            ) if self.historique_feedbacks else 0,
            'score_confiance_moyen': round(
                statistics.mean(self.scores_confiance.values()), 2
            ) if self.scores_confiance else 0,
            'dernier_feedback': self.historique_feedbacks[-1]['timestamp'] if self.historique_feedbacks else None
        }


