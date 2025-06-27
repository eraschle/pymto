"""Revit element creation and type management - IronPython 2.7 compatible"""

# IronPython imports - these will be available in RevitPythonShell
import re
from pathlib import Path
from Autodesk.Revit.DB import (
    BuiltInCategory,
    Document,
    ElementId,
    FamilySymbol,
    FilteredElementCollector,
    StorageType,
    StructuralType,  # pyright: ignore[reportAttributeAccessIssue]
    Transaction,
    UnitTypeId,
    UnitUtils,
    XYZ,
)


def _get_generic_sysbols(document: Document, category=None):
    """Get all generic family symbols in the document"""
    category = category or BuiltInCategory.OST_GenericModel
    collector = FilteredElementCollector(document)
    collector = collector.OfCategory(BuiltInCategory.OST_GenericModel)  # pyright: ignore
    symbols = collector.OfClass(FamilySymbol).ToElements()
    return [sym for sym in symbols if isinstance(sym, FamilySymbol)]


def _get_symbols_by(document: Document, family_name: str, category=None):
    """Get all generic family symbols in the document"""
    family_syms = []
    for symbol in _get_generic_sysbols(document, category):
        if symbol.FamilyName != family_name:
            continue
        family_syms.append(symbol)
    return family_syms


class RevitElementTypeManager:
    """Manages Revit family types and element creation"""

    def __init__(self, document: Document, revit_library_path: str):
        """Initialize with Revit document"""
        self.document = document
        self.revit_library_path = Path(revit_library_path)
        self._family_cache = {}
        self._type_cache: dict[str, FamilySymbol] = {}

    def get_or_create_family_type(
        self,
        family_name: str,
        type_name: str,
        category=BuiltInCategory.OST_GenericModel,
    ):
        """Get existing family type or create new one"""
        cache_key = f"{family_name}_{type_name}"

        if cache_key in self._type_cache:
            return self._type_cache[cache_key]

        # Try to find existing type
        existing_type = self._find_family_symbol(family_name, type_name, category)
        if existing_type:
            self._type_cache[cache_key] = existing_type
            return existing_type

        # Create new type
        new_family_symbol = self._create_family_type(family_name, type_name, category)
        if not isinstance(new_family_symbol, FamilySymbol):
            raise Exception(f"Failed to create family type: {new_family_symbol}")

        if new_family_symbol:
            self._type_cache[cache_key] = new_family_symbol

        return new_family_symbol

    def _find_family_symbol(self, family_name, type_name, category):
        """Find existing family type"""
        for family_symbol in _get_symbols_by(self.document, family_name, category):
            if family_symbol.Name != type_name:
                continue
            return family_symbol
        return None

    def _create_family_type(self, family_name, type_name, category):
        """Create new family type by duplicating existing or loading family"""
        # First try to find the base family
        base_symbol = self._find_base_family_symbol(family_name, category)

        if base_symbol:
            # Duplicate existing symbol to create new type
            try:
                new_symbol = base_symbol.Duplicate(type_name)
                return new_symbol
            except Exception as e:
                print(f"Failed to duplicate family symbol: {str(e)}")
                return None
        else:
            # Try to load family from standard location
            return self._load_family_from_file(family_name, type_name)

    def _find_base_family_symbol(self, family_name, category):
        """Find a base symbol from the family to duplicate"""
        for symbol in _get_generic_sysbols(self.document, category):
            if symbol.FamilyName != family_name:
                continue
            return symbol
        return None

    def _load_family_from_file(self, family_name, type_name=None):
        """Load family from RFA file (implementation depends on your family library)"""
        if not self.revit_library_path.exists():
            raise Exception("Revit Family Library path does not exist")

        print(
            f"Family '{family_name}' not found in document. Please load the family manually."
        )
        return None

    def apply_type_parameters(self, family_symbol, parameters_dict):
        """Apply parameters to family type"""
        if not parameters_dict:
            return

        for param_name, param_value in parameters_dict.items():
            param = family_symbol.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                try:
                    self._set_parameter_value(param, param_value)
                except Exception as e:
                    print(f"Failed to set parameter '{param_name}': {str(e)}")

    def _set_parameter_value(self, parameter, value):
        """Set parameter value based on parameter type"""
        if parameter.StorageType == StorageType.Double:
            if isinstance(value, (int, float)):
                parameter.Set(float(value))
            else:
                parameter.SetValueString(str(value))
        elif parameter.StorageType == StorageType.Integer:
            parameter.Set(int(value))
        elif parameter.StorageType == StorageType.String:
            parameter.Set(str(value))
        elif parameter.StorageType == StorageType.ElementId:
            if isinstance(value, ElementId):
                parameter.Set(value)
            else:
                parameter.Set(ElementId(int(value)))


BACKUP_PATTER = re.compile(r"(\d{4})$")
def is_revit_backup_file(file_path: Path):
    """Check if the given path is a Revit backup file.

    Parameters
    ----------
    file_path : Path
        The file path to check

    Returns
    -------
    bool
        True if the path is a Revit backup file, False otherwise
    """
    if file_path.suffix.lower() not in (".rvt", ".rfa"):
        return False
    file_name = file_path.with_suffix("").name
    if BACKUP_PATTER.search(file_name) is not None:
        return True
    return False

def is_revit_library_file(family_path: Path):
    """Check if the given path is a valid Revit family file.

    Parameters
    ----------
    family_path : Path
        The file path to check

    Returns
    -------
    bool
        True if the path is a valid Revit family file, False otherwise
    """
    if not family_path.exists():
        return False
    if not family_path.suffix.lower() == ".rfa":
        return False
    if is_revit_backup_file(family_path):
        return False
    return True


def get_revit_library_path(current: Path, recursive: bool = True):
    """Generator to recursively find Revit family files in a directory.

    Parameters
    ----------
    current : Path
        The current directory to search
    recursive : bool, optional
        Whether to search recursively in subdirectories (default is True)

    Yields
    ------
    Path
        Paths to Revit family files found in the directory
    """
    for path in current.iterdir():
        if path.is_dir() and recursive:
            yield from get_revit_library_path(path, recursive)
        elif is_revit_library_file(path):
            yield path


class RevitElementCreator:
    """Creates Revit elements from data"""

    def __init__(self, document: Document, revit_library_path: str):
        """Initialize with Revit document"""
        self.document = document
        self.type_manager = RevitElementTypeManager(document, revit_library_path)
        self._current_tx = None

    def start_transaction(self, transaction_name="Create Elements"):
        """Start a transaction for element creation"""
        if self._current_tx is not None:
            raise Exception("Transaction already active")

        self._current_tx = Transaction(self.document, transaction_name)
        self._current_tx.Start()

    def commit_transaction(self):
        """Commit current transaction"""
        if self._current_tx is None:
            raise Exception("No active transaction")

        self._current_tx.Commit()
        self._current_tx = None

    def rollback_transaction(self):
        """Rollback current transaction"""
        if self._current_tx is None:
            raise Exception("No active transaction")

        self._current_tx.RollBack()
        self._current_tx = None

    def create_element_from_data(self, element_data, family_mapping=None):
        """Create Revit element from ElementData object"""
        if family_mapping is None:
            family_mapping = self._get_default_family_mapping()

        # Determine family and type names
        family_info = self._get_family_info_for_element(element_data, family_mapping)
        if not family_info:
            print(
                f"No family mapping found for object type: {element_data.object_type}"
            )
            return None

        family_name = family_info["family_name"]
        type_name = family_info["type_name"]
        category = family_info.get("category", BuiltInCategory.OST_GenericModel)

        # Get or create family type
        family_symbol = self.type_manager.get_or_create_family_type(
            family_name, type_name, category
        )
        if not family_symbol:
            print(f"Failed to get family symbol for: {family_name}")
            return None

        # Activate symbol if needed
        if not family_symbol.IsActive:
            family_symbol.Activate()

        # Apply type parameters based on dimensions
        type_params = self._create_type_parameters_from_dimensions(
            element_data.dimensions
        )
        self.type_manager.apply_type_parameters(family_symbol, type_params)

        # Create instance
        instance = self._create_family_instance(element_data, family_symbol)
        if instance:
            # Apply instance parameters
            instance_params = self._create_instance_parameters_from_data(element_data)
            self._apply_instance_parameters(instance, instance_params)

        return instance

    def _get_default_family_mapping(self):
        """Default mapping of object types to families"""
        return {
            "WATER_SPECIAL": {
                "family_name": "WaterSpecial",
                "type_name": "Standard",
                "category": BuiltInCategory.OST_GenericModel,
            },
            "WATER_PIPE": {
                "family_name": "WaterPipe",
                "type_name": "Standard",
                "category": BuiltInCategory.OST_PipeAccessory,
            },
            "SHAFT": {
                "family_name": "Shaft",
                "type_name": "Standard",
                "category": BuiltInCategory.OST_GenericModel,
            },
        }

    def _get_family_info_for_element(self, element_data, family_mapping):
        """Get family information for an element"""
        base_info = family_mapping.get(element_data.object_type)
        if not base_info:
            return None

        # Create unique type name based on dimensions
        type_name = self._generate_type_name(element_data)

        return {
            "family_name": base_info["family_name"],
            "type_name": type_name,
            "category": base_info.get("category", BuiltInCategory.OST_GenericModel),
        }

    def _generate_type_name(self, element_data):
        """Generate unique type name based on element properties"""
        base_name = element_data.object_type

        # Add dimension info to type name
        dim_parts = []
        if hasattr(element_data.dimensions, "diameter"):
            dim_parts.append(f"D{int(element_data.dimensions.diameter)}")
        if hasattr(element_data.dimensions, "radius"):
            dim_parts.append(f"R{int(element_data.dimensions.radius)}")
        if hasattr(element_data.dimensions, "width"):
            dim_parts.append(f"W{int(element_data.dimensions.width)}")
        if hasattr(element_data.dimensions, "height"):
            dim_parts.append(f"H{int(element_data.dimensions.height)}")

        if dim_parts:
            return "{}_{}".format(base_name, "_".join(dim_parts))
        else:
            return f"{base_name}_Standard"

    def _create_type_parameters_from_dimensions(self, dimensions):
        """Create type parameters dictionary from dimensions"""
        parameters = {}

        # Map dimension properties to parameter names
        if hasattr(dimensions, "diameter"):
            parameters["Diameter"] = dimensions.diameter
        if hasattr(dimensions, "radius"):
            parameters["Radius"] = dimensions.radius
        if hasattr(dimensions, "width"):
            parameters["Width"] = dimensions.width
        if hasattr(dimensions, "height"):
            parameters["Height"] = dimensions.height

        return parameters

    def _create_instance_parameters_from_data(self, element_data):
        """Create instance parameters from element data"""
        return {
            "Object_Type": element_data.object_type,
            "Layer_Name": element_data.layer_name,
            "Point_Count": len(element_data.points),
        }

    def _create_family_instance(self, element_data, family_symbol):
        """Create family instance at specified location"""
        # Get position from element data
        position = self._get_revit_position(element_data.get_main_point())

        # Create instance
        try:
            instance = self.document.Create.NewFamilyInstance(  # pyright: ignore[reportAttributeAccessIssue]
                position, family_symbol, StructuralType.NonStructural
            )
            return instance
        except Exception as e:
            print(f"Failed to create family instance: {str(e)}")
            return None

    def _get_revit_position(self, point):
        """Convert point to Revit XYZ position"""
        if point is None:
            return XYZ(0, 0, 0)

        # Convert to internal units (feet)
        # Assuming input is in meters
        east = UnitUtils.ConvertToInternalUnits(point.x, UnitTypeId.Meters)
        north = UnitUtils.ConvertToInternalUnits(point.y, UnitTypeId.Meters)
        alt = UnitUtils.ConvertToInternalUnits(point.z, UnitTypeId.Meters)

        return XYZ(east, north, alt)

    def _apply_instance_parameters(self, instance, parameters_dict):
        """Apply parameters to family instance"""
        if not parameters_dict:
            return

        for param_name, param_value in parameters_dict.items():
            parameter = instance.LookupParameter(param_name)
            if parameter is None or parameter.IsReadOnly:
                continue
            try:
                self.type_manager._set_parameter_value(parameter, param_value)
            except Exception as e:
                print(f"Failed to set instance parameter '{param_name}': {str(e)}")

    def create_elements_from_data_list(
        self, elements_data, family_mapping=None, batch_size=100
    ):
        """Create multiple elements with batch processing"""
        created_elements = []

        for i, element_data in enumerate(elements_data):
            # Start new transaction for each batch
            if i % batch_size == 0:
                if self._current_tx:
                    self.commit_transaction()
                self.start_transaction(f"Create Elements Batch {i // batch_size + 1}")

            try:
                element = self.create_element_from_data(element_data, family_mapping)
                if element:
                    created_elements.append(element)
            except Exception as e:
                print(f"Failed to create element {i}: {str(e)}")

        # Commit final transaction
        if self._current_tx:
            self.commit_transaction()

        return created_elements
