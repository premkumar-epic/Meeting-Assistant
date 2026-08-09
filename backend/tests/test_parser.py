from __future__ import annotations

import pytest
from app.services.parser import extract_entities, extract_action_items


def test_extract_entities_empty():
    assert extract_entities("") == []
    assert extract_entities("   ") == []


def test_extract_entities_detection():
    text = "We will meet with Google and John Doe on December 25th, 2026."
    entities = extract_entities(text)
    
    # Asserting entity types detected
    labels = {e["label"] for e in entities}
    texts = {e["text"] for e in entities}
    
    assert "ORG" in labels  # Google
    assert "PERSON" in labels  # John Doe
    assert "DATE" in labels  # December 25th, 2026
    
    assert "Google" in texts
    assert "John Doe" in texts


def test_extract_action_items_empty():
    assert extract_action_items("") == []


def test_extract_action_items_rules():
    # Test trigger word triggers action item
    text1 = "John Doe needs to create the database index."
    actions1 = extract_action_items(text1)
    assert len(actions1) == 1
    assert actions1[0]["assignee"] == "John Doe"
    assert "database" in actions1[0]["text"]

    # Test imperative sentence starting with verb triggers action item
    text2 = "Submit the report before midnight."
    actions2 = extract_action_items(text2)
    assert len(actions2) == 1
    assert actions2[0]["assignee"] == "Unassigned"

    # Test Speaker / I will trigger
    text3 = "I will coordinate with the team tomorrow."
    actions3 = extract_action_items(text3)
    assert len(actions3) == 1
    assert actions3[0]["assignee"] == "Speaker"
