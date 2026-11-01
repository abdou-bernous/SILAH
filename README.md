# SILAH — portail paie & RH

SILAH est un espace en ligne où chaque salarié retrouve sa paie et ses démarches RH, et où le service RH
prépare la paie et traite les demandes. Le design est volontairement doux (tons cappuccino et gris clair).

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

## Moteur de paie

Calcul algérien simplifié pour un salarié mensualisé (`backend/api/payroll.py`) :
- cotisation CNAS : 9 % salarié, 26 % employeur, sur les éléments soumis
- IRG sur salaires : barème mensuel de la loi de finances 2022, abattement de 40 % (entre 1 000 et 1 500 DA),
  exonération jusqu'à 30 000 DA et formule de lissage entre 30 000 et 35 000 DA
- primes soumises ou non à la CNAS et à l'IRG, absence non rémunérée valorisée sur 22 jours ouvrés

Les taux sont regroupés en tête du fichier pour être ajustés facilement. Les régimes particuliers (handicapés,
retraités, primes à taux fixe...) ne sont pas couverts par le MVP. Les congés sont décomptés en jours ouvrés
selon les jours de repos de l'entreprise (vendredi et samedi par défaut).

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

Ouvrez http://localhost:3000. La base est remplie avec une entreprise fictive (`SEED_DEMO=1`).

### Sans Docker

Backend :

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # entreprise et comptes de démonstration
python manage.py runserver
```

Frontend (dans un autre terminal) :

```bash
cd frontend
npm install
npm run dev
```

### Comptes de démonstration

Mot de passe commun : `Silah2026!`

| Identifiant | Rôle |
|---|---|
| `salarie` | Salarié (Amine Mansouri) |
| `yasmine` | Salariée |
| `manager` | Manager de l'équipe commerciale |
| `rh` | Gestionnaire RH (accès aussi à l'admin Django sur `/admin/`) |

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
    models.py       entreprise, salariés, bulletins, documents, absences, frais, notifications
    payroll.py      moteur de paie et décompte des jours
    pdf.py          rendu PDF des bulletins
    views.py        API REST
    management/commands/seed_demo.py
frontend/
  src/app/connexion           page de connexion
  src/app/(espace)/           espace connecté (salarié, manager, RH)
  src/components/             shell, calendrier d'équipe, bulletin, formulaires
  src/lib/                    client API, types, formatage
```

## Pistes pour la suite

- Réinitialisation du mot de passe par e-mail
- Import de salariés par fichier CSV et export comptable de la paie
- Signature électronique des documents
- Multi-entreprises (un cabinet qui gère plusieurs clients)
- Application mobile (Capacitor, comme FarmHub)
