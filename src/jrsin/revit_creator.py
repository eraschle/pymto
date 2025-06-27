# -*- coding: utf-8 -*-
"""Revit element creation and type management - IronPython 2.7 compatible"""

# IronPython imports - these will be available in RevitPythonShell
try:
    # Revit API imports
    from Autodesk.Revit.DB import *
    from Autodesk.Revit.UI import *
    
    # Standard IronPython/CLR imports
    import clr
    import System
    from System.Collections.Generic import List
    
    REVIT_AVAILABLE = True
except ImportError:
    # For development/testing outside Revit
    REVIT_AVAILABLE = False
    print("Revit API not available - running in development mode")


class RevitElementTypeManager(object):
    """Manages Revit family types and element creation"""
    
    def __init__(self, doc):
        """Initialize with Revit document"""
        if not REVIT_AVAILABLE:
            raise Exception("Revit API not available")
        
        self.doc = doc
        self._family_cache = {}
        self._type_cache = {}
    
    def get_or_create_family_type(self, family_name, type_name, category=BuiltInCategory.OST_GenericModel):
        """Get existing family type or create new one"""
        cache_key = "{}_{}".format(family_name, type_name)
        
        if cache_key in self._type_cache:
            return self._type_cache[cache_key]
        
        # Try to find existing type
        existing_type = self._find_family_type(family_name, type_name, category)
        if existing_type:
            self._type_cache[cache_key] = existing_type
            return existing_type
        
        # Create new type
        new_type = self._create_family_type(family_name, type_name, category)
        if new_type:
            self._type_cache[cache_key] = new_type
        
        return new_type
    
    def _find_family_type(self, family_name, type_name, category):
        """Find existing family type"""
        collector = FilteredElementCollector(self.doc)
        collector.OfCategory(category)
        symbols = collector.OfClass(FamilySymbol).ToElements()
        
        for symbol in symbols:
            if symbol.Family.Name == family_name and symbol.Name == type_name:
                return symbol
        
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
                print("Failed to duplicate family symbol: {}".format(str(e)))
                return None
        else:
            # Try to load family from standard location
            return self._load_family_from_file(family_name, type_name)
    
    def _find_base_family_symbol(self, family_name, category):
        """Find a base symbol from the family to duplicate"""
        collector = FilteredElementCollector(self.doc)
        collector.OfCategory(category)
        symbols = collector.OfClass(FamilySymbol).ToElements()
        
        for symbol in symbols:
            if symbol.Family.Name == family_name:
                return symbol
        
        return None
    
    def _load_family_from_file(self, family_name, type_name):
        """Load family from RFA file (implementation depends on your family library)"""
        # This would need to be implemented based on your family file organization
        # For now, return None - families need to be pre-loaded
        print("Family '{}' not found in document. Please load the family manually.".format(family_name))
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
                    print("Failed to set parameter '{}': {}".format(param_name, str(e)))
    
    def _set_parameter_value(self, parameter, value):
        """Set parameter value based on parameter type"""
        if parameter.StorageType == StorageType.Double:
            # Convert to internal units if needed
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
                # Try to convert string/int to ElementId
                parameter.Set(ElementId(int(value)))


class RevitElementCreator(object):
    """Creates Revit elements from data"""
    
    def __init__(self, doc):
        """Initialize with Revit document"""
        if not REVIT_AVAILABLE:
            raise Exception("Revit API not available")
        
        self.doc = doc
        self.type_manager = RevitElementTypeManager(doc)
        self._current_transaction = None
    
    def start_transaction(self, transaction_name="Create Elements"):
        """Start a transaction for element creation"""
        if self._current_transaction is not None:
            raise Exception("Transaction already active")
        
        self._current_transaction = Transaction(self.doc, transaction_name)
        self._current_transaction.Start()
    
    def commit_transaction(self):
        """Commit current transaction"""
        if self._current_transaction is None:
            raise Exception("No active transaction")
        
        self._current_transaction.Commit()
        self._current_transaction = None
    
    def rollback_transaction(self):
        """Rollback current transaction"""
        if self._current_transaction is None:
            raise Exception("No active transaction")
        
        self._current_transaction.RollBack()
        self._current_transaction = None
    
    def create_element_from_data(self, element_data, family_mapping=None):
        """Create Revit element from ElementData object"""
        if family_mapping is None:
            family_mapping = self._get_default_family_mapping()
        
        # Determine family and type names
        family_info = self._get_family_info_for_element(element_data, family_mapping)
        if not family_info:
            print("No family mapping found for object type: {}".format(element_data.object_type))
            return None
        
        family_name = family_info["family_name"]
        type_name = family_info["type_name"]
        category = family_info.get("category", BuiltInCategory.OST_GenericModel)
        
        # Get or create family type
        family_symbol = self.type_manager.get_or_create_family_type(family_name, type_name, category)
        if not family_symbol:
            print("Failed to get family symbol for: {}".format(family_name))
            return None
        
        # Activate symbol if needed
        if not family_symbol.IsActive:
            family_symbol.Activate()
        
        # Apply type parameters based on dimensions
        type_params = self._create_type_parameters_from_dimensions(element_data.dimensions)
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
                "category": BuiltInCategory.OST_GenericModel
            },
            "WATER_PIPE": {
                "family_name": "WaterPipe", 
                "type_name": "Standard",
                "category": BuiltInCategory.OST_PipeAccessory
            },
            "SHAFT": {
                "family_name": "Shaft",
                "type_name": "Standard", 
                "category": BuiltInCategory.OST_GenericModel
            }
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
            "category": base_info.get("category", BuiltInCategory.OST_GenericModel)
        }
    
    def _generate_type_name(self, element_data):
        """Generate unique type name based on element properties"""
        base_name = element_data.object_type
        
        # Add dimension info to type name
        dim_parts = []
        if hasattr(element_data.dimensions, 'diameter'):
            dim_parts.append("D{}".format(int(element_data.dimensions.diameter)))
        if hasattr(element_data.dimensions, 'radius'):
            dim_parts.append("R{}".format(int(element_data.dimensions.radius)))
        if hasattr(element_data.dimensions, 'width'):
            dim_parts.append("W{}".format(int(element_data.dimensions.width)))
        if hasattr(element_data.dimensions, 'height'):
            dim_parts.append("H{}".format(int(element_data.dimensions.height)))
        
        if dim_parts:
            return "{}_{}".format(base_name, "_".join(dim_parts))
        else:
            return "{}_Standard".format(base_name)
    
    def _create_type_parameters_from_dimensions(self, dimensions):
        """Create type parameters dictionary from dimensions"""
        params = {}
        
        # Map dimension properties to parameter names
        if hasattr(dimensions, 'diameter'):
            params["Diameter"] = dimensions.diameter
        if hasattr(dimensions, 'radius'):
            params["Radius"] = dimensions.radius  
        if hasattr(dimensions, 'width'):
            params["Width"] = dimensions.width
        if hasattr(dimensions, 'height'):
            params["Height"] = dimensions.height
        
        return params
    
    def _create_instance_parameters_from_data(self, element_data):
        """Create instance parameters from element data"""
        return {
            "Object_Type": element_data.object_type,
            "Layer_Name": element_data.layer_name,
            "Point_Count": len(element_data.points)
        }
    
    def _create_family_instance(self, element_data, family_symbol):
        """Create family instance at specified location"""
        # Get position from element data
        position = self._get_revit_position(element_data.get_main_point())
        
        # Create instance
        try:
            instance = self.doc.Create.NewFamilyInstance(
                position, 
                family_symbol, 
                StructuralType.NonStructural
            )
            return instance
        except Exception as e:
            print("Failed to create family instance: {}".format(str(e)))
            return None
    
    def _get_revit_position(self, point):
        """Convert point to Revit XYZ position"""
        if point is None:
            return XYZ(0, 0, 0)
        
        # Convert to internal units (feet)
        # Assuming input is in meters
        x = UnitUtils.ConvertToInternalUnits(point.x, UnitTypeId.Meters)
        y = UnitUtils.ConvertToInternalUnits(point.y, UnitTypeId.Meters) 
        z = UnitUtils.ConvertToInternalUnits(point.z, UnitTypeId.Meters)
        
        return XYZ(x, y, z)
    
    def _apply_instance_parameters(self, instance, parameters_dict):
        """Apply parameters to family instance"""
        if not parameters_dict:
            return
        
        for param_name, param_value in parameters_dict.items():
            param = instance.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                try:
                    self.type_manager._set_parameter_value(param, param_value)
                except Exception as e:
                    print("Failed to set instance parameter '{}': {}".format(param_name, str(e)))
    
    def create_elements_from_data_list(self, elements_data, family_mapping=None, batch_size=100):
        """Create multiple elements with batch processing"""
        created_elements = []
        
        for i, element_data in enumerate(elements_data):
            # Start new transaction for each batch
            if i % batch_size == 0:
                if self._current_transaction:
                    self.commit_transaction()
                self.start_transaction("Create Elements Batch {}".format(i // batch_size + 1))
            
            try:
                element = self.create_element_from_data(element_data, family_mapping)
                if element:
                    created_elements.append(element)
            except Exception as e:
                print("Failed to create element {}: {}".format(i, str(e)))
        
        # Commit final transaction
        if self._current_transaction:
            self.commit_transaction()
        
        return created_elements