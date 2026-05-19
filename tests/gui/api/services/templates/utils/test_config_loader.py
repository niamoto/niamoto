import yaml

from niamoto.gui.api.services.templates.utils import config_loader


def test_get_hierarchy_info_reads_relation_from_dict_transform_groups(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    transform_path = config_dir / "transform.yml"
    transform_path.write_text(
        yaml.safe_dump(
            {
                "groups": {
                    "taxons": {
                        "sources": [
                            {
                                "name": "occurrences",
                                "data": "occurrences",
                                "grouping": "taxons",
                                "relation": {
                                    "plugin": "nested_set",
                                    "key": "id_taxonref",
                                },
                            }
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    import_config = {
        "entities": {
            "datasets": {"occurrences": {}},
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "connector": {"extraction": {"levels": []}},
                }
            },
        }
    }
    monkeypatch.setattr(config_loader, "get_working_directory", lambda: work_dir)

    info = config_loader.get_hierarchy_info(import_config, "taxons")

    assert info["source_dataset"] == "occurrences"
    assert info["relation"] == {"plugin": "nested_set", "key": "id_taxonref"}
    assert info["is_hierarchical_grouping"] is True
