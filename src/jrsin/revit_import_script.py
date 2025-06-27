# -*- coding: utf-8 -*-
"""
Main script for importing DXF data into Revit
Compatible with RevitPythonShell and IronPython 2.7

Usage:
1. Copy this script to RevitPythonShell
2. Update the JSON_FILE_PATH variable to point to your revit_data.json file
3. Run the script in RevitPythonShell

The script will:
- Read the JSON data
- Create necessary family types
- Create Revit elements with appropriate parameters
- Set up shared parameters for data tracking
"""

import logging
import os

from Autodesk.Revit.DB import BuiltInCategory, Document, Transaction

from jrsin.data_models import RevitDataReader
from jrsin.parameter_manager import RevitParameterManager
from jrsin.revit_creator import RevitElementCreator

log = logging.getLogger(__name__)


def _get_env_path(var_name: str, *subdirs: str) -> str:
    """Get environment variable or return default path"""
    default_path = os.getenv("USERPROFILE", ".")
    library_path = os.getenv(var_name, default_path)
    return os.path.join(library_path, *subdirs)


# CONFIGURATION - UPDATE THESE PATHS
JSON_FILE_PATH = r"C:/path/to/your/revit_data.json"  # UPDATE THIS PATH!
REVIT_LIBRARY_PATH = _get_env_path("RSRG_BIBLIOTHEK", "Revit", "Familien")

# Family mapping - customize based on your family library
CUSTOM_FAMILY_MAPPING = {
    "WATER_SPECIAL": {
        "family_name": "Generic Model",  # Use built-in family or your custom family
        "type_name": "Water Special",
        "category": BuiltInCategory.OST_GenericModel,
    },
    "WATER_PIPE": {
        "family_name": "Generic Model",
        "type_name": "Water Pipe",
        "category": BuiltInCategory.OST_GenericModel,
    },
    "SHAFT": {
        "family_name": "Generic Model", 
        "type_name": "Shaft",
        "category": BuiltInCategory.OST_GenericModel,
    },
}

# Get the current Revit document
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


class RevitImportController:
    """Main controller for DXF data import into Revit"""

    def __init__(
        self, document: Document, json_file_path: str, revit_library_path: str
    ):
        self.document = document
        self.json_file_path = json_file_path

        # Initialize components
        self.data_reader = RevitDataReader(json_file_path)
        self.element_creator = RevitElementCreator(document, revit_library_path)
        self.parameter_manager = RevitParameterManager(doc)

        # Statistics
        self.stats = {
            "elements_processed": 0,
            "elements_created": 0,
            "elements_failed": 0,
            "types_created": 0,
            "parameters_created": 0,
        }
    
    def run_import(self, family_mapping=None, setup_parameters=True):
        """Run the complete import process"""
        log.info("=" * 60)
        log.info("Starting DXF Data Import to Revit")
        log.info("=" * 60)

        try:
            # Step 1: Load and analyze data
            log.info("1. Loading JSON data...")
            self.data_reader.load_data()
            data_stats = self.data_reader.get_statistics()
            self._print_data_statistics(data_stats)
            
            # Step 2: Setup parameters if requested
            if setup_parameters:
                log.info("2. Setting up shared parameters...")
                self._setup_shared_parameters()
            
            # Step 3: Create elements
            log.info("3. Creating Revit elements...")
            elements = self.data_reader.get_all_elements()
            created_elements = self._create_elements_batch(elements, family_mapping)
            
            # Step 4: Print results
            log.info("4. Import completed!")
            self._print_import_results()

            return created_elements

        except Exception as e:
            print("ERROR during import: {}".format(str(e)))
            if self.element_creator._current_tx:
                self.element_creator.rollback_transaction()
            return []

    def _print_data_statistics(self, stats):
        """Print statistics about loaded data"""
        log.info("Data Statistics:")
        log.info("  Total categories: {}".format(stats["total_categories"]))
        log.info("  Total elements: {}".format(stats["total_elements"]))
        log.info("  Unique object types: {}".format(stats["unique_object_types"]))

        log.info("\nElements by category:")
        for category, count in stats["elements_by_category"].items():
            log.info("  {}: {}".format(category, count))

        log.info("\nElements by type:")
        for obj_type, count in stats["elements_by_type"].items():
            log.info("  {}: {}".format(obj_type, count))

    def _setup_shared_parameters(self):
        """Setup shared parameters for the import"""
        try:
            created_params = self.parameter_manager.setup_dxf_import_parameters()
            self.stats["parameters_created"] = len(created_params)
            log.info("Created {} shared parameters".format(len(created_params)))
        except Exception as e:
            log.error("Warning: Failed to setup shared parameters: {}".format(str(e)))
            log.error("Elements will be created without custom parameters")

    def _create_elements_batch(self, elements, family_mapping):
        """Create elements in batches with progress reporting"""
        if family_mapping is None:
            family_mapping = CUSTOM_FAMILY_MAPPING

        created_elements = []
        batch_size = 50
        total_elements = len(elements)

        log.info(
            "Creating {} elements in batches of {}...".format(
                total_elements, batch_size
            )
        )

        for i in range(0, total_elements, batch_size):
            batch = elements[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_elements + batch_size - 1) // batch_size

            log.info(
                "Processing batch {}/{} ({} elements)...".format(
                    batch_num, total_batches, len(batch)
                )
            )

            try:
                # Create elements in this batch
                batch_created = self._create_elements_in_transaction(
                    batch, family_mapping
                )
                created_elements.extend(batch_created)

                # Update statistics
                self.stats["elements_processed"] += len(batch)
                self.stats["elements_created"] += len(batch_created)
                self.stats["elements_failed"] += len(batch) - len(batch_created)

                log.info(
                    "  Created: {}, Failed: {}".format(
                        len(batch_created), len(batch) - len(batch_created)
                    )
                )

            except Exception as e:
                log.error("  ERROR in batch {}: {}".format(batch_num, str(e)))
                self.stats["elements_processed"] += len(batch)
                self.stats["elements_failed"] += len(batch)

        return created_elements

    def _create_elements_in_transaction(self, elements_batch, family_mapping):
        """Create a batch of elements within a single transaction"""
        created_elements = []

        # Start transaction for this batch
        transaction = Transaction(self.document, "Import DXF Elements Batch")
        transaction.Start()

        try:
            for element_data in elements_batch:
                try:
                    # Create Revit element
                    revit_element = self.element_creator.create_element_from_data(
                        element_data, family_mapping
                    )

                    if revit_element:
                        # Apply data parameters
                        self.parameter_manager.apply_element_data_to_parameters(
                            revit_element, element_data
                        )
                        created_elements.append(revit_element)

                except Exception as e:
                    log.error("    Failed to create element: {}".format(str(e)))

            # Commit transaction
            transaction.Commit()

        except Exception as e:
            # Rollback on error
            transaction.RollBack()
            log.error("    Transaction failed: {}".format(str(e)))
            created_elements = []

        return created_elements

    def _print_import_results(self):
        """Print final import statistics"""
        log.info("\n" + "=" * 60)
        log.info("IMPORT RESULTS")
        log.info("=" * 60)
        log.info("Elements processed: {}".format(self.stats["elements_processed"]))
        log.info("Elements created: {}".format(self.stats["elements_created"]))
        log.info("Elements failed: {}".format(self.stats["elements_failed"]))
        log.info("Parameters created: {}".format(self.stats["parameters_created"]))

        if self.stats["elements_processed"] > 0:
            success_rate = (
                self.stats["elements_created"]
                * 100.0
                / self.stats["elements_processed"]
            )
            log.info("Success rate: {:.1f}%".format(success_rate))

        log.info("=" * 60)


def validate_requirements():
    """Validate that all requirements are met"""
    errors = []

    # Check JSON file path
    if not os.path.exists(JSON_FILE_PATH):
        errors.append("JSON file not found: {}".format(JSON_FILE_PATH))

    # Check Revit document
    if not doc:
        errors.append("No active Revit document")

    # Check if document has a shared parameter file
    try:
        param_file = doc.Application.OpenSharedParameterFile()
        if not param_file:
            print(
                "WARNING: No shared parameter file found. Parameters will not be created."
            )
    except:
        print("WARNING: Could not access shared parameter file.")

    return errors


def main():
    """Main execution function"""
    log.info("DXF to Revit Import Script")
    log.info("Compatible with RevitPythonShell and IronPython 2.7")
    log.info("JSON file: {}".format(JSON_FILE_PATH))

    # Validate requirements
    errors = validate_requirements()
    if errors:
        log.info("ERROR: Requirements not met:")
        for error in errors:
            log.info("  - {}".format(error))
        log.info("Please fix these issues and run the script again.")
        return

    # Create controller and run import
    try:
        controller = RevitImportController(doc, JSON_FILE_PATH, REVIT_LIBRARY_PATH)
        created_elements = controller.run_import(
            family_mapping=CUSTOM_FAMILY_MAPPING, setup_parameters=True
        )

        log.info("\nImport completed successfully!")
        log.info("Created {} elements".format(len(created_elements)))

    except Exception as e:
        log.info("\nFATAL ERROR: {}".format(str(e)))
        import traceback

        traceback.print_exc()


# Example of how to run with custom settings
def run_custom_import():
    """Example of running import with custom settings"""
    
    # Custom family mapping
    custom_mapping = {
        "WATER_SPECIAL": {
            "family_name": "My Custom Water Family",
            "type_name": "Special Type",
            "category": BuiltInCategory.OST_GenericModel,
        }
    }

    # Run import
    controller = RevitImportController(doc, JSON_FILE_PATH, REVIT_LIBRARY_PATH)
    elements = controller.run_import(
        family_mapping=custom_mapping, setup_parameters=True
    )

    return elements


# For testing individual components
def test_data_reader():
    """Test the data reader functionality"""
    reader = RevitDataReader(JSON_FILE_PATH)
    reader.load_data()
    stats = reader.get_statistics()

    log.info("Test Results:")
    for key, value in stats.items():
        log.info("  {}: {}".format(key, value))

    return reader


if __name__ == "__main__":
    # Run the main import
    main()
    
    # Uncomment these lines to run tests or custom imports:
    # test_data_reader()
    # run_custom_import()
