"""Çoxmənbəli məqalə yığımı.

Hər mənbə modulu eyni interfeysi verir:
    fetch(field_key: str, since: date, limit: int) -> list[dict]
və nəticələr `schemas.PaperIn` formatına uyğun lüğətlərdir.
"""

from . import arxiv, crossref, doaj, openalex

# Sahə açarı -> həmin sahəni təsvir edən axtarış terminləri.
# arXiv kateqoriya kodları ilə işlədiyi üçün bu siyahını istifadə etmir.
FIELD_TERMS: dict[str, list[str]] = {
    # texnologiya
    "ai": ["machine learning", "neural network", "large language model", "deep learning"],
    "cv": ["computer vision", "image segmentation", "object detection"],
    "security": ["intrusion detection", "malware", "cryptography", "cybersecurity"],
    "robotics": ["robotics", "motion planning", "autonomous navigation"],
    "software": ["software engineering", "program analysis", "software testing"],
    "data": ["database systems", "information retrieval", "data management"],
    "networks": ["computer networks", "wireless networks", "network protocol"],
    "hci": ["human computer interaction", "user interface", "usability study"],

    # təbiət elmləri
    "physics": ["quantum mechanics", "condensed matter", "particle physics", "thermodynamics"],
    "astronomy": ["astrophysics", "exoplanet", "galaxy formation", "cosmology"],
    "chemistry": ["organic synthesis", "catalysis", "molecular structure", "chemical reaction"],
    "biology": ["molecular biology", "gene expression", "protein structure", "cell signaling"],
    "earth": ["climate change", "atmospheric science", "geophysics", "ocean circulation"],

    # formal elmlər
    "math": ["numerical analysis", "optimization theory", "probability theory", "graph theory"],
    "statistics": ["statistical inference", "bayesian analysis", "regression model", "experimental design"],

    # tibb və sağlamlıq
    "medicine": ["clinical trial", "patient outcomes", "diagnosis and treatment", "public health"],
    "neuroscience": ["neural circuits", "brain imaging", "cognitive neuroscience", "neurodegeneration"],

    # sosial elmlər
    "economics": ["economic growth", "monetary policy", "market equilibrium", "financial risk"],
    "psychology": ["cognitive psychology", "behavioral study", "mental health", "social behavior"],
}

SOURCES = {
    "arxiv": arxiv,
    "crossref": crossref,
    "doaj": doaj,
    "openalex": openalex,     # rusdilli məqalələr üçün əsas mənbə
}

__all__ = ["SOURCES", "FIELD_TERMS", "arxiv", "crossref", "doaj", "openalex"]
