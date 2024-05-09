import pytest
from niamoto.core.utils.csv_utils import analyze_csv_data_types, is_duckdb_type_numeric


def test_analyze_csv_data_types():
    """
    Tests that a Taxon instance can be deleted from the database.
    """
    csv_file = "tests/test_data/data/sources/mock_taxonomy.csv"
    with open(csv_file, "w") as f:
        f.write(
            "id_taxon,full_name,rank_name,id_family,id_genus,id_species,id_infra,authors\n"
        )
        f.write("1,Famille1,id_family,1,,,,\n")
        f.write("2,Genre1,id_genus,1,2,,,Auteur1\n")
        f.write("3,Espece1,id_species,1,2,3,,Auteur2\n")
        f.write("4,Infra1,id_infra,1,2,3,4,Auteur3\n")
    expected_types = [
        ("id_taxon", "BIGINT"),
        ("full_name", "VARCHAR"),
        ("rank_name", "VARCHAR"),
        ("id_family", "BIGINT"),
        ("id_genus", "BIGINT"),
        ("id_species", "BIGINT"),
        ("id_infra", "BIGINT"),
        ("authors", "VARCHAR"),
    ]

    result = analyze_csv_data_types(csv_file)
    assert result == expected_types


def test_analyze_csv_data_types_invalid_file():
    """
    Test case for the analyze_csv_data_types function of the csv_utils module when provided with an invalid file.
    """
    invalid_csv_file = "tests/test_data/data/sources/invalid.csv"

    with pytest.raises(ValueError) as e:
        analyze_csv_data_types(invalid_csv_file)
    assert "Unable to analyze CSV file" in str(e.value)


def test_is_duckdb_type_numeric():
    """
    Test case for the is_duckdb_type_numeric function of the csv_utils module.
    """
    assert is_duckdb_type_numeric("INTEGER")
    assert is_duckdb_type_numeric("DOUBLE")
    assert not is_duckdb_type_numeric("VARCHAR")
    assert not is_duckdb_type_numeric("DATE")
