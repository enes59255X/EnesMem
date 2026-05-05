"""
lua_engine.py — Basic Lua scripting framework for EnesMem.
Provides Lua script execution with memory access bindings.
"""
import re
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
import os
import json

from utils.patterns import DataType
from utils.logger import log


@dataclass
class LuaScript:
    """Represents a Lua script with metadata."""
    name: str
    description: str
    code: str
    enabled: bool = False
    hotkey: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "enabled": self.enabled,
            "hotkey": self.hotkey
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LuaScript":
        return cls(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            code=data.get("code", ""),
            enabled=data.get("enabled", False),
            hotkey=data.get("hotkey", "")
        )


class LuaEngine:
    """
    Basic Lua scripting engine for EnesMem.
    Parses and executes simplified Lua scripts for memory operations.
    """
    
    # Pre-defined script templates
    TEMPLATES = {
        "read_value": '''-- Read value from address
local addr = 0xADDRESS
local val = readInteger(addr)
print("Value: " .. val)''',
        
        "write_value": '''-- Write value to address
local addr = 0xADDRESS
local newVal = VALUE
writeInteger(addr, newVal)
print("Written: " .. newVal)''',
        
        "freeze_value": '''-- Freeze/unfreeze address
local addr = 0xADDRESS
local val = VALUE
freeze(addr, val)
sleep(1000)
unfreeze(addr)''',
        
        "auto_assemble": '''-- Simple AOB injection
local addr = AOBScan("PATTERN")
if addr then
    writeBytes(addr, {BYTES})
    print("Injected at: " .. addr)
end''',
        
        "loop_script": '''-- Loop script with condition
local addr = 0xADDRESS
local target = TARGET
while true do
    local val = readInteger(addr)
    if val < target then
        writeInteger(addr, target)
    end
    sleep(100)
end'''
    }
    
    def __init__(self):
        self._scripts: Dict[str, LuaScript] = {}
        self._running: Dict[str, bool] = {}
        self._mem_io = None  # Will be set when process attached
        self._config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "lua_scripts.json"
        )
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        
        # Built-in functions available to scripts
        self._builtins: Dict[str, Callable] = {
            "print": self._lua_print,
            "sleep": self._lua_sleep,
            "readBytes": self._lua_read_bytes,
            "writeBytes": self._lua_write_bytes,
            "readInteger": self._lua_read_int,
            "readFloat": self._lua_read_float,
            "writeInteger": self._lua_write_int,
            "writeFloat": self._lua_write_float,
            "freeze": self._lua_freeze,
            "unfreeze": self._lua_unfreeze,
            "getAddress": self._lua_get_address,
            "AOBScan": self._lua_aob_scan,
        }
    
    def set_memory_io(self, mem_io) -> None:
        """Set memory I/O interface (MemoryIO instance)."""
        self._mem_io = mem_io
    
    def add_script(self, script: LuaScript) -> bool:
        """Add a script to the collection."""
        if script.name in self._scripts:
            return False
        self._scripts[script.name] = script
        return True
    
    def remove_script(self, name: str) -> bool:
        """Remove a script by name."""
        if name in self._scripts:
            del self._scripts[name]
            if name in self._running:
                del self._running[name]
            return True
        return False
    
    def get_script(self, name: str) -> Optional[LuaScript]:
        """Get a script by name."""
        return self._scripts.get(name)
    
    def list_scripts(self) -> List[LuaScript]:
        """Get all scripts."""
        return list(self._scripts.values())
    
    def update_script(self, name: str, script: LuaScript) -> bool:
        """Update an existing script."""
        if name not in self._scripts:
            return False
        self._scripts[name] = script
        return True
    
    def execute(self, script_name: str) -> tuple[bool, str]:
        """
        Execute a script by name.
        
        Returns:
            Tuple of (success: bool, output: str)
        """
        script = self._scripts.get(script_name)
        if not script:
            return False, f"Script not found: {script_name}"
        
        if not self._mem_io:
            return False, "No process attached"
        
        return self.execute_code(script.code, script_name)
    
    def execute_code(self, code: str, context: str = "anonymous") -> tuple[bool, str]:
        """
        Execute raw Lua-like code.
        
        This is a simplified parser that handles basic Lua syntax
        for memory operations.
        
        Returns:
            Tuple of (success: bool, output: str)
        """
        output = []
        lines = code.strip().split('\n')
        
        # Remove comments
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if '--' in line:
                line = line[:line.index('--')].strip()
            if line:
                cleaned_lines.append(line)
        
        # Simple line-by-line execution
        for i, line in enumerate(cleaned_lines):
            try:
                result = self._execute_line(line, output.append)
                if not result:
                    return False, '\n'.join(output)
            except Exception as e:
                output.append(f"Error at line {i+1}: {e}")
                log.error("LuaEngine: Line %d error: %s", i+1, e)
                return False, '\n'.join(output)
        
        return True, '\n'.join(output) if output else "Script executed successfully"
    
    def _execute_line(self, line: str, output_fn: Callable[[str], None]) -> bool:
        """Execute a single line of Lua-like code."""
        # Handle local variable assignment
        local_match = re.match(r'^local\s+(\w+)\s*=\s*(.+)$', line)
        if local_match:
            var_name = local_match.group(1)
            expr = local_match.group(2).strip()
            
            # Evaluate expression
            value = self._eval_expression(expr, output_fn)
            # Store in context (simplified - would need proper scope)
            return True
        
        # Handle function call
        func_match = re.match(r'^(\w+)\s*\((.*)\)$', line)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2).strip()
            
            if func_name in self._builtins:
                args = self._parse_args(args_str)
                try:
                    result = self._builtins[func_name](*args)
                    if result is not None:
                        output_fn(str(result))
                except Exception as e:
                    output_fn(f"Error calling {func_name}: {e}")
                    return False
            else:
                output_fn(f"Unknown function: {func_name}")
                return False
            return True
        
        # Handle while loops (simplified - just check first iteration)
        if line.startswith('while'):
            # Loop handling would require more complex parser
            # For now, just skip
            return True
        
        if line == 'end':
            return True
        
        output_fn(f"Unknown statement: {line}")
        return False
    
    def _eval_expression(self, expr: str, output_fn: Callable[[str], None]) -> Any:
        """Evaluate a Lua expression."""
        expr = expr.strip()
        
        # Hex number
        if expr.startswith('0x'):
            return int(expr, 16)
        
        # Decimal number
        try:
            return int(expr)
        except ValueError:
            pass
        
        try:
            return float(expr)
        except ValueError:
            pass
        
        # String
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]
        
        # Function call
        func_match = re.match(r'^(\w+)\s*\((.*)\)$', expr)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2).strip()
            
            if func_name in self._builtins:
                args = self._parse_args(args_str)
                return self._builtins[func_name](*args)
        
        # Variable (return as-is for now)
        return expr
    
    def _parse_args(self, args_str: str) -> List[Any]:
        """Parse function arguments."""
        if not args_str:
            return []
        
        args = []
        # Simple split by comma (doesn't handle nested structures)
        for arg in args_str.split(','):
            arg = arg.strip()
            
            # Hex
            if arg.startswith('0x'):
                args.append(int(arg, 16))
            # Integer
            elif arg.isdigit() or (arg.startswith('-') and arg[1:].isdigit()):
                args.append(int(arg))
            # Float
            elif '.' in arg and arg.replace('.', '').replace('-', '').isdigit():
                args.append(float(arg))
            # String
            elif (arg.startswith('"') and arg.endswith('"')) or \
                 (arg.startswith("'") and arg.endswith("'")):
                args.append(arg[1:-1])
            # Table/array (simplified)
            elif arg.startswith('{') and arg.endswith('}'):
                # Parse as list of hex or numbers
                inner = arg[1:-1]
                items = []
                for item in inner.split(','):
                    item = item.strip()
                    if item.startswith('0x'):
                        items.append(int(item, 16))
                    elif item.isdigit():
                        items.append(int(item))
                args.append(items)
            else:
                args.append(arg)
        
        return args
    
    # Built-in function implementations
    def _lua_print(self, *args) -> str:
        """Print function for Lua."""
        return ' '.join(str(a) for a in args)
    
    def _lua_sleep(self, ms: int) -> None:
        """Sleep for milliseconds."""
        import time
        time.sleep(ms / 1000.0)
    
    def _lua_read_bytes(self, addr: int, size: int) -> Optional[bytes]:
        """Read bytes from memory."""
        if not self._mem_io:
            return None
        try:
            return self._mem_io.read_bytes(addr, size)
        except:
            return None
    
    def _lua_write_bytes(self, addr: int, bytes_data: List[int]) -> bool:
        """Write bytes to memory."""
        if not self._mem_io:
            return False
        try:
            data = bytes(bytes_data)
            self._mem_io.write_bytes(addr, data)
            return True
        except:
            return False
    
    def _lua_read_int(self, addr: int) -> Optional[int]:
        """Read integer from memory."""
        if not self._mem_io:
            return None
        try:
            return self._mem_io.read_value(addr, DataType.INT32)
        except:
            return None
    
    def _lua_read_float(self, addr: int) -> Optional[float]:
        """Read float from memory."""
        if not self._mem_io:
            return None
        try:
            return self._mem_io.read_value(addr, DataType.FLOAT)
        except:
            return None
    
    def _lua_write_int(self, addr: int, value: int) -> bool:
        """Write integer to memory."""
        if not self._mem_io:
            return False
        try:
            self._mem_io.write_value(addr, value, DataType.INT32)
            return True
        except:
            return False
    
    def _lua_write_float(self, addr: int, value: float) -> bool:
        """Write float to memory."""
        if not self._mem_io:
            return False
        try:
            self._mem_io.write_value(addr, value, DataType.FLOAT)
            return True
        except:
            return False
    
    def _lua_freeze(self, addr: int, value: Any) -> bool:
        """Freeze value at address."""
        # Would integrate with Freezer class
        log.info("LuaEngine: Freeze 0x%X = %s", addr, value)
        return True
    
    def _lua_unfreeze(self, addr: int) -> bool:
        """Unfreeze address."""
        log.info("LuaEngine: Unfreeze 0x%X", addr)
        return True
    
    def _lua_get_address(self, module: str, offset: int = 0) -> Optional[int]:
        """Get address of module + offset."""
        if not self._mem_io:
            return None
        # Simplified - would need proper module lookup
        return None
    
    def _lua_aob_scan(self, pattern: str) -> Optional[int]:
        """Scan for AOB pattern."""
        if not self._mem_io:
            return None
        # Simplified - would integrate with AOB scanner
        return None
    
    def save_scripts(self) -> bool:
        """Save all scripts to file."""
        try:
            data = {
                "scripts": [s.to_dict() for s in self._scripts.values()]
            }
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            log.info("LuaEngine: Saved %d scripts", len(self._scripts))
            return True
        except Exception as e:
            log.error("LuaEngine: Save failed: %s", e)
            return False
    
    def load_scripts(self) -> bool:
        """Load scripts from file."""
        try:
            if not os.path.exists(self._config_path):
                return True
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._scripts.clear()
            for s_data in data.get("scripts", []):
                try:
                    script = LuaScript.from_dict(s_data)
                    self._scripts[script.name] = script
                except Exception as e:
                    log.warning("LuaEngine: Failed to load script: %s", e)
            
            log.info("LuaEngine: Loaded %d scripts", len(self._scripts))
            return True
        except Exception as e:
            log.error("LuaEngine: Load failed: %s", e)
            return False
    
    def get_template(self, name: str) -> Optional[str]:
        """Get a script template by name."""
        return self.TEMPLATES.get(name)
    
    def list_templates(self) -> Dict[str, str]:
        """List all available templates."""
        return dict(self.TEMPLATES)


# Global instance
lua_engine = LuaEngine()
