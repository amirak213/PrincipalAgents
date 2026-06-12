import pandas as pd
import json
import numpy as np
from collections import Counter
from datetime import datetime
import os
import traceback  

from PertinenceCalculator import PertinenceCalculator
from Standarisation_Clients import ClientProfile


class SystemeRecommandation:
   
    def __init__(self, fichier_clients_json, fichier_circuits_json):
       
        # 1. Charger les clients depuis le JSON
    
        self.clients = self._charger_clients_json(fichier_clients_json)
        
        
        # 2. Initialiser le calculateur de pertinence (étape 3)
        
        self.calculateur = PertinenceCalculator(fichier_circuits_json=fichier_circuits_json)
        
        # 3. Statistiques
        self.nb_clients = len(self.clients)
        self.nb_circuits = len(self.calculateur.circuits) if hasattr(self.calculateur, 'circuits') else 0
        
        # 4. Historique des recommandations
        self.historique_recommandations = []
        
        
    
    def _charger_clients_json(self, fichier_json):
       
        clients = {}
        
        try:
            with open(fichier_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"\n   📋 Structure du JSON: {type(data)}")
            
            if isinstance(data, dict):
                print(f"   • Nombre de clients: {len(data)}")
                
                # Afficher un exemple pour debug
                if len(data) > 0:
                    premier_user = list(data.keys())[0]
                    print(f"   • Premier client: {premier_user}")
                    print(f"   • Champs: {list(data[premier_user].keys())}")
                    
                    # Vérifier la présence de budget_max
                    if 'budget_max' in data[premier_user]:
                        print(f"   • ✓ budget_max présent: {data[premier_user]['budget_max']}")
                
                # Créer les profils clients
                for user_id, profil_data in data.items():
                    try:
                        client = self._creer_client_from_dict(user_id, profil_data)
                        clients[user_id] = client
                    except Exception as e:
                        print(f"   ⚠️ Erreur pour {user_id}: {e}")
            else:
                print(f"   ❌ Format JSON non supporté: {type(data)}")
            
        except FileNotFoundError:
            print(f"   ❌ Fichier non trouvé: {fichier_json}")
        except json.JSONDecodeError as e:
            print(f"   ❌ Erreur de décodage JSON: {e}")
        except Exception as e:
            print(f"   ❌ Erreur chargement: {e}")
            traceback.print_exc()
        
        return clients
    
    def _creer_client_from_dict(self, user_id, data):
        
        # Extraire les données
        types_preferes = data.get('types_preferes', [])
        epoques = list(data.get('preferences_thematiques', {}).keys())
        budget_max = data.get('budget_max', None)
        duree_max = data.get('duree_max', 180)
        
        # Créer un dictionnaire pour ClientProfile
        row_data = {
            'user_id': user_id,
            'preference_fonction': ', '.join(types_preferes),
            'preference_epoque': ', '.join(epoques),
            'mobilite': data.get('mobilité', 'normale'),
            'zone': data.get('zone_preferee', 'Mixte'),
            'type_tarif': data.get('type_tarif', 'resident'),
            'duree_visite_min': duree_max,
            'budget_max': budget_max,
            'nb_pois': len(types_preferes) if types_preferes else 5
        }
        
        # Convertir en objet ClientProfile
        try:
            # Essayer avec Series d'abord
            client = ClientProfile(pd.Series(row_data))
        except:
            # Sinon créer directement
            client = ClientProfile(row_data)
        
        # Ajouter TOUS les attributs nécessaires pour la compatibilité
        client.types_preferes = types_preferes
        client.preference_epoque = epoques
        client.budget_max = budget_max
        client.duree_max = duree_max
        client.zone = data.get('zone_preferee', 'Mixte')
        client.mobilite = data.get('mobilité', 'normale')
        client.type_tarif = data.get('type_tarif', 'resident')
        client.transport = data.get('transport', 'voiture')
        
        # Ajouter l'historique si présent
        if 'historique_circuits' in data:
            client.historique_circuits = data['historique_circuits']
        else:
            client.historique_circuits = []
            
        if 'historique_notes' in data:
            client.historique_notes = data['historique_notes']
        else:
            client.historique_notes = {}
        
        return client
    
    def get_client(self, user_id):
        ""
        return self.clients.get(user_id)
    
    def get_circuit_par_id(self, circuit_id):
        """Récupère un circuit par son ID"""
        if not hasattr(self.calculateur, 'circuits'):
            return None
        for circuit in self.calculateur.circuits:
            if circuit['circuit_id'] == circuit_id:
                return circuit
        return None
    
    def recommander_pour_client(self, user_id, n_recommandations=3):
        """Génère des recommandations pour un client"""
        client = self.get_client(user_id)
        if not client:
            return {'error': f'Client {user_id} non trouvé'}
        
        # Générer les recommandations
        exclure_ids = getattr(client, 'historique_circuits', [])
        
        try:
            # CORRECTION: Appel avec les bons noms de paramètres
            recommandations = self.calculateur.recommander(
                profil=client,                          # ← 'profil' au lieu de 'client'
                n_recommandations=n_recommandations,    # ← CORRIGÉ: paramètre bien nommé
                exclure_ids=exclure_ids
            )
        except Exception as e:
            print(f"   ⚠️ Erreur recommandation pour {user_id}: {e}")
            recommandations = []
        
        # Enregistrer dans l'historique
        self.historique_recommandations.append({
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'recommandations': [r.get('circuit_id', 'N/A') for r in recommandations]
        })
        
        return {
            'user_id': user_id,
            'profil': {
                'epoques': list(getattr(client, 'preference_epoque', []))[:3],
                'types': list(getattr(client, 'types_preferes', []))[:3],
                'duree_max': getattr(client, 'duree_max', 'N/A'),
                'zone': getattr(client, 'zone', 'N/A'),
                'budget_max': getattr(client, 'budget_max', None)
            },
            'recommandations': recommandations,
            'nb_recommandations': len(recommandations)
        }
    
    def recommander_plusieurs_clients(self, liste_user_ids, n_recommandations=3):
        """Recommande pour plusieurs clients"""
        resultats = {}
        for user_id in liste_user_ids:
            resultats[user_id] = self.recommander_pour_client(user_id, n_recommandations)
        return resultats
    
    def analyser_couverture(self):
        
        print("\n" + "="*70)
        print("📊 ANALYSE DE COUVERTURE")
        print("="*70)
        
        if not self.clients:
            print("⚠️ Aucun client chargé")
            return
        
        # Distribution des zones
        zones = {}
        budgets = []
        durees = []
        
        for client in self.clients.values():
            # Zone
            zone = getattr(client, 'zone', 'Inconnue')
            zones[zone] = zones.get(zone, 0) + 1
            
            # Budget
            budget = getattr(client, 'budget_max', None)
            if budget and budget > 0:
                budgets.append(budget)
            
            # Durée
            duree = getattr(client, 'duree_max', None)
            if duree and duree > 0:
                durees.append(duree)
        
       
        if budgets:
            print(f"\n💰 Budgets:")
            print(f"   • Min: {min(budgets):.0f} DT")
            print(f"   • Max: {max(budgets):.0f} DT")
            print(f"   • Moyen: {sum(budgets)/len(budgets):.0f} DT")
            print(f"   • Clients avec budget: {len(budgets)}/{self.nb_clients}")
        
        if durees:
            print(f"\n⏱️  Durées souhaitées:")
            print(f"   • Min: {min(durees):.0f} min")
            print(f"   • Max: {max(durees):.0f} min")
            print(f"   • Moyenne: {sum(durees)/len(durees):.0f} min")
        
        # Top préférences (époques)
        all_epoques = []
        for c in self.clients.values():
            epoques = getattr(c, 'preference_epoque', [])
            all_epoques.extend(epoques)
        
        if all_epoques:
            print("\n🏛️  Top 5 époques préférées:")
            for epoque, count in Counter(all_epoques).most_common(5):
                print(f"   • {epoque}: {count} clients")
        
       
    
    def simuler_feedback(self, user_id, circuit_id, note):
        """Simule un feedback client"""
        client = self.get_client(user_id)
        if client:
            if not hasattr(client, 'historique_circuits'):
                client.historique_circuits = []
            client.historique_circuits.append(circuit_id)
            
            if not hasattr(client, 'historique_notes'):
                client.historique_notes = {}
            client.historique_notes[circuit_id] = note
            
            
            return True
        return False
    
    def exporter_recommandations(self, fichier_sortie='recommandations.json', n_clients_max=1000):
        """Exporte les recommandations dans un fichier JSON"""
    
        
        if not self.clients:
            print("   ⚠️ Aucun client - export annulé")
            return {}
        
        resultats = {}
        clients_liste = list(self.clients.keys())[:n_clients_max]
        
        for user_id in clients_liste:
            recos = self.recommander_pour_client(user_id, n_recommandations=5)
            if 'error' not in recos and recos['recommandations']:
                resultats[user_id] = {
                    'recommandations': [
                        {
                            'circuit_id': r.get('circuit_id', 'N/A'),
                            'score': r.get('score_global', 0),
                            'duree': r.get('duree', 0),
                            'nb_monuments': r.get('nb_monuments', 'N/A')
                        }
                        for r in recos['recommandations']
                    ]
                }
        
        with open(fichier_sortie, 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        
        
        return resultats
    
    def afficher_recommandations(self, user_id, n=3):
        """Affiche les recommandations pour un client"""
        resultats = self.recommander_pour_client(user_id, n)
        
        if 'error' in resultats:
            print(f"❌ {resultats['error']}")
            return
       
        if resultats['profil']['budget_max']:
            print(f"   Budget max: {resultats['profil']['budget_max']} DT")

       


# ==================== FONCTION PRINCIPALE ====================

def main():
    
   
    
    # 1. Vérifier que les fichiers existent
    FICHIER_CLIENTS_JSON = r"C:\Users\anasd\OneDrive\Bureau\stage II2\Profile_clients.json"
    FICHIER_CIRCUITS_JSON = r"C:\Users\anasd\OneDrive\Bureau\stage II2\Profile_circuit.json"
    
    
    fichiers_ok = True
    
    for fichier in [FICHIER_CLIENTS_JSON, FICHIER_CIRCUITS_JSON]:
        if os.path.exists(fichier):
            taille = os.path.getsize(fichier)
            print(f"   ✓ {os.path.basename(fichier)} existe ({taille} octets)")
        else:
            print(f"   ❌ {fichier} n'existe pas")
            fichiers_ok = False
    
    if not fichiers_ok:
        print("\n❌ Fichiers manquants - arrêt du programme")
        return
    
    # 2. Initialiser le système
    systeme = SystemeRecommandation(FICHIER_CLIENTS_JSON, FICHIER_CIRCUITS_JSON)
    
    # 3. Analyse de couverture (seulement si des clients sont chargés)
    if systeme.clients:
        systeme.analyser_couverture()
        
        # 4. Afficher les recommandations pour les 5 premiers clients
        clients_test = list(systeme.clients.keys())[:5]
        
        for user_id in clients_test:
            systeme.afficher_recommandations(user_id, n=3)
        
        # 5. Test de feedback
        if clients_test:
            client_test = clients_test[0]
            resultats = systeme.recommander_pour_client(client_test, n_recommandations=1)
            if resultats.get('recommandations'):
                circuit_test = resultats['recommandations'][0].get('circuit_id', 'CIRCUIT_001')
                print(f"\nClient {client_test} a reçu {circuit_test} en recommandation")
                systeme.simuler_feedback(client_test, circuit_test, 5)
                
                print(f"\nNouvelles recommandations (sans le circuit déjà vu):")
                nouvelles = systeme.recommander_pour_client(client_test, n_recommandations=3)
                for i, rec in enumerate(nouvelles.get('recommandations', []), 1):
                    print(f"   {i}. {rec.get('circuit_id', 'N/A')} - Score: {rec.get('score_global', 0):.3f}")
        
        # 6. Export des recommandations
        systeme.exporter_recommandations('recommandations_1000_clients.json', n_clients_max=1000)
    
    else:
        print("\n❌ Aucun client chargé - impossible de continuer")
   


if __name__ == "__main__":
    main()