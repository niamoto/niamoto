import json
from typing import Optional, Any, Dict
from niamoto.core.models import TaxonRef, PlotRef
from shapely import wkt
from shapely.geometry import mapping


class BaseGenerator:
    """
    The BaseGenerator class provides common methods for generating data dictionaries.
    """

    def taxon_to_dict(self, taxon: TaxonRef, stats: Optional[Any]) -> Dict[str, Any]:
        taxon_dict = {
            "id": taxon.id,
            "full_name": taxon.full_name,
            "authors": taxon.authors,
            "rank_name": taxon.rank_name,
            "lft": taxon.lft,
            "rght": taxon.rght,
            "level": taxon.level,
            "parent_id": taxon.parent_id,
        }

        if stats:
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]
                    if value is not None:
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))
                else:
                    taxon_dict[key] = value

            taxon_dict["frequencies"] = frequencies

        return taxon_dict

    def plot_to_dict(self, plot: PlotRef, stats: Optional[Any]) -> Dict[str, Any]:
        plot_dict = {
            "id": plot.id,
            "id_locality": plot.id_locality,
            "locality": plot.locality,
            "substrat": plot.substrat,
            "geometry": mapping(wkt.loads(plot.geometry)) if isinstance(plot.geometry, str) else None,
        }

        if stats:
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]
                    if value is not None:
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))
                else:
                    plot_dict[key] = value

            plot_dict["frequencies"] = frequencies

        return plot_dict
