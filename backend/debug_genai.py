import google.generativeai as genai

try:
    from google.generativeai.types import FunctionDeclaration

    print("Found in google.generativeai.types")
except ImportError:
    print("Not found in google.generativeai.types")

print("genai content:", dir(genai))
try:
    import google.generativeai.types as types

    print("types content:", dir(types))
except ImportError:
    print("Could not import types")
