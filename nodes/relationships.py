import yaml
from pocketflow import Node
from utils.call_llm import call_llm


class AnalyzeRelationships(Node):
    """Analyzes relationships between technical components and architectural patterns."""
    
    def prep(self, shared):
        abstractions = shared["abstractions"]
        structure = shared.get("structure", {})
        project_name = shared.get("project_name", "Unknown Project")
        return abstractions, structure, project_name

    def exec(self, prep_res):
        abstractions, structure, project_name = prep_res
        
        # Create abstraction summary for context
        abstraction_list = []
        for i, abs_info in enumerate(abstractions):
            abstraction_list.append(f"{i}: {abs_info['name']} - {abs_info['primary_responsibility']}")
        abstraction_context = "\n".join(abstraction_list)
        
        prompt = f"""
Analyze the relationships between these technical components from {project_name} and provide comprehensive architectural analysis.

Components:
{abstraction_context}

Structural Analysis:
{structure}

Provide:
1. **Technical Project Summary**: Overall architecture and technical approach
2. **Architecture Overview**: Design patterns, architectural decisions, and technical philosophy
3. **Component Relationships**: How components interact technically (dependencies, data flow, communication patterns)
4. **Data Flow Patterns**: How data moves through the system
5. **API Interfaces**: Key interfaces and contracts between components

Return in YAML format:
```yaml
summary: "Comprehensive technical project summary"
architecture_overview: "Architectural patterns and design decisions"
component_relationships:
  - from: 0  # component index
    to: 1    # component index
    relationship_type: "depends_on/uses/inherits/implements/calls"
    description: "Technical description of the relationship"
    interface_details: "API/interface details"
data_flow:
  - flow_name: "DataProcessingFlow"
    description: "How data flows through components"
    components: [0, 1, 2]
    details: "Technical implementation details"
api_interfaces:
  - component: 0
    interface_name: "PublicAPI"
    methods: ["method1", "method2"]
    description: "Interface description and usage"
```"""

        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        
        result = yaml.safe_load(yaml_str)
        
        # Validate response
        required_keys = ["summary", "architecture_overview", "component_relationships"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key: {key}")
        
        return result

    def post(self, shared, prep_res, exec_res):
        shared["relationships"] = exec_res
        return "default"


class OrderChapters(Node):
    """Orders the identified abstractions for logical presentation based on dependencies and architectural layers."""
    
    def prep(self, shared):
        abstractions = shared["abstractions"]
        relationships = shared.get("relationships", {})
        return abstractions, relationships
    
    def exec(self, prep_res):
        abstractions, relationships = prep_res
        
        # Create context for ordering decision
        abstraction_list = []
        for i, abs_info in enumerate(abstractions):
            abstraction_list.append(f"{i}: {abs_info['name']} - {abs_info['primary_responsibility']}")
        
        component_relationships = relationships.get("component_relationships", [])
        relationship_context = []
        for rel in component_relationships:
            from_idx = rel.get("from", 0)
            to_idx = rel.get("to", 0)
            if from_idx < len(abstractions) and to_idx < len(abstractions):
                from_name = abstractions[from_idx]["name"]
                to_name = abstractions[to_idx]["name"]
                rel_type = rel.get("relationship_type", "relates_to")
                relationship_context.append(f"{from_name} -> {to_name} ({rel_type})")
        
        prompt = f"""
Order these technical components for logical presentation in AI agent development documentation. 
Consider architectural layers, dependency hierarchy, and logical learning progression.

Components:
{chr(10).join(abstraction_list)}

Relationships:
{chr(10).join(relationship_context)}

Architecture Overview:
{relationships.get("architecture_overview", "No architecture description available")}

Provide the optimal order for technical documentation, considering:
1. Foundational components first (low-level, widely depended upon)
2. Core business logic and main abstractions
3. Higher-level orchestration and integration components
4. Specialized or auxiliary components

Return the order as a YAML list of indices:

```yaml
chapter_order: [2, 0, 1, 4, 3]  # Example order using component indices
reasoning: "Brief explanation of the ordering logic"
```"""

        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        
        result = yaml.safe_load(yaml_str)
        
        if not isinstance(result, dict) or "chapter_order" not in result:
            raise ValueError("Invalid response format - missing chapter_order")
        
        chapter_order = result["chapter_order"]
        if not isinstance(chapter_order, list):
            raise ValueError("chapter_order must be a list")
        
        # Validate all indices are valid
        valid_order = []
        for idx in chapter_order:
            if isinstance(idx, int) and 0 <= idx < len(abstractions):
                valid_order.append(idx)
        
        if not valid_order:
            # Fallback to simple sequential order
            valid_order = list(range(len(abstractions)))
        
        print(f"Ordered {len(valid_order)} components for documentation")
        return valid_order
    
    def post(self, shared, prep_res, exec_res):
        shared["chapter_order"] = exec_res
        return "default" 