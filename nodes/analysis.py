import os
import yaml
from pocketflow import Node
from utils.crawl_github_files import crawl_github_files
from utils.call_llm import call_llm
from utils.crawl_local_files import crawl_local_files
from utils.analyze_file_structure import analyze_file_structure


class FetchRepo(Node):
    """Fetches repository files from GitHub or local directory."""
    
    def prep(self, shared):
        repo_url = shared.get("repo_url")
        local_dir = shared.get("local_dir")
        project_name = shared.get("project_name")

        if not project_name:
            # Basic name derivation from URL or directory
            if repo_url:
                project_name = repo_url.split("/")[-1].replace(".git", "")
            else:
                project_name = os.path.basename(os.path.abspath(local_dir))
            shared["project_name"] = project_name

        # Get file patterns directly from shared
        include_patterns = shared["include_patterns"]
        exclude_patterns = shared["exclude_patterns"]
        max_file_size = shared["max_file_size"]

        return {
            "repo_url": repo_url,
            "local_dir": local_dir,
            "token": shared.get("github_token"),
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_file_size": max_file_size,
            "use_relative_paths": True,
        }

    def exec(self, prep_res):
        if prep_res["repo_url"]:
            print(f"Crawling repository: {prep_res['repo_url']}...")
            result = crawl_github_files(
                repo_url=prep_res["repo_url"],
                token=prep_res["token"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"],
            )
        else:
            print(f"Crawling directory: {prep_res['local_dir']}...")
            result = crawl_local_files(
                directory=prep_res["local_dir"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"]
            )

        # Convert dict to list of tuples: [(path, content), ...]
        files_list = list(result.get("files", {}).items())
        if len(files_list) == 0:
            raise ValueError("Failed to fetch files")
        print(f"Fetched {len(files_list)} files.")
        return files_list

    def post(self, shared, prep_res, exec_res):
        shared["files"] = exec_res  # List of (path, content) tuples


class AnalyzeStructure(Node):
    """Analyzes codebase structure without full content analysis."""
    
    def prep(self, shared):
        files_data = shared["files"]
        project_name = shared["project_name"]
        use_cache = shared.get("use_cache", True)
        
        # Convert files list to dict for structure analysis
        files_dict = {path: content for path, content in files_data}
        
        return files_dict, project_name, use_cache
    
    def exec(self, prep_res):
        files_dict, project_name, use_cache = prep_res
        print(f"Analyzing codebase structure for {project_name}...")
        
        # Use the structure analysis utility
        structure = analyze_file_structure(files_dict)
        
        # Create lightweight summary for LLM analysis
        summary_context = self._create_structure_summary(structure)
        
        # Use LLM for high-level architectural understanding
        prompt = f"""
Analyze the structure of the codebase '{project_name}':

{summary_context}

Based on this structural analysis, provide insights about:
1. The overall architecture and organization
2. Key architectural patterns detected
3. Most important directories/modules
4. Entry points and core components
5. Technology stack and framework usage

Format as YAML:

```yaml
architecture:
  type: "framework/library/application/etc"
  pattern: "mvc/layered/microservices/etc"
  description: "Brief architectural description"
key_directories:
  - name: "directory_name"
    importance: "high/medium/low"
    purpose: "what this directory contains"
technology_stack:
  - "primary language/framework"
  - "additional technologies"
entry_points:
  - "file paths that serve as entry points"
core_areas:
  - name: "area name"
    files: ["key file paths"]
    description: "what this area handles"
```"""
        
        response = call_llm(prompt, use_cache=(use_cache and self.cur_retry == 0))
        
        # Parse LLM response
        yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        llm_analysis = yaml.safe_load(yaml_str)
        
        # Combine structure analysis with LLM insights
        structure["llm_analysis"] = llm_analysis
        
        return structure
    
    def post(self, shared, prep_res, exec_res):
        shared["structure"] = exec_res
        print(f"Structural analysis complete. Found {len(exec_res['entry_points'])} entry points and {len(exec_res['core_modules'])} core modules.")
    
    def _create_structure_summary(self, structure):
        """Create a lightweight summary of structure for LLM analysis."""
        summary = f"""
File Structure Summary:
- Total files: {len(structure['file_info'])}
- File types: {dict(structure['file_types'])}
- Directory depth: {structure['directory_structure'].get('depth', 0)}
- Main directories: {structure['directory_structure'].get('common_dirs', [])}

Entry Points Found:
{chr(10).join(f"- {ep}" for ep in structure['entry_points'])}

Core Modules (most imported):
{chr(10).join(f"- {module} (imported by {count} files)" for module, count in structure['core_modules'][:5])}

Detected Patterns:
{chr(10).join(f"- {pattern}: {value}" for pattern, value in structure['patterns'].items())}

Dependencies Overview:
- Files with imports: {len(structure['imports'])}
- Files with exports: {len(structure['exports'])}
"""
        return summary


class IdentifyCore(Node):
    """Identifies core files that represent main abstractions."""
    
    def prep(self, shared):
        structure = shared["structure"]
        files_data = shared["files"]
        project_name = shared["project_name"]
        use_cache = shared.get("use_cache", True)
        max_core_files = min(20, len(files_data) // 2)  # Limit to 20 files or half the codebase
        
        return structure, files_data, project_name, use_cache, max_core_files
    
    def exec(self, prep_res):
        structure, files_data, project_name, use_cache, max_core_files = prep_res
        print(f"Identifying core files for {project_name}...")
        
        # Create context with structural information
        context = self._create_core_selection_context(structure, files_data)
        
        prompt = f"""
Based on the structural analysis of '{project_name}', identify the {max_core_files} most important files that best represent the core abstractions and functionality of this codebase.

{context}

Consider these factors:
1. Entry points and main files
2. Files that are heavily imported by others (high dependency centrality)
3. Files that define key classes, interfaces, or core functionality
4. Files that represent different architectural layers or components
5. Configuration and setup files that define system behavior

Select files that together give the best overview of how this system works.

Format as YAML:

```yaml
core_files:
  - index: 0  # Index in the files list
    path: "path/to/file"
    importance: "high/medium"
    reason: "why this file is core"
  - index: 1
    path: "path/to/file"
    importance: "high/medium"
    reason: "why this file is core"
# ... up to {max_core_files} files
```"""
        
        response = call_llm(prompt, use_cache=(use_cache and self.cur_retry == 0))
        
        # Parse and validate response
        yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        core_selection = yaml.safe_load(yaml_str)
        
        if not isinstance(core_selection, dict) or "core_files" not in core_selection:
            raise ValueError("LLM response missing core_files")
        
        # Validate and extract indices
        core_indices = []
        for item in core_selection["core_files"]:
            if not isinstance(item, dict) or "index" not in item:
                continue
            idx = item["index"]
            if 0 <= idx < len(files_data):
                core_indices.append(idx)
        
        print(f"Selected {len(core_indices)} core files out of {len(files_data)} total files.")
        return core_indices
    
    def post(self, shared, prep_res, exec_res):
        shared["core_files"] = exec_res
    
    def _create_core_selection_context(self, structure, files_data):
        """Create context for core file selection."""
        # List all files with indices
        file_listing = []
        for i, (path, content) in enumerate(files_data):
            size = len(content)
            lines = len(content.splitlines())
            file_listing.append(f"{i}: {path} ({size} bytes, {lines} lines)")
        
        context = f"""
All Files (with indices):
{chr(10).join(file_listing)}

Entry Points:
{chr(10).join(f"- {ep}" for ep in structure.get('entry_points', []))}

Most Imported Files:
{chr(10).join(f"- {module} (imported by {count} files)" for module, count in structure.get('core_modules', [])[:10])}

Architectural Insights:
{structure.get('llm_analysis', {}).get('architecture', {}).get('description', 'No architectural description available')}

Key Areas:
{chr(10).join(f"- {area.get('name', 'Unknown')}: {area.get('description', 'No description')}" for area in structure.get('llm_analysis', {}).get('core_areas', []))}
"""
        return context


class IdentifyAbstractions(Node):
    """Analyzes core files to identify key technical abstractions."""
    
    def prep(self, shared):
        # Read core file indices and extract their content
        core_files = shared.get("core_files", [])
        files = shared["files"]
        
        # Create focused context with only core files
        core_content = []
        for idx in core_files:
            if idx < len(files):
                file_path, file_content = files[idx]
                core_content.append(f"File: {file_path}\n{file_content}")
        
        context = "\n\n---\n\n".join(core_content)
        return context, shared.get("structure", {}), shared.get("project_name", "Unknown Project")

    def exec(self, prep_res):
        context, structure, project_name = prep_res
        
        prompt = f"""
Analyze the following core files from the {project_name} project and identify 5-10 key technical abstractions/components.

For each abstraction, provide:
1. **Name**: Clear, technical component name
2. **Primary Responsibility**: What this component is responsible for in the system
3. **Implementation Approach**: How it's implemented (patterns, techniques, architecture)
4. **Key Interfaces**: Important methods, APIs, or interfaces it exposes
5. **Technical Details**: Architecture patterns, data structures, algorithms used
6. **Dependencies**: What other components it depends on
7. **Usage Context**: When and how other components interact with it

Focus on technical depth suitable for AI development agents who need to understand implementation details.

Project Structure Context:
{structure}

Core Files:
{context}

Return your analysis in YAML format:
```yaml
abstractions:
  - name: "ComponentName"
    primary_responsibility: "What this component does"
    implementation_approach: "How it's implemented"
    key_interfaces: "Important APIs/methods"
    technical_details: "Architecture patterns, data structures"
    dependencies: "Dependencies on other components"
    usage_context: "How other components use this"
    files: [0, 1, 2]  # indices of relevant files
```"""

        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        
        result = yaml.safe_load(yaml_str)
        
        # Validate and ensure we have abstractions
        if not isinstance(result, dict) or "abstractions" not in result:
            raise ValueError("Invalid response format - missing abstractions")
        
        abstractions = result["abstractions"]
        if not isinstance(abstractions, list) or len(abstractions) == 0:
            raise ValueError("No abstractions identified")
        
        return abstractions

    def post(self, shared, prep_res, exec_res):
        shared["abstractions"] = exec_res
        return "default" 