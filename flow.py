from pocketflow import Flow
# Import all node classes from nodes.py
from nodes import (
    FetchRepo,
    AnalyzeStructure,
    IdentifyCore,
    IdentifyAbstractions,
    AnalyzeRelationships,
    OrderChapters,
    WriteProjectOverview,
    WriteChapters,
    CombineTutorial
)

def create_tutorial_flow():
    """Creates and returns the AI agent development documentation generation flow."""

    # Instantiate nodes with the enhanced technical analysis approach
    fetch_repo = FetchRepo()
    analyze_structure = AnalyzeStructure(max_retries=3, wait=10)
    identify_core = IdentifyCore(max_retries=3, wait=10)
    identify_abstractions = IdentifyAbstractions(max_retries=5, wait=20)
    analyze_relationships = AnalyzeRelationships(max_retries=5, wait=20)
    order_chapters = OrderChapters(max_retries=5, wait=20)
    write_project_overview = WriteProjectOverview(max_retries=3, wait=10)
    write_chapters = WriteChapters(max_retries=5, wait=20) # This is a BatchNode
    combine_tutorial = CombineTutorial()

    # Connect nodes in the enhanced technical documentation sequence
    fetch_repo >> analyze_structure
    analyze_structure >> identify_core
    identify_core >> identify_abstractions
    identify_abstractions >> analyze_relationships
    analyze_relationships >> order_chapters
    order_chapters >> write_project_overview
    write_project_overview >> write_chapters
    write_chapters >> combine_tutorial

    # Create the flow starting with FetchRepo
    tutorial_flow = Flow(start=fetch_repo)

    return tutorial_flow
