#!/usr/bin/env python3
"""
Test script for PaperSearch application.
Tests PubMed, arXiv, and bioRxiv search functionality.
"""

import sys
sys.path.insert(0, 'src')

from papersearch import pubmed, arxiv, biorxiv, utils

def test_pubmed():
    """Test PubMed search functionality"""
    print("=" * 60)
    print("Testing PubMed Search")
    print("=" * 60)
    
    try:
        print("\nTest 1: Basic search")
        results = pubmed.search_pubmed('machine learning', max_results=3)
        print(f"Results found: {len(results)}")
        for i, r in enumerate(results[:3], 1):
            print(f"{i}. {r.get('title', '')[:60]}...")
        
        print("\nTest 2: Search with year filter")
        results = pubmed.search_pubmed('AI healthcare', year=2024, max_results=3)
        print(f"Results found: {len(results)}")
        
        print("\nTest 3: Search with year range")
        results = pubmed.search_pubmed('CRISPR', min_year=2023, max_year=2025, max_results=3)
        print(f"Results found: {len(results)}")
        
        print("\n✅ PubMed tests passed!")
        
    except Exception as e:
        print(f"❌ PubMed test failed: {e}")
        import traceback
        traceback.print_exc()

def test_arxiv():
    """Test arXiv search functionality"""
    print("\n" + "=" * 60)
    print("Testing arXiv Search")
    print("=" * 60)
    
    try:
        print("\nTest 1: Basic search")
        results = arxiv.search_arxiv('deep learning', max_results=3)
        print(f"Results found: {len(results)}")
        for i, r in enumerate(results[:3], 1):
            print(f"{i}. {r.get('title', '')[:60]}...")
        
        print("\nTest 2: Search with year filter")
        results = arxiv.search_arxiv('large language model', year=2024, max_results=3)
        print(f"Results found: {len(results)}")
        
        print("\n✅ arXiv tests passed!")
        
    except Exception as e:
        print(f"❌ arXiv test failed: {e}")
        import traceback
        traceback.print_exc()

def test_biorxiv():
    """Test bioRxiv search functionality"""
    print("\n" + "=" * 60)
    print("Testing bioRxiv Search")
    print("=" * 60)
    
    try:
        print("\nTest 1: Basic search")
        results = biorxiv.search_biorxiv('CRISPR', max_results=3)
        print(f"Results found: {len(results)}")
        for i, r in enumerate(results[:3], 1):
            print(f"{i}. {r.get('title', '')[:60]}...")
        
        print("\nTest 2: Search with year filter")
        results = biorxiv.search_biorxiv('single cell RNA sequencing', year=2024, max_results=3)
        print(f"Results found: {len(results)}")
        
        print("\n✅ bioRxiv tests passed!")
        
    except Exception as e:
        print(f"❌ bioRxiv test failed: {e}")
        import traceback
        traceback.print_exc()

def test_export():
    """Test export functionality"""
    print("\n" + "=" * 60)
    print("Testing Export Functionality")
    print("=" * 60)
    
    try:
        # Create test data
        test_results = [
            {
                'title': 'Test Article 1',
                'authors': ['John Doe', 'Jane Smith'],
                'journal': 'Test Journal',
                'year': 2024,
                'abstract': 'This is a test abstract.',
                'doi': '10.1234/test.2024.001',
                'cited_by_count': 10
            },
            {
                'title': 'Test Article 2',
                'authors': ['Alice Johnson'],
                'journal': 'Another Journal',
                'year': 2023,
                'abstract': 'Another test abstract.',
                'doi': '10.1234/test.2023.002',
                'cited_by_count': 5
            }
        ]
        
        print("\nTest 1: Export to CSV")
        csv_path = 'test_output.csv'
        utils.export_results(test_results, csv_path, search_query='test query')
        print(f"✓ CSV export successful: {csv_path}")
        
        print("\nTest 2: Export to JSON")
        json_path = 'test_output.json'
        utils.export_results(test_results, json_path)
        print(f"✓ JSON export successful: {json_path}")
        
        print("\nTest 3: Export EndNote references")
        endnote_dir = 'endnote_test'
        utils.export_endnote_references(test_results, endnote_dir)
        print(f"✓ EndNote export successful: {endnote_dir}")
        
        # Cleanup
        import os
        if os.path.exists(csv_path):
            os.remove(csv_path)
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(endnote_dir):
            import shutil
            shutil.rmtree(endnote_dir)
        
        print("\n✅ Export tests passed!")
        
    except Exception as e:
        print(f"❌ Export test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PaperSearch Test Suite")
    print("=" * 60)
    
    test_pubmed()
    test_arxiv()
    test_biorxiv()
    test_export()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
