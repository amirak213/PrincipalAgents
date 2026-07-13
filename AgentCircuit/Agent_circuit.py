

import json
import random
from datetime import datetime
from collections import Counter


class AgentCircuit:
   
    
    def __init__(self, systeme_recommandation):
       
        self.systeme = systeme_recommandation
        self.nom = "Agent Circuit"
        self.version = "1.0"
        
        # Catégorisation automatique des circuits
        self.categories = self._categoriser_circuits()
        
        # Historique des suggestions
        self.historique_suggestions = []
        self.circuits_du_jour_historique = []
        
        print(f"✅ AgentCircuit initialisé - Version {self.version}")
        print(f"   📊 {len(self.systeme.calculateur.circuits)} circuits analysés")
        print(f"   🏷️  Catégories: {', '.join(self.categories.keys())}")
    
    def _categoriser_circuits(self):
       
        categories = {
            'court': [],      # < 2h
            'moyen': [],      # 2-4h
            'long': [],       # > 4h
            'economique': [], # < 30€
            'premium': [],    # > 60€
            'standard': [],   # 30-60€
            'culturel': [],
            'nature': [],
            'religieux': [],
            'mixte': [],
            'familial': [],
            'romantique': [],
            'aventure': []
        }
        
        for circuit in self.systeme.calculateur.circuits:
            circuit_id = circuit.get('circuit_id', 'inconnu')
            duree = circuit.get('duree_totale', 0)
            prix = circuit.get('prix', 0)
            types = circuit.get('types_monuments', [])
            
            # Catégorisation par durée
            if duree < 120:
                categories['court'].append(circuit_id)
            elif duree < 240:
                categories['moyen'].append(circuit_id)
            else:
                categories['long'].append(circuit_id)
            
            # Catégorisation par prix
            if prix < 30:
                categories['economique'].append(circuit_id)
            elif prix > 60:
                categories['premium'].append(circuit_id)
            else:
                categories['standard'].append(circuit_id)
            
            # Catégorisation par type (basée sur les monuments)
            if types:
                # Compter les types de monuments dans le circuit
                type_counts = Counter(types)
                
                if type_counts.get('culturel', 0) > len(types)/2:
                    categories['culturel'].append(circuit_id)
                elif type_counts.get('nature', 0) > len(types)/2:
                    categories['nature'].append(circuit_id)
                elif type_counts.get('religieux', 0) > len(types)/2:
                    categories['religieux'].append(circuit_id)
                else:
                    categories['mixte'].append(circuit_id)
            
            # Autres catégories basées sur des heuristiques
            if len(types) >= 4:
                categories['familial'].append(circuit_id)
            
            if circuit.get('popularite_moyenne', 0) >= 4.5:
                categories['romantique'].append(circuit_id)
            
            if circuit.get('duree_totale', 0) > 300 or circuit.get('nb_monuments', 0) > 8:
                categories['aventure'].append(circuit_id)
        
        return categories
    
    def suggerer_circuit_similaire(self, circuit_id, n=3):
       
        # Trouver le circuit de référence
        circuit_ref = None
        for circuit in self.systeme.calculateur.circuits:
            if circuit.get('circuit_id') == circuit_id:
                circuit_ref = circuit
                break
        
        if not circuit_ref:
            print(f"❌ Circuit {circuit_id} non trouvé")
            return []
        
        similaires = []
        
        for circuit in self.systeme.calculateur.circuits:
            if circuit.get('circuit_id') == circuit_id:
                continue
            
            score = 0
            details = []
            
            # 1. Similarité de durée (±30 min)
            diff_duree = abs(circuit.get('duree_totale', 0) - circuit_ref.get('duree_totale', 0))
            if diff_duree < 30:
                score += 0.3
                details.append("durée similaire")
            elif diff_duree < 60:
                score += 0.15
                details.append("durée proche")
            
            # 2. Similarité de prix (±10€)
            diff_prix = abs(circuit.get('prix', 0) - circuit_ref.get('prix', 0))
            if diff_prix < 10:
                score += 0.3
                details.append("prix similaire")
            elif diff_prix < 20:
                score += 0.15
                details.append("prix proche")
            
            # 3. Similarité de nombre de monuments
            diff_nb = abs(circuit.get('nb_monuments', 0) - circuit_ref.get('nb_monuments', 0))
            if diff_nb < 2:
                score += 0.2
                details.append("même nombre de monuments")
            
            # 4. Types de monuments en commun
            types_ref = set(circuit_ref.get('types_monuments', []))
            types_circuit = set(circuit.get('types_monuments', []))
            if types_ref and types_circuit:
                communs = types_ref.intersection(types_circuit)
                if communs:
                    score += 0.2 * (len(communs) / max(len(types_ref), 1))
                    details.append(f"types en commun: {', '.join(communs)}")
            
            if score > 0.4:  # Seuil de similarité
                similaires.append({
                    'circuit_id': circuit.get('circuit_id'),
                    'score_similarite': round(score, 2),
                    'details': details,
                    'duree': circuit.get('duree_totale'),
                    'prix': circuit.get('prix'),
                    'nb_monuments': circuit.get('nb_monuments')
                })
        
        # Trier par score et limiter
        resultats = sorted(similaires, key=lambda x: x['score_similarite'], reverse=True)[:n]
        
        # Enregistrer dans l'historique
        self.historique_suggestions.append({
            'timestamp': datetime.now().isoformat(),
            'circuit_reference': circuit_id,
            'suggestions': [r['circuit_id'] for r in resultats],
            'nb_suggestions': len(resultats)
        })
        
        return resultats
    
    def circuit_du_jour(self):
       
        if not self.systeme.calculateur.circuits:
            return None
        
        # Critères de sélection
        circuits_eligibles = []
        
        for circuit in self.systeme.calculateur.circuits:
            score_selection = 0
            justifications = []
            
            # Popularité (poids fort)
            popularite = circuit.get('score_moyen', 3)
            score_selection += popularite * 2
            justifications.append(f"popularité: {popularite}/5")
            
            # Éviter les circuits déjà mis en avant récemment
            if circuit.get('circuit_id') in self.circuits_du_jour_historique[-7:]:
                score_selection -= 3  # Pénalité
                justifications.append("déjà mis en avant récemment")
            
            # Bonus pour les circuits avec des avis récents
            # (simulé ici avec un random pour l'exemple)
            if random.random() > 0.7:
                score_selection += 1
                justifications.append("avis récents positifs")
            
            # Bonus saisonnier (simulé)
            mois = datetime.now().month
            if 3 <= mois <= 5:  # Printemps
                if 'nature' in str(circuit.get('types_monuments', [])):
                    score_selection += 1
                    justifications.append("adapté au printemps")
            elif 6 <= mois <= 8:  # Été
                if circuit.get('duree_totale', 0) < 180:  # Circuits courts en été
                    score_selection += 1
                    justifications.append("circuit court pour l'été")
            
            circuits_eligibles.append({
                'circuit': circuit,
                'score': score_selection,
                'justifications': justifications
            })
        
        # Sélectionner le meilleur
        if circuits_eligibles:
            meilleur = max(circuits_eligibles, key=lambda x: x['score'])
            
            # Enregistrer dans l'historique
            self.circuits_du_jour_historique.append(meilleur['circuit'].get('circuit_id'))
            
            return {
                'circuit_id': meilleur['circuit'].get('circuit_id'),
                'nom': meilleur['circuit'].get('monuments_noms', ['Circuit'])[0][:30] + "...",
                'score_selection': round(meilleur['score'], 1),
                'justifications': meilleur['justifications'],
                'date': datetime.now().strftime('%Y-%m-%d'),
                'details': {
                    'duree': meilleur['circuit'].get('duree_totale'),
                    'prix': meilleur['circuit'].get('prix'),
                    'nb_monuments': meilleur['circuit'].get('nb_monuments'),
                    'popularite': meilleur['circuit'].get('score_moyen')
                }
            }
        
        # Fallback: circuit aléatoire
        circuit_aleatoire = random.choice(self.systeme.calculateur.circuits)
        return {
            'circuit_id': circuit_aleatoire.get('circuit_id'),
            'nom': "Circuit aléatoire",
            'score_selection': 1.0,
            'justifications': ["sélection par défaut"],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'details': {
                'duree': circuit_aleatoire.get('duree_totale'),
                'prix': circuit_aleatoire.get('prix'),
                'nb_monuments': circuit_aleatoire.get('nb_monuments')
            }
        }
    
    def rechercher_par_criteres(self, **criteres):
        
        resultats = []
        
        for circuit in self.systeme.calculateur.circuits:
            correspond = True
            explications = []
            
            # Filtre par durée max
            if 'duree_max' in criteres:
                if circuit.get('duree_totale', 0) > criteres['duree_max']:
                    correspond = False
                    explications.append(f"durée > {criteres['duree_max']}")
            
            # Filtre par prix max
            if 'prix_max' in criteres:
                if circuit.get('prix', 0) > criteres['prix_max']:
                    correspond = False
                    explications.append(f"prix > {criteres['prix_max']}")
            
            # Filtre par type
            if 'type' in criteres:
                types_circuit = circuit.get('types_monuments', [])
                if criteres['type'] not in types_circuit:
                    # Vérifier si le circuit est dans la catégorie correspondante
                    if circuit.get('circuit_id') not in self.categories.get(criteres['type'], []):
                        correspond = False
                        explications.append(f"type ≠ {criteres['type']}")
            
            # Filtre par nombre minimum de monuments
            if 'nb_min_monuments' in criteres:
                if circuit.get('nb_monuments', 0) < criteres['nb_min_monuments']:
                    correspond = False
                    explications.append(f"nb monuments < {criteres['nb_min_monuments']}")
            
            # Filtre par popularité minimum
            if 'popularite_min' in criteres:
                if circuit.get('score_moyen', 0) < criteres['popularite_min']:
                    correspond = False
                    explications.append(f"popularité < {criteres['popularite_min']}")
            
            if correspond:
                resultats.append({
                    'circuit_id': circuit.get('circuit_id'),
                    'duree': circuit.get('duree_totale'),
                    'prix': circuit.get('prix'),
                    'nb_monuments': circuit.get('nb_monuments'),
                    'score': circuit.get('score_moyen'),
                    'types': circuit.get('types_monuments', [])
                })
        
        return sorted(resultats, key=lambda x: x.get('score', 0), reverse=True)
    
    def get_statistiques_categories(self):
       
        stats = {}
        
        for categorie, circuits in self.categories.items():
            stats[categorie] = {
                'nb_circuits': len(circuits),
                'pourcentage': round(len(circuits) / len(self.systeme.calculateur.circuits) * 100, 1) if self.systeme.calculateur.circuits else 0,
                'exemples': circuits[:3]  # 3 exemples
            }
        
        return stats
    
    def get_circuits_par_type(self, type_monument):
        
        circuits_type = []
        
        for circuit in self.systeme.calculateur.circuits:
            types = circuit.get('types_monuments', [])
            if type_monument in types:
                circuits_type.append({
                    'circuit_id': circuit.get('circuit_id'),
                    'score': circuit.get('score_moyen'),
                    'duree': circuit.get('duree_totale')
                })
        
        return sorted(circuits_type, key=lambda x: x['score'], reverse=True)
    
    def get_statistiques(self):
        
        return {
            'nom': self.nom,
            'version': self.version,
            'total_circuits': len(self.systeme.calculateur.circuits),
            'categories': self.get_statistiques_categories(),
            'nb_suggestions_effectuees': len(self.historique_suggestions),
            'circuits_du_jour': len(self.circuits_du_jour_historique),
            'dernier_circuit_du_jour': self.circuits_du_jour_historique[-1] if self.circuits_du_jour_historique else None
        }


