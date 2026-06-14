"""bioRxiv API integration for PaperSearch."""

import urllib.parse
import re

import requests

BASE_URL = "https://api.biorxiv.org/details/biorxiv/0/0"


def search_biorxiv(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    year: int = None,
    min_year: int = None,
    max_year: int = None,
) -> list[dict]:
    """Search bioRxiv for preprints matching the query.
    
    Note: bioRxiv API does not support server-side search filtering,
    so we fetch results and filter them client-side. We also page
    through results to find matching papers.
    """
    # Build date range - default to recent years since older papers are less relevant
    if year:
        date_from = f"{year}-01-01"
        date_to = f"{year}-12-31"
    elif min_year or max_year:
        date_from = f"{min_year}-01-01" if min_year else "2020-01-01"
        date_to = f"{max_year}-12-31" if max_year else "3000-12-31"
    else:
        # Default to last 5 years for better relevance
        from datetime import datetime
        current_year = datetime.now().year
        date_from = f"{current_year - 5}-01-01"
        date_to = f"{current_year}-12-31"
    
    base_url = f"https://api.biorxiv.org/details/biorxiv/{date_from}/{date_to}"
    page_size = 30
    max_pages = 10  # Limit to 10 pages (300 results) to avoid long waits
    cursor = 0
    
    all_results = []
    filtered_results = []
    
    # Parse keywords for filtering
    keywords = [kw.lower().strip() for kw in query.split(",") if kw.strip()] if query else []
    
    for page in range(max_pages):
        if len(filtered_results) >= max_results:
            break
            
        url = f"{base_url}/{cursor}/{page_size}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            parsed = _parse_biorxiv_response(data)
            all_results.extend(parsed)
            
            # Filter by keywords if provided
            if keywords:
                for result in parsed:
                    text = f"{result.get('title', '')} {result.get('abstract', '')}".lower()
                    if any(kw in text for kw in keywords):
                        filtered_results.append(result)
            
            # Move to next page
            cursor += page_size
            
            # Check if there are more results
            if len(parsed) < page_size:
                break
                
        except Exception as e:
            print(f"Error fetching bioRxiv page {page}: {e}")
            break
    
    # If no keywords or no matches found, return all results
    if not keywords or len(filtered_results) == 0:
        final_results = all_results
    else:
        final_results = filtered_results
    
    # Apply sorting
    if sort_by == "pub_date":
        final_results.sort(key=lambda x: x.get("year", 0), reverse=True)
    elif sort_by == "cited_by_count":
        final_results.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
    
    return final_results[:max_results]


def fetch_papers(biorxiv_ids: list[str]) -> list[dict]:
    """Fetch detailed information for specific bioRxiv preprint IDs."""
    results = []
    
    for paper_id in biorxiv_ids:
        # Format: biorxiv.2023.01.01.522222 or just the number part
        if paper_id.startswith("biorxiv."):
            paper_id = paper_id.replace("biorxiv.", "")
        
        params = {
            "id": paper_id,
        }
        
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        parsed = _parse_biorxiv_response(data)
        if parsed:
            results.extend(parsed)
    
    return results


def _parse_biorxiv_response(data: dict) -> list[dict]:
    """Parse bioRxiv JSON response into standardized format."""
    results = []
    
    for item in data.get("collection", []):
        results.append({
            "id": item.get("preprint_doi"),
            "title": item.get("title"),
            "authors": [a.strip() for a in item.get("authors", "").split(";") if a.strip()],
            "journal": f"bioRxiv Preprint",
            "year": item.get("date").split("-")[0] if item.get("date") else None,
            "doi": item.get("preprint_doi"),
            "abstract": item.get("abstract"),
            "cited_by_count": int(item.get("cited_by", 0)),
            "published": item.get("date"),
        })
    
    return results
