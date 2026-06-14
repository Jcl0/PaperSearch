"""Utility functions for PaperSearch."""

import csv
import json
import os
import re
from datetime import datetime


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)[:100]


def get_journal_abbreviation(journal: str) -> str:
    """Get journal abbreviation from full journal name."""
    if not journal:
        return "Unknown"
    
    # Common journal abbreviations
    abbreviations = {
        "nature medicine": "NatMed",
        "nature": "Nature",
        "science": "Science",
        "cell": "Cell",
        "the lancet": "Lancet",
        "new england journal of medicine": "NEnglJMed",
        "journal of the american medical association": "JAMA",
        "british medical journal": "BMJ",
        "plos one": "PLoSOne",
        "nature communications": "NatCommun",
        "science advances": "SciAdv",
        "cell reports": "CellRep",
        "proceedings of the national academy of sciences": "PNAS",
        "journal of biological chemistry": "JBiolChem",
        "nucleic acids research": "NucleicAcidsRes",
        "nature genetics": "NatGenet",
        "nature biotechnology": "NatBiotechnol",
        "nature neuroscience": "NatNeurosci",
        "nature cell biology": "NatCellBiol",
        "nature immunology": "NatImmunol",
        "nature microbiology": "NatMicrobiol",
        "nature methods": "NatMethods",
        "nature protocols": "NatProtoc",
        "nature reviews genetics": "NatRevGenet",
        "nature reviews molecular cell biology": "NatRevMolCellBiol",
        "nature reviews immunology": "NatRevImmunol",
        "nature reviews neuroscience": "NatRevNeurosci",
        "cell stem cell": "CellStemCell",
        "cell metabolism": "CellMetab",
        "cell cycle": "CellCycle",
        "cancer cell": "CancerCell",
        "developmental cell": "DevCell",
        "neuron": "Neuron",
        "genome research": "GenomeRes",
        "genome biology": "GenomeBiol",
        "bioinformatics": "Bioinformatics",
        "bmc bioinformatics": "BMCBioinformatics",
        "npj digital medicine": "NPJDigMed",
        "radiotherapy and oncology": "RadiotherOncol",
        "international journal of radiation oncology biology physics": "IntJRadiatOncolBiolPhys",
        "medical physics": "MedPhys",
        "physics in medicine and biology": "PhysMedBiol",
        "radiology": "Radiology",
        "journal of clinical investigation": "JClinInvest",
        "journal of the american college of cardiology": "JAmCollCardiol",
        "circulation": "Circulation",
        "circulation research": "CircRes",
        "journal of immunology": "JImmunol",
        "immunity": "Immunity",
        "journal of neuroscience": "JNeurosci",
        "brain": "Brain",
        "journal of neurology": "JNeurol",
        "annals of neurology": "AnnNeurol",
        "stroke": "Stroke",
        "neuroimage": "NeuroImage",
        "psychiatry research": "PsychiatryRes",
        "biological psychiatry": "BiolPsychiatry",
        "american journal of psychiatry": "AmJPsychiatry",
        "journal of affective disorders": "JAffectDisord",
        "psychological science": "PsycholSci",
        "journal of personality and social psychology": "JPersSocPsychol",
        "journal of applied psychology": "JApplPsychol",
        "journal of management": "JManag",
        "strategic management journal": "StrategManagJ",
        "academy of management journal": "AcadManagJ",
        "research policy": "ResPolicy",
        "journal of business research": "JBusRes",
        "marketing science": "MarkSci",
        "journal of marketing": "JMark",
        "management science": "ManageSci",
        "operations research": "OperRes",
        "information systems research": "InfSystRes",
        "mis quarterly": "MISQ",
        "journal of management information systems": "JManagInfSyst",
        "information systems journal": "InfSystJ",
        "decision support systems": "DecisSupportSyst",
        "expert systems with applications": "ExpertSystAppl",
        "computers in human behavior": "ComputHumBehav",
        "international journal of human-computer studies": "IntJHumComputStud",
        "computers & education": "ComputEduc",
        "internet and higher education": "InternetHighEduc",
        "british journal of educational technology": "BrJEducTechnol",
        "journal of educational psychology": "JEducPsychol",
        "learning and instruction": "LearnInstr",
        "review of educational research": "RevEducRes",
        "journal of environmental management": "JEnvironManag",
        "environmental science & technology": "EnvironSciTechnol",
        "nature climate change": "NatClimChang",
        "journal of cleaner production": "JCleanProd",
        "journal of hazardous materials": "JHazardMater",
        "chemosphere": "Chemosphere",
        "environmental pollution": "EnvironPollut",
        "science of the total environment": "SciTotalEnviron",
        "environmental health perspectives": "EnvironHealthPerspect",
        "journal of medicinal chemistry": "JMedChem",
        "bioorganic & medicinal chemistry": "BioorgMedChem",
        "journal of the american chemical society": "JAmChemSoc",
        "chemical communications": "ChemCommun",
        "advanced materials": "AdvMater",
        "advanced functional materials": "AdvFunctMater",
        "nano letters": "NanoLett",
        "acs nano": "ACSNano",
        "small": "Small",
        "nature nanotechnology": "NatNanotechnol",
        "plos biology": "PLoSBiol",
        "plos medicine": "PLoSMed",
        "bmj open": "BMJOpen",
        "scientific reports": "SciRep",
        "npj science of learning": "NPJSciLearn",
    }
    
    journal_lower = journal.lower().strip()
    
    # Check for exact match
    if journal_lower in abbreviations:
        return abbreviations[journal_lower]
    
    # Try to find partial match
    for full_name, abbr in abbreviations.items():
        if full_name in journal_lower or journal_lower in full_name:
            return abbr
    
    # If no abbreviation found, use first few words
    words = journal_lower.split()
    if len(words) <= 2:
        return journal[:30].replace(" ", "")
    else:
        # Take first letter of each word
        abbr = "".join([word[0].upper() for word in words[:4]])
        return abbr


def get_unique_filename(directory: str, base_name: str, extension: str = "ris") -> str:
    """Generate a unique filename by appending numbers if needed.
    
    If filename exists: filename_1.ext, filename_2.ext, ...
    If filename_1 exists: filename_2.ext, ...
    """
    base_name = sanitize_filename(base_name)
    
    # Check if base filename exists
    base_path = os.path.join(directory, f"{base_name}.{extension}")
    if not os.path.exists(base_path):
        return base_path
    
    # Find the highest existing number
    counter = 1
    pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)\.{extension}$")
    
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            num = int(match.group(1))
            if num >= counter:
                counter = num + 1
    
    return os.path.join(directory, f"{base_name}_{counter}.{extension}")


def export_results(results: list[dict], output_path: str, search_query: str = "", 
                   endnote_files: list = None, pdf_files: list = None,
                   pdf_download_success: list = None, pdf_download_method: list = None) -> None:
    """Export search results to a file.
    
    Supports: .csv, .md, .json
    
    Args:
        results: List of search results
        output_path: Path to output file
        search_query: The search query used (for adding to CSV)
        endnote_files: List of EndNote filenames (one per result)
        pdf_files: List of PDF filenames (one per result)
        pdf_download_success: List of PDF download success status (one per result)
        pdf_download_method: List of PDF download methods (one per result)
    """
    if not results:
        print("No results to export.")
        return
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Normalize the results for export
    normalized_results = []
    for i, result in enumerate(results, 1):
        normalized = {
            "Index": i,
            "Search Query": search_query,
            "Title": result.get("title", ""),
            "Authors": ", ".join(result.get("authors", [])),
            "Journal": result.get("journal", ""),
            "Year": result.get("year", ""),
            "DOI": result.get("doi", ""),
            "Citations": result.get("cited_by_count", 0),
            "arXiv ID": result.get("arxiv_id", ""),
            "PMID": result.get("pmid", ""),
        }
        
        # Add EndNote filename if available
        if endnote_files and i <= len(endnote_files):
            normalized["EndNote File"] = endnote_files[i-1]
        else:
            normalized["EndNote File"] = ""
        
        # Add PDF filename if available
        if pdf_files and i <= len(pdf_files):
            normalized["PDF File"] = pdf_files[i-1]
        else:
            normalized["PDF File"] = ""
        
        # Add PDF download success status
        if pdf_download_success and i <= len(pdf_download_success):
            normalized["PDF Download Success"] = pdf_download_success[i-1]
        else:
            normalized["PDF Download Success"] = ""
        
        # Add PDF download method
        if pdf_download_method and i <= len(pdf_download_method):
            normalized["PDF Download Method"] = pdf_download_method[i-1]
        else:
            normalized["PDF Download Method"] = ""
        
        # Add Abstract last
        normalized["Abstract"] = result.get("abstract", "")
        
        normalized_results.append(normalized)
    
    # Determine output format based on file extension
    if output_path.endswith(".csv"):
        _export_csv(normalized_results, output_path)
    elif output_path.endswith(".md"):
        _export_markdown(normalized_results, output_path)
    elif output_path.endswith(".json"):
        _export_json(results, output_path)
    else:
        # Default to CSV
        _export_csv(normalized_results, output_path + ".csv")


def export_endnote_references(results: list[dict], output_dir: str = "endnote") -> list:
    """Export results as EndNote reference files (.ris format).
    
    Args:
        results: List of search results
        output_dir: Directory to save EndNote files
    
    Returns:
        List of EndNote filenames (one per result)
    """
    if not results:
        print("No results to export as EndNote references.")
        return []
    
    # Ensure endnote directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    endnote_files = []
    
    for result in results:
        ris_content = _generate_ris_content(result)
        filename = _generate_endnote_filename(result, output_dir)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(ris_content)
        
        print(f"EndNote reference saved: {filename}")
        endnote_files.append(os.path.basename(filename))
    
    return endnote_files


def _generate_ris_content(result: dict) -> str:
    """Generate RIS format content for a single result."""
    ris_lines = []
    
    # Reference type: Journal Article
    ris_lines.append("TY  - JOUR")
    
    # Authors
    authors = result.get("authors", [])
    for author in authors[:10]:  # Limit to 10 authors
        ris_lines.append(f"AU  - {author}")
    
    # Title
    title = result.get("title", "")
    if title:
        ris_lines.append(f"TI  - {title}")
    
    # Journal
    journal = result.get("journal", "")
    if journal:
        ris_lines.append(f"JO  - {journal}")
    
    # Year
    year = result.get("year", "")
    if year:
        ris_lines.append(f"PY  - {year}")
    
    # DOI
    doi = result.get("doi", "")
    if doi:
        ris_lines.append(f"DO  - {doi}")
    
    # Abstract
    abstract = result.get("abstract", "")
    if abstract:
        ris_lines.append(f"AB  - {abstract}")
    
    # PMID if available
    pmid = result.get("pmid", result.get("id", ""))
    if pmid and not pmid.startswith("http"):
        ris_lines.append(f"PM  - {pmid}")
    
    # End of reference
    ris_lines.append("ER  -")
    
    return "\n".join(ris_lines)


def _generate_endnote_filename(result: dict, output_dir: str) -> str:
    """Generate a unique filename for EndNote reference using Author_Year_JournalAbbreviation format."""
    # Get first author full name (not abbreviated)
    authors = result.get("authors", [])
    first_author = authors[0] if authors else "Unknown"
    
    # Clean author name: remove commas, replace spaces with underscores
    author_name = first_author.replace(",", "").replace(" ", "_")
    author_name = sanitize_filename(author_name)
    
    # Get journal abbreviation
    journal = result.get("journal", "")
    journal_abbr = get_journal_abbreviation(journal)
    
    # Get year
    year = str(result.get("year", "")) if result.get("year") else "Unknown"
    
    # Format: Author_Year_JournalAbbreviation
    base_name = f"{author_name}_{year}_{journal_abbr}"
    
    return get_unique_filename(output_dir, base_name, "ris")


def _export_csv(results: list[dict], output_path: str) -> None:
    """Export results to CSV format."""
    if not results:
        return
    
    fieldnames = ["Index", "Search Query", "Title", "Authors", "Journal", "Year", "DOI", "Citations", "arXiv ID", "PMID", "EndNote File", "PDF File", "PDF Download Success", "PDF Download Method", "Abstract"]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _export_markdown(results: list[dict], output_path: str) -> None:
    """Export results to Markdown format."""
    if not results:
        return
    
    # Set column order
    column_order = ["Index", "Search Query", "Title", "Authors", "Journal", "Year", "DOI", "Citations", "arXiv ID", "PMID", "EndNote File", "PDF File", "PDF Download Success", "PDF Download Method", "Abstract"]
    
    # Build markdown table
    lines = []
    
    # Add title
    lines.append("# Literature Search Results")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Results: {len(results)}")
    lines.append("")
    
    # Add table header
    lines.append("| " + " | ".join(column_order) + " |")
    lines.append("| " + " | ".join(["---"] * len(column_order)) + " |")
    
    # Add table rows
    for row in results:
        row_values = []
        for col in column_order:
            value = str(row.get(col, ""))
            # Escape special markdown characters
            value = value.replace("|", "\\|")
            value = value.replace("\n", " ")
            row_values.append(value)
        lines.append("| " + " | ".join(row_values) + " |")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def _export_json(results: list[dict], output_path: str) -> None:
    """Export results to JSON format."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
