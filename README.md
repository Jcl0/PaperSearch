# PaperSearch

Collecting literature knowledge is crucial for developing LLM applications. PaperSearch provides a comprehensive literature search and PDF download tool supporting PubMed and arXiv databases. While automated PDF downloading is not available for all papers due to access restrictions, the tool offers PDF download options.

## Acknowledgments

**Developed with [Trae](https://trae.ai/)** - an AI-powered coding assistant that enhanced the development process.

This project was inspired by and draws concepts from:

- [google-deepmind/science-skills](https://github.com/google-deepmind/science-skills) - Scientific literature search and analysis skills
- [ferru97/PyPaperBot](https://github.com/ferru97/PyPaperBot/) - Academic paper download tool

## Features

- **Multi-database search**: Query PubMed, arXiv, and bioRxiv simultaneously
- **Advanced filtering**: Filter by year range, citation count, and sort results
- **PDF download**: Automatically download PDFs from:
  - **arXiv** - Direct download for preprints with arXiv ID
  - **SciHub** - Fallback download via DOI or title
- **Multiple export formats**: CSV, Markdown, JSON, and EndNote RIS
- **GUI interface**: User-friendly graphical interface for easy searching
- **Parallel downloads**: Efficient concurrent PDF downloads with configurable workers

## Installation

```bash
cd papersearch
pip install .
```

## Quick Start

### GUI Interface

```bash
python main.py
```

### CLI Usage

```bash
# Search PubMed for cancer research
papersearch search "BRCA1 cancer" -n 20

# Search arXiv for deep learning papers
papersearch search "deep learning" -d arxiv -n 10

# Search bioRxiv for preprints
papersearch search "mRNA vaccine" -d biorxiv -n 15

# Search across multiple databases simultaneously
papersearch search "AI in healthcare" -d pubmed,arxiv -n 20

# Search with year range filter
papersearch search "machine learning diagnosis" -n 15 --year-start 2020 --year-end 2025

# Search and download PDFs with verbose output
papersearch search "CRISPR gene editing" -n 10 --download-pdf --verbose

# Search with citation count filter
papersearch search "single cell RNA sequencing" -n 15 --min-citations 50

# Export results to CSV file
papersearch search "neural network medical imaging" -n 20 -o results.csv --format csv

# Export results to Markdown for documentation
papersearch search "transformer architecture" -d arxiv -n 10 -o papers.md --format markdown

```

## Configuration

Edit `config.ini` to customize:

```ini
[scihub]
mirrors = ["https://sci-hub.st/"]

[pdf_download]
max_workers = 10
timeout = 300
download_delay = 2
```

## PDF Download

PaperSearch supports PDF downloading from multiple sources:

| Source | Priority | Description |
|--------|----------|-------------|
| arXiv | 1st | Direct download for arXiv preprints |
| SciHub | 2nd | Fallback via DOI or paper title |

Downloads are processed in parallel using configurable worker threads, with optional delay between requests to avoid rate limiting.

## Export Formats

| Format | Description |
|--------|-------------|
| CSV | Full results with all metadata |
| Markdown | Formatted table view |
| JSON | Raw data export |
| EndNote RIS | Reference manager compatible |

## License

This project is for educational and research purposes only. Please ensure compliance with copyright laws when downloading academic papers.

## Related Projects

- [google-deepmind/science-skills](https://github.com/google-deepmind/science-skills) - Scientific literature analysis
- [ferru97/PyPaperBot](https://github.com/ferru97/PyPaperBot/) - Academic paper downloader
