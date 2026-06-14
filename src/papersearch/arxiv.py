"""arXiv API integration for PaperSearch."""

import urllib.parse

import requests

BASE_URL = "http://export.arxiv.org/api/query"


def search_arxiv(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    year: int = None,
    min_year: int = None,
    max_year: int = None,
) -> list[dict]:
    """Search arXiv for preprints matching the query."""
    sort_param = {
        "relevance": "relevance",
        "pub_date": "submittedDate",
        "cited_by_count": "relevance"  # arXiv doesn't support citation sort
    }.get(sort_by, "relevance")
    
    # Build date filter
    date_filter = ""
    if year:
        date_filter = f"submittedDate:[{year}0101 TO {year}1231]"
    elif min_year or max_year:
        start_date = f"{min_year}0101" if min_year else "00010101"
        end_date = f"{max_year}1231" if max_year else "99991231"
        date_filter = f"submittedDate:[{start_date} TO {end_date}]"
    
    # Combine query with date filter
    full_query = query
    if date_filter:
        full_query = f"({query}) AND {date_filter}"
    
    # Limit query length to avoid 414 error (arXiv doesn't support POST)
    if len(full_query) > 500:
        full_query = full_query[:500]
    
    params = {
        "search_query": full_query,
        "max_results": max_results,
        "sortBy": sort_param,
        "sortOrder": "descending",
    }
    
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    response = requests.get(url)
    response.raise_for_status()
    
    return _parse_arxiv_response(response.content)


def fetch_papers(arxiv_ids: list[str]) -> list[dict]:
    """Fetch detailed information for specific arXiv IDs."""
    results = []
    
    for arxiv_id in arxiv_ids:
        # Format: http://arxiv.org/abs/1234.56789 or just 1234.56789
        if not arxiv_id.startswith("http"):
            arxiv_id = f"http://arxiv.org/abs/{arxiv_id}"
        
        params = {
            "id_list": arxiv_id.split("/")[-1],
        }
        
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        response = requests.get(url)
        response.raise_for_status()
        
        parsed = _parse_arxiv_response(response.content)
        if parsed:
            results.extend(parsed)
    
    return results


def _parse_arxiv_response(xml_content: bytes) -> list[dict]:
    """Parse arXiv XML response into standardized format."""
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(xml_content)
    
    results = []
    
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        arxiv_id = entry.findtext("{http://www.w3.org/2005/Atom}id")
        
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        title = title_elem.text if title_elem is not None else None
        
        summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
        summary = summary_elem.text if summary_elem is not None else None
        
        published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
        published = published_elem.text if published_elem is not None else None
        
        authors = []
        for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
            name_elem = author.find("{http://www.w3.org/2005/Atom}name")
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)
        
        # Extract DOI if available
        doi = None
        for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
            if link.get("title") == "doi":
                doi = link.get("href")
                if doi and doi.startswith("http://dx.doi.org/"):
                    doi = doi.replace("http://dx.doi.org/", "")
        
        results.append({
            "id": arxiv_id,
            "arxiv_id": arxiv_id.split("/")[-1] if arxiv_id else None,  # Extract pure arXiv ID
            "title": title.strip() if isinstance(title, str) else None,
            "authors": authors,
            "journal": "arXiv Preprint",
            "year": published[:4] if isinstance(published, str) else None,
            "doi": doi,
            "abstract": summary.strip() if isinstance(summary, str) else None,
            "cited_by_count": 0,
            "published": published,
        })
    
    return results
