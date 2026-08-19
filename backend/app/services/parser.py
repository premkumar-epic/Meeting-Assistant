from __future__ import annotations

import spacy
import threading
from typing import Any

# Global NLP cache
_NLP_LOCK = threading.Lock()
_NLP: spacy.Language | None = None


def _get_nlp() -> spacy.Language:
    """Load and cache the spaCy English model."""
    global _NLP
    with _NLP_LOCK:
        if _NLP is None:
            try:
                _NLP = spacy.load("en_core_web_sm")
            except OSError:
                # Fallback in case the model is not linked
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
                _NLP = spacy.load("en_core_web_sm")
    return _NLP


def extract_entities(text_or_doc: str | Any) -> list[dict[str, str]]:
    """
    Extract Named Entities (PERSON, ORG, DATE) from the transcript using spaCy.
    Returns a sorted list of unique entities.
    """
    if isinstance(text_or_doc, str):
        if not text_or_doc.strip():
            return []
        nlp = _get_nlp()
        doc = nlp(text_or_doc)
    else:
        doc = text_or_doc


    unique_entities: set[tuple[str, str]] = set()
    allowed_labels = {"PERSON", "ORG", "DATE"}

    for ent in doc.ents:
        label = ent.label_
        if label in allowed_labels:
            entity_text = ent.text.strip().replace("\n", " ")
            if len(entity_text) > 1:  # Filter out single-character garbage
                unique_entities.add((entity_text, label))

    # Convert to list of dicts and sort alphabetically by text
    entities_list = [
        {"text": val[0], "label": val[1]}
        for val in sorted(list(unique_entities), key=lambda x: x[0])
    ]
    return entities_list


def extract_action_items(text_or_doc: str | Any) -> list[dict[str, Any]]:
    """
    Extract action items from the text by matching action-oriented verbs,
    imperative sentence shapes, and keyword indicators.
    """
    if isinstance(text_or_doc, str):
        if not text_or_doc.strip():
            return []
        nlp = _get_nlp()
        doc = nlp(text_or_doc)
    else:
        doc = text_or_doc

    action_items: list[dict[str, Any]] = []
    
    # Common action-oriented helper phrases
    trigger_phrases = {
        "need to", "needs to", "have to", "has to", "should", "must", 
        "will do", "going to", "action item", "todo", "assign to", 
        "please", "tasked with", "responsible for", "i will", "we will",
        "you will", "i'll", "we'll", "you'll"
    }

    # Iterate over sentences in the document
    for sent in doc.sents:
        sent_text = sent.text.strip()
        sent_lower = sent_text.lower()
        
        is_action = False
        assignee = "Unassigned"
        
        # Rule 1: Trigger phrase check
        if any(phrase in sent_lower for phrase in trigger_phrases):
            is_action = True
            
        # Rule 2: Imperative or action-oriented verb structure
        # Check if the sentence starts with a verb, or has a verb in dependency relation
        if not is_action and len(sent) > 0:
            first_token = sent[0]
            # Check if starts with a verb (imperative)
            if first_token.pos_ == "VERB" and first_token.dep_ == "ROOT":
                is_action = True

        # Rule 3: Search for target assignee within the sentence
        if is_action:
            # If "I will do...", the assignee might be "I" / speaker.
            # Look for PERSON entity in this sentence
            sentence_entities = [ent for ent in sent.ents if ent.label_ == "PERSON"]
            if sentence_entities:
                assignee = sentence_entities[0].text.strip()
            elif "i will" in sent_lower or "i'll" in sent_lower:
                assignee = "Speaker"
            elif "we need to" in sent_lower or "we should" in sent_lower:
                assignee = "Team"
            elif "you need to" in sent_lower or "please" in sent_lower:
                # If "you need to" or "please do...", assignee could be "Assignee"
                assignee = "Assignee"

            # Parse action text to clean up prefixes
            action_items.append({
                "id": len(action_items),
                "text": sent_text,
                "assignee": assignee,
            })

    return action_items

def parse_transcript(text: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Parse transcript once and extract both entities and action items to save time."""
    if not text.strip():
        return [], []
    nlp = _get_nlp()
    doc = nlp(text)
    return extract_entities(doc), extract_action_items(doc)
