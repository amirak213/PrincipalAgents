import pandas as pd
import json
import re
from datetime import datetime

def analyser_fichier_clients(fichier_clients):
    
    
    # Chargement du fichier (séparateur point-virgule)
    df = pd.read_csv(fichier_clients, sep=';', encoding='utf-8')
    print(f"📖 {len(df)} clients chargés")
    return df


class ClientProfile:

    
    def __init__(self, row):

        self.user_id = row['user_id']
        
        # Conversion des préférences (string → liste)
        self.preference_fonction = self._nettoyer_liste(row['preference_fonction'])
        self.preference_epoque = self._nettoyer_liste(row['preference_epoque'])
        
        # Attributs catégoriels simples (transport supprimé)
        self.mobilite = row['mobilite']
        self.zone = row['zone']
        self.type_tarif = row['type_tarif']
        
        # Attributs numériques
        self.budget_max = float(row['budget_max']) if pd.notna(row['budget_max']) else None
        self.duree_visite_min = float(row['duree_visite_min']) if pd.notna(row['duree_visite_min']) else None
        self.nb_pois = int(row['nb_pois']) if pd.notna(row['nb_pois']) else None
        
        # Liste des POIs (si disponible)
        self.liste_pois = self._nettoyer_liste_pois(row['liste_pois']) if 'liste_pois' in row else []
        
        # Pour la compatibilité avec l'étape 2 (sans transport)
        self.preferences_thematiques = self._creer_preferences_thematiques()
        self.types_preferes = self.preference_fonction
        self.duree_max = self.duree_visite_min
        self.mobilité = self.mobilite
        self.zone_preferee = self.zone
        
        # Note: transport forcé à 'voiture' pour tous
        self.transport = 'voiture'
        
        # Historique (vide au départ)
        self.historique_circuits = []
        self.historique_notes = {}
        self.feedbacks = []
        
        self.date_creation = datetime.now()
    
    def _nettoyer_liste(self, valeur):
       
        if pd.isna(valeur) or valeur == '':
            return []
        
        # Remplacer les virgules et espaces, filtrer les vides
        items = [item.strip() for item in str(valeur).split(',')]
        return [item for item in items if item and item != 'nan']
    
    def _nettoyer_liste_pois(self, valeur):
       
        if pd.isna(valeur) or valeur == '':
            return []
        
        # Nettoyage spécifique pour les POIs
        items = re.split(r'[|,]', str(valeur))
        return [item.strip() for item in items if item.strip() and '|' not in item]
    
    def _creer_preferences_thematiques(self):
       
        prefs = {}
        for epoque in self.preference_epoque:
            prefs[epoque.lower()] = 1.0
        return prefs
    
    def ajouter_interaction(self, circuit_id, note=None):
       
        self.historique_circuits.append(circuit_id)
        if note is not None:
            self.historique_notes[circuit_id] = note
    
    def __repr__(self):
        return (f"ClientProfile({self.user_id}):\n"
                f"  • Fonctions: {self.preference_fonction}\n"
                f"  • Époques: {self.preference_epoque}\n"
                f"  • Mobilité: {self.mobilite}\n"
                f"  • Transport: {self.transport} (fixé pour tous)\n"
                f"  • Budget: {self.budget_max} DT, Durée: {self.duree_visite_min} min\n"
                f"  • Zone: {self.zone}, Tarif: {self.type_tarif}\n"
                f"  • Nb POIs souhaité: {self.nb_pois}")


class GestionnaireClients:
    
    
    def __init__(self, fichier_clients):
       
        self.fichier = fichier_clients
        self.df = pd.read_csv(fichier_clients, sep=';', encoding='utf-8')
        self.profils = {}
        
        print(f"📂 Chargement de {len(self.df)} clients depuis {fichier_clients}")
        self._charger_tous_les_profils()
    
    def _charger_tous_les_profils(self):
        """Charge tous les profils à partir du DataFrame"""
        for _, row in self.df.iterrows():
            profil = ClientProfile(row)
            self.profils[profil.user_id] = profil
        
        print(f"✅ {len(self.profils)} profils chargés (transport forcé: voiture)")
    
    def get_profil(self, user_id):
        """Récupère un profil par son ID"""
        return self.profils.get(user_id)
    
    def get_profils_par_zone(self, zone):
        """Récupère les profils d'une zone donnée"""
        return [p for p in self.profils.values() if p.zone == zone]
    
    def get_profils_par_mobilite(self, mobilite):
        """Récupère les profils avec une mobilité donnée"""
        return [p for p in self.profils.values() if p.mobilite == mobilite]
    
    def sauvegarder_profils_json(self, fichier_sortie='clients_profils.json'):
        """Sauvegarde les profils au format JSON"""
        data = {}
        for user_id, profil in self.profils.items():
            data[user_id] = {
                'preference_fonction': profil.preference_fonction,
                'preference_epoque': profil.preference_epoque,
                'mobilite': profil.mobilite,
                'transport': profil.transport,  # 'voiture' pour tous
                'budget_max': profil.budget_max,
                'duree_visite_min': profil.duree_visite_min,
                'zone': profil.zone,
                'type_tarif': profil.type_tarif,
                'nb_pois': profil.nb_pois,
                'liste_pois': profil.liste_pois[:5] if profil.liste_pois else []
            }
        
        with open(fichier_sortie, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Profils sauvegardés dans {fichier_sortie}")
    
    def afficher_statistiques(self):
       
        
        # Distribution par mobilité
        print("\n🚶 Mobilité:")
        mobilites = {}
        for p in self.profils.values():
            mobilites[p.mobilite] = mobilites.get(p.mobilite, 0) + 1
        for mob, count in mobilites.items():
            print(f"   • {mob}: {count} clients ({count/len(self.profils)*100:.1f}%)")
        
        # Distribution par zone
        print("\n📍 Zone:")
        zones = {}
        for p in self.profils.values():
            zones[p.zone] = zones.get(p.zone, 0) + 1
        for z, count in zones.items():
            print(f"   • {z}: {count} clients")
        
        # Statistiques numériques
        budgets = [p.budget_max for p in self.profils.values() if p.budget_max]
        durees = [p.duree_visite_min for p in self.profils.values() if p.duree_visite_min]
        nb_pois = [p.nb_pois for p in self.profils.values() if p.nb_pois]
        
       
        
        # Top préférences fonctions
        
        from collections import Counter
        toutes_fonctions = []
        for p in self.profils.values():
            toutes_fonctions.extend(p.preference_fonction)
        
        for fonc, count in Counter(toutes_fonctions).most_common(10):
            print(f"   • {fonc}: {count} clients")
        
        # Top préférences époques
        print("\n📜 Top 10 époques préférées:")
        toutes_epoques = []
        for p in self.profils.values():
            toutes_epoques.extend(p.preference_epoque)
        
        for ep, count in Counter(toutes_epoques).most_common(10):
            print(f"   • {ep}: {count} clients")
    
    def exporter_pour_recommandation(self, fichier_sortie='profils_pour_recommandation.json'):
       
        data = {}
        for user_id, profil in self.profils.items():
            data[user_id] = {
                'preferences_thematiques': {ep.lower(): 1.0 for ep in profil.preference_epoque},
                'duree_max': profil.duree_visite_min,
                'types_preferes': profil.preference_fonction,
                'budget_max': profil.budget_max,
                'mobilité': profil.mobilite,
                'zone_preferee': profil.zone,
                'type_tarif': profil.type_tarif,
                'transport': 'voiture',  # Forcé à voiture
                'historique_circuits': [],
                'historique_notes': {}
            }
        
        with open(fichier_sortie, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        
        return data


# fonctions principales 

if __name__ == "__main__":
    
    # À MODIFIER: chemin vers votre fichier clients
    FICHIER_CLIENTS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\Profile_clients.csv"
    
    # 1. Analyse du fichier
    df_clients = analyser_fichier_clients(FICHIER_CLIENTS)
    
    # 2. Création du gestionnaire
    gestionnaire = GestionnaireClients(FICHIER_CLIENTS)
    
    # 3. Affichage des statistiques (sans transport)
    gestionnaire.afficher_statistiques()
    
    # 4. Sauvegarde au format JSON pour l'étape 3
    gestionnaire.exporter_pour_recommandation('Profile_clients.json')
    
   
    
    premier_user = df_clients.iloc[0]['user_id']
    profil_exemple = gestionnaire.get_profil(premier_user)
    if profil_exemple:
        print(f"\n{profil_exemple}")
 