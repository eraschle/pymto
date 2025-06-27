"""Parameter management for Revit elements - IronPython 2.7 compatible"""

# IronPython imports
import logging

import System
from Autodesk.Revit.DB import (
    BuiltInCategory,
    CategorySet,
    Definition,
    DefinitionGroup,
    Document,
    ElementId,
    ExternalDefinitionCreationOptions,
    ForgeTypeId,
    SpecTypeId,
    StorageType,
)

log = logging.getLogger(__name__)


class RevitParameterManager:
    """Manages shared and project parameters for Revit elements"""

    def __init__(self, document: Document):
        """Initialize with Revit document"""
        self.document = document
        self.application = document.Application
        self._parameter_definitions = {}

    def create_shared_parameter_group(self, group_name: str):
        """Create or get shared parameter group by name. In case of any Exception,
        it will return None.

        Parameters
        ----------
        group_name : str
            Name of the shared parameter group to create or retrieve

        Returns
        -------
        DefinitionGroup
            The created or existing shared parameter group
        """
        shared_param = self.application.OpenSharedParameterFile()  # pyright: ignore[reportFunctionMemberAccess]
        if not shared_param:
            return None

        # Try to get existing group
        groups = shared_param.Groups
        for group in groups:
            if group.Name != group_name:
                continue
            return group

        return groups.Create(group_name)

    def create_shared_parameter(
        self, group: DefinitionGroup, param_name: str, param_type: ForgeTypeId
    ):
        """Create or get shared parameter definition,

        In case of any Exception, it will return None.

        Parameters
        ----------
        group : DefinitionGroup
            The shared parameter group to create the definition in
        param_name : str
            Name of the parameter to create
        param_type : ForgeTypeId
            Type of the parameter (e.g., SpecTypeId.String.Text)

        Returns
        -------
        Definition
            The created or existing parameter definition
        """
        try:
            definitions = group.Definitions
            for definition in definitions.GetEnumerator():
                if definition.Name != param_name:
                    continue
                return definition

            options = ExternalDefinitionCreationOptions(param_name, param_type)
            options.UserModifiable = True
            options.Visible = True

            new_definition = definitions.Create(options)
            return new_definition

        except Exception as e:
            print(f"Failed to create shared parameter definition: {str(e)}")
            return None

    def create_category_set(self, categories) -> CategorySet:
        if isinstance(categories, BuiltInCategory):
            categories = [categories]

        category_set = self.application.Create.NewCategorySet()  # pyright: ignore[reportFunctionMemberAccess]
        for category in categories:
            if not isinstance(category, BuiltInCategory):
                continue
            category = self.document.Settings.Categories.get_Item(category)  # pyright: ignore[reportAttributeAccessIssue]
            if not category:
                continue
            category_set.Insert(category)

        return category_set

    def bind_parameter_to_categories(
        self,
        definition: Definition,
        categories,
        param_group: ForgeTypeId,
        is_instance: bool = True,
    ):
        """Bind shared parameter to categories"""
        if self.document.ParameterBindings.Contains(definition):
            log.warning(f"Parameter '{definition.Name}' already exists in bindings.")
            return False
        try:
            # Create category set and binding
            category_set = self.create_category_set(categories)
            if is_instance:
                binding = self.application.Create.NewInstanceBinding(category_set)  # pyright: ignore[reportFunctionMemberAccess]
            else:
                binding = self.application.Create.NewTypeBinding(category_set)  # pyright: ignore[reportFunctionMemberAccess]

            param_map = self.document.ParameterBindings
            success = param_map.Insert(definition, binding, param_group)
            return success

        except Exception as e:
            log.error(f"Failed to bind shared parameter: {str(e)}")
            return False

    def get_parameter_type_from_value(self, value):
        """Determine parameter type from value"""
        if isinstance(value, bool):
            return SpecTypeId.Boolean.YesNo
        if isinstance(value, int):
            return SpecTypeId.Int.Integer
        if isinstance(value, float):
            return SpecTypeId.Number
        return SpecTypeId.String.Text

    def create_project_parameters_for_elements(
        self, parameter_definitions, categories=None
    ):
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
                    param_type = self.get_parameter_type_from_value(
                        param_info["sample_value"]
                    )
                else:
                    param_type = SpecTypeId.String.Text

                # Create definition
                definition = self.create_shared_parameter(group, param_name, param_type)
                if not definition:
                    continue
                # Bind to categories
                success = self.bind_parameter_to_categories(
                    definition, categories, param_info.get("is_instance", True)
                )
                if success:
                    created_params.append(
                        {
                            "name": param_name,
                            "definition": definition,
                            "type": param_type,
                        }
                    )
                    print(f"Created parameter: {param_name}")
                else:
                    print(f"Failed to bind parameter: {param_name}")

            except Exception as e:
                print(f"Failed to create parameter '{param_name}': {str(e)}")

        return created_params

    def set_parameter_value(self, element, param_name, value):
        """Set parameter value on element"""
        try:
            param = element.LookupParameter(param_name)
            if not param:
                print(f"Parameter '{param_name}' not found on element")
                return False

            if param.IsReadOnly:
                print(f"Parameter '{param_name}' is read-only")
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
            print(f"Failed to set parameter '{param_name}' to '{value}': {str(e)}")
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
                "description": "Original DXF object type",
            },
            "DXF_LayerName": {
                "type": SpecTypeId.String.Text,
                "is_instance": True,
                "description": "Original DXF layer name",
            },
            "DXF_PointCount": {
                "type": SpecTypeId.Int.Integer,
                "is_instance": True,
                "description": "Number of points in original geometry",
            },
            "DXF_Diameter": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element diameter from DXF",
            },
            "DXF_Radius": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element radius from DXF",
            },
            "DXF_Width": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element width from DXF",
            },
            "DXF_Height": {
                "type": SpecTypeId.Length,
                "is_instance": False,
                "description": "Element height from DXF",
            },
            "DXF_CenterX": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "X coordinate of element center",
            },
            "DXF_CenterY": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "Y coordinate of element center",
            },
            "DXF_CenterZ": {
                "type": SpecTypeId.Length,
                "is_instance": True,
                "description": "Z coordinate of element center",
            },
            "DXF_ImportDate": {
                "type": SpecTypeId.String.Text,
                "is_instance": True,
                "description": "Date when element was imported",
            },
        }

    def setup_dxf_import_parameters(self, categories=None):
        """Setup all standard parameters needed for DXF import"""
        if categories is None:
            categories = [
                BuiltInCategory.OST_GenericModel,
                BuiltInCategory.OST_PipeAccessory,
                BuiltInCategory.OST_Conduit,
                BuiltInCategory.OST_PipeCurves,
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
            "DXF_ImportDate": import_date,
        }

        # Add dimension parameters
        if hasattr(element_data.dimensions, "diameter"):
            params["DXF_Diameter"] = element_data.dimensions.diameter
        if hasattr(element_data.dimensions, "radius"):
            params["DXF_Radius"] = element_data.dimensions.radius
        if hasattr(element_data.dimensions, "width"):
            params["DXF_Width"] = element_data.dimensions.width
        if hasattr(element_data.dimensions, "height"):
            params["DXF_Height"] = element_data.dimensions.height

        # Add center coordinates
        center = element_data.get_center_point()
        if center:
            params["DXF_CenterX"] = center.x
            params["DXF_CenterY"] = center.y
            params["DXF_CenterZ"] = center.z

        # Apply all parameters
        return self.set_multiple_parameters(element, params)
