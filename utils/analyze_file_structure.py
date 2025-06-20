import ast
import re
import os
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict, Counter

def analyze_file_structure(files: Dict[str, str], language_patterns: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyze codebase structure to extract imports, dependencies, entry points, and patterns
    without requiring full content analysis.
    
    Args:
        files: Dictionary mapping file paths to file contents
        language_patterns: Optional language-specific patterns for analysis
        
    Returns:
        Dictionary containing structural analysis results
    """
    
    # Initialize analysis results
    structure = {
        "file_info": {},           # Per-file metadata
        "imports": defaultdict(set),  # file -> set of imported modules
        "exports": defaultdict(set),  # file -> set of exported symbols  
        "dependencies": defaultdict(set),  # file -> set of files it depends on
        "entry_points": [],        # Likely entry point files
        "core_modules": [],        # Files that are imported by many others
        "file_types": Counter(),   # Count of different file types
        "directory_structure": {}, # Directory organization
        "patterns": {}            # Detected architectural patterns
    }
    
    # Analyze each file
    for file_path, content in files.items():
        file_info = analyze_single_file(file_path, content)
        structure["file_info"][file_path] = file_info
        
        # Count file types
        ext = os.path.splitext(file_path)[1]
        structure["file_types"][ext] += 1
        
        # Extract imports and dependencies
        if file_info["imports"]:
            structure["imports"][file_path] = file_info["imports"]
            
        if file_info["exports"]:
            structure["exports"][file_path] = file_info["exports"]
    
    # Build dependency graph
    structure["dependencies"] = build_dependency_graph(structure["imports"], files.keys())
    
    # Identify entry points and core modules
    structure["entry_points"] = identify_entry_points(structure, files)
    structure["core_modules"] = identify_core_modules(structure["dependencies"])
    
    # Analyze directory structure
    structure["directory_structure"] = analyze_directory_structure(files.keys())
    
    # Detect architectural patterns
    structure["patterns"] = detect_patterns(structure)
    
    return structure

def analyze_single_file(file_path: str, content: str) -> Dict[str, Any]:
    """Analyze a single file to extract imports, exports, and basic info."""
    
    file_info = {
        "size": len(content),
        "lines": len(content.splitlines()),
        "imports": set(),
        "exports": set(),
        "functions": [],
        "classes": [],
        "has_main": False,
        "is_config": False,
        "language": detect_language(file_path)
    }
    
    # Language-specific analysis
    if file_info["language"] == "python":
        analyze_python_file(content, file_info)
    elif file_info["language"] in ["javascript", "typescript"]:
        analyze_js_ts_file(content, file_info)
    elif file_info["language"] in ["go"]:
        analyze_go_file(content, file_info)
    elif file_info["language"] in ["java"]:
        analyze_java_file(content, file_info)
    elif file_info["language"] in ["c", "cpp"]:
        analyze_c_cpp_file(content, file_info)
    
    # Detect configuration files
    file_info["is_config"] = is_config_file(file_path, content)
    
    return file_info

def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    
    lang_map = {
        '.py': 'python', '.pyi': 'python', '.pyx': 'python',
        '.js': 'javascript', '.jsx': 'javascript',
        '.ts': 'typescript', '.tsx': 'typescript',
        '.go': 'go',
        '.java': 'java',
        '.c': 'c', '.h': 'c',
        '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin'
    }
    
    return lang_map.get(ext, 'unknown')

def analyze_python_file(content: str, file_info: Dict) -> None:
    """Analyze Python file for imports, exports, and structure."""
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_info["imports"].add(alias.name)
                    
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_info["imports"].add(node.module)
                    
            elif isinstance(node, ast.FunctionDef):
                file_info["functions"].append(node.name)
                if node.name == "main":
                    file_info["has_main"] = True
                    
            elif isinstance(node, ast.ClassDef):
                file_info["classes"].append(node.name)
                
    except SyntaxError:
        # Fallback to regex if AST parsing fails
        analyze_python_regex(content, file_info)

def analyze_python_regex(content: str, file_info: Dict) -> None:
    """Fallback regex analysis for Python files."""
    # Import patterns
    import_patterns = [
        r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
        r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        file_info["imports"].update(matches)
    
    # Function and class patterns
    func_matches = re.findall(r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)', content, re.MULTILINE)
    class_matches = re.findall(r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content, re.MULTILINE)
    
    file_info["functions"].extend(func_matches)
    file_info["classes"].extend(class_matches)
    
    if "def main(" in content or 'if __name__ == "__main__"' in content:
        file_info["has_main"] = True

def analyze_js_ts_file(content: str, file_info: Dict) -> None:
    """Analyze JavaScript/TypeScript file for imports and exports."""
    # Import patterns
    import_patterns = [
        r'import\s+.*?\s+from\s+[\'"`]([^\'"`]+)[\'"`]',  # import ... from "module"
        r'import\s+[\'"`]([^\'"`]+)[\'"`]',                # import "module"
        r'require\([\'"`]([^\'"`]+)[\'"`]\)',              # require("module")
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        file_info["imports"].update(matches)
    
    # Export patterns
    if re.search(r'export\s+(default\s+)?', content):
        file_info["exports"].add("default" if "export default" in content else "named")

def analyze_go_file(content: str, file_info: Dict) -> None:
    """Analyze Go file for imports and structure."""
    # Import patterns
    import_matches = re.findall(r'import\s+["`]([^"`]+)["`]', content)
    file_info["imports"].update(import_matches)
    
    # Function patterns
    func_matches = re.findall(r'func\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
    file_info["functions"].extend(func_matches)
    
    if "func main(" in content:
        file_info["has_main"] = True

def analyze_java_file(content: str, file_info: Dict) -> None:
    """Analyze Java file for imports and structure."""
    # Import patterns
    import_matches = re.findall(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*);', content)
    file_info["imports"].update(import_matches)
    
    # Class patterns
    class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
    file_info["classes"].extend(class_matches)

def analyze_c_cpp_file(content: str, file_info: Dict) -> None:
    """Analyze C/C++ file for includes and structure."""
    # Include patterns
    include_matches = re.findall(r'#include\s+[<"]([^>"]+)[>"]', content)
    file_info["imports"].update(include_matches)
    
    # Function patterns (basic)
    func_matches = re.findall(r'^\s*(?:static\s+)?(?:inline\s+)?[a-zA-Z_][a-zA-Z0-9_*\s]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content, re.MULTILINE)
    file_info["functions"].extend(func_matches)
    
    if "int main(" in content:
        file_info["has_main"] = True

def is_config_file(file_path: str, content: str) -> bool:
    """Determine if a file is a configuration file."""
    config_indicators = [
        # File names
        'config', 'settings', 'setup', 'Makefile', 'Dockerfile',
        # File extensions
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.env', '.properties'
    ]
    
    file_lower = file_path.lower()
    return any(indicator in file_lower for indicator in config_indicators)

def build_dependency_graph(imports: Dict[str, Set], all_files: List[str]) -> Dict[str, Set]:
    """Build dependency graph between files."""
    dependencies = defaultdict(set)
    
    # Create mapping from module names to file paths
    module_to_file = {}
    for file_path in all_files:
        # Simple heuristic: convert file path to module name
        module_name = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
        module_to_file[module_name] = file_path
        
        # Also try basename
        basename = os.path.splitext(os.path.basename(file_path))[0]
        module_to_file[basename] = file_path
    
    # Build dependencies
    for file_path, file_imports in imports.items():
        for imported_module in file_imports:
            # Try to find corresponding file
            if imported_module in module_to_file:
                target_file = module_to_file[imported_module]
                if target_file != file_path:  # Don't self-reference
                    dependencies[file_path].add(target_file)
    
    return dependencies

def identify_entry_points(structure: Dict, files: Dict[str, str]) -> List[str]:
    """Identify likely entry point files."""
    entry_points = []
    
    for file_path, file_info in structure["file_info"].items():
        # Check for main functions
        if file_info["has_main"]:
            entry_points.append(file_path)
            continue
            
        # Check for typical entry point names
        basename = os.path.basename(file_path).lower()
        if basename in ['main.py', 'app.py', 'server.py', 'index.js', 'main.go', 'main.java']:
            entry_points.append(file_path)
            continue
            
        # Check for setup files
        if basename in ['setup.py', '__init__.py'] and file_info["size"] > 100:
            entry_points.append(file_path)
    
    return entry_points

def identify_core_modules(dependencies: Dict[str, Set]) -> List[Tuple[str, int]]:
    """Identify core modules based on how many files depend on them."""
    dependents = defaultdict(int)
    
    for file_path, deps in dependencies.items():
        for dep in deps:
            dependents[dep] += 1
    
    # Sort by number of dependents
    core_modules = sorted(dependents.items(), key=lambda x: x[1], reverse=True)
    return core_modules[:10]  # Top 10 most depended-upon files

def analyze_directory_structure(file_paths: List[str]) -> Dict[str, Any]:
    """Analyze directory organization patterns."""
    directories = defaultdict(list)
    
    for file_path in file_paths:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            directories[dir_path].append(os.path.basename(file_path))
    
    return {
        "directories": dict(directories),
        "depth": max(len(path.split('/')) for path in file_paths),
        "common_dirs": [d for d, files in directories.items() if len(files) > 3]
    }

def detect_patterns(structure: Dict) -> Dict[str, Any]:
    """Detect common architectural patterns."""
    patterns = {}
    
    directories = structure["directory_structure"]["directories"]
    
    # MVC pattern
    has_mvc = any(d in str(directories.keys()).lower() for d in ['models', 'views', 'controllers'])
    patterns["mvc"] = has_mvc
    
    # Layered architecture
    has_layers = any(d in str(directories.keys()).lower() for d in ['service', 'repository', 'controller', 'entity'])
    patterns["layered"] = has_layers
    
    # Test structure
    has_tests = any('test' in d.lower() for d in directories.keys())
    patterns["has_tests"] = has_tests
    
    # Package structure
    has_packages = len(directories) > 3
    patterns["modular"] = has_packages
    
    return patterns

if __name__ == "__main__":
    # Example usage
    example_files = {
        "main.py": """
import os
import sys
from utils.helper import process_data

def main():
    print("Hello World")

if __name__ == "__main__":
    main()
""",
        "utils/helper.py": """
def process_data(data):
    return data.upper()

class DataProcessor:
    def __init__(self):
        pass
"""
    }
    
    result = analyze_file_structure(example_files)
    print("Structure Analysis Results:")
    for key, value in result.items():
        print(f"{key}: {value}") 