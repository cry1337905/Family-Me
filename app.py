import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client

# Supabase-Verbindung herstellen
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.title("Familienberatung – Analyse & Verlauf")

# Navigation
menu = ["Familie anlegen", "Mitglied anlegen", "Einschätzung erfassen", "Analyse & Auswertung"]
wahl = st.sidebar.selectbox("Menü", menu)

if wahl == "Familie anlegen":
    st.subheader("Neue Familie registrieren")
    name = st.text_input("Familienname")
    email = st.text_input("Kontakt-E-Mail")
    if st.button("Speichern"):
        supabase.table("familien").insert({"familienname": name, "kontakt_email": email}).execute()
        st.success(f"Familie {name} erfolgreich angelegt!")

elif wahl == "Mitglied anlegen":
    st.subheader("Familienmitglied hinzufügen")
    
    # Familien abfragen für Dropdown
    fam_response = supabase.table("familien").select("id, familienname").execute()
    familien = {f['familienname']: f['id'] for f in fam_response.data}
    
    if familien:
        fam_wahl = st.selectbox("Familie auswählen", list(familien.keys()))
        vorname = st.text_input("Vorname")
        rolle = st.selectbox("Rolle", ["Kind", "Mutter", "Vater", "Sonstige"])
        geburtsdatum = st.date_input("Geburtsdatum")
        
        if st.button("Mitglied Speichern"):
            supabase.table("mitglieder").insert({
                "familie_id": familien[fam_wahl],
                "vorname": vorname,
                "rolle": rolle,
                "geburtsdatum": str(geburtsdatum)
            }).execute()
            st.success(f"{vorname} wurde hinzugefügt.")

elif wahl == "Einschätzung erfassen":
    st.subheader("Neueinschätzung / Evaluation")
    
    mitgl_response = supabase.table("mitglieder").select("id, vorname, rolle").execute()
    mitglieder = {f"{m['vorname']} ({m['rolle']})": m['id'] for m in mitgl_response.data}
    
    if mitglieder:
        m_wahl = st.selectbox("Person auswählen", list(mitglieder.keys()))
        typ = st.selectbox("Zeitpunkt", ["T0 (Ersteinschätzung)", "T1 (Follow-up)", "T2 (Abschluss)"])
        datum = st.date_input("Datum der Einschätzung")
        
        st.write("---")
        sv = st.slider("Sozialverhalten (1-10)", 1, 10, 5)
        er = st.slider("Emotionsregulation (1-10)", 1, 10, 5)
        sm = st.slider("Schulische Motivation (1-10)", 1, 10, 5)
        komm = st.slider("Kommunikation (1-10)", 1, 10, 5)
        
        if st.button("Einschätzung speichern"):
            supabase.table("einschaetzungen").insert({
                "mitglied_id": mitglieder[m_wahl],
                "zeitpunkt_typ": typ,
                "datum": str(datum),
                "sozialverhalten": sv,
                "emotionsregulation": er,
                "schulische_motivation": sm,
                "kommunikation": komm
            }).execute()
            st.success("Einschätzung gespeichert!")

elif wahl == "Analyse & Auswertung":
    st.subheader("Entwicklungsvergleich (Vorher / Nachher)")
    
    mitgl_response = supabase.table("mitglieder").select("id, vorname").execute()
    mitglieder = {m['vorname']: m['id'] for m in mitgl_response.data}
    
    if mitglieder:
        m_wahl = st.selectbox("Person zur Analyse wählen", list(mitglieder.keys()))
        m_id = mitglieder[m_wahl]
        
        # Daten aus Supabase laden
        data = supabase.table("einschaetzungen").select("*").eq("mitglied_id", m_id).order("datum").execute().data
        
        if len(data) >= 2:
            df = pd.DataFrame(data)
            categories = ['Sozialverhalten', 'Emotionsregulation', 'Schul. Motivation', 'Kommunikation']
            
            # Erste vs. Letzte Einschätzung
            t0 = df.iloc[0]
            t_neu = df.iloc[-1]
            
            fig = go.Figure()

            fig.add_trace(go.Scatterpolar(
                r=[t0['sozialverhalten'], t0['emotionsregulation'], t0['schulische_motivation'], t0['kommunikation']],
                theta=categories, fill='toself', name=f"Start: {t0['zeitpunkt_typ']} ({t0['datum']})"
            ))
            
            fig.add_trace(go.Scatterpolar(
                r=[t_neu['sozialverhalten'], t_neu['emotionsregulation'], t_neu['schulische_motivation'], t_neu['kommunikation']],
                theta=categories, fill='toself', name=f"Aktuell: {t_neu['zeitpunkt_typ']} ({t_neu['datum']})"
            ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                showlegend=True,
                title=f"Fortschrittsanalyse für {m_wahl}"
            )

            st.plotly_chart(fig)
        else:
            st.info("Es müssen mindestens zwei Einschätzungen (T0 und T1) vorliegen, um ein Verlaufsdiagramm zu erzeugen.")