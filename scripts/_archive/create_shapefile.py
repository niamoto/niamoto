import geopandas as gpd
import requests
import io
import zipfile
from pathlib import Path


SHAPEFILE_SUFFIXES = {".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj"}


def _safe_zip_member_path(extract_to: Path, member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError(f"Unsafe ZIP member path: {member_name}")

    destination = (extract_to / member_path).resolve()
    destination.relative_to(extract_to.resolve())
    return destination


def _extract_shapefile_members(z: zipfile.ZipFile, extract_to="."):
    extract_root = Path(extract_to)
    extract_root.mkdir(parents=True, exist_ok=True)

    members_to_extract = []
    for info in z.infolist():
        if info.is_dir():
            continue
        suffix = Path(info.filename).suffix.lower()
        if suffix not in SHAPEFILE_SUFFIXES:
            continue
        members_to_extract.append(
            (info, suffix, _safe_zip_member_path(extract_root, info.filename))
        )

    extracted_shp = None
    for info, suffix, destination in members_to_extract:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as source, destination.open("wb") as target:
            target.write(source.read())
        if suffix == ".shp" and extracted_shp is None:
            extracted_shp = destination

    return str(extracted_shp) if extracted_shp else None


def download_extract_zip(url, extract_to="."):
    # Télécharger le fichier ZIP
    print(f"Téléchargement des données depuis {url}...")
    response = requests.get(url)
    response.raise_for_status()

    # Extraire le contenu
    print("Extraction des données...")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    return _extract_shapefile_members(z, extract_to)


def main():
    # URL des pays à l'échelle 1:110m de Natural Earth
    url = (
        "https://naturalearth.s3.amazonaws.com/110m_cultural/"
        "ne_110m_admin_0_countries.zip"
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


if __name__ == "__main__":
    main()
