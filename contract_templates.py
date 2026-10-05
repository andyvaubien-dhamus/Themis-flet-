import json
import os
import base64
import datetime

def get_logo_html():
    """Charge themis.png en Base64 pour un affichage garanti sans blocage navigateur."""
    for p in ["themis.png", "Themis.png"]:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    return f'<img src="data:image/png;base64,{b64}" style="max-height: 52px; margin-bottom: 8px; border-radius: 6px;" /><br>'
            except Exception:
                pass
    return ""

def text_to_html_list(text):
    if not text:
        return ""
    lines = text.strip().split("\n")
    html = "<ul>"
    for line in lines:
        line = line.strip()
        if line.startswith("-"):
            line = line[1:].strip()
        if line:
            html += f"<li>{line}</li>"
    html += "</ul>"
    return html


# ===========================================================================
# 1. DOSSIER CONTRACTUEL COMPLET (7 PAGES) AVEC COORDONNÉES BANCAIRES
# ===========================================================================
def generate_dossier_contractuel_html(d, ent):
    """Génère l'intégralité du dossier contractuel (7 pages A4 complètes, non abrégées)."""
    d_dict = dict(d) if hasattr(d, "keys") else d
    ent_dict = dict(ent) if hasattr(ent, "keys") else ent

    setup = float(d_dict["montant_setup"])
    pct = int(d_dict["pourcentage_acompte"])
    acompte_val = setup * (pct / 100)
    solde_val = setup - acompte_val
    abo_val = float(d_dict["montant_abo"])
    logo_html = get_logo_html()

    iban_str = ent_dict.get("iban") or "Non renseigné"
    bic_str = ent_dict.get("bic") or "Non renseigné"
    banque_str = ent_dict.get("banque_nom") or "Établissement Bancaire"
    titulaire_str = ent_dict.get("titulaire_compte") or ent_dict.get("nom")

    # Lecture des lignes multi-prestations
    try:
        lignes = json.loads(d_dict.get("lignes_json") or "[]")
    except Exception:
        lignes = []

    if not lignes:
        lignes = [{"designation": "Forfait Setup & Création Initiale", "qte": 1, "prix_setup": setup, "prix_abo": abo_val}]

    table_lignes_html = ""
    for lig in lignes:
        q = int(lig.get("qte", 1))
        ps = float(lig.get("prix_setup", 0.0))
        pa = float(lig.get("prix_abo", 0.0))
        tot_l_setup = q * ps
        abo_str = f"{pa:.2f} €/m" if pa > 0 else "-"
        table_lignes_html += f"""
        <tr>
            <td><strong>{lig.get('designation', '')}</strong></td>
            <td style="text-align: center;">{q}</td>
            <td style="text-align: right;">{ps:.2f} €</td>
            <td style="text-align: right;">{abo_str}</td>
            <td style="text-align: right;">{tot_l_setup:.2f} €</td>
        </tr>
        """

    # Bloc ROI Client & Rentabilité de l'investissement
    roi_h = float(d_dict.get("roi_heures_semaine") or 0.0)
    roi_taux = float(d_dict.get("roi_cout_horaire") or 25.0)
    roi_html = ""
    if roi_h > 0:
        gain_annuel = roi_h * 52 * roi_taux
        amortissement_semaines = (setup / (roi_h * roi_taux)) if (roi_h * roi_taux) > 0 else 0
        roi_html = f"""
        <div style="margin: 15px 0; padding: 12px 16px; background: #F0FFF4; border: 1px solid #9AE6B4; border-radius: 6px;">
            <h3 style="margin: 0 0 5px 0; color: #22543D; font-size: 12px;">📊 RENTABILITÉ ESTIMÉE DE L'INVESTISSEMENT (ROI CLIENT)</h3>
            <p style="margin: 0; font-size: 11px; color: #276749;">
                Sur la base de <strong>{roi_h:.1f} heures économisées par semaine</strong> valorisées à {roi_taux:.2f} €/h :<br>
                • <strong>Gain de productivité annuel estimé : {gain_annuel:,.2f} € HT / an</strong> (soit {roi_h*52:.0f} h libérées pour votre équipe)<br>
                • <strong>Amortissement de la prestation : {amortissement_semaines:.1f} semaines</strong>. L'investissement est intégralement rentabilisé dès le 2ème mois.
            </p>
        </div>
        """

    try:
        sections = json.loads(d_dict.get("sections_json") or "[]")
    except Exception:
        sections = []

    sections_html = ""
    for sec in sections:
        if sec.get("title") or sec.get("content"):
            sections_html += f"<h2>{sec.get('title', '')}</h2>{text_to_html_list(sec.get('content', ''))}"

    client_display = d_dict.get("client_societe") or f"{d_dict.get('client_prenom', '')} {d_dict.get('client_nom', '')}"

    rib_box_html = f"""
    <div style="margin-top: 15px; padding: 10px 14px; background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; font-size: 11px;">
        <strong style="color: #1A365D;">COORDONNÉES BANCAIRES POUR LE RÈGLEMENT (VIREMENT) :</strong><br>
        Banque : <strong>{banque_str}</strong> | Titulaire : <strong>{titulaire_str}</strong><br>
        IBAN : <code style="font-size: 11.5px; font-weight: bold; color: #2B6CB0;">{iban_str}</code> | 
        BIC : <code style="font-size: 11.5px; font-weight: bold; color: #2B6CB0;">{bic_str}</code>
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Dossier_Contractuel_{d_dict['numero_devis']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333333; background: #FAF7F2; margin: 0; padding: 20px; }}
        .no-print {{ text-align: center; margin-bottom: 25px; position: sticky; top: 15px; z-index: 1000; }}
        .btn-print {{ background-color: #6E8A85; color: #ffffff; border: none; border-radius: 8px; padding: 12px 28px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(110, 138, 133, 0.3); }}
        .btn-print:hover {{ background-color: #55706B; }}
        .page-doc {{ width: 210mm; min-height: 297mm; padding: 20mm; margin: 0 auto 30px auto; box-sizing: border-box; border: 1px solid #CBD5E0; background: #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-radius: 8px; page-break-after: always; }}
        h1 {{ font-size: 18px; color: #1A365D; border-bottom: 2px solid #3182CE; padding-bottom: 5px; margin-top: 0; }}
        h2 {{ font-size: 14px; color: #2B6CB0; margin-top: 15px; margin-bottom: 6px; }}
        h3 {{ font-size: 13px; color: #2B6CB0; margin: 0 0 5px 0; }}
        p, li {{ font-size: 12px; line-height: 1.5; text-align: justify; }}
        .box-info {{ border: 1px solid #CBD5E0; padding: 12px; border-radius: 5px; background: #F8FAFC; margin-bottom: 15px; width: 48%; display: inline-block; vertical-align: top; box-sizing: border-box; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #CBD5E0; padding: 8px; text-align: left; font-size: 12px; }}
        th {{ background-color: #EDF2F7; color: #1A365D; }}
        .signatures-container {{ margin-top: 25px; width: 100%; }}
        .sig-box-left {{ width: 45%; height: 70px; border: 1px dashed #A0AEC0; padding: 8px; font-size: 11px; color: #718096; display: inline-block; box-sizing: border-box; }}
        .sig-box-right {{ width: 45%; height: 70px; border: 1px dashed #A0AEC0; padding: 8px; font-size: 11px; color: #718096; display: inline-block; float: right; box-sizing: border-box; }}
        .clear {{ clear: both; }}
        @media print {{ body {{ background: transparent !important; padding: 0 !important; }} .no-print {{ display: none !important; }} .page-doc {{ box-shadow: none !important; border: none !important; border-radius: 0 !important; margin: 0 !important; width: 100% !important; min-height: 297mm !important; padding: 15mm 20mm !important; }} }}
    </style>
</head>
<body>
    <div class="no-print"><button class="btn-print" onclick="window.print()">🖨️ Imprimer ou Enregistrer en PDF (Ctrl + P)</button></div>

    <!-- PAGE 1 : DEVIS -->
    <div class="page-doc">
        <table style="width: 100%; border: none; margin-bottom: 20px;"><tr>
            <td style="border: none; vertical-align: top;">
                {logo_html}
                <h2 style="margin: 0; color: #1a365d;">{ent_dict['nom']}</h2>
                <p style="margin: 5px 0 0 0;">{ent_dict['adresse']}</p>
                <p style="margin: 2px 0;">Solutions logicielles & automatisation</p>
                <p style="font-size: 10px; color: #666; margin: 4px 0 0 0;">{ent_dict['forme_juridique']}<br>SIRET : {ent_dict['siret']}<br>{ent_dict['rcs_rm']}</p>
            </td>
            <td style="border: none; text-align: right; vertical-align: top;">
                <h1 style="margin: 0; border: none; font-size: 20px; color: #1a365d;">DEVIS N° {d_dict['numero_devis']}</h1>
                <p style="margin: 5px 0 0 0;">Date : {d_dict['date_creation']}</p>
                <p style="margin: 2px 0;">Validité : {d_dict['date_validite']}</p>
            </td>
        </tr></table>
        <div style="margin-top: 15px;">
            <div class="box-info"><h3>Client :</h3><p><strong>{d_dict.get('client_societe') or 'Particulier'}</strong></p><p>{d_dict.get('client_prenom', '')} {d_dict.get('client_nom', '')}</p><p>{d_dict.get('client_adresse', '')}</p><p>Tél : {d_dict.get('client_telephone', '')} | Email : {d_dict.get('client_email', '')}</p></div>
            <div class="box-info" style="float: right;"><h3>Modalités de règlement :</h3><p><strong>Acompte ({pct}%) : {acompte_val:.2f} €</strong></p><p><strong>Solde : {solde_val:.2f} €</strong></p><p>Abonnement : {abo_val:.2f} € / mois</p></div>
            <div class="clear"></div>
        </div>
        <table>
            <tr><th>Description de la Prestation</th><th style="width: 45px; text-align: center;">Qté</th><th style="width: 95px; text-align: right;">Prix Setup HT</th><th style="width: 95px; text-align: right;">Abo. Mensuel</th><th style="width: 105px; text-align: right;">Total Setup HT</th></tr>
            {table_lignes_html}
        </table>
        {roi_html}
        <div style="text-align: right; margin-top: 10px;">
            <p style="font-size: 13px; margin: 2px 0;">Total Frais de Création : <strong>{setup:.2f} € H.T.</strong></p>
            <p style="font-size: 13px; margin: 2px 0;">Total Abonnements récurrents : <strong>{abo_val:.2f} € H.T. / mois</strong></p>
            <p style="font-size: 10px; color: #666; margin-top: 4px;"><em>TVA non applicable, art. 293 B du CGI.</em></p>
        </div>
        {rib_box_html}
        <div class="signatures-container"><p><strong>Bon pour accord et engagement :</strong></p><div class="sig-box-left">Signature du Prestataire :</div><div class="sig-box-right">Signature & Cachet du Client :</div><div class="clear"></div></div>
    </div>

    <!-- PAGE 2 : BON DE COMMANDE -->
    <div class="page-doc">
        <table style="width: 100%; border: none; margin-bottom: 20px;"><tr>
            <td style="border: none; vertical-align: top;">
                {logo_html}
                <h2 style="margin: 0; color: #1a365d;">{ent_dict['nom']}</h2>
                <p style="margin: 5px 0 0 0;">{ent_dict['adresse']}</p>
            </td>
            <td style="border: none; text-align: right; vertical-align: top;">
                <h1 style="margin: 0; border: none; font-size: 20px; color: #1a365d;">BON DE COMMANDE N° {d_dict['numero_devis'].replace("DEV", "BC")}</h1>
                <p style="margin: 5px 0 0 0;">Devis de référence : {d_dict['numero_devis']} du {d_dict['date_creation']}</p>
            </td>
        </tr></table>
        <div class="box-info">
            <h3>Client :</h3>
            <p style="margin: 0;"><strong>{d_dict.get('client_societe') or 'Particulier'}</strong></p>
            <p style="margin: 2px 0;">{d_dict.get('client_prenom', '')} {d_dict.get('client_nom', '')}</p>
            <p style="margin: 2px 0;">{d_dict.get('client_adresse', '')}</p>
            <p style="margin: 2px 0;">Tél : {d_dict.get('client_telephone', '')} | Email : {d_dict.get('client_email', '')}</p>
        </div>
        <div class="clear"></div>
        <h2>Objet de la commande</h2>
        <p>Le Client confirme la commande ferme et définitive de la prestation décrite au devis n° {d_dict['numero_devis']} pour un montant de <strong>{setup:.2f} € H.T.</strong> au titre du forfait Setup & Création Initiale, et un abonnement mensuel de <strong>{abo_val:.2f} € H.T.</strong></p>
        <table><tr><th>Élément</th><th style="text-align: right; width: 140px;">Montant H.T.</th></tr><tr><td>Total Forfaits Setup & Création</td><td style="text-align: right;">{setup:.2f} €</td></tr><tr><td>Acompte à la commande ({pct}%)</td><td style="text-align: right;">{acompte_val:.2f} €</td></tr><tr><td>Solde à la livraison</td><td style="text-align: right;">{solde_val:.2f} €</td></tr><tr><td>Abonnement mensuel</td><td style="text-align: right;">{abo_val:.2f} €</td></tr></table>
        <p>La signature vaut acceptation sans réserve des CGV et engage le Client au versement de l'acompte prévu.</p>
        {rib_box_html}
        <div class="signatures-container"><p><strong>Bon pour commande, le _____________________</strong></p><div class="sig-box-left">Pour le Prestataire<br>Signature :</div><div class="sig-box-right">Pour le Client<br>Signature & Cachet :</div><div class="clear"></div></div>
    </div>

    <!-- PAGE 3 : ANNEXE 1 CAHIER DES CHARGES -->
    <div class="page-doc">
        <h1>ANNEXE 1 : Cahier des Charges Fonctionnel</h1>
        <p>Client : <strong>{d_dict.get('client_societe') or 'Particulier'}</strong></p>
        <p>Le présent document définit le périmètre strict de l'application livrée dans le cadre du devis n° {d_dict['numero_devis']}. Il constitue le référentiel technique et fonctionnel sur la base duquel la recette de l'application sera effectuée.</p>
        {sections_html if sections_html else "<p><em>Aucune section détaillée n'a encore été renseignée pour ce devis.</em></p>"}
    </div>

    <!-- PAGE 4 : ANNEXE 2 CGV (14 ARTICLES) -->
    <div class="page-doc">
        <h1>ANNEXE 2 : Conditions Générales de Vente (CGV)</h1>

        <h2>Article 1 : Objet</h2>
        <p>Les présentes conditions générales de vente régissent les relations contractuelles entre {ent_dict['nom']} (ci-après « le Prestataire ») et le Client, dans le cadre de la conception, du développement et de la mise à disposition d'une solution logicielle sur-mesure, telle que définie au devis n° {d_dict['numero_devis']} et à son Annexe 1 (Cahier des Charges Fonctionnel). Toute commande implique l'acceptation sans réserve des présentes CGV par le Client.</p>

        <h2>Article 2 : Devis, commande et durée de validité</h2>
        <p>Le devis est établi pour une durée de validité de trente (30) jours à compter de sa date d'émission. La commande est réputée ferme et définitive à compter de la signature du devis par le Client et du versement de l'acompte prévu à l'article 3. Toute prestation complémentaire non prévue au devis initial fera l'objet d'un devis additionnel.</p>

        <h2>Article 3 : Prix et modalités de paiement</h2>
        <p>Les prix sont exprimés en euros. Conformément à l'article 293 B du Code général des impôts, la TVA n'est pas applicable. Les frais de création (« Setup ») sont facturés en deux temps : un acompte de {pct}% à la commande, exigible avant le démarrage des travaux, et un solde facturé à la livraison de l'application, avant sa mise en production définitive. L'abonnement mensuel de {abo_val:.2f} € couvre l'hébergement, la maintenance technique et les mises à jour de l'application ; il est facturé mensuellement à compter de la mise en service et reconductible tacitement, sauf résiliation dans les conditions de l'article 10. Tout retard de paiement pourra entraîner la suspension des prestations après mise en demeure restée infructueuse pendant quinze (15) jours.</p>

        <h2>Article 4 : Délais d'exécution</h2>
        <p>Les délais de réalisation communiqués par le Prestataire sont donnés à titre indicatif et courent à compter de la réception de l'acompte et de l'ensemble des éléments nécessaires au démarrage du projet (contenus, accès, validations). Ils pourront être prolongés en cas de retard imputable au Client dans la fourniture de ces éléments ou dans la validation des livrables intermédiaires.</p>

        <h2>Article 5 : Obligations du Client</h2>
        <p>Le Client s'engage à fournir dans les meilleurs délais l'ensemble des informations, contenus, identifiants et accès nécessaires à la bonne exécution de la prestation, à désigner un interlocuteur habilité à valider les livrables, et à formuler ses observations dans un délai raisonnable afin de ne pas retarder le projet. Le Client demeure seul responsable de la licéité des contenus qu'il fournit et de leur conformité à la réglementation en vigueur.</p>

        <h2>Article 6 : Obligations du Prestataire</h2>
        <p>Le Prestataire s'engage à mettre en œuvre les moyens raisonnables et les compétences nécessaires à la réalisation de la prestation conformément au cahier des charges (Annexe 1), dans le respect des règles de l'art. Le Prestataire tient le Client informé de l'avancement du projet et l'alerte sans délai en cas de difficulté susceptible d'affecter les délais ou le périmètre convenu.</p>

        <h2>Article 7 : Recette et livraison</h2>
        <p>À l'issue du développement, l'application est mise à disposition du Client à des fins de vérification et de recette, dans les conditions décrites en Annexe 3 (Procès-Verbal de Recette). L'absence de retour du Client dans un délai de dix (10) jours ouvrés à compter de la mise à disposition vaut acceptation tacite de la livraison.</p>

        <h2>Article 8 : Propriété intellectuelle</h2>
        <p>Le Prestataire demeure titulaire de l'ensemble des droits de propriété intellectuelle attachés aux codes sources, briques logicielles, méthodes et savoir-faire développés, y compris ceux développés spécifiquement pour le Client, sauf stipulation contraire expresse figurant au devis. Le Client bénéficie, à compter du complet paiement des sommes dues, d'un droit d'usage de l'application pour ses besoins propres, non exclusif et non cessible. Les contenus fournis par le Client (textes, images, marques, logo) restent sa propriété exclusive.</p>

        <h2>Article 9 : Garantie et maintenance</h2>
        <p>Le Prestataire garantit la correction, sans frais supplémentaires, des anomalies ou dysfonctionnements bloquants signalés par le Client dans un délai de trente (30) jours à compter de la recette, dès lors que ceux-ci résultent d'un défaut de conception ou de réalisation imputable au Prestataire. Cette garantie ne couvre pas les évolutions fonctionnelles, les demandes de nouvelles fonctionnalités, ni les dysfonctionnements résultant d'une utilisation non conforme, d'une modification effectuée par un tiers, ou d'un environnement technique du Client non maîtrisé par le Prestataire. Au-delà de cette période, la maintenance corrective et évolutive est couverte par l'abonnement mensuel visé à l'article 3.</p>

        <h2>Article 10 : Résiliation</h2>
        <p>L'abonnement mensuel peut être résilié par chacune des parties moyennant un préavis écrit de trente (30) jours. En cas de manquement grave de l'une des parties à ses obligations, non régularisé dans un délai de quinze (15) jours après mise en demeure, l'autre partie pourra résilier le contrat de plein droit, sans préjudice de tout dommage et intérêt éventuel. Les sommes dues au titre des prestations déjà réalisées restent exigibles.</p>

        <h2>Article 11 : Responsabilité</h2>
        <p>La responsabilité du Prestataire ne pourra être engagée qu'en cas de faute prouvée, et est limitée aux dommages directs, à l'exclusion de tout préjudice indirect (perte d'exploitation, perte de données, perte de chiffre d'affaires, préjudice commercial). En tout état de cause, la responsabilité totale du Prestataire est plafonnée au montant total effectivement versé par le Client au titre du devis concerné.</p>

        <h2>Article 12 : Confidentialité et protection des données</h2>
        <p>Chaque partie s'engage à conserver strictement confidentielles les informations de nature commerciale, technique ou financière dont elle aurait connaissance à l'occasion de l'exécution du contrat, et à ne les divulguer à aucun tiers sans accord préalable écrit de l'autre partie. Le traitement des données à caractère personnel réalisé dans le cadre de la prestation est effectué conformément au Règlement Général sur la Protection des Données (RGPD) et à la loi Informatique et Libertés.</p>

        <h2>Article 13 : Force majeure</h2>
        <p>Aucune des parties ne pourra être tenue responsable de l'inexécution de ses obligations si celle-ci résulte d'un cas de force majeure au sens de l'article 1218 du Code civil et de la jurisprudence des tribunaux français.</p>

        <h2>Article 14 : Droit applicable et litiges</h2>
        <p>Les présentes CGV sont soumises au droit français. En cas de différend relatif à leur interprétation ou à leur exécution, les parties s'efforceront de trouver une solution amiable avant toute action contentieuse. À défaut d'accord amiable, les tribunaux compétents seront ceux du ressort du siège du Prestataire, sauf disposition d'ordre public contraire.</p>
    </div>

    <!-- PAGE 5 : ANNEXE 3 PROCÈS-VERBAL DE RECETTE -->
    <div class="page-doc">
        <h1>ANNEXE 3 : PROCÈS-VERBAL DE RECETTE</h1>

        <h2>Objet</h2>
        <p>Le présent procès-verbal a pour objet de constater la vérification, par le Client <strong>{client_display}</strong>, de la conformité de l'application livrée par le Prestataire au titre du devis n° {d_dict['numero_devis']}, au regard des spécifications décrites en Annexe 1 (Cahier des Charges Fonctionnel).</p>

        <h2>Vérifications effectuées</h2>
        <p>Le Client déclare avoir procédé, seul ou avec l'assistance du Prestataire, aux vérifications suivantes :</p>
        <ul>
            <li>Contrôle du bon fonctionnement des fonctionnalités décrites en Annexe 1</li>
            <li>Vérification de l'accessibilité et de la prise en main de l'application</li>
            <li>Contrôle de la cohérence des contenus et informations intégrées</li>
            <li>Test des principaux parcours d'utilisation de l'application</li>
        </ul>

        <h2>Résultat de la recette</h2>
        <p>(Cocher la mention applicable lors de l'impression ou de la signature du document)</p>
        <table class="table-devis">
            <tr>
                <th style="width: 15%; text-align: center;">☐</th>
                <td>Recette prononcée <strong>sans réserve</strong> : l'application est conforme au cahier des charges et est acceptée en l'état.</td>
            </tr>
            <tr>
                <th style="text-align: center;">☐</th>
                <td>Recette prononcée <strong>avec réserves</strong> : l'application est acceptée sous réserve de la correction des anomalies listées ci-dessous, dans les conditions de garantie prévues à l'Article 9 des CGV.</td>
            </tr>
        </table>

        <h2>Liste des réserves éventuelles</h2>
        <table class="table-devis">
            <tr>
                <th style="width: 40px;">N°</th>
                <th>Description de l'anomalie</th>
                <th style="width: 180px;">Date de correction prévue</th>
            </tr>
            <tr><td>1</td><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td>2</td><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td>3</td><td>&nbsp;</td><td>&nbsp;</td></tr>
        </table>

        <h2>Effets de la signature</h2>
        <p>La signature du présent procès-verbal, avec ou sans réserve, emporte acceptation de la livraison au sens de l'Article 7 des CGV et déclenche le point de départ du délai de garantie prévu à l'Article 9 des CGV. À défaut de retour signé du Client dans un délai de dix (10) jours ouvrés à compter de la mise à disposition de l'application, la recette sera réputée acquise sans réserve.</p>

        <div class="signatures-container" style="margin-top: 40px;">
            <p><strong>Fait en deux exemplaires, le _____________________</strong></p>
            <div class="sig-box-left">Pour le Prestataire<br>Nom et qualité :<br>Signature :</div>
            <div class="sig-box-right">Pour le Client<br>Nom et qualité :<br>Signature :</div>
            <div class="clear"></div>
        </div>
    </div>

    <!-- PAGE 6 : ANNEXE 4 CONTRAT DE PRESTATION (SLA) -->
    <div class="page-doc">
        <h1>ANNEXE 4 : Contrat de Prestation et d'Abonnement</h1>

        <p><strong>ENTRE LES SOUSSIGNÉS :</strong></p>
        <p>{ent_dict['nom']}, {ent_dict['forme_juridique']}, dont le siège est situé {ent_dict['adresse']}, SIRET {ent_dict['siret']}, {ent_dict['rcs_rm']}, ci-après désigné « le Prestataire »,</p>
        <p>ET</p>
        <p><strong>{d_dict.get('client_societe') or 'Particulier'}</strong>, {d_dict.get('client_prenom', '')} {d_dict.get('client_nom', '')}, dont l'adresse est {d_dict.get('client_adresse', '')}, ci-après désigné « le Client »,</p>
        <p><em>Ci-après désignés ensemble « les Parties ».</em></p>

        <p>Le présent contrat a pour objet de formaliser, en complément du devis n° {d_dict['numero_devis']}, de son Annexe 1 (Cahier des Charges Fonctionnel) et des Conditions Générales de Vente (Annexe 2), les conditions de réalisation de la prestation de développement et les modalités de l'abonnement mensuel de maintenance et d'hébergement.</p>

        <h2>Article 1 : Objet</h2>
        <p>Le Prestataire s'engage à développer, livrer, héberger et maintenir, pour le compte du Client, l'application décrite en Annexe 1, et à fournir les prestations d'hébergement et de maintenance associées à l'abonnement mensuel prévu à l'article 3 des CGV.</p>

        <h2>Article 2 : Durée</h2>
        <p>Le présent contrat prend effet à sa date de signature. La phase de développement se déroule jusqu'à la recette de l'application (Annexe 3). L'abonnement mensuel prend effet à la mise en service de l'application et est conclu pour une durée initiale de douze (12) mois, renouvelable ensuite par tacite reconduction pour des périodes successives d'un (1) mois, sauf résiliation dans les conditions de l'Article 6.</p>

        <h2>Article 3 : Niveau de service (SLA)</h2>
        <p>Le Prestataire s'engage sur les objectifs de service suivants pour l'application hébergée, sauf cas de force majeure ou maintenance programmée annoncée au moins 48 heures à l'avance :</p>
        <table class="table-devis">
            <tr>
                <th style="width: 100px;">Niveau d'incident</th>
                <th>Définition</th>
                <th style="width: 140px;">Délai de prise en charge</th>
            </tr>
            <tr>
                <td><strong>Bloquant</strong></td>
                <td>Application inaccessible ou fonctionnalité essentielle inopérante</td>
                <td>1 jour ouvré</td>
            </tr>
            <tr>
                <td><strong>Majeur</strong></td>
                <td>Fonctionnalité dégradée sans blocage total de l'application</td>
                <td>3 jours ouvrés</td>
            </tr>
            <tr>
                <td><strong>Mineur</strong></td>
                <td>Anomalie sans impact significatif sur l'usage de l'application</td>
                <td>10 jours ouvrés</td>
            </tr>
        </table>
        <p>Les délais ci-dessus courent à compter du signalement de l'anomalie par le Client au Prestataire, et correspondent à un délai de prise en charge (début du diagnostic), non à une garantie de résolution dans ce délai pour les anomalies complexes.</p>

        <h2>Article 4 : Modalités financières</h2>
        <p>Les modalités de prix et de facturation applicables au présent contrat sont celles définies au devis n° {d_dict['numero_devis']} et à l'Article 3 des Conditions Générales de Vente (Annexe 2).</p>

        <h2>Article 5 : Suspension du service</h2>
        <p>Le Prestataire peut suspendre temporairement l'accès à l'application en cas de maintenance programmée (avec information préalable du Client), d'impayé persistant après mise en demeure restée infructueuse pendant quinze (15) jours (conformément à l'Article 3 des CGV), ou de nécessité impérieuse liée à la sécurité des systèmes. Le Prestataire informe le Client dans les meilleurs délais de toute suspension et de sa durée prévisible.</p>

        <h2>Article 6 : Résiliation</h2>
        <p>L'abonnement mensuel peut être résilié par chacune des Parties dans les conditions prévues à l'Article 10 des CGV (Annexe 2), à savoir moyennant un préavis écrit de trente (30) jours, ou de plein droit en cas de manquement grave non régularisé après mise en demeure.</p>

        <h2>Article 7 : Réversibilité</h2>
        <p>En cas de résiliation ou de non-renouvellement de l'abonnement, le Prestataire s'engage à restituer au Client, dans un délai de trente (30) jours à compter de la date d'effet de la résiliation, une exportation des données propres au Client hébergées dans l'application, dans un format structuré et exploitable. Cette réversibilité porte sur les données du Client ; elle ne confère aucun droit sur le code source de l'application, dont la propriété reste régie par l'Article 8 des CGV.</p>

        <h2>Article 8 : Confidentialité</h2>
        <p>Les Parties demeurent tenues aux obligations de confidentialité prévues à l'Article 12 des CGV (Annexe 2) ainsi que, le cas échéant, à l'Accord de Confidentialité signé préalablement entre les Parties (Annexe 5).</p>

        <h2>Article 9 : Hiérarchie contractuelle et divers</h2>
        <p>En cas de contradiction entre les documents contractuels, l'ordre de priorité suivant s'applique : (1) le présent Contrat de Prestation et d'Abonnement, (2) le Bon de Commande signé, (3) les Conditions Générales de Vente (Annexe 2), (4) le devis et son Annexe 1. Pour tout ce qui n'est pas prévu au présent contrat, les dispositions des CGV s'appliquent. Le présent contrat est soumis au droit français, dans les conditions de compétence juridictionnelle prévues à l'Article 14 des CGV.</p>

        <div class="signatures-container">
            <p><strong>Fait en deux exemplaires, le _____________________</strong></p>
            <div class="sig-box-left">Pour le Prestataire<br>Signature :</div>
            <div class="sig-box-right">Pour le Client<br>Signature :</div>
            <div class="clear"></div>
        </div>
    </div>

    <!-- PAGE 7 : ANNEXE 5 ACCORD DE CONFIDENTIALITÉ (NDA) -->
    <div class="page-doc">
        <h1>ANNEXE 5 : Accord de Confidentialité (NDA)</h1>

        <p><strong>ENTRE LES SOUSSIGNÉS :</strong></p>
        <p>{ent_dict['nom']}, dont le siège est situé {ent_dict['adresse']}, SIRET {ent_dict['siret']}, ci-après désigné « le Prestataire »,</p>
        <p>ET</p>
        <p><strong>{d_dict.get('client_societe') or 'Particulier'}</strong>, {d_dict.get('client_prenom', '')} {d_dict.get('client_nom', '')}, dont l'adresse est {d_dict.get('client_adresse', '')}, ci-après désigné « le Client »,</p>
        <p><em>Ci-après désignés ensemble « les Parties ».</em></p>

        <h2>Article 1 : Objet</h2>
        <p>Le présent accord a pour objet de définir les conditions dans lesquelles les Parties s'engagent à préserver la confidentialité des informations échangées dans le cadre du projet objet du devis n° {d_dict['numero_devis']}, tant lors des échanges précontractuels que pendant l'exécution de la prestation.</p>

        <h2>Article 2 : Informations confidentielles</h2>
        <p>Sont considérées comme confidentielles toutes les informations, quelle qu'en soit la forme, communiquées par l'une des Parties à l'autre à l'occasion du projet, notamment les informations commerciales, financières ou stratégiques, les spécifications fonctionnelles et techniques, les données clients ou salariés, et tout code source ou savoir-faire communiqué. Ne sont pas confidentielles les informations déjà connues, publiques sans manquement au présent accord, reçues licitement d'un tiers, ou dont la divulgation est requise par la loi.</p>

        <h2>Article 3 : Obligations des Parties</h2>
        <p>Chaque Partie s'engage à ne divulguer les informations confidentielles de l'autre Partie à aucun tiers sans accord écrit préalable, à ne les utiliser que dans le cadre du projet, à en limiter l'accès aux personnes ayant besoin d'en connaître, et à mettre en œuvre des mesures de protection raisonnables équivalentes à celles appliquées à ses propres informations sensibles.</p>

        <h2>Article 4 : Durée</h2>
        <p>L'obligation de confidentialité s'applique pendant toute la durée de la relation contractuelle et perdure pendant trois (3) ans à compter du terme de celle-ci, quelle qu'en soit la cause.</p>

        <h2>Article 5 : Absence de transfert de droits</h2>
        <p>La communication d'informations confidentielles au titre du présent accord ne confère à la Partie réceptrice aucun droit, licence ou titre de propriété intellectuelle sur ces informations.</p>

        <h2>Article 6 : Droit applicable</h2>
        <p>Le présent accord est soumis au droit français, dans les conditions de compétence juridictionnelle prévues à l'Article 14 des CGV (Annexe 2).</p>

        <div class="signatures-container">
            <p><strong>Fait en deux exemplaires, le _____________________</strong></p>
            <div class="sig-box-left">Pour le Prestataire<br>Signature :</div>
            <div class="sig-box-right">Pour le Client<br>Signature :</div>
            <div class="clear"></div>
        </div>
    </div>
</body>
</html>"""


# ===========================================================================
# 2. SCOPE-SHIELD : GÉNÉRATEUR D'AVENANT CONTRACTUEL FLASH
# ===========================================================================
def generate_avenant_flash_html(avenant_row, devis_row, ent):
    avn = dict(avenant_row) if hasattr(avenant_row, "keys") else avenant_row
    dev = dict(devis_row) if hasattr(devis_row, "keys") else devis_row
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()

    prix_supp = float(avn["impact_prix_ht"])
    delai_supp = int(avn["impact_delai_jours"])
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Avenant_{avn['numero_avenant']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #333; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; }}
        h1 {{ font-size: 19px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #CBD5E0; padding: 10px; font-size: 12px; text-align: left; }}
        th {{ background: #E7EEE6; color: #1A365D; }}
        .sig {{ width: 45%; height: 75px; border: 1px dashed #A0AEC0; padding: 8px; font-size: 11px; float: left; margin-top: 30px; }}
        .sig-r {{ float: right; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {logo_html}
        <h2>{ent_d['nom']} — AVENANT CONTRACTUEL</h2>
        <p style="font-size: 11px; color: #666;">SIRET : {ent_d['siret']} | Rattaché au Devis n° <strong>{dev['numero_devis']}</strong></p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 15px 0;">
        <h1>AVENANT N° {avn['numero_avenant']}</h1>
        <p><strong>Date d'émission :</strong> {avn['date_avenant']}</p>
        <p><strong>Client bénéficiaire :</strong> {dev.get('client_societe') or 'Particulier'} ({dev.get('client_prenom', '')} {dev.get('client_nom', '')})</p>
        
        <h3>1. Objet de la modification de périmètre (Scope-Shield)</h3>
        <p style="background: #F8FAFC; padding: 12px; border-left: 4px solid #6E8A85; border-radius: 4px;">
            {avn['description_demande']}
        </p>

        <h3>2. Impacts financiers et sur les délais</h3>
        <table>
            <tr><th>Nature de l'impact</th><th>Détails & Ajustements</th></tr>
            <tr><td><strong>Impact Financier</strong></td><td><strong>+{prix_supp:.2f} € H.T.</strong> ajoutés au solde final de livraison</td></tr>
            <tr><td><strong>Impact Délais de Réalisation</strong></td><td><strong>+{delai_supp} jour(s) ouvré(s)</strong> ajoutés au calendrier initial</td></tr>
        </table>
        <p style="font-size: 11px; color: #555;">La signature du présent avenant confirme l'accord exprès du Client pour ces travaux complémentaires et valide la réévaluation de la facture de solde correspondante.</p>
        
        <div class="sig">Pour le Prestataire :<br>Date & Signature</div>
        <div class="sig sig-r">Pour le Client (Bon pour accord) :<br>Date & Signature</div>
        <div style="clear: both;"></div>
    </div></body></html>"""


# ===========================================================================
# 3. COCKPIT MCO : RAPPORT MENSUEL DE SANTÉ DES FLUX
# ===========================================================================
def generate_rapport_mco_html(mco_row, client_row, ent):
    m = dict(mco_row) if hasattr(mco_row, "keys") else mco_row
    c = dict(client_row) if hasattr(client_row, "keys") else client_row
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Rapport_MCO_{m['mois']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #333; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; }}
        h1 {{ font-size: 18px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 6px; }}
        .kpi-box {{ display: inline-block; width: 31%; background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 12px; text-align: center; box-sizing: border-box; margin-right: 2%; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {logo_html}
        <h2>{ent_d['nom']} — SUPERVISION & MAINTIEN EN CONDITION OPÉRATIONNELLE</h2>
        <p style="font-size: 11px; color: #666;">Rapport technique mensuel d'exploitation — Période : <strong>{m['mois']}</strong></p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 15px 0;">
        <h1>RAPPORT DE SANTÉ DES FLUX & CONNECTEURS</h1>
        <p><strong>Client souscrit :</strong> {c.get('societe') or 'Particulier'} ({c.get('prenom', '')} {c.get('nom', '')})</p>
        
        <div style="margin: 25px 0;">
            <div class="kpi-box"><p style="font-size: 11px; margin: 0; color: #666;">FLUX SUPERVISÉS</p><h2 style="margin: 5px 0; color: #2B6CB0;">{m['flux_surveilles']} passerelles</h2></div>
            <div class="kpi-box"><p style="font-size: 11px; margin: 0; color: #666;">OPÉRATIONS TRAITÉES</p><h2 style="margin: 5px 0; color: #2F855A;">{m['operations_traitees']}</h2></div>
            <div class="kpi-box" style="margin-right: 0;"><p style="font-size: 11px; margin: 0; color: #666;">DISPONIBILITÉ GLOBALE</p><h2 style="margin: 5px 0; color: #6E8A85;">{m['statut_sante']}</h2></div>
        </div>

        <h3>Détails des interventions & contrôle de sécurité</h3>
        <p style="background: #F8FAFC; padding: 15px; border-radius: 6px; font-size: 12px; line-height: 1.6;">
            • <strong>Incidents préventifs neutralisés :</strong> {m['incidents_resolus']} anomalie(s) d'API ou de webhook corrigée(s) avant impact métier.<br>
            • <strong>Contrôle des quotas :</strong> Aucune saturation de connecteurs détectée sur la période.<br>
            • <strong>Commentaires de l'expert :</strong> {m.get('commentaires') or 'L\'ensemble des flux fonctionne selon les spécifications nominales du contrat SLA.'}
        </p>
        <p style="font-size: 10px; color: #777; margin-top: 40px; border-top: 1px solid #CBD5E0; padding-top: 10px;">Document généré automatiquement par Themis ERP — Justificatif contractuel d'exécution de la prestation de maintenance.</p>
    </div></body></html>"""


# ===========================================================================
# 4. GESTION DES SECRETS : ATTESTATION DE RÉVOCATION & DÉCHARGE RGPD
# ===========================================================================
def generate_revocation_secrets_html(client_row, secrets_list, ent):
    c = dict(client_row) if hasattr(client_row, "keys") else client_row
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()

    rows_html = ""
    for s in secrets_list:
        s_d = dict(s) if hasattr(s, "keys") else s
        rows_html += f"<tr><td><strong>{s_d['service_nom']}</strong></td><td>{s_d['type_identifiant']}</td><td style='color: green; font-weight: bold;'>{s_d['statut']}</td><td>{s_d['date_ajout']}</td></tr>"

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Decharge_Securite_{c['id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #333; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; }}
        h1 {{ font-size: 18px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #CBD5E0; padding: 8px 10px; font-size: 11.5px; text-align: left; }}
        th {{ background: #E7EEE6; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {logo_html}
        <h2>{ent_d['nom']} — PROTOCOLE DE SÉCURITÉ & RESTITUTION D'ACCÈS</h2>
        <p style="font-size: 11px; color: #666;">Conformité RGPD et clôture d'habilitation technique</p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 15px 0;">
        <h1>ATTESTATION DE FIN D'HABILITATION & GESTION DES SECRETS</h1>
        <p><strong>Destinataire :</strong> {c.get('societe') or 'Client'} ({c.get('prenom', '')} {c.get('nom', '')})</p>
        <p>Dans le cadre de la livraison définitive de votre solution, le Prestataire certifie avoir clôturé ses accès opérationnels et vous invite à procéder à la révocation ou régénération des clés API suivantes :</p>
        <table>
            <tr><th>Service / Plateforme</th><th>Type d'accès</th><th>Statut chez le prestataire</th><th>Date de configuration</th></tr>
            {rows_html if rows_html else "<tr><td colspan='4'>Aucun secret enregistré pour ce client.</td></tr>"}
        </table>
        <p style="font-size: 11px; color: #555; line-height: 1.5;">Le Prestataire décline toute responsabilité en cas de maintien actif de clés partagées non révoquées au-delà de 15 jours suivant la signature du procès-verbal de recette.</p>
        <div style="margin-top: 40px; font-size: 12px; font-weight: bold;">Pour {ent_d['nom']} — Le Responsable Technique</div>
    </div></body></html>"""


# ===========================================================================
# 5. LIVRABLES TECHNIQUES : ARCHITECTURE BLUEPRINT (SCHÉMA FLUX A4)
# ===========================================================================
def generate_blueprint_html(bp_row, client_nom, ent):
    bp = dict(bp_row) if hasattr(bp_row, "keys") else bp_row
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()

    try:
        etapes = json.loads(bp["etapes_json"]) if bp["etapes_json"] else []
    except Exception:
        etapes = []

    steps_html = ""
    for idx, step in enumerate(etapes):
        steps_html += f"""
        <div style="background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
            <strong style="color: #2B6CB0;">Étape {idx+1} :</strong> {step}
        </div>
        """

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Blueprint_{bp['id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #333; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; }}
        h1 {{ font-size: 18px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 6px; }}
        .diagram-box {{ background: #EDF2F7; border: 2px dashed #A0AEC0; border-radius: 8px; padding: 15px; text-align: center; margin: 20px 0; font-weight: bold; color: #2D3748; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {logo_html}
        <h2>{ent_d['nom']} — DOSSIER D'INGÉNIERIE LOGIQUE</h2>
        <p style="font-size: 11px; color: #666;">Document technique d'architecture logicielle & flux de données</p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 15px 0;">
        <h1>BLUEPRINT : {bp['nom_flux']}</h1>
        <p><strong>Bénéficiaire :</strong> {client_nom}</p>
        
        <h3>1. Schéma directeur du flux (Pipeline)</h3>
        <div class="diagram-box">
            ⚡ DÉCLENCHEUR : {bp['declencheur']}<br>
            ⬇️ (Transmission sécurisée & Mapping)<br>
            ⚙️ TRAITEMENTS MÉTIER & ACTIONS FINALES
        </div>

        <h3>2. Description séquentielle des étapes d'automatisation</h3>
        {steps_html if steps_html else "<p>Aucune étape détaillée n'a été saisie.</p>"}

        <h3>3. Dictionnaire & intégrité des données mappées</h3>
        <p style="background: #FFF5F5; border-left: 4px solid #E53E3E; padding: 10px; font-size: 11.5px; border-radius: 4px;">
            {bp.get('donnees_mappees') or 'Validation de schéma JSON, déduplication et chiffrement des flux en transit appliqués.'}
        </p>
        <p style="font-size: 10px; color: #777; margin-top: 40px; border-top: 1px solid #CBD5E0; padding-top: 10px;">Livrable d'ingénierie remis au Client avec le Procès-Verbal de Recette — Droits d'exploitation concédés selon Art. 8 des CGV.</p>
    </div></body></html>"""


# ===========================================================================
# 6. LIVRET D'ACCUEIL & GUIDE D'EXPLOITATION OFFICIEL THEMIS ERP (A4 / PDF)
# ===========================================================================
def generate_livret_accueil_html(ent):
    """Génère le livret d'accueil imprimable reprenant toutes les fonctions modernes de Themis."""
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Livret_Accueil_Themis_ERP</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #2D3748; line-height: 1.6; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; margin-bottom: 25px; page-break-after: always; }}
        h1 {{ font-size: 19px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 6px; margin-top: 0; }}
        h2 {{ font-size: 14px; color: #2B6CB0; margin-top: 16px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }}
        p, li {{ font-size: 11px; text-align: justify; }}
        .box {{ background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 10px 14px; margin: 10px 0; font-size: 11px; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; margin: 0; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer le Livret en PDF</button>
    </div>
    
    <div class="page">
        {logo_html}
        <h1>THEMIS ERP — MANUEL D'EXPLOITATION & LIVRET D'ACCUEIL</h1>
        <p><strong>Édition Micro-Entreprise & B2B</strong> | Prestataire : {ent_d['nom']} | Version 3.5</p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 12px 0;">
        
        <h2>1. Philosophie & Piliers Juridiques</h2>
        <p>Themis ERP est spécialement conçu pour sécuriser et automatiser l'activité des prestataires du numérique, ingénieurs et agences d'automatisation. Il verrouille la facturation et protège l'entreprise contre le travail non rémunéré et les décalages de trésorerie.</p>
        
        <h2>2. Tableau de Bord & Radar de Vigilance Trésorerie</h2>
        <div class="box">
            • <strong>Radar de Vigilance en Temps Réel :</strong> Détecte immédiatement les acomptes non facturés, les soldes à émettre, les abonnements échus et les factures en retard.<br>
            • <strong>Jauges Légales :</strong> Surveillance permanente de la Franchise en base de TVA (36 800 €) et du Plafond BNC (77 700 €).<br>
            • <strong>Échéancier Trimestriel T1-T4 :</strong> Calcul en direct des cotisations URSSAF (21,2 %) et du versement libératoire IR (2,2 %) sur les encaissements réels.<br>
            • <strong>Synchronisation Comptable :</strong> Le passage en « Facture Acquittée » alimente instantanément le Livre des Recettes ; un retour en « Facture Émise » purge immédiatement la ligne pour éviter toute fausse déclaration.
        </div>

        <h2>3. Recouvrement Automatisé Make & Journal d'Audit</h2>
        <p>Themis dispose d'un moteur de recouvrement graduel connecté à Make :</p>
        <ul>
            <li><strong>Rédaction Intégrale par Themis :</strong> Themis génère lui-même les courriers officiels en HTML stylisé (Niveau 1 : Rappel courtois, Niveau 2 : Pénalités L441-10 + 40 €, Niveau 3 : Mise en demeure avec suspension de contrat).</li>
            <li><strong>Expédition Make & Accusé :</strong> Make reçoit l'email prêt à l'envoi et renvoie un accusé de réception instantané (200 OK).</li>
            <li><strong>Journal des Relances :</strong> Suivi chronologique de chaque relance avec traçabilité de la <strong>Date d'acquittement</strong> effective et relecture de l'email expédié en un clic.</li>
        </ul>

        <h2>4. Coordonnées Bancaires & Règlements</h2>
        <p>Toutes les pièces commerciales (Devis, Bons de commande et Factures) intègrent un <strong>cartouche RIB officiel</strong> avec IBAN, BIC, Banque et mention automatique du libellé obligatoire pour garantir un paiement sans friction.</p>
    </div>

    <div class="page">
        <h2>5. Portefeuille Client 360° & Coffre-Fort de Secrets</h2>
        <div class="box">
            • <strong>Portefeuille Unifié :</strong> Vision instantanée du CA total encaissé (Valeur Vie / LTV), des abonnements mensuels actifs (€/mois) et de la santé comptable de chaque client.<br>
            • <strong>Fiche Modale Popup 360° :</strong> Clic sur « Inspecter 360° » ouvrant immédiatement le dossier en 4 onglets : Travaux & Devis, Abonnements & MCO, Factures & Règlements, Clés API & Sécurité.<br>
            • <strong>Décharge RGPD :</strong> Édition en 1 clic du protocole de restitution et de révocation des clés API en fin de mission.
        </div>

        <h2>6. Moteur Fiscal & Bascule TVA (Guadeloupe 8,5 % / Métropole 20 %)</h2>
        <p>Themis s'adapte à la croissance de votre chiffre d'affaires :</p>
        <ul>
            <li><strong>Franchise en Base (Défaut) :</strong> Application stricte de la mention légale <em>« TVA non applicable, art. 293 B du CGI »</em>.</li>
            <li><strong>Bascule Assujetti en 1 clic :</strong> En cas de dépassement du seuil de 36 800 €, Themis calcule automatiquement le montant H.T., la TVA (8,5 % DOM Guadeloupe ou 20 % Métropole) et le Net à Payer T.T.C., avec affichage du N° de TVA Intracommunautaire.</li>
        </ul>

        <h2>7. Factur-X (Réforme 2026-2027) & Conformité Éditeur Art. 286 du CGI</h2>
        <div class="box">
            • <strong>Format Hybride Factur-X :</strong> Devant chaque facture, un bouton permet d'extraire le fichier XML normalisé (norme européenne CII) prêt pour Chorus Pro et le Portail Public de Facturation.<br>
            • <strong>Attestation Éditeur Officielle :</strong> Génération de l'attestation formelle d'inaltérabilité, de sécurisation et de conservation au titre de l'Art. 286 du CGI pour vous prémunir de tout redressement lors d'un contrôle fiscal.
        </div>

        <h2>8. Sauvegarde Globale & Exports Comptables</h2>
        <p>Protection absolue de vos données d'entreprise :</p>
        <ul>
            <li><strong>Sauvegarde ZIP en 1 Clic :</strong> Crée une archive autonome horodatée contenant la base SQLite (`devis_suivi.db`) et tous les scans de contrats signés.</li>
            <li><strong>Exports Officiels Excel & CSV :</strong> Extraction du Livre des Recettes et du Registre des Dépenses au format normalisé de l'administration fiscale.</li>
        </ul>

        <div style="margin-top: 35px; border-top: 1px solid #CBD5E0; padding-top: 10px; font-size: 10.5px; color: #777;">
            © Dhamusoft — Tous droits réservés • Guide d'exploitation Themis ERP Suite.
        </div>
    </div>
    </body></html>"""
    
# ===========================================================================
# [FONCTIONS AJOUTÉES - ÉTAPE 5] : Attestation Art. 286 CGI & Factur-X XML
# ===========================================================================

def generate_attestation_conformite_html(ent):
    """Génère l'Attestation formelle de conformité de l'éditeur au titre de l'Art. 286, I, 3° bis du CGI."""
    ent_d = dict(ent) if hasattr(ent, "keys") else ent
    logo_html = get_logo_html()
    today_fr = datetime.date.today().strftime("%d/%m/%Y")

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Attestation_Conformite_Art286_CGI</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; padding: 30px; background: #FAF7F2; color: #2D3748; line-height: 1.6; }}
        .page {{ width: 210mm; min-height: 270mm; margin: auto; background: white; padding: 25mm 20mm; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); box-sizing: border-box; }}
        h1 {{ font-size: 18px; color: #1A365D; border-bottom: 2px solid #6E8A85; padding-bottom: 8px; text-transform: uppercase; text-align: center; }}
        .legal-box {{ background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 14px; margin: 18px 0; font-size: 11.5px; }}
        .pillar {{ margin: 12px 0; font-size: 12px; }}
        .sig-box {{ margin-top: 40px; float: right; width: 260px; border: 1px dashed #A0AEC0; padding: 12px; text-align: center; font-size: 11px; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; width: 100%; border: none; }} .no-print {{ display: none; }} }}
    </style></head><body>
    <div class="no-print" style="text-align: center; margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 25px; background: #6E8A85; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Imprimer ou Enregistrer en PDF</button>
    </div>
    <div class="page">
        {logo_html}
        <p style="font-size: 11px; color: #718096; margin: 0;">RÉPUBLIQUE FRANÇAISE — MINISTÈRE DE L'ÉCONOMIE ET DES FINANCES</p>
        <p style="font-size: 11px; color: #718096; margin: 0;">Code Général des Impôts — Article 286, I, 3° bis</p>
        <hr style="border: 0; border-top: 1px solid #CBD5E0; margin: 15px 0;">
        
        <h1>ATTESTATION INDIVIDUELLE DE CONFORMITÉ DE L'ÉDITEUR</h1>
        <p style="text-align: center; font-size: 12px; font-weight: bold; color: #2B6CB0;">Système d'Enregistrement et d'Encaissement Themis ERP Suite (Version 3.0)</p>

        <div class="legal-box">
            <strong>Éditeur et Concepteur du Logiciel :</strong><br>
            Raison sociale : <strong>{ent_d['nom']}</strong><br>
            Siège social : {ent_d['adresse']}<br>
            SIRET : {ent_d['siret']} | Forme juridique : {ent_d['forme_juridique']}
        </div>

        <p style="font-size: 12px; text-align: justify;">
            Je soussigné, représentant légal de l'éditeur ci-dessus désigné, certifie sur l'honneur que le progiciel de facturation et de gestion commerciale <strong>Themis ERP Suite</strong> satisfait à l'ensemble des conditions d'<strong>inaltérabilité, de sécurisation, de conservation et d'archivage des données</strong> prévues par l'article 286, I, 3° bis du Code Général des Impôts (loi anti-fraude n° 2015-1785 de finances pour 2016).
        </p>

        <div class="pillar">
            <strong>1. Condition d'Inaltérabilité :</strong><br>
            Le logiciel interdit formellement la modification ou la suppression directe des factures dès leur émission. Toute rectification commerciale fait l'objet d'une facture d'avoir rectificative dûment référencée et chaînée.
        </div>
        <div class="pillar">
            <strong>2. Condition de Sécurisation :</strong><br>
            Toutes les transactions, encaissements et pièces de facturation sont tracés chronologiquement sans rupture de séquence avec horodatage strict et contrôle de doublons.
        </div>
        <div class="pillar">
            <strong>3. Condition de Conservation & Archivage :</strong><br>
            Le système assure la conservation intégrale des données de facturation et des règlements dans le Livre des Recettes officiel sur la durée légale de six (6) ans requise par l'administration fiscale, avec possibilité d'exportation standardisée.
        </div>

        <p style="font-size: 11px; color: #666; margin-top: 25px;">
            La présente attestation est délivrée pour valoir ce que de droit en cas de contrôle de l'administration fiscale.
        </p>

        <div class="sig-box">
            Fait à {ent_d['adresse'].split(',')[-1].strip()}, le {today_fr}<br><br>
            <strong>Pour l'Éditeur Themis ERP</strong><br>
            Cachet et Signature autorisée :
        </div>
    </div></body></html>"""


def generate_facturx_xml(facture_row, ent):
    """Génère la chaîne XML conforme à la norme Factur-X / CII (Profil Basic/Comfort)."""
    f = dict(facture_row) if hasattr(facture_row, "keys") else facture_row
    ent_d = dict(ent) if hasattr(ent, "keys") else ent

    montant_ht = float(f["montant_ht"])
    is_tva = (ent_d.get("assujetti_tva") == 1)
    taux_tva = float(ent_d.get("taux_tva_defaut") or 8.5) if is_tva else 0.0
    montant_tva = (montant_ht * (taux_tva / 100.0)) if is_tva else 0.0
    montant_ttc = montant_ht + montant_tva
    issue_date_nodash = f["date_facture"].replace("-", "")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                          xmlns:cram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                          xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
    <rsm:ExchangedDocumentContext>
        <cram:GuidelineSpecifiedDocumentContextParameter>
            <cram:ID>urn:factur-x.eu:1p0:basic</cram:ID>
        </cram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>
    <rsm:ExchangedDocument>
        <cram:ID>{f['numero_facture']}</cram:ID>
        <cram:TypeCode>380</cram:TypeCode>
        <cram:IssueDateTime>
            <udt:DateTimeString format="102">{issue_date_nodash}</udt:DateTimeString>
        </cram:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <cram:ApplicableHeaderTradeAgreement>
            <cram:SellerTradeParty>
                <cram:Name>{ent_d['nom']}</cram:Name>
                <cram:SpecifiedLegalOrganization>
                    <cram:ID schemeID="0002">{ent_d['siret']}</cram:ID>
                </cram:SpecifiedLegalOrganization>
            </cram:SellerTradeParty>
            <cram:BuyerTradeParty>
                <cram:Name>{f.get('client_societe') or f.get('client_nom', 'Client')}</cram:Name>
            </cram:BuyerTradeParty>
        </cram:ApplicableHeaderTradeAgreement>
        <cram:ApplicableHeaderTradeSettlement>
            <cram:InvoiceCurrencyCode>EUR</cram:InvoiceCurrencyCode>
            <cram:SpecifiedTradeSettlementPaymentMeans>
                <cram:TypeCode>42</cram:TypeCode>
                <cram:PayeePartyCreditorFinancialAccount>
                    <cram:IBANID>{ent_d.get('iban', '')}</cram:IBANID>
                </cram:PayeePartyCreditorFinancialAccount>
            </cram:SpecifiedTradeSettlementPaymentMeans>
            <cram:SpecifiedTradeSettlementHeaderMonetarySummation>
                <cram:LineTotalAmount>{montant_ht:.2f}</cram:LineTotalAmount>
                <cram:TaxBasisTotalAmount>{montant_ht:.2f}</cram:TaxBasisTotalAmount>
                <cram:TaxTotalAmount currencyID="EUR">{montant_tva:.2f}</cram:TaxTotalAmount>
                <cram:GrandTotalAmount>{montant_ttc:.2f}</cram:GrandTotalAmount>
                <cram:DuePayableAmount>{montant_ttc:.2f}</cram:DuePayableAmount>
            </cram:SpecifiedTradeSettlementHeaderMonetarySummation>
        </cram:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""    
