import pandas as pd
import numpy as np
import heapq
from geopy.distance import geodesic
import random
from deap import base, creator, tools, algorithms
import os
import warnings
warnings.filterwarnings('ignore')


# Catégories de tarifs disponibles
CATEGORIES_TARIF = ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']

# Mapping entre nom de colonne CSV et nom de catégorie
COLONNES_TARIF = {
    'resident':    'Tarif_resident',
    'etudiant':    'Tarif_etudiant',
    'etranger':    'Tarif_etranger',
    'enseignant':  'Tarif_enseignant',
    'retraite':    'Tarif_retraite',
    'enfant':      'Tarif_enfant',
}


class CircuitOptimizer:

    def __init__(self, monuments_file, vitesse_voiture=50):

        if not os.path.exists(monuments_file):
            raise FileNotFoundError(f"Le fichier {monuments_file} n'existe pas")

        self.monuments_file = monuments_file
        self.df = pd.read_csv(monuments_file, encoding='utf-8', sep=';')
        self.monuments = self.df.to_dict('records')
        self.vitesse = vitesse_voiture

        # Vérification des colonnes tarifs
        self.colonnes_tarif_disponibles = {
            cat: col for cat, col in COLONNES_TARIF.items()
            if col in self.df.columns
        }
        if self.colonnes_tarif_disponibles:
            print(f"✅ Colonnes tarifs détectées : {list(self.colonnes_tarif_disponibles.values())}")
        else:
            print("⚠️  Aucune colonne tarif trouvée. Les tarifs ne seront pas calculés.")

        self.graphe = self._construire_graphe()
        self._configurer_algo_genetique()

        print(f"✅ {len(self.monuments)} monuments chargés depuis {monuments_file}")

    # ------------------------------------------------------------------
    # Utilitaires de base
    # ------------------------------------------------------------------

    def _temps_trajet(self, coord1, coord2):
        """Calcule le temps de trajet en minutes."""
        distance_km = geodesic(coord1, coord2).kilometers
        return (distance_km / self.vitesse) * 60

    def _construire_graphe(self):
        """Construit le graphe des temps de trajet entre monuments."""
        graphe = {}
        for i, m1 in enumerate(self.monuments):
            coord_i = (m1['latitude'], m1['longitude'])
            graphe[m1['nom']] = {}
            for j, m2 in enumerate(self.monuments):
                if i != j:
                    coord_j = (m2['latitude'], m2['longitude'])
                    graphe[m1['nom']][m2['nom']] = self._temps_trajet(coord_i, coord_j)
        return graphe

    def _configurer_algo_genetique(self):
        """Configure l'algorithme génétique DEAP."""
        if not hasattr(creator, "FitnessMin"):
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
            creator.create("Individual", list, fitness=creator.FitnessMin)

        self.toolbox = base.Toolbox()
        self.toolbox.register("indices", random.sample, range(len(self.monuments)), len(self.monuments))
        self.toolbox.register("individual", tools.initIterate, creator.Individual, self.toolbox.indices)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("mate", tools.cxOrdered)
        self.toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    # ------------------------------------------------------------------
    # Calcul durée
    # ------------------------------------------------------------------

    def duree_circuit(self, indices_monuments):
        """Calcule la durée totale d'un circuit (visites + trajets) en minutes."""
        duree = 0
        for idx in indices_monuments:
            duree += self.monuments[idx].get('duree_visite_min', 60)

        for i in range(len(indices_monuments) - 1):
            m1 = self.monuments[indices_monuments[i]]['nom']
            m2 = self.monuments[indices_monuments[i + 1]]['nom']
            duree += self.graphe[m1][m2]

        return duree

    def evaluer_circuit(self, individu):
        return (self.duree_circuit(individu),)

    # ------------------------------------------------------------------
    # Calcul tarifs  ← NOUVEAU
    # ------------------------------------------------------------------

    def _tarif_monument(self, idx, categorie):
       
        col = self.colonnes_tarif_disponibles.get(categorie)
        if col is None:
            return 0.0
        valeur = self.monuments[idx].get(col, '')
        if valeur == '' or valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
            return 0.0
        try:
            return float(str(valeur).replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0

    def tarifs_circuit(self, indices_monuments):
        
        totaux = {cat: 0.0 for cat in self.colonnes_tarif_disponibles}
        for idx in indices_monuments:
            for cat in self.colonnes_tarif_disponibles:
                totaux[cat] += self._tarif_monument(idx, cat)
        return {cat: round(val, 2) for cat, val in totaux.items()}

    # ------------------------------------------------------------------
    # Optimisation
    # ------------------------------------------------------------------

    def optimiser(self, indices_selectionnes, pop_size=100, generations=50,
                  prob_croisement=0.7, prob_mutation=0.2, verbose=True):
        """Optimise l'ordre de visite avec un algorithme génétique."""
        n = len(indices_selectionnes)

        if n < 2:
            return indices_selectionnes, self.monuments[indices_selectionnes[0]].get('duree_visite_min', 60)

        def evaluer_adaptee(individu):
            indices_globaux = [indices_selectionnes[i] for i in individu]
            return (self.duree_circuit(indices_globaux),)

        toolbox_local = base.Toolbox()
        toolbox_local.register("indices", random.sample, range(n), n)
        toolbox_local.register("individual", tools.initIterate, creator.Individual, toolbox_local.indices)
        toolbox_local.register("population", tools.initRepeat, list, toolbox_local.individual)
        toolbox_local.register("evaluate", evaluer_adaptee)
        toolbox_local.register("mate", tools.cxOrdered)
        toolbox_local.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
        toolbox_local.register("select", tools.selTournament, tournsize=3)

        pop = toolbox_local.population(n=pop_size)
        pop, log = algorithms.eaSimple(
            pop, toolbox_local, prob_croisement, prob_mutation, generations,
            verbose=verbose
        )

        meilleur = tools.selBest(pop, 1)[0]
        meilleur_circuit = [indices_selectionnes[i] for i in meilleur]

        return meilleur_circuit, meilleur.fitness.values[0]

    # ------------------------------------------------------------------
    # Génération de circuits
    # ------------------------------------------------------------------

    def generer_circuits(self, nb_circuits=100, min_monuments=3, max_monuments=7,
                         chemin_sortie='circuits_optimises.csv'):
       
        data = []

        for i in range(nb_circuits):
            nb = random.randint(min_monuments, min(max_monuments, len(self.monuments)))
            indices = random.sample(range(len(self.monuments)), nb)

            circuit, duree = self.optimiser(indices, pop_size=50, generations=30, verbose=False)

            score = sum(self.monuments[idx].get('popularite', 1) for idx in circuit) / nb

            # ── Calcul des tarifs par catégorie ──────────────────────────
            tarifs = self.tarifs_circuit(circuit)
            # ─────────────────────────────────────────────────────────────

            ligne = {
                'id':           f'CIRCUIT_{i:04d}',
                'indices':      circuit,
                'noms':         [self.monuments[idx]['nom'] for idx in circuit],
                'nb_monuments': nb,
                'duree':        round(duree, 1),
                'score':        round(score, 2),
            }
            # Ajouter une colonne par catégorie tarif
            for cat, total in tarifs.items():
                ligne[f'tarif_{cat}'] = total

            data.append(ligne)

        df = pd.DataFrame(data)

        dossier_sortie = os.path.dirname(chemin_sortie)
        if dossier_sortie and not os.path.exists(dossier_sortie):
            os.makedirs(dossier_sortie, exist_ok=True)
            print(f"✅ Dossier créé : {dossier_sortie}")

        df.to_csv(chemin_sortie, index=False)
        print(f"\n✅ {len(df)} circuits sauvegardés dans '{chemin_sortie}'")

        return df

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def afficher_circuit(self, indices):
        
        print("\n" + "="*60)
        print("DÉTAILS DU CIRCUIT")
        print("="*60)

        visite_total = 0
        trajet_total = 0

        for i, idx in enumerate(indices):
            m = self.monuments[idx]
            duree_visite = m.get('duree_visite_min', 60)
            visite_total += duree_visite

            print(f"\n{i+1}. {m['nom']}")
            print(f"   └─ Visite : {duree_visite} min")

            # Tarifs du monument courant
            if self.colonnes_tarif_disponibles:
                tarifs_ligne = []
                for cat in self.colonnes_tarif_disponibles:
                    val = self._tarif_monument(idx, cat)
                    tarifs_ligne.append(f"{cat}: {val} DT")
                print(f"   └─ Tarifs : {' | '.join(tarifs_ligne)}")

            if i < len(indices) - 1:
                trajet = self.graphe[m['nom']][self.monuments[indices[i + 1]]['nom']]
                trajet_total += trajet
                print(f"   └─ Trajet vers suivant : {trajet:.1f} min")

        duree_totale = visite_total + trajet_total
        print("\n" + "-"*60)
        print(f"⏱  Durée totale  : {duree_totale:.1f} min  "
              f"(visites {visite_total} min + trajets {trajet_total:.1f} min)")

        # ── Récapitulatif des tarifs par catégorie ──────────────────────
        if self.colonnes_tarif_disponibles:
            print("\n💰 TARIF TOTAL DU CIRCUIT PAR CATÉGORIE :")
            tarifs_totaux = self.tarifs_circuit(indices)
            for cat, total in tarifs_totaux.items():
                print(f"   • {cat.capitalize():12s} : {total:.2f} DT")
        # ────────────────────────────────────────────────────────────────

        print("="*60)


# ======================================================================
# Fichier exemple
# ======================================================================

def creer_fichier_exemple(chemin_fichier='monuments.csv'):
    data = {
        'nom':              ['Amphithéâtre', 'Thermes', 'Musée', 'Cathédrale', 'Tophet'],
        'latitude':         [36.8547, 36.8592, 36.8547, 36.8569, 36.8347],
        'longitude':        [10.3247, 10.3347, 10.3247, 10.3244, 10.3347],
        'duree_visite_min': [45, 60, 90, 30, 45],
        'popularite':       [5, 5, 4, 3, 4],
        'Tarif_resident':   [9, 9, 9, 0, 9],
        'Tarif_etudiant':   [2, 2, 2, 0, 2],
        'Tarif_etranger':   [12, 12, 12, 0, 12],
        'Tarif_enseignant': [4.5, 4.5, 4.5, 0, 4.5],
        'Tarif_retraite':   [4.5, 4.5, 4.5, 0, 4.5],
        'Tarif_enfant':     [2, 2, 2, 0, 2],
    }
    pd.DataFrame(data).to_csv(chemin_fichier, index=False, sep=';')
    print(f"✅ Fichier exemple créé : {chemin_fichier}")
    return chemin_fichier


# ======================================================================
# Point d'entrée principal
# ======================================================================

if __name__ == "__main__":

    # Chemin vers votre fichier de monuments (avec colonnes tarifs)
    FICHIER_MONUMENTS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\monuments.csv"

    # Chemin pour sauvegarder les circuits optimisés
    FICHIER_CIRCUITS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\circuits_optimises.csv"

   

    if not os.path.exists(FICHIER_MONUMENTS):
        print(f"⚠️  Attention : Le fichier {FICHIER_MONUMENTS} n'existe pas!")
        reponse = input("Voulez-vous créer un fichier exemple à cet emplacement ? (o/n): ")
        if reponse.lower() == 'o':
            dossier_monuments = os.path.dirname(FICHIER_MONUMENTS)
            if dossier_monuments and not os.path.exists(dossier_monuments):
                os.makedirs(dossier_monuments, exist_ok=True)
            creer_fichier_exemple(FICHIER_MONUMENTS)
        else:
            print("❌ Arrêt du programme - fichier monuments requis")
            exit()

    try:
        optim = CircuitOptimizer(FICHIER_MONUMENTS, vitesse_voiture=50)

        # Test rapide sur un sous-ensemble de monuments
        nb_test = min(4, len(optim.monuments))
        test = random.sample(range(len(optim.monuments)), nb_test)
        circuit, duree = optim.optimiser(test, verbose=False)
        optim.afficher_circuit(circuit)

        # Génération de 100 circuits avec tarifs
        df_circuits = optim.generer_circuits(
            nb_circuits=100,
            min_monuments=3,
            max_monuments=7,
            chemin_sortie=FICHIER_CIRCUITS
        )

        # Aperçu des colonnes tarifs dans le résultat
        cols_tarif = [c for c in df_circuits.columns if c.startswith('tarif_')]
        if cols_tarif:
            print("\n📊 Aperçu des tarifs générés (5 premiers circuits) :")
            print(df_circuits[['id', 'nb_monuments', 'duree'] + cols_tarif].head().to_string(index=False))

    except FileNotFoundError as e:
        print(f"❌ Erreur fichier non trouvé : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
