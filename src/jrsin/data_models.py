"""Data models for reading revit_data.json - IronPython 2.7 compatible"""

import json


class Point:
    """Represents a 3D point with x, y, z coordinates"""

    def __init__(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @classmethod
    def from_dict(cls, point_dict):
        """Create Point from dictionary"""
        return cls(point_dict["x"], point_dict["y"], point_dict["z"])

    def __repr__(self):
        return "Point(x={}, y={}, z={})".format(self.x, self.y, self.z)  # noqa: UP032


class Dimensions:
    """Represents element dimensions"""

    def __init__(self, **kwargs):
        # Store all dimension properties dynamically
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, dim_dict):
        """Create Dimensions from dictionary"""
        return cls(**dim_dict)

    def get_radius(self):
        """Get radius if available"""
        return getattr(self, "radius", None)

    def get_diameter(self):
        """Get diameter if available"""
        return getattr(self, "diameter", None)

    def get_width(self):
        """Get width if available"""
        return getattr(self, "width", None)

    def get_height(self):
        """Get height if available"""
        return getattr(self, "height", None)


class ElementData:
    """Represents a single element from the JSON data"""

    def __init__(self, object_type, layer_name, dimensions, points):
        self.object_type = object_type
        self.layer_name = layer_name
        self.dimensions = dimensions
        self.points = points

    @classmethod
    def from_dict(cls, element_dict):
        """Create ElementData from dictionary"""
        dimensions = Dimensions.from_dict(element_dict["dimensions"])
        points = [Point.from_dict(p) for p in element_dict["points"]]

        return cls(element_dict["object_type"], element_dict["layer_name"], dimensions, points)

    def get_center_point(self):
        """Calculate center point from all points"""
        if not self.points:
            return None

        sum_x = sum(p.x for p in self.points)
        sum_y = sum(p.y for p in self.points)
        sum_z = sum(p.z for p in self.points)

        count = len(self.points)
        return Point(sum_x / count, sum_y / count, sum_z / count)

    def get_main_point(self):
        """Get the first point as main position"""
        return self.points[0] if self.points else None

    def is_line_based_element(self):
        """Check if this is a pipe-related element"""
        return "WATER" in self.object_type or "PIPE" in self.object_type

    def is_point_based_element(self):
        """Check if this is a shaft-related element"""
        return "SHAFT" in self.object_type or "SPECIAL" in self.object_type


class RevitDataReader:
    """Reader for revit_data.json file - IronPython compatible"""

    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self._data = None
        self._elements_by_category = {}

    def load_data(self):
        """Load and parse JSON data"""
        try:
            with open(self.json_file_path) as f:
                self._data = json.load(f)

            # Parse elements by category
            for category_name, elements_list in self._data.items():
                element_objects = []
                for element_dict in elements_list:
                    element_objects.append(ElementData.from_dict(element_dict))
                self._elements_by_category[category_name] = element_objects

        except Exception as e:
            raise Exception(f"Failed to load JSON data: {str(e)}")

    def get_categories(self):
        """Get all category names"""
        if self._data is None:
            self.load_data()
        if self._data is None:
            return []
        return self._data.keys()

    def get_elements_by_category(self, category_name):
        """Get all elements for a specific category"""
        if self._data is None:
            self.load_data()
        return self._elements_by_category.get(category_name, [])

    def get_all_elements(self):
        """Get all elements from all categories"""
        if self._data is None:
            self.load_data()

        all_elements = []
        for elements in self._elements_by_category.values():
            all_elements.extend(elements)
        return all_elements

    def get_elements_by_type(self, object_type):
        """Get all elements of a specific object type"""
        all_elements = self.get_all_elements()
        return [elem for elem in all_elements if elem.object_type == object_type]

    def get_unique_object_types(self):
        """Get all unique object types in the data"""
        all_elements = self.get_all_elements()
        return list({elem.object_type for elem in all_elements})

    def get_unique_layer_names(self):
        """Get all unique layer names in the data"""
        all_elements = self.get_all_elements()
        return list({elem.layer_name for elem in all_elements})

    def get_statistics(self):
        """Get statistics about the data"""
        stats = {
            "total_categories": len(self.get_categories()),
            "total_elements": len(self.get_all_elements()),
            "unique_object_types": len(self.get_unique_object_types()),
            "unique_layer_names": len(self.get_unique_layer_names()),
        }

        # Count by category
        stats["elements_by_category"] = {}
        for category in self.get_categories():
            stats["elements_by_category"][category] = len(self.get_elements_by_category(category))

        # Count by object type
        stats["elements_by_type"] = {}
        for obj_type in self.get_unique_object_types():
            stats["elements_by_type"][obj_type] = len(self.get_elements_by_type(obj_type))

        return stats
