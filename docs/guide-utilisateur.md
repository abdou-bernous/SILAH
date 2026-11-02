# Guide d'utilisation de SILAH

Ce guide explique comment se servir de SILAH, rôle par rôle. Les noms de boutons et de menus sont ceux affichés à
l'écran en français. En arabe, ils sont au même endroit, avec la mise en page inversée.

**Version du guide** : 2 novembre 2026, à jour avec le commit `6594a35`. Le journal des mises à jour est en fin de
document.

## Sommaire

1. [Premiers pas](#1-premiers-pas)
2. [Salarié](#2-salarié)
3. [Manager](#3-manager)
4. [Gestionnaire RH](#4-gestionnaire-rh)
5. [Comptable / gestionnaire de paie](#5-comptable--gestionnaire-de-paie)
6. [Administrateur système](#6-administrateur-système)
7. [Questions fréquentes](#7-questions-fréquentes)
8. [Journal des mises à jour du guide](#8-journal-des-mises-à-jour-du-guide)

---

## 1. Premiers pas

### Se connecter

1. Ouvrez l'adresse de SILAH (en local : http://localhost:3100).
2. Saisissez votre **identifiant ou votre e-mail**, puis votre **mot de passe**.
3. Cliquez sur **Se connecter**.

Après 20 tentatives en une minute, la connexion est bloquée un moment : attendez une minute.

### Choisir la langue

Les boutons **FR** et **ع**, en haut de l'écran, changent la langue. Le choix est mémorisé sur votre appareil.

### Mot de passe oublié

1. Sur la page de connexion, cliquez sur **Mot de passe oublié ?**
2. Saisissez votre e-mail, puis cliquez sur **Recevoir le lien**.
3. Ouvrez le lien reçu par e-mail, choisissez un nouveau mot de passe (8 caractères minimum, pas uniquement des
   chiffres, pas un mot de passe trop courant) et enregistrez.

Le lien ne sert qu'une fois. Si votre adresse n'est pas connue, aucun e-mail n'est envoyé, mais le message affiché est
le même, par sécurité. Sans e-mail dans votre dossier, demandez au service RH de changer votre mot de passe.

### Changer son mot de passe

**Mon profil** → bouton **Mot de passe** en haut à droite.

### Sur téléphone

Le site s'adapte au téléphone. Dans l'espace salarié, une barre d'onglets en bas de l'écran donne accès à Accueil,
Bulletins, Absences, Frais et Mon profil. Le menu ☰, en haut, donne accès au reste.

Pour l'installer comme une application, ouvrez le menu du navigateur, puis choisissez **Ajouter à l'écran d'accueil**
(Android) ou **Partager → Sur l'écran d'accueil** (iPhone).

### Notifications

La cloche, en haut de l'écran, affiche le nombre de notifications non lues : bulletin publié, demande validée ou
refusée, document déposé… Si un serveur e-mail est configuré, les plus importantes sont aussi envoyées par e-mail.

---

## 2. Salarié

### Accueil

L'accueil montre votre dernier bulletin, des raccourcis (**Poser une absence**, **Déclarer une note de frais**,
**Mettre à jour mon dossier**), vos compteurs de congés, vos prochaines absences et vos documents récents.

### Bulletins de paie

Menu **Bulletins de paie**.

- Les bulletins sont classés par année, avec le net et le brut cumulés.
- Cliquez sur un bulletin pour voir le détail de chaque ligne : salaire de base, primes, cotisations CNAS, IRG, net à
  payer.
- **Imprimer** ou **Télécharger le PDF**. Le PDF est en français et en arabe.
- Un bulletin marqué **Rectificatif** remplace un bulletin précédent qui contenait une erreur. Le motif et l'écart de
  net sont indiqués en haut. L'ancien reste consultable, avec la mention qu'il n'est plus en vigueur.

Vous ne voyez un bulletin qu'une fois **publié** par le service RH.

### Documents et attestations

Menu **Documents**.

- Vos documents personnels (contrat, attestations…) et ceux de l'entreprise (règlement intérieur, notes de service).
- Filtrez par catégorie ou cherchez par titre. Un badge **Nouveau** signale un document pas encore ouvert.
- Pour une **attestation de travail** ou une **attestation de salaire** : cliquez sur le bouton correspondant, dans
  le cadre **Demander une attestation**. Une fois la demande validée par le service RH, le PDF (français et arabe)
  arrive dans vos documents et vous êtes prévenu. Une seule demande en cours par type d'attestation.

### Absences et congés

Menu **Absences**.

1. Cliquez sur **Nouvelle demande** (ou **Poser une absence** depuis l'accueil).
2. Choisissez le type : congé annuel, récupération, maladie, absence exceptionnelle, congé sans solde, télétravail.
3. Indiquez les dates **Du** et **Au**. Cochez les demi-journées si besoin : départ l'après-midi, retour le midi.
4. La durée décomptée, en jours ouvrés, s'affiche automatiquement. Les jours de repos de l'entreprise (vendredi et
   samedi par défaut) ne sont pas comptés.
5. Ajoutez un commentaire ou un justificatif si besoin (certificat médical… 10 Mo maximum), puis **Envoyer la
   demande**.

Votre manager, ou le service RH si vous n'avez pas de manager, est prévenu. Vous voyez le statut dans **Mes
demandes** : en attente, validée, refusée (avec le commentaire), annulée.

- Le congé annuel et la récupération sont décomptés de votre solde. Une demande qui dépasse le solde disponible est
  refusée.
- Deux demandes ne peuvent pas se chevaucher.
- **Annuler** : possible tant que la demande est en attente, ou validée mais pas encore commencée.
- Un **congé sans solde** validé est retenu sur le salaire du mois.
- L'onglet **Calendrier de l'équipe** montre qui est absent. Le motif d'absence d'un collègue reste privé.

### Notes de frais

Menu **Notes de frais**.

1. **Nouvelle note** : date (aujourd'hui au plus tard), catégorie (transport, repas, hébergement, kilométriques,
   fournitures, autre), montant en DA, description.
2. Joignez le justificatif (photo ou PDF du ticket, 10 Mo maximum), puis enregistrez.
3. Suivez le statut : en attente → validée → remboursée, ou refusée.

Une note peut être annulée tant qu'elle est en attente. Le remboursement se fait soit à part, soit directement sur
votre bulletin de paie, sur une ligne « Remboursement de frais » non imposable.

### Mon profil

- **Coordonnées** : votre téléphone et votre contact d'urgence se modifient directement (**Modifier**).
- **État civil, adresse et coordonnées bancaires** : ces informations figurent sur vos bulletins. Cliquez sur
  **Demander une modification**, changez les champs voulus, puis envoyez. Seuls les champs que vous changez vraiment
  sont envoyés : une demande qui ne change rien est refusée. Le service RH vérifie et applique. Une seule demande
  peut être en cours, et vous pouvez l'annuler tant qu'elle n'est pas traitée.

---

## 3. Manager

Le manager a aussi tout l'espace salarié pour lui-même.

### Valider les demandes de son équipe

Menu **Validations équipe**, onglet **À valider**.

- Absences et notes de frais de vos collaborateurs directs, avec le justificatif s'il y en a un (trombone).
- ✓ pour valider, ✗ pour refuser. Vous pouvez ajouter un commentaire, conseillé en cas de refus pour que le salarié
  comprenne.
- Le collaborateur est prévenu de la décision.
- Un congé sans solde validé ou saisi sur un mois dont la paie est déjà calculée affiche l'encadré **Paie à revoir** :
  le service RH et le comptable sont prévenus pour corriger la paie.

Vous ne pouvez pas valider vos propres demandes.

### Saisir une absence pour un collaborateur

**Validations équipe** → **Ajouter une absence** : choisissez le collaborateur, le type et les dates. L'absence est
validée directement et le collaborateur est prévenu. C'est utile pour un arrêt maladie signalé par téléphone, par
exemple.

### Planning et historique

- Onglet **Planning** : calendrier des absences de l'équipe.
- Onglet **Historique** : toutes les demandes déjà traitées.

---

## 4. Gestionnaire RH

Le RH gère **son** entreprise : salariés, paie, documents, demandes. Il a aussi son espace salarié.

### Salariés

Menu **Salariés**.

- **Ajouter un salarié** : identité et accès (identifiant, mot de passe initial), contrat et rémunération (poste,
  catégorie, type de contrat, date d'embauche, salaire de base), données personnelles. Un salaire inférieur au SNMG
  (24 000 DA pour 173,33 h) est signalé, sans être bloqué, pour les temps partiels. La date de naissance
  doit donner au moins 15 ans.
- Le **manager** d'un salarié doit avoir le rôle Manager ou RH.
- Sur la fiche d'un salarié :
  - **Rubriques permanentes** : éléments repris sur chaque bulletin (panier, transport, IEP…). Choisissez la
    rubrique, le montant, puis **Ajouter**. Les primes imposées à 10 % (PRC, rappel) n'en font pas partie : elles ne
    reviennent pas chaque mois, ajoutez-les dans la paie du mois concerné.
  - **Compteurs de congés** de l'année : modifiez le nombre de jours acquis.
  - Ses bulletins et ses documents personnels.
- **Désactiver le compte** : le salarié ne peut plus se connecter, ses bulletins sont conservés, et ses demandes en
  attente et ses absences à venir sont annulées. **Réactiver le compte** le rétablit. Vous ne pouvez pas désactiver
  votre propre compte ni changer votre propre rôle.

### Préparer et publier la paie du mois

Menu **Paie**.

1. Choisissez le **mois** et l'**année**.
2. **Variables individuelles** : pour chaque salarié, saisissez les heures supplémentaires (majoration de 50 % au
   minimum) et une éventuelle prime individuelle, puis **Enregistrer**. Les congés sans solde validés sont repris
   automatiquement. Au-delà de 34,67 h supplémentaires dans le mois (20 % de la durée légale), le calcul affiche un
   avertissement : une dérogation est nécessaire. Si le bulletin du salarié est déjà publié, un message le signale :
   passez par **Corriger** (section suivante) pour que les variables y figurent.
3. **Primes et indemnités (appliquées à tous)** : ajoutez une rubrique commune à tous les salariés du mois si besoin.
   Choisissez dans la liste (PRI, PRC, panier…) ou créez une rubrique libre, puis réglez le montant, la soumission
   à la CNAS et le régime d'IRG.
4. Laissez cochée la case **Rembourser les notes de frais validées sur le bulletin** pour payer les frais avec le
   salaire. Décochez-la si vous les remboursez à part.
5. Cliquez sur **Calculer** (le bouton porte aussi le nom du mois) : les bulletins sont créés **en brouillon**. Les
   salariés ne voient encore rien. Le calcul tient compte de la date d'embauche : un salarié embauché après le mois
   est écarté, avec le motif « Embauché le …, après ce mois » ; embauché en cours de mois, son salaire de base est
   réduit des jours ouvrés qui précèdent son arrivée (ligne « Entrée en cours de mois ») et un avertissement le
   signale. Un congé sans solde qui couvre tous les jours ouvrés du mois ne laisse aucun salaire de base.
6. Vérifiez chaque brouillon (cliquez sur le nom) et les totaux du mois. En cas d'erreur, corrigez la cause (fiche
   du salarié, variables, absences) puis relancez **Calculer** : les brouillons sont recalculés. Vous pouvez aussi
   supprimer un brouillon (corbeille).
7. Publiez un bulletin (**Publier**) ou tous (**Publier les N brouillon(s)**). Les salariés sont prévenus, et les
   notes de frais incluses passent à « remboursée ».

Un bulletin déjà publié n'est jamais recalculé : voir la section suivante.

**Déclarations du mois** : totaux pour la déclaration G50 (IRG au barème et IRG 10 %) et pour la CNAS (part
salariale 9 %, part patronale 25 % + FNPOS 0,5 %). Tant qu'il reste des brouillons, la mention **Montants
provisoires** s'affiche : déclarez une fois la paie publiée.

### Corriger un bulletin déjà publié

Un bulletin publié ne se modifie pas et ne se supprime pas : on le remplace par un **bulletin rectificatif**.

1. Si l'erreur vient de la fiche du salarié, des variables du mois ou des absences, corrigez d'abord la source.
2. Dans **Paie**, choisissez le mois, puis cliquez sur le crayon **Corriger** du bulletin concerné.
3. Indiquez le **motif de la correction** (obligatoire), ajustez les primes du mois appliquées au calcul, puis
   cliquez sur **Calculer le rectificatif**.
4. Ouvrez le rectificatif (**Vérifier**) : l'écart de net avec l'ancien bulletin est affiché (**à verser** ou **à
   reprendre** au salarié). Vous pouvez **Recalculer** ou **Annuler la correction** : l'ancien bulletin reste alors en
   vigueur.
5. **Publier le rectificatif** : il remplace l'ancien bulletin, qui reste archivé avec la mention « remplacé ». Le
   salarié est prévenu. Les totaux G50 et CNAS ne comptent que la version en vigueur.

Si la déclaration G50 ou CNAS du mois a déjà été déposée, voyez avec votre comptable comment régulariser.

### Demandes à traiter

L'accueil affiche le nombre de demandes en attente. Le bandeau **N demande(s) à traiter** mène aux bons écrans.

- **Validations équipe** : absences et notes de frais de tous les salariés de l'entreprise, plus les **notes validées
  à rembourser** (**Marquer remboursée**, sauf si la note est déjà incluse dans un bulletin).
- **Demandes à traiter** :
  - **Demandes d'attestation** : **Délivrer** génère le PDF et le dépose dans les documents du salarié. La fiche du
    salarié doit être complète (date d'embauche, poste, et salaire de base pour une attestation de salaire), sinon un
    message indique ce qui manque. Aucune attestation n'est délivrée avant la date d'embauche ni pour un salarié
    désactivé.
  - Modifications de dossier : l'ancienne et la nouvelle valeur sont affichées. **Appliquer** met à jour le dossier,
    **Refuser** avec un commentaire.

Vos propres demandes ne passent jamais par vous : vos absences et notes de frais vont à votre manager, ou à défaut à
un autre RH ou au comptable ; vos modifications de dossier et vos attestations vont à un autre RH ou au comptable. Si
personne d'autre ne peut décider, elles sont validées d'office, avec une trace dans le journal.

Une absence sans solde validée, saisie ou annulée sur un mois déjà calculé déclenche une alerte : recalculez le
brouillon, ou corrigez le bulletin s'il est publié.

### Dépôt de documents

Menu **Dépôt de documents** : choisissez un salarié, ou aucun pour un document de toute l'entreprise, puis la
catégorie, le titre et le fichier (10 Mo maximum). Les personnes concernées sont prévenues.

### Entreprise

Menu **Entreprise** : identité de l'employeur (raison sociale en français et en arabe, NIF, NIS, RC, n° employeur
CNAS), affichée en en-tête des bulletins, ainsi que les jours de repos hebdomadaire et le congé annuel acquis par an.

### Journal d'activité

Menu **Journal d'activité** : les 200 dernières actions sensibles (paie calculée ou publiée, dossier modifié, absence
validée, attestation délivrée…), avec l'auteur, la date et l'heure. Le journal ne contient ni montants ni données
personnelles.

---

## 5. Comptable / gestionnaire de paie

Le comptable gère **plusieurs entreprises clientes**. Dans chacune, il fait tout ce que fait un RH (section 4).

- **Mes entreprises** : une carte par entreprise, avec le nombre de salariés, la dernière paie et ce qui reste à
  traiter (brouillons, absences, frais, modifications de dossier, attestations). **Salariés** et **Paie** ouvrent
  l'entreprise.
- **Changer d'entreprise** : le sélecteur en haut de l'écran.
- **Nouvelle entreprise** : renseignez l'identité de l'employeur. Vous êtes automatiquement rattaché à l'entreprise
  créée, et vous pouvez ensuite ajouter les salariés, dont un RH si l'entreprise en a un.
- **Mon compte** : vos coordonnées et votre mot de passe.

Une entreprise désactivée par l'administrateur reste visible, marquée « Désactivée », mais on ne peut plus y
travailler.

---

## 6. Administrateur système

L'administrateur système supervise la plateforme. Il n'a **aucun accès** aux dossiers des salariés, à la paie, aux
documents ni à l'identité des employeurs : ces données restent aux RH et aux comptables.

- **Tableau de bord** : chiffres agrégés (entreprises actives, salariés, comptables, bulletins publiés, demandes en
  attente, net à payer publié sur 6 mois) et derniers comptes créés.
- **Entreprises** : liste de toutes les entreprises. **Désactiver** ferme une entreprise : ses salariés ne peuvent
  plus se connecter, les sessions ouvertes sont coupées, et l'historique est conservé. **Réactiver** la rouvre. La
  création d'une entreprise est réservée aux comptables.
- **Comptables & admins** : **Nouveau compte** pour un comptable ou un autre administrateur. Pour un comptable,
  cochez les entreprises qu'il gère. Vous ne pouvez pas retirer vos propres droits ni désactiver votre propre compte.

---

## 7. Questions fréquentes

**Je ne vois pas mon bulletin du mois.**
Il n'est pas encore publié : le service RH l'a peut-être encore en brouillon. Vous serez prévenu à la publication.

**Il y a une erreur sur un bulletin.**
Signalez-la au service RH. Avant publication, il recalcule le brouillon. Après publication, il établit un bulletin
rectificatif (section 4, « Corriger un bulletin déjà publié »).

**Un salarié a trop perçu.**
Le bulletin rectificatif indique le montant « à reprendre au salarié ». Il n'existe pas encore de retenue automatique
sur le mois suivant : à traiter avec le comptable.

**Mon solde de congés est faux.**
Le service RH peut corriger les jours acquis sur votre fiche (**Compteurs de congés**).

**Je n'arrive plus à me connecter.**
Essayez **Mot de passe oublié ?**. Si votre entreprise a été désactivée, la connexion est refusée : contactez votre
employeur.

**Mes collègues voient-ils le motif de mes absences ?**
Non : dans le calendrier de l'équipe, ils voient seulement « Absent ». Le type d'absence n'est visible que par vous,
votre manager et le service RH. Le télétravail n'apparaît pas dans le calendrier.

---

## 8. Journal des mises à jour du guide

| Date | Commit | Changement |
|---|---|---|
| 2 novembre 2026 | `6594a35` | Compléments : calcul selon la date d'embauche, alerte heures sup., variables après publication, rubriques à 10 %, conditions d'une attestation, qui valide les demandes d'un RH, confidentialité du calendrier |
| 2 novembre 2026 | `6594a35` | Première version : tous les rôles, paie, bulletin rectificatif, demandes à traiter, attestations, mot de passe oublié, usage sur téléphone |
