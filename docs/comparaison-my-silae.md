# Comparaison My Silae / SILAH

Comparaison faite le 1er novembre 2026 à partir de sources publiques : fiches commerciales, App Store et articles
d'intégrateurs. Je n'ai pas eu accès au produit lui-même. Les modules réellement disponibles dépendent de ce que
l'employeur active. My Silae vise le droit français : les modules liés à ce droit (DPAE, BDESE, mutuelle, index
égalité) ne sont pas à reprendre tels quels pour l'Algérie.

Légende : **Présent**, **Partiel**, **Absent**. La colonne « Avant » indique l'état de SILAH avant ce chantier.

## Tableau des fonctionnalités

### Salarié

| Fonctionnalité | My Silae | Avant | SILAH maintenant |
|---|---|---|---|
| Bulletins en ligne, téléchargement | Oui | Présent | Présent |
| Coffre-fort de documents | Oui, certifié selon l'éditeur | Partiel | Partiel : documents privés et traçabilité de lecture, sans certification ni archivage légal |
| Demande de congés et absences | Oui | Présent | Présent |
| Compteurs à jour | Oui | Présent | Présent |
| Estimation des soldes futurs | Oui | Absent | Absent |
| Télétravail | Oui | Présent | Présent |
| Notes de frais, frais kilométriques | Oui (Silae Expense) | Partiel | Partiel : catégorie kilométrique sans barème automatique |
| Demande d'attestation | Non documenté dans les sources lues | Absent | **Présent** : PDF français et arabe déposé dans les documents |
| Signature électronique | Oui | Absent | Absent |
| Mot de passe oublié en autonomie | Non documenté | Absent | **Présent** |
| Vue du planning | Oui | Partiel | Partiel : calendrier des absences, pas d'horaires |

### Manager

| Fonctionnalité | My Silae | Avant | SILAH maintenant |
|---|---|---|---|
| Validation des absences et des frais | Oui | Présent | Présent |
| Agenda d'équipe | Oui | Présent | Présent |
| Ajouter une absence pour un membre | Oui | Absent | **Présent** |
| Saisie de variables de paie | Oui | Absent | Partiel : saisie réservée aux RH et comptables |
| Workflow configurable par service | Oui | Absent | Absent : validation par le manager direct |

### RH et gestionnaire de paie

| Fonctionnalité | My Silae | Avant | SILAH maintenant |
|---|---|---|---|
| Multi-sociétés, accès par profil | Oui | Présent | Présent |
| Absences validées reprises en paie | Oui | Partiel | Partiel : les congés sans solde sont repris, les arrêts maladie n'ont pas de calcul propre |
| Éléments de paie par salarié | Oui | Absent | **Présent** : rubriques permanentes et grille mensuelle |
| Frais remboursés via la paie | Oui (connecteur) | Absent | **Présent** |
| Journal d'audit horodaté | Oui | Absent | **Présent** |
| Dépôt de documents | Oui | Présent | Présent |
| Onboarding en ligne | Oui | Absent | Absent |
| Édition de contrats depuis des modèles | Oui | Absent | Absent |
| Entretiens, avec rappels | Oui | Absent | Absent |
| Visites médicales | Oui | Absent | Absent |
| Plannings, badgeuse déclarative | Oui | Absent | Absent |
| Tableaux de bord RH avancés | Oui (Silae BI) | Partiel | Partiel : totaux de paie et tableau de bord plateforme |
| Export comptable, fichier de virement | Oui | Absent | Absent |
| API d'intégration | Oui | Partiel | Partiel : API REST interne, préfixe stable `/api/v1/` ajouté |

### Mobile

| Fonctionnalité | My Silae | Avant | SILAH maintenant |
|---|---|---|---|
| Application iOS et Android | Oui | Absent | Absent, préparation faite (voir [mobile.md](mobile.md)) |
| Validation par le manager sur mobile | Oui | Partiel | Partiel : par le site, sur téléphone |
| Site adapté au téléphone | Non documenté | Partiel | **Présent** côté salarié : barre d'onglets, zones sûres, site installable |

## Là où SILAH a de l'avance

- **Réglementation algérienne** : CNAS, IRG, SNMG, déclarations G50, ce que My Silae ne couvre pas.
- **Français et arabe** : interface de droite à gauche et bulletins PDF bilingues.
- **Attestations en autonomie**, très demandées en Algérie pour les banques et les administrations.

## Priorités recommandées

1. **Faire valider la paie par un expert algérien.** Cela prime sur toute nouvelle fonction, en particulier le
   décompte des congés (jours ouvrés ou calendaires, article 41 de la loi 90-11).
2. **Déclarations et paiement** : export G50, déclaration CNAS, fichier de virement, export comptable. C'est le gain
   de temps le plus direct pour un comptable.
3. **Arrêts maladie en paie**, avec indemnisation CNAS.
4. **Variables saisies par les managers**, validées ensuite par les RH.
5. **Onboarding et contrats** : invitation du salarié, pièces à fournir, contrat généré depuis un modèle.
6. **Application mobile** avec Capacitor et notifications push.
7. **Planning et pointage**, surtout pour la distribution et la production.
8. **Signature électronique** : à faire avec un prestataire reconnu en Algérie, car une case à cocher n'aurait pas la
   même valeur juridique.

## Sources

- [Silae, site officiel](https://www.silae.fr/)
- [YaKaPaie, fonctionnalités de My Silae](https://yakapaie.fr/articles/125-decouvrez-toutes-les-fonctionnalites-de-my-silae)
- [Plateya, My Silae RH](https://plateya.fr/blog/detail/my-silae-rh-le-portail-salarie-de-silae)
- [mySilae sur l'App Store](https://apps.apple.com/app/id1128357646)
- [Appvizer, My Silae](https://www.appvizer.fr/ressources-humaines/paie/my-silae)
- [Absys Cyborg, My Silae](https://absyscyborg.com/fr/logiciels/silae/my-silae)
- [Apogea, My Silae](https://www.apogea.fr/my-silae/) : vu seulement dans les résultats de recherche, la page a refusé
  la lecture directe.
