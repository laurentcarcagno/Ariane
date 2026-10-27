// Builds ARIANE-manuel-utilisateur.docx from the screenshots in img/ (run capture.mjs and the Excel renders first).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun, LevelFormat, Packer, PageNumber, Paragraph,
  ShadingType, Table, TableCell, TableOfContents, TableRow, TextRun, WidthType,
} from "docx";

const here = path.dirname(fileURLToPath(import.meta.url));
const NAVY = "12293A";
const CONTENT_DXA = 9638; // A4 with 2 cm margins

const p = (text, opts = {}) => new Paragraph({ spacing: { after: 120, line: 276 }, ...opts, children: runs(text) });
// **word** marks a term in bold (used for interface labels only)
const runs = (text) => text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) => t.startsWith("**") ? new TextRun({ text: t.slice(2, -2), bold: true }) : new TextRun(t));
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(t)] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: runs(t) });
const step = (t) => new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 60 }, children: runs(t) });

let figure = 0;
function fig(file, caption, widthPx = 620) {
  const data = fs.readFileSync(path.join(here, "img", file));
  const w = data.readUInt32BE(16), h = data.readUInt32BE(20); // PNG header
  figure += 1;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height: Math.round((widthPx * h) / w) },
        altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figure ${figure}. ${caption}`, italics: true, size: 18, color: "55606B" })] }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "C9D3DC" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(widths, head, rows) {
  const cell = (text, w, header) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders, margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: header ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text, bold: header, color: header ? "FFFFFF" : undefined, size: 19 })] })],
  });
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, widths[i], false)) }))],
  });
}

const cover = [
  new Paragraph({ spacing: { before: 3000, after: 120 }, children: [new TextRun({ text: "ARIANE", bold: true, size: 72, color: NAVY, characterSpacing: 120 })] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Manuel utilisateur", size: 44, color: NAVY })] }),
  new Paragraph({ spacing: { after: 600 }, children: [new TextRun({ text: "Analyse des plans de faisceau et de leur nomenclature", size: 26, color: "55606B" })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Version 1.0 du 27/10/2026", size: 22 })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Plugin Beyond Gravity", size: 22 })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Exemple traité : harnais 3500402-907", size: 22 })] }),
];

const body = [
  new Paragraph({ pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: "Sommaire", bold: true, size: 32, color: NAVY })] }),
  new TableOfContents("Sommaire", { hyperlink: true, headingStyleRange: "1-2" }),

  // 1
  h1("1. À quoi sert ARIANE"),
  p("ARIANE lit le plan d'un faisceau électrique et sa nomenclature, deux fichiers PDF. Il reconstruit la liste des connexions (la netlist) et la topologie du faisceau, puis contrôle que les deux documents disent la même chose. Le résultat s'affiche dans quatre vues et s'exporte vers Excel."),
  p("L'analyse se fait sur le serveur ARIANE de votre entreprise. Aucun service externe n'est appelé. Les PDF ne sont pas conservés : seul le résultat de l'analyse est enregistré, et il n'est visible que par les utilisateurs du même client."),
  p("ARIANE ne corrige jamais une connexion. Quand le plan est ambigu ou se contredit, la ligne concernée apparaît dans le rapport et la pin est marquée en rouge ou en orange. La décision de modifier le plan vous revient."),
  p("Chaque client dispose de son plugin, qui sait lire ses propres plans. Ce manuel décrit le plugin Beyond Gravity et s'appuie sur le harnais 3500402-907 (plan DRW3500402-907, nomenclature PL_3500402-907)."),

  // 2
  h1("2. Ouvrir l'application"),
  p("ARIANE s'ouvre dans un navigateur. La connexion passe par l'annuaire de l'entreprise (Keycloak) : vous saisissez vos identifiants sur la page de connexion, puis vous revenez sur ARIANE. Votre compte porte le nom de votre client, ce qui détermine les plugins proposés et les analyses visibles."),
  p("L'écran d'accueil comporte quatre zones (figure 1). La bande sombre du haut affiche le nom du plugin et de la référence analysée, votre client et votre identifiant, ainsi que les compteurs d'erreurs et d'alertes une fois une analyse chargée. Le panneau de gauche regroupe l'import, l'historique, la recherche et les exports. Les onglets et la vue active occupent le centre. Le panneau de droite détaille l'élément sélectionné."),
  ...fig("01-accueil.png", "Écran d'accueil, avant toute analyse."),
  p("Sur une installation de développement sans authentification, la bande du haut porte le suffixe « dev » à côté du client et la page de connexion n'apparaît pas."),

  // 3
  h1("3. Importer un plan"),
  step("Choisissez le plugin dans la liste **Plugin client**. Elle ne propose que les plugins activés pour votre client."),
  step("Déposez le plan de faisceau dans la première zone en pointillés, ou cliquez dessus pour choisir le fichier. Faites de même avec la nomenclature dans la seconde zone."),
  step("Cliquez sur **Analyser**. Le bouton reste grisé tant que les deux fichiers ne sont pas choisis."),
  ...fig("02-import.png", "Les deux PDF sont choisis, l'analyse peut commencer."),
  p("L'analyse prend quelques secondes. À la fin, ARIANE ouvre l'onglet Rapport. Si un fichier n'est pas un PDF, ou si le plugin ne l'accepte pas, un message rouge apparaît sous le bouton et rien n'est enregistré."),
  h2("3.1 Retrouver une analyse"),
  p("Chaque analyse réussie est ajoutée à la liste **Analyses précédentes** du panneau de gauche, avec sa date, son nombre d'erreurs et son nombre d'alertes. Un clic rouvre l'analyse sans relire les PDF. La croix à droite de la ligne la supprime."),
  ...fig("11-historique.png", "L'historique des analyses du client.", 300),

  // 4
  h1("4. Lire le résultat"),
  p("Les compteurs rouge et orange en haut à droite résument l'analyse. Dans l'exemple, ARIANE signale 4 erreurs et 15 alertes. Quatre onglets présentent le même résultat sous des angles différents. Une sélection faite dans un onglet reste active dans les autres : le fil choisi dans la vue Connecteurs se retrouve dans le panneau de droite."),
  h2("4.1 Rapport"),
  p("L'onglet Rapport s'ouvre en premier. La rangée de tuiles donne les quantités reconnues. L'exemple compte 8 connecteurs, 96 conducteurs regroupés en 48 paires, 48 paires routées dans le faisceau, 122 contacts pin et 114 contacts socket."),
  ...fig("03-rapport.png", "Le rapport : quantités reconnues, puis liste des contrôles."),
  p("Sous les tuiles, trois boutons **Erreur**, **Alerte** et **Info** filtrent la liste. Une erreur est une incohérence entre les documents. Une alerte demande une vérification mais ne contredit rien de façon certaine. Une info signale une donnée manquante sans conséquence sur les connexions, par exemple une quantité encore à définir dans la nomenclature."),
  p("Un clic sur une ligne ouvre la vue concernée avec la pin ou le segment sélectionné (figure 5)."),
  h2("4.2 Connecteurs"),
  p("Chaque connecteur du plan est un bloc : son repère, sa référence et ses pins disposées en rangées. Un badge **n à vérifier** apparaît dans l'en-tête du bloc quand une pin pose problème, rouge s'il s'agit d'une erreur, orange s'il ne s'agit que d'une alerte. Les pins en erreur sont entourées de rouge et portent un petit carré rouge."),
  ...fig("08-erreur.png", "Pin W du connecteur INIT B P1, ouverte depuis le rapport."),
  p("Cliquer une pin affiche à droite le fil qui l'occupe : signal, polarité, type de câble, départ, arrivée, paire associée et chemin dans le faisceau. Chaque ligne du chemin donne le segment, son diamètre en millimètres et le repère de nomenclature. Quand une pin porte plusieurs fils, un encadré orange les liste et un clic sur l'un d'eux le sélectionne. Si la pin est en erreur, un encadré rouge reprend les lignes du rapport qui la concernent."),
  p("Sous chaque bloc, ARIANE indique le nombre de places vides du connecteur. La majuscule et la minuscule d'une lettre désignent deux pins différentes : c n'est pas C, et W n'est pas w."),
  p("Le champ **Recherche** du panneau de gauche accepte un numéro de fil (907-01+), un nom de signal ou une pin. Le premier fil trouvé est sélectionné (figure 6)."),
  ...fig("09-recherche.png", "Recherche du fil 907-01+ : le chemin et les deux pins sont mis en évidence."),
  h2("4.3 Faisceau"),
  p("La vue Faisceau redessine la topologie de la feuille 1 du plan. Les six connecteurs S/C partent du haut et rejoignent les deux connecteurs INIT en bas. Les numéros rouges sont les nœuds du plan. Chaque segment porte son diamètre en millimètres et le repère de la nomenclature, par exemple « Ø12.5 · 09 »."),
  ...fig("04-faisceau.png", "Topologie du faisceau. Les pastilles sur les connecteurs comptent les points à vérifier."),
  p("Quand un fil est sélectionné, son chemin s'affiche en jaune. Un segment dont le diamètre n'a pas pu être lu porte « Ø ? » avec un symbole d'alerte. La case **Ø / repères** masque ou affiche ces étiquettes."),
  p("La barre d'outils règle le zoom : les boutons moins et plus, **Ajuster** pour tenir dans la fenêtre, **100 %** pour la taille réelle. La molette de la souris avec la touche Ctrl zoome aussi, et les barres de défilement déplacent la vue."),
  h2("4.4 Câblage"),
  p("La vue Câblage reproduit la disposition de la feuille 2 du plan : les blocs S/C à gauche, les blocs INIT à droite, avec les traits d'origine redessinés par ARIANE. Les cadres rouges et orange désignent les blocs qui contiennent des erreurs ou des alertes. La feuille entière est visible, cartouche compris."),
  ...fig("06-cablage.png", "Le câblage, tel que la feuille 2 le présente."),

  // 5
  h1("5. Les contrôles"),
  p("Le tableau suivant liste les contrôles qui se sont déclenchés sur l'exemple. Le code apparaît en petits caractères au-dessus du message dans le rapport."),
  table([2300, 1100, 3300, 2938], ["Code", "Niveau", "Ce que ARIANE a constaté", "Que faire"], [
    ["duplicate-destination", "Erreur", "Une même pin de destination est citée par plusieurs lignes S/C.", "Ouvrir le plan et décider quelle ligne est la bonne."],
    ["origin-mismatch", "Erreur", "L'origine écrite côté INIT ne correspond pas à la ligne S/C qui y arrive.", "Comparer les deux côtés du plan."],
    ["wire-number-mismatch", "Erreur", "Le numéro de fil n'est pas le même côté S/C et côté INIT.", "Corriger le numéro dans le plan."],
    ["orphan-dst", "Erreur", "Une pin INIT annonce une origine, mais aucune ligne S/C ne la référence.", "Vérifier s'il manque un fil ou si l'origine est fausse."],
    ["connector-suffix", "Alerte", "Le côté INIT écrit J02 là où le bloc S/C s'appelle J01.", "Confirmer que c'est le même connecteur."],
    ["label-mismatch", "Alerte", "L'intitulé d'un bloc ne correspond à aucun libellé de la nomenclature.", "Comparer l'intitulé du bloc et le libellé de la nomenclature."],
    ["diameter-missing", "Alerte", "Aucun diamètre n'a été trouvé pour un segment.", "Lire le diamètre sur le plan et le reporter à la main."],
    ["diameter-ambiguous", "Alerte", "Plusieurs diamètres sont proches d'un même segment.", "Choisir le bon sur la feuille 3."],
    ["bom-tbd", "Info", "Une quantité de la nomenclature est encore à définir (TBD).", "Aucune, sauf si la quantité est attendue."],
    ["segment-no-bom", "Info", "Aucun repère de la nomenclature n'est relié à ce segment par un trait de repère.", "Aucune, sauf si le segment doit en porter un."],
  ]),
  p("", { spacing: { after: 120 } }),
  p("Sur l'exemple, les quatre erreurs concernent le connecteur S/C #x-4 et le connecteur INIT B P1. La pin w de INIT B P1 est citée comme destination par deux lignes S/C, les pins G et L. L'origine écrite pour la pin w désigne la pin L alors que la ligne arrive de la pin G, et le numéro de fil lu côté S/C (907-37) diffère de celui lu côté INIT (907-40). Enfin la pin W, avec une majuscule, annonce une origine que rien ne référence. Ces quatre lignes se recoupent, mais ARIANE ne décide pas laquelle est juste."),

  // 6
  h1("6. Exporter les résultats"),
  p("Quatre exports sont proposés dans le panneau de gauche. Le bouton CSV produit la liste From-To des 96 fils avec leurs segments, dans un format que Excel ouvre directement (séparateur point-virgule). Le bouton JSON enregistre le modèle complet de l'analyse, utile pour d'autres outils. Le bouton SVG de la vue enregistre le dessin de l'onglet Faisceau et ne fonctionne que lorsque cet onglet est affiché. Le bouton Excel… produit le classeur décrit ci-dessous."),
  h2("6.1 Le formulaire de l'export Excel"),
  p("Le bouton **Excel…** ouvre un formulaire. Le client, le projet, la référence et la date se déduisent de l'analyse. Le formulaire ne demande que ce que les PDF ne contiennent pas : l'édition, un sous-titre, la classification du document, le statut export control, puis les noms de la rédaction, de la vérification et de l'approbation qualité. Les valeurs saisies sont gardées dans votre navigateur et proposées à l'export suivant."),
  ...fig("10-export.png", "Le formulaire de l'export Excel, rempli pour l'exemple."),
  h2("6.2 Le classeur"),
  p("Le classeur contient six onglets. Les cinq derniers portent le même bandeau : logo, titre, référence, date et édition, suivi d'une ligne vide avant le tableau."),
  p("La page de garde reprend le modèle de document de l'entreprise (figure 10). Les cases de classification sont cochées selon le formulaire, et les noms saisis apparaissent dans les cadres d'approbation."),
  ...fig("xl-page-de-garde.png", "L'onglet Page de garde, rendu par Excel.", 430),
  p("L'onglet **From-To** donne une ligne par fil : numéro, paire, polarité, signal, type de câble, connecteur et pin de départ, connecteur et pin d'arrivée, segments traversés et diamètre maximal. Les lignes en erreur sont colorées en rose, ainsi que les fils non routés, qui portent la mention NON ROUTÉ."),
  ...fig("xl-from-to.png", "Onglet From-To (les premières lignes)."),
  p("L'onglet **Connecteurs** liste chaque pin avec le ou les fils qu'elle porte et l'origine ou la destination écrite sur le plan. L'onglet **Segments** décrit chaque segment de la topologie : nœuds, diamètre, repères de nomenclature et longueur sur le plan. L'onglet **Nomenclature** reprend les 48 positions du fichier PL, avec une colonne TBD pour les quantités à définir. L'onglet **Rapport** reprend les contrôles, les erreurs d'abord."),
  ...fig("xl-connecteurs.png", "Onglet Connecteurs."),
  ...fig("xl-rapport.png", "Onglet Rapport : les erreurs sont en rose, les alertes en jaune."),
  p("Le fichier d'exemple complet, produit avec les réglages de la figure 9, est fourni avec ce manuel sous le nom exemple-export.xlsx."),

  // 7
  h1("7. Points à connaître"),
  bullet("Le nombre de contacts pin et socket est déduit du suffixe des références de connecteur (PN pour pin, SN pour socket). Cette règle est une hypothèse du plugin. Si elle ne correspond pas à votre convention, les écarts de comptage avec la nomenclature n'ont pas de valeur."),
  bullet("ARIANE indique le nombre de places vides par connecteur, mais pas encore leurs lettres. Ce sont par exemple les pins C, F et M sur certains blocs S/C."),
  bullet("Un diamètre introuvable ne peut pas encore se corriger dans l'application. Le segment N3A-N1A de l'exemple est dans ce cas et le diamètre maximal d'un chemin qui le traverse ne le prend pas en compte."),
  bullet("Les lignes de la nomenclature dont la quantité est TBD sont reprises telles quelles dans l'export, sans valeur par défaut."),
  bullet("Un plan dont la mise en page diffère beaucoup de l'exemple peut produire des anomalies de lecture. Elles apparaissent alors dans le rapport comme des erreurs ou des alertes, jamais comme des connexions inventées."),
  p("Pour signaler un cas qui pose problème, joignez le plan, la nomenclature et le message du rapport à votre demande."),
];

const doc = new Document({
  creator: "ARIANE",
  title: "ARIANE, manuel utilisateur",
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 34, bold: true, color: NAVY }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: NAVY }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, right: 1134, bottom: 1134, left: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 } },
      children: [new TextRun({ text: "ARIANE   Manuel utilisateur", size: 17, color: "55606B" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " / ", PageNumber.TOTAL_PAGES], size: 17, color: "55606B" })] })] }) },
    children: [...cover, ...body],
  }],
});

const out = path.join(here, "ARIANE-manuel-utilisateur.docx");
fs.writeFileSync(out, await Packer.toBuffer(doc));
console.log("written", out, `${figure} figures`);
