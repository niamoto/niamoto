import geopandas as gpd
import requests
import io
import zipfile
import os


def download_extract_zip(url, extract_to="."):
    # Télécharger le fichier ZIP
    print(f"Téléchargement des données depuis {url}...")
    response = requests.get(url)
    response.raise_for_status()

    # Extraire le contenu
    print("Extraction des données...")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    z.extractall(extract_to)

    # Trouver le fichier .shp dans les fichiers extraits
    shp_files = [f for f in z.namelist() if f.endswith(".shp")]
    return os.path.join(extract_to, shp_files[0]) if shp_files else None


# URL des pays à l'échelle 1:110m de Natural Earth
url = (
    "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
)

# Télécharger et extraire
shp_path = download_extract_zip(url)

if shp_path:
    # Lire le shapefile
    print(f"Lecture du shapefile: {shp_path}")
    world = gpd.read_file(shp_path)

    # Filtrer pour ne garder que le Cameroun et le Gabon
    cameroon_gabon = world[world["NAME"].isin(["Cameroon", "Gabon"])]

    # Si aucun pays trouvé, chercher avec 'NAME_EN' ou d'autres colonnes possibles
    if len(cameroon_gabon) == 0:
        print("Recherche des pays par noms alternatifs...")
        # Vérifier les colonnes disponibles
        print("Colonnes disponibles:", world.columns)

        # Essayer avec d'autres colonnes possibles
        for col in ["NAME_EN", "ADMIN", "SOVEREIGNT"]:
            if col in world.columns:
                cameroon_gabon = world[world[col].isin(["Cameroon", "Gabon"])]
                if len(cameroon_gabon) > 0:
                    print(f"Pays trouvés dans la colonne '{col}'")
                    break

    # Vérifier que nous avons trouvé les pays
    if len(cameroon_gabon) > 0:
        print(f"Pays trouvés: {cameroon_gabon['NAME'].values}")

        # Créer un nouveau GeoDataFrame avec des attributs personnalisés
        combined = gpd.GeoDataFrame(
            {
                "name": cameroon_gabon["NAME"].values,
                "code": cameroon_gabon["ISO_A3"].values,
                "region": ["Central Africa"] * len(cameroon_gabon),
                "geometry": cameroon_gabon["geometry"].values,
            },
            crs=cameroon_gabon.crs,
        )

        # Sauvegarder en shapefile
        output_file = "cameroon_gabon.shp"
        combined.to_file(output_file)
        print(f"Shapefile '{output_file}' créé avec succès!")

        # Sauvegarder aussi en GPKG pour tester
        gpkg_file = "cameroon_gabon.gpkg"
        combined.to_file(gpkg_file, driver="GPKG")
        print(f"GeoPackage '{gpkg_file}' créé avec succès!")
    else:
        print("Impossible de trouver le Cameroun et le Gabon dans les données.")
else:
    print("Impossible de trouver un fichier shapefile dans l'archive téléchargée.")
