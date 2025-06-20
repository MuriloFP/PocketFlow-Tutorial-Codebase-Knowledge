"""
Legacy import file for backward compatibility.

The node classes have been refactored into a modular structure under the nodes/ package.
This file provides backward compatibility by importing all classes from the new structure.
"""

# Import all node classes from the new modular structure
from nodes import (
    # Analysis nodes
    FetchRepo,
    AnalyzeStructure,
    IdentifyCore,
    IdentifyAbstractions,
    
    # Relationship nodes
    AnalyzeRelationships,
    OrderChapters,
    
    # Output nodes
    WriteProjectOverview,
    WriteChapters,
    CombineTutorial
)

# Keep backward compatibility - export everything
__all__ = [
    'FetchRepo',
    'AnalyzeStructure', 
    'IdentifyCore',
    'IdentifyAbstractions',
    'AnalyzeRelationships',
    'OrderChapters',
    'WriteProjectOverview',
    'WriteChapters',
    'CombineTutorial'
]
