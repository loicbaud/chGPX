from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
import json
import geopandas as gpd
import gpxpy

#Dictionnaire de configuration de la base de donnée psql
db_config = {
    "dbname": "chGPX",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}
app = Flask(__name__,
            static_folder='dist',
            static_url_path='')


#autorisation des cookies et de CORS car le backend et le frontend ne sont pas sur le même port (5173 vs 8000)
app.config.update(
SESSION_COOKIE_SAMESITE='None',
SESSION_COOKIE_SECURE=True)

CORS(app,supports_credentials=True)
app.config['SECRET_KEY'] = 'clé secrète à changer'

@app.route('/register', methods=['POST'])
def register():
    """
    inputs :
        contenu (json)
            contient l'email et le mot de passe
    returns :
        json
            message indiquant l'état de la requête (réussite vs potentiel échec) + code http

    La route permet de créer un nouvel utilisateur dans la base de donnée
    """
    try:
        contenu = request.json
        email = contenu["email"]
        mdp = contenu["mdp"]

        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            insert_query = "INSERT INTO utilisateurs (email,mdp) VALUES (%s,%s)"
            values = (email, mdp)
            cursor.execute(insert_query, values)

            connection.commit()
            cursor.close()

            session['logged_in'] = True
            session['username'] = email
            print(session)

            return jsonify({'message':'Insertion réalisée avec succès',
                            'Logged_in':session['logged_in']}),201
        except Exception as e:
            return jsonify({'erreur': str(e)}), 400

    except Exception as e:
        return jsonify({'erreur': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    """
    inputs :
        contenu (json)
            contient l'email et le mot de passe
        returns :
        json
            message indiquant l'état de la requête (réussite vs potentiel échec) + code http

    La route permet de rechercher un utilisateur dans la base de donnée et de le logguer
    La requête SQL recherche le nombre de couples email + mot de passe comme l'email est UNIQUE alors si le nombre renvoyé par count(*) est > 0 alors
    les crédits d'authentification sont correctes
    """
    try:
        contenu = request.json
        email = contenu["email"]
        mdp = contenu["mdp"]

        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            select_query = "SELECT count(*) FROM utilisateurs WHERE email = %s AND mdp = %s"
            values = (email,mdp)

            try:
                cursor.execute(select_query, values)
                count = cursor.fetchone()[0]

                if count > 0:
                    session['logged_in'] = True
                    session['username'] = email
                    print(session)
                    return jsonify({'message':'Login réalisé avec succès',
                                    'logged_in':session['logged_in']}),202

                else:
                    return jsonify({'erreur': 'Crédits invalides'}), 401

            except Exception as e:
                return jsonify({'erreur': str(e)}), 400

        except Exception as e:
            return jsonify({'erreur': str(e)}), 400


    except Exception as e:
        return jsonify({'erreur': str(e)}), 400

@app.route('/logout',methods=['POST'])
def logout():
    """
    inputs :
        un appel du frontend mais sans transmission d'information
    ouputs :
        json
            Contient un message de réussite + un code http

    La route permet la déconnexion de l'utilisateur en vidant le cookie
    """
    session.clear()
    print(session)
    return jsonify({'message':'Déconnexion réussie'}),200

@app.route('/upload-gpx', methods=['POST'])
def upload_file():
    """
    inputs :
        session (json)
            Contient le nom d'utilisateur et le status de sa session
        gpx_file (json)
            Contient le fichier transmis par l'utilisateur au format .gpx
    output :
        json
             Contient un message + un code http

    La route permet d'envoyer un fichier dans la base de donnée. Le fichier est utilisé au format geojson dans le but de gagner en temps de calcul
    (conversion réalisée avec geopandas).
    """

    #Vérification de la connexion de l'utilisateur
    if not session:
        print("Non valide")
        return jsonify({'erreur':'Utilisateur non connecté'}), 401

    #Vérification que le fichier est utilisable
    if 'gpx_file' not in request.files:
        return jsonify({'erreur': 'Aucun fichier reçu ou clé incorrecte'}), 400

    gpx_files = request.files.getlist('gpx_file')
    email = session['username']

    #Vérification que le fichier n'est pas vide
    if not gpx_files or gpx_files[0].filename == '':
        return jsonify({'erreur': 'Fichier vide'}), 400

    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        for gpx_file in gpx_files:

            #Conversion en geojson avec geopandas
            gdf = gpd.read_file(gpx_file, layer="tracks")
            geojson_file = gdf.to_json(na='drop')
            tracks_data = json.loads(geojson_file)

            for feature in tracks_data["features"]:
                properties = feature["properties"]
                geometry = feature["geometry"]
                geometry_json = json.dumps(geometry)

                insert_query = sql.SQL("INSERT INTO geojson (geometry, name, type, email) VALUES (ST_GeomFromGEOJSON(%s), %s, %s, %s)")
                values = (geometry_json, properties.get("name", None), properties.get("type", None),email)

                cursor.execute(insert_query, values)

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'message': 'Fichiers geojson reçus'}), 200

    except Exception as e:
        return jsonify({'erreur': str(e)}), 400

@app.route('/download-geojson', methods=['POST'])
def download_geojson():
    """
    input
        session (json)
            Contient le nom d'utilisateur et le status de sa session
    output :
        geojson_collection (json
            listes des fichiers geojson + code http ou message d'erreur + code http

    La route permet l'envoi des fichiers geojson contenu dans la base de donnée et qui sont liés à l'adresse mail de l'utilisateur. L'envoi est une liste
    de fichier geojson
    """
    print(session)

    #Vérification que l'utilisateur est connecté
    if not session:
        print(session)
        print("Non valide")
        return jsonify({'erreur': 'Utilisateur non connecté'}), 401

    try:
        email = session['username']

        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        #Récupération des fichiers associés à l'adresse mail
        select_query = f"SELECT ST_AsGeoJSON(geometry) AS geojson FROM geojson WHERE email = '{email}'"
        print(select_query)

        cursor.execute(select_query)

        rows = cursor.fetchall()

        connection.close()

        #Création d'une liste contenant le contenu de la requête SQL
        features = []
        for row in rows:
            geojson = json.loads(row[0])
            features.append(geojson)

        #Conversion de la liste en un json
        geojson_collection = {
            "type": "FeatureCollection",
            "features": features
        }

        return jsonify(geojson_collection), 200
    except Exception as e:
        return jsonify({'erreur' : e}), 400

@app.route('/download-geojson-test', methods=['POST'])
def download_geojson_test():
    """
    input :
        un appel du frontend mais sans transmission d'information
    output :
        geojson_collection (json
            listes des fichiers geojson + code http ou message d'erreur + code http

    La route fonctionne comme la route download-geojson mais sans utilisation du login. La route renvoie l'entièreté du contenu de la base de donnée.
    Dans la version actuelle du projet cette route n'est plus utilisée mais elle est conservée à titre de backup.
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # une seule requête qui récupère les deux colonnes
        cursor.execute("SELECT ST_AsGeoJSON(geometry), name FROM geojson ORDER BY id DESC LIMIT 1")
        rows = cursor.fetchall()
        connection.close()

        features = []
        for row in rows:
            features.append({
                "type": "Feature",
                "geometry": json.loads(row[0]),  # row[0] = géométrie
                "properties": { "name": row[1] } # row[1] = nom texte brut
            })

        return jsonify({"type": "FeatureCollection", "features": features}), 200

    except Exception as e:
        return jsonify({'erreur': str(e)}), 400

@app.route('/stats', methods=['POST'])
def stats():
    """
    input :  récupère une liste de gpx transmis par le frontend

    output : json contenant les statistiques des traces elle-memes (distance totale et D+) et les
    statistiques d'équivalence en dur pour effectuer les comparaisons sur l'UI

    """
    try:
        gpx_files = request.files.getlist('gpx_file')  # récupère la liste
        distance_totale = 0
        d_plus_total = 0

        for gpx_file in gpx_files:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    distance_totale += segment.length_2d()
                    uphill, _ = segment.get_uphill_downhill()
                    d_plus_total += uphill

        d_plus_UTMB = 10000
        dist_UTMB = 171000
        d_plus_DiagFou = 10500
        dist_DiagFou = 175000
        dist_Marathon = 42195
        d_plus_SwissMan = 5575
        dist_SwissMan = 226000
        d_plus_ultraTerrestre = 14330
        dist_ultraTerrestre = 224000

        equi_UTMB = (distance_totale + d_plus_total) / (d_plus_UTMB + dist_UTMB)
        equi_DiagFou = (distance_totale + d_plus_total) / (d_plus_DiagFou + dist_DiagFou)
        equi_Marathon = (distance_totale) / (dist_Marathon)
        equi_SwissMan = (distance_totale + d_plus_total) / (d_plus_SwissMan + dist_SwissMan)
        equi_ultraTerrestre = (distance_totale + d_plus_total) / (dist_ultraTerrestre + d_plus_ultraTerrestre)

        return jsonify({
            'distance_km': round(distance_totale / 1000, 2),
            'd_plus': round(d_plus_total),
            'equi_UTMB' : round(equi_UTMB, 2),
            'equi_DiagFou': round(equi_DiagFou, 2),
            'equi_Marathon': round(equi_Marathon, 2),
            'equi_SwissMan': round(equi_SwissMan, 2),
            'equi_ultraTerrestre': round(equi_ultraTerrestre, 2),
        }), 200

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('dist', 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory('dist', 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=8000)