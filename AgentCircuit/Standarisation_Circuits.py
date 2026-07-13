import pandas as pd
import ast
import json
from collections import Counter
import numpy as np

def extraire_tarif(valeur):
   
    if pd.isna(valeur) or valeur == '':
        return None
    
    try:
        if isinstance(valeur, str):
            valeur_propre = valeur.replace(',', '.').strip()
        else:
            valeur_propre = str(valeur).replace(',', '.').strip()
        
        return float(valeur_propre)
    except (ValueError, AttributeError):
        return None

def preparer_base_circuits(fichier_csv, fichier_monuments=None, sauvegarder=True):
  
    
  
    
    # 1. Chargement du fichier circuits
    print(f"📖 Chargement circuits: {fichier_csv}")
    df = pd.read_csv(fichier_csv)
    print(f"   → {len(df)} circuits chargés")
    
    # 2. Afficher les noms de colonnes
    print("\n📋 Colonnes dans votre fichier circuits:")
    for i, col in enumerate(df.columns):
        print(f"   {i+1}. '{col}'")
    
    # 3. Correction des noms de colonnes
    print("\n🔄 Adaptation aux noms de colonnes...")
    
    mapping_colonnes = {
        'id': 'circuit_id',
        'indices': 'indices',
        'noms': 'noms',
        'nb_momuments': 'nb_monuments',
        'duree': 'duree_totale',
        'score': 'score_moyen'
    }
    
    df.rename(columns=mapping_colonnes, inplace=True)
    print(f"   ✓ Colonnes renommées")
    
    # 4. Conversion des colonnes string → listes
    print("\n🔄 Conversion des colonnes...")
    
    df['indices'] = df['indices'].apply(ast.literal_eval)
    print(f"   ✓ 'indices' converti")
    
    df['noms'] = df['noms'].apply(ast.literal_eval)
    print(f"   ✓ 'noms' converti")
    
    # 5. CHARGEMENT DES TARIFS DEPUIS LE FICHIER MONUMENTS
    print("\n💰 Chargement des tarifs depuis le fichier monuments...")
    
    if fichier_monuments and pd.io.common.file_exists(fichier_monuments):
        # Charger le fichier monuments
        print(f"   📖 Lecture: {fichier_monuments}")
        df_monuments = pd.read_csv(fichier_monuments, sep=';', encoding='utf-8')
        print(f"   ✓ {len(df_monuments)} monuments chargés")
        
        # INSPECTION: Afficher les colonnes réelles
        print("\n   📋 Colonnes dans le fichier monuments:")
        for i, col in enumerate(df_monuments.columns):
            print(f"      {i+1}. '{col}'")
        
        # Détecter les colonnes de noms disponibles
        colonnes_noms = [col for col in df_monuments.columns if 'nom' in col.lower()]
        print(f"\n   🔍 Colonnes de noms détectées: {colonnes_noms}")
        
        # Choisir la première colonne de nom disponible
        colonne_nom = None
        for col in colonnes_noms:
            if col in df_monuments.columns:
                colonne_nom = col
                break
        
        if colonne_nom is None:
            print("   ❌ Aucune colonne de nom trouvée!")
            return df
        
        print(f"   ✅ Utilisation de la colonne: '{colonne_nom}'")
        
        # Détecter les colonnes de tarifs
        colonnes_tarifs = [col for col in df_monuments.columns if 'tarif' in col.lower()]
        print(f"\n   💰 Colonnes de tarifs détectées: {colonnes_tarifs}")
        
        # Mapping des catégories vers les colonnes réelles
        mapping_tarifs = {}
        for categorie in ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']:
            # Chercher une colonne qui correspond
            colonne_trouvee = None
            for col in colonnes_tarifs:
                if categorie.lower() in col.lower():
                    colonne_trouvee = col
                    break
            mapping_tarifs[categorie] = colonne_trouvee
        
        print(f"\n   🔄 Mapping tarifs détecté:")
        for cat, col in mapping_tarifs.items():
            if col:
                print(f"      • {cat} → '{col}'")
            else:
                print(f"      • {cat} → (non trouvé)")
        
        # Créer un dictionnaire des tarifs par nom de monument
        tarifs_par_monument = {}
        
        for _, row in df_monuments.iterrows():
            # Utiliser la colonne de nom détectée
            nom = row[colonne_nom] if pd.notna(row[colonne_nom]) else f"Monument_{_}"
            
            if pd.notna(nom) and nom != '':
                tarifs_par_monument[nom] = {}
                
                # Extraire les tarifs pour chaque catégorie
                for categorie, colonne in mapping_tarifs.items():
                    if colonne and colonne in row:
                        tarifs_par_monument[nom][categorie] = extraire_tarif(row[colonne])
                    else:
                        tarifs_par_monument[nom][categorie] = None
        
        
        
        # Afficher un exemple
        if len(tarifs_par_monument) > 0:
            exemple_nom = list(tarifs_par_monument.keys())[0]
            print(f"\n   📌 Exemple - {exemple_nom}:")
            for cat, val in tarifs_par_monument[exemple_nom].items():
                print(f"      • {cat}: {val}")
        
        # 6. AJOUT DES COLONNES DE TARIFS POUR CHAQUE CIRCUIT
        print("\n🔄 Calcul des tarifs par circuit...")
        
        # Initialiser les colonnes de tarifs
        for categorie in ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']:
            df[f'cout_total_{categorie}'] = 0.0
        
        # Calculer le coût total pour chaque circuit
        circuits_sans_tarifs = 0
        monuments_non_trouves = set()
        
        for idx, row in df.iterrows():
            noms_circuit = row['noms']
            
            couts = {cat: 0 for cat in ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']}
            monuments_trouves = 0
            
            for nom_monument in noms_circuit:
                # Chercher le monument dans le dictionnaire des tarifs
                monument_trouve = None
                for nom_tarif in tarifs_par_monument:
                    if nom_monument.lower() in nom_tarif.lower() or nom_tarif.lower() in nom_monument.lower():
                        monument_trouve = nom_tarif
                        break
                
                if monument_trouve:
                    tarifs = tarifs_par_monument[monument_trouve]
                    for categorie in couts.keys():
                        if categorie in tarifs and tarifs[categorie] is not None:
                            couts[categorie] += tarifs[categorie]
                    monuments_trouves += 1
                else:
                    monuments_non_trouves.add(nom_monument)
            
            # Enregistrer les coûts
            for categorie, cout in couts.items():
                df.at[idx, f'cout_total_{categorie}'] = round(cout, 2)
            
            if monuments_trouves < len(noms_circuit):
                circuits_sans_tarifs += 1
        
        
        if circuits_sans_tarifs > 0:
            print(f"   ⚠️  {circuits_sans_tarifs} circuits avec des monuments sans tarifs")
        
        if monuments_non_trouves:
            print(f"\n   ⚠️  {len(monuments_non_trouves)} monuments non trouvés (exemples):")
            for m in list(monuments_non_trouves)[:5]:
                print(f"      - {m}")
        
        # Statistiques des tarifs
        print("\n📊 Statistiques des tarifs par circuit:")
        for categorie in ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']:
            colonne = f'cout_total_{categorie}'
            valeurs_non_nulles = df[df[colonne] > 0][colonne]
            if len(valeurs_non_nulles) > 0:
                print(f"   • {categorie}: min={valeurs_non_nulles.min():.1f}, "
                      f"max={valeurs_non_nulles.max():.1f}, "
                      f"moyenne={valeurs_non_nulles.mean():.1f} DT")
            else:
                print(f"   • {categorie}: pas de données")
    
    else:
        print("   ⚠️ Fichier monuments non trouvé - création de tarifs simulés")
        for categorie in ['resident', 'etudiant', 'etranger', 'enseignant', 'retraite', 'enfant']:
            df[f'cout_total_{categorie}'] = np.random.uniform(10, 50, len(df)).round(1)
    
    # 7. Analyse des monuments
    print("\n🏛️ Analyse des monuments dans les circuits:")
    tous_les_noms = []
    for noms in df['noms']:
        tous_les_noms.extend(noms)
    
    monuments_uniques = set(tous_les_noms)
    print(f"   • {len(monuments_uniques)} monuments uniques dans les circuits")
    
    freq_monuments = Counter(tous_les_noms)
    top_monuments = freq_monuments.most_common(5)
    print(f"\n   • Top 5 monuments les plus populaires:")
    for nom, freq in top_monuments:
        print(f"     - {nom}: présent dans {freq} circuits")
    
    # 8. Sauvegarde
    if sauvegarder:
        fichier_propre = fichier_csv.replace('.csv', '_propre.csv')
        df.to_csv(fichier_propre, index=False)
        print(f"\n💾 Version propre sauvegardée: {fichier_propre}")
        
        fichier_json = fichier_csv.replace('.csv', '_pour_agent.json')
        
        data_agent = []
        for _, row in df.iterrows():
            circuit_data = {
                'circuit_id': row['circuit_id'],
                'indices': row['indices'],
                'noms': row['noms'],
                'nb_monuments': row['nb_monuments'],
                'duree_totale': row['duree_totale'],
                'score_moyen': row['score_moyen'],
                'cout_par_categorie': {
                    'resident': row['cout_total_resident'],
                    'etudiant': row['cout_total_etudiant'],
                    'etranger': row['cout_total_etranger'],
                    'enseignant': row['cout_total_enseignant'],
                    'retraite': row['cout_total_retraite'],
                    'enfant': row['cout_total_enfant']
                }
            }
            data_agent.append(circuit_data)
        
        with open(fichier_json, 'w', encoding='utf-8') as f:
            json.dump(data_agent, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Données pour agent sauvegardées: {fichier_json}")
    
    return df


# ==================== EXÉCUTION ====================

if __name__ == "__main__":
    
    FICHIER_CIRCUITS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\circuits_optimises.csv"
    FICHIER_MONUMENTS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\monuments.csv"
    
    df_propre = preparer_base_circuits(FICHIER_CIRCUITS, FICHIER_MONUMENTS, sauvegarder=True)