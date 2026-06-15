"""PubMed API integration for PaperSearch."""

import asyncio
import json
import os
import urllib.parse
import xml.etree.ElementTree as ET

import aiohttp
import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov"
CROSSREF_URL = "https://api.crossref.org/works"


def _env_params(email: str = None, api_key: str = None) -> dict:
    """Returns a dictionary of parameters from the environment."""
    params = {}
    if email:
        params["email"] = email
    elif os.environ.get("NCBI_EMAIL"):
        params["email"] = os.environ.get("NCBI_EMAIL")
    
    if api_key:
        params["api_key"] = api_key
    elif os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ.get("NCBI_API_KEY")
    
    return params


async def _async_get_citation_count(session: aiohttp.ClientSession, doi: str) -> int:
    """Get citation count from CrossRef API asynchronously."""
    if not doi:
        return 0
    
    try:
        url = f"{CROSSREF_URL}/{urllib.parse.quote(doi)}"
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("message", {}).get("is-referenced-by-count", 0)
    except Exception:
        pass
    
    return 0


async def _async_fetch_citation_counts(results: list[dict]) -> None:
    """Fetch citation counts for all articles asynchronously."""
    if not results:
        return
    
    # Create a mapping of index to DOI
    doi_map = {i: result.get("doi") for i, result in enumerate(results) if result.get("doi")}
    
    if not doi_map:
        return
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for index, doi in doi_map.items():
            task = asyncio.ensure_future(_async_get_citation_count(session, doi))
            task.index = index
            tasks.append(task)
        
        # Run all tasks concurrently
        completed_tasks = await asyncio.gather(*tasks)
        
        # Update results with citation counts
        for task, count in zip(tasks, completed_tasks):
            results[task.index]["cited_by_count"] = count


def _fetch_citation_counts_parallel(results: list[dict]) -> None:
    """Fetch citation counts for all articles in parallel using asyncio."""
    if not results:
        return
    
    # Run async function synchronously
    asyncio.run(_async_fetch_citation_counts(results))


def search_pubmed(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    email: str = None,
    api_key: str = None,
    year: int = None,
    min_year: int = None,
    max_year: int = None,
    fetch_citations: bool = True,
) -> list[dict]:
    """Search PubMed for articles matching the query."""
    params = _env_params(email, api_key) | {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort_by,
        "retmode": "json",
    }
    
    # Handle year filtering
    if year:
        params["mindate"] = f"{year}/01/01"
        params["maxdate"] = f"{year}/12/31"
        params["datetype"] = "pdat"
    elif min_year or max_year:
        if min_year:
            params["mindate"] = f"{min_year}/01/01"
        if max_year:
            params["maxdate"] = f"{max_year}/12/31"
        params["datetype"] = "pdat"
    
    # Use POST request to avoid URL length limit (414 error)
    url = f"{EUTILS_BASE}/entrez/eutils/esearch.fcgi"
    response = requests.post(url, data=params)
    response.raise_for_status()
    
    data = response.json()
    pmids = data["esearchresult"]["idlist"]
    
    if not pmids:
        return []
    
    return fetch_articles(pmids, fetch_citations=fetch_citations)


def fetch_articles(pmids: list[str], fetch_citations: bool = True) -> list[dict]:
    """Fetch detailed article information for a list of PMIDs."""
    params = _env_params() | {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    
    # Use POST request to avoid URL length limit (414 error)
    url = f"{EUTILS_BASE}/entrez/eutils/efetch.fcgi"
    response = requests.post(url, data=params)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    results = []
    
    for article in root.iter("PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        if pmid_elem is None:
            continue
        
        art = article.find(".//Article")
        if art is None:
            continue
        
        authors = []
        for author in art.findall(".//AuthorList/Author"):
            last = author.findtext("LastName") or ""
            init = author.findtext("Initials") or ""
            name = f"{last} {init}".strip() if last else author.findtext("CollectiveName") or ""
            if name:
                authors.append(name)
        
        abstract_parts = []
        for at in art.findall(".//Abstract/AbstractText"):
            label = at.get("Label")
            text = "".join(at.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts) if abstract_parts else None
        
        doi = None
        for eid in art.findall("ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = eid.text
                break
        
        journal_elem = art.find(".//Journal")
        journal = journal_elem.findtext("Title") if journal_elem is not None else None
        
        year = None
        if journal_elem is not None:
            pd = journal_elem.find(".//PubDate")
            if pd is not None:
                year = pd.findtext("Year")
        
        results.append({
            "pmid": pmid_elem.text,
            "title": art.findtext("ArticleTitle"),
            "authors": authors,
            "journal": journal,
            "year": year,
            "doi": doi,
            "abstract": abstract,
            "cited_by_count": None,
        })
    
    # Fetch citation counts in parallel if requested
    if fetch_citations:
        _fetch_citation_counts_parallel(results)
    
    return results



