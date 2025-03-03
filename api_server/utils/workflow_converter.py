"""
Workflow converter module.

This module provides functionality to convert ComfyUI's standard workflow JSON to API-compatible workflow JSON.
"""

import json
import os
import sys
from typing import Dict, List, Any, Union, TextIO, Optional
from collections import OrderedDict

# Import NODE_CLASS_MAPPINGS from ComfyUI nodes
script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(script_dir)

# Simple path finding helper
def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Otherwise, continue the search from the parent directory
    return find_path(name, parent_directory)

# Find and add ComfyUI directory to path
comfyui_path = find_path("ComfyUI")
if comfyui_path:
    sys.path.append(comfyui_path)
    print(f"'{comfyui_path}' added to sys.path")

# Import NODE_CLASS_MAPPINGS - handle the case where it might not be available
try:
    from nodes import NODE_CLASS_MAPPINGS
    NODE_CLASS_MAPPINGS_AVAILABLE = True
except ImportError:
    print("Warning: Could not import NODE_CLASS_MAPPINGS. Using empty dictionary instead.")
    NODE_CLASS_MAPPINGS = {}
    NODE_CLASS_MAPPINGS_AVAILABLE = False


class FileHandler:
    """Handles file reading and writing operations.

    This class provides methods to read and write JSON files.
    """

    @staticmethod
    def read_json_file(file_path: Union[str, TextIO], encoding: str = "utf-8") -> dict:
        """
        Reads a JSON file and returns its contents as a dictionary.

        Args:
            file_path (Union[str, TextIO]): JSON file path or file object
            encoding (str, optional): File encoding. Default is "utf-8"

        Returns:
            dict: JSON file contents as a dictionary

        Raises:
            FileNotFoundError: If the file cannot be found
            ValueError: If the file is not a valid JSON
        """
        if hasattr(file_path, "read"):
            return json.load(file_path)
        with open(file_path, "r", encoding=encoding) as file:
            data = json.load(file)
        return data

    @staticmethod
    def write_json_file(file_path: Union[str, TextIO], data: dict, encoding: str = "utf-8") -> None:
        """
        Writes a dictionary to a JSON file.

        Args:
            file_path (Union[str, TextIO]): JSON file path or file object to write to
            data (dict): Data to write
            encoding (str, optional): File encoding. Default is "utf-8"

        Raises:
            IOError: If an error occurs during file writing
        """
        if hasattr(file_path, "write"):
            json.dump(data, file_path, indent=2, ensure_ascii=False)
            return

        with open(file_path, "w", encoding=encoding) as file:
            json.dump(data, file, indent=2, ensure_ascii=False)


class WorkflowConverter:
    """
    Converts standard workflow JSON to API-compatible workflow JSON.
    """

    def __init__(self, workflow_data: Dict = None):
        """
        WorkflowConverter class constructor.

        Args:
            workflow_data (Dict, optional): Workflow data to convert. Default is None
        """
        self.workflow_data = workflow_data
        self.api_workflow = {}
        self.node_class_mappings = NODE_CLASS_MAPPINGS

    def load_workflow(self, file_path: Union[str, TextIO]) -> None:
        """
        Loads workflow data from a JSON file.

        Args:
            file_path (Union[str, TextIO]): Workflow JSON file path or file object
        """
        self.workflow_data = FileHandler.read_json_file(file_path)

    def convert_to_api_format(self) -> Dict:
        """
        Converts standard workflow data to API format.

        Returns:
            Dict: API-formatted workflow data
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Please load workflow data first.")

        self.api_workflow = {}

        # Convert node data
        for node in self.workflow_data.get("nodes", []):
            node_id = str(node["id"])
            node_type = node["type"]
            
            # Process node inputs
            inputs = {}
            
            # Process widget values
            if "widgets_values" in node:
                # Process widgets based on node type
                self._process_widgets(node, inputs)
            
            # Process connected inputs
            if "inputs" in node:
                self._process_connections(node, inputs)
            
            # Add node to API workflow
            self.api_workflow[node_id] = {
                "inputs": inputs,
                "class_type": node_type,
                "_meta": {
                    "title": node_type
                }
            }

        # Sort nodes by ID
        sorted_api_workflow = OrderedDict()
        for node_id in sorted(self.api_workflow.keys(), key=int):
            sorted_api_workflow[node_id] = self.api_workflow[node_id]
        
        self.api_workflow = sorted_api_workflow
        return self.api_workflow

    def _process_widgets(self, node: Dict, inputs: Dict) -> None:
        """
        Process node widget values.

        Args:
            node (Dict): Node data
            inputs (Dict): Dictionary to store input data
        """
        node_type = node["type"]
        widgets_values = node.get("widgets_values", [])
        
        # Process widgets based on node type
        # Check if node type exists in NODE_CLASS_MAPPINGS
        if NODE_CLASS_MAPPINGS_AVAILABLE and node_type in self.node_class_mappings:
            # Handle specific node types
            if node_type == "CheckpointLoaderSimple":
                if len(widgets_values) > 0:
                    inputs["ckpt_name"] = widgets_values[0]
            
            elif node_type == "CLIPTextEncode":
                if len(widgets_values) > 0:
                    inputs["text"] = widgets_values[0]
            
            elif node_type == "EmptyLatentImage":
                if len(widgets_values) >= 3:
                    inputs["width"] = widgets_values[0]
                    inputs["height"] = widgets_values[1]
                    inputs["batch_size"] = widgets_values[2]
            
            elif node_type == "KSampler":
                if len(widgets_values) >= 7:
                    inputs["seed"] = widgets_values[0]
                    inputs["steps"] = widgets_values[2]
                    inputs["cfg"] = widgets_values[3]
                    inputs["sampler_name"] = widgets_values[4]
                    inputs["scheduler"] = widgets_values[5]
                    inputs["denoise"] = widgets_values[6]
            
            elif node_type == "SaveImage":
                if len(widgets_values) > 0:
                    inputs["filename_prefix"] = widgets_values[0]
            
            # For other node types, use a generic approach
            else:
                for i, value in enumerate(widgets_values):
                    inputs[f"param_{i}"] = value
        else:
            # For unknown node types, use a generic approach
            for i, value in enumerate(widgets_values):
                inputs[f"param_{i}"] = value

    def _process_connections(self, node: Dict, inputs: Dict) -> None:
        """
        Process node connections.

        Args:
            node (Dict): Node data
            inputs (Dict): Dictionary to store input data
        """
        node_inputs = node.get("inputs", [])
        
        # Find connection information through workflow links
        links = self.workflow_data.get("links", [])
        
        for input_data in node_inputs:
            input_name = input_data.get("name")
            link_id = input_data.get("link")
            
            if link_id is not None:
                # Find information for the given link ID
                for link in links:
                    if link[0] == link_id:
                        # link format: [link_id, source_node_id, source_slot_index, target_node_id, target_slot_index, link_type]
                        source_node_id = str(link[1])
                        source_slot_index = link[2]
                        inputs[input_name] = [source_node_id, source_slot_index]
                        break

    def save_api_workflow(self, file_path: Union[str, TextIO]) -> None:
        """
        Save API workflow to a JSON file.

        Args:
            file_path (Union[str, TextIO]): File path or file object to save to

        Raises:
            ValueError: If API workflow has not been generated
        """
        if not self.api_workflow:
            raise ValueError("API workflow has not been generated. Call convert_to_api_format() first.")
        
        FileHandler.write_json_file(file_path, self.api_workflow)


def convert_workflow(input_file: str, output_file: str) -> None:
    """
    Convert standard workflow JSON file to API-compatible workflow JSON file.

    Args:
        input_file (str): Input workflow JSON file path
        output_file (str): Output API workflow JSON file path
    """
    converter = WorkflowConverter()
    converter.load_workflow(input_file)
    converter.convert_to_api_format()
    converter.save_api_workflow(output_file)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert ComfyUI workflow to API format")
    parser.add_argument("--input", type=str, required=True, help="Input workflow JSON file path")
    parser.add_argument("--output", type=str, required=True, help="Output API workflow JSON file path")
    
    args = parser.parse_args()
    convert_workflow(args.input, args.output)
