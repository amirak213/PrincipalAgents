

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import random

# Import du système principal et des agents
from Matching_client_circuit import SystemeRecommandation
from Agent_principal import AgentRecommandationPrincipal

# ==================== CONFIGURATION DE LA PAGE ====================

st.set_page_config(
    page_title="🎯 Système de Recommandation Agentique",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== STYLES CSS PERSONNALISÉS ====================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .agent-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 5px solid #FF4B4B;
    }
    .recommandation-card {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #ddd;
    }
    .score-high {
        color: #28a745;
        font-weight: bold;
    }
    .score-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .score-low {
        color: #dc3545;
        font-weight: bold;
    }
    .feedback-positif {
        background-color: #d4edda;
        padding: 0.5rem;
        border-radius: 5px;
        color: #155724;
    }
    .feedback-negatif {
        background-color: #f8d7da;
        padding: 0.5rem;
        border-radius: 5px;
        color: #721c24;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== INITIALISATION DU SYSTÈME ====================

@st.cache_resource
def init_systeme():
    """Initialise le système de recommandation et les agents (mise en cache)"""
    
    # Chemins des fichiers (à adapter selon votre installation)
    FICHIER_CLIENTS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\Profile_client.json"
    FICHIER_CIRCUITS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\Profile_circuit.json"
    FICHIER_MONUMENTS = r"C:\Users\anasd\OneDrive\Bureau\stage II2\monuments.csv"
    
    # Vérification de l'existence des fichiers
    fichiers_manquants = []
    if not os.path.exists(FICHIER_CLIENTS):
        fichiers_manquants.append(FICHIER_CLIENTS)
    if not os.path.exists(FICHIER_CIRCUITS):
        fichiers_manquants.append(FICHIER_CIRCUITS)
    
    if fichiers_manquants:
        st.error(f"❌ Fichiers manquants : {fichiers_manquants}")
        st.info("Création de fichiers de démonstration...")
        return create_demo_files(FICHIER_CLIENTS, FICHIER_CIRCUITS)
    
    try:
        # Initialisation du système
        systeme = SystemeRecommandation(FICHIER_CLIENTS, FICHIER_CIRCUITS)
        agent_principal = AgentRecommandationPrincipal(systeme)
        
        return systeme, agent_principal
    except Exception as e:
        st.error(f"❌ Erreur d'initialisation : {e}")
        return None, None

def create_demo_files(clients_path, circuits_path):
    """Crée des fichiers de démonstration"""
    
    # Création de clients de démonstration
    clients_demo = {
        "user_1": {
            "id": "user_1",
            "nom": "Alice Martin",
            "preference_epoque": ["romaine", "punique"],
            "types_preferes": ["culturel", "historique"],
            "budget_max": 50,
            "duree_max": 240,
            "contraintes": []
        },
        "user_2": {
            "id": "user_2",
            "nom": "Bernard Dubois",
            "preference_epoque": ["médiévale", "andalouse"],
            "types_preferes": ["religieux", "culturel"],
            "budget_max": 75,
            "duree_max": 180,
            "contraintes": []
        },
        "user_3": {
            "id": "user_3",
            "nom": "Claire Petit",
            "preference_epoque": ["moderne", "contemporaine"],
            "types_preferes": ["nature", "aventure"],
            "budget_max": 30,
            "duree_max": 300,
            "contraintes": ["restauration"]
        }
    }
    
    # Sauvegarde des clients
    with open(clients_path, 'w', encoding='utf-8') as f:
        json.dump(clients_demo, f, indent=2, ensure_ascii=False)
    
    # Création de circuits de démonstration
    circuits_demo = []
    for i in range(1, 11):
        circuit = {
            "circuit_id": f"CIRCUIT_{i:04d}",
            "monuments_indices": list(range(3, 7)),
            "monuments_noms": [f"Monument {j}" for j in range(1, 5)],
            "nbre_monuments": random.randint(3, 6),
            "duree_totale": random.randint(90, 300),
            "score_moyen": round(random.uniform(3.0, 5.0), 2),
            "types_monuments": random.sample(["culturel", "religieux", "nature", "historique"], 2),
            "prix": random.randint(20, 80)
        }
        circuits_demo.append(circuit)
    
    # Sauvegarde des circuits
    with open(circuits_path, 'w', encoding='utf-8') as f:
        json.dump(circuits_demo, f, indent=2, ensure_ascii=False)
    
    st.success("✅ Fichiers de démonstration créés avec succès !")
    
    # Réinitialiser le système avec les nouveaux fichiers
    systeme = SystemeRecommandation(clients_path, circuits_path)
    agent_principal = AgentRecommandationPrincipal(systeme)
    
    return systeme, agent_principal

# ==================== FONCTIONS D'AFFICHAGE ====================

def afficher_entete():
    """Affiche l'en-tête de l'application"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 class='main-header'>🤖 SYSTÈME DE RECOMMANDATION AGENTIQUE</h1>", unsafe_allow_html=True)
        st.markdown("---")

def afficher_agents_sidebar():
    """Affiche les agents dans la sidebar"""
    with st.sidebar:
        st.markdown("## 🤖 Agents Actifs")
        
        agents = [
            {"nom": "Agent Profil", "role": "Gestion des profils clients", "emoji": "👤"},
            {"nom": "Agent Circuit", "role": "Analyse des circuits", "emoji": "🗺️"},
            {"nom": "Agent Feedback", "role": "Apprentissage des retours", "emoji": "📝"},
            {"nom": "Agent Principal", "role": "Coordination", "emoji": "🎯"}
        ]
        
        for agent in agents:
            with st.container():
                st.markdown(f"""
                <div class='agent-card'>
                    <b>{agent['emoji']} {agent['nom']}</b><br>
                    <small>{agent['role']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Statistiques rapides
        if 'agent_principal' in st.session_state:
            stats = st.session_state.agent_principal.get_statistiques()
            st.markdown("### 📊 Statistiques")
            st.metric("Clients actifs", stats['clients_actifs'])
            st.metric("Recommandations", stats['recommandations_generees'])
            st.metric("Satisfaction", f"{stats['taux_satisfaction']:.1f}/5")

def afficher_selection_client():
    """Affiche la sélection du client"""
    st.markdown("## 👤 Sélection du Client")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Récupérer la liste des clients disponibles
        if st.session_state.systeme and hasattr(st.session_state.systeme, 'clients'):
            clients_disponibles = list(st.session_state.systeme.clients.keys())
        else:
            clients_disponibles = ["user_1", "user_2", "user_3"]
        
        user_id = st.selectbox(
            "Choisissez un client :",
            options=clients_disponibles,
            index=0,
            key="user_select"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Charger le profil", use_container_width=True):
            st.session_state.user_id = user_id
            st.session_state.analyse_profil = st.session_state.agent_principal.analyser_profil_et_suggérer(user_id)
            st.rerun()
    
    return st.session_state.get('user_id', None)

def afficher_profil_client(user_id):
    """Affiche les informations du profil client"""
    if not user_id:
        return
    
    client = st.session_state.systeme.get_client(user_id)
    if not client:
        st.warning(f"Client {user_id} non trouvé")
        return
    
    st.markdown("---")
    st.markdown(f"## 📋 Profil de {getattr(client, 'nom', user_id)}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Époques préférées",
            ", ".join(getattr(client, 'preference_epoque', ['Non renseigné']))[:20]
        )
    
    with col2:
        st.metric(
            "Types préférés",
            ", ".join(getattr(client, 'types_preferes', ['Non renseigné']))[:20]
        )
    
    with col3:
        st.metric(
            "Budget max",
            f"{getattr(client, 'budget_max', 'N/A')} €"
        )
    
    with col4:
        st.metric(
            "Durée max",
            f"{getattr(client, 'duree_max', 'N/A')} min"
        )
    
    # Afficher les recommandations de l'agent profil
    if 'analyse_profil' in st.session_state and st.session_state.analyse_profil:
        with st.expander("💡 Recommandations Agent Profil", expanded=False):
            analyse = st.session_state.analyse_profil
            if analyse.get('recommandations_personnalisees'):
                for rec in analyse['recommandations_personnalisees']:
                    st.info(f"📌 {rec['message']}")

def afficher_recommandations(user_id):
    """Affiche les recommandations intelligentes"""
    st.markdown("---")
    st.markdown("## 🎯 Recommandations Intelligentes")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nb_recommandations = st.slider(
            "Nombre de recommandations :",
            min_value=3,
            max_value=10,
            value=5,
            key="nb_rec"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Générer", type="primary", use_container_width=True):
            with st.spinner("🤖 Les agents travaillent..."):
                recommandations = st.session_state.agent_principal.recommander_intelligemment(
                    user_id,
                    n=nb_recommandations,
                    contexte_supplementaire={'source': 'streamlit'}
                )
                st.session_state.recommandations = recommandations
            st.success("✅ Recommandations générées !")
            st.rerun()
    
    # Afficher les recommandations si disponibles
    if 'recommandations' in st.session_state and st.session_state.recommandations:
        rec_data = st.session_state.recommandations
        
        if not rec_data.get('success', False):
            st.error(rec_data.get('error', 'Erreur inconnue'))
            return
        
        st.markdown(f"### 📍 Top {len(rec_data['recommandations'])} circuits pour vous")
        
        # Afficher les explications
        if rec_data.get('explications'):
            with st.expander("💬 Pourquoi ces recommandations ?", expanded=False):
                for exp in rec_data['explications']:
                    st.markdown(f"- {exp['message']}")
        
        # Afficher chaque recommandation
        for i, rec in enumerate(rec_data['recommandations'], 1):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{i}. {rec['circuit_id']}**")
                    
                    # Types de monuments
                    types = rec.get('metadonnees_agents', {}).get('categorie', 'Non catégorisé')
                    st.markdown(f"📌 *{types}*")
                    
                    # Afficher les similaires si disponibles
                    similaires = rec.get('metadonnees_agents', {}).get('similaires', [])
                    if similaires:
                        st.markdown(f"🔄 Similaires : {', '.join([s['circuit_id'] for s in similaires[:2]])}")
                
                with col2:
                    duree = rec.get('duree_totale', 'N/A')
                    st.markdown(f"⏱️ **{duree} min**")
                
                with col3:
                    prix = rec.get('prix', 'N/A')
                    st.markdown(f"💰 **{prix} €**")
                
                with col4:
                    score = rec.get('score_global', 0)
                    if score >= 0.8:
                        st.markdown(f"<p class='score-high'>⭐ {score:.2f}</p>", unsafe_allow_html=True)
                    elif score >= 0.5:
                        st.markdown(f"<p class='score-medium'>⭐ {score:.2f}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p class='score-low'>⭐ {score:.2f}</p>", unsafe_allow_html=True)
                
                # Bouton pour donner un feedback
                if st.button(f"📝 Donner mon avis", key=f"feedback_btn_{rec['circuit_id']}", use_container_width=True):
                    st.session_state.feedback_circuit = rec['circuit_id']
                    st.session_state.show_feedback = True
                
                st.markdown("---")

def afficher_feedback(user_id):
    """Affiche le formulaire de feedback"""
    if not st.session_state.get('show_feedback', False):
        return
    
    st.markdown("---")
    st.markdown("## 📝 Donner votre avis")
    
    circuit_id = st.session_state.feedback_circuit
    
    with st.form(key="feedback_form"):
        st.markdown(f"### Circuit : {circuit_id}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            note = st.slider(
                "Note (sur 5) :",
                min_value=0.0,
                max_value=5.0,
                value=4.0,
                step=0.5,
                format="%.1f"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if note >= 4:
                st.markdown("<div class='feedback-positif'>😊 Excellent choix !</div>", unsafe_allow_html=True)
            elif note >= 3:
                st.markdown("<div class='feedback-positif'>👍 Satisfaisant</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='feedback-negatif'>😕 À améliorer</div>", unsafe_allow_html=True)
        
        commentaire = st.text_area(
            "Commentaire (optionnel) :",
            placeholder="Partagez votre expérience...",
            max_chars=200
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submit = st.form_submit_button("✅ Envoyer", use_container_width=True)
        
        with col2:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submit:
            with st.spinner("🤖 Agent Feedback en action..."):
                resultat = st.session_state.agent_principal.traiter_feedback_utilisateur(
                    user_id,
                    circuit_id,
                    note,
                    commentaire
                )
                
                if resultat['success']:
                    st.success(resultat['remerciement'])
                    st.balloons()
                    
                    # Afficher l'analyse
                    with st.expander("🔍 Analyse du feedback", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Sentiment", resultat['feedback']['analyse']['sentiment'])
                        with col2:
                            st.metric("Confiance", f"{resultat['feedback']['analyse']['confiance']:.0%}")
                        
                        if resultat.get('tendances_mises_a_jour'):
                            st.info(f"Moyenne globale : {resultat['tendances_mises_a_jour']['moyenne_globale']:.2f}/5")
                    
                    # Réinitialiser
                    st.session_state.show_feedback = False
                    st.session_state.feedback_circuit = None
                    
                    # Mettre à jour l'analyse du profil
                    st.session_state.analyse_profil = st.session_state.agent_principal.analyser_profil_et_suggérer(user_id)
                    
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement du feedback")
        
        if cancel:
            st.session_state.show_feedback = False
            st.session_state.feedback_circuit = None
            st.rerun()

def afficher_tableau_bord():
    """Affiche le tableau de bord des agents"""
    st.markdown("---")
    st.markdown("## 📊 Tableau de Bord des Agents")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Tendances", "🏆 Top Circuits", "🤖 Stats Agents", "📁 Données"])
    
    with tab1:
        st.markdown("### Tendances des Feedbacks")
        
        # Analyser les tendances
        tendances = st.session_state.agent_feedback.analyser_tendances()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Feedbacks",
                tendances['total_feedbacks']
            )
        
        with col2:
            st.metric(
                "Moyenne Globale",
                f"{tendances['moyenne_generale']:.2f}/5"
            )
        
        with col3:
            st.metric(
                "Circuits Évalués",
                len(st.session_state.agent_feedback.tendances)
            )
        
        # Distribution des notes
        if tendances['distribution_globale']:
            fig = px.bar(
                x=list(tendances['distribution_globale'].keys()),
                y=list(tendances['distribution_globale'].values()),
                labels={'x': 'Note', 'y': 'Nombre'},
                title="Distribution des Notes",
                color_discrete_sequence=['#FF4B4B']
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### Top Circuits")
        
        # Circuits les plus appréciés
        populaires = st.session_state.agent_feedback.get_circuits_populaires(5)
        
        if populaires:
            df_top = pd.DataFrame(populaires)
            df_top.columns = ['Circuit', 'Feedbacks', 'Moyenne']
            st.dataframe(df_top, use_container_width=True)
            
            # Graphique
            fig = px.bar(
                df_top,
                x='Circuit',
                y='Moyenne',
                color='Feedbacks',
                title="Top 5 Circuits par Note",
                labels={'Moyenne': 'Note moyenne', 'Feedbacks': 'Nb feedbacks'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Statistiques des Agents")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Agent Profil
            stats_profil = st.session_state.agent_profil.get_statistiques()
            st.markdown("**👤 Agent Profil**")
            st.json({
                "Analyses": stats_profil['nb_analyses_effectuees'],
                "Clients analysés": stats_profil['clients_analyses']
            })
        
        with col2:
            # Agent Circuit
            stats_circuit = st.session_state.agent_circuit.get_statistiques()
            st.markdown("**🗺️ Agent Circuit**")
            st.json({
                "Circuits": stats_circuit['total_circuits'],
                "Catégories": len(stats_circuit['categories']),
                "Suggestions": stats_circuit['nb_suggestions_effectuees']
            })
    
    with tab4:
        st.markdown("### Données Brutes")
        
        data_type = st.radio(
            "Choisir les données à afficher :",
            ["Clients", "Circuits", "Feedbacks"],
            horizontal=True
        )
        
        if data_type == "Clients":
            if hasattr(st.session_state.systeme, 'clients'):
                clients_data = []
                for client_id, client in st.session_state.systeme.clients.items():
                    clients_data.append({
                        "ID": client_id,
                        "Nom": getattr(client, 'nom', 'N/A'),
                        "Budget": getattr(client, 'budget_max', 'N/A'),
                        "Durée": getattr(client, 'duree_max', 'N/A')
                    })
                st.dataframe(pd.DataFrame(clients_data), use_container_width=True)
        
        elif data_type == "Circuits":
            if hasattr(st.session_state.systeme.calculateur, 'circuits'):
                df_circuits = pd.DataFrame(st.session_state.systeme.calculateur.circuits)
                st.dataframe(df_circuits, use_container_width=True)
        
        else:  # Feedbacks
            if st.session_state.agent_feedback.historique_feedbacks:
                df_feedbacks = pd.DataFrame(st.session_state.agent_feedback.historique_feedbacks)
                st.dataframe(df_feedbacks, use_container_width=True)

def afficher_enrichissement_profil(user_id):
    """Affiche la section d'enrichissement du profil"""
    st.markdown("---")
    st.markdown("## ✨ Enrichir mon profil")
    
    with st.expander("➕ Ajouter des préférences", expanded=False):
        with st.form(key="enrich_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nouvelles_epoques = st.multiselect(
                    "Ajouter des époques :",
                    options=["romaine", "punique", "byzantine", "arabe", "ottomane", "moderne"],
                    help="Sélectionnez les époques qui vous intéressent"
                )
            
            with col2:
                nouveaux_types = st.multiselect(
                    "Ajouter des types :",
                    options=["culturel", "religieux", "nature", "aventure", "historique", "familial"],
                    help="Sélectionnez les types de monuments"
                )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                nouveau_budget = st.number_input(
                    "Budget max (€) :",
                    min_value=0,
                    max_value=200,
                    value=50,
                    step=10
                )
            
            with col2:
                nouvelle_duree = st.number_input(
                    "Durée max (min) :",
                    min_value=30,
                    max_value=480,
                    value=180,
                    step=30
                )
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                submit_enrich = st.form_submit_button("✅ Enrichir", use_container_width=True)
            
            if submit_enrich:
                nouvelles_prefs = {}
                
                if nouvelles_epoques:
                    nouvelles_prefs['epoques'] = nouvelles_epoques
                if nouveaux_types:
                    nouvelles_prefs['types'] = nouveaux_types
                if nouveau_budget:
                    nouvelles_prefs['budget'] = nouveau_budget
                if nouvelle_duree:
                    nouvelles_prefs['duree'] = nouvelle_duree
                
                if nouvelles_prefs:
                    with st.spinner("🤖 Agent Profil en action..."):
                        success = st.session_state.agent_profil.enrichir_profil(user_id, nouvelles_prefs)
                        
                        if success:
                            st.success("✅ Profil enrichi avec succès !")
                            
                            # Mettre à jour l'analyse
                            st.session_state.analyse_profil = st.session_state.agent_principal.analyser_profil_et_suggérer(user_id)
                            
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de l'enrichissement")

# fonction principale de l'application

def main():
    
    
    # Initialisation de la session
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.systeme = None
        st.session_state.agent_principal = None
        st.session_state.agent_profil = None
        st.session_state.agent_circuit = None
        st.session_state.agent_feedback = None
        st.session_state.user_id = None
        st.session_state.recommandations = None
        st.session_state.show_feedback = False
        st.session_state.feedback_circuit = None
        st.session_state.analyse_profil = None
    
    # Initialisation du système
    if not st.session_state.initialized:
        with st.spinner("🚀 Initialisation du système agentique..."):
            systeme, agent_principal = init_systeme()
            
            if systeme and agent_principal:
                st.session_state.systeme = systeme
                st.session_state.agent_principal = agent_principal
                st.session_state.agent_profil = agent_principal.agent_profil
                st.session_state.agent_circuit = agent_principal.agent_circuit
                st.session_state.agent_feedback = agent_principal.agent_feedback
                st.session_state.initialized = True
                st.success("✅ Système initialisé avec succès !")
            else:
                st.error("❌ Échec de l'initialisation")
                return
    
    # Affichage de l'interface
    afficher_entete()
    afficher_agents_sidebar()
    
    # Sélection du client
    user_id = afficher_selection_client()
    
    if user_id:
        # Afficher le profil
        afficher_profil_client(user_id)
        
        # Afficher les recommandations
        afficher_recommandations(user_id)
        
        # Afficher le feedback si demandé
        afficher_feedback(user_id)
        
        # Afficher l'enrichissement de profil
        afficher_enrichissement_profil(user_id)
        
        # Afficher le tableau de bord
        afficher_tableau_bord()

# ==================== LANCEMENT ====================

if __name__ == "__main__":
    main()