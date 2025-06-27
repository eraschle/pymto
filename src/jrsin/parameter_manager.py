# -*- coding: utf-8 -*-
"""Parameter management for Revit elements - IronPython 2.7 compatible"""

# IronPython imports
try:
    from Autodesk.Revit.DB import *
    from Autodesk.Revit.UI import *
    import clr
    import System
    from System.Collections.Generic import List
    
    REVIT_AVAILABLE = True
except ImportError:
    REVIT_AVAILABLE = False
    print("Revit API not available - running in development mode")


class RevitParameterManager(object):
    """Manages shared and project parameters for Revit elements"""
    
    def __init__(self, doc):
        """Initialize with Revit document"""
        if not REVIT_AVAILABLE:
            raise Exception("Revit API not available")
        
        self.doc = doc
        self.app = doc.Application
        self._parameter_definitions = {}
    
    def create_shared_parameter_group(self, group_name):
        """Create or get shared parameter group"""
        try:
            param_file = self.app.OpenSharedParameterFile()
            if not param_file:
                print("No shared parameter file found")
                return None
            
            # Try to get existing group
            groups = param_file.Groups
            for group in groups:
                if group.Name == group_name:
                    return group
            
            # Create new group
            new_group = groups.Create(group_name)
            return new_group
            
        except Exception as e:
            print("Failed to create shared parameter group: {}".format(str(e)))
            return None
    
    def create_shared_parameter_definition(self, group, param_name, param_type, is_instance=True):
        """Create shared parameter definition"""
        try:
            # Check if parameter already exists
            definitions = group.Definitions
            for definition in definitions:
                if definition.Name == param_name:
                    return definition
            
            # Create new definition
            options = ExternalDefinitionCreationOptions(param_name, param_type)
            options.UserModifiable = True
            options.Visible = True
            
            new_definition = definitions.Create(options)
            return new_definition
            
        except Exception as e:
            print("Failed to create shared parameter definition: {}".format(str(e)))
            return None
    
    def bind_shared_parameter_to_category(self, definition, categories, is_instance=True):
        """Bind shared parameter to categories"""
        try:
            # Create category set
            category_set = self.app.Create.NewCategorySet()
            
            # Add categories
            if isinstance(categories, list):
                for category in categories:
                    if isinstance(category, BuiltInCategory):
                        cat = self.doc.Settings.Categories.get_Item(category)
                        if cat:
                            category_set.Insert(cat)
            else:
                if isinstance(categories, BuiltInCategory):
                    cat = self.doc.Settings.Categories.get_Item(categories)
                    if cat:
                        category_set.Insert(cat)
            
            # Create binding
            if is_instance:
                binding = self.app.Create.NewInstanceBinding(category_set)
            else:
                binding = self.app.Create.NewTypeBinding(category_set)
            
            # Bind parameter
            param_map = self.doc.ParameterBindings
            success = param_map.Insert(definition, binding, BuiltInParameterGroup.PG_GENERAL)
            
            return success
            
        except Exception as e:
            print("Failed to bind shared parameter: {}".format(str(e)))
            return False
    
    def get_parameter_type_from_value(self, value):
        """Determine parameter type from value"""
        if isinstance(value, bool):
            return SpecTypeId.Boolean.YesNo
        elif isinstance(value, int):
            return SpecTypeId.Int.Integer  
        elif isinstance(value, float):
            return SpecTypeId.Number
        elif isinstance(value, str):
            return SpecTypeId.String.Text
        else:
            return SpecTypeId.String.Text
    
    def create_project_parameters_for_elements(self, parameter_definitions, categories=None):
        """Create project parameters for specific element types"""
        if categories is None:
            categories = [BuiltInCategory.OST_GenericModel]
        
        created_params = []
        
        # Create shared parameter group
        group = self.create_shared_parameter_group("DXF Import Parameters")
        if not group:
            print("Failed to create parameter group")
            return created_params
        
        for param_name, param_info in parameter_definitions.items():
            try:
                # Determine parameter type
                if "type" in param_info:
                    param_type = param_info["type"]
                elif "sample_value" in param_info:
                    param_type = self.get_parameter_type_from_value(param_info["sample_value"])
                else:
                    param_type = SpecTypeId.String.Text
                
                # Create definition
                definition = self.create_shared_parameter_definition(
                    group, 
                    param_name, 
                    param_type, 
                    param_info.get("is_instance", True)
                )
                
                if definition:
                    # Bind to categories
                    success = self.bind_shared_parameter_to_category(
                        definition, 
                        categories, 
                        param_info.get("is_instance", True)
                    )
                    
                    if success:
                        created_params.append({
                            "name": param_name,
                            "definition": definition,
                            "type": param_type
                        })
                        print("Created parameter: {}".format(param_name))
                    else:
                        print("Failed to bind parameter: {}".format(param_name))
                
            except Exception as e:
                print("Failed to create parameter '{}': {}".format(param_name, str(e)))
        
        return created_params
    
    def set_parameter_value(self, element, param_name, value):
        """Set parameter value on element"""
        try:
            param = element.LookupParameter(param_name)
            if not param:
                print("Parameter '{}' not found on element".format(param_name))
                return False
            
            if param.IsReadOnly:
                print("Parameter '{}' is read-only".format(param_name))
                return False
            
            # Set value based on parameter storage type
            if param.StorageType == StorageType.Double:
                if isinstance(value, (int, float)):
                    param.Set(float(value))
                else:
                    param.SetValueString(str(value))
            elif param.StorageType == StorageType.Integer:
                if isinstance(value, bool):
                    param.Set(1 if value else 0)
                else:
                    param.Set(int(value))
            elif param.StorageType == StorageType.String:
                param.Set(str(value))
            elif param.StorageType == StorageType.ElementId:
                if isinstance(value, ElementId):
                    param.Set(value)
                else:
                    param.Set(ElementId(int(value)))
            
            return True
            
        except Exception as e:
            print("Failed to set parameter '{}' to '{}': {}".format(param_name, value, str(e)))
            return False
    
    def set_multiple_parameters(self, element, parameters_dict):
        """Set multiple parameters on element"""
        success_count = 0
        
        for param_name, value in parameters_dict.items():
            if self.set_parameter_value(element, param_name, value):
                success_count += 1
        
        return success_count
    
    def get_standard_dxf_parameters(self):
        """Get standard parameter definitions for DXF import elements"""
        return {
            "DXF_ObjectType": {
                "type": SpecTypeId.String.Text,
                "is_instance": True,
                "description": "Original DXF object type"
            },
            "DXF_LayerName": {
                "type": SpecTypeId.String.Text,
                "is_instance": True,
                "description": "Original DXF layer name"
            },
            "DXF_PointCount": {
                "type": SpecTypeId.Int.Integer,
                "is_instance": True, 
                "description": "Number of points in original geometry"
            },
            "DXF_Diameter": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element diameter from DXF"
            },
            "DXF_Radius": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element radius from DXF"
            },
            "DXF_Width": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element width from DXF"
            },
            "DXF_Height": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element height from DXF"
            },
            "DXF_CenterX": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "X coordinate of element center"
            },
            "DXF_CenterY": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "Y coordinate of element center"
            },
            "DXF_CenterZ": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "Z coordinate of element center"
            },
            "DXF_ImportDate": {
                "type": SpecTypeId.String.Text,
                "is_instance": True,
                "description": "Date when element was imported"
            }
        }
    
    def setup_dxf_import_parameters(self, categories=None):
        """Setup all standard parameters needed for DXF import"""
        if categories is None:
            categories = [
                BuiltInCategory.OST_GenericModel,
                BuiltInCategory.OST_PipeAccessory,
                BuiltInCategory.OST_Conduit,
                BuiltInCategory.OST_PipeCurves
            ]
        
        standard_params = self.get_standard_dxf_parameters()
        return self.create_project_parameters_for_elements(standard_params, categories)
    
    def apply_element_data_to_parameters(self, element, element_data, import_date=None):
        """Apply ElementData properties to element parameters"""
        if import_date is None:
            import_date = System.DateTime.Now.ToString()
        
        # Prepare parameter values
        params = {
            "DXF_ObjectType": element_data.object_type,
            "DXF_LayerName": element_data.layer_name,
            "DXF_PointCount": len(element_data.points),
            "DXF_ImportDate": import_date
        }
        
        # Add dimension parameters
        if hasattr(element_data.dimensions, 'diameter'):
            params["DXF_Diameter"] = element_data.dimensions.diameter
        if hasattr(element_data.dimensions, 'radius'):
            params["DXF_Radius"] = element_data.dimensions.radius
        if hasattr(element_data.dimensions, 'width'):
            params["DXF_Width"] = element_data.dimensions.width
        if hasattr(element_data.dimensions, 'height'):
            params["DXF_Height"] = element_data.dimensions.height
        
        # Add center coordinates
        center = element_data.get_center_point()
        if center:
            params["DXF_CenterX"] = center.x
            params["DXF_CenterY"] = center.y  
            params["DXF_CenterZ"] = center.z
        
        # Apply all parameters
        return self.set_multiple_parameters(element, params)