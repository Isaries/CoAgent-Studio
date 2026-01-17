import inspect

from google.genai import types

# google-genai types check
try:
    print(f"FunctionDeclaration location: {inspect.getfile(types.FunctionDeclaration)}")
    print(f"Tool location: {inspect.getfile(types.Tool)}")
    print("Imports successful.")
except Exception as e:
    print(f"Error inspecting types: {e}")
