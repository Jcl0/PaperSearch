#!/usr/bin/env python3
"""
PaperSearch CLI - A comprehensive literature search tool

This tool allows searching PubMed and other academic databases,
filtering by citation count, and exporting results to tabular formats.
"""

import argparse
import json
import os
import sys
import importlib.util
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    from python_dotenv import load_dotenv

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from papersearch import pubmed, arxiv, biorxiv, utils, pdf_downloader


def main():
    load_dotenv(os.path.expanduser("~/.env"))
    
    parser = argparse.ArgumentParser(
        prog="papersearch",
        description="Search academic literature across multiple databases",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search for literature",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    search_parser.add_argument(
        "query",
        type=str,
        help="Search query string"
    )
    search_parser.add_argument(
        "--database",
        "-d",
        type=str,
        choices=["pubmed", "arxiv", "biorxiv"],
        default="pubmed",
        help="Database to search"
    )
    search_parser.add_argument(
        "--max-results",
        "-n",
        type=int,
        default=10,
        help="Maximum number of results to retrieve"
    )
    search_parser.add_argument(
        "--sort-by",
        "-s",
        type=str,
        choices=["relevance", "pub_date", "cited_by_count"],
        default="relevance",
        help="Sort order for results"
    )
    search_parser.add_argument(
        "--min-citations",
        "-c",
        type=int,
        default=0,
        help="Minimum number of citations required"
    )
    search_parser.add_argument(
        "--year",
        "-y",
        type=int,
        help="Filter results by a specific year"
    )
    search_parser.add_argument(
        "--min-year",
        type=int,
        help="Filter results by minimum year (inclusive)"
    )
    search_parser.add_argument(
        "--max-year",
        type=int,
        help="Filter results by maximum year (inclusive)"
    )
    search_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (supports .csv, .xlsx, .json)"
    )
    search_parser.add_argument(
        "--endnote",
        "-e",
        action="store_true",
        help="Export results as EndNote reference files (.ris)"
    )
    search_parser.add_argument(
        "--email",
        type=str,
        default=os.environ.get("NCBI_EMAIL"),
        help="Email address for NCBI API (required for higher rate limits)"
    )
    search_parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("NCBI_API_KEY"),
        help="NCBI API key for higher rate limits"
    )
    
    # Fetch command
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch detailed information for specific PMIDs/DOIs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    fetch_parser.add_argument(
        "ids",
        type=str,
        nargs="+",
        help="PMIDs or DOIs to fetch (space-separated)"
    )
    fetch_parser.add_argument(
        "--database",
        "-d",
        type=str,
        choices=["pubmed", "arxiv", "biorxiv"],
        default="pubmed",
        help="Database to fetch from"
    )
    fetch_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (supports .csv, .xlsx, .json)"
    )
    
    # Export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export results to different formats",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    export_parser.add_argument(
        "input",
        type=str,
        help="Input JSON file path"
    )
    export_parser.add_argument(
        "output",
        type=str,
        help="Output file path (.csv or .xlsx)"
    )
    
    args = parser.parse_args()
    
    if args.command == "search":
        handle_search(args)
    elif args.command == "fetch":
        handle_fetch(args)
    elif args.command == "export":
        handle_export(args)


def handle_search(args):
    """Handle the search command"""
    print(f"Searching {args.database} for: {args.query}")
    print(f"Max results: {args.max_results}, Sort by: {args.sort_by}")
    
    if args.database == "pubmed":
        # Only fetch citations if sorting by citation count or filtering by minimum citations
        fetch_citations = (args.sort_by == "cited_by_count" or args.min_citations > 0)
        
        results = pubmed.search_pubmed(
            query=args.query,
            max_results=args.max_results,
            sort_by=args.sort_by,
            email=args.email,
            api_key=args.api_key,
            year=args.year,
            min_year=args.min_year,
            max_year=args.max_year,
            fetch_citations=fetch_citations
        )
    elif args.database == "arxiv":
        # Only fetch citations if sorting by citation count or filtering by minimum citations
        fetch_citations = (args.sort_by == "cited_by_count" or args.min_citations > 0)
        
        results = arxiv.search_arxiv(
            query=args.query,
            max_results=args.max_results,
            sort_by=args.sort_by,
            year=args.year,
            min_year=args.min_year,
            max_year=args.max_year,
            fetch_citations=fetch_citations
        )
    elif args.database == "biorxiv":
        results = biorxiv.search_biorxiv(
            query=args.query,
            max_results=args.max_results,
            sort_by=args.sort_by,
            year=args.year,
            min_year=args.min_year,
            max_year=args.max_year
        )
    else:
        print(f"Unknown database: {args.database}")
        return
    
    # Filter by minimum citations if specified
    if args.min_citations > 0:
        results = [r for r in results if r.get("cited_by_count", 0) >= args.min_citations]
        print(f"Filtered to {len(results)} results with >= {args.min_citations} citations")
    
    display_results(results)
    
    if args.output:
        # Setup logging to output directory
        output_dir = os.path.dirname(args.output)
        if output_dir:
            pdf_downloader.setup_logging(output_dir)
        
        utils.export_results(results, args.output, search_query=args.query)
        print(f"Results exported to {args.output}")
    
    if args.endnote:
        utils.export_endnote_references(results)
        print(f"EndNote references exported to 'endnote/' directory")


def handle_fetch(args):
    """Handle the fetch command"""
    print(f"Fetching details for {len(args.ids)} IDs...")
    
    if args.database == "pubmed":
        results = pubmed.fetch_articles(args.ids)
    elif args.database == "arxiv":
        results = arxiv.fetch_papers(args.ids)
    elif args.database == "biorxiv":
        results = biorxiv.fetch_papers(args.ids)
    else:
        print(f"Unknown database: {args.database}")
        return
    
    display_results(results)
    
    if args.output:
        # Setup logging to output directory
        output_dir = os.path.dirname(args.output)
        if output_dir:
            pdf_downloader.setup_logging(output_dir)
        
        utils.export_results(results, args.output)
        print(f"Results exported to {args.output}")


def handle_export(args):
    """Handle the export command"""
    with open(args.input, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Setup logging to output directory
    output_dir = os.path.dirname(args.output)
    if output_dir:
        pdf_downloader.setup_logging(output_dir)
    
    utils.export_results(results, args.output)
    print(f"Results exported to {args.output}")


def _safe_print(text):
    """Print text safely handling Unicode encoding issues on Windows."""
    import sys
    try:
        print(text)
    except UnicodeEncodeError:
        # Write directly as UTF-8 bytes to stdout
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write((str(text) + '\n').encode('utf-8', errors='replace'))
        else:
            # Fallback: remove problematic characters
            safe_text = ''.join(c for c in str(text) if ord(c) < 128)
            print(safe_text)


def display_results(results):
    """Display search results in a readable format"""
    if not results:
        _safe_print("No results found.")
        return
    
    _safe_print(f"\nFound {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'No title')
        authors = ', '.join(result.get('authors', []))[:100] + '...' if len(result.get('authors', [])) else 'Unknown'
        journal = result.get('journal', 'Unknown')
        year = result.get('year', 'Unknown')
        citations = result.get('cited_by_count', 0)
        doi = result.get('doi', 'Not available')
        
        _safe_print(f"[{i}] {title}")
        _safe_print(f"      Authors: {authors}")
        _safe_print(f"      Journal: {journal}")
        _safe_print(f"      Year: {year}")
        _safe_print(f"      Citations: {citations}")
        _safe_print(f"      DOI: {doi}")
        _safe_print("")


if __name__ == "__main__":
    main()
