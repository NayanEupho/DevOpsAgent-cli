import langfuse
import pkgutil
import importlib

def find_callback_handler():
    print(f"Langfuse version: {getattr(langfuse, '__version__', 'unknown')}")
    print(f"Langfuse path: {langfuse.__path__}")
    
    for loader, name, ispkg in pkgutil.walk_packages(langfuse.__path__, langfuse.__name__ + '.'):
        print(f"Found module: {name}")
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, 'CallbackHandler'):
                print(f"!!! FOUND CallbackHandler in {name}")
        except Exception as e:
            print(f"Could not import {name}: {e}")

if __name__ == "__main__":
    find_callback_handler()
