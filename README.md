# PRAG-visualization
Automated PDF parsing and GPT-based knowledge graph construction for visualizing photosynthesis research texts.
The workflow is broken down into the following steps:

1. **Research Paper Evaluation**  
   - Automatic PDF text extraction and scoring of scientific depth and domain coverage using OpenAI’s API.  
2. **Entity & Relationship Extraction**  
   - Automated parsing of PDFs to identify entities and relationships (via GPT-based NLP techniques) and classify them according to spatial and temporal scales.  
3. **Knowledge Graph Visualization**  
   - Interactive web application (using Dash & Cytoscape) to visualize nodes and edges derived from the extracted entities and relationships.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [1. Research Paper Evaluation ([paper_evaluation.py](./paper_evaluation.py))]
  - [2. Entity & Relationship Extraction ([entity_extraction.py](./entity_extraction.py))]
  - [3. Knowledge Graph Visualization ([KG_visualization.py](./KG_visualization.py))]

---

## Features
- **Automated PDF Parsing**: Uses libraries like **PyPDF2** or **PyMuPDF** (`fitz`) to extract text from research papers.
- **OpenAI GPT Integration**: Leverages OpenAI’s ChatCompletion API to evaluate research papers (scientific depth/domain coverage) and to extract entities and relationships.
- **Spatial/Temporal Classification**: Categorizes extracted entities according to user-defined spatial and temporal scales.
- **Interactive Graph**: A Dash web app that visualizes nodes and edges, allowing for on-the-fly styling and PNG export.

---

## Installation
Make sure you have [Python 3.7+](https://www.python.org/) installed. Then install the required libraries:

```bash
pip install openai PyPDF2 PyMuPDF dash dash-cytoscape dash-daq
