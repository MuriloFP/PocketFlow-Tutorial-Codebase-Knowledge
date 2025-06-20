import os
from pocketflow import Node, BatchNode
from utils.call_llm import call_llm


class WriteProjectOverview(Node):
    """Generates comprehensive project overview for AI agent system prompts."""
    
    def prep(self, shared):
        return {
            "project_name": shared.get("project_name", "Unknown Project"),
            "structure": shared.get("structure", {}),
            "abstractions": shared.get("abstractions", []),
            "relationships": shared.get("relationships", {}),
            "files": shared.get("files", [])
        }

    def exec(self, prep_res):
        project_data = prep_res
        project_name = project_data["project_name"]
        structure = project_data["structure"]
        abstractions = project_data["abstractions"]
        relationships = project_data["relationships"]
        
        # Create component summary
        component_summary = []
        for i, abs_info in enumerate(abstractions):
            component_summary.append(f"- **{abs_info['name']}**: {abs_info['primary_responsibility']}")
        components_text = "\n".join(component_summary)
        
        # Create technology stack info
        files = project_data["files"]
        file_extensions = set()
        for file_path, _ in files:
            if '.' in file_path:
                ext = file_path.split('.')[-1].lower()
                file_extensions.add(ext)
        
        prompt = f"""
Generate a comprehensive project overview document for {project_name} specifically designed for AI development agents. This will be included in AI agent system prompts to provide complete project context.

Project Structure:
{structure}

Core Components:
{components_text}

Relationships Analysis:
{relationships}

File Types: {', '.join(sorted(file_extensions))}

Create a comprehensive overview covering:

1. **Project Purpose & Scope**: What the project does and its technical objectives
2. **Architecture Overview**: High-level architecture, design patterns, and technical approach
3. **Core Components**: Summary of main components and their roles
4. **Technology Stack**: Languages, frameworks, libraries, and tools used
5. **Development Patterns**: Coding patterns, conventions, and architectural decisions
6. **Component Interactions**: How components work together technically
7. **Key Interfaces & APIs**: Important interfaces for development
8. **Development Guidelines**: Technical guidelines for implementing new features
9. **Navigation Guide**: How AI agents should navigate the codebase for different tasks
10. **Extension Points**: Where and how new features should be added

Format as a comprehensive technical document suitable for AI agent system prompts. Use clear technical language and provide specific guidance for development tasks.
"""

        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        shared["project_overview"] = exec_res
        return "default"


class WriteChapters(BatchNode):
    """Generates detailed technical documentation for each component."""
    
    def prep(self, shared):
        chapter_order = shared["chapter_order"]
        abstractions = shared["abstractions"]
        relationships = shared["relationships"]
        files = shared["files"]
        
        # Prepare comprehensive context for each chapter
        chapters_to_write = []
        for order_idx in chapter_order:
            abstraction = abstractions[order_idx]
            
            # Get related files content
            file_contents = []
            for file_idx in abstraction.get("files", []):
                if file_idx < len(files):
                    file_path, content = files[file_idx]
                    file_contents.append(f"### {file_path}\n```\n{content}\n```")
            
            chapter_context = {
                "abstraction": abstraction,
                "related_abstractions": abstractions,
                "relationships": relationships,
                "file_contents": file_contents,
                "abstraction_index": order_idx
            }
            chapters_to_write.append(chapter_context)
        
        return chapters_to_write

    def exec(self, chapter_context):
        abstraction = chapter_context["abstraction"]
        related_abstractions = chapter_context["related_abstractions"]
        relationships = chapter_context["relationships"]
        file_contents = chapter_context["file_contents"]
        abstraction_index = chapter_context["abstraction_index"]
        
        # Find relationships involving this component
        relevant_relationships = []
        for rel in relationships.get("component_relationships", []):
            if rel.get("from") == abstraction_index or rel.get("to") == abstraction_index:
                relevant_relationships.append(rel)
        
        # Create context about related components
        related_components_info = []
        for rel in relevant_relationships:
            other_idx = rel.get("to") if rel.get("from") == abstraction_index else rel.get("from")
            if other_idx < len(related_abstractions):
                other_component = related_abstractions[other_idx]
                related_components_info.append(f"- **{other_component['name']}**: {rel.get('description', 'No description')}")
        
        files_content = "\n\n".join(file_contents) if file_contents else "No specific files identified for this component."
        related_text = "\n".join(related_components_info) if related_components_info else "No direct relationships identified."
        
        prompt = f"""
Write comprehensive technical documentation for the '{abstraction['name']}' component. This documentation is for AI development agents who need to understand implementation details for feature development.

Component Information:
- **Name**: {abstraction['name']}
- **Primary Responsibility**: {abstraction['primary_responsibility']}
- **Implementation Approach**: {abstraction['implementation_approach']}
- **Key Interfaces**: {abstraction['key_interfaces']}
- **Technical Details**: {abstraction['technical_details']}
- **Dependencies**: {abstraction['dependencies']}
- **Usage Context**: {abstraction['usage_context']}

Related Components:
{related_text}

Source Code:
{files_content}

Generate comprehensive documentation including:

1. **Component Overview**: Technical summary and architectural role
2. **Implementation Details**: How it's implemented, patterns used, data structures
3. **API Reference**: Key methods, functions, interfaces with usage examples
4. **Architecture Integration**: How it fits into the overall system architecture
5. **Data Structures**: Important data types, models, schemas used
6. **Usage Patterns**: Common usage patterns and examples
7. **Dependencies & Relationships**: Technical dependencies and interaction patterns
8. **Extension Points**: How to extend or modify this component
9. **Performance Considerations**: Performance characteristics and optimization notes
10. **Development Guidelines**: Best practices for working with this component

Use technical language appropriate for AI development agents. Include code examples where relevant. Focus on implementation details that would be needed for feature development.

Format as markdown with clear headings and technical depth.
"""

        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res_list):
        shared["chapters"] = exec_res_list
        return "default"


class CombineTutorial(Node):
    """Assembles final documentation structure with project overview, enhanced cross-referencing, and AI agent navigation features."""
    
    def prep(self, shared):
        return {
            "project_name": shared.get("project_name", "Unknown Project"),
            "abstractions": shared["abstractions"],
            "relationships": shared["relationships"],
            "chapter_order": shared["chapter_order"],
            "chapters": shared["chapters"],
            "project_overview": shared.get("project_overview", ""),
            "output_dir": shared.get("output_dir", "output")
        }

    def exec(self, prep_res):
        project_name = prep_res["project_name"]
        abstractions = prep_res["abstractions"]
        relationships = prep_res["relationships"]
        chapter_order = prep_res["chapter_order"]
        chapters = prep_res["chapters"]
        project_overview = prep_res["project_overview"]
        base_output_dir = prep_res["output_dir"]
        
        # Create project-specific output directory
        safe_project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        output_dir = os.path.join(base_output_dir, safe_project_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Write project overview file
        overview_path = os.path.join(output_dir, "project_overview.md")
        with open(overview_path, "w", encoding="utf-8") as f:
            f.write(f"# {project_name} - Development Overview\n\n")
            f.write(project_overview)
            f.write("\n\n---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)")
        
        # Generate enhanced index content with technical focus
        index_content = f"# {project_name} - Technical Documentation\n\n"
        
        # Add technical summary
        if "summary" in relationships:
            index_content += "## Technical Overview\n\n"
            index_content += f"{relationships['summary']}\n\n"
        
        # Add architecture overview
        if "architecture_overview" in relationships:
            index_content += "## Architecture Overview\n\n"
            index_content += f"{relationships['architecture_overview']}\n\n"
        
        # Create enhanced Mermaid diagram showing technical relationships
        index_content += "## Component Architecture\n\n"
        index_content += "```mermaid\n"
        index_content += "graph TD\n"
        
        # Add nodes for each abstraction
        for i, abstraction in enumerate(abstractions):
            node_name = f"A{i}"
            clean_name = abstraction["name"].replace('"', '\\"')
            index_content += f'    {node_name}["{clean_name}<br/>{abstraction["primary_responsibility"][:50]}..."]\n'
        
        # Add relationships
        for rel in relationships.get("component_relationships", []):
            from_idx = rel.get("from", 0)
            to_idx = rel.get("to", 0)
            if from_idx < len(abstractions) and to_idx < len(abstractions):
                relationship_type = rel.get("relationship_type", "relates_to")
                index_content += f"    A{from_idx} -->|{relationship_type}| A{to_idx}\n"
        
        index_content += "```\n\n"
        
        # Add data flow diagram if available
        if relationships.get("data_flow"):
            index_content += "## Data Flow\n\n"
            index_content += "```mermaid\n"
            index_content += "flowchart LR\n"
            for flow in relationships["data_flow"]:
                flow_components = flow.get("components", [])
                for i in range(len(flow_components) - 1):
                    current = flow_components[i]
                    next_comp = flow_components[i + 1]
                    if current < len(abstractions) and next_comp < len(abstractions):
                        index_content += f"    A{current} --> A{next_comp}\n"
            index_content += "```\n\n"
        
        # Add component documentation links
        index_content += "## Component Documentation\n\n"
        chapter_files = []
        for i, order_idx in enumerate(chapter_order):
            abstraction = abstractions[order_idx]
            # Create safe filename
            safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in abstraction["name"].lower())
            chapter_filename = f"{i+1:02d}_{safe_name}.md"
            chapter_files.append((chapter_filename, chapters[i]))
            
            index_content += f"{i+1}. **[{abstraction['name']}]({chapter_filename})** - {abstraction['primary_responsibility']}\n"
        
        index_content += "\n\n---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)"
        
        # Write index file
        index_path = os.path.join(output_dir, "index.md")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        
        # Write individual chapter files
        for filename, content in chapter_files:
            chapter_path = os.path.join(output_dir, filename)
            with open(chapter_path, "w", encoding="utf-8") as f:
                f.write(content)
                f.write("\n\n---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)")
        
        return {
            "output_directory": output_dir,
            "files_created": {
                "project_overview": overview_path,
                "index": index_path,
                "chapters": [os.path.join(output_dir, filename) for filename, _ in chapter_files]
            }
        }

    def post(self, shared, prep_res, exec_res):
        shared["final_output_dir"] = exec_res["output_directory"]
        print("\nDocumentation generated successfully!")
        print(f"Output directory: {exec_res['output_directory']}")
        print(f"Project overview: {exec_res['files_created']['project_overview']}")
        print(f"Main index: {exec_res['files_created']['index']}")
        print(f"Component documentation files: {len(exec_res['files_created']['chapters'])}")
        return "default" 