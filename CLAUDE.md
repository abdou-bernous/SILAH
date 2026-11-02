# Consignes pour ce dépôt

## Guide d'utilisation : à tenir à jour à chaque modification

`docs/guide-utilisateur.md` décrit SILAH pour ses utilisateurs (salarié, manager, RH, comptable, administrateur
système). Le propriétaire du projet veut qu'il reste exact.

Toute modification qu'un utilisateur peut voir ou ressentir met à jour le guide **dans le même commit** : écran,
bouton, libellé, règle métier, droit d'un rôle, calcul de paie, notification, message d'erreur important. Pour chaque
modification :

1. Corriger ou compléter la section du rôle concerné, en reprenant les libellés exacts de
   `frontend/src/lib/i18n/messages.ts` (colonne française).
2. Mettre à jour la ligne « Version du guide » (date et commit de base) en haut du fichier.
3. Ajouter une ligne au tableau « Journal des mises à jour du guide », en fin de fichier.
4. Ne rien décrire qui ne soit pas dans le code poussé : pas de fonction prévue ou en cours.

Seuls les changements purement techniques, invisibles pour l'utilisateur (refactorisation, tests, CI), en sont
dispensés. Le README reste la documentation technique.
