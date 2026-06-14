#!/usr/bin/env python3
"""
PDF Downloader module for PaperSearch.

This module provides functionality to download PDF files from multiple sources:
- arXiv (preprints)
- SciHub (fallback)
"""

import os
import re
import ast
import time
import hashlib
import requests
import threading
import configparser
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import journal abbreviation function from utils
from .utils import get_journal_abbreviation, sanitize_filename, get_unique_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_download_errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'scihub_mirrors': [
        "https://sci-hub.se/",
        "https://sci-hub.ru/",
        "https://sci-hub.st/",
        "https://sci-hub.mksa.top/",
    ],
    'max_workers': 5,
    'timeout': 30,
    'proxy': None,
    'log_file': 'pdf_download_errors.log',
    'download_delay': 2  # Delay in seconds between downloads
}

# Headers to mimic browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# Error categories
ERROR_CATEGORIES = {
    'NO_IDENTIFIER': 'No DOI, PMID, arXiv ID, or title provided',
    'ARXIV_ERROR': 'arXiv download error',
    'IEEE_ERROR': 'IEEE Xplore download error',
    'ELSEVIER_ERROR': 'ScienceDirect/Elsevier download error',
    'SPRINGER_ERROR': 'Springer download error',
    'WILEY_ERROR': 'Wiley download error',
    'ACM_ERROR': 'ACM Digital Library download error',
    'SCIHUB_CAPTCHA': 'SciHub blocked by captcha',
    'SCIHUB_NO_PDF_URL': 'No PDF URL found in response',
    'SCIHUB_HTTP_ERROR': 'SciHub HTTP error',
    'SCIHUB_TIMEOUT': 'SciHub connection timeout',
    'SCIHUB_CONNECTION_ERROR': 'SciHub connection error',
    'SCIHUB_NO_MIRRORS': 'No available SciHub mirrors',
    'ALL_MIRRORS_FAILED': 'All SciHub mirrors failed',
    'NO_DOI_ARXIV': 'Neither DOI nor arXiv ID available',
    'DIRECT_PDF_ERROR': 'Direct PDF download error',
}


def log_download_failure(paper_info: Dict, error_type: str, error_details: str = ""):
    """
    Log download failure with detailed information.
    
    Args:
        paper_info: Dictionary containing paper details (title, authors, doi, pmid, journal, year)
        error_type: Error category from ERROR_CATEGORIES
        error_details: Additional details about the error
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_entry = {
        'timestamp': timestamp,
        'error_type': error_type,
        'error_message': ERROR_CATEGORIES.get(error_type, error_type),
        'error_details': error_details,
        'title': paper_info.get('title', 'N/A')[:200],
        'authors': paper_info.get('authors', 'N/A')[:100],
        'journal': paper_info.get('journal', 'N/A')[:100],
        'year': paper_info.get('year', 'N/A'),
        'doi': paper_info.get('doi', 'N/A'),
        'arxiv_id': paper_info.get('arxiv_id', 'N/A'),
    }
    
    # Format log message
    log_message = (
        f"[DOWNLOAD FAILURE] {timestamp}\n"
        f"  Title: {log_entry['title']}\n"
        f"  Authors: {log_entry['authors']}\n"
        f"  Journal: {log_entry['journal']}\n"
        f"  Year: {log_entry['year']}\n"
        f"  DOI: {log_entry['doi']}\n"
        f"  arXiv ID: {log_entry['arxiv_id']}\n"
        f"  Error Type: {log_entry['error_type']}\n"
        f"  Error Message: {log_entry['error_message']}\n"
        f"  Error Details: {log_entry['error_details']}\n"
        "----------------------------------------"
    )
    
    logger.error(log_message)
    
    return log_entry


def load_config(config_path: str = None) -> dict:
    """Load configuration from config.ini file.
    
    If config_path is not provided, will search for config.ini in:
    1. Current working directory
    2. The directory containing this module
    """
    config = DEFAULT_CONFIG.copy()
    
    # Determine config path
    if config_path is None:
        # First try current working directory
        if os.path.exists("config.ini"):
            config_path = "config.ini"
        else:
            # Try the papersearch directory (two levels up from this module)
            module_dir = os.path.dirname(os.path.abspath(__file__))  # papersearch/src/papersearch/
            src_dir = os.path.dirname(module_dir)  # papersearch/src/
            papersearch_dir = os.path.dirname(src_dir)  # papersearch/
            config_path = os.path.join(papersearch_dir, "config.ini")
    
    print(f"[Config] Looking for config at: {config_path}")
    
    if os.path.exists(config_path):
        try:
            # Read raw file content first to handle Python-style list format
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # Try to parse with configparser, but handle Python list format separately
            # First, extract mirrors section manually
            mirrors_match = re.search(r'mirrors\s*=\s*(\[.*?\])', raw_content, re.DOTALL)
            if mirrors_match:
                mirrors_str = mirrors_match.group(1).strip()
                try:
                    mirrors = ast.literal_eval(mirrors_str)
                    if isinstance(mirrors, list):
                        config['scihub_mirrors'] = mirrors
                        print(f"[Config] Loaded {len(mirrors)} SciHub mirrors from config")
                        for m in mirrors:
                            print(f"[Config]   - {m}")
                except (ValueError, SyntaxError) as e:
                    print(f"[Config] Failed to parse mirrors list: {e}")
            
            # Now parse rest of config with configparser
            # Remove the mirrors line to avoid parsing errors
            clean_content = re.sub(r'mirrors\s*=\s*\[.*?\]', 'mirrors = ""', raw_content, flags=re.DOTALL)
            
            parser = configparser.ConfigParser()
            parser.read_string(clean_content)
            
            # Load proxy setting
            if 'scihub' in parser and 'proxy' in parser['scihub']:
                proxy = parser['scihub']['proxy'].strip()
                if proxy:
                    config['proxy'] = proxy
                else:
                    config['proxy'] = None
            
            if 'pdf_download' in parser:
                if 'max_workers' in parser['pdf_download']:
                    config['max_workers'] = int(parser['pdf_download']['max_workers'])
                if 'timeout' in parser['pdf_download']:
                    config['timeout'] = int(parser['pdf_download']['timeout'])
                if 'download_delay' in parser['pdf_download']:
                    config['download_delay'] = int(parser['pdf_download']['download_delay'])
        
        except Exception as e:
            print(f"[PDF Download] Error reading config: {e}, using defaults")
    else:
        print(f"[Config] Config file not found at {config_path}, using defaults")
    
    return config


def _get_soup(content: bytes):
    """Parse HTML content with BeautifulSoup."""
    return BeautifulSoup(content, 'html.parser')


def _extract_pdf_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract PDF URL from parsed HTML.
    
    Looks for PDF URL in:
    1. iframe src attribute
    2. embed src attribute
    3. object data attribute
    4. JavaScript location.href
    5. Data URL in any element
    """
    # Try iframe
    iframe = soup.find('iframe')
    if iframe and iframe.get('src'):
        src = iframe.get('src')
        if not src.startswith('http'):
            src = urljoin(base_url, src)
        return src
    
    # Try embed
    embed = soup.find('embed')
    if embed and embed.get('src'):
        src = embed.get('src')
        if not src.startswith('http'):
            src = urljoin(base_url, src)
        return src
    
    # Try object
    obj = soup.find('object')
    if obj and obj.get('data'):
        data = obj.get('data')
        if not data.startswith('http'):
            data = urljoin(base_url, data)
        return data
    
    # Try JavaScript location.href patterns
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Match various patterns like:
            # location.href = "url"
            # top.location = "url"
            # window.location = "url"
            patterns = [
                r'location\.href\s*=\s*["\']([^"\']+)["\']',
                r'top\.location\s*=\s*["\']([^"\']+)["\']',
                r'window\.location\s*=\s*["\']([^"\']+)["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, script.string)
                if match:
                    url = match.group(1)
                    if url.startswith('http') or url.startswith('//'):
                        if url.startswith('//'):
                            url = 'https:' + url
                        return url
                    return urljoin(base_url, url)
    
    # Try to find any element with PDF-like URL
    for tag in soup.find_all(['a', 'area']):
        href = tag.get('href', '')
        if '.pdf' in href.lower() or 'download' in href.lower():
            if not href.startswith('http'):
                href = urljoin(base_url, href)
            return href
    
    return None


def _generate_name_hash(url: str) -> str:
    """Generate a unique name from URL hash."""
    return hashlib.md5(url.encode()).hexdigest()[:16]


# ============== Download Sources ==============

def download_from_arxiv(arxiv_id: str, timeout: int = 30, proxies: dict = None,
                       paper_info: Dict = None) -> tuple:
    """Download PDF from arXiv using arXiv ID.
    
    Args:
        arxiv_id: arXiv ID (e.g., "2301.12345" or full URL)
        timeout: Request timeout in seconds
        proxies: Proxy dictionary
        paper_info: Paper info for logging
    
    Returns:
        Tuple of (PDF content as bytes, download URL), or (None, None) if failed
    """
    try:
        # Clean arXiv ID
        if arxiv_id.startswith("http"):
            arxiv_id = arxiv_id.split("/")[-1]
        
        # Try PDF link first (most reliable)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        print(f"[PDF Download] Trying arXiv PDF: {pdf_url}")
        
        response = requests.get(pdf_url, timeout=timeout, proxies=proxies, headers=HEADERS)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "")
        if "pdf" in content_type.lower() or len(response.content) > 10000:
            print(f"[PDF Download] arXiv download success: {arxiv_id}")
            return (response.content, pdf_url)
        
        # If PDF link doesn't work, try the abstract page
        abstract_url = f"https://arxiv.org/abs/{arxiv_id}"
        response = requests.get(abstract_url, timeout=timeout, proxies=proxies, headers=HEADERS)
        response.raise_for_status()
        
        soup = _get_soup(response.content)
        
        # Find PDF link on abstract page
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/pdf/' in href:
                pdf_url = href if href.startswith('http') else f"https://arxiv.org{href}"
                pdf_response = requests.get(pdf_url, timeout=timeout, proxies=proxies, headers=HEADERS)
                pdf_response.raise_for_status()
                print(f"[PDF Download] arXiv download success (via abstract): {arxiv_id}")
                return (pdf_response.content, pdf_url)
        
        print(f"[PDF Download] arXiv: No PDF link found for {arxiv_id}")
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error {e.response.status_code}"
        print(f"[PDF Download] arXiv download failed: {error_msg}")
    except requests.exceptions.Timeout:
        error_msg = "Connection timeout"
        print(f"[PDF Download] arXiv download failed: {error_msg}")
    except requests.exceptions.ConnectionError:
        error_msg = "Connection error"
        print(f"[PDF Download] arXiv download failed: {error_msg}")
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"[PDF Download] arXiv download failed: {error_msg}")
    
    if paper_info:
        log_download_failure(paper_info, 'ARXIV_ERROR', error_msg if 'error_msg' in dir() else 'Unknown error')
    
    return (None, None)


def download_from_scihub(doi: str = None, pmid: str = None, title: str = None, 
                         scihub_mirrors: list = None, timeout: int = 30, 
                         proxies: dict = None, paper_info: Dict = None) -> tuple:
    """Download PDF from SciHub using DOI, PMID, or title.
    
    Tries all mirrors in order until one succeeds.
    Uses BeautifulSoup to parse HTML and extract PDF URL.
    """
    if scihub_mirrors is None:
        scihub_mirrors = DEFAULT_CONFIG['scihub_mirrors']
    
    if not scihub_mirrors:
        if paper_info:
            log_download_failure(paper_info, 'SCIHUB_NO_MIRRORS', "No SciHub mirrors configured")
        print("[PDF Download] No SciHub mirrors available")
        return (None, None)
    
    query = None
    
    # Use DOI directly (URL + DOI format is more reliable)
    if doi:
        query = doi  # Direct DOI, e.g., "10.1038/xxx"
    elif pmid:
        query = f"pmid:{pmid}"
    elif title:
        query = quote(title)
    
    if not query:
        if paper_info:
            log_download_failure(paper_info, 'NO_IDENTIFIER', "No DOI, PMID, or title provided")
        return (None, None)
    
    # Track mirror failures for detailed logging
    mirror_failures = []
    
    # Try all mirrors in order
    total_mirrors = len(scihub_mirrors)
    for i, scihub_url in enumerate(scihub_mirrors, 1):
        try:
            # Remove trailing slash and build URL
            base_url = scihub_url.rstrip('/')
            url = f"{base_url}/{query}"
            print(f"[PDF Download] Trying SciHub mirror {i}/{total_mirrors}: {scihub_url}")
            
            response = requests.get(url, timeout=timeout, proxies=proxies, headers=HEADERS)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            
            # Direct PDF response
            if content_type == "application/pdf":
                print(f"[PDF Download] SciHub success (direct PDF) from mirror {i}/{total_mirrors}")
                return (response.content, url)
            
            # Parse HTML to find PDF URL
            soup = _get_soup(response.content)
            
            # Check if blocked by captcha
            page_text = soup.get_text().lower()
            if any(keyword in page_text for keyword in ['captcha', 'verify you are human', 'blocked', 'access denied']):
                mirror_failures.append(f"Mirror {scihub_url}: blocked by captcha")
                print(f"[PDF Download] Mirror {i}/{total_mirrors} blocked by captcha")
                continue
            
            # Try to extract PDF URL from various elements
            pdf_url = _extract_pdf_url(soup, base_url)
            
            if pdf_url:
                print(f"[PDF Download] Found PDF URL: {pdf_url[:80]}...")
                
                # Make request to PDF URL
                headers = HEADERS.copy()
                headers['Referer'] = url
                
                pdf_response = requests.get(pdf_url, timeout=timeout, proxies=proxies, headers=headers)
                pdf_response.raise_for_status()
                
                if pdf_response.headers.get("Content-Type") == "application/pdf":
                    print(f"[PDF Download] SciHub success from mirror {i}/{total_mirrors}")
                    return (pdf_response.content, pdf_url)
                else:
                    mirror_failures.append(f"Mirror {scihub_url}: PDF URL returned non-PDF content")
                    print(f"[PDF Download] Mirror {i}/{total_mirrors}: PDF URL returned non-PDF content")
            else:
                mirror_failures.append(f"Mirror {scihub_url}: no PDF URL found in response")
                print(f"[PDF Download] Mirror {i}/{total_mirrors}: no PDF URL found")
            
            # If no PDF found but response is HTML, maybe it's a redirect or data URL
            if 'application/pdf' not in content_type:
                # Try to find PDF in data URL
                data_url_pattern = re.compile(r'data:application/pdf;[^"\']+["\']')
                match = data_url_pattern.search(response.text)
                if match:
                    import base64
                    data_url = match.group(0)
                    # Extract base64 data
                    b64_data = re.search(r'base64,([^"\']+)', data_url)
                    if b64_data:
                        pdf_data = base64.b64decode(b64_data.group(1))
                        print(f"[PDF Download] SciHub success (data URL) from mirror {i}/{total_mirrors}")
                        return (pdf_data, url)
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            mirror_failures.append(f"Mirror {scihub_url}: {error_msg}")
            print(f"[PDF Download] Mirror {i}/{total_mirrors} ({scihub_url}) failed: {error_msg}")
        except requests.exceptions.Timeout:
            error_msg = "Connection timeout"
            mirror_failures.append(f"Mirror {scihub_url}: {error_msg}")
            print(f"[PDF Download] Mirror {i}/{total_mirrors} ({scihub_url}) failed: {error_msg}")
        except requests.exceptions.ConnectionError:
            error_msg = "Connection refused"
            mirror_failures.append(f"Mirror {scihub_url}: {error_msg}")
            print(f"[PDF Download] Mirror {i}/{total_mirrors} ({scihub_url}) failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)[:100]
            mirror_failures.append(f"Mirror {scihub_url}: {error_msg}")
            print(f"[PDF Download] Mirror {i}/{total_mirrors} ({scihub_url}) failed: {error_msg}")
    
    # All mirrors failed - log the detailed failure
    error_details = "\n".join(mirror_failures)
    print(f"[PDF Download] All {total_mirrors} SciHub mirrors failed for query: {query[:50]}")
    
    if paper_info:
        # Determine the primary failure type
        if any('captcha' in f.lower() for f in mirror_failures):
            error_type = 'SCIHUB_CAPTCHA'
        elif any('timeout' in f.lower() for f in mirror_failures):
            error_type = 'SCIHUB_TIMEOUT'
        elif any('connection' in f.lower() for f in mirror_failures):
            error_type = 'SCIHUB_CONNECTION_ERROR'
        elif any('no PDF URL' in f for f in mirror_failures):
            error_type = 'SCIHUB_NO_PDF_URL'
        else:
            error_type = 'ALL_MIRRORS_FAILED'
        
        log_download_failure(paper_info, error_type, error_details)
    
    return (None, None)


def download_pdf(paper: Dict, pdf_dir: str, scihub_mirrors: list = None, 
                 timeout: int = 30, proxy: str = None) -> Tuple[str, bool, str]:
    """
    Download PDF for a single paper using multiple sources.
    
    Download order:
    1. arXiv (if arXiv ID available)
    2. SciHub (fallback)
    
    Args:
        paper: Paper dictionary with title, authors, journal, year, doi, pmid, arxiv_id
        pdf_dir: Directory to save PDF files
        scihub_mirrors: List of SciHub mirror URLs
        timeout: Request timeout in seconds
        proxy: Proxy URL (e.g., "http://127.0.0.1:7890")
    
    Returns:
        Tuple of (filename, success, download_method)
    """
    # Setup proxies
    proxies = None
    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy
        }
    
    # Create paper info for logging
    paper_info = {
        'title': paper.get('title', ""),
        'authors': ", ".join(paper.get('authors', [])),
        'journal': paper.get('journal', ""),
        'year': paper.get('year', ""),
        'doi': paper.get('doi', ""),
        'arxiv_id': paper.get('arxiv_id', "")
    }
    
    # Get first author full name (not abbreviated)
    authors = paper.get('authors', [])
    first_author = authors[0] if authors else "Unknown"
    
    # Clean author name: remove commas, replace spaces with underscores
    author_name = first_author.replace(",", "").replace(" ", "_")
    author_name = sanitize_filename(author_name)
    
    journal = paper.get('journal', "")
    journal_abbr = get_journal_abbreviation(journal)
    year = paper.get('year', "")
    
    # Format: Author_Year_JournalAbbreviation
    base_name = f"{author_name}_{year}_{journal_abbr}"
    filename = get_unique_filename(pdf_dir, base_name, "pdf")
    
    doi = paper.get('doi', "")
    arxiv_id = paper.get('arxiv_id', "")
    title = paper.get('title', "")
    
    print(f"[PDF Download] Trying to download: {title[:50]}...")
    
    pdf_content = None
    download_method = None
    
    # 1. Try arXiv first (if available)
    if arxiv_id:
        print(f"[PDF Download] Trying arXiv (ID: {arxiv_id})...")
        pdf_content, _ = download_from_arxiv(arxiv_id, timeout=timeout, proxies=proxies,
                                         paper_info=paper_info)
        if pdf_content:
            download_method = "arXiv"

    # 2. Try SciHub as fallback
    if not pdf_content:
        if doi:
            print(f"[PDF Download] Trying SciHub (DOI: {doi})...")
            pdf_content, _ = download_from_scihub(doi=doi, scihub_mirrors=scihub_mirrors,
                                              timeout=timeout, proxies=proxies,
                                              paper_info=paper_info)
            if pdf_content:
                download_method = "SciHub"
        else:
            print(f"[PDF Download] No DOI or arXiv ID available, trying SciHub with title...")
            pdf_content, _ = download_from_scihub(title=title, scihub_mirrors=scihub_mirrors,
                                              timeout=timeout, proxies=proxies,
                                              paper_info=paper_info)
            if pdf_content:
                download_method = "SciHub"

    # Save PDF if downloaded successfully
    if pdf_content:
        with open(filename, "wb") as f:
            f.write(pdf_content)
        print(f"[PDF Download] Successfully downloaded ({download_method}): {os.path.basename(filename)}")
        return (os.path.basename(filename), True, download_method)
    
    # Failed to download
    print(f"[PDF Download] Failed to download: {title[:50]}...")
    
    if not doi and not arxiv_id:
        log_download_failure(paper_info, 'NO_DOI_ARXIV', "Neither DOI nor arXiv ID available")
    
    return (os.path.basename(filename), False, "Failed")


def download_pdfs_parallel(papers: List[Dict], pdf_dir: str, max_workers: int = 5, 
                           scihub_mirrors: list = None, timeout: int = 30, 
                           proxy: str = None, config_path: str = "config.ini") -> List[Dict]:
    """
    Download PDFs in parallel using multiple threads.
    
    Args:
        papers: List of paper dictionaries
        pdf_dir: Directory to save PDF files
        max_workers: Maximum number of parallel downloads
        scihub_mirrors: List of SciHub mirror URLs (if None, loads from config)
        timeout: Request timeout in seconds
        proxy: Proxy URL (e.g., "http://127.0.0.1:7890")
        config_path: Path to config file
    
    Returns:
        List of download records with filename, success status, and message
    """
    # Load config if scihub_mirrors not provided
    if scihub_mirrors is None:
        config = load_config(config_path)
        scihub_mirrors = config.get('scihub_mirrors', DEFAULT_CONFIG['scihub_mirrors'])
        proxy = proxy or config.get('proxy')
        max_workers = config.get('max_workers', max_workers)
    
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Separate papers into groups for parallel processing
    papers_with_identifiers = []
    papers_without_identifiers = []
    
    for paper in papers:
        if paper.get('doi') or paper.get('arxiv_id'):
            papers_with_identifiers.append(paper)
        else:
            papers_without_identifiers.append(paper)
    
    results = []
    
    # Handle papers without identifiers first
    for paper in papers_without_identifiers:
        paper_info = {
            'title': paper.get('title', ""),
            'authors': ", ".join(paper.get('authors', [])),
            'journal': paper.get('journal', ""),
            'year': paper.get('year', ""),
            'doi': paper.get('doi', ""),
            'arxiv_id': paper.get('arxiv_id', ""),
            'pmid': paper.get('pmid', "")
        }
        log_download_failure(paper_info, 'NO_DOI_ARXIV', "Neither DOI nor arXiv ID available")
        results.append({
            'title': paper.get('title', ""),
            'authors': ", ".join(paper.get('authors', [])),
            'journal': paper.get('journal', ""),
            'year': paper.get('year', ""),
            'doi': paper.get('doi', ""),
            'arxiv_id': paper.get('arxiv_id', ""),
            'pmid': paper.get('pmid', ""),
            'pdf_filename': "Download Failed",
            'download_success': False,
            'download_method': 'Failed'
        })
    
    # Download papers with identifiers in parallel
    if papers_with_identifiers:
        total_papers = len(papers_with_identifiers)
        print(f"[PDF Download] Starting parallel downloads for {total_papers} papers using {max_workers} workers...")
        
        def download_paper_wrapper(paper):
            filename, success, message = download_pdf(paper, pdf_dir, scihub_mirrors, 
                                                      timeout, proxy)
            # Show "Download Failed" instead of empty string if download failed
            display_filename = filename if success else "Download Failed"
            return {
                'title': paper.get('title', ""),
                'authors': ", ".join(paper.get('authors', [])),
                'journal': paper.get('journal', ""),
                'year': paper.get('year', ""),
                'doi': paper.get('doi', ""),
                'arxiv_id': paper.get('arxiv_id', ""),
                'pmid': paper.get('pmid', ""),
                'pdf_filename': display_filename,
                'download_success': success,
                'download_method': message
            }
        
        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            futures = [executor.submit(download_paper_wrapper, paper) 
                       for paper in papers_with_identifiers]
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(futures):
                completed += 1
                print(f"[PDF Download] Progress: {completed}/{total_papers}")
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"[PDF Download] Error in parallel download: {e}")
    
    # Maintain original order
    final_results = []
    paper_dict = {f"{p.get('title', '')}_{p.get('doi', '')}_{p.get('arxiv_id', '')}": p 
                  for p in results}
    
    for paper in papers:
        key = f"{paper.get('title', '')}_{paper.get('doi', '')}_{paper.get('arxiv_id', '')}"
        if key in paper_dict:
            final_results.append(paper_dict[key])
    
    return final_results
