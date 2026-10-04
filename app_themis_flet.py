import datetime
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import webbrowser
import base64
import flet as ft
import pandas as pd

from contract_templates import (
    generate_dossier_contractuel_html,
    text_to_html_list,
    generate_avenant_flash_html,
    generate_rapport_mco_html,
    generate_revocation_secrets_html,
    generate_blueprint_html,
    generate_livret_accueil_html,
)

# ---------------------------------------------------------------------------
# Chemins sécurisés (Compatible Bureau & Compilation PyInstaller)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "devis_suivi.db")
SCANS_DIR = os.path.join(BASE_DIR, "scans_contrats")
os.makedirs(SCANS_DIR, exist_ok=True)

LOGO_PATH = os.path.join(BUNDLE_DIR, "themis.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(BASE_DIR, "themis.png")

ICO_PATH = os.path.join(BUNDLE_DIR, "Themis.ico")
if not os.path.exists(ICO_PATH):
    ICO_PATH = os.path.join(BUNDLE_DIR, "themis.ico")
if not os.path.exists(ICO_PATH):
    ICO_PATH = os.path.join(BASE_DIR, "Themis.ico")
if not os.path.exists(ICO_PATH):
    ICO_PATH = os.path.join(BASE_DIR, "themis.ico")

# ---------------------------------------------------------------------------
# Palette Thémis & Thèmes Métier
# ---------------------------------------------------------------------------
THEME = {
    "cream": "#FAF7F2",
    "cream_card": "#FFFFFF",
    "sage": "#6E8A85",
    "sage_dark": "#55706B",
    "sage_light": "#C4D2C2",
    "sage_pale": "#E7EEE6",
    "blush": "#EFC9C3",
    "blush_dark": "#D9A79F",
    "blush_pale": "#FBEDEA",
    "text": "#2D3748",
    "text_muted": "#718096",
}

SECTION_COLORS = {
    "general": {"icon_bg": "#EBF8FF", "icon_color": "#2B6CB0", "text_color": "#2B6CB0"},
    "production": {"icon_bg": "#FAF5FF", "icon_color": "#6B46C1", "text_color": "#553C9A"},
    "crm": {"icon_bg": "#E6FFFA", "icon_color": "#2C7A7B", "text_color": "#234E52"},
    "facturation": {"icon_bg": "#FEFCBF", "icon_color": "#B7791F", "text_color": "#975A16"},
    "finance": {"icon_bg": "#F0FFF4", "icon_color": "#22543D", "text_color": "#1C4532"},
    "systeme": {"icon_bg": "#EDF2F7", "icon_color": "#4A5568", "text_color": "#2D3748"},
}

DEFAULT_ENTREPRISE_NOM = "LYSIS - Atelier Textile"
DEFAULT_ENTREPRISE_ADRESSE = "Capesterre-Belle-Eau, Guadeloupe"

PLAFOND_MICRO_BNC = 77700.00
SEUIL_TVA_BASE = 36800.00

STATUTS_FACTURES = ["Facture Émise", "Facture Annulée", "Facture Acquittée"]
STATUTS_DEVIS = ["Brouillon", "Envoyé au client", "Validé & Signé", "En cours de réalisation"]
TYPES_CATALOGUE = ["Setup / Création", "Abonnement Mensuel", "Maintenance", "Prestation Horaire", "Autre"]
CATEGORIES_DEPENSES = ["Serveurs & Cloud", "Abonnements SaaS & Outils", "Matériel Informatique", "Télécom & Internet", "Déplacements & Représentation", "Frais Bancaires / Assurances", "Autre"]
MODES_REGLEMENT = ["Virement bancaire", "Carte bancaire", "Prélèvement", "Chèque", "Espèces"]
COLONNES_KANBAN = ["À faire", "En cours", "En test", "Terminé"]
PRIORITES = ["Basse", "Normale", "Haute", "Urgente"]


# ---------------------------------------------------------------------------
# Base de Données SQLite
# ---------------------------------------------------------------------------
def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            societe TEXT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            adresse TEXT NOT NULL,
            telephone TEXT,
            email TEXT,
            siret TEXT,
            notes TEXT,
            date_creation TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalogue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            designation TEXT NOT NULL,
            type_service TEXT NOT NULL,
            prix_unitaire_ht REAL NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_devis TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            date_creation TEXT NOT NULL,
            date_validite TEXT NOT NULL,
            client_nom TEXT NOT NULL,
            client_prenom TEXT NOT NULL,
            client_societe TEXT,
            client_adresse TEXT NOT NULL,
            client_telephone TEXT,
            client_email TEXT,
            montant_setup REAL NOT NULL,
            montant_abo REAL NOT NULL,
            pourcentage_acompte INTEGER NOT NULL,
            statut TEXT NOT NULL,
            sections_json TEXT,
            lignes_json TEXT,
            roi_heures_semaine REAL DEFAULT 0.0,
            roi_cout_horaire REAL DEFAULT 25.0,
            contrat_signe INTEGER DEFAULT 0,
            date_signature_contrat TEXT,
            archive INTEGER DEFAULT 0,
            motif_archivage TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_facture TEXT UNIQUE NOT NULL,
            numero_devis TEXT NOT NULL,
            type_facture TEXT NOT NULL,
            date_facture TEXT NOT NULL,
            date_echeance TEXT NOT NULL,
            montant_ht REAL NOT NULL,
            statut TEXT NOT NULL,
            numero_facture_liee TEXT,
            motif TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entreprise (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nom TEXT NOT NULL,
            adresse TEXT NOT NULL,
            siret TEXT,
            rcs_rm TEXT,
            forme_juridique TEXT,
            taux_urssaf REAL DEFAULT 21.2,
            taux_ir REAL DEFAULT 2.2
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facture_id INTEGER,
            numero_facture TEXT NOT NULL,
            date_paiement TEXT NOT NULL,
            client_nom TEXT NOT NULL,
            nature_prestation TEXT NOT NULL,
            montant_recu REAL NOT NULL,
            mode_paiement TEXT NOT NULL,
            reference_reglement TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_depense TEXT NOT NULL,
            fournisseur TEXT NOT NULL,
            categorie TEXT NOT NULL,
            montant REAL NOT NULL,
            mode_paiement TEXT NOT NULL,
            justificatif_ref TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id TEXT,
            client_nom TEXT NOT NULL,
            nom_projet TEXT NOT NULL,
            description TEXT,
            date_debut TEXT NOT NULL,
            date_livraison_prevue TEXT,
            statut TEXT DEFAULT 'En cours',
            budget_ht REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS taches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id INTEGER NOT NULL,
            titre TEXT NOT NULL,
            description TEXT,
            colonne TEXT NOT NULL,
            priorite TEXT DEFAULT 'Normale',
            heures_estimees REAL DEFAULT 0.0,
            heures_passees REAL DEFAULT 0.0,
            date_creation TEXT,
            FOREIGN KEY (projet_id) REFERENCES projets (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_avenant TEXT UNIQUE NOT NULL,
            devis_id TEXT NOT NULL,
            date_avenant TEXT NOT NULL,
            description_demande TEXT NOT NULL,
            impact_prix_ht REAL NOT NULL,
            impact_delai_jours INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'Validé'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mco_suivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            mois TEXT NOT NULL,
            flux_surveilles INTEGER DEFAULT 1,
            operations_traitees INTEGER DEFAULT 0,
            incidents_resolus INTEGER DEFAULT 0,
            statut_sante TEXT DEFAULT '100% Opérationnel',
            commentaires TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secrets_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            service_nom TEXT NOT NULL,
            type_identifiant TEXT NOT NULL,
            valeur_cle TEXT NOT NULL,
            statut TEXT DEFAULT 'Actif chez prestataire',
            date_ajout TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id INTEGER NOT NULL,
            nom_flux TEXT NOT NULL,
            declencheur TEXT NOT NULL,
            etapes_json TEXT NOT NULL,
            donnees_mappees TEXT,
            FOREIGN KEY (projet_id) REFERENCES projets (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            devis_id TEXT,
            nom_document TEXT NOT NULL,
            chemin_fichier TEXT NOT NULL,
            date_upload TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    for col in [
        "client_id INTEGER", "lignes_json TEXT", "sections_json TEXT",
        "roi_heures_semaine REAL DEFAULT 0.0", "roi_cout_horaire REAL DEFAULT 25.0",
        "contrat_signe INTEGER DEFAULT 0", "date_signature_contrat TEXT",
        "archive INTEGER DEFAULT 0", "motif_archivage TEXT"
    ]:
        try: cursor.execute(f"ALTER TABLE devis ADD COLUMN {col}")
        except sqlite3.OperationalError: pass

    for col in ["numero_facture_liee TEXT", "motif TEXT"]:
        try: cursor.execute(f"ALTER TABLE factures ADD COLUMN {col}")
        except sqlite3.OperationalError: pass

    for col in ["taux_urssaf REAL DEFAULT 21.2", "taux_ir REAL DEFAULT 2.2"]:
        try: cursor.execute(f"ALTER TABLE entreprise ADD COLUMN {col}")
        except sqlite3.OperationalError: pass

    cursor.execute(
        """
        INSERT OR IGNORE INTO entreprise (id, nom, adresse, siret, rcs_rm, forme_juridique, taux_urssaf, taux_ir)
        VALUES (1, ?, ?, '', '', '', 21.2, 2.2)
        """,
        (DEFAULT_ENTREPRISE_NOM, DEFAULT_ENTREPRISE_ADRESSE),
    )

    catalogue_officiel = [
        ("AUTO-CPX-03", "Forfait Automatisation Avancée — APIs Sur-Mesure & Données Complexes", "Setup / Création", 1600.00, "Développement sur-mesure, OAuth2, Webhooks, flux volumineux"),
        ("AUTO-INT-02", "Forfait Automatisation Métier — Flux Multi-étapes & Routage Conditionnel", "Setup / Création", 490.00, "Intégration 3-5 apps, logique conditionnelle et nettoyage"),
        ("AUTO-SMP-01", "Forfait Automatisation Simple — Flux Linéaire (2 applications)", "Setup / Création", 190.00, "Conception et déploiement d'un flux automatisé direct"),
        ("SRV-CONF-01", "Pack Maintenance + Support Prioritaire & Abonnement Hébergement Cloud + Maintien Opérationnel", "Abonnement Mensuel", 120.00, "Hébergement cloud, maintien opérationnel, sauvegardes et support prioritaire"),
        ("SRV-SETUP-01", "Développement Application Sur-Mesure (Setup initial)", "Setup / Création", 700.00, "Conception, développement et déploiement initial de l'application"),
        ("SRV-DEV-H", "Prestation de Développement Spécifique (Taux Horaire)", "Prestation Horaire", 65.00, "Facturation horaire à la demande pour développements spécifiques"),
        ("SRV-MAINT-01", "Abonnement Pack Maintenance Évolutive & Support Prioritaire", "Abonnement Mensuel", 85.00, "Assistance, correctifs et évolutions mineures mensuelles"),
        ("SRV-ABO-01", "Abonnement Hébergement Cloud & Maintien Opérationnel", "Abonnement Mensuel", 50.00, "Supervision continue et sauvegardes quotidiennes"),
    ]

    for item in catalogue_officiel:
        cursor.execute(
            """
            INSERT INTO catalogue (reference, designation, type_service, prix_unitaire_ht, description)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(reference) DO UPDATE SET
                designation=excluded.designation,
                type_service=excluded.type_service,
                prix_unitaire_ht=excluded.prix_unitaire_ht,
                description=excluded.description
            """,
            item,
        )

    conn.commit()
    conn.close()


def sanitize_tag(text: str) -> str:
    """Nettoie le nom de l'entreprise ou du client pour l'intégrer au numéro de facture."""
    if not text:
        return "CLIENT"
    clean = re.sub(r"[^a-zA-Z0-9]", "", text.strip().upper())
    return clean[:14] if clean else "CLIENT"


def get_next_devis():
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.date.today().strftime("%Y%m")
    cursor.execute("SELECT numero_devis FROM devis WHERE numero_devis LIKE ? ORDER BY id DESC LIMIT 1", (f"DEV-{today_str}-%",))
    res = cursor.fetchone()
    conn.close()
    if res:
        try:
            last_seq = int(res[0].split("-")[-1])
            return f"DEV-{today_str}-{str(last_seq + 1).zfill(2)}"
        except Exception: pass
    return f"DEV-{today_str}-01"


def get_next_avoir(client_tag: str = "CLIENT"):
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.date.today().strftime("%Y%m")
    cursor.execute("SELECT numero_facture FROM factures WHERE numero_facture LIKE ? ORDER BY id DESC LIMIT 1", (f"AV-{today_str}-%",))
    res = cursor.fetchone()
    conn.close()
    seq_str = "01"
    if res:
        try:
            parts = res[0].split("_")[0].split("-")
            last_seq = int(parts[-1])
            seq_str = str(last_seq + 1).zfill(2)
        except Exception: pass
    return f"AV-{today_str}-{seq_str}_{client_tag}"


def get_next_avenant(devis_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM avenants WHERE devis_id = ?", (devis_num,))
    c = cursor.fetchone()[0]
    conn.close()
    return f"AVN-{devis_num}-{str(c + 1).zfill(2)}"


def get_entreprise_info():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nom, adresse, siret, rcs_rm, forme_juridique, taux_urssaf, taux_ir FROM entreprise WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "nom": row[0] or "",
            "adresse": row[1] or "",
            "siret": row[2] or "Non renseigné",
            "rcs_rm": row[3] or "Non renseigné",
            "forme_juridique": row[4] or "Non renseigné",
            "taux_urssaf": float(row[5]) if row[5] is not None else 21.2,
            "taux_ir": float(row[6]) if row[6] is not None else 2.2,
        }
    return {"nom": "", "adresse": "", "siret": "Non renseigné", "rcs_rm": "Non renseigné", "forme_juridique": "Non renseigné", "taux_urssaf": 21.2, "taux_ir": 2.2}


def get_app_logo_base64():
    for p in [LOGO_PATH, os.path.join(BASE_DIR, "themis.png"), "themis.png", "Themis.png"]:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception: pass
    return None


# ---------------------------------------------------------------------------
# Composants UI Communs & Pied de Page
# ---------------------------------------------------------------------------
def create_card(content, padding=24):
    return ft.Container(
        content=content,
        bgcolor=THEME["cream_card"],
        border=ft.border.all(1, THEME["sage_light"]),
        border_radius=14,
        padding=padding,
        shadow=ft.BoxShadow(blur_radius=10, color="#0A000000", offset=ft.Offset(0, 3)),
    )


def create_header(icon_char, title, subtitle):
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(icon_char, size=26),
                    bgcolor=THEME["blush_pale"],
                    border_radius=14,
                    width=54,
                    height=54,
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    controls=[
                        ft.Text(title, size=23, weight=ft.FontWeight.BOLD, color=THEME["text"]),
                        ft.Text(subtitle, size=13, color=THEME["text_muted"]),
                    ],
                    spacing=2,
                ),
            ],
            spacing=18,
        ),
        margin=ft.margin.only(bottom=25, top=5),
    )


def build_footer():
    now = datetime.date.today()
    mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mois_nom = mois_fr[now.month - 1]
    annee = now.year

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(f"© Dhamusoft — Tous droits réservés • {mois_nom} {annee}", size=11, color=THEME["text_muted"], weight=ft.FontWeight.W_500),
                ft.Text("Themis ERP Suite • Édition Micro-Entreprise", size=10, color=THEME["text_muted"], italic=True),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(vertical=18),
        border=ft.border.only(top=ft.BorderSide(1, THEME["sage_light"])),
        margin=ft.margin.only(top=35, bottom=15),
    )


def show_toast(page: ft.Page, message: str, is_error: bool = False):
    sb = ft.SnackBar(
        content=ft.Text(message, color=ft.colors.WHITE, weight=ft.FontWeight.W_500),
        bgcolor=THEME["sage_dark"] if not is_error else ft.colors.RED_700,
        duration=4000,
    )
    if hasattr(page, "open"): page.open(sb)
    else:
        page.snack_bar = sb
        page.snack_bar.open = True
        page.update()


def execute_print_facture(numero_facture, page: ft.Page):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT f.*, d.client_nom, d.client_prenom, d.client_societe, d.client_adresse
        FROM factures f
        JOIN devis d ON f.numero_devis = d.numero_devis
        WHERE f.numero_facture = ?
        """,
        (numero_facture,),
    )
    f = cursor.fetchone()
    ent = get_entreprise_info()
    conn.close()

    if not f:
        show_toast(page, "Facture introuvable.", is_error=True)
        return

    statut = f["statut"]
    stamp_html = ""
    if statut in ["Facture Acquittée", "Payée"]:
        stamp_html = '<div style="position: absolute; top: 120px; right: 50px; transform: rotate(-14deg); border: 3px solid #2F855A; color: #2F855A; font-size: 26px; font-weight: 800; padding: 6px 20px; border-radius: 8px; opacity: 0.85; letter-spacing: 2px;">PAYÉE</div>'
    elif statut in ["Facture Annulée", "Annulée"]:
        stamp_html = '<div style="position: absolute; top: 120px; right: 50px; transform: rotate(-14deg); border: 3px solid #C53030; color: #C53030; font-size: 26px; font-weight: 800; padding: 6px 20px; border-radius: 8px; opacity: 0.85; letter-spacing: 2px;">ANNULÉE</div>'

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Facture_{f['numero_facture']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #333; }}
        .page {{ position: relative; width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); box-sizing: border-box; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #CBD5E0; padding: 8px 10px; font-size: 12px; }}
        th {{ background: #E7EEE6; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {stamp_html}
        <h2>{ent['nom']}</h2>
        <p>{ent['adresse']}<br>SIRET : {ent['siret']}</p>
        <hr>
        <h1>{f['type_facture'].upper()} N° {f['numero_facture']}</h1>
        <p>Date : {f['date_facture']} | Devis de référence : {f['numero_devis']}</p>
        <p><strong>Facturé à :</strong> {f['client_societe'] or 'Particulier'} ({f['client_prenom']} {f['client_nom']})<br>{f['client_adresse']}</p>
        <table>
            <tr><th>Désignation</th><th style="text-align: right;">Montant HT</th></tr>
            <tr><td>{f['type_facture']} — Devis {f['numero_devis']}</td><td style="text-align: right;">{float(f['montant_ht']):.2f} €</td></tr>
        </table>
        <h3 style="text-align: right;">NET À PAYER : {float(f['montant_ht']):.2f} €</h3>
        <p style="font-size: 10px; color: #777;">TVA non applicable, art. 293 B du CGI. Pénalités de retard applicables de plein droit selon art. L441-10 du Code de Commerce. Indemnité forfaitaire de recouvrement : 40 €.</p>
    </div>
    </body></html>"""

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
        tf.write(html)
        temp_path = tf.name

    webbrowser.open(f"file://{temp_path}")
    show_toast(page, f"Facture {numero_facture} ouverte pour impression.")


# ---------------------------------------------------------------------------
# Moteur de Détection des Anomalies & Abonnements Dus
# ---------------------------------------------------------------------------
def check_anomalies_facturation():
    """Scanne la base pour détecter les décalages de compte et les factures d'abonnements manquantes."""
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    current_month_str = today.strftime("%Y-%m")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    anomalies = {
        "acomptes_manquants": [],
        "soldes_manquants": [],
        "abonnements_dus": [],
        "factures_en_retard": [],
        "factures_en_attente": [],
    }

    cursor.execute("""
        SELECT numero_devis, client_societe, client_nom, client_prenom, montant_setup, montant_abo, pourcentage_acompte, date_creation
        FROM devis
        WHERE statut = 'Validé & Signé' AND contrat_signe = 1 AND archive = 0
    """)
    devis_signes = cursor.fetchall()

    for d in devis_signes:
        num_d = d["numero_devis"]
        client = d["client_societe"] or f"{d['client_prenom']} {d['client_nom']}"
        setup = float(d["montant_setup"])
        abo = float(d["montant_abo"])
        pct_acompte = int(d["pourcentage_acompte"])

        cursor.execute("SELECT numero_facture, type_facture, statut, date_facture FROM factures WHERE numero_devis = ?", (num_d,))
        factures_liees = cursor.fetchall()
        types_emis = [f["type_facture"] for f in factures_liees]

        if pct_acompte > 0 and "Facture d'Acompte" not in types_emis and setup > 0:
            val_acompte = setup * (pct_acompte / 100.0)
            anomalies["acomptes_manquants"].append({
                "numero_devis": num_d,
                "client": client,
                "montant": val_acompte,
            })

        has_acompte_paye = any(f["type_facture"] == "Facture d'Acompte" and f["statut"] in ["Facture Acquittée", "Payée"] for f in factures_liees)
        if (has_acompte_paye or pct_acompte == 0) and "Facture de Solde" not in types_emis and setup > 0:
            val_solde = setup if pct_acompte == 0 else setup * (1 - (pct_acompte / 100.0))
            anomalies["soldes_manquants"].append({
                "numero_devis": num_d,
                "client": client,
                "montant": val_solde,
            })

        if abo > 0:
            facture_abo_ce_mois = any(
                f["type_facture"] == "Facture d'Abonnement Mensuel" and current_month_str in f["numero_facture"]
                for f in factures_liees
            )
            if not facture_abo_ce_mois:
                anomalies["abonnements_dus"].append({
                    "numero_devis": num_d,
                    "client": client,
                    "montant": abo,
                    "mois": current_month_str,
                })

    cursor.execute("""
        SELECT f.numero_facture, f.numero_devis, f.montant_ht, f.date_facture, f.date_echeance, 
               d.client_societe, d.client_nom, d.client_prenom
        FROM factures f
        JOIN devis d ON f.numero_devis = d.numero_devis
        WHERE f.statut = 'Facture Émise' AND f.type_facture != 'Avoir'
    """)
    factures_en_cours = cursor.fetchall()

    for f in factures_en_cours:
        client = f["client_societe"] or f"{f['client_prenom']} {f['client_nom']}"
        item = {
            "numero_facture": f["numero_facture"],
            "numero_devis": f["numero_devis"],
            "client": client,
            "montant": float(f["montant_ht"]),
            "date_echeance": f["date_echeance"],
        }
        if f["date_echeance"] < today_str:
            anomalies["factures_en_retard"].append(item)
        else:
            anomalies["factures_en_attente"].append(item)

    conn.close()
    return anomalies


def build_radar_vigilance(page: ft.Page):
    ano = check_anomalies_facturation()
    nb_retards = len(ano["factures_en_retard"])
    nb_acomptes = len(ano["acomptes_manquants"])
    nb_soldes = len(ano["soldes_manquants"])
    nb_abos = len(ano["abonnements_dus"])

    total_actions = nb_retards + nb_acomptes + nb_soldes + nb_abos

    if total_actions == 0 and len(ano["factures_en_attente"]) == 0:
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.VERIFIED_ROUNDED, color=ft.colors.GREEN_700, size=24),
                ft.Column([
                    ft.Text("Radar de Trésorerie : Aucune anomalie comptable détectée ✅", size=13, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_900),
                    ft.Text("Tous les acomptes, soldes et abonnements du mois sont facturés et à jour.", size=11, color=ft.colors.GREEN_800),
                ], spacing=2),
            ], spacing=12),
            bgcolor=ft.colors.GREEN_50,
            border=ft.border.all(1, ft.colors.GREEN_300),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        )

    items_ui = []

    for r in ano["factures_en_retard"]:
        items_ui.append(
            ft.Row([
                ft.Row([
                    ft.Container(content=ft.Text("IMPAYÉ / RETARD", size=10, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), bgcolor=ft.colors.RED_700, border_radius=4, padding=ft.padding.symmetric(horizontal=6, vertical=3)),
                    ft.Text(f"{r['numero_facture']} ({r['client']})", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(f"Échue le {r['date_echeance']}", size=11, color=ft.colors.RED_800, italic=True),
                ], spacing=10),
                ft.Row([
                    ft.Text(f"{r['montant']:.2f} € HT", weight=ft.FontWeight.BOLD, size=13, color=ft.colors.RED_800),
                    ft.ElevatedButton("Acquitter / Voir", height=30, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=lambda e: page.go("/facturation_print")),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    for ab in ano["abonnements_dus"]:
        items_ui.append(
            ft.Row([
                ft.Row([
                    ft.Container(content=ft.Text("ABONNEMENT DÛ", size=10, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), bgcolor=ft.colors.PURPLE_700, border_radius=4, padding=ft.padding.symmetric(horizontal=6, vertical=3)),
                    ft.Text(f"Abonnement {ab['mois']} — Devis {ab['numero_devis']} ({ab['client']})", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text("Mois échu non facturé", size=11, color=ft.colors.PURPLE_900, italic=True),
                ], spacing=10),
                ft.Row([
                    ft.Text(f"{ab['montant']:.2f} € HT", weight=ft.FontWeight.BOLD, size=13, color=ft.colors.PURPLE_900),
                    ft.ElevatedButton("Émettre Abonnement", height=30, bgcolor=THEME["sage_dark"], color=ft.colors.WHITE, on_click=lambda e: page.go("/factures")),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    for a in ano["acomptes_manquants"]:
        items_ui.append(
            ft.Row([
                ft.Row([
                    ft.Container(content=ft.Text("ACOMPTE NON ÉMIS", size=10, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), bgcolor=ft.colors.ORANGE_800, border_radius=4, padding=ft.padding.symmetric(horizontal=6, vertical=3)),
                    ft.Text(f"Devis {a['numero_devis']} ({a['client']})", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text("Contrat signé, acompte non facturé !", size=11, color=THEME["text_muted"], italic=True),
                ], spacing=10),
                ft.Row([
                    ft.Text(f"{a['montant']:.2f} € HT", weight=ft.FontWeight.BOLD, size=13, color=ft.colors.ORANGE_800),
                    ft.ElevatedButton("Émettre Acompte", height=30, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=lambda e: page.go("/factures")),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    for s in ano["soldes_manquants"]:
        items_ui.append(
            ft.Row([
                ft.Row([
                    ft.Container(content=ft.Text("SOLDE À FACTURER", size=10, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), bgcolor=THEME["sage_dark"], border_radius=4, padding=ft.padding.symmetric(horizontal=6, vertical=3)),
                    ft.Text(f"Devis {s['numero_devis']} ({s['client']})", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text("Acompte payé, solde de livraison disponible", size=11, color=THEME["text_muted"], italic=True),
                ], spacing=10),
                ft.Row([
                    ft.Text(f"{s['montant']:.2f} € HT", weight=ft.FontWeight.BOLD, size=13, color=THEME["sage_dark"]),
                    ft.ElevatedButton("Émettre Solde", height=30, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=lambda e: page.go("/factures")),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    bg_col = "#FFF5F5" if nb_retards > 0 else ("#FFFDF5" if (nb_acomptes + nb_soldes + nb_abos) > 0 else "#F7FAFC")
    bd_col = ft.colors.RED_300 if nb_retards > 0 else (ft.colors.ORANGE_300 if (nb_acomptes + nb_soldes + nb_abos) > 0 else THEME["sage_light"])

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.RADAR_ROUNDED, color=ft.colors.RED_800 if nb_retards > 0 else ft.colors.ORANGE_900),
                ft.Text(f"Radar Facturation & Vigilance Trésorerie ({total_actions} action(s) requise(s))", weight=ft.FontWeight.BOLD, size=14, color=ft.colors.RED_900 if nb_retards > 0 else ft.colors.ORANGE_900),
            ], spacing=8),
            ft.Divider(height=10, color=bd_col),
            ft.Column(items_ui, spacing=6),
        ], spacing=8),
        bgcolor=bg_col,
        border=ft.border.all(1, bd_col),
        border_radius=12,
        padding=16,
    )


# --- 1. TABLEAU DE BORD ---
def view_dashboard(page: ft.Page):
    conn = get_db()
    ent = get_entreprise_info()
    current_year = datetime.date.today().year

    df_devis = pd.read_sql_query("SELECT * FROM devis WHERE archive = 0 ORDER BY id DESC", conn)
    df_fact = pd.read_sql_query("SELECT * FROM factures ORDER BY id DESC", conn)
    df_paiements = pd.read_sql_query("SELECT * FROM paiements ORDER BY date_paiement DESC, id DESC", conn)
    df_depenses = pd.read_sql_query("SELECT * FROM depenses ORDER BY date_depense DESC, id DESC", conn)
    conn.close()

    taux_urssaf = ent["taux_urssaf"]
    taux_ir = ent["taux_ir"]
    taux_charges = taux_urssaf + taux_ir

    if not df_paiements.empty:
        df_p_year = df_paiements[df_paiements["date_paiement"].str.startswith(str(current_year))]
        ca_annuel_encaisse = df_p_year["montant_recu"].sum() if not df_p_year.empty else 0.0
    else:
        ca_annuel_encaisse = 0.0

    total_depenses_an = df_depenses["montant"].sum() if not df_depenses.empty else 0.0
    charges_fiscales_sociales = ca_annuel_encaisse * (taux_charges / 100)
    benefice_net_euros = ca_annuel_encaisse - total_depenses_an - charges_fiscales_sociales
    taux_marge_nette = (benefice_net_euros / ca_annuel_encaisse * 100) if ca_annuel_encaisse > 0 else 0.0

    pct_seuil_micro = min(ca_annuel_encaisse / PLAFOND_MICRO_BNC, 1.0)
    pct_seuil_tva = min(ca_annuel_encaisse / SEUIL_TVA_BASE, 1.0)

    color_jauge_tva = ft.colors.GREEN_700 if pct_seuil_tva < 0.70 else (ft.colors.ORANGE_700 if pct_seuil_tva < 0.90 else ft.colors.RED_700)
    color_jauge_micro = ft.colors.GREEN_700 if pct_seuil_micro < 0.70 else (ft.colors.ORANGE_700 if pct_seuil_micro < 0.90 else ft.colors.RED_700)

    reste_avant_tva = max(SEUIL_TVA_BASE - ca_annuel_encaisse, 0.0)
    reste_avant_plafond = max(PLAFOND_MICRO_BNC - ca_annuel_encaisse, 0.0)

    def kpi_card(label, value_str, sub_info, icon, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Icon(icon, size=26, color=color), bgcolor=THEME["sage_pale"], border_radius=12, padding=12),
                    ft.Column([
                        ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700, color=THEME["text_muted"]),
                        ft.Text(value_str, size=19, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(sub_info, size=11, color=THEME["text_muted"], italic=True),
                    ], spacing=2),
                ],
                spacing=12,
            ),
            bgcolor=THEME["cream_card"],
            border=ft.border.all(1, THEME["sage_light"]),
            border_radius=14,
            padding=16,
            expand=True,
        )

    kpis_row = ft.Row([
        kpi_card("CA Réel Encaissé", f"{ca_annuel_encaisse:.2f} €", f"Facturé : {df_fact['montant_ht'].sum():.2f} €", ft.icons.SAVINGS_OUTLINED, ft.colors.GREEN_700),
        kpi_card("Charges & Dépenses", f"{(total_depenses_an + charges_fiscales_sociales):.2f} €", f"Dont {charges_fiscales_sociales:.2f} € URSSAF/IR", ft.icons.SHOPPING_BAG_OUTLINED, THEME["blush_dark"]),
        kpi_card("Bénéfice Net Réel", f"{benefice_net_euros:.2f} €", f"Marge Nette : {taux_marge_nette:.1f} %", ft.icons.TRENDING_UP, ft.colors.BLUE_800 if benefice_net_euros >= 0 else ft.colors.RED_700),
    ], spacing=16)

    card_jauge_tva = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("⚡ FRANCHISE EN BASE DE TVA (36 800 €)", size=11, weight=ft.FontWeight.BOLD), ft.Text(f"{ca_annuel_encaisse:.2f} € ({pct_seuil_tva * 100:.1f} %)", size=12, weight=ft.FontWeight.BOLD, color=color_jauge_tva)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=pct_seuil_tva, color=color_jauge_tva, bgcolor=THEME["sage_pale"], height=9),
            ft.Text(f"Reste {reste_avant_tva:.2f} € avant TVA obligatoire." if reste_avant_tva > 0 else "⚠️ Seuil TVA dépassé : Facturation TVA requise.", size=11, color=THEME["text_muted"], italic=True),
        ], spacing=6),
        bgcolor=THEME["cream_card"], border=ft.border.all(1, THEME["sage_light"]), border_radius=14, padding=16, expand=True,
    )

    card_jauge_micro = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("🏛️ PLAFOND STATUT MICRO (77 700 €)", size=11, weight=ft.FontWeight.BOLD), ft.Text(f"{ca_annuel_encaisse:.2f} € ({pct_seuil_micro * 100:.1f} %)", size=12, weight=ft.FontWeight.BOLD, color=color_jauge_micro)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=pct_seuil_micro, color=color_jauge_micro, bgcolor=THEME["sage_pale"], height=9),
            ft.Text(f"Reste {reste_avant_plafond:.2f} € avant sortie du régime micro.", size=10, color=THEME["text_muted"], italic=True),
        ], spacing=6),
        bgcolor=THEME["cream_card"], border=ft.border.all(1, THEME["sage_light"]), border_radius=14, padding=16, expand=True,
    )

    quarters_def = [
        ("T1 (Janvier - Mars)", ["-01-", "-02-", "-03-"], "30 Avril"),
        ("T2 (Avril - Juin)", ["-04-", "-05-", "-06-"], "31 Juillet"),
        ("T3 (Juillet - Septembre)", ["-07-", "-08-", "-09-"], "31 Octobre"),
        ("T4 (Octobre - Décembre)", ["-10-", "-11-", "-12-"], "31 Janvier"),
    ]
    trimestres_rows = []
    for label, months, date_limite in quarters_def:
        ca_trim = 0.0
        if not df_paiements.empty:
            for m in months:
                sub = df_paiements[df_paiements["date_paiement"].str.contains(f"{current_year}{m}")]
                if not sub.empty: ca_trim += sub["montant_recu"].sum()
        urssaf_trim = ca_trim * (taux_urssaf / 100)
        ir_trim = ca_trim * (taux_ir / 100)
        trimestres_rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(label, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(f"{ca_trim:.2f} €", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(f"{urssaf_trim:.2f} €", color=THEME["sage_dark"])),
                ft.DataCell(ft.Text(f"{ir_trim:.2f} €", color=THEME["blush_dark"])),
                ft.DataCell(ft.Text(f"{(urssaf_trim + ir_trim):.2f} €", weight=ft.FontWeight.BOLD, color=ft.colors.RED_800)),
                ft.DataCell(ft.Text(f"Avant le {date_limite}", size=11, italic=True)),
            ])
        )

    table_trimestres = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Période Trimestrielle")),
            ft.DataColumn(ft.Text("CA Encaissé")),
            ft.DataColumn(ft.Text(f"URSSAF ({taux_urssaf}%)")),
            ft.DataColumn(ft.Text(f"Impôt IR ({taux_ir}%)")),
            ft.DataColumn(ft.Text("Total Charges dues")),
            ft.DataColumn(ft.Text("Date limite Déclaration")),
        ],
        rows=trimestres_rows,
        heading_row_color=THEME["sage_pale"],
        border=ft.border.all(1, THEME["sage_light"]),
        border_radius=8,
    )

    card_echeancier = create_card(
        ft.Column([
            ft.Row([
                ft.Icon(ft.icons.CALENDAR_MONTH_ROUNDED, color=THEME["sage_dark"]),
                ft.Text(f"🗓️ Échéancier Trimestriel des Cotisations & Impôts — Exercice {current_year}", size=15, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
            ], spacing=8),
            ft.Text(f"Calcul en direct sur les encaissements réels du Livre des Recettes (URSSAF {taux_urssaf}% + Versement Libératoire IR {taux_ir}% = Total {taux_charges:.1f}%)", size=11, color=THEME["text_muted"]),
            table_trimestres,
        ], spacing=10),
        padding=18,
    )

    devis_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(str(r["numero_devis"]), weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(str(r["date_creation"]))),
            ft.DataCell(ft.Text(str(r["client_societe"] or "-"))),
            ft.DataCell(ft.Text(f"{float(r['montant_setup']):.2f} €")),
            ft.DataCell(ft.Text(f"{float(r['montant_abo']):.2f} €/m")),
            ft.DataCell(ft.Container(content=ft.Text(str(r["statut"]), size=11, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]), bgcolor=THEME["sage_pale"], padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=8)),
            ft.DataCell(ft.Text("Signé ✅" if r["contrat_signe"] == 1 else "Non signé ⚠️", color=ft.colors.GREEN_800 if r["contrat_signe"] == 1 else ft.colors.ORANGE_800, weight=ft.FontWeight.BOLD)),
        ])
        for _, r in df_devis.iterrows()
    ]

    table_devis = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("N° Devis")), ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Société")),
            ft.DataColumn(ft.Text("Setup HT")), ft.DataColumn(ft.Text("Abonnement")), ft.DataColumn(ft.Text("Statut")), ft.DataColumn(ft.Text("Contrat 7P")),
        ],
        rows=devis_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
    )

    factures_rows = []
    for _, r in df_fact.iterrows():
        f_num = r["numero_facture"]
        factures_rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(f_num), weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(str(r["numero_devis"]))),
                ft.DataCell(ft.Text(str(r["type_facture"]))),
                ft.DataCell(ft.Text(str(r["date_facture"]))),
                ft.DataCell(ft.Text(f"{float(r['montant_ht']):.2f} €")),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(str(r["statut"]), size=11, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
                        bgcolor=THEME["sage_pale"] if r["statut"] != "Facture Annulée" else THEME["blush_pale"],
                        padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=8
                    )
                ),
                ft.DataCell(
                    ft.IconButton(
                        icon=ft.icons.PRINT_ROUNDED,
                        tooltip=f"Imprimer la facture {f_num}",
                        icon_size=18,
                        on_click=lambda e, fn=f_num: execute_print_facture(fn, page)
                    )
                ),
            ])
        )

    table_factures = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("N° Facture")), ft.DataColumn(ft.Text("N° Devis")), ft.DataColumn(ft.Text("Type")),
            ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Montant HT")), ft.DataColumn(ft.Text("Statut")),
            ft.DataColumn(ft.Text("Imprimer")),
        ],
        rows=factures_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
    )

    operations_tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="📋 Devis Commerciaux Actifs", icon=ft.icons.DESCRIPTION_OUTLINED, content=ft.Container(content=table_devis, padding=16)),
            ft.Tab(text="🧾 Factures Émises & Réimpression", icon=ft.icons.RECEIPT_LONG_OUTLINED, content=ft.Container(content=table_factures, padding=16)),
        ],
    )

    return ft.ListView(
        controls=[
            create_header("🧭", "Tableau de bord ERP", f"Pilotage de la Micro-Entreprise — Exercice {current_year}"),
            build_radar_vigilance(page),
            ft.Container(height=14),
            kpis_row,
            ft.Container(height=14),
            ft.Row([card_jauge_tva, card_jauge_micro], spacing=16),
            ft.Container(height=14),
            card_echeancier,
            ft.Container(height=14),
            create_card(operations_tabs, padding=10),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- MODULE GUIDE & LIVRET D'ACCUEIL ---
def view_livret_accueil(page: ft.Page):
    ent = get_entreprise_info()

    def print_livret_pdf(e):
        html = generate_livret_accueil_html(ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name
        webbrowser.open(f"file://{temp_path}")
        show_toast(page, "Livret d'accueil ouvert pour impression PDF.")

    def guide_section(title, icon_char, content_widgets):
        return ft.ExpansionTile(
            leading=ft.Container(content=ft.Text(icon_char, size=18), bgcolor=THEME["sage_pale"], border_radius=8, padding=6),
            title=ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=THEME["text"]),
            controls=[ft.Container(content=ft.Column(content_widgets, spacing=8), padding=15)],
            initially_expanded=False,
        )

    return ft.ListView(
        controls=[
            create_header("📘", "Manuel & Livret d'Accueil Themis ERP", "Guide complet d'exploitation et règles de gestion de votre micro-entreprise"),
            create_card(
                ft.Row([
                    ft.Column([
                        ft.Text("Documentation Officielle d'Exploitation", size=16, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
                        ft.Text("Ce livret synthétise l'ensemble des modules, automatisations et règles légales intégrées dans votre ERP.", size=12, color=THEME["text_muted"]),
                    ], expand=True),
                    ft.ElevatedButton("🖨️ Imprimer le Livret Complet (PDF)", icon=ft.icons.PRINT_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, height=45, on_click=print_livret_pdf),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=18,
            ),
            ft.Container(height=15),
            create_card(
                ft.Column([
                    guide_section(
                        "1. Philosophie & Piliers Fondateurs", "🏛️",
                        [
                            ft.Text("Themis ERP est conçu pour les micro-entrepreneurs du numérique (automatisations, développement logiciel, intégration d'APIs).", size=12),
                            ft.Text("• Sécurité juridique absolue : Dossier contractuel exhaustif de 7 pages (CGV 14 articles, SLA 9 articles, NDA 6 articles, PV de recette).", size=12),
                            ft.Text("• Verrouillage anti-travail gratuit : Scope-Shield avec avenants flash pour facturer immédiatement les ajouts en cours de mission.", size=12),
                            ft.Text("• Sérénité fiscale : Calcul automatique de vos cotisations URSSAF et surveillance permanente des seuils de TVA.", size=12),
                        ]
                    ),
                    guide_section(
                        "2. Tableau de Bord & Pilotage Financier", "🧭",
                        [
                            ft.Text("• CA Encaissé Réel : Sommes effectivement perçues sur le compte bancaire, distinctes du simple facturé.", size=12),
                            ft.Text("• Double Jauge Légale : Surveillance du seuil de TVA (36 800 €) avec alerte couleur et du plafond micro (77 700 €).", size=12),
                            ft.Text("• Échéancier Trimestriel T1-T4 : Affiche en direct le montant exact à payer à l'URSSAF (21,2 %) et aux Impôts (2,2 %).", size=12),
                            ft.Text("• Marge Nette Réelle : Calculée après déduction de vos dépenses réelles et de vos charges fiscales et sociales.", size=12),
                        ]
                    ),
                    guide_section(
                        "3. Commercial, CRM & Fiches 360°", "👥",
                        [
                            ft.Text("• Portefeuille Client 360° : Synthèse instantanée du CA encaissé (LTV), des abonnements récurrents et des travaux réalisés.", size=12),
                            ft.Text("• Modal Popup Instantanée : Clic sur 'Inspecter 360°' ouvrant immédiatement le dossier sans défilement.", size=12),
                            ft.Text("• Coffre-Fort de Secrets API : Répertoire chiffré des clés API et webhooks avec génération de Décharge de sécurité RGPD.", size=12),
                            ft.Text("• Catalogue 8 Forfaits : Tarification standard des prestations d'automatisation, hébergement et maintenance récurrente.", size=12),
                        ]
                    ),
                    guide_section(
                        "4. Production, Projets & Livrables Techniques", "🚀",
                        [
                            ft.Text("• Conversion Devis en Projet : Dès qu'un devis est validé et signé, il est converti en projet Kanban en 1 clic.", size=12),
                            ft.Text("• Kanban 4 Colonnes : Suivi de vos tâches (À faire, En cours, En test, Terminé) et calcul du taux horaire effectif réalisé (€/h).", size=12),
                            ft.Text("• Scope-Shield (Avenants Flash) : Mini-contrat d'ajustement (+prix, +délai) en 30 secondes pour chaque demande hors-périmètre.", size=12),
                            ft.Text("• Architecture Blueprint : Émission d'une fiche technique A4 schématisant le pipeline de données.", size=12),
                            ft.Text("• Cockpit MCO : Enregistrement mensuel des requêtes et incidents pour éditer le rapport de maintenance qui fidélise vos abonnés.", size=12),
                        ]
                    ),
                    guide_section(
                        "5. Facturation & Verrous Juridiques", "⚖️",
                        [
                            ft.Text("• Règle d'or de Themis : Aucune facture ne peut être émise sans devis validé et contrat formellement signé.", size=12),
                            ft.Text("• Naming Explicite : Chaque facture porte la référence du client et le type pour éliminer tout risque d'erreur comptable.", size=12),
                            ft.Text("• Abonnements Récurrents : Gestion de l'échéance mensuelle automatique synchronisée avec le radar de trésorerie.", size=12),
                            ft.Text("• Synchro Livre des Recettes : Dès qu'une facture est acquittée, elle s'inscrit automatiquement dans votre registre officiel URSSAF.", size=12),
                        ]
                    ),
                ], spacing=10),
                padding=16,
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 2. ESPACE PROJETS, KANBAN, SCOPE-SHIELD & BLUEPRINT ---
def view_kanban(page: ft.Page):
    conn = get_db()
    ent = get_entreprise_info()
    taux_charges = ent["taux_urssaf"] + ent["taux_ir"]

    df_projets = pd.read_sql_query("SELECT * FROM projets ORDER BY id DESC", conn)
    df_devis_signes = pd.read_sql_query("SELECT numero_devis, client_societe, client_nom, client_prenom, montant_setup, sections_json FROM devis WHERE statut = 'Validé & Signé' AND contrat_signe = 1 AND archive = 0", conn)
    conn.close()

    selected_proj_id = int(df_projets.iloc[0]["id"]) if not df_projets.empty else None

    dd_devis_to_convert = ft.Dropdown(
        label="Devis signé & validé à convertir en projet :",
        options=[ft.dropdown.Option(key=r["numero_devis"], text=f"{r['numero_devis']} — {r['client_societe'] or r['client_nom']}") for _, r in df_devis_signes.iterrows()],
        width=420,
    )

    def convert_devis(e):
        if not dd_devis_to_convert.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devis WHERE numero_devis = ?", (dd_devis_to_convert.value,))
        d = cursor.fetchone()
        cursor.execute(
            "INSERT INTO projets (devis_id, client_nom, nom_projet, description, date_debut, date_livraison_prevue, budget_ht) VALUES (?, ?, ?, 'Projet automatisé', ?, ?, ?)",
            (d[1], d[7] or f"{d[6]} {d[5]}", f"Projet {d[1]} - {d[7] or d[5]}", str(datetime.date.today()), str(datetime.date.today() + datetime.timedelta(days=30)), float(d[11])),
        )
        new_p_id = cursor.lastrowid
        try:
            sections = json.loads(d[15]) if d[15] else []
            for s in sections:
                if s.get("title"):
                    cursor.execute("INSERT INTO taches (projet_id, titre, colonne, priorite, heures_estimees, date_creation) VALUES (?, ?, 'À faire', 'Normale', 4.0, ?)", (new_p_id, s.get("title"), str(datetime.date.today())))
        except Exception: pass
        conn.commit()
        conn.close()
        show_toast(page, "Projet créé avec succès !")
        page.go("/kanban")

    subview_container = ft.Container()
    current_tab = "kanban"

    txt_new_task_title = ft.TextField(label="Titre de la tâche à ajouter *", expand=True)
    dd_new_task_prio = ft.Dropdown(label="Priorité", options=[ft.dropdown.Option(p) for p in PRIORITES], value="Normale", width=140)
    txt_new_task_h = ft.TextField(label="Heures", value="2.0", width=90)

    def add_task_quick(e):
        if not selected_proj_id or not txt_new_task_title.value.strip(): return
        try: h_val = float(txt_new_task_h.value.replace(",", "."))
        except ValueError: h_val = 2.0
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO taches (projet_id, titre, description, colonne, priorite, heures_estimees, heures_passees, date_creation) VALUES (?, ?, '', 'À faire', ?, ?, 0.0, ?)",
            (selected_proj_id, txt_new_task_title.value.strip(), dd_new_task_prio.value, h_val, str(datetime.date.today())),
        )
        conn.commit()
        conn.close()
        txt_new_task_title.value = ""
        refresh_current_view()

    def move_t(tid, c, direction):
        idx = COLONNES_KANBAN.index(c) + direction
        conn = get_db()
        conn.cursor().execute("UPDATE taches SET colonne = ? WHERE id = ?", (COLONNES_KANBAN[idx], tid))
        conn.commit()
        conn.close()
        refresh_current_view()

    def delete_tache(tid):
        conn = get_db()
        conn.cursor().execute("DELETE FROM taches WHERE id = ?", (tid,))
        conn.commit()
        conn.close()
        refresh_current_view()

    def build_kanban_view():
        if not selected_proj_id:
            return ft.Text("Aucun projet sélectionné. Utilisez la conversion de devis ci-dessus.", italic=True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM taches WHERE projet_id = ? ORDER BY id DESC", (selected_proj_id,))
        taches = cursor.fetchall()
        conn.close()

        cols_ui = []
        couleurs = {"À faire": "#FEFCBF", "En cours": "#BEE3F8", "En test": "#E9D8FD", "Terminé": "#C6F6D5"}
        for col_name in COLONNES_KANBAN:
            tasks_in_col = [t for t in taches if t[4] == col_name]
            task_cards = []
            for t in tasks_in_col:
                tid, titre, prio, h_val = t[0], t[2], t[5], float(t[7])
                task_cards.append(
                    ft.Container(
                        bgcolor=ft.colors.WHITE, border=ft.border.all(1, "#E2E8F0"), border_radius=10, padding=12,
                        content=ft.Column([
                            ft.Row([ft.Text(prio, size=10, weight=ft.FontWeight.BOLD), ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=15, on_click=lambda e, i=tid: delete_tache(i))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(titre, size=12, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.Text(f"⏱️ {h_val:.1f}h", size=11, color=THEME["text_muted"]),
                                ft.Row([
                                    ft.IconButton(icon=ft.icons.ARROW_BACK, icon_size=16, on_click=lambda e, i=tid, c=col_name: move_t(i, c, -1), disabled=(col_name == "À faire")),
                                    ft.IconButton(icon=ft.icons.ARROW_FORWARD, icon_size=16, on_click=lambda e, i=tid, c=col_name: move_t(i, c, 1), disabled=(col_name == "Terminé")),
                                ], spacing=0),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ], spacing=4),
                    )
                )

            cols_ui.append(
                ft.Container(
                    width=280, bgcolor=THEME["cream_card"], border=ft.border.all(1, THEME["sage_light"]), border_radius=12, padding=12,
                    content=ft.Column([
                        ft.Row([ft.Container(width=10, height=10, bgcolor=couleurs[col_name], border_radius=5), ft.Text(f"{col_name} ({len(tasks_in_col)})", weight=ft.FontWeight.BOLD, size=13)], spacing=8),
                        ft.Divider(height=10, color=THEME["sage_light"]),
                        ft.Column(controls=task_cards, spacing=8),
                    ], spacing=6),
                )
            )

        return ft.Column([
            create_card(
                ft.Row([txt_new_task_title, dd_new_task_prio, txt_new_task_h, ft.ElevatedButton("Ajouter la tâche", icon=ft.icons.ADD, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=add_task_quick)]),
                padding=12,
            ),
            ft.Container(height=15),
            ft.Row(controls=cols_ui, spacing=16, scroll=ft.ScrollMode.AUTO),
        ])

    def build_finance_view():
        if not selected_proj_id: return ft.Text("Sélectionnez un projet.")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projets WHERE id = ?", (selected_proj_id,))
        p = cursor.fetchone()
        cursor.execute("SELECT * FROM taches WHERE projet_id = ?", (selected_proj_id,))
        taches = cursor.fetchall()
        conn.close()

        budget_ht = float(p[8])
        total_heures = sum(float(t[7]) for t in taches)
        taux_horaire_reel = (budget_ht / total_heures) if total_heures > 0 else budget_ht
        charges_euros = budget_ht * (taux_charges / 100)
        marge_nette = budget_ht - charges_euros
        taux_marge = (marge_nette / budget_ht * 100) if budget_ht > 0 else 0.0

        return create_card(
            ft.Column([
                ft.Text(f"📊 Analyse Financière du Projet : {p[3]}", size=16, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
                ft.Divider(height=18),
                ft.Row([
                    ft.Column([ft.Text("BUDGET FACTURÉ HT", size=11, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{budget_ht:.2f} €", size=22, weight=ft.FontWeight.BOLD)]),
                    ft.Column([ft.Text("HEURES INVESTIES", size=11, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{total_heures:.1f} heures", size=22, weight=ft.FontWeight.BOLD)]),
                    ft.Column([ft.Text("RENDEMENT HORAIRE EFFECTIF", size=11, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{taux_horaire_reel:.2f} € / h", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_800)]),
                    ft.Column([ft.Text("MARGE NETTE RÉELLE", size=11, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{marge_nette:.2f} € ({taux_marge:.1f} %)", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)]),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                ft.Divider(height=20),
                ft.Text(f"💡 Déduction faite de {charges_euros:.2f} € provisionnés pour cotisations URSSAF et Impôt sur le Revenu ({taux_charges:.1f} %).", size=12, italic=True),
            ], spacing=12),
            padding=24,
        )

    txt_avn_desc = ft.TextField(label="Description détaillée de l'ajout demandé par le client *", expand=True)
    txt_avn_prix = ft.TextField(label="Impact Prix HT (+ €) *", value="150.00", width=180)
    txt_avn_delai = ft.TextField(label="Impact Délais (+ Jours)", value="3", width=160)

    def trigger_scope_shield(e):
        if not selected_proj_id or not txt_avn_desc.value.strip(): return
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT devis_id FROM projets WHERE id = ?", (selected_proj_id,))
        p_row = cursor.fetchone()
        cursor.execute("SELECT * FROM devis WHERE numero_devis = ?", (p_row["devis_id"],))
        d_row = cursor.fetchone()

        c_tag = sanitize_tag(d_row["client_societe"] or d_row["client_nom"])
        num_avn = get_next_avenant(d_row["numero_devis"]) + f"_{c_tag}"
        p_sup = float(txt_avn_prix.value.replace(",", "."))
        d_sup = int(txt_avn_delai.value)

        cursor.execute(
            "INSERT INTO avenants (numero_avenant, devis_id, date_avenant, description_demande, impact_prix_ht, impact_delai_jours, statut) VALUES (?, ?, ?, ?, ?, ?, 'Validé')",
            (num_avn, d_row["numero_devis"], str(datetime.date.today()), txt_avn_desc.value.strip(), p_sup, d_sup),
        )
        conn.commit()
        cursor.execute("SELECT * FROM avenants WHERE numero_avenant = ?", (num_avn,))
        avn_row = cursor.fetchone()
        conn.close()

        html = generate_avenant_flash_html(avn_row, d_row, ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name
        webbrowser.open(f"file://{temp_path}")
        show_toast(page, f"Avenant Flash {num_avn} généré avec succès !")
        txt_avn_desc.value = ""
        refresh_current_view()

    def build_scope_shield_view():
        return create_card(
            ft.Column([
                ft.Text("🛡️ Scope-Shield — Bloquer le travail gratuit & Générer un Avenant Flash", size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Lorsqu'un client demande une modification hors cahier des charges, quantifiez immédiatement son impact contractuel :", size=12, color=THEME["text_muted"]),
                ft.Row([txt_avn_desc, txt_avn_prix, txt_avn_delai]),
                ft.ElevatedButton("📄 Générer l'Avenant A4 Officiel (PDF)", icon=ft.icons.DESCRIPTION, bgcolor=THEME["blush_dark"], color=ft.colors.WHITE, height=45, on_click=trigger_scope_shield),
            ], spacing=14),
            padding=24,
        )

    txt_bp_nom = ft.TextField(label="Nom du Blueprint / Pipeline *", value="Pipeline d'Automatisation Principal", expand=True)
    txt_bp_trigger = ft.TextField(label="Déclencheur (Trigger) *", value="Webhook Stripe (payment_intent.succeeded)", expand=True)
    txt_bp_etapes = ft.TextField(label="Étapes séquentielles (séparées par une virgule)", value="1. Parsing JSON & Contrôle doublons, 2. Création client Airtable, 3. Génération Facture PDF, 4. Envoi Email Brevo", multiline=True, min_lines=2)
    txt_bp_mapping = ft.TextField(label="Règles de sécurité & dictionnaire de données", value="Chiffrement TLS 1.3, idempotency-key 24h, conformité RGPD.", multiline=True, min_lines=2)

    def print_blueprint(e):
        if not selected_proj_id: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT nom_projet, client_nom FROM projets WHERE id = ?", (selected_proj_id,))
        p = cursor.fetchone()
        conn.close()

        etapes_list = [s.strip() for s in txt_bp_etapes.value.split(",") if s.strip()]
        bp_row = {
            "id": selected_proj_id, "nom_flux": txt_bp_nom.value.strip(),
            "declencheur": txt_bp_trigger.value.strip(), "etapes_json": json.dumps(etapes_list),
            "donnees_mappees": txt_bp_mapping.value.strip(),
        }
        html = generate_blueprint_html(bp_row, p[1], ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name
        webbrowser.open(f"file://{temp_path}")
        show_toast(page, "Blueprint technique généré pour impression.")

    def build_blueprint_view():
        return create_card(
            ft.Column([
                ft.Text("🗺️ Architecture Blueprint — Rendre le flux visible et prestigieux", size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Éditez la fiche technique d'ingénierie à remettre au client avec le Procès-Verbal de Recette :", size=12, color=THEME["text_muted"]),
                ft.Row([txt_bp_nom, txt_bp_trigger]),
                txt_bp_etapes,
                txt_bp_mapping,
                ft.ElevatedButton("🖨️ Éditer le Blueprint Technique A4", icon=ft.icons.PRINT, bgcolor=THEME["sage"], color=ft.colors.WHITE, height=45, on_click=print_blueprint),
            ], spacing=14),
            padding=24,
        )

    def refresh_current_view():
        if current_tab == "kanban": subview_container.content = build_kanban_view()
        elif current_tab == "finance": subview_container.content = build_finance_view()
        elif current_tab == "scope": subview_container.content = build_scope_shield_view()
        elif current_tab == "blueprint": subview_container.content = build_blueprint_view()
        page.update()

    def set_active_tab(tab_name):
        nonlocal current_tab
        current_tab = tab_name
        btn_tab_k.bgcolor = THEME["sage"] if tab_name == "kanban" else ft.colors.TRANSPARENT
        btn_tab_k.color = ft.colors.WHITE if tab_name == "kanban" else THEME["text"]
        btn_tab_f.bgcolor = THEME["sage"] if tab_name == "finance" else ft.colors.TRANSPARENT
        btn_tab_f.color = ft.colors.WHITE if tab_name == "finance" else THEME["text"]
        btn_tab_s.bgcolor = THEME["sage"] if tab_name == "scope" else ft.colors.TRANSPARENT
        btn_tab_s.color = ft.colors.WHITE if tab_name == "scope" else THEME["text"]
        btn_tab_b.bgcolor = THEME["sage"] if tab_name == "blueprint" else ft.colors.TRANSPARENT
        btn_tab_b.color = ft.colors.WHITE if tab_name == "blueprint" else THEME["text"]
        refresh_current_view()

    btn_tab_k = ft.ElevatedButton("📌 Tableau Kanban", icon=ft.icons.VIEW_KANBAN_ROUNDED, on_click=lambda e: set_active_tab("kanban"))
    btn_tab_f = ft.ElevatedButton("💶 Rentabilité & Heures", icon=ft.icons.QUERY_STATS, on_click=lambda e: set_active_tab("finance"))
    btn_tab_s = ft.ElevatedButton("🛡️ Scope-Shield (Avenants)", icon=ft.icons.SHIELD_ROUNDED, on_click=lambda e: set_active_tab("scope"))
    btn_tab_b = ft.ElevatedButton("🗺️ Blueprint Technique", icon=ft.icons.MAP_ROUNDED, on_click=lambda e: set_active_tab("blueprint"))

    dd_select_proj = ft.Dropdown(
        label="Sélectionner le projet actif :",
        options=[ft.dropdown.Option(key=str(r["id"]), text=f"{r['nom_projet']} ({float(r['budget_ht']):.2f} € HT)") for _, r in df_projets.iterrows()],
        value=str(selected_proj_id) if selected_proj_id else None,
        width=380,
    )

    def on_proj_select(e):
        nonlocal selected_proj_id
        if dd_select_proj.value:
            selected_proj_id = int(dd_select_proj.value)
            refresh_current_view()

    dd_select_proj.on_change = on_proj_select
    set_active_tab("kanban")

    return ft.ListView(
        controls=[
            create_header("🚀", "Projets, Kanban & Livrables Techniques", "Espace de production épuré et modulaire"),
            create_card(
                ft.Row([
                    dd_select_proj,
                    ft.Row([dd_devis_to_convert, ft.ElevatedButton("Convertir Devis", icon=ft.icons.ROCKET_LAUNCH, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=convert_devis)]),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=16,
            ),
            ft.Container(height=14),
            ft.Row([btn_tab_k, btn_tab_f, btn_tab_s, btn_tab_b], spacing=12),
            ft.Container(height=16),
            subview_container,
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 3. MODULE CRM & FICHE CLIENT 360° AVEC MODAL POPUP ---
def view_crm_clients(page: ft.Page):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients ORDER BY id DESC")
    clients_rows = cursor.fetchall()
    ent = get_entreprise_info()
    conn.close()

    txt_societe = ft.TextField(label="Nom de la Société", expand=True)
    txt_nom = ft.TextField(label="Nom du contact *", width=250)
    txt_prenom = ft.TextField(label="Prénom *", width=250)
    txt_adresse = ft.TextField(label="Adresse complète *", multiline=True, min_lines=2)
    txt_tel = ft.TextField(label="Téléphone", width=250)
    txt_email = ft.TextField(label="Email", width=250)

    txt_recherche = ft.TextField(label="🔍 Rechercher dans le portefeuille (Nom, Société, Email)", expand=True, border_color=THEME["sage_light"])
    portefeuille_table_container = ft.Container()

    def get_client_stats(cid, c_nom_complet, c_soc):
        conn = get_db()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT SUM(montant_abo) FROM devis WHERE (client_id = ? OR client_societe = ? OR client_nom = ?) AND statut = 'Validé & Signé' AND archive = 0", (cid, c_soc, c_nom_complet))
        abo_sum = c.fetchone()[0] or 0.0

        c.execute("""
            SELECT SUM(p.montant_recu) 
            FROM paiements p
            JOIN factures f ON p.numero_facture = f.numero_facture
            JOIN devis d ON f.numero_devis = d.numero_devis
            WHERE d.client_id = ? OR d.client_societe = ? OR p.client_nom LIKE ?
        """, (cid, c_soc, f"%{c_nom_complet}%"))
        ltv_sum = c.fetchone()[0] or 0.0

        c.execute("SELECT COUNT(*) FROM projets WHERE client_nom LIKE ? OR client_nom LIKE ?", (f"%{c_soc}%", f"%{c_nom_complet}%"))
        nb_proj = c.fetchone()[0]

        c.execute("""
            SELECT COUNT(*) 
            FROM factures f
            JOIN devis d ON f.numero_devis = d.numero_devis
            WHERE (d.client_id = ? OR d.client_societe = ?) AND f.statut = 'Facture Émise' AND f.date_echeance < ?
        """, (cid, c_soc, str(datetime.date.today())))
        nb_retards = c.fetchone()[0]

        conn.close()
        return {
            "abo_mensuel": float(abo_sum),
            "ltv": float(ltv_sum),
            "nb_projets": nb_proj,
            "has_retards": nb_retards > 0
        }

    def open_client_360_modal(cid):
        """Ouvre directement la fiche 360° du client dans une fenêtre modale centrée."""
        conn = get_db()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM clients WHERE id = ?", (cid,))
        client = c.fetchone()
        if not client:
            conn.close()
            return

        c.execute("SELECT * FROM devis WHERE client_id = ? OR client_societe = ? ORDER BY id DESC", (cid, client["societe"]))
        devis_list = c.fetchall()

        c.execute("SELECT * FROM projets WHERE client_nom LIKE ? OR client_nom LIKE ? ORDER BY id DESC", (f"%{client['societe']}%", f"%{client['nom']}%"))
        projets_list = c.fetchall()

        c.execute("""
            SELECT f.* 
            FROM factures f
            JOIN devis d ON f.numero_devis = d.numero_devis
            WHERE d.client_id = ? OR d.client_societe = ?
            ORDER BY f.id DESC
        """, (cid, client["societe"]))
        factures_list = c.fetchall()

        c.execute("SELECT * FROM mco_suivi WHERE client_id = ? ORDER BY mois DESC", (cid,))
        mco_list = c.fetchall()

        c.execute("SELECT * FROM secrets_vault WHERE client_id = ? ORDER BY id DESC", (cid,))
        secrets_list = c.fetchall()

        conn.close()

        # 1. Onglet Travaux
        travaux_cards = []
        for p in projets_list:
            travaux_cards.append(
                ft.Container(
                    bgcolor=THEME["sage_pale"], border_radius=8, padding=10,
                    content=ft.Row([
                        ft.Column([
                            ft.Text(p["nom_projet"], weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"Date début : {p['date_debut']} | Livraison : {p['date_livraison_prevue'] or '-'}", size=11, color=THEME["text_muted"]),
                        ]),
                        ft.Text(f"{float(p['budget_ht']):.2f} € HT", weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )

        tab_travaux = ft.ListView([
            ft.Text(f"Projets en production & Devis ({len(projets_list)} projet(s), {len(devis_list)} devis)", weight=ft.FontWeight.BOLD, size=13),
            ft.Column(travaux_cards if travaux_cards else [ft.Text("Aucun projet enregistré.", italic=True)]),
        ], spacing=8, expand=True)

        # 2. Onglet Abonnements
        mco_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(m["mois"], weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(f"{m['flux_surveilles']} flux")),
                ft.DataCell(ft.Text(f"{m['operations_traitees']} ops")),
                ft.DataCell(ft.Text(m["statut_sante"], color=ft.colors.GREEN_800)),
            ])
            for m in mco_list
        ]
        tab_abos = ft.ListView([
            ft.Text("Supervision & Maintien Opérationnel (MCO)", weight=ft.FontWeight.BOLD, size=13),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Mois")), ft.DataColumn(ft.Text("Passerelles")), ft.DataColumn(ft.Text("Opérations")), ft.DataColumn(ft.Text("Santé"))],
                rows=mco_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
            ) if mco_rows else ft.Text("Aucun historique de maintenance saisi.", italic=True),
        ], spacing=8, expand=True)

        # 3. Onglet Facturation
        tot_facture = sum(float(f["montant_ht"]) for f in factures_list)
        tot_regle = sum(float(f["montant_ht"]) for f in factures_list if f["statut"] in ["Facture Acquittée", "Payée"])
        tab_factures = ft.ListView([
            ft.Row([
                ft.Text(f"Facturé : {tot_facture:.2f} € HT", weight=ft.FontWeight.BOLD),
                ft.Text(f"Encaissé : {tot_regle:.2f} € HT", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800),
                ft.Text(f"Reste Dû : {(tot_facture - tot_regle):.2f} € HT", weight=ft.FontWeight.BOLD, color=ft.colors.RED_800 if (tot_facture - tot_regle) > 0 else THEME["sage_dark"]),
            ], spacing=16),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Facture")), ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Montant HT")), ft.DataColumn(ft.Text("Statut"))],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f["numero_facture"], weight=ft.FontWeight.BOLD, size=11)),
                        ft.DataCell(ft.Text(f["date_facture"], size=11)),
                        ft.DataCell(ft.Text(f"{float(f['montant_ht']):.2f} €", size=11)),
                        ft.DataCell(ft.Text(f["statut"], size=11, color=ft.colors.GREEN_800 if f["statut"] in ["Facture Acquittée", "Payée"] else ft.colors.ORANGE_800)),
                    ]) for f in factures_list
                ],
                heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
            ) if factures_list else ft.Text("Aucune facture émise.", italic=True),
        ], spacing=8, expand=True)

        # 4. Onglet Secrets & Décharge RGPD
        tab_secrets = ft.ListView([
            ft.Row([
                ft.Text("Accès techniques & Habilitations", weight=ft.FontWeight.BOLD, size=13),
                ft.ElevatedButton("📄 Imprimer Décharge RGPD (PDF)", icon=ft.icons.SECURITY_ROUNDED, bgcolor=THEME["blush_dark"], color=ft.colors.WHITE, on_click=lambda e: print_decharge_rgpd(cid)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Plateforme")), ft.DataColumn(ft.Text("Type")), ft.DataColumn(ft.Text("Statut"))],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(s["service_nom"], weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(s["type_identifiant"])),
                        ft.DataCell(ft.Text(s["statut"], color=ft.colors.GREEN_800)),
                    ]) for s in secrets_list
                ],
                heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
            ) if secrets_list else ft.Text("Aucun secret technique enregistré.", italic=True),
        ], spacing=8, expand=True)

        detail_tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="🛠️ Travaux", content=ft.Container(tab_travaux, padding=10)),
                ft.Tab(text="🩺 Abonnements", content=ft.Container(tab_abos, padding=10)),
                ft.Tab(text="🧾 Facturation", content=ft.Container(tab_factures, padding=10)),
                ft.Tab(text="🔐 Sécurité", content=ft.Container(tab_secrets, padding=10)),
            ],
            expand=True,
        )

        nom_display = client["societe"] or f"{client['prenom']} {client['nom']}"

        dlg_360 = ft.AlertDialog(
            title=ft.Row([
                ft.Container(content=ft.Text("360°", size=11, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), bgcolor=THEME["sage_dark"], border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=4)),
                ft.Text(f"Fiche Client : {nom_display}", size=18, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
            ], spacing=10),
            content=ft.Container(
                content=detail_tabs,
                width=820,
                height=480,
            ),
            actions=[
                ft.TextButton("Fermer", on_click=lambda e: close_dialog(dlg_360)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def close_dialog(d):
            if hasattr(page, "close"):
                page.close(d)
            else:
                d.open = False
                page.update()

        if hasattr(page, "open"):
            page.open(dlg_360)
        else:
            page.dialog = dlg_360
            dlg_360.open = True
            page.update()

    def print_decharge_rgpd(cid):
        conn = get_db()
        conn.row_factory = sqlite3.Row
        c = conn.cursor().execute("SELECT * FROM clients WHERE id = ?", (cid,)).fetchone()
        s_list = conn.cursor().execute("SELECT * FROM secrets_vault WHERE client_id = ?", (cid,)).fetchall()
        conn.close()

        html = generate_revocation_secrets_html(c, s_list, ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name

        webbrowser.open(f"file://{temp_path}")
        show_toast(page, "Protocole de restitution généré.")

    def refresh_portefeuille(filtre=""):
        conn = get_db()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM clients ORDER BY id DESC")
        all_c = c.fetchall()
        conn.close()

        if filtre.strip():
            f_low = filtre.strip().lower()
            filtered = [r for r in all_c if f_low in (r["societe"] or "").lower() or f_low in (r["nom"] or "").lower() or f_low in (r["email"] or "").lower()]
        else:
            filtered = all_c

        rows = []
        for r in filtered:
            cid = r["id"]
            c_nom = f"{r['prenom']} {r['nom']}"
            c_soc = r["societe"] or ""
            stats = get_client_stats(cid, c_nom, c_soc)

            abo_badge = ft.Container(
                content=ft.Text(f"{stats['abo_mensuel']:.2f} €/m" if stats['abo_mensuel'] > 0 else "Aucun", size=11, weight=ft.FontWeight.BOLD, color=ft.colors.PURPLE_900 if stats['abo_mensuel'] > 0 else THEME["text_muted"]),
                bgcolor="#FAF5FF" if stats['abo_mensuel'] > 0 else THEME["sage_pale"],
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6,
            )

            status_badge = ft.Container(
                content=ft.Text("À jour ✅" if not stats["has_retards"] else "Impayé ⚠️", size=11, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800 if not stats["has_retards"] else ft.colors.RED_800),
                bgcolor=ft.colors.GREEN_50 if not stats["has_retards"] else ft.colors.RED_50,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6,
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(c_soc or "Particulier", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(c_nom)),
                        ft.DataCell(abo_badge),
                        ft.DataCell(ft.Text(f"{stats['ltv']:.2f} €", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)),
                        ft.DataCell(ft.Text(f"{stats['nb_projets']} projet(s)")),
                        ft.DataCell(status_badge),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "Inspecter 360°",
                                icon=ft.icons.INFO_OUTLINED,
                                height=32,
                                bgcolor=THEME["sage"],
                                color=ft.colors.WHITE,
                                on_click=lambda e, i=cid: open_client_360_modal(i),
                            )
                        ),
                    ]
                )
            )

        portefeuille_table_container.content = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Société")),
                ft.DataColumn(ft.Text("Contact Principal")),
                ft.DataColumn(ft.Text("Abonnement Actif")),
                ft.DataColumn(ft.Text("Total Encaissé (LTV)")),
                ft.DataColumn(ft.Text("Projets")),
                ft.DataColumn(ft.Text("Comptabilité")),
                ft.DataColumn(ft.Text("Fiche 360° (Popup)")),
            ],
            rows=rows,
            heading_row_color=THEME["sage_pale"],
            border=ft.border.all(1, THEME["sage_light"]),
            border_radius=8,
        )
        page.update()

    txt_recherche.on_change = lambda e: refresh_portefeuille(txt_recherche.value)

    def save_new_client(e):
        if not txt_nom.value.strip() or not txt_adresse.value.strip(): return
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO clients (societe, nom, prenom, adresse, telephone, email, siret, notes, date_creation) VALUES (?, ?, ?, ?, ?, ?, '', '', ?)",
            (txt_societe.value.strip(), txt_nom.value.strip(), txt_prenom.value.strip(), txt_adresse.value.strip(), txt_tel.value.strip(), txt_email.value.strip(), str(datetime.date.today())),
        )
        conn.commit()
        conn.close()
        show_toast(page, "Nouveau client enregistré !")
        page.go("/crm")

    refresh_portefeuille()

    return ft.ListView(
        controls=[
            create_header("👥", "Portefeuille Clients & Fiches 360°", "Vue unifiée des travaux réalisés, abonnements actifs et santé comptable"),
            create_card(
                ft.Column([
                    ft.Row([
                        txt_recherche,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    portefeuille_table_container,
                ], spacing=14),
                padding=16,
            ),
            ft.Container(height=16),
            ft.ExpansionTile(
                leading=ft.Icon(ft.icons.PERSON_ADD_ALT_1_ROUNDED, color=THEME["sage_dark"]),
                title=ft.Text("➕ Ajouter un nouveau client au portefeuille", size=14, weight=ft.FontWeight.BOLD),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Row([txt_societe, txt_nom, txt_prenom]),
                            txt_adresse,
                            ft.Row([txt_tel, txt_email]),
                            ft.ElevatedButton("Enregistrer le client", icon=ft.icons.SAVE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=save_new_client),
                        ], spacing=12),
                        padding=16,
                    )
                ],
                initially_expanded=False,
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 4. MODULE CATALOGUE ---
def view_catalogue(page: ft.Page):
    conn = get_db()
    df_cat = pd.read_sql_query("SELECT * FROM catalogue ORDER BY id DESC", conn)
    conn.close()

    cat_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(r["reference"], weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(r["designation"])),
            ft.DataCell(ft.Container(content=ft.Text(r["type_service"], size=11, color=THEME["sage_dark"], weight=ft.FontWeight.BOLD), bgcolor=THEME["sage_pale"], padding=4, border_radius=6)),
            ft.DataCell(ft.Text(f"{float(r['prix_unitaire_ht']):.2f} €")),
        ])
        for _, r in df_cat.iterrows()
    ]

    table_cat = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Réf.")), ft.DataColumn(ft.Text("Désignation")), ft.DataColumn(ft.Text("Type")), ft.DataColumn(ft.Text("Prix Unit. HT"))],
        rows=cat_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
    )

    return ft.ListView(
        controls=[
            create_header("📦", "Catalogue Prestations & Tarifs", "Répertoire officiel des 8 forfaits standards Themis"),
            create_card(table_cat, padding=16),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 5. CRÉER & MODIFIER DEVIS ---
def view_devis_form(page: ft.Page):
    conn = get_db()
    clients_df = pd.read_sql_query("SELECT id, societe, nom, prenom, adresse, telephone, email FROM clients ORDER BY societe, nom", conn)
    catalogue_df = pd.read_sql_query("SELECT id, reference, designation, prix_unitaire_ht, type_service FROM catalogue ORDER BY id DESC", conn)
    devis_existants = pd.read_sql_query("SELECT numero_devis, client_societe, client_nom FROM devis WHERE archive = 0 ORDER BY id DESC", conn)
    conn.close()

    is_editing = False
    current_devis_num = get_next_devis()
    selected_client_id = None

    txt_num = ft.TextField(label="N° Devis", value=current_devis_num, read_only=True, bgcolor=THEME["sage_pale"], width=220)
    txt_date = ft.TextField(label="Date (AAAA-MM-JJ)", value=str(datetime.date.today()), width=200)

    txt_societe = ft.TextField(label="Société", expand=True)
    txt_nom = ft.TextField(label="Nom contact", width=220)
    txt_prenom = ft.TextField(label="Prénom", width=220)
    txt_adresse = ft.TextField(label="Adresse", multiline=True, min_lines=2)
    txt_tel = ft.TextField(label="Tél", width=220)
    txt_email = ft.TextField(label="Email", width=220)

    client_options = [ft.dropdown.Option(key=str(r["id"]), text=f"{r['societe'] or r['nom']} ({r['email']})") for _, r in clients_df.iterrows()]
    dd_client_crm = ft.Dropdown(label="⚡ Sélectionner Client CRM :", options=client_options, width=420)

    def on_c_pick(e):
        nonlocal selected_client_id
        if not dd_client_crm.value: return
        selected_client_id = int(dd_client_crm.value)
        c = clients_df[clients_df["id"] == selected_client_id].iloc[0]
        txt_societe.value, txt_nom.value, txt_prenom.value, txt_adresse.value, txt_tel.value, txt_email.value = c["societe"] or "", c["nom"] or "", c["prenom"] or "", c["adresse"] or "", c["telephone"] or "", c["email"] or ""
        page.update()

    dd_client_crm.on_change = on_c_pick

    devis_lignes = [{"designation": "Forfait Automatisation Métier — Flux Multi-étapes & Routage Conditionnel", "qte": 1, "prix_setup": 490.0, "prix_abo": 0.0}]
    lignes_container = ft.Column(spacing=10)
    lbl_tot_setup = ft.Text("0.00 €", size=18, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"])
    lbl_tot_abo = ft.Text("0.00 € / mois", size=18, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"])
    slider_acompte = ft.Slider(min=0, max=50, divisions=10, value=30, label="{value}%")

    txt_roi_heures = ft.TextField(label="Heures économisées / semaine pour le client", value="4.0", width=250)
    txt_roi_taux = ft.TextField(label="Coût horaire moyen client (€/h)", value="25.0", width=220)
    lbl_roi_summary = ft.Text("Gain annuel estimé : 5 200,00 € HT / an  |  Amorti en 4.9 semaines", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)

    def compute_totals():
        tot_s, tot_a = 0.0, 0.0
        for l in devis_lignes:
            try:
                tot_s += float(l.get("qte", 1)) * float(l.get("prix_setup", 0.0))
                tot_a += float(l.get("qte", 1)) * float(l.get("prix_abo", 0.0))
            except Exception: pass
        return tot_s, tot_a

    def update_financials():
        tot_s, tot_a = compute_totals()
        lbl_tot_setup.value = f"{tot_s:.2f} € HT"
        lbl_tot_abo.value = f"{tot_a:.2f} € HT / mois"
        try:
            h = float(txt_roi_heures.value.replace(",", "."))
            tx = float(txt_roi_taux.value.replace(",", "."))
            gain = h * 52 * tx
            amort = (tot_s / (h * tx)) if (h * tx) > 0 else 0
            lbl_roi_summary.value = f"Gain annuel client : {gain:,.2f} € HT / an  |  Amorti en {amort:.1f} semaines"
        except Exception: pass
        page.update()

    txt_roi_heures.on_change = lambda e: update_financials()
    txt_roi_taux.on_change = lambda e: update_financials()

    def refresh_lignes():
        lignes_container.controls.clear()
        for idx, lig in enumerate(devis_lignes):
            t_desig = ft.TextField(label="Désignation", value=lig["designation"], expand=True)
            t_qte = ft.TextField(label="Qté", value=str(lig["qte"]), width=60)
            t_setup = ft.TextField(label="Setup HT", value=f"{float(lig['prix_setup']):.2f}", width=120)
            t_abo = ft.TextField(label="Abo Mensuel", value=f"{float(lig['prix_abo']):.2f}", width=120)

            def b_d(e, i=idx): devis_lignes[i]["designation"] = e.control.value
            def b_q(e, i=idx):
                try: devis_lignes[i]["qte"] = int(e.control.value)
                except ValueError: devis_lignes[i]["qte"] = 1
                update_financials()
            def b_s(e, i=idx):
                try: devis_lignes[i]["prix_setup"] = float(e.control.value.replace(",", "."))
                except ValueError: devis_lignes[i]["prix_setup"] = 0.0
                update_financials()
            def b_a(e, i=idx):
                try: devis_lignes[i]["prix_abo"] = float(e.control.value.replace(",", "."))
                except ValueError: devis_lignes[i]["prix_abo"] = 0.0
                update_financials()
            def rem(e, i=idx):
                if len(devis_lignes) > 1:
                    devis_lignes.pop(i)
                    refresh_lignes()

            t_desig.on_change = b_d
            t_qte.on_change = b_q
            t_setup.on_change = b_s
            t_abo.on_change = b_a

            lignes_container.controls.append(
                ft.Container(
                    bgcolor=THEME["sage_pale"], border_radius=8, padding=6,
                    content=ft.Row([t_desig, t_qte, t_setup, t_abo, ft.IconButton(icon=ft.icons.DELETE_OUTLINE, on_click=rem)]),
                )
            )
        update_financials()

    cat_dd = ft.Dropdown(
        label="Insérer une prestation du catalogue :",
        options=[ft.dropdown.Option(key=str(r["id"]), text=f"{r['reference']} — {r['designation']} ({r['prix_unitaire_ht']:.2f} € HT)") for _, r in catalogue_df.iterrows()],
        expand=True,
    )

    def add_from_cat(e):
        if not cat_dd.value: return
        item = catalogue_df[catalogue_df["id"] == int(cat_dd.value)].iloc[0]
        p = float(item["prix_unitaire_ht"])
        is_abo = ("Abonnement" in item["type_service"])
        devis_lignes.append({"designation": item["designation"], "qte": 1, "prix_setup": 0.0 if is_abo else p, "prix_abo": p if is_abo else 0.0})
        refresh_lignes()

    refresh_lignes()

    def load_devis(e):
        nonlocal is_editing, selected_client_id
        if not selector_edit.value: return
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devis WHERE numero_devis = ?", (selector_edit.value,))
        row = cursor.fetchone()
        conn.close()
        if row:
            is_editing = True
            txt_num.value = row["numero_devis"]
            selected_client_id = row["client_id"]
            txt_date.value = row["date_creation"]
            txt_nom.value = row["client_nom"] or ""
            txt_prenom.value = row["client_prenom"] or ""
            txt_societe.value = row["client_societe"] or ""
            txt_adresse.value = row["client_adresse"] or ""
            txt_tel.value = row["client_telephone"] or ""
            txt_email.value = row["client_email"] or ""
            slider_acompte.value = row["pourcentage_acompte"] or 30

            try:
                devis_lignes.clear()
                devis_lignes.extend(json.loads(row["lignes_json"]))
            except Exception:
                devis_lignes.clear()
                devis_lignes.append({"designation": "Forfait Setup & Création", "qte": 1, "prix_setup": float(row["montant_setup"]), "prix_abo": float(row["montant_abo"])})

            refresh_lignes()
            page.update()

    selector_edit = ft.Dropdown(
        label="Charger un devis existant pour correction :",
        options=[ft.dropdown.Option(key=row["numero_devis"], text=f"{row['numero_devis']} ({row['client_societe'] or row['client_nom'] or 'Particulier'})") for _, row in devis_existants.iterrows()],
        on_change=load_devis,
        width=450,
    )

    def save_devis(e):
        tot_s, tot_a = compute_totals()
        if tot_s <= 0 and tot_a <= 0: return
        nom_c = txt_nom.value.strip() or txt_societe.value.strip() or "Client"
        adresse_c = txt_adresse.value.strip() or "Non renseignée"

        conn = get_db()
        cursor = conn.cursor()
        if is_editing:
            cursor.execute(
                """
                UPDATE devis SET
                    date_creation=?, date_validite=?, client_id=?, client_nom=?, client_prenom=?,
                    client_societe=?, client_adresse=?, client_telephone=?, client_email=?,
                    montant_setup=?, montant_abo=?, pourcentage_acompte=?, lignes_json=?,
                    roi_heures_semaine=?, roi_cout_horaire=?
                WHERE numero_devis=?
                """,
                (
                    txt_date.value, str(datetime.date.today() + datetime.timedelta(days=30)), selected_client_id,
                    nom_c, txt_prenom.value.strip(), txt_societe.value.strip(), adresse_c, txt_tel.value.strip(), txt_email.value.strip(),
                    tot_s, tot_a, int(slider_acompte.value), json.dumps(devis_lignes), float(txt_roi_heures.value.replace(",", ".")), float(txt_roi_taux.value.replace(",", ".")),
                    txt_num.value
                ),
            )
            show_toast(page, f"Devis {txt_num.value} mis à jour avec succès !")
        else:
            cursor.execute(
                """
                INSERT INTO devis (
                    numero_devis, client_id, date_creation, date_validite, client_nom, client_prenom,
                    client_societe, client_adresse, client_telephone, client_email,
                    montant_setup, montant_abo, pourcentage_acompte, statut, sections_json, lignes_json,
                    roi_heures_semaine, roi_cout_horaire, contrat_signe
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Brouillon', '[]', ?, ?, ?, 0)
                """,
                (
                    txt_num.value, selected_client_id, txt_date.value, str(datetime.date.today() + datetime.timedelta(days=30)),
                    nom_c, txt_prenom.value.strip(), txt_societe.value.strip(), adresse_c, txt_tel.value.strip(), txt_email.value.strip(),
                    tot_s, tot_a, int(slider_acompte.value), json.dumps(devis_lignes), float(txt_roi_heures.value.replace(",", ".")), float(txt_roi_taux.value.replace(",", ".")),
                ),
            )
            show_toast(page, f"Devis {txt_num.value} créé avec succès !")

        conn.commit()
        conn.close()
        page.go("/dashboard")

    return ft.ListView(
        controls=[
            create_header("✒️", "Devis & Commandes", "Création, modification et calcul de rentabilité ROI"),
            create_card(selector_edit),
            ft.Container(height=10),
            create_card(
                ft.Column([
                    ft.Text("1. Client & Coordonnées", weight=ft.FontWeight.BOLD, size=15),
                    dd_client_crm,
                    ft.Row([txt_societe, txt_nom, txt_prenom]),
                    txt_adresse,
                    ft.Divider(height=20),
                    ft.Text("2. Prestations & Abonnements Cumulés", weight=ft.FontWeight.BOLD, size=15),
                    ft.Row([cat_dd, ft.ElevatedButton("Ajouter", icon=ft.icons.ADD_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=add_from_cat)]),
                    lignes_container,
                    ft.Divider(height=20),
                    ft.Text("3. Rentabilité & Économies Estimées (ROI Client)", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row([txt_roi_heures, txt_roi_taux]),
                    lbl_roi_summary,
                    ft.Divider(height=20),
                    ft.Row([
                        ft.Column([ft.Text("TOTAL CRÉATION :", size=10, weight=ft.FontWeight.BOLD), lbl_tot_setup]),
                        ft.Container(width=40),
                        ft.Column([ft.Text("TOTAL ABONNEMENT :", size=10, weight=ft.FontWeight.BOLD), lbl_tot_abo]),
                    ]),
                    slider_acompte,
                    ft.ElevatedButton("💾 Enregistrer le Devis", icon=ft.icons.SAVE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, height=50, on_click=save_devis),
                ], spacing=14)
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 6. COCKPIT MCO & SUPERVISION ---
def view_mco_cockpit(page: ft.Page):
    conn = get_db()
    ent = get_entreprise_info()
    df_clients = pd.read_sql_query("SELECT id, societe, nom, prenom FROM clients ORDER BY societe, nom", conn)
    df_mco = pd.read_sql_query(
        """
        SELECT m.*, c.societe, c.nom, c.prenom
        FROM mco_suivi m
        JOIN clients c ON m.client_id = c.id
        ORDER BY m.mois DESC, m.id DESC
        """,
        conn,
    )
    conn.close()

    selected_c_id = int(df_clients.iloc[0]["id"]) if not df_clients.empty else None

    current_month_str = datetime.date.today().strftime("%Y-%m")
    txt_mco_mois = ft.TextField(label="Mois audité (AAAA-MM)", value=current_month_str, width=180)
    txt_mco_flux = ft.TextField(label="Nombre de passerelles surveillées", value="3", width=220)
    txt_mco_ops = ft.TextField(label="Opérations / requêtes traitées", value="4120", width=220)
    txt_mco_incidents = ft.TextField(label="Incidents préventifs neutralisés", value="2", width=220)
    dd_mco_sante = ft.Dropdown(
        label="Disponibilité / Santé",
        options=[ft.dropdown.Option("100% Opérationnel"), ft.dropdown.Option("99.8% Nominal"), ft.dropdown.Option("En maintenance planifiée")],
        value="100% Opérationnel",
        width=250,
    )
    txt_mco_notes = ft.TextField(label="Commentaire d'exploitation pour le client", value="Surveillance continue sans anomalie. Quotas consommés à 41%.", expand=True)

    def add_telemetry(e):
        if not selected_c_id: return
        conn = get_db()
        conn.cursor().execute(
            """
            INSERT INTO mco_suivi (client_id, mois, flux_surveilles, operations_traitees, incidents_resolus, statut_sante, commentaires)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                selected_c_id, txt_mco_mois.value.strip(), int(txt_mco_flux.value),
                int(txt_mco_ops.value), int(txt_mco_incidents.value), dd_mco_sante.value, txt_mco_notes.value.strip(),
            ),
        )
        conn.commit()
        conn.close()
        show_toast(page, "Données d'exploitation mensuelles enregistrées !")
        page.go("/mco")

    def print_rapport_mco(mco_id):
        conn = get_db()
        conn.row_factory = sqlite3.Row
        m = conn.cursor().execute("SELECT * FROM mco_suivi WHERE id = ?", (mco_id,)).fetchone()
        c = conn.cursor().execute("SELECT * FROM clients WHERE id = ?", (m["client_id"],)).fetchone()
        conn.close()

        html = generate_rapport_mco_html(m, c, ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name

        webbrowser.open(f"file://{temp_path}")
        show_toast(page, "Rapport Mensuel de Supervision généré.")

    mco_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(r["mois"], weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(r["societe"] or f"{r['prenom']} {r['nom']}")),
            ft.DataCell(ft.Text(f"{r['flux_surveilles']} flux")),
            ft.DataCell(ft.Text(f"{r['operations_traitees']} ops")),
            ft.DataCell(ft.Text(f"{r['incidents_resolus']} résolus", color=ft.colors.GREEN_800)),
            ft.DataCell(ft.ElevatedButton("🖨️ Rapport PDF", icon=ft.icons.PRINT_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=lambda e, i=r["id"]: print_rapport_mco(i))),
        ])
        for _, r in df_mco.iterrows()
    ]

    table_mco = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Mois")), ft.DataColumn(ft.Text("Client Abonné")), ft.DataColumn(ft.Text("Flux")), ft.DataColumn(ft.Text("Requêtes")), ft.DataColumn(ft.Text("Incidents")), ft.DataColumn(ft.Text("Action"))],
        rows=mco_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
    )

    dd_select_c_mco = ft.Dropdown(
        label="Client sous contrat de maintenance :",
        options=[ft.dropdown.Option(key=str(r["id"]), text=f"{r['societe'] or r['nom']}") for _, r in df_clients.iterrows()],
        value=str(selected_c_id) if selected_c_id else None,
        width=350,
    )

    def on_c_mco_change(e):
        nonlocal selected_c_id
        if dd_select_c_mco.value: selected_c_id = int(dd_select_c_mco.value)

    dd_select_c_mco.on_change = on_c_mco_change

    return ft.ListView(
        controls=[
            create_header("🩺", "Cockpit MCO & Supervision des Abonnés", "Suivi opérationnel et justification tangible de vos abonnements récurrents"),
            create_card(
                ft.Column([
                    ft.Text("Enregistrer les métriques mensuelles pour un client souscrit :", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row([dd_select_c_mco, txt_mco_mois, dd_mco_sante]),
                    ft.Row([txt_mco_flux, txt_mco_ops, txt_mco_incidents]),
                    txt_mco_notes,
                    ft.ElevatedButton("Enregistrer les opérations du mois", icon=ft.icons.SAVE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=add_telemetry),
                ], spacing=14)
            ),
            ft.Container(height=18),
            create_card(table_mco if mco_rows else ft.Text("Aucun historique de maintenance saisi.", italic=True), padding=16),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 7. ARCHIVES ---
def view_archives(page: ft.Page):
    conn = get_db()
    df_actifs = pd.read_sql_query("SELECT numero_devis, client_societe FROM devis WHERE archive = 0 ORDER BY id DESC", conn)
    df_archives = pd.read_sql_query("SELECT * FROM devis WHERE archive = 1 ORDER BY id DESC", conn)
    conn.close()

    warning_box_archive = ft.Container(visible=False)
    dd_archive = ft.Dropdown(label="Devis actif à archiver", options=[ft.dropdown.Option(str(d)) for d in df_actifs["numero_devis"].tolist()], width=300)

    def on_select_archive(e):
        if not dd_archive.value:
            warning_box_archive.visible = False
            page.update()
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM factures WHERE numero_devis = ?", (dd_archive.value,))
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            warning_box_archive.content = ft.Container(content=ft.Text(f"ℹ️ {count} facture(s) liée(s) à ce devis. L'archivage est autorisé.", size=12), bgcolor=THEME["blush_pale"], padding=8, border_radius=6)
            warning_box_archive.visible = True
        else: warning_box_archive.visible = False
        page.update()

    dd_archive.on_change = on_select_archive
    dd_statut_archive = ft.Dropdown(label="Statut appliqué", options=[ft.dropdown.Option(s) for s in ["Refusé", "Annulé", "Sans suite", "Autre"]], value="Refusé", width=200)
    txt_motif = ft.TextField(label="Précisions complémentaires", expand=True)

    def do_archive(e):
        if not dd_archive.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE devis SET archive = 1, statut = ?, motif_archivage = ? WHERE numero_devis = ?", (dd_statut_archive.value or "Annulé", txt_motif.value.strip(), dd_archive.value))
        conn.commit()
        conn.close()
        show_toast(page, f"Devis {dd_archive.value} archivé.")
        page.go("/archives")

    dd_restaure = ft.Dropdown(label="Sélectionner un devis archivé", options=[ft.dropdown.Option(str(d)) for d in df_archives["numero_devis"].tolist()], width=350)
    info_restaure = ft.Text("", italic=True)
    btn_delete = ft.OutlinedButton("Supprimer définitivement", icon=ft.icons.DELETE_FOREVER_ROUNDED, disabled=True)
    chk_confirm = ft.Checkbox(label="Je confirme vouloir supprimer définitivement ce devis (action irréversible)", value=False, disabled=True)

    def on_select_restaure(e):
        if not dd_restaure.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT client_societe, statut, motif_archivage FROM devis WHERE numero_devis = ?", (dd_restaure.value,))
        d_info = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM factures WHERE numero_devis = ?", (dd_restaure.value,))
        nb_fac = cursor.fetchone()[0]
        conn.close()

        info_restaure.value = f"Client : {d_info[0] or 'Particulier'} — Statut : {d_info[1]}"
        if nb_fac > 0:
            chk_confirm.disabled = True
            btn_delete.disabled = True
            show_toast(page, f"Suppression bloquée : {nb_fac} facture(s) rattachée(s).", is_error=True)
        else:
            chk_confirm.disabled = False
            btn_delete.disabled = True
        page.update()

    dd_restaure.on_change = on_select_restaure
    chk_confirm.on_change = lambda e: (setattr(btn_delete, "disabled", not chk_confirm.value), page.update())

    def do_restore(e):
        if not dd_restaure.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE devis SET archive = 0 WHERE numero_devis = ?", (dd_restaure.value,))
        conn.commit()
        conn.close()
        show_toast(page, f"Devis {dd_restaure.value} restauré.")
        page.go("/archives")

    def do_delete(e):
        if not dd_restaure.value or not chk_confirm.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM devis WHERE numero_devis = ?", (dd_restaure.value,))
        conn.commit()
        conn.close()
        show_toast(page, "Devis supprimé définitivement.")
        page.go("/archives")

    btn_delete.on_click = do_delete

    return ft.ListView(
        controls=[
            create_header("🗃️", "Archives & Sécurité", "Mise en sommeil et protection de la comptabilité"),
            create_card(
                ft.Column(controls=[
                    ft.Text("📦 Archiver un devis actif", weight=ft.FontWeight.BOLD, size=15),
                    warning_box_archive,
                    ft.Row([dd_archive, dd_statut_archive]),
                    txt_motif,
                    ft.ElevatedButton("Archiver", icon=ft.icons.ARCHIVE_ROUNDED, bgcolor=THEME["blush_dark"], color=ft.colors.WHITE, on_click=do_archive),
                ], spacing=14)
            ),
            ft.Container(height=20),
            create_card(
                ft.Column(controls=[
                    ft.Text("♻️ Restaurer ou Supprimer définitivement", weight=ft.FontWeight.BOLD, size=15),
                    dd_restaure, info_restaure, chk_confirm,
                    ft.Row(controls=[ft.ElevatedButton("Restaurer ce devis", icon=ft.icons.RESTORE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=do_restore), btn_delete]),
                ], spacing=14)
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 8. ÉTABLIR FACTURE (NOMENCLATURE EXPLICITE & ABONNEMENTS) ---
def view_factures(page: ft.Page):
    conn = get_db()
    df_devis_eligibles = pd.read_sql_query(
        """
        SELECT numero_devis, client_societe, client_nom, client_prenom, montant_setup, montant_abo, pourcentage_acompte, date_signature_contrat
        FROM devis
        WHERE archive = 0 AND statut = 'Validé & Signé' AND contrat_signe = 1
        ORDER BY id DESC
        """,
        conn,
    )
    df_fact = pd.read_sql_query("SELECT numero_facture, montant_ht, numero_devis, date_facture, date_echeance, statut FROM factures WHERE type_facture != 'Avoir' ORDER BY id DESC", conn)
    conn.close()

    form_dynamic_container = ft.Container()
    current_mode = "create"

    has_eligibles = not df_devis_eligibles.empty

    if has_eligibles:
        devis_options = [
            ft.dropdown.Option(
                key=row["numero_devis"],
                text=f"{row['numero_devis']} — {row['client_societe'] or row['client_nom']} (Signé le {row['date_signature_contrat'] or '-'})",
            )
            for _, row in df_devis_eligibles.iterrows()
        ]
        default_devis = df_devis_eligibles.iloc[0]["numero_devis"]
    else:
        devis_options = []
        default_devis = None

    dd_create_devis = ft.Dropdown(
        label="Devis éligible (Validé & Contrat signé) *",
        options=devis_options,
        value=default_devis,
        width=450,
        border_color=THEME["sage_dark"],
    )

    dd_create_type = ft.Dropdown(
        label="Type de facture *",
        options=[
            ft.dropdown.Option("Facture d'Acompte"),
            ft.dropdown.Option("Facture de Solde"),
            ft.dropdown.Option("Facture d'Abonnement Mensuel"),
        ],
        value="Facture d'Acompte",
        width=270,
    )

    txt_abo_mois = ft.TextField(
        label="Mois concerné (AAAA-MM)",
        value=datetime.date.today().strftime("%Y-%m"),
        width=180,
        visible=False,
    )

    txt_create_num = ft.TextField(label="N° Facture Explicite (Auto-généré)", width=360, read_only=True, bgcolor=THEME["sage_pale"])
    txt_create_date_f = ft.TextField(label="Date d'émission (AAAA-MM-JJ)", value=str(datetime.date.today()), width=200)
    txt_create_date_e = ft.TextField(label="Date d'échéance (AAAA-MM-JJ)", value=str(datetime.date.today() + datetime.timedelta(days=15)), width=200)
    txt_create_montant = ft.TextField(label="Montant H.T. à facturer (€) *", width=220)
    info_devis_box = ft.Container(visible=False)

    def update_create_form():
        if not dd_create_devis.value:
            info_devis_box.visible = False
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT montant_setup, montant_abo, pourcentage_acompte, client_societe, client_nom, client_prenom, date_signature_contrat FROM devis WHERE numero_devis = ?", (dd_create_devis.value,))
        d = cursor.fetchone()
        conn.close()
        if d:
            setup, abo, pct = float(d[0]), float(d[1]), int(d[2])
            client_tag = sanitize_tag(d[3] or d[4])
            t_type = dd_create_type.value

            is_abo = (t_type == "Facture d'Abonnement Mensuel")
            txt_abo_mois.visible = is_abo

            if is_abo:
                mois_val = txt_abo_mois.value.strip() or datetime.date.today().strftime("%Y-%m")
                txt_create_num.value = f"FAC-ABO-{mois_val}_{dd_create_devis.value}_{client_tag}"
                txt_create_montant.value = f"{abo:.2f}"
            elif t_type == "Facture d'Acompte":
                txt_create_num.value = f"FAC-A_{dd_create_devis.value}_{client_tag}"
                montant_calc = setup * (pct / 100)
                txt_create_montant.value = f"{montant_calc:.2f}"
            else:
                txt_create_num.value = f"FAC-S_{dd_create_devis.value}_{client_tag}"
                montant_calc = setup * (1 - (pct / 100))
                txt_create_montant.value = f"{montant_calc:.2f}"

            info_devis_box.content = ft.Container(
                content=ft.Text(f"✅ Dossier vérifié | Client : {d[3] or d[4]} | Setup : {setup:.2f} € HT (Acompte {pct}%) | Abonnement : {abo:.2f} € HT/mois", size=12, color=ft.colors.GREEN_800, weight=ft.FontWeight.BOLD),
                bgcolor=ft.colors.GREEN_50,
                padding=12,
                border_radius=10,
            )
            info_devis_box.visible = True
            page.update()

    dd_create_devis.on_change = lambda e: update_create_form()
    dd_create_type.on_change = lambda e: update_create_form()
    txt_abo_mois.on_change = lambda e: update_create_form()

    def do_create_facture(e):
        if not dd_create_devis.value: return
        try: m_val = float(txt_create_montant.value.replace(",", "."))
        except ValueError: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO factures (numero_facture, numero_devis, type_facture, date_facture, date_echeance, montant_ht, statut)
                VALUES (?, ?, ?, ?, ?, ?, 'Facture Émise')
                """,
                (txt_create_num.value, dd_create_devis.value, dd_create_type.value, txt_create_date_f.value.strip(), txt_create_date_e.value.strip(), m_val),
            )
            conn.commit()
            conn.close()
            show_toast(page, f"Facture explicite {txt_create_num.value} établie avec succès !")
            page.go("/facturation_print")
        except sqlite3.IntegrityError:
            conn.close()
            show_toast(page, "Cette facture a déjà été émise sous ce numéro.", is_error=True)

    if has_eligibles:
        form_create_view = ft.Column(controls=[
            ft.Text("Établir une facture avec désignation & nom de société explicite", size=15, weight=ft.FontWeight.BOLD),
            info_devis_box,
            ft.Row([dd_create_devis, dd_create_type, txt_abo_mois]),
            ft.Row([txt_create_num, txt_create_montant]),
            ft.Row([txt_create_date_f, txt_create_date_e]),
            ft.ElevatedButton("💾 Émettre la facture officielle", icon=ft.icons.RECEIPT_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, height=48, on_click=do_create_facture),
        ], spacing=16)
    else:
        form_create_view = ft.Container(
            content=ft.Column([
                ft.Text("🔒 ÉMISSION DE FACTURE BLOQUÉE", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.RED_700),
                ft.Text(
                    "Conformément aux règles de Themis ERP, aucune facture ne peut être émise sans que le devis soit 'Validé & Signé' ET que le Dossier Contractuel (7 pages) n'ait été formellement signé.",
                    size=12,
                ),
                ft.ElevatedButton(
                    "👉 Aller dans 'Dossier Contractuel' pour valider la signature",
                    icon=ft.icons.GAVEL_ROUNDED,
                    bgcolor=THEME["sage"],
                    color=ft.colors.WHITE,
                    on_click=lambda e: page.go("/dossier"),
                ),
            ], spacing=12),
            padding=20,
            bgcolor=THEME["blush_pale"],
            border_radius=12,
        )

    dd_edit_fact = ft.Dropdown(label="Sélectionner la facture à corriger", options=[ft.dropdown.Option(str(f)) for f in df_fact["numero_facture"].tolist()], width=450)
    txt_edit_date_f = ft.TextField(label="Date d'émission", width=200)
    txt_edit_date_e = ft.TextField(label="Date d'échéance", width=200)
    txt_edit_montant = ft.TextField(label="Montant H.T. corrigé (€)", width=220)
    dd_edit_statut = ft.Dropdown(label="Statut", options=[ft.dropdown.Option(s) for s in STATUTS_FACTURES], width=250)

    def on_edit_fact_select(e):
        if not dd_edit_fact.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT date_facture, date_echeance, montant_ht, statut FROM factures WHERE numero_facture = ?", (dd_edit_fact.value,))
        row = cursor.fetchone()
        conn.close()
        if row:
            txt_edit_date_f.value, txt_edit_date_e.value, txt_edit_montant.value = str(row[0]), str(row[1]), f"{float(row[2]):.2f}"
            st = row[3] if row[3] in STATUTS_FACTURES else ("Facture Acquittée" if row[3] == "Payée" else "Facture Émise")
            dd_edit_statut.value = st
            page.update()

    dd_edit_fact.on_change = on_edit_fact_select

    def save_correction(e):
        if not dd_edit_fact.value: return
        try: m_val = float(txt_edit_montant.value.replace(",", "."))
        except ValueError: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE factures SET date_facture=?, date_echeance=?, montant_ht=?, statut=? WHERE numero_facture=?", (txt_edit_date_f.value.strip(), txt_edit_date_e.value.strip(), m_val, dd_edit_statut.value, dd_edit_fact.value))
        conn.commit()
        conn.close()
        show_toast(page, "Correction enregistrée !")
        page.go("/facturation_print")

    form_edit_view = ft.Column(controls=[
        ft.Text("Modifier ou corriger une facture existante", size=15, weight=ft.FontWeight.BOLD),
        dd_edit_fact, ft.Row([txt_edit_date_f, txt_edit_date_e]), ft.Row([txt_edit_montant, dd_edit_statut]),
        ft.ElevatedButton("Enregistrer la correction", icon=ft.icons.SAVE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=save_correction),
    ], spacing=16)

    dd_fact_orig = ft.Dropdown(label="Facture d'origine à créditer *", options=[ft.dropdown.Option(str(f)) for f in df_fact["numero_facture"].tolist()], width=450)
    lbl_orig_info = ft.Text("", italic=True)
    txt_motif_avoir = ft.TextField(label="Motif obligatoire de l'avoir * (ex: Annulation, Erreur de calcul...)", expand=True)
    txt_montant_avoir = ft.TextField(label="Montant H.T. à créditer (€) *", width=220)
    txt_date_avoir = ft.TextField(label="Date de l'avoir (AAAA-MM-JJ)", value=str(datetime.date.today()), width=200)

    def on_orig_select(e):
        if not dd_fact_orig.value:
            lbl_orig_info.value = ""
            page.update()
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT montant_ht FROM factures WHERE numero_facture = ?", (dd_fact_orig.value,))
        row = cursor.fetchone()
        conn.close()
        if row:
            lbl_orig_info.value = f"Montant H.T. initial de la facture : {float(row[0]):.2f} €"
            txt_montant_avoir.value = f"{abs(float(row[0])):.2f}"
            page.update()

    dd_fact_orig.on_change = on_orig_select

    def create_avoir(e):
        if not dd_fact_orig.value or not txt_motif_avoir.value.strip():
            show_toast(page, "Facture d'origine et motif obligatoires.", is_error=True)
            return
        try: m_av = float(txt_montant_avoir.value.replace(",", "."))
        except ValueError:
            show_toast(page, "Montant invalide.", is_error=True)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT numero_devis FROM factures WHERE numero_facture = ?", (dd_fact_orig.value,))
        num_devis = cursor.fetchone()[0]

        cursor.execute("SELECT client_societe, client_nom FROM devis WHERE numero_devis = ?", (num_devis,))
        c_info = cursor.fetchone()
        c_tag = sanitize_tag(c_info[0] or c_info[1])

        num_av = get_next_avoir(c_tag)
        cursor.execute(
            """
            INSERT INTO factures (numero_facture, numero_devis, type_facture, date_facture, date_echeance, montant_ht, statut, numero_facture_liee, motif)
            VALUES (?, ?, 'Avoir', ?, ?, ?, 'Facture Émise', ?, ?)
            """,
            (num_av, num_devis, txt_date_avoir.value.strip(), txt_date_avoir.value.strip(), -abs(m_av), dd_fact_orig.value, txt_motif_avoir.value.strip()),
        )
        conn.commit()
        conn.close()
        show_toast(page, f"Avoir {num_av} émis avec succès !")
        page.go("/facturation_print")

    form_avoir_view = ft.Column(controls=[
        ft.Text("Émettre une note de crédit explicite (Avoir)", size=15, weight=ft.FontWeight.BOLD),
        dd_fact_orig,
        lbl_orig_info,
        ft.Row([txt_montant_avoir, txt_date_avoir]),
        txt_motif_avoir,
        ft.ElevatedButton("Émettre l'avoir officiel", icon=ft.icons.CREDIT_CARD_ROUNDED, bgcolor=THEME["blush_dark"], color=ft.colors.WHITE, on_click=create_avoir),
    ], spacing=16)

    def set_mode(mode):
        nonlocal current_mode
        current_mode = mode
        if mode == "create":
            form_dynamic_container.content = form_create_view
            if has_eligibles: update_create_form()
        elif mode == "edit":
            form_dynamic_container.content = form_edit_view
        else:
            form_dynamic_container.content = form_avoir_view
        page.update()

    btn_mode_create = ft.ElevatedButton("1. Établir une Facture", icon=ft.icons.ADD_CARD_ROUNDED, on_click=lambda e: set_mode("create"))
    btn_mode_edit = ft.ElevatedButton("2. Modifier / Corriger", icon=ft.icons.EDIT_NOTE_ROUNDED, on_click=lambda e: set_mode("edit"))
    btn_mode_avoir = ft.ElevatedButton("3. Émettre un Avoir", icon=ft.icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, on_click=lambda e: set_mode("avoir"))
    set_mode("create")

    return ft.ListView(
        controls=[
            create_header("🧾", "Facturation & Avoirs", "Émission verrouillée, abonnements et nomenclature explicite"),
            ft.Row([btn_mode_create, btn_mode_edit, btn_mode_avoir], spacing=12),
            ft.Container(height=14),
            create_card(form_dynamic_container, padding=24),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 9. APERÇU FACTURES & TAMPONS VIRTUELS ---
def view_facture_interactive(page: ft.Page):
    conn = get_db()
    items = pd.read_sql_query("SELECT numero_facture FROM factures ORDER BY id DESC", conn)
    ent = get_entreprise_info()
    conn.close()

    dd_select = ft.Dropdown(label="Sélectionner la facture explicite :", options=[ft.dropdown.Option(str(i[0])) for i in items.values], width=450, border_color=THEME["sage_light"])
    dd_statut = ft.Dropdown(label="Nouveau statut :", options=[ft.dropdown.Option(s) for s in STATUTS_FACTURES], width=240, border_color=THEME["sage_light"])
    invoice_sheet_container = ft.Container(visible=False)

    def render_in_app_invoice(f_row):
        statut = f_row["statut"]
        montant = float(f_row["montant_ht"])
        is_payee = (statut in ["Facture Acquittée", "Payée"])
        is_annulee = (statut in ["Facture Annulée", "Annulée"])

        stamp_control = ft.Container()
        if is_payee:
            stamp_control = ft.Container(
                content=ft.Text("PAYÉE", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700),
                border=ft.border.all(3, ft.colors.GREEN_700), border_radius=8, padding=ft.padding.symmetric(horizontal=18, vertical=6), rotate=ft.transform.Rotate(-0.2)
            )
        elif is_annulee:
            stamp_control = ft.Container(
                content=ft.Text("ANNULÉE", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.RED_700),
                border=ft.border.all(3, ft.colors.RED_700), border_radius=8, padding=ft.padding.symmetric(horizontal=18, vertical=6), rotate=ft.transform.Rotate(-0.2)
            )

        paper_content = ft.Container(
            bgcolor=ft.colors.WHITE, border=ft.border.all(1, "#CBD5E0"), border_radius=12, padding=32,
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Column([ft.Text(ent['nom'], size=19, weight=ft.FontWeight.BOLD, color="#1A365D"), ft.Text(ent['adresse'], size=12, color="#555"), ft.Text(f"{ent['forme_juridique']} - SIRET : {ent['siret']}", size=11, color="#777")]),
                    ft.Column([ft.Text(f"{f_row['type_facture'].upper()}", size=17, weight=ft.FontWeight.BOLD, color="#1A365D"), ft.Text(f"N° {f_row['numero_facture']}", size=13, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]), ft.Text(f"Date : {f_row['date_facture']}", size=12, color="#555")], horizontal_alignment=ft.CrossAxisAlignment.END),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=28, color="#E2E8F0"),
                ft.Row(controls=[
                    ft.Container(content=ft.Column([ft.Text("Facturé à :", size=12, weight=ft.FontWeight.BOLD, color="#2B6CB0"), ft.Text(f_row['client_societe'] or 'Particulier', size=13, weight=ft.FontWeight.BOLD), ft.Text(f"{f_row['client_prenom']} {f_row['client_nom']}", size=12), ft.Text(f_row['client_adresse'], size=12)]), bgcolor="#F8FAFC", border=ft.border.all(1, "#CBD5E0"), border_radius=8, padding=14, width=320),
                    ft.Container(content=ft.Column([ft.Text("Détails :", size=12, weight=ft.FontWeight.BOLD, color="#2B6CB0"), ft.Text(f"Devis : {f_row['numero_devis']}", size=12), ft.Text(f"État : {statut}", size=12, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"])]), bgcolor="#F8FAFC", border=ft.border.all(1, "#CBD5E0"), border_radius=8, padding=14, width=320),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=18),
                ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("Désignation", weight=ft.FontWeight.BOLD)), ft.DataColumn(ft.Text("Qté", weight=ft.FontWeight.BOLD)), ft.DataColumn(ft.Text("Montant HT", weight=ft.FontWeight.BOLD))],
                    rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(f"{f_row['type_facture']} — Réf {f_row['numero_devis']}")), ft.DataCell(ft.Text("1")), ft.DataCell(ft.Text(f"{montant:.2f} €"))])],
                    heading_row_color="#E7EEE6", border=ft.border.all(1, "#CBD5E0")
                ),
                ft.Container(height=18),
                ft.Row(controls=[ft.Container(expand=True), ft.Column([ft.Text(f"Total H.T. : {montant:.2f} €", size=14), ft.Text(f"NET À PAYER : {montant:.2f} €", size=19, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]), ft.Text("TVA non applicable, art. 293 B du CGI.", size=10, italic=True)], horizontal_alignment=ft.CrossAxisAlignment.END)]),
            ])
        )

        return ft.Stack(controls=[paper_content, ft.Container(content=stamp_control, top=80, right=50)])

    def load_invoice(e):
        if not dd_select.value: return
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT f.*, d.client_nom, d.client_prenom, d.client_societe, d.client_adresse
            FROM factures f
            JOIN devis d ON f.numero_devis = d.numero_devis
            WHERE f.numero_facture = ?
            """,
            (dd_select.value,),
        )
        f_row = cursor.fetchone()
        conn.close()
        if f_row:
            st = f_row["statut"] if f_row["statut"] in STATUTS_FACTURES else ("Facture Acquittée" if f_row["statut"] == "Payée" else "Facture Émise")
            dd_statut.value = st
            invoice_sheet_container.content = render_in_app_invoice(f_row)
            invoice_sheet_container.visible = True
            page.update()

    dd_select.on_change = load_invoice

    def update_invoice_status(e):
        if not dd_select.value or not dd_statut.value: return
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("UPDATE factures SET statut = ? WHERE numero_facture = ?", (dd_statut.value, dd_select.value))

        if dd_statut.value == "Facture Acquittée":
            cursor.execute("SELECT * FROM paiements WHERE numero_facture = ?", (dd_select.value,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    SELECT f.montant_ht, d.client_societe, d.client_nom, d.client_prenom, f.type_facture
                    FROM factures f
                    JOIN devis d ON f.numero_devis = d.numero_devis
                    WHERE f.numero_facture = ?
                    """,
                    (dd_select.value,),
                )
                fd = cursor.fetchone()
                if fd:
                    c_name = fd[1] or f"{fd[3]} {fd[2]}"
                    cursor.execute("INSERT INTO paiements (numero_facture, date_paiement, client_nom, nature_prestation, montant_recu, mode_paiement, reference_reglement) VALUES (?, ?, ?, ?, ?, 'Virement bancaire', 'Règlement client direct')", (dd_select.value, str(datetime.date.today()), c_name, fd[4], float(fd[0])))

        conn.commit()
        conn.close()
        show_toast(page, f"Statut mis à jour : {dd_statut.value}. Synchronisé au livre des recettes.")
        load_invoice(None)

    return ft.ListView(
        controls=[
            create_header("🖨️", "Aperçu & Gestion des Factures", "Consultation, mise à jour du statut et réimpression avec tampons virtuels"),
            create_card(
                ft.Row(
                    controls=[
                        dd_select,
                        dd_statut,
                        ft.ElevatedButton("Valider Statut", icon=ft.icons.CHECK_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=update_invoice_status),
                        ft.ElevatedButton(
                            "🖨️ Imprimer la Facture (PDF)",
                            icon=ft.icons.PRINT_ROUNDED,
                            bgcolor=THEME["sage_dark"],
                            color=ft.colors.WHITE,
                            height=48,
                            on_click=lambda e: execute_print_facture(dd_select.value, page) if dd_select.value else show_toast(page, "Sélectionnez une facture d'abord.", is_error=True)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                )
            ),
            ft.Container(height=18),
            invoice_sheet_container,
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 10. LIVRE DES RECETTES (URSSAF) ---
def view_livre_recettes(page: ft.Page):
    conn = get_db()
    df_p = pd.read_sql_query("SELECT * FROM paiements ORDER BY date_paiement DESC, id DESC", conn)
    ent = get_entreprise_info()
    conn.close()

    taux_urssaf, taux_ir = ent["taux_urssaf"], ent["taux_ir"]
    total_encaisse = df_p["montant_recu"].sum() if not df_p.empty else 0.0

    p_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(r["date_paiement"])),
            ft.DataCell(ft.Text(r["numero_facture"], weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(r["client_nom"])),
            ft.DataCell(ft.Text(r["nature_prestation"])),
            ft.DataCell(ft.Text(r["mode_paiement"])),
            ft.DataCell(ft.Text(f"{float(r['montant_recu']):.2f} €", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)),
        ])
        for _, r in df_p.iterrows()
    ]

    table_paiements = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("N° Facture")), ft.DataColumn(ft.Text("Client")), ft.DataColumn(ft.Text("Nature Prestation")), ft.DataColumn(ft.Text("Règlement")), ft.DataColumn(ft.Text("Encaissé"))],
        rows=p_rows,
        heading_row_color=THEME["sage_pale"],
        border=ft.border.all(1, THEME["sage_light"]),
        border_radius=8,
    )

    return ft.ListView(
        controls=[
            create_header("💰", "Livre des Recettes (URSSAF)", "Document légal obligatoire listant les encaissements"),
            create_card(
                ft.Row([
                    ft.Column([ft.Text("TOTAL ENCAISSÉ", size=10, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{total_encaisse:.2f} €", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)]),
                    ft.Column([ft.Text(f"COTISATIONS URSSAF ({taux_urssaf}%)", size=10, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{(total_encaisse * taux_urssaf / 100):.2f} €", size=20, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"])]),
                    ft.Column([ft.Text(f"IMPÔT REVENU IR ({taux_ir}%)", size=10, color=THEME["text_muted"], weight=ft.FontWeight.BOLD), ft.Text(f"{(total_encaisse * taux_ir / 100):.2f} €", size=20, weight=ft.FontWeight.BOLD, color=THEME["blush_dark"])]),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                padding=20,
            ),
            ft.Container(height=18),
            create_card(table_paiements if p_rows else ft.Text("Aucun encaissement pour le moment.", italic=True), padding=16),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 11. DÉPENSES & ACHATS ---
def view_depenses(page: ft.Page):
    conn = get_db()
    df_dep = pd.read_sql_query("SELECT * FROM depenses ORDER BY date_depense DESC, id DESC", conn)
    conn.close()

    txt_fournisseur = ft.TextField(label="Fournisseur *", expand=True)
    txt_date_d = ft.TextField(label="Date (AAAA-MM-JJ)", value=str(datetime.date.today()), width=200)
    dd_cat = ft.Dropdown(label="Catégorie", options=[ft.dropdown.Option(c) for c in CATEGORIES_DEPENSES], value=CATEGORIES_DEPENSES[0], width=260)
    txt_montant_d = ft.TextField(label="Montant TTC (€) *", width=180)

    def add_depense(e):
        if not txt_fournisseur.value.strip() or not txt_montant_d.value.strip(): return
        try: m = float(txt_montant_d.value.replace(",", "."))
        except ValueError: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO depenses (date_depense, fournisseur, categorie, montant, mode_paiement, justificatif_ref, notes) VALUES (?, ?, ?, ?, 'Carte bancaire', '', '')", (txt_date_d.value.strip(), txt_fournisseur.value.strip(), dd_cat.value, m))
        conn.commit()
        conn.close()
        show_toast(page, "Dépense enregistrée !")
        page.go("/depenses")

    dep_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(r["date_depense"])),
            ft.DataCell(ft.Text(r["fournisseur"], weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(r["categorie"])),
            ft.DataCell(ft.Text(f"{float(r['montant']):.2f} €", color=THEME["blush_dark"], weight=ft.FontWeight.BOLD)),
        ])
        for _, r in df_dep.iterrows()
    ]

    table_depenses = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Fournisseur")), ft.DataColumn(ft.Text("Catégorie")), ft.DataColumn(ft.Text("Montant"))],
        rows=dep_rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
    )

    return ft.ListView(
        controls=[
            create_header("📉", "Dépenses & Achats", "Frais d'exploitation, abonnements et matériel"),
            create_card(
                ft.Column(controls=[
                    ft.Text("➕ Ajouter une dépense d'exploitation", size=15, weight=ft.FontWeight.BOLD),
                    ft.Row([txt_date_d, txt_fournisseur, dd_cat, txt_montant_d, ft.ElevatedButton("Ajouter", bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=add_depense)]),
                ], spacing=14)
            ),
            ft.Container(height=18),
            create_card(table_depenses if dep_rows else ft.Text("Aucune dépense enregistrée.", italic=True), padding=16),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 12. DOSSIER CONTRACTUEL (7 PAGES) ---
def view_dossier_contractuel(page: ft.Page):
    conn = get_db()
    items = pd.read_sql_query("SELECT numero_devis, client_societe, client_nom, statut, contrat_signe, date_signature_contrat, client_id FROM devis WHERE archive = 0 ORDER BY id DESC", conn)
    ent = get_entreprise_info()
    conn.close()

    dd_select = ft.Dropdown(
        label="Sélectionner le devis :",
        options=[ft.dropdown.Option(key=str(row[0]), text=f"{row[0]} — {row[1] or row[2]} ({'Signé ✅' if row[4] == 1 else 'Non signé ⚠️'})") for _, row in items.iterrows()],
        width=450,
    )

    signature_status_box = ft.Container(visible=False)
    txt_date_sign = ft.TextField(label="Date de signature effective (AAAA-MM-JJ)", value=str(datetime.date.today()), width=240)

    selected_file_path = None
    lbl_file_selected = ft.Text("Aucun fichier de scan sélectionné.", size=12, italic=True)

    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal selected_file_path
        if e.files and len(e.files) > 0:
            selected_file_path = e.files[0].path
            lbl_file_selected.value = f"📄 Prêt à archiver : {os.path.basename(selected_file_path)}"
            lbl_file_selected.color = ft.colors.GREEN_800
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    txt_scan_note = ft.TextField(label="Titre ou description du scan (ex: Contrat signé avec cachet commercial)", expand=True)
    scans_history_container = ft.Container()

    def refresh_scans_history(devis_num):
        conn = get_db()
        df_scans = pd.read_sql_query("SELECT * FROM documents_clients WHERE devis_id = ? ORDER BY id DESC", conn, params=(devis_num,))
        conn.close()

        if df_scans.empty:
            scans_history_container.content = ft.Text("Aucun document scanné n'a encore été rattaché à ce contrat.", italic=True, size=12)
        else:
            rows = []
            for _, sc in df_scans.iterrows():
                fpath = sc["chemin_fichier"]
                rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(sc["nom_document"], weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(sc["date_upload"])),
                        ft.DataCell(ft.Text(sc["notes"] or "-")),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "Consulter le scan",
                                icon=ft.icons.VISIBILITY_ROUNDED,
                                bgcolor=THEME["sage"],
                                color=ft.colors.WHITE,
                                on_click=lambda e, p=fpath: webbrowser.open(f"file://{p}"),
                            )
                        ),
                    ])
                )
            scans_history_container.content = ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Nom du document")), ft.DataColumn(ft.Text("Date d'archivage")), ft.DataColumn(ft.Text("Notes")), ft.DataColumn(ft.Text("Action"))],
                rows=rows, heading_row_color=THEME["sage_pale"], border=ft.border.all(1, THEME["sage_light"]), border_radius=8,
            )
        page.update()

    def on_devis_change(e):
        if not dd_select.value:
            signature_status_box.visible = False
            page.update()
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT statut, contrat_signe, date_signature_contrat, client_societe, client_nom FROM devis WHERE numero_devis = ?", (dd_select.value,))
        d = cursor.fetchone()
        conn.close()

        is_signe = (d[1] == 1)
        statut_devis = d[0]

        signature_status_box.content = ft.Container(
            bgcolor=ft.colors.GREEN_50 if is_signe else THEME["blush_pale"],
            border=ft.border.all(1, ft.colors.GREEN_400 if is_signe else THEME["blush_dark"]),
            border_radius=10,
            padding=14,
            content=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE_ROUNDED if is_signe else ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.GREEN_800 if is_signe else ft.colors.RED_800),
                ft.Column([
                    ft.Text(f"Statut Devis : {statut_devis} | Dossier Contractuel : {'VALIDÉ & SIGNÉ' if is_signe else 'NON SIGNÉ (Émission de facture bloquée)'}", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_900 if is_signe else ft.colors.RED_900),
                    ft.Text(f"Date de signature enregistrée : {d[2] or 'Aucune'}" if is_signe else "Pour débloquer la facturation, validez la signature ci-dessous.", size=12),
                ]),
            ]),
        )
        signature_status_box.visible = True
        refresh_scans_history(dd_select.value)

    dd_select.on_change = on_devis_change

    def mark_contract_signed(e):
        if not dd_select.value: return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE devis SET statut = 'Validé & Signé', contrat_signe = 1, date_signature_contrat = ?
            WHERE numero_devis = ?
            """,
            (txt_date_sign.value.strip(), dd_select.value),
        )
        conn.commit()
        conn.close()
        show_toast(page, f"Le devis {dd_select.value} et son dossier contractuel sont validés & signés. La facturation est débloquée !")
        on_devis_change(None)

    def attach_scanned_file(e):
        nonlocal selected_file_path
        if not dd_select.value or not selected_file_path:
            show_toast(page, "Sélectionnez un devis et choisissez un fichier scanné d'abord.", is_error=True)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM devis WHERE numero_devis = ?", (dd_select.value,))
        cid = cursor.fetchone()[0]

        fname = f"{dd_select.value}_scan_{datetime.date.today().strftime('%Y%m%d%H%M%S')}_{os.path.basename(selected_file_path)}"
        dest_path = os.path.join(SCANS_DIR, fname)
        shutil.copyfile(selected_file_path, dest_path)

        cursor.execute(
            """
            INSERT INTO documents_clients (client_id, devis_id, nom_document, chemin_fichier, date_upload, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cid or 1, dd_select.value, os.path.basename(selected_file_path), dest_path, str(datetime.date.today()), txt_scan_note.value.strip()),
        )
        conn.commit()
        conn.close()

        show_toast(page, "Scan du contrat archivé avec succès dans le dossier client !")
        selected_file_path = None
        lbl_file_selected.value = "Aucun fichier de scan sélectionné."
        txt_scan_note.value = ""
        refresh_scans_history(dd_select.value)

    def print_dossier(e):
        if not dd_select.value: return
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devis WHERE numero_devis = ?", (dd_select.value,))
        d = cursor.fetchone()
        conn.close()

        html = generate_dossier_contractuel_html(d, ent)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as tf:
            tf.write(html)
            temp_path = tf.name

        webbrowser.open(f"file://{temp_path}")
        show_toast(page, "Dossier contractuel exhaustif (7P) ouvert pour impression.")

    return ft.ListView(
        controls=[
            create_header("⚖️", "Dossier Contractuel Complet (7 Pages)", "Édition intégrale, validation de signature et archivage des scans"),
            create_card(
                ft.Column([
                    ft.Row([
                        dd_select,
                        ft.ElevatedButton("📄 Ouvrir et Imprimer le Dossier (7 Pages)", icon=ft.icons.DESCRIPTION_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, height=48, on_click=print_dossier),
                    ]),
                    signature_status_box,
                    ft.Divider(height=18),
                    ft.Text("✍️ Valider la signature du Dossier Contractuel (Condition préalable à la facturation) :", weight=ft.FontWeight.BOLD, size=13),
                    ft.Row([
                        txt_date_sign,
                        ft.ElevatedButton("Marquer comme Signé & Valider Devis", icon=ft.icons.CHECK_ROUNDED, bgcolor=ft.colors.GREEN_800, color=ft.colors.WHITE, on_click=mark_contract_signed),
                    ]),
                    ft.Divider(height=18),
                    ft.Text("📎 Archiver le Scan / PDF signé du client :", weight=ft.FontWeight.BOLD, size=13),
                    ft.Row([
                        ft.ElevatedButton("Choisir le fichier PDF/Scan...", icon=ft.icons.UPLOAD_FILE_ROUNDED, on_click=lambda e: file_picker.pick_files()),
                        lbl_file_selected,
                    ]),
                    ft.Row([
                        txt_scan_note,
                        ft.ElevatedButton("Rattacher au dossier client", icon=ft.icons.ATTACH_FILE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=attach_scanned_file),
                    ]),
                    ft.Container(height=12),
                    ft.Text("📁 Contrats et scans archivés pour ce devis :", weight=ft.FontWeight.BOLD, size=12),
                    scans_history_container,
                ], spacing=12),
                padding=20,
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# --- 13. PARAMÈTRES ENTREPRISE ---
def view_settings(page: ft.Page):
    ent = get_entreprise_info()
    txt_nom = ft.TextField(label="Nom commercial / Raison sociale", value=ent["nom"])
    txt_adresse = ft.TextField(label="Adresse du siège", value=ent["adresse"])
    txt_forme = ft.TextField(label="Forme juridique", value="" if ent["forme_juridique"] == "Non renseigné" else ent["forme_juridique"])
    txt_siret = ft.TextField(label="Numéro SIRET (14 chiffres)", value="" if ent["siret"] == "Non renseigné" else ent["siret"])
    txt_rcs = ft.TextField(label="RCS ou RM", value="" if ent["rcs_rm"] == "Non renseigné" else ent["rcs_rm"])

    txt_taux_urssaf = ft.TextField(label="Taux Cotisations URSSAF (%)", value=f"{ent['taux_urssaf']:.1f}", width=220)
    txt_taux_ir = ft.TextField(label="Taux Provision Impôt sur le Revenu (%)", value=f"{ent['taux_ir']:.1f}", width=220)

    def save_settings(e):
        try:
            t_u = float(txt_taux_urssaf.value.replace(",", "."))
            t_i = float(txt_taux_ir.value.replace(",", "."))
        except ValueError:
            show_toast(page, "Les taux doivent être des valeurs numériques.", is_error=True)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE entreprise SET nom=?, adresse=?, siret=?, rcs_rm=?, forme_juridique=?, taux_urssaf=?, taux_ir=? WHERE id=1", (txt_nom.value.strip(), txt_adresse.value.strip(), txt_siret.value.strip(), txt_rcs.value.strip(), txt_forme.value.strip(), t_u, t_i))
        conn.commit()
        conn.close()
        show_toast(page, "Paramètres et taux fiscaux actualisés !")
        page.go("/dashboard")

    return ft.ListView(
        controls=[
            create_header("⚙️", "Paramètres de l'Entreprise", "Mentions légales obligatoires et taux de cotisations"),
            create_card(
                ft.Column(controls=[
                    ft.Text("1. Informations Légales", weight=ft.FontWeight.BOLD, size=15),
                    txt_nom, txt_adresse, txt_forme, txt_siret, txt_rcs,
                    ft.Divider(height=18),
                    ft.Text("2. Taux Fiscaux & Sociaux Micro-Entreprise", weight=ft.FontWeight.BOLD, size=15),
                    ft.Row([txt_taux_urssaf, txt_taux_ir]),
                    ft.Text("💡 Taux standard BNC/Services : URSSAF 21,2 % et Versement Libératoire IR 2,2 %.", size=11, color=THEME["text_muted"], italic=True),
                    ft.ElevatedButton("Enregistrer les paramètres", icon=ft.icons.SAVE_ROUNDED, bgcolor=THEME["sage"], color=ft.colors.WHITE, on_click=save_settings),
                ], spacing=14)
            ),
            build_footer(),
        ],
        spacing=10,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Point d'entrée de l'application & Navigation Accordéon Stylisée
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    init_db()

    page.title = "Themis ERP - Micro-Entreprise"
    page.bgcolor = THEME["cream"]
    page.padding = 0

    page.fonts = {
        "Manrope": "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap"
    }
    page.theme = ft.Theme(font_family="Manrope")

    try:
        if os.path.exists(ICO_PATH):
            page.window.icon = ICO_PATH
    except Exception:
        pass

    content_area = ft.Container(expand=True, padding=ft.padding.symmetric(horizontal=30, vertical=20))

    def route_change(e):
        route = page.route
        if route in ["/dashboard", "", "/"]: content_area.content = view_dashboard(page)
        elif route == "/guide": content_area.content = view_livret_accueil(page)
        elif route == "/kanban": content_area.content = view_kanban(page)
        elif route == "/mco": content_area.content = view_mco_cockpit(page)
        elif route == "/crm": content_area.content = view_crm_clients(page)
        elif route == "/catalogue": content_area.content = view_catalogue(page)
        elif route == "/devis": content_area.content = view_devis_form(page)
        elif route == "/archives": content_area.content = view_archives(page)
        elif route == "/dossier": content_area.content = view_dossier_contractuel(page)
        elif route == "/factures": content_area.content = view_factures(page)
        elif route == "/facturation_print": content_area.content = view_facture_interactive(page)
        elif route == "/livre_recettes": content_area.content = view_livre_recettes(page)
        elif route == "/depenses": content_area.content = view_depenses(page)
        elif route == "/settings": content_area.content = view_settings(page)
        page.update()

    page.on_route_change = route_change

    def nav_sub_btn(icon, text, route, section="general"):
        is_active = page.route == route
        cfg = SECTION_COLORS.get(section, SECTION_COLORS["general"])
        def click(e): page.go(route)

        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(icon, size=16, color=cfg["icon_color"]), bgcolor=cfg["icon_bg"], border_radius=6, padding=5),
                ft.Text(text, size=12, weight=ft.FontWeight.W_600 if not is_active else ft.FontWeight.BOLD, color=THEME["text"] if not is_active else THEME["sage_dark"]),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=THEME["sage_light"] if is_active else ft.colors.TRANSPARENT,
            on_click=click,
            ink=True,
        )

    def nav_accordion_section(title, icon, color_key, sub_buttons, is_open=True):
        cfg = SECTION_COLORS.get(color_key, SECTION_COLORS["general"])
        return ft.ExpansionTile(
            leading=ft.Container(content=ft.Icon(icon, size=18, color=cfg["icon_color"]), bgcolor=cfg["icon_bg"], border_radius=8, padding=6),
            title=ft.Text(
                title,
                size=13.5,
                weight=ft.FontWeight.W_800,
                color=cfg["text_color"],
            ),
            controls=sub_buttons,
            initially_expanded=is_open,
            dense=True,
            tile_padding=ft.padding.symmetric(horizontal=6, vertical=2),
        )

    def build_sidebar():
        b64_logo = get_app_logo_base64()
        logo_widget = ft.Container()
        if b64_logo:
            logo_widget = ft.Container(
                content=ft.Image(src_base64=b64_logo, width=54, height=54, fit=ft.ImageFit.CONTAIN, border_radius=10),
                alignment=ft.alignment.center,
                margin=ft.margin.only(bottom=6),
            )

        return ft.Container(
            width=275,
            bgcolor=THEME["sage_pale"],
            border=ft.border.only(right=ft.BorderSide(1, THEME["sage_light"])),
            padding=ft.padding.symmetric(horizontal=10, vertical=15),
            content=ft.Column(
                controls=[
                    ft.Column([
                        logo_widget,
                        ft.Text("THEMIS ERP", size=20, weight=ft.FontWeight.BOLD, color=THEME["sage_dark"]),
                        ft.Text("Gestion Micro-Entreprise & CRM", size=10, color=THEME["text_muted"]),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(color=THEME["sage_light"], height=16),
                    nav_sub_btn(ft.icons.DASHBOARD_ROUNDED, "Tableau de bord ERP", "/dashboard", "general"),
                    nav_sub_btn(ft.icons.MENU_BOOK_ROUNDED, "Manuel & Livret d'Accueil", "/guide", "general"),
                    ft.Container(height=6),
                    nav_accordion_section(
                        "Production & Projets", ft.icons.PRECISION_MANUFACTURING_ROUNDED, "production",
                        [
                            nav_sub_btn(ft.icons.VIEW_KANBAN_ROUNDED, "Projets & Kanban (4P)", "/kanban", "production"),
                            nav_sub_btn(ft.icons.HEALTH_AND_SAFETY_ROUNDED, "Cockpit MCO & Abonnés", "/mco", "production"),
                        ],
                        is_open=True,
                    ),
                    nav_accordion_section(
                        "Commercial & CRM", ft.icons.CONTACTS_ROUNDED, "crm",
                        [
                            nav_sub_btn(ft.icons.PEOPLE_ALT_ROUNDED, "Portefeuille & Fiches 360°", "/crm", "crm"),
                            nav_sub_btn(ft.icons.INVENTORY_2_ROUNDED, "Catalogue Prestations", "/catalogue", "crm"),
                            nav_sub_btn(ft.icons.DESCRIPTION_ROUNDED, "Créer / Modifier Devis", "/devis", "crm"),
                            nav_sub_btn(ft.icons.ARCHIVE_ROUNDED, "Archiver / Supprimer", "/archives", "crm"),
                        ],
                        is_open=True,
                    ),
                    nav_accordion_section(
                        "Facturation & Contrats", ft.icons.GAVEL_ROUNDED, "facturation",
                        [
                            nav_sub_btn(ft.icons.GAVEL_ROUNDED, "Dossier Contractuel (7P)", "/dossier", "facturation"),
                            nav_sub_btn(ft.icons.POST_ADD_ROUNDED, "Établir Facture / Avoir", "/factures", "facturation"),
                            nav_sub_btn(ft.icons.RECEIPT_LONG_ROUNDED, "Aperçu & Tampons", "/facturation_print", "facturation"),
                        ],
                        is_open=True,
                    ),
                    nav_accordion_section(
                        "Finance & Fiscalité", ft.icons.ACCOUNT_BALANCE_ROUNDED, "finance",
                        [
                            nav_sub_btn(ft.icons.SAVINGS_ROUNDED, "Livre des Recettes (URSSAF)", "/livre_recettes", "finance"),
                            nav_sub_btn(ft.icons.SHOPPING_BAG_ROUNDED, "Dépenses & Achats", "/depenses", "finance"),
                        ],
                        is_open=False,
                    ),
                    ft.Container(height=6),
                    nav_sub_btn(ft.icons.SETTINGS_ROUNDED, "Paramètres Entreprise", "/settings", "systeme"),
                ],
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    page.add(ft.Row(controls=[build_sidebar(), content_area], expand=True, spacing=0))
    page.go("/dashboard")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    ft.app(target=main, host="0.0.0.0", port=port, view=ft.AppView.WEB_BROWSER)
