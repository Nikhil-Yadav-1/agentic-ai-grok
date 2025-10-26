# backend/load_tools.py
import importlib
import inspect
from typing import List
from backend.config import TOOL_MODULES
from langchain_core.tools import BaseTool

# existing load_all_tools should remain; we add a wrapper helper and debug prints
def _wrap_callable_with_exec_debug(fn, name):
    # avoid double-wrapping
    if getattr(fn, "_exec_debug_wrapped", False):
        return fn
    def _wrapped(*args, **kwargs):
        try:
            print(f"tool: executing the {name}... tool")
        except Exception:
            pass
        return fn(*args, **kwargs)
    try:
        _wrapped.__name__ = getattr(fn, "__name__", name)
    except Exception:
        pass
    setattr(_wrapped, "_exec_debug_wrapped", True)
    return _wrapped

def _instrument_tools_module(module_name="backend.tools"):
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"load_tools: could not import {module_name}: {e}")
        return
    changed = []
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            continue
        if inspect.isfunction(attr) and not getattr(attr, "_exec_debug_wrapped", False):
            wrapped = _wrap_callable_with_exec_debug(attr, attr_name)
            setattr(mod, attr_name, wrapped)
            changed.append(attr_name)
    if changed:
        print(f"load_tools: instrumented tool functions in {module_name}: {changed}")
    else:
        print(f"load_tools: no tool functions instrumented in {module_name}")

# call instrumentation early so tools are auto-wrapped before loading
_instrument_tools_module()

def load_all_tools() -> List:
    print("load_tools: load_all_tools called")
    all_tools = []

    for module_name in TOOL_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            print(f"⚠️ Could not import module '{module_name}': {e}")
            continue

        for name, obj in inspect.getmembers(module):
            # LangChain @tool decorator converts functions into BaseTool subclasses
            if isinstance(obj, BaseTool):
                all_tools.append(obj)

    print(f"✅ Loaded {len(all_tools)} tools from {TOOL_MODULES}: {[t.name for t in all_tools]}")
    return all_tools


if __name__ == "__main__":
    # Test tool loading
    tools = load_all_tools()
    print("Loaded tools:", [t.name for t in tools])
