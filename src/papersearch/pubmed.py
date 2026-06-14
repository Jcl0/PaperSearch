"""PubMed API integration for PaperSearch."""

import json
import os
import urllib.parse
import xml.etree.ElementTree as ET

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov"


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


def search_pubmed(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    email: str = None,
    api_key: str = None,
    year: int = None,
    min_year: int = None,
    max_year: int = None,
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
    
    return fetch_articles(pmids)


def fetch_articles(pmids: list[str]) -> list[dict]:
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
            "cited_by_count": 0,
        })
    
    return results
