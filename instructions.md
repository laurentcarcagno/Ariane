# Mission
Développe un outil web local qui importe les PDF d'un plan de faisceau
(câblage aérospatial) et sa nomenclature, reconstruit la netlist, puis
affiche une vue SVG interactive. Quand on clique sur une pin d'un
connecteur, l'outil doit mettre en évidence le fil, son chemin dans le
faisceau, la pin et le connecteur à l'autre extrémité.

# Contraintes
- Données industrielles confidentielles : tout le traitement se fait
  dans le navigateur ou en local. Aucun envoi vers un service externe,
  aucun CDN au runtime (dépendances embarquées dans le build).
- Environnement d'entreprise derrière un proxy HTTPS : prévoir une
  installation simple (npm) et un build statique ouvrable hors ligne.
- Stack suggérée : TypeScript + Vite, pdf.js pour lire le PDF (texte,
  coordonnées, chemins vectoriels), SVG pour le rendu.
- Ne jamais inventer une connexion. Toute donnée ambiguë ou
  contradictoire est signalée à l'utilisateur, pas corrigée en silence.

# Fichiers d'entrée (exemple fourni : harnais 3500402-907 "Init Lower 1-6")
1. DRW3500402-907_Init_Lower_1-6.pdf : plan A2, 3 feuilles, généré
   par Ghostscript puis assemblé dans Nitro PDF. Le texte est vectoriel
   (polices Courier New / Arial embarquées) : PAS besoin d'OCR. Les
   pages ont /Rotate 90, il faut gérer correctement la rotation des
   coordonnées.
   - Feuille 1 : topologie du faisceau. Six branches S/C I #x-1..#x-6
     J01 en haut, deux connecteurs INIT A (Lower) P1 et INIT B (Lower)
     P1 en bas. Les points de dérivation sont numérotés en rouge (1..12
     côté A, 1..5 / 7..12 côté B). Les segments portent des repères de
     nomenclature (07 câble, 08/09/10 tresses, 13-21 étiquettes).
     Les tracés bleus sont des chemins vectoriels exploitables.
   - Feuille 2 : schéma de câblage (la source principale).
     * 6 blocs "S/C I #x-N J01", connecteur D38999/20FD19SN (19
       contacts). Chaque ligne contient : polarité (+/-), nom de signal
       (ex. "S/C_#1_N1 Nom" / "S/C_#1_N1 Red"), lettre de pin (colonne
       x≈230 dans le repère pdfplumber), destination "INIT_A_P1:c" ou
       "INIT_B_P1:c" (colonne x≈284), numéro de fil en rouge "907-01"
       placé entre les deux lignes d'une paire.
     * 2 blocs INIT A / INIT B P1, connecteur D38999/26FJ61PN (61
       contacts). Chaque ligne contient : origine "SC_I_#x-1_J01:N",
       pin locale, numéro de fil.
     * Fils de type TSP-20 (paire torsadée blindée AWG20). Le blindage
       est repris au backshell (Note 4).
   - Feuille 3 : diamètres par segment (Ø9 / 12.5 / 15 / 17.5 / 19.5
     / 22 mm). La table des longueurs est "TBD".
2. PL_3500402-907_A.1.pdf : nomenclature (wkhtmltopdf, tableau texte).
   Elle sert aux contrôles de cohérence.

# Pièges identifiés (à gérer explicitement)
- Les lettres de pin D38999 sont sensibles à la casse et peuvent être
  doubles : c ≠ C, et AA, BB… PP existent. Ne jamais normaliser la casse.
- L'extraction peut fusionner des mots collés
  ("INIT_A_P1:NINIT_A_P1:k"). Il faut regrouper par coordonnées (x, y)
  et non par ordre de flux du texte.
- Une lettre de pin isolée peut être décalée de ±1-2 pt en y par
  rapport à sa ligne. Prévoir une tolérance d'alignement.
- Les deux vues se répondent : la ligne S/C N°#1 pin N → INIT_A_P1:c
  doit retrouver, côté INIT A, la ligne pin c → SC_I_#x-1_J01:N avec
  le même numéro de fil. Recouper systématiquement les deux tables.
- Incohérences déjà repérées à signaler dans le rapport :
  * côté INIT B, les origines sont libellées "SC_I_#x-N_J02:…" alors
    que les connecteurs S/C sont nommés J01 ;
  * une même pin INIT_B_P1 (ex. "w") semble apparaître deux fois dans
    le bloc S/C #4 Red. À vérifier : extraction ou erreur du plan.

# Fonctionnalités attendues
1. Import : glisser-déposer les PDF, puis parsing côté client.
2. Modèle de données JSON exportable :
   - connectors {id, ref, partNumber, contacts[]}
   - wires {id "907-xx", type, pairId, from {conn, pin}, to {conn, pin},
     signal, polarity, nomRed}
   - topology {nodes (connecteurs + points de dérivation),
     segments {id, diameter, nodesA/B, bomItem}}
   - routes {wireId → liste ordonnée de segments}
3. Topologie : extraire les segments et nœuds depuis les tracés bleus
   de la feuille 1 (graphe), associer les numéros rouges aux nœuds,
   puis calculer la route de chaque fil (plus court chemin entre ses
   deux connecteurs). Si l'extraction géométrique échoue, fournir un
   éditeur ou un fichier JSON de topologie corrigeable à la main.
4. Vues interactives SVG :
   - Vue "faisceau" (feuille 1 redessinée) : clic sur un connecteur,
     puis sur une pin. Le chemin du fil, les points de dérivation
     traversés et le connecteur d'arrivée sont surlignés.
   - Vue "connecteurs" : face de chaque connecteur avec ses pins. Clic
     sur une pin : la pin d'arrivée et le fil sont surlignés, et la
     paire torsadée associée (+/-) est mise en évidence secondairement.
   - Option : superposition sur le rendu pdf.js original, avec
     surlignage des textes et des tracés correspondants.
   - Panneau d'info : n° fil, signal, type, pin départ → pin arrivée,
     segments et diamètres traversés.
   - Recherche par n° de fil, signal ou pin.
5. Exports : liste from/to (CSV et Excel), JSON du modèle, SVG de la vue
   courante.
6. Rapport de contrôle affiché à l'import :
   - recoupement S/C ↔ INIT (fils orphelins, pins en double, n° de fil
     incohérents) ;
   - comptage par rapport à la nomenclature. Attendu sur cet exemple :
     2 × 61 = 122 contacts pin (pos 05), 6 × 19 = 114 contacts socket
     (pos 06, pins vides comblées selon la Note 5), 48 paires TSP
     907-01..907-48 (8 signaux × 6 S/C × Nom/Red = 96 conducteurs) ;
   - éléments TBD de la nomenclature et de la table des longueurs.

# Démarche demandée
1. Commence par un script d'exploration (pdf.js ou pdfplumber) qui
   extrait mots et chemins vectoriels avec leurs coordonnées. Montre-moi
   la netlist extraite et le rapport de contrôle AVANT de construire
   l'interface.
2. Écris le parser de manière générique (détection des blocs par leurs
   en-têtes et colonnes), pas en coordonnées codées en dur. D'autres
   plans du même fournisseur et du même format devront fonctionner.
3. Ajoute des tests unitaires sur la netlist de cet exemple : 48 paires,
   recoupement des deux tables, sensibilité à la casse.
4. Construis ensuite l'interface, puis l'export.

# Critères d'acceptation
- Un clic sur S/C I #x-1 J01 pin N surligne le fil 907-01 (+), son
  chemin jusqu'à INIT A P1 pin c, et la paire associée (pin A → INIT A
  pin B).
- Les 96 conducteurs sont tous routés ou explicitement signalés comme
  non routés.
- Aucune donnée ne quitte la machine.