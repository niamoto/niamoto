# graph_generator.py
from typing import Dict, Any

import matplotlib.pyplot as plt
import io
import base64


class GraphGenerator:
    @staticmethod
    def generate_elevation_distribution_graph(data: Dict[str, Any]) -> str:
        # Code pour générer le graphique
        fig, ax = plt.subplots(figsize=(10, 8))
        # ... (code pour créer le graphique)

        # Sauvegarder le graphique en format base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        graphic = base64.b64encode(image_png)
        graphic = graphic.decode('utf-8')

        return graphic

    @staticmethod
    def generate_forest_percentage_graph(data: Dict[str, Any]) -> str:
        # Code similaire pour un autre type de graphique
        pass