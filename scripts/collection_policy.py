"""Bounded research collection policy shared by collectors and coverage audit."""
MAX_RESEARCH_TARGETS = 8
MAX_TOTAL_TARGETS = 16
EXPECTED_CADENCE_HOURS = 3
TARGET_CAPTURE_TOLERANCE_HOURS = 6


def research_capacity(base_source_count):
    if not 0 <= base_source_count <= MAX_TOTAL_TARGETS:
        raise ValueError('Configured base sources exceed the total collection limit')
    return min(MAX_RESEARCH_TARGETS, MAX_TOTAL_TARGETS-base_source_count)
