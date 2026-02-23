# Build et release Windows — Tablerreur

Ce document décrit comment produire une release Windows avec installateur (NSIS et/ou MSI) pour Tablerreur, et comment **publier les .exe directement sur GitHub** (Releases).

## Prérequis

Sur une machine **Windows** :

- **Rust** : [rustup](https://rustup.rs/) (toolchain stable, cible `x86_64-pc-windows-msvc` par défaut)
- **Node.js** : LTS recommandé (pour `npm` et le CLI Tauri)
- **Python 3** : pour le sidecar (packaging PyInstaller) et les scripts du projet
- **Visual Studio Build Tools** (ou Visual Studio avec charge de travail C++) : requis pour la compilation Rust sur Windows (MSVC)
- **WebView2** : généralement déjà présent sur Windows 10/11 ; l’installateur peut proposer de le télécharger si absent
- **7-Zip** (optionnel) : pour générer le `.exe` portable tout-en-un ; sans 7-Zip, seul le `.zip` portable est produit

## Étapes

1. **Cloner le dépôt et installer les dépendances**

   ```powershell
   cd Tablerreur
   npm install
   ```

2. **Créer un environnement Python dédié (recommandé)**

   Pour éviter d’embarquer des modules inutiles (PySide6, etc.) dans le sidecar :

   ```powershell
   python -m venv .venv-sidecar
   .venv-sidecar\Scripts\Activate.ps1
   pip install -e ".[web]"
   pip install pyinstaller
   ```

   Puis lancer le build en laissant ce venv activé (ou en définissant `BUILD_VENV_PYTHON` vers `.venv-sidecar\Scripts\python.exe`).

3. **Builder le sidecar puis l’app Tauri**

   Une seule commande :

   ```powershell
   npm run build:windows
   ```

   Cela exécute :

   - `python scripts/build_sidecar.py` : packaging du backend Python en `src-tauri/binaries/tablerreur-backend-x86_64-pc-windows-msvc/` et mise à jour de `tauri.conf.json` (resources)
   - `npm run tauri build` : compilation Rust + génération des installateurs
   - `python scripts/build_portable_exe.py` : création d’un bundle portable (zip + exe tout-en-un si 7-Zip est disponible)

4. **Récupérer les artefacts**

   Dans `src-tauri/target/release/bundle/` :

   - **NSIS** : `nsis/Tablerreur_<version>_x64-setup.exe` — installateur classique (télécharge WebView2 si besoin)
   - **MSI** : `msi/Tablerreur_<version>_x64_fr-FR.msi` — installateur MSI en français (WiX, langue fr-FR)
   - **Portable** : `portable/Tablerreur_<version>_x64_portable.zip` — à extraire puis lancer `tablerreur.exe`
   - **Portable tout-en-un** : `portable/Tablerreur_<version>_x64_portable.exe` — un seul .exe qui s’extrait et lance l’app (généré seulement si [7-Zip](https://www.7-zip.org/) est installé ; sinon le script peut télécharger automatiquement le module 7zS.sfx)

## Publier les .exe sur GitHub (téléchargement direct)

Pour que les utilisateurs puissent **télécharger le .exe directement depuis GitHub** (sans build local) :

1. **Créer une release** sur le dépôt GitHub : onglet *Releases* → *Create a new release*.
2. Choisir un **tag** (ex. `v0.1.0`) et publier la release (draft ou immédiat).
3. Le workflow **Release Windows** (`.github/workflows/release-windows.yml`) se déclenche automatiquement :
   - build du sidecar Python puis de l’app Tauri sur un runner Windows ;
   - génération des installateurs (NSIS, MSI) et du bundle portable (zip + exe) ;
   - **attachement de tous les artefacts à la release** (ex. `Tablerreur_0.1.0_x64-setup.exe`, `Tablerreur_0.1.0_x64_portable.exe`, etc.).

Une fois le workflow terminé, les fichiers sont visibles dans la release sous *Assets* ; les utilisateurs peuvent télécharger le .exe directement depuis GitHub.

La version utilisée pour les noms de fichiers est dérivée du **tag** (ex. tag `v0.1.0` → version `0.1.0`).

## Configuration (tauri.conf.json)

- **Langue MSI** : `bundle.windows.wix.language` = `"fr-FR"`
- **WebView2** : `bundle.windows.webviewInstallMode.type` = `"downloadBootstrapper"` (installateur plus léger ; connexion requise pour installer WebView2 si absent)

Pour un déploiement hors ligne, on peut passer à `embedBootstrapper` ou `offlineInstaller` (voir [Tauri — Windows Installer](https://v2.tauri.app/distribute/windows-installer)).

## Dépannage

- **Sidecar introuvable** : exécuter d’abord `python scripts/build_sidecar.py` puis `npm run tauri build`.
- **Erreur MSVC** : vérifier que les Build Tools Visual Studio (C++) sont installés et que `cl` est disponible (ou relancer le « Developer Command Prompt »).
- **PyInstaller / imports** : si le sidecar plante au démarrage, vérifier les `hiddenimports` et `excludes` dans `scripts/build_sidecar.py`.
