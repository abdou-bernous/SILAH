# SILAH — portail paie & RH

SILAH est un espace en ligne où chaque salarié retrouve sa paie et ses démarches RH, où le service RH ou le
comptable prépare la paie de une ou plusieurs entreprises, et où l'administrateur de la plateforme supervise
l'ensemble. L'interface est disponible en **français et en arabe** (mise en page de droite à gauche), et les
bulletins suivent la **réglementation algérienne**. Le design est volontairement doux (tons cappuccino et gris clair).

## Rôles

| Rôle | Ce qu'il fait |
|---|---|
| Salarié | Consulte ses bulletins et documents, pose ses congés, déclare ses frais |
| Manager | Valide les demandes de ses collaborateurs directs |
| Gestionnaire RH | Gère les salariés, la paie et les documents de **son** entreprise |
| Comptable / gestionnaire de paie | Gère **plusieurs entreprises clientes** : en crée de nouvelles, bascule de l'une à l'autre (sélecteur en haut de l'écran) et y fait tout ce que fait un RH |
| Administrateur plateforme | Voit et gère tout : tableau de bord global (entreprises, salariés, masse salariale sur 6 mois, demandes en attente), création des comptes comptables et attribution des entreprises, désactivation d'une entreprise |

Chaque entreprise est cloisonnée : un RH ne voit que la sienne, un comptable seulement celles qui lui sont
attribuées (l'en-tête `X-Company` envoyé par le frontend est revérifié côté serveur à chaque requête).

## Fonctionnalités du MVP

**Salarié**
- Tableau de bord : dernier bulletin, compteurs de congés, prochaines absences, documents récents
- Bulletins de paie : historique par année, détail des rubriques, impression et téléchargement PDF
- Coffre-fort de documents : contrats, attestations, documents de l'entreprise, avec catégories et recherche
- Absences & congés : soldes (congé annuel, récupération), demandes à la demi-journée avec décompte automatique
  des jours ouvrés, justificatif, annulation, calendrier de l'équipe
- Notes de frais : déclaration avec justificatif, suivi (en attente, validée, refusée, remboursée)
- Profil : téléphone et contact d'urgence modifiables directement ; adresse, RIB et état civil via une demande
  validée par les RH ; changement de mot de passe
- Notifications dans l'application (et par e-mail si un serveur SMTP est configuré)

**Manager**
- Validation ou refus (avec commentaire) des absences et notes de frais de ses collaborateurs directs
- Historique et planning des absences de l'équipe (le motif d'absence reste privé pour les collègues)

**Gestionnaire RH**
- Dossiers salariés : création, modification, désactivation, compteurs de congés
- Paie mensuelle : calcul en brouillon avec primes et indemnités, déduction automatique des congés sans solde,
  vérification, puis publication (les salariés sont notifiés)
- Dépôt de documents dans le coffre-fort d'un salarié ou pour toute l'entreprise
- Traitement des demandes de modification de dossier, remboursement des notes de frais
- Paramètres de l'entreprise : identité (NIF, NIS, RC, CNAS), jours de repos hebdomadaire, congé annuel

## Paie algérienne

Moteur de paie pour salariés mensualisés (`backend/api/payroll.py`), règles vérifiées sur les sources publiques 2026 :
- **SNMG** : 24 000 DA / mois depuis le 1er janvier 2026, base 173,33 h / mois (40 h / semaine) ; un salaire
  inférieur est signalé (temps partiel possible) mais pas bloqué
- **CNAS** sur l'assiette cotisable : 9 % salarié ; 25 % employeur + 0,5 % FNPOS (œuvres sociales)
- **IRG salaires** : barème mensuel de la loi de finances 2022 (0 / 23 / 27 / 30 / 33 / 35 %), base arrondie à la
  dizaine inférieure, abattement de 40 % borné entre 1 000 et 1 500 DA, exonération jusqu'à 30 000 DA, lissage
  entre 30 000 et 35 000 DA ; lissage étendu jusqu'à 42 500 DA pour les travailleurs handicapés
- **IRG 10 % libératoire** pour les primes non mensuelles (PRC / PRI trimestrielles, rappels)
- rubriques prêtes à l'emploi : PRI, PRC, IEP, heures supplémentaires, nuisance, panier et transport (non soumis
  CNAS, imposables), allocations familiales et prime de scolarité (exonérées), ou rubrique libre
- absences non rémunérées valorisées sur 22 jours ouvrés, heures travaillées proratisées
- totaux mensuels pour la **déclaration G50** (IRG) et le versement **CNAS** affichés sur l'écran Paie
- bulletin et PDF **bilingues français / arabe** avec NIF, NIS, RC, n° employeur CNAS, NIN, n° SS, catégorie,
  situation familiale et mode de paiement

Non couverts : régimes sectoriels (CACOBATPH), aides à l'emploi (CNAC / ANEM), indemnité de congé payé calculée
au 1/12e, retraités. Les taux sont regroupés en tête du fichier pour être ajustés facilement. **Avant toute
mise en production, faites valider les calculs par un expert-comptable ou un gestionnaire de paie algérien.**

Les congés annuels sont de 2,5 jours par mois de travail (30 jours par an, loi 90-11) et décomptés selon les
jours de repos de l'entreprise (vendredi et samedi par défaut).

## Langues

Le sélecteur FR / ع en haut de chaque écran (et sur la page de connexion) bascule toute l'interface ; le choix
est mémorisé dans le navigateur. Les traductions sont dans `frontend/src/lib/i18n/messages.ts` (une ligne par
texte : `[français, arabe]`). Les messages d'erreur renvoyés par l'API et les notifications restent en français
pour l'instant.

## Stack

Identique à FarmHub :
- **Frontend** : Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Axios, Heroicons
- **Backend** : Django 4.2, Django REST Framework, SimpleJWT, PostgreSQL (SQLite en local), ReportLab pour les PDF
- Docker Compose et GitHub Actions (tests Django, vérification TypeScript, build Next.js)

Les fichiers (bulletins, documents, justificatifs) ne sont jamais servis publiquement : ils passent uniquement
par des routes d'API authentifiées qui vérifient les droits de l'utilisateur.

## Démarrage rapide

### Avec Docker

```bash
docker compose up --build
```

Ouvrez http://localhost:3100. La base est remplie avec deux entreprises fictives (`SEED_DEMO=1`).

### Sans Docker

Backend :

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # entreprises et comptes de démonstration (--reset pour repartir de zéro)
python manage.py runserver 8100
```

Frontend (dans un autre terminal) :

```bash
cd frontend
npm install
npm run dev
```

Ports : le frontend tourne sur http://localhost:3100 et l'API sur http://localhost:8100 (pour ne pas entrer en
conflit avec d'autres projets sur 3000 / 8000). L'admin Django est sur http://localhost:8100/admin/.

### Comptes de démonstration

Mot de passe commun : `Silah2026!`

| Identifiant | Rôle |
|---|---|
| `salarie` | Salarié d'Atlas Distribution (Amine Mansouri) |
| `yasmine` | Salariée d'Atlas Distribution |
| `manager` | Manager de l'équipe commerciale d'Atlas Distribution |
| `rh` | Gestionnaire RH d'Atlas Distribution |
| `rh.nour`, `sofiane`, `lina` | RH et salariés de Nour Pharma (Oran) |
| `comptable` | Comptable qui gère Atlas Distribution et Nour Pharma |
| `admin` | Administrateur de la plateforme (accès aussi à l'admin Django sur `/admin/`) |

En production, désactivez l'encart de démonstration de la page de connexion avec `NEXT_PUBLIC_SHOW_DEMO=0`
et ne lancez pas `seed_demo`.

## Tests

```bash
cd backend && python manage.py test
cd frontend && npx tsc --noEmit && npm run build
```

## Structure

```
backend/
  silah/            réglages Django
  api/
    models.py       entreprises, salariés, bulletins, documents, absences, frais, notifications
    payroll.py      moteur de paie algérien et décompte des jours
    pdf.py          rendu PDF bilingue des bulletins (polices DejaVu dans api/fonts)
    permissions.py  cloisonnement par entreprise et rôles
    views.py        API REST
    management/commands/seed_demo.py
frontend/
  src/app/connexion           page de connexion
  src/app/(espace)/           espace connecté (salarié, manager, RH, comptable, admin)
  src/app/(espace)/entreprises    entreprises gérées (comptable, admin)
  src/app/(espace)/plateforme     tableau de bord et comptes de l'administrateur
  src/components/             shell, sélecteurs d'entreprise et de langue, bulletin, formulaires
  src/lib/                    client API, types, formatage, traductions (i18n)
```

## Pistes pour la suite

- Réinitialisation du mot de passe par e-mail
- Import de salariés par fichier CSV et export comptable de la paie
- Signature électronique des documents
- Traduction en arabe des messages d'erreur de l'API et des notifications
- Fichiers de déclaration (G50, DAS annuelle CNAS) prêts à déposer
- Application mobile (Capacitor, comme FarmHub)
