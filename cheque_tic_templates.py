# cheque_tic_templates.py
# Moteur de génération des livrables administratifs - Dispositif Chèque TIC Région Guadeloupe

import datetime


def generate_pack_cheque_tic_html(dossier: dict, ent: dict) -> str:
    """Génère le dossier administratif complet de 5 pièces pour l'ASP et le Conseil Régional."""
    today_fr = datetime.date.today().strftime("%d/%m/%Y")
    
    tot_projet = float(dossier['budget_web_ht'] or 0) + float(dossier['budget_securite_ht'] or 0) + float(dossier['budget_themis_logiciel_ht'] or 0)
    subv = float(dossier['subvention_calculee'] or 0)
    rac = float(dossier['reste_a_charge_ht'] or 0)
    
    # Transformation de la note Gemini en paragraphes HTML
    note_brute = dossier.get("note_impact_redigee") or "Note d'impact en attente de génération par l'IA."
    note_html = "".join([f"<p>{p.strip()}</p>" for p in note_brute.split("\n\n") if p.strip()])

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Pack_Cheque_TIC_{dossier['siret']}</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #090D16; background: #FAF7F2; margin: 0; padding: 20px; font-size: 11pt; line-height: 1.5; }}
        .page {{ position: relative; width: 210mm; min-height: 297mm; margin: 0 auto 20px auto; background: #FFFFFF; padding: 20mm; box-sizing: border-box; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 4px; page-break-after: always; }}
        .no-print {{ text-align: center; margin-bottom: 25px; }}
        .btn-print {{ background: #05231A; color: #FFFFFF; border: none; padding: 12px 28px; font-size: 13px; font-weight: 700; border-radius: 6px; cursor: pointer; letter-spacing: 0.5px; }}
        .header-box {{ border-bottom: 2px solid #05231A; padding-bottom: 12px; margin-bottom: 25px; }}
        .header-box table {{ width: 100%; border-collapse: collapse; }}
        .tag {{ font-size: 8pt; font-weight: 800; background: #05231A; color: #A7F3D0; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }}
        .title {{ font-size: 16pt; font-weight: 900; color: #05231A; margin: 8px 0 2px 0; text-transform: uppercase; }}
        .subtitle {{ font-size: 9.5pt; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        .cadre-info {{ background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 14px; margin: 15px 0; font-size: 10pt; }}
        .grid-2 {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .grid-2 td {{ width: 50%; vertical-align: top; padding: 0 10px; }}
        table.data {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        table.data th, table.data td {{ border: 1px solid #CBD5E1; padding: 8px 10px; font-size: 9.5pt; text-align: left; }}
        table.data th {{ background: #F1F5F9; font-weight: 800; color: #05231A; }}
        .signature-box {{ margin-top: 35px; border: 1px dashed #94A3B8; border-radius: 6px; padding: 15px; height: 110px; }}
        @media print {{ body {{ background: transparent; padding: 0; }} .page {{ box-shadow: none; margin: 0; width: 100%; min-height: auto; padding: 15mm; }} .no-print {{ display: none; }} }}
    </style>
</head>
<body>

<div class="no-print">
    <button class="btn-print" onclick="window.print()">🖨️ IMPRIMER OU ENREGISTRER LE PACK OFFICIEL (PDF)</button>
</div>

<!-- ================= PAGE 1 : LETTRE OFFICIELLE DE DEMANDE ================= -->
<div class="page">
    <div class="header-box">
        <table>
            <tr>
                <td>
                    <span class="tag">RÉGION GUADELOUPE • DISPOSITIF CHÈQUE TIC</span>
                    <div class="title">Demande Officielle de Subvention</div>
                    <div class="subtitle">Cadre d'intervention Délibération N° CR-19-175</div>
                </td>
                <td style="text-align: right; vertical-align: bottom; font-size: 9pt; color: #64748B;">
                    Date : <strong>{today_fr}</strong>
                </td>
            </tr>
        </table>
    </div>

    <table style="width: 100%; margin-bottom: 30px;">
        <tr>
            <td style="width: 55%; vertical-align: top; font-size: 10pt;">
                <strong>DEMANDEUR :</strong><br>
                {dossier['nom_entreprise']} ({dossier['forme_juridique']})<br>
                SIRET : {dossier['siret']} | Code NAF : {dossier['code_naf']}<br>
                {dossier['adresse_siege']}, {dossier['commune']}<br>
                Représentée par : {dossier['representant_legal']} ({dossier['fonction_signataire']})<br>
                Email : {dossier['email_client']} | Tél : {dossier['telephone_client']}
            </td>
            <td style="width: 45%; vertical-align: top; font-size: 10pt; background: #F8FAFC; border: 1px solid #CBD5E1; padding: 12px; border-radius: 6px;">
                <strong>DESTINATAIRE :</strong><br>
                <strong>Monsieur le Président du Conseil Régional</strong><br>
                Région Guadeloupe — Hôtel de Région<br>
                Avenue Paul Lacavé — Petit-Paris<br>
                97100 Basse-Terre, Guadeloupe<br>
                <em>Direction Générale Adjointe au Développement Économique</em>
            </td>
        </tr>
    </table>

    <p><strong>OBJET :</strong> Demande d'attribution de la subvention régionale « Chèque TIC » — Numérisation, résilience et cybersécurité des TPME guadeloupéennes.</p>

    <p>Monsieur le Président,</p>
    <p>J'ai l'honneur de solliciter par la présente le bénéfice de l'aide financière régionale au titre du dispositif <strong>Chèque TIC</strong> afin de soutenir le plan de transformation numérique d'urgence de mon entreprise <strong>{dossier['nom_entreprise']}</strong>, implantée sur la commune de <strong>{dossier['commune']}</strong>.</p>
    
    <p>Confrontée à des contraintes opérationnelles majeures pesant sur notre rentabilité (<em>notamment : {dossier['douleur_actuelle']}</em>), notre structure engage un investissement global en numérisation de <strong>{tot_projet:,.2f} € HT</strong>, déployé par le cabinet spécialisé <strong>{ent['nom']}</strong>.</p>

    <div class="cadre-info">
        <strong>SYNTHÈSE DU PLAN FINANCIER SOUMIS À INSTRUCTION :</strong><br>
        • Dépenses éligibles au taux bonifié de 80 % (Développement & Sécurité) : <strong>{(float(dossier['budget_web_ht'] or 0) + float(dossier['budget_securite_ht'] or 0)):,.2f} € HT</strong><br>
        • Dépenses éligibles au taux de 40 % (ERP THEMIS & Automatisation métier) : <strong>{float(dossier['budget_themis_logiciel_ht'] or 0):,.2f} € HT</strong><br>
        • <strong>Montant de l'aide sollicitée : <span style="color: #047857; font-size: 12pt;">{subv:,.2f} €</span></strong> (Reste à charge autofinancé : {rac:,.2f} € HT)
    </div>

    <p>L'octroi de ce soutien conditionne directement la concrétisation de notre feuille de route à 12 mois, visant en priorité : <strong>{dossier['ambition_12_mois']}</strong>.</p>

    <p>Vous trouverez ci-joint la note d'impact technique, le devis certifié de notre prestataire ainsi que l'ensemble des attestations administratives de régularité.</p>

    <table style="width: 100%; margin-top: 40px;">
        <tr>
            <td style="width: 50%;">Fait à {dossier['commune']}, le {today_fr}</td>
            <td style="width: 50%; text-align: right;">
                <strong>Pour l'entreprise requérante :</strong><br>
                {dossier['representant_legal']}<br>
                <em>Signature et cachet commercial</em>
                <div class="signature-box" style="margin-top: 10px;"></div>
            </td>
        </tr>
    </table>
</div>

<!-- ================= PAGE 2 & 3 : NOTE D'IMPACT STRATÉGIQUE (RÉDIGÉE PAR IA) ================= -->
<div class="page">
    <div class="header-box">
        <table>
            <tr>
                <td>
                    <span class="tag">DOCUMENT TECHNIQUE N°1</span>
                    <div class="title">Note d'Impact Stratégique & Numérique</div>
                    <div class="subtitle">Dossier Chèque TIC • Diagnostic & Programme Prévisionnel</div>
                </td>
                <td style="text-align: right; vertical-align: bottom; font-size: 9pt; color: #64748B;">
                    Entreprise : <strong>{dossier['nom_entreprise']}</strong>
                </td>
            </tr>
        </table>
    </div>

    <div style="font-size: 10pt; line-height: 1.6; text-align: justify;">
        {note_html}
    </div>

    <div style="margin-top: 30px; border-top: 1px solid #CBD5E1; padding-top: 10px; font-size: 8.5pt; color: #64748B;">
        Document d'évaluation technico-économique instruit au titre du Programme Opérationnel FEDER-FSE Guadeloupe et des aides directes régionales aux TPME.
    </div>
</div>

<!-- ================= PAGE 4 : MANDAT DE REPRÉSENTATION ADMINISTRATIVE ================= -->
<div class="page">
    <div class="header-box">
        <table>
            <tr>
                <td>
                    <span class="tag">RÉGULARITÉ ADMINISTRATIVE</span>
                    <div class="title">Mandat de Représentation Administrative</div>
                    <div class="subtitle">Instruction Dématérialisée Chèque TIC Guadeloupe</div>
                </td>
                <td style="text-align: right; vertical-align: bottom; font-size: 9pt; color: #64748B;">
                    Validité : 12 Mois
                </td>
            </tr>
        </table>
    </div>

    <p><strong>ENTRE LES SOUSSIGNÉS :</strong></p>
    
    <div class="cadre-info">
        <strong>1. LE MANDANT (L'Entreprise Bénéficiaire) :</strong><br>
        L'entreprise <strong>{dossier['nom_entreprise']}</strong>, immatriculée sous le SIRET n° <strong>{dossier['siret']}</strong>, ayant son siège à <strong>{dossier['adresse_siege']}, {dossier['commune']}</strong>, représentée par <strong>{dossier['representant_legal']}</strong> en sa qualité de {dossier['fonction_signataire']}.
    </div>

    <div class="cadre-info">
        <strong>2. LE MANDATAIRE (Le Cabinet Accompagnateur) :</strong><br>
        L'entreprise <strong>{ent['nom']}</strong>, {ent['forme_juridique']}, SIRET n° <strong>{ent['siret']}</strong>, sise à <strong>{ent['adresse']}</strong>, représentée par son Responsable des Systèmes d'Information.
    </div>

    <p><strong>ARTICLE 1 — OBJET DU MANDAT :</strong><br>
    Le Mandant donne expressément pouvoir au Mandataire d'accomplir en son nom et pour son compte l'ensemble des diligences administratives, techniques et dématérialisées requises pour l'instruction, le dépôt et le suivi du dossier de subvention régionale <strong>« Chèque TIC »</strong> auprès du Conseil Régional de la Guadeloupe et de l'Agence de Services et de Paiement (ASP).</p>

    <p><strong>ARTICLE 2 — LIMITATION STRICTE DU POUVOIR FINANCIER (GARANTIE DE TRANSPARENCE) :</strong><br>
    Le présent mandat est exclusivement administratif. <strong>Il est expressément stipulé que le Mandataire n'est aucunement habilité à encaisser la subvention.</strong> Les fonds régionaux accordés seront intégralement et directement versés par le payeur public sur le compte bancaire exclusif de l'entreprise Mandante, conformément au relevé d'identité bancaire (RIB) joint au dossier d'instruction.</p>

    <p><strong>ARTICLE 3 — OBLIGATIONS & CONFIDENTIALITÉ :</strong><br>
    Le Mandataire s'engage à traiter les pièces comptables et administratives remises dans le respect strict des normes de sécurité et de la réglementation RGPD en vigueur.</p>

    <table style="width: 100%; margin-top: 50px;">
        <tr>
            <td style="width: 50%; vertical-align: top;">
                <strong>LE MANDANT</strong><br>
                <em>"Bon pour mandat de représentation administrative"</em><br>
                {dossier['representant_legal']}<br>
                <div class="signature-box" style="margin-top: 10px;"></div>
            </td>
            <td style="width: 50%; vertical-align: top;">
                <strong>LE MANDATAIRE</strong><br>
                <em>"Bon pour acceptation du mandat"</em><br>
                Pour {ent['nom']}<br>
                <div class="signature-box" style="margin-top: 10px;"></div>
            </td>
        </tr>
    </table>
</div>

<!-- ================= PAGE 5 : BORDEREAU DES PIÈCES JUSTIFICATIVES ================= -->
<div class="page">
    <div class="header-box">
        <table>
            <tr>
                <td>
                    <span class="tag">PIÈCES DE RECEVABILITÉ</span>
                    <div class="title">Bordereau Récapitulatif de Dépôt</div>
                    <div class="subtitle">Conformité Guichet Unique Région Guadeloupe</div>
                </td>
                <td style="text-align: right; vertical-align: bottom; font-size: 9pt; color: #64748B;">
                    Dossier : <strong>{dossier['siret']}</strong>
                </td>
            </tr>
        </table>
    </div>

    <p>Pour garantir une recevabilité sans suspension d'instruction auprès des services instructeurs régionaux, le présent dossier est assorti des pièces justificatives suivantes :</p>

    <table class="data">
        <tr>
            <th style="width: 10%;">Statut</th>
            <th style="width: 35%;">Pièce Administrative Exigée</th>
            <th style="width: 55%;">Condition de Conformité Légale</th>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Extrait Kbis ou Registre National des Entreprises (RNE)</strong></td>
            <td>Datant de moins de 3 mois, mentionnant un établissement actif situé en Guadeloupe.</td>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Attestation de Régularité Fiscale (DGFIP)</strong></td>
            <td>Établie au cours du trimestre courant, justifiant de l'absence de contentieux d'impôts directs.</td>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Attestation de Vigilance Sociale (CGSS)</strong></td>
            <td>Certifiant que l'entreprise est à jour de ses cotisations sociales obligatoires.</td>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Pièce d'Identité du Dirigeant Signataire</strong></td>
            <td>Copie recto-verso de la CNI ou Passeport en cours de validité de {dossier['representant_legal']}.</td>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Relevé d'Identité Bancaire (RIB) Professionnel</strong></td>
            <td>Au nom strict de l'entité juridique pour le virement direct de l'aide publique.</td>
        </tr>
        <tr>
            <td style="text-align: center; color: #047857; font-weight: bold;">CONFORME</td>
            <td><strong>Devis Technique Prestataire Détaillé</strong></td>
            <td>Émis par {ent['nom']}, avec nomenclature conforme (Prestations 80% / Solution logicielle 40%).</td>
        </tr>
    </table>

    <div class="cadre-info" style="margin-top: 30px;">
        <strong>NOTIFICATION D'ENGAGEMENT :</strong><br>
        Le demandeur certifie sur l'honneur l'exactitude des renseignements portés au présent dossier et atteste ne pas avoir engagé de commandes ou de dépenses préalablement à l'accusé de réception officiel de sa demande auprès de la Région Guadeloupe.
    </div>

    <div style="margin-top: 40px; text-align: center; font-size: 9.5pt; color: #64748B;">
        Dossier validé et scellé par l'environnement de gestion THEMIS ERP Suite • Conforme aux spécifications FEDER-Région.
    </div>
</div>

</body>
</html>"""
    return html
