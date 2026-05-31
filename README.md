# CHgpx

> Visualisez, analysez et comparez vos traces GPS sur une carte topographique suisse.

---
## Aperçu

CHgpx est une application web
qui permet d'importer des traces au format GPX, 
de les afficher sur une carte topo (SwissTopo via WMTS)
et d'en calculer des statistiques (D+, distance).
De plus un comparateur avec des courses connues est intégré afin
de pouvoir évaluer son effort. 

---

## Fonctionnalités

-  **Carte interactive** — fond de carte swisstopo via WMTS
- **Import GPX** — chargement de fichiers `.gpx` directement depuis le navigateur
- **Statistiques** — distance totale, dénivelé positif, comparaison avec des courses emblématiques
- **Panneau de couches** — affichage/masquage individuel de chaque trace via des cases à cocher
- **Authentification** — inscription, connexion et déconnexion avec gestion de session
-  **Persistance** — stockage des géométries en base de données PostgreSQL/PostGIS

---

## Architecture
```
CHgpx/     
├── Production                    #Bundle du projet
        └──dist                   #Fichiers servant au frontend
              └──assets           #Fichier compilé par Vite (css et js)
              └──index.html       #Structure de l'interface
        └──app.py                 #Backend  

├── SQL_scripts                   #Scripts pour la création de la base de donnée
        └──geojson                #Table stockant les geojson
        └──utilisateur            #Table stockant les couples email/mots de passe
```
---

## Prérequis

- Python ≥ 3.10
- postgreSQL ≥ 16 (idéalement sur un VPS)

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/loicbaud/chGPX.git
```

### 2. Installation des dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Création de la base de donnée

```bash
CREATE DATABASE chGPX;
CREATE EXTENSION postgis;

\i /SQL_scripts/utilisateurs.sql #utiliser scp pour télécharger au préalable les scripts sur le VPS ou utiliser un logiciel comme pgAdmin
\i /SQL_scripts/geojson.sql
```

### 3. Lancement
```bash
python app.py #Windows
python3 app.py #Linux
```

---
## FRONTEND
Fonctions principales du frontend. Le code est également commenté. 
### `handleFiles` :
Pipeline de traitement des fichiers GPX. 
- **Input** : fichier GPX sélectionné par l'utilisateur
- Envoi au backend avec `sendToBackend` et lance le chainage des promesses

### `sendToBackend` :
Emballes les fichiers dans un FormData pour l'envoi au backend

### `loadGpsTracks` :
Récupère les traces GPS au format GeoJSON,  depuis le backend.
- **Input** : tableau de fichiers GPX
- Normalise le GeoJSON, créer un couche et une source vectorielle 
, stock la couche dans un objet et l'ajoute à la carte.

### `loadStats` :
Récupère les statistiques calculées par le backend.
- **Input** : tableau de fichiers GPX
- Envoi les fichiers au backend qui calcul 
les stats relatives au fichier envoyé. 
- Initalisation de la checkbox pour afficher les stats 
quand la premiere couche est chargée. 

### `layerPanel` :
- **Input** : tableau de fichiers GPX
- Permet de créer dynamiquement des cases 
à cocher. Listener sur la checkbox pour montrer 
/ cacher la couche correspondante.


---

## Auteurs

- **Loïc Baud** — [GitHub](https://github.com/loicbaud)
- **Nicolas Erne** — [GitHub](https://github.com/nico-ayo)

---

*© 2026 - Loïc Baud & Nicolas Erne - HEIG-VD*
