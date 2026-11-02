# Passer SILAH en application mobile

Le site est préparé pour devenir une application iOS et Android sans réécriture. La méthode prévue est d'envelopper le
site déployé avec [Capacitor](https://capacitorjs.com/), via l'option `server.url`. L'application charge alors le vrai
site, donc chaque mise à jour du site arrive sans passer par les stores.

## Ce qui est déjà en place

- **Données** : tout passe par l'API REST (`frontend/src/lib/api.ts`). Le préfixe `/api/v1/` est stable : une version
  installée sur un téléphone continuera d'appeler le même contrat quand `/api/` évoluera.
- **Authentification** : JWT envoyé dans l'en-tête `Authorization`.
- **Écran** : barre d'onglets sur téléphone pour l'espace salarié, zones sûres (`viewport-fit=cover`), champs en 16 px
  pour éviter le zoom automatique d'iOS.
- **Installation** : manifeste web (`frontend/src/app/manifest.ts`) et couleur de thème. Le site peut déjà être ajouté à
  l'écran d'accueil.
- **Téléchargements** : ils passent tous par `downloadFile` dans `lib/api.ts`.

## Étapes

1. Déployer le site en HTTPS, avec `FRONTEND_URL` et `NEXT_PUBLIC_API_URL` en production.
2. Dans `frontend/` :

   ```bash
   npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios
   npx cap init SILAH dz.silah.app --web-dir public
   npx cap add android
   npx cap add ios
   ```

3. Créer `frontend/capacitor.config.ts` :

   ```ts
   import type { CapacitorConfig } from '@capacitor/cli'

   const config: CapacitorConfig = {
     appId: 'dz.silah.app',
     appName: 'SILAH',
     webDir: 'public',
     server: { url: 'https://votre-domaine.dz', cleartext: false },
   }
   export default config
   ```

4. Brancher les téléchargements : les liens `blob:` ne fonctionnent pas dans une WebView Android. Dans `downloadFile`,
   détecter `Capacitor.isNativePlatform()`, écrire le fichier avec `@capacitor/filesystem`, puis l'ouvrir avec
   `@capacitor/share`. `openFile` a besoin du même traitement.
5. Fournir des icônes PNG 192 et 512 px : le manifeste ne déclare aujourd'hui qu'un SVG, et les stores exigent des
   images aux tailles fixes.
6. Tester sur de vrais appareils, puis publier sur Google Play et l'App Store.

## À prévoir

- **App Store** : Apple peut refuser une application qui n'est qu'un site enveloppé. Ajouter des fonctions natives
  aide : notifications push, ouverture par Face ID, partage de PDF.
- **Notifications push** : `@capacitor/push-notifications`, Firebase, et un modèle côté API pour stocker les jetons des
  appareils. Le point d'entrée existe déjà : la fonction `notify` dans `backend/api/views.py`.
- **Hors ligne** : l'application a besoin du réseau. Une page d'erreur claire suffit pour commencer.
- **Jetons** : ils sont aujourd'hui dans des cookies lisibles par JavaScript. Sur mobile, les placer dans le stockage
  sécurisé de l'appareil.

Note : aucun fichier `capacitor.config` n'existe dans la copie locale de FarmHub. Si FarmHub a une configuration
ailleurs, la reprendre pour rester cohérent.
