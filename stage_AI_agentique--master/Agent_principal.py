

import json
from datetime import datetime
import random
import statistics

# Import des autres agents
from Agent_profil import AgentProfil
from Agent_circuit import AgentCircuit
from Agent_feedback import AgentFeedback


class AgentRecommandationPrincipal:
    
    
    def __init__(self, systeme_recommandation):
       
        self.systeme = systeme_recommandation
        self.nom = "Agent Principal"
        self.version = "1.0"
        
        # Initialisation des agents spécialisés
        self.agent_profil = AgentProfil(systeme_recommandation)
        self.agent_circuit = AgentCircuit(systeme_recommandation)
        self.agent_feedback = AgentFeedback(systeme_recommandation)
        
        # Contexte global du système
        self.contexte = {
            'derniere_interaction': None,
            'clients_actifs': [],
            'tendances_saisonnieres': self._initialiser_tendances(),
            'statistiques_globales': {},
            'mode_operationnel': 'normal',  # normal, apprentissage, maintenance
            'performance': {
                'temps_moyen_reponse': 0,
                'taux_satisfaction': 0,
                'nb_recommandations_generees': 0
            }
        }
        
      
    
    def _initialiser_tendances(self):
        """Initialise les tendances saisonnières"""
        return {
            'printemps': {
                'mois': [3, 4, 5],
                'types_favoris': ['culturel', 'nature'],
                'duree_ideale': 180,  # 3h
                'themes': ['floraison', 'histoire', 'decouverte']
            },
            'ete': {
                'mois': [6, 7, 8],
                'types_favoris': ['nature', 'plage', 'loisirs'],
                'duree_ideale': 120,  # 2h (moins long à cause de la chaleur)
                'themes': ['rafraichissant', 'ombre', 'soiree']
            },
            'automne': {
                'mois': [9, 10, 11],
                'types_favoris': ['musee', 'culturel', 'religieux'],
                'duree_ideale': 210,  # 3h30
                'themes': ['couleurs', 'patrimoine', 'confort']
            },
            'hiver': {
                'mois': [12, 1, 2],
                'types_favoris': ['religieux', 'musee', 'culturel'],
                'duree_ideale': 150,  # 2h30
                'themes': ['chaleureux', 'intérieur', 'tradition']
            }
        }
    
    def _get_saison_actuelle(self):
        """Détermine la saison actuelle"""
        mois = datetime.now().month
        
        for saison, data in self.contexte['tendances_saisonnieres'].items():
            if mois in data['mois']:
                return saison
        return 'printemps'  # Défaut
    
    def recommander_intelligemment(self, user_id, n=3, contexte_supplementaire=None):
       
        # Vérifier le client
        client = self.systeme.get_client(user_id)
        if not client:
            return {
                'success': False,
                'error': 'Client non trouvé',
                'user_id': user_id
            }
        
        
        
        # 1. Obtenir les recommandations de base du système
        recommandations_base = self.systeme.recommander_pour_client(user_id, n * 2)
        
        if 'error' in recommandations_base:
            return recommandations_base
        
        # 2. Enrichir avec le contexte
        saison = self._get_saison_actuelle()
        contexte = {
            'saison': saison,
            'timestamp': datetime.now().isoformat(),
            'tendances_saison': self.contexte['tendances_saisonnieres'][saison]
        }
        
        if contexte_supplementaire:
            contexte.update(contexte_supplementaire)
        
        # 3. Améliorer chaque recommandation avec les agents
        recommandations_ameliorees = []
        
        for rec in recommandations_base['recommandations']:
            circuit_id = rec['circuit_id']
            
            # Enrichissement par AgentCircuit
            similaires = self.agent_circuit.suggerer_circuit_similaire(circuit_id, n=2)
            
            # Adaptation saisonnière
            adaptation_saison = self._adapter_a_la_saison(rec, saison)
            
            # Vérifier les feedbacks récents
            feedbacks_recents = self._check_feedbacks_recents(circuit_id)
            
            # Construire la recommandation enrichie
            rec_amelioree = {
                **rec,
                'metadonnees_agents': {
                    'similaires': similaires,
                    'adaptation_saison': adaptation_saison,
                    'feedbacks_recents': feedbacks_recents,
                    'categorie': self._trouver_categorie_circuit(circuit_id)
                },
                'score_agent': self._calculer_score_agent(rec, client, contexte)
            }
            
            # Recalculer le score global (moyenne du score système et score agent)
            rec_amelioree['score_global'] = round(
                (rec['score_global'] + rec_amelioree['score_agent']) / 2, 3
            )
            
            recommandations_ameliorees.append(rec_amelioree)
        
        # 4. Trier par score global
        recommandations_ameliorees.sort(key=lambda x: x['score_global'], reverse=True)
        
        # 5. Mettre à jour le contexte
        self._mettre_a_jour_contexte(user_id, len(recommandations_ameliorees))
        
        # 6. Générer des explications
        explications = self._generer_explications(recommandations_ameliorees[:n], client)
        
        resultat = {
            'success': True,
            'user_id': user_id,
            'recommandations': recommandations_ameliorees[:n],
            'contexte': contexte,
            'explications': explications,
            'stats': {
                'total_generees': len(recommandations_ameliorees),
                'avec_similaires': sum(1 for r in recommandations_ameliorees if r['metadonnees_agents']['similaires']),
                'saison_prise_en_compte': saison,
                'timestamp': datetime.now().isoformat()
            }
        }
        
      
        
        return resultat
    
    def _adapter_a_la_saison(self, recommandation, saison):
        """Adapte une recommandation à la saison"""
        adaptation = {
            'pertinence_saison': 'moyenne',
            'ajustement_score': 0,
            'message': ''
        }
        
        types_favoris = self.contexte['tendances_saisonnieres'][saison]['types_favoris']
        duree_ideale = self.contexte['tendances_saisonnieres'][saison]['duree_ideale']
        
        # Vérifier le type
        if recommandation.get('type_dominant') in types_favoris:
            adaptation['pertinence_saison'] = 'forte'
            adaptation['ajustement_score'] = 0.2
            adaptation['message'] = f"Parfait pour {saison} !"
        else:
            adaptation['ajustement_score'] = -0.1
            adaptation['message'] = f"Circuit {'adapté' if adaptation['ajustement_score'] > 0 else 'moins adapté'} à {saison}"
        
        # Adapter à la durée idéale
        duree = recommandation.get('duree_totale', 0)
        if abs(duree - duree_ideale) < 30:
            adaptation['ajustement_score'] += 0.1
        elif duree > duree_ideale + 60:
            adaptation['ajustement_score'] -= 0.1
        
        return adaptation
    
    def _check_feedbacks_recents(self, circuit_id):
        """Vérifie les feedbacks récents d'un circuit"""
        if circuit_id in self.agent_feedback.tendances:
            data = self.agent_feedback.tendances[circuit_id]
            return {
                'nb_feedbacks': data['total_notes'],
                'moyenne': data['moyenne'],
                'recents': data['feedbacks'][-3:] if data['feedbacks'] else []
            }
        return {
            'nb_feedbacks': 0,
            'moyenne': None,
            'recents': []
        }
    
    def _trouver_categorie_circuit(self, circuit_id):
        """Trouve la catégorie d'un circuit"""
        for categorie, circuits in self.agent_circuit.categories.items():
            if circuit_id in circuits:
                return categorie
        return 'non_categorise'
    
    def _calculer_score_agent(self, recommandation, client, contexte):
      
        score = 0.5  # Score de base
        
        # 1. Compatibilité avec le profil (AgentProfil)
        compatibilite = self.agent_feedback._evaluer_compatibilite_profil(
            getattr(client, 'id', 'unknown'), 
            recommandation['circuit_id']
        )
        score += compatibilite['score'] * 0.3
        
        # 2. Adaptation saisonnière
        if 'adaptation_saison' in recommandation.get('metadonnees_agents', {}):
            score += recommandation['metadonnees_agents']['adaptation_saison']['ajustement_score']
        
        # 3. Popularité réelle (basée sur feedbacks)
        feedbacks = self._check_feedbacks_recents(recommandation['circuit_id'])
        if feedbacks['moyenne']:
            score += (feedbacks['moyenne'] / 5) * 0.2
        
        # 4. Bonus pour les circuits avec des similaires
        if recommandation.get('metadonnees_agents', {}).get('similaires'):
            score += 0.1
        
        return round(min(1, max(0, score)), 3)
    
    def _generer_explications(self, recommandations, client):
        """Génère des explications personnalisées pour les recommandations"""
        explications = []
        
        if not recommandations:
            return explications
        
        # Explication sur le top 1
        top1 = recommandations[0]
        explications.append({
            'type': 'top',
            'message': f"Notre meilleure suggestion pour vous aujourd'hui",
            'raison': self._trouver_raison_recommandation(top1, client)
        })
        
        # Explication sur la diversité
        categories = set(r.get('metadonnees_agents', {}).get('categorie') for r in recommandations)
        if len(categories) > 2:
            explications.append({
                'type': 'diversite',
                'message': f"Nous avons diversifié vos suggestions avec {len(categories)} types de circuits"
            })
        
        # Explication saisonnière
        saison = self._get_saison_actuelle()
        explications.append({
            'type': 'saison',
            'message': f"Adapté à la saison ({saison})"
        })
        
        return explications
    
    def _trouver_raison_recommandation(self, recommandation, client):
        """Trouve la raison principale d'une recommandation"""
        raisons = []
        
        # Raison basée sur les préférences
        if hasattr(client, 'types_preferes') and client.types_preferes:
            raisons.append("correspond à vos types préférés")
        
        # Raison basée sur la popularité
        if recommandation.get('score_global', 0) > 0.8:
            raisons.append("très apprécié par d'autres visiteurs")
        
        # Raison basée sur la saison
        if recommandation.get('metadonnees_agents', {}).get('adaptation_saison', {}).get('pertinence_saison') == 'forte':
            raisons.append("idéal pour la saison")
        
        return " • ".join(raisons) if raisons else "correspond à votre profil"
    
    def _mettre_a_jour_contexte(self, user_id, nb_recommandations):
        """Met à jour le contexte global"""
        self.contexte['derniere_interaction'] = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'nb_recommandations': nb_recommandations
        }
        
        if user_id not in self.contexte['clients_actifs']:
            self.contexte['clients_actifs'].append(user_id)
        
        self.contexte['performance']['nb_recommandations_generees'] += 1
    
    def traiter_feedback_utilisateur(self, user_id, circuit_id, note, commentaire=""):
        
        print(f"\n📝 Traitement du feedback de {user_id}...")
        
        # Enregistrer via AgentFeedback
        feedback = self.agent_feedback.enregistrer_feedback(
            user_id, circuit_id, note, commentaire
        )
        
        # Analyser les tendances après ce feedback
        tendances = self.agent_feedback.analyser_tendances()
        
        # Mettre à jour le score de satisfaction global
        self.contexte['performance']['taux_satisfaction'] = (
            self.contexte['performance']['taux_satisfaction'] * 0.9 + note * 0.1
        )
        
        # Vérifier si le profil doit être enrichi
        if note >= 4:  # Feedback positif
            self._enrichir_profil_si_pertinent(user_id, circuit_id)
        
        resultat = {
            'success': True,
            'feedback': feedback,
            'tendances_mises_a_jour': {
                'moyenne_globale': tendances['moyenne_generale'],
                'circuit_ameliore': circuit_id in [c['circuit_id'] for c in tendances['circuits_les_plus_apprecies']]
            },
            'remerciement': self._generer_remerciement(note)
        }
        
        print(f"✅ Feedback traité avec succès")
        
        return resultat
    
    def _enrichir_profil_si_pertinent(self, user_id, circuit_id):
        """Enrichit le profil si le feedback est très positif"""
        # Trouver le circuit
        circuit = None
        for c in self.systeme.calculateur.circuits:
            if c.get('circuit_id') == circuit_id:
                circuit = c
                break
        
        if circuit and circuit.get('types_monuments'):
            # Suggérer d'ajouter ces types aux préférences
            nouvelles_prefs = {
                'types': circuit.get('types_monuments', [])
            }
            self.agent_profil.enrichir_profil(user_id, nouvelles_prefs)
    
    def _generer_remerciement(self, note):
        """Génère un message de remerciement personnalisé"""
        if note >= 4:
            return "Merci pour votre excellent retour ! 😊"
        elif note >= 3:
            return "Merci pour votre retour, nous nous améliorons !"
        else:
            return "Merci pour votre honnêteté, nous allons nous améliorer !"
    
    def analyser_profil_et_suggérer(self, user_id):
        
        print(f"\n🔍 Analyse approfondie du profil {user_id}...")
        
        # Analyse par AgentProfil
        analyse_profil = self.agent_profil.analyser_preferences(user_id)
        
        if not analyse_profil:
            return {'success': False, 'error': 'Profil non trouvé'}
        
        # Suggestions de complétion
        suggestions = self.agent_profil.suggerer_completion_profil(user_id)
        
        # Statistiques des feedbacks de l'utilisateur
        feedbacks_user = [
            f for f in self.agent_feedback.historique_feedbacks 
            if f['user_id'] == user_id
        ]
        
        # Recommandations personnalisées d'amélioration
        recommandations = []
        
        if suggestions and suggestions['champs_manquants']:
            recommandations.append({
                'type': 'completion',
                'message': f"Complétez votre profil : {', '.join(suggestions['champs_manquants'])}",
                'questions': suggestions['questions']
            })
        
        if len(feedbacks_user) < 3:
            recommandations.append({
                'type': 'engagement',
                'message': "Donnez votre avis sur des circuits pour améliorer vos recommandations"
            })
        
        resultat = {
            'success': True,
            'user_id': user_id,
            'analyse_profil': analyse_profil,
            'suggestions_completion': suggestions,
            'statistiques_feedbacks': {
                'total': len(feedbacks_user),
                'moyenne': round(statistics.mean([f['note'] for f in feedbacks_user]), 2) if feedbacks_user else None,
                'dernier': feedbacks_user[-1] if feedbacks_user else None
            },
            'recommandations_personnalisees': recommandations
        }
        
        print(f"✅ Analyse du profil terminée")
        
        return resultat
    
    def circuit_mis_en_avant(self):
       
        
        circuit_jour = self.agent_circuit.circuit_du_jour()
        
        if not circuit_jour:
            return {'success': False, 'error': 'Aucun circuit disponible'}
        
        # Enrichir avec les feedbacks
        circuit_id = circuit_jour['circuit_id']
        feedbacks = self._check_feedbacks_recents(circuit_id)
        
        # Enrichir avec les similaires
        similaires = self.agent_circuit.suggerer_circuit_similaire(circuit_id, n=2)
        
        resultat = {
            'success': True,
            'circuit_du_jour': {
                **circuit_jour,
                'feedbacks': feedbacks,
                'similaires': similaires,
                'categorie': self._trouver_categorie_circuit(circuit_id)
            },
            'justification': circuit_jour['justifications'],
            'pourquoi_aujourdhui': self._expliquer_circuit_du_jour(circuit_jour)
        }
        
    
        
        return resultat
    
    def _expliquer_circuit_du_jour(self, circuit_jour):
        """Explique pourquoi ce circuit a été choisi aujourd'hui"""
        explications = []
        
        # Raison saisonnière
        saison = self._get_saison_actuelle()
        explications.append(f"Idéal pour {saison}")
        
        # Raison de popularité
        if circuit_jour.get('details', {}).get('popularite', 0) > 4:
            explications.append("Très populaire")
        
        # Raison de nouveauté
        if random.random() > 0.7:  # Simulé
            explications.append("Nouveauté")
        
        return explications
    
    def rapport_complet(self):
        
        print(f"\n📊 Génération du rapport complet...")
        
        rapport = {
            'timestamp': datetime.now().isoformat(),
            'agent_principal': {
                'nom': self.nom,
                'version': self.version,
                'contexte': {
                    'clients_actifs': len(self.contexte['clients_actifs']),
                    'mode': self.contexte['mode_operationnel'],
                    'derniere_interaction': self.contexte['derniere_interaction'],
                    'saison_actuelle': self._get_saison_actuelle()
                },
                'performance': self.contexte['performance']
            },
            'agent_profil': self.agent_profil.get_statistiques(),
            'agent_circuit': self.agent_circuit.get_statistiques(),
            'agent_feedback': self.agent_feedback.get_statistiques(),
            'synthese': {
                'total_clients_actifs': len(self.contexte['clients_actifs']),
                'total_circuits': len(self.systeme.calculateur.circuits),
                'total_feedbacks': len(self.agent_feedback.historique_feedbacks),
                'satisfaction_globale': self.contexte['performance']['taux_satisfaction'],
                'recommandations_agents': self._generer_recommandations_globales()
            }
        }
        
    
        
        return rapport
    
    def _generer_recommandations_globales(self):
        """Génère des recommandations globales basées sur tous les agents"""
        recommandations = []
        
        # De AgentFeedback
        recommandations.extend(self.agent_feedback.get_recommandations_amelioration())
        
        # De AgentProfil
        if self.agent_profil.historique_analyses:
            profils_incomplets = sum(
                1 for a in self.agent_profil.historique_analyses[-20:] 
                if "incomplet" in a.get('completude', '')
            )
            if profils_incomplets > 10:
                recommandations.append({
                    'type': 'profils',
                    'priorite': 'moyenne',
                    'message': "Encourager les utilisateurs à compléter leur profil"
                })
        
        # De AgentCircuit
        categories_vides = [c for c, data in self.agent_circuit.get_statistiques_categories().items() 
                           if data['nb_circuits'] == 0]
        if categories_vides:
            recommandations.append({
                'type': 'circuits',
                'priorite': 'basse',
                'message': f"Créer des circuits pour les catégories manquantes: {', '.join(categories_vides[:3])}"
            })
        
        return recommandations
    
    def get_statistiques(self):
        
        return {
            'nom': self.nom,
            'version': self.version,
            'clients_actifs': len(self.contexte['clients_actifs']),
            'recommandations_generees': self.contexte['performance']['nb_recommandations_generees'],
            'taux_satisfaction': round(self.contexte['performance']['taux_satisfaction'], 2),
            'saison_actuelle': self._get_saison_actuelle(),
            'mode_operationnel': self.contexte['mode_operationnel']
        }


