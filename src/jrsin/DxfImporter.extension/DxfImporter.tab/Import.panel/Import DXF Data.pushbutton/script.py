# -*- coding: utf-8 -*-
"""
Import DXF Data - pyRevit Button Script
IronPython 2.7 compatible

This script provides a UI for importing DXF data from JSON files into Revit.
"""

import os

# Revit API imports
from Autodesk.Revit.DB import Document, Transaction

# Our custom modules from lib directory
from data_models import RevitDataReader
from parameter_manager import RevitParameterManager
from revit_creator import RevitElementCreator

# pyRevit imports
from pyrevit import forms, script
from pyrevit.forms import WPFWindow


class DxfImportDialog(WPFWindow):
    """Main dialog for DXF import configuration"""
    
    def __init__(self):
        # type: () -> None
        """Initialize the dialog"""
        self.json_file_path = None
        self.setup_parameters = True
        self.family_mapping = self._get_default_family_mapping()
        self.selected_categories = None
        
        # Create simple form using pyRevit forms
        self._setup_ui()
    
    def _setup_ui(self):
        # type: () -> None
        """Setup the user interface"""
        # This is a simplified version - we'll use pyRevit's built-in dialogs
        pass
    
    def _get_default_family_mapping(self):
        # type: () -> dict
        """Get default family mapping"""
        return {
            "WATER_SPECIAL": {
                "family_name": "Generic Model",
                "type_name": "Water Special",
                "category": "OST_GenericModel",
            },
            "WATER_PIPE": {
                "family_name": "Generic Model", 
                "type_name": "Water Pipe",
                "category": "OST_GenericModel",
            },
            "SHAFT": {
                "family_name": "Generic Model",
                "type_name": "Shaft", 
                "category": "OST_GenericModel",
            },
        }


class DxfImportController(object):
    """Main controller for DXF import process"""
    
    def __init__(self, document: Document):
        # type: (Document) -> None
        """Initialize controller with Revit document"""
        self.document = document
        self.output = script.get_output()
        
        # Initialize components
        self.data_reader = None
        self.element_creator = RevitElementCreator(document)
        self.parameter_manager = RevitParameterManager(document)
        
        # Statistics
        self.stats = {
            "elements_processed": 0,
            "elements_created": 0,
            "elements_failed": 0,
            "parameters_created": 0,
        }
    
    def select_json_file(self):
        # type: () -> str or None
        """Show file selection dialog for JSON file"""
        try:
            json_file = forms.pick_file(
                file_ext='json',
                title='Select DXF Data JSON File',
                init_dir=os.path.expanduser('~')
            )
            return json_file
        except Exception:
            return None
    
    def show_import_dialog(self):
        # type: () -> dict or None
        """Show configuration dialog and return settings"""
        # Simple configuration using pyRevit forms
        options = [
            "Setup shared parameters",
            "Skip parameter setup"
        ]
        
        param_choice = forms.CommandSwitchWindow.show(
            options,
            message="Choose parameter setup option:"
        )
        
        if param_choice is None:
            return None
            
        setup_parameters = param_choice == "Setup shared parameters"
        
        return {
            "setup_parameters": setup_parameters,
            "family_mapping": None  # Use default
        }
    
    def run_import(self, json_file_path, settings):
        # type: (str, dict) -> list
        """Run the complete import process"""
        self.output.print_md("# DXF Data Import")
        self.output.print_md("---")
        
        try:
            # Step 1: Load and analyze data
            self.output.print_md("## 1. Loading JSON data...")
            self.data_reader = RevitDataReader(json_file_path)
            self.data_reader.load_data()
            
            data_stats = self.data_reader.get_statistics()
            self._print_data_statistics(data_stats)
            
            # Step 2: Setup parameters if requested
            if settings.get("setup_parameters", True):
                self.output.print_md("## 2. Setting up shared parameters...")
                self._setup_shared_parameters()
            
            # Step 3: Create elements
            self.output.print_md("## 3. Creating Revit elements...")
            elements = self.data_reader.get_all_elements()
            created_elements = self._create_elements_batch(elements, settings.get("family_mapping"))
            
            # Step 4: Print results
            self.output.print_md("## 4. Import completed!")
            self._print_import_results()
            
            return created_elements
            
        except Exception as e:
            self.output.print_md("**ERROR:** {}".format(str(e)))
            if self.element_creator._current_tx:
                self.element_creator.rollback_transaction()
            return []
    
    def _print_data_statistics(self, stats):
        # type: (dict) -> None
        """Print statistics about loaded data"""
        self.output.print_md("**Data Statistics:**")
        self.output.print_md("- Total categories: {}".format(stats["total_categories"]))
        self.output.print_md("- Total elements: {}".format(stats["total_elements"]))
        self.output.print_md("- Unique object types: {}".format(stats["unique_object_types"]))
        
        self.output.print_md("**Elements by category:**")
        for category, count in stats["elements_by_category"].items():
            self.output.print_md("- {}: {}".format(category, count))
        
        self.output.print_md("**Elements by type:**")
        for obj_type, count in stats["elements_by_type"].items():
            self.output.print_md("- {}: {}".format(obj_type, count))
    
    def _setup_shared_parameters(self):
        # type: () -> None
        """Setup shared parameters for the import"""
        try:
            created_params = self.parameter_manager.setup_dxf_import_parameters()
            self.stats["parameters_created"] = len(created_params)
            self.output.print_md("Created {} shared parameters".format(len(created_params)))
        except Exception as e:
            self.output.print_md("**Warning:** Failed to setup shared parameters: {}".format(str(e)))
            self.output.print_md("Elements will be created without custom parameters")
    
    def _create_elements_batch(self, elements, family_mapping):
        # type: (list, dict or None) -> list
        """Create elements in batches with progress reporting"""
        created_elements = []
        batch_size = 50
        total_elements = len(elements)
        
        self.output.print_md("Creating {} elements in batches of {}...".format(
            total_elements, batch_size
        ))
        
        # Create progress bar
        with self.output.progress() as progress:
            for i in range(0, total_elements, batch_size):
                batch = elements[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_elements + batch_size - 1) // batch_size
                
                progress.update_progress(i, total_elements)
                self.output.print_md("Processing batch {}/{}...".format(batch_num, total_batches))
                
                try:
                    # Create elements in this batch
                    batch_created = self._create_elements_in_transaction(batch, family_mapping)
                    created_elements.extend(batch_created)
                    
                    # Update statistics
                    self.stats["elements_processed"] += len(batch)
                    self.stats["elements_created"] += len(batch_created)
                    self.stats["elements_failed"] += len(batch) - len(batch_created)
                    
                    self.output.print_md("  Created: {}, Failed: {}".format(
                        len(batch_created), len(batch) - len(batch_created)
                    ))
                    
                except Exception as e:
                    self.output.print_md("**ERROR** in batch {}: {}".format(batch_num, str(e)))
                    self.stats["elements_processed"] += len(batch)
                    self.stats["elements_failed"] += len(batch)
        
        return created_elements
    
    def _create_elements_in_transaction(self, elements_batch, family_mapping):
        # type: (list, dict or None) -> list
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
                    self.output.print_md("    Failed to create element: {}".format(str(e)))
            
            # Commit transaction
            transaction.Commit()
            
        except Exception as e:
            # Rollback on error
            transaction.RollBack()
            self.output.print_md("    Transaction failed: {}".format(str(e)))
            created_elements = []
        
        return created_elements
    
    def _print_import_results(self):
        # type: () -> None
        """Print final import statistics"""
        self.output.print_md("---")
        self.output.print_md("# IMPORT RESULTS")
        self.output.print_md("---")
        self.output.print_md("**Elements processed:** {}".format(self.stats["elements_processed"]))
        self.output.print_md("**Elements created:** {}".format(self.stats["elements_created"]))
        self.output.print_md("**Elements failed:** {}".format(self.stats["elements_failed"]))
        self.output.print_md("**Parameters created:** {}".format(self.stats["parameters_created"]))
        
        if self.stats["elements_processed"] > 0:
            success_rate = (
                self.stats["elements_created"] * 100.0 / self.stats["elements_processed"]
            )
            self.output.print_md("**Success rate:** {:.1f}%".format(success_rate))


def main():
    # type: () -> None
    """Main function executed when button is clicked"""
    doc = __revit__.ActiveUIDocument.Document
    output = script.get_output()
    
    if not doc:
        forms.alert("No active Revit document found.", exitscript=True)
    
    # Create controller
    controller = DxfImportController(doc)
    
    # Select JSON file
    output.print_md("# DXF Data Import Tool")
    output.print_md("Select a JSON file containing DXF data to import...")
    
    json_file_path = controller.select_json_file()
    if not json_file_path:
        forms.alert("No file selected. Import cancelled.", exitscript=True)
    
    if not os.path.exists(json_file_path):
        forms.alert("Selected file does not exist: {}".format(json_file_path), exitscript=True)
    
    # Show configuration dialog
    settings = controller.show_import_dialog()
    if settings is None:
        forms.alert("Import cancelled by user.", exitscript=True)
    
    # Run import
    try:
        created_elements = controller.run_import(json_file_path, settings)
        
        if created_elements:
            forms.alert(
                "Import completed successfully!\nCreated {} elements.".format(len(created_elements)),
                title="Import Complete"
            )
        else:
            forms.alert(
                "Import completed but no elements were created.\nCheck the output window for details.",
                title="Import Complete"
            )
    
    except Exception as e:
        forms.alert("Import failed: {}".format(str(e)), title="Import Error")


# Execute main function when script is run
if __name__ == "__main__":

    main()
