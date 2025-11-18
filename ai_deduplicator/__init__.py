"""AI Deduplicator - Intelligent file organization and deduplication tools.

This package provides two main tools:
- ai_dynamic_deduplicate: AI-driven intelligent file organization
- deduplicate_files: Rule-based file deduplication
"""

from ai_deduplicator.ai_dynamic_deduplicate import main as ai_deduplicate
from ai_deduplicator.deduplicate_files import main as deduplicate
from ai_deduplicator import dedup_utils

__version__ = "0.1.0"
__all__ = ['ai_deduplicate', 'deduplicate', 'dedup_utils']
