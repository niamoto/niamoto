# src/niamoto/core/plugins/exporters/dwc_archive_exporter.py

"""
Darwin Core Archive Exporter plugin for generating standard DwC-A files.

This exporter generates a compliant Darwin Core Archive containing:
- occurrence.csv: All occurrence records in CSV format
- meta.xml: Structure description of the archive
- eml.xml: Ecological Metadata Language file with dataset metadata
- dwc-archive.zip: Complete archive ready for GBIF and other biodiversity portals
"""

import csv
import gzip
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom

from pydantic import BaseModel, Field, ConfigDict

from niamoto.common.database import Database
from niamoto.common.exceptions import ProcessError
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from niamoto.core.plugins.models import TargetConfig, BasePluginParams
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

# Check if we're in CLI context for progress display
try:
    from niamoto.cli.utils.progress import ProgressManager

    CLI_CONTEXT = True
except ImportError:
    CLI_CONTEXT = False
    ProgressManager = None


class DatasetMetadata(BaseModel):
    """Metadata for the Darwin Core Archive dataset."""

    title: str = Field(default="Niamoto Biodiversity Data")
    description: str = Field(default="Biodiversity occurrence data from Niamoto")
    publisher: str = Field(default="Niamoto")
    contact_name: str = Field(default="Niamoto Project")
    contact_email: str = Field(default="contact@niamoto.nc")
    rights: str = Field(default="CC-BY-4.0")
    citation: Optional[str] = None
    homepage: Optional[str] = None
    language: str = Field(default="fr")
    geographic_coverage: Optional[str] = Field(default="New Caledonia")


class DwcArchiveExporterParams(BasePluginParams):
    """Parameters for the Darwin Core Archive exporter."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Generate standard Darwin Core Archive (DwC-A)",
            "examples": [
                {
                    "output_dir": "exports/dwc-archive",
                    "archive_name": "dwc-archive.zip",
                }
            ],
        }
    )

    output_dir: str = Field(
        default="exports/dwc-archive",
        description="Directory where DwC-A will be generated",
    )
    archive_name: str = Field(
        default="dwc-archive.zip", description="Name of the output ZIP archive"
    )
    metadata: DatasetMetadata = Field(default_factory=DatasetMetadata)
    compress_csv: bool = Field(
        default=False, description="Compress CSV files with gzip"
    )
    delimiter: str = Field(
        default="\t", description="CSV field delimiter (tab by default)"
    )
    encoding: str = Field(default="utf-8", description="Character encoding")


@register("dwc_archive_exporter", PluginType.EXPORTER)
class DwcArchiveExporter(ExporterPlugin):
    """Generates standard Darwin Core Archive files."""

    def __init__(self, db: Database):
        """Initialize the exporter with database connection."""
        super().__init__(db)
        self.stats: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "total_occurrences": 0,
            "total_taxa": 0,
        }

    def export(
        self,
        target_config: TargetConfig,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """
        Execute the Darwin Core Archive export process.

        Args:
            target_config: The validated configuration for this export target
            repository: The Database instance to fetch data from
            group_filter: Optional filter to process only specific groups
        """
        logger.info(
            f"Starting Darwin Core Archive export for target: '{target_config.name}'"
        )
        self.stats["start_time"] = datetime.now()

        try:
            # Validate parameters
            params = DwcArchiveExporterParams.model_validate(target_config.params)
            output_dir = Path(params.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process groups and collect all occurrences
            all_occurrences = []
            dwc_terms = set()

            groups_to_process = target_config.groups or []
            if group_filter:
                groups_to_process = [
                    g for g in groups_to_process if g.group_by == group_filter
                ]

            if CLI_CONTEXT and ProgressManager:
                progress_manager = ProgressManager()
                with progress_manager.progress_context() as pm:
                    all_occurrences, dwc_terms = (
                        self._collect_occurrences_with_progress(
                            groups_to_process, repository, pm
                        )
                    )
            else:
                all_occurrences, dwc_terms = self._collect_occurrences(
                    groups_to_process, repository
                )

            if not all_occurrences:
                logger.warning("No occurrences found to export")
                return

            # Generate archive files
            self._generate_archive(all_occurrences, dwc_terms, output_dir, params)

            logger.info(
                f"Darwin Core Archive generated: {output_dir / params.archive_name}"
            )

        except Exception as e:
            logger.error(f"Darwin Core Archive export failed: {str(e)}")
            raise ProcessError(f"Darwin Core Archive export failed: {str(e)}")
        finally:
            self.stats["end_time"] = datetime.now()
            logger.info(f"Export stats: {self.stats}")

    def _collect_occurrences(
        self,
        groups: List[Any],
        repository: Database,
    ) -> tuple[List[Dict[str, Any]], set]:
        """Collect all occurrences from all groups."""
        all_occurrences = []
        dwc_terms = set()

        for group_config in groups:
            # Handle both dict and object formats
            group_name = (
                group_config.get("group_by")
                if isinstance(group_config, dict)
                else group_config.group_by
            )
            logger.info(f"Processing group: {group_name}")

            # Get data for this group
            group_data = self._fetch_group_data(repository, group_name)

            if not group_data:
                logger.warning(f"No data found for group: {group_name}")
                continue

            self.stats["total_taxa"] += len(group_data)

            # Process each item with transformer
            for item in group_data:
                occurrences = self._apply_transformer(item, group_config)

                if occurrences and isinstance(occurrences, list):
                    all_occurrences.extend(occurrences)

                    # Collect all DwC terms used
                    for occ in occurrences:
                        dwc_terms.update(occ.keys())

        self.stats["total_occurrences"] = len(all_occurrences)
        return all_occurrences, dwc_terms

    def _collect_occurrences_with_progress(
        self,
        groups: List[Any],
        repository: Database,
        progress_manager: "ProgressManager",
    ) -> tuple[List[Dict[str, Any]], set]:
        """Collect all occurrences with progress tracking."""
        all_occurrences = []
        dwc_terms = set()

        for group_config in groups:
            # Handle both dict and object formats
            group_name = (
                group_config.get("group_by")
                if isinstance(group_config, dict)
                else group_config.group_by
            )
            logger.info(f"Processing group: {group_name}")

            # Get data for this group
            group_data = self._fetch_group_data(repository, group_name)

            if not group_data:
                logger.warning(f"No data found for group: {group_name}")
                progress_manager.add_warning(f"No data found for group: {group_name}")
                continue

            self.stats["total_taxa"] += len(group_data)

            # Add progress task
            task_name = f"dwc_{group_name}"
            progress_manager.add_task(
                task_name,
                f"Collecting DwC occurrences from {group_name}",
                total=len(group_data),
            )

            # Process each item with transformer
            for item in group_data:
                try:
                    occurrences = self._apply_transformer(item, group_config)

                    if occurrences and isinstance(occurrences, list):
                        all_occurrences.extend(occurrences)

                        # Collect all DwC terms used
                        for occ in occurrences:
                            dwc_terms.update(occ.keys())
                except Exception as e:
                    logger.error(f"Error processing item: {str(e)}")
                    progress_manager.add_error(f"Error processing item: {str(e)}")

                progress_manager.update_task(task_name, advance=1)

            progress_manager.complete_task(
                task_name, f"Collected {len(all_occurrences)} occurrences"
            )

        self.stats["total_occurrences"] = len(all_occurrences)
        return all_occurrences, dwc_terms

    def _fetch_group_data(
        self, repository: Database, group_name: str
    ) -> List[Dict[str, Any]]:
        """Fetch data for a group from the repository."""
        try:
            from sqlalchemy import text
            import json

            query = text(f"SELECT * FROM {group_name}")

            with repository.engine.connect() as connection:
                result_proxy = connection.execute(query)
                rows = result_proxy.fetchall()
                columns = result_proxy.keys()

                if rows:
                    result = []
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        item = {}

                        for col_name, col_value in row_dict.items():
                            if col_value:
                                try:
                                    if isinstance(col_value, str):
                                        data = json.loads(col_value)
                                    else:
                                        data = col_value

                                    item[col_name] = data

                                    if isinstance(data, dict):
                                        item.update(data)
                                except (json.JSONDecodeError, TypeError):
                                    item[col_name] = col_value

                        result.append(item)

                    return result
                else:
                    return []

        except Exception as e:
            logger.error(f"Error fetching data for group {group_name}: {str(e)}")
            return []

    def _apply_transformer(
        self, item: Dict[str, Any], group_config: Any
    ) -> List[Dict[str, Any]]:
        """Apply transformer plugin to the data."""
        try:
            # Handle both dict and object formats
            if isinstance(group_config, dict):
                transformer_plugin = group_config.get("transformer_plugin")
                transformer_params = group_config.get("transformer_params") or {}
            else:
                transformer_plugin = getattr(group_config, "transformer_plugin", None)
                transformer_params = (
                    getattr(group_config, "transformer_params", None) or {}
                )

            if not transformer_plugin:
                logger.warning("No transformer plugin configured")
                return []

            # Get the transformer plugin
            transformer_class = PluginRegistry.get_plugin(
                transformer_plugin, PluginType.TRANSFORMER
            )

            if not transformer_class:
                logger.error(f"Transformer plugin '{transformer_plugin}' not found")
                return []

            # Instantiate and configure the transformer
            transformer = transformer_class(self.db)

            # Apply transformation
            result = transformer.transform(item, transformer_params)

            return result if isinstance(result, list) else []

        except Exception as e:
            logger.error(f"Transformer error: {str(e)}")
            return []

    def _generate_archive(
        self,
        occurrences: List[Dict[str, Any]],
        dwc_terms: set,
        output_dir: Path,
        params: DwcArchiveExporterParams,
    ) -> None:
        """Generate the complete Darwin Core Archive."""
        # Sort terms for consistent column order
        sorted_terms = sorted(dwc_terms)

        # Generate CSV file
        csv_filename = "occurrence.csv"
        if params.compress_csv:
            csv_filename += ".gz"

        csv_path = output_dir / csv_filename
        self._generate_occurrence_csv(occurrences, sorted_terms, csv_path, params)

        # Generate meta.xml
        meta_path = output_dir / "meta.xml"
        self._generate_meta_xml(sorted_terms, csv_filename, meta_path, params)

        # Generate eml.xml
        eml_path = output_dir / "eml.xml"
        self._generate_eml_xml(eml_path, params.metadata)

        # Create ZIP archive
        archive_path = output_dir / params.archive_name
        self._create_zip_archive(archive_path, [csv_path, meta_path, eml_path])

    def _generate_occurrence_csv(
        self,
        occurrences: List[Dict[str, Any]],
        terms: List[str],
        output_path: Path,
        params: DwcArchiveExporterParams,
    ) -> None:
        """Generate occurrence.csv file."""
        logger.info(f"Generating occurrence CSV: {output_path}")

        if params.compress_csv:
            file_handle = gzip.open(output_path, "wt", encoding=params.encoding)
        else:
            file_handle = open(output_path, "w", encoding=params.encoding, newline="")

        try:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=terms,
                delimiter=params.delimiter,
                extrasaction="ignore",
            )

            writer.writeheader()

            for occurrence in occurrences:
                # Convert all values to strings
                row = {
                    k: str(v) if v is not None else "" for k, v in occurrence.items()
                }
                writer.writerow(row)

        finally:
            file_handle.close()

        logger.info(f"Generated {len(occurrences)} occurrence records")

    def _generate_meta_xml(
        self,
        terms: List[str],
        csv_filename: str,
        output_path: Path,
        params: DwcArchiveExporterParams,
    ) -> None:
        """Generate meta.xml file."""
        logger.info(f"Generating meta.xml: {output_path}")

        # Create XML structure
        archive = ET.Element(
            "archive",
            attrib={"xmlns": "http://rs.tdwg.org/dwc/text/", "metadata": "eml.xml"},
        )

        core = ET.SubElement(
            archive,
            "core",
            attrib={
                "encoding": params.encoding,
                "fieldsTerminatedBy": params.delimiter,
                "linesTerminatedBy": "\\n",
                "fieldsEnclosedBy": "",
                "ignoreHeaderLines": "1",
                "rowType": "http://rs.tdwg.org/dwc/terms/Occurrence",
            },
        )

        files = ET.SubElement(core, "files")
        ET.SubElement(files, "location").text = csv_filename

        # Add field definitions
        for index, term in enumerate(terms):
            field_attrib = {
                "index": str(index),
                "term": f"http://rs.tdwg.org/dwc/terms/{term}",
            }
            ET.SubElement(core, "field", attrib=field_attrib)

        # Pretty print XML
        xml_str = minidom.parseString(
            ET.tostring(archive, encoding="unicode")
        ).toprettyxml(indent="  ")

        # Remove extra blank lines
        xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    def _generate_eml_xml(
        self,
        output_path: Path,
        metadata: DatasetMetadata,
    ) -> None:
        """Generate eml.xml file."""
        logger.info(f"Generating eml.xml: {output_path}")

        # Create EML structure
        eml = ET.Element(
            "eml:eml",
            attrib={
                "xmlns:eml": "eml://ecoinformatics.org/eml-2.1.1",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd",
                "packageId": f"niamoto-{datetime.now().strftime('%Y%m%d')}",
                "system": "http://niamoto.nc",
                "scope": "system",
                "xml:lang": metadata.language,
            },
        )

        dataset = ET.SubElement(eml, "dataset")

        # Title
        ET.SubElement(dataset, "title").text = metadata.title

        # Creator/Contact
        creator = ET.SubElement(dataset, "creator")
        ET.SubElement(creator, "individualName").text = metadata.contact_name
        ET.SubElement(creator, "electronicMailAddress").text = metadata.contact_email

        # Publisher
        ET.SubElement(dataset, "publisher").text = metadata.publisher

        # Pub date
        ET.SubElement(dataset, "pubDate").text = datetime.now().strftime("%Y-%m-%d")

        # Language
        ET.SubElement(dataset, "language").text = metadata.language

        # Abstract
        abstract = ET.SubElement(dataset, "abstract")
        ET.SubElement(abstract, "para").text = metadata.description

        # Intellectual Rights
        intellectualRights = ET.SubElement(dataset, "intellectualRights")
        ET.SubElement(intellectualRights, "para").text = metadata.rights

        # Geographic Coverage
        if metadata.geographic_coverage:
            coverage = ET.SubElement(dataset, "coverage")
            geographicCoverage = ET.SubElement(coverage, "geographicCoverage")
            ET.SubElement(
                geographicCoverage, "geographicDescription"
            ).text = metadata.geographic_coverage

        # Contact
        contact = ET.SubElement(dataset, "contact")
        ET.SubElement(contact, "individualName").text = metadata.contact_name
        ET.SubElement(contact, "electronicMailAddress").text = metadata.contact_email

        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(eml, encoding="unicode")).toprettyxml(
            indent="  "
        )

        # Remove extra blank lines
        xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    def _create_zip_archive(
        self,
        archive_path: Path,
        files: List[Path],
    ) -> None:
        """Create ZIP archive."""
        logger.info(f"Creating Darwin Core Archive: {archive_path}")

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if file_path.exists():
                    zipf.write(file_path, file_path.name)

        logger.info(f"Archive created successfully: {archive_path}")
