#!/usr/bin/env python3
"""
PaperSearch GUI Interface

A graphical user interface for the PaperSearch literature search tool.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from papersearch import pubmed, arxiv, biorxiv, utils, pdf_downloader


class PaperSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PaperSearch - Literature Search Tool")
        self.root.geometry("950x750")
        self.root.resizable(True, True)
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create main frame
        self.main_frame = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Search Options
        self.left_panel = ttk.Frame(self.main_frame, width=380, padding=10)
        self.main_frame.add(self.left_panel, weight=1)
        
        # Right panel - Results
        self.right_panel = ttk.Frame(self.main_frame, width=570, padding=10)
        self.main_frame.add(self.right_panel, weight=2)
        
        self._create_search_panel()
        self._create_results_panel()
        
        # Results storage
        self.search_results = []
        
    def _create_search_panel(self):
        """Create the search options panel."""
        # Search Query
        ttk.Label(self.left_panel, text="Search Query", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.query_entry = ttk.Entry(self.left_panel, width=45)
        self.query_entry.grid(row=1, column=0, columnspan=3, sticky='we', pady=2)
        self.query_entry.insert(0, "radiotherapy")
        
        # Database Selection
        ttk.Label(self.left_panel, text="Database", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        self.database_var = tk.StringVar(value="pubmed")
        databases = [
            ("PubMed", "pubmed"),
            ("arXiv", "arxiv"),
            ("bioRxiv", "biorxiv"),
        ]
        for i, (name, value) in enumerate(databases):
            ttk.Radiobutton(self.left_panel, text=name, variable=self.database_var, value=value).grid(row=3+i, column=0, sticky='w')
        
        # Sort By
        ttk.Label(self.left_panel, text="Sort By", font=('Arial', 10, 'bold')).grid(row=8, column=0, sticky='w', pady=5)
        self.sort_by_var = tk.StringVar(value="relevance")
        sort_options = [
            ("Relevance", "relevance"),
            ("Publication Date", "pub_date"),
            ("Citation Count", "cited_by_count")
        ]
        for i, (name, value) in enumerate(sort_options):
            ttk.Radiobutton(self.left_panel, text=name, variable=self.sort_by_var, value=value).grid(row=9+i, column=0, sticky='w')
        
        # Year Filter
        ttk.Label(self.left_panel, text="Year Filter", font=('Arial', 10, 'bold')).grid(row=12, column=0, sticky='w', pady=5)
        
        ttk.Label(self.left_panel, text="Year:").grid(row=13, column=0, sticky='w')
        self.year_entry = ttk.Entry(self.left_panel, width=10)
        self.year_entry.grid(row=13, column=1, sticky='w', pady=2)
        
        ttk.Label(self.left_panel, text="Year Range:").grid(row=14, column=0, sticky='w')
        self.min_year_entry = ttk.Entry(self.left_panel, width=8)
        self.min_year_entry.grid(row=14, column=1, sticky='w', pady=2)
        # Default empty, no year limit
        
        ttk.Label(self.left_panel, text="to").grid(row=14, column=2, sticky='w')
        self.max_year_entry = ttk.Entry(self.left_panel, width=8)
        self.max_year_entry.grid(row=14, column=3, sticky='w', pady=2)
        # Default empty, no year limit
        
        # Citation Filter
        ttk.Label(self.left_panel, text="Min Citations", font=('Arial', 10, 'bold')).grid(row=15, column=0, sticky='w', pady=5)
        self.min_citations_entry = ttk.Entry(self.left_panel, width=10)
        self.min_citations_entry.grid(row=16, column=0, sticky='w', pady=2)
        self.min_citations_entry.insert(0, "0")
        
        # Max Results
        ttk.Label(self.left_panel, text="Max Results", font=('Arial', 10, 'bold')).grid(row=17, column=0, sticky='w', pady=5)
        self.max_results_entry = ttk.Entry(self.left_panel, width=10)
        self.max_results_entry.grid(row=18, column=0, sticky='w', pady=2)
        self.max_results_entry.insert(0, "20")  # Default 20 results
        
        # Output Directory
        ttk.Label(self.left_panel, text="Output Directory", font=('Arial', 10, 'bold')).grid(row=19, column=0, sticky='w', pady=5)
        self.output_dir_entry = ttk.Entry(self.left_panel, width=30)
        self.output_dir_entry.grid(row=20, column=0, sticky='we', pady=2)
        self.output_dir_entry.insert(0, "D:\\")
        
        self.browse_button = ttk.Button(self.left_panel, text="Browse", command=self._browse_output_dir, width=10)
        self.browse_button.grid(row=20, column=1, sticky='w', padx=5)
        
        # Export Options
        ttk.Label(self.left_panel, text="Export Options", font=('Arial', 10, 'bold')).grid(row=21, column=0, sticky='w', pady=5)
        
        self.export_csv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.left_panel, text="CSV", variable=self.export_csv_var).grid(row=22, column=0, sticky='w')
        
        self.export_md_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.left_panel, text="Markdown", variable=self.export_md_var).grid(row=22, column=1, sticky='w')
        
        self.export_json_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.left_panel, text="JSON", variable=self.export_json_var).grid(row=23, column=0, sticky='w')
        
        self.export_endnote_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.left_panel, text="EndNote RIS", variable=self.export_endnote_var).grid(row=23, column=1, sticky='w')
        
        self.export_pdf_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.left_panel, text="PDF", variable=self.export_pdf_var).grid(row=24, column=0, sticky='w')
        
        # Export Button
        self.export_button = ttk.Button(self.left_panel, text="Export Results", command=self._export_with_dialog, width=15)
        self.export_button.grid(row=25, column=0, sticky='w', pady=10)
        self.export_button.config(state='disabled')  # Disabled initially, enabled after results
        
        # Search Button
        self.search_button = ttk.Button(self.left_panel, text="Search", command=self._start_search, style='Accent.TButton')
        self.search_button.grid(row=25, column=1, sticky='w', pady=10)
        
        # Progress Label
        self.progress_label = ttk.Label(self.left_panel, text="", foreground='blue')
        self.progress_label.grid(row=26, column=0, columnspan=2, sticky='w')
        
        # Configure grid weights
        self.left_panel.grid_columnconfigure(0, weight=1)
        
    def _create_results_panel(self):
        """Create the results display panel."""
        # Results Treeview
        ttk.Label(self.right_panel, text="Search Results", font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        self.results_frame = ttk.Frame(self.right_panel)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create Treeview
        self.results_tree = ttk.Treeview(self.results_frame, columns=('Index', 'Title', 'Authors', 'Year', 'Journal', 'Citations'), show='headings')
        self.results_tree.heading('Index', text='#', anchor='w')
        self.results_tree.heading('Title', text='Title', anchor='w')
        self.results_tree.heading('Authors', text='Authors', anchor='w')
        self.results_tree.heading('Year', text='Year', anchor='w')
        self.results_tree.heading('Journal', text='Journal', anchor='w')
        self.results_tree.heading('Citations', text='Citations', anchor='w')
        
        self.results_tree.column('Index', width=50, anchor='w')
        self.results_tree.column('Title', width=200, anchor='w')
        self.results_tree.column('Authors', width=120, anchor='w')
        self.results_tree.column('Year', width=60, anchor='w')
        self.results_tree.column('Journal', width=120, anchor='w')
        self.results_tree.column('Citations', width=70, anchor='w')
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self.tree_scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.configure(yscrollcommand=self.tree_scrollbar.set)
        
        # Details Panel
        ttk.Label(self.right_panel, text="Details", font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        self.details_text = scrolledtext.ScrolledText(self.right_panel, width=85, height=15, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, pady=2)
        self.details_text.insert(tk.INSERT, "Select a paper to view details...")
        self.details_text.config(state=tk.DISABLED)
        
        # Bind treeview selection
        self.results_tree.bind('<<TreeviewSelect>>', self._on_select_result)
        
    def _browse_output_dir(self):
        """Browse for output directory."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, dir_path)
    
    def _start_search(self):
        """Start the search in a separate thread."""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query")
            return
        
        # Disable search button
        self.search_button.config(state='disabled')
        self.progress_label.config(text="Searching...")
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.INSERT, "Searching, please wait...")
        self.details_text.config(state=tk.DISABLED)
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Start search in background thread
        thread = threading.Thread(target=self._perform_search)
        thread.daemon = True
        thread.start()
    
    def _perform_search(self):
        """Perform the actual search."""
        try:
            query = self.query_entry.get().strip()
            database = self.database_var.get()
            
            # Parse max_results - if empty, get all results (set a large number)
            max_results_str = self.max_results_entry.get().strip()
            if max_results_str:
                max_results = int(max_results_str)
            else:
                max_results = 1000  # Get all results
            
            # Parse min_citations - if empty, default to 0
            min_citations_str = self.min_citations_entry.get().strip()
            if min_citations_str:
                min_citations = int(min_citations_str)
            else:
                min_citations = 0
            
            sort_by = self.sort_by_var.get()
            
            # Validate query
            if not query:
                self.root.after(0, lambda: self.progress_label.config(text="Please enter a search query"))
                self.root.after(0, lambda: self.search_button.config(state='normal'))
                messagebox.showwarning("Warning", "Please enter a search query")
                return
            
            # Parse year filters
            year = None
            min_year = None
            max_year = None
            
            if self.year_entry.get().strip():
                year = int(self.year_entry.get())
            else:
                if self.min_year_entry.get().strip():
                    min_year = int(self.min_year_entry.get())
                if self.max_year_entry.get().strip():
                    max_year = int(self.max_year_entry.get())
            
            # Perform search - get more results for filtering
            self.root.after(0, lambda: self.progress_label.config(text=f"Searching {database}..."))
            
            # If there are year or citation filters, get more results
            has_filters = (year or min_year or max_year or min_citations > 0)
            fetch_count = max_results * 3 if has_filters else max_results
            
            if database == "pubmed":
                results = pubmed.search_pubmed(query, max_results=fetch_count)
            elif database == "arxiv":
                results = arxiv.search_arxiv(query, max_results=fetch_count)
            elif database == "biorxiv":
                results = biorxiv.search_biorxiv(query, max_results=fetch_count)
            else:
                results = []
            
            # Apply year filters - safe handling to avoid type errors
            def _get_year(r):
                """Safely get year, handling string and numeric types"""
                y = r.get("year")
                if y is None:
                    return None
                try:
                    return int(y)
                except (ValueError, TypeError):
                    return None
            
            if year:
                results = [r for r in results if _get_year(r) == year]
            else:
                if min_year:
                    results = [r for r in results if _get_year(r) is not None and _get_year(r) >= min_year]
                if max_year:
                    results = [r for r in results if _get_year(r) is not None and _get_year(r) <= max_year]
            
            # Apply citation filter - filter before limiting results
            if min_citations > 0:
                results = [r for r in results if r.get("cited_by_count", 0) >= min_citations]
            
            # Finally limit results
            results = results[:max_results]
            
            # Apply sorting
            if sort_by == "pub_date":
                results.sort(key=lambda x: int(x.get("year") or 0), reverse=True)
            elif sort_by == "cited_by_count":
                results.sort(key=lambda x: int(x.get("cited_by_count") or 0), reverse=True)
            # else: relevance (default, no additional sorting needed)
            
            self.search_results = results
            
            # Update UI with results
            self.root.after(0, lambda: self._display_results(results))
            
        except Exception as e:
            self.root.after(0, lambda err=e: self._handle_search_error(str(err)))
    
    def _display_results(self, results):
        """Display search results in the treeview."""
        self.progress_label.config(text=f"Search complete, found {len(results)} papers")
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "")[:50] + "..." if len(result.get("title", "")) > 50 else result.get("title", "")
            authors = ", ".join(result.get("authors", []))[:25] + "..." if len(", ".join(result.get("authors", []))) > 25 else ", ".join(result.get("authors", []))
            journal = result.get("journal", "")[:25] + "..." if len(result.get("journal", "")) > 25 else result.get("journal", "")
            
            self.results_tree.insert('', tk.END, values=(
                i,
                title,
                authors,
                result.get("year", ""),
                journal,
                result.get("cited_by_count", 0)
            ))
        
        if results:
            self.results_tree.selection_set(self.results_tree.get_children()[0])
            self._on_select_result(None)
            # Enable export button
            self.export_button.config(state='normal')
        
        # Enable search button
        self.search_button.config(state='normal')
    
    def _on_select_result(self, event):
        """Handle selection of a result."""
        selected_items = self.results_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        index = int(self.results_tree.item(item, 'values')[0]) - 1
        
        if 0 <= index < len(self.search_results):
            result = self.search_results[index]
            
            self.details_text.config(state=tk.NORMAL)
            self.details_text.delete(1.0, tk.END)
            
            details = f"Title: {result.get('title', '')}\n\n"
            details += f"Authors: {', '.join(result.get('authors', []))}\n\n"
            details += f"Journal: {result.get('journal', '')}\n"
            details += f"Year: {result.get('year', '')}\n"
            details += f"DOI: {result.get('doi', '')}\n"
            details += f"Citations: {result.get('cited_by_count', 0)}\n\n"
            details += f"Abstract:\n{result.get('abstract', '')}"
            
            self.details_text.insert(tk.INSERT, details)
            self.details_text.config(state=tk.DISABLED)
    
    def _export_results(self, query, results):
        """Export results to selected formats."""
        if not results:
            self.progress_label.config(text="No results to export")
            return
        
        output_dir = self.output_dir_entry.get().strip()
        
        # Check if output directory exists and is writable
        if not output_dir:
            messagebox.showerror("Error", "Please specify output directory")
            return
        
        # If directory doesn't exist, try to create
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"Created output directory: {output_dir}")
            except PermissionError:
                messagebox.showerror("Permission Error", f"Cannot create directory: {output_dir}\nPlease select another directory or run as administrator")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output directory: {e}")
                return
        
        # Check if directory is writable
        if not os.access(output_dir, os.W_OK):
            messagebox.showerror("Permission Error", f"No write permission: {output_dir}\nPlease select another directory or run as administrator")
            return
        
        # Create PaperSearchRes subdirectory
        output_dir = os.path.join(output_dir, "PaperSearchRes")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"papersearch_{timestamp}"
        
        # Clear progress label
        self.progress_label.config(text="")
        self.root.update_idletasks()
        
        exported_files = []
        errors = []
        
        # Lists to store filenames and download info
        endnote_files = []
        pdf_files = []
        pdf_download_success = []
        pdf_download_method = []
        
        try:
            # Export EndNote first (to get filenames)
            if self.export_endnote_var.get():
                endnote_dir = os.path.join(output_dir, "endnote")
                try:
                    self.progress_label.config(text="Exporting EndNote files...")
                    self.root.update_idletasks()
                    endnote_files = utils.export_endnote_references(results, endnote_dir)
                    exported_files.append(f"EndNote: {endnote_dir} ({len(endnote_files)} files)")
                    self.progress_label.config(text=f"EndNote exported: {endnote_dir}")
                except PermissionError:
                    errors.append(f"EndNote file is occupied or no write permission")
                except Exception as e:
                    errors.append(f"EndNote export failed: {e}")
            
            # Export PDF (to get filenames)
            if self.export_pdf_var.get():
                pdf_dir = os.path.join(output_dir, "pdf")
                try:
                    # Load config from file
                    config = pdf_downloader.load_config()
                    
                    # Show progress (clear previous text first)
                    self.progress_label.config(text="")
                    self.root.update_idletasks()
                    self.progress_label.config(text="Downloading PDF files...")
                    self.root.update_idletasks()
                    
                    # Download PDFs in parallel (using config settings)
                    download_records = pdf_downloader.download_pdfs_parallel(
                        results, 
                        pdf_dir,
                        max_workers=config['max_workers'],
                        scihub_mirrors=config['scihub_mirrors'],
                        timeout=config['timeout']
                    )
                    
                    # Extract PDF filenames and download info from download records
                    pdf_files = [r['pdf_filename'] for r in download_records]
                    pdf_download_success = [str(r['download_success']) for r in download_records]
                    pdf_download_method = [r['download_method'] for r in download_records]
                    
                    success_count = sum(1 for r in download_records if r['download_success'])
                    exported_files.append(f"PDF: {pdf_dir} ({success_count}/{len(download_records)} success)")
                    self.progress_label.config(text=f"PDF download complete: {success_count}/{len(download_records)}")
                except PermissionError:
                    errors.append(f"PDF directory has no write permission")
                except Exception as e:
                    errors.append(f"PDF download failed: {e}")
                    pdf_files = []
                    pdf_download_success = []
                    pdf_download_method = []
            
            # Auto-select CSV if EndNote or PDF is selected
            export_csv = self.export_csv_var.get() or self.export_endnote_var.get() or self.export_pdf_var.get()
            
            # Export CSV (with EndNote and PDF filenames)
            if export_csv:
                csv_path = os.path.join(output_dir, f"{base_name}.csv")
                try:
                    self.progress_label.config(text="Exporting CSV...")
                    self.root.update_idletasks()
                    # Use download_records if available (contains download info), otherwise use original results
                    export_data = download_records if 'download_records' in locals() else results
                    utils.export_results(export_data, csv_path, search_query=query, 
                                        endnote_files=endnote_files, pdf_files=pdf_files,
                                        pdf_download_success=pdf_download_success,
                                        pdf_download_method=pdf_download_method)
                    exported_files.append(f"CSV: {csv_path}")
                    self.progress_label.config(text=f"CSV exported: {csv_path}")
                except PermissionError:
                    errors.append(f"CSV file is occupied or no write permission")
                except Exception as e:
                    errors.append(f"CSV export failed: {e}")
            
            # Export Markdown
            if self.export_md_var.get():
                md_path = os.path.join(output_dir, f"{base_name}.md")
                try:
                    self.progress_label.config(text="Exporting Markdown...")
                    self.root.update_idletasks()
                    # Use download_records if available
                    export_data = download_records if 'download_records' in locals() else results
                    utils.export_results(export_data, md_path, search_query=query, 
                                        endnote_files=endnote_files, pdf_files=pdf_files,
                                        pdf_download_success=pdf_download_success,
                                        pdf_download_method=pdf_download_method)
                    exported_files.append(f"Markdown: {md_path}")
                    self.progress_label.config(text=f"Markdown exported: {md_path}")
                except PermissionError:
                    errors.append(f"Markdown file is occupied or no write permission")
                except Exception as e:
                    errors.append(f"Markdown export failed: {e}")
            
            # Export JSON
            if self.export_json_var.get():
                json_path = os.path.join(output_dir, f"{base_name}.json")
                try:
                    self.progress_label.config(text="Exporting JSON...")
                    self.root.update_idletasks()
                    utils.export_results(results, json_path, search_query=query)
                    exported_files.append(f"JSON: {json_path}")
                    self.progress_label.config(text=f"JSON exported: {json_path}")
                except PermissionError:
                    errors.append(f"JSON file is occupied or no write permission")
                except Exception as e:
                    errors.append(f"JSON export failed: {e}")
            
            # Show results
            if exported_files and not errors:
                self.progress_label.config(text=f"Export complete! Exported {len(results)} results, {len(exported_files)} files")
            elif exported_files and errors:
                self.progress_label.config(text=f"Partial export success, {len(errors)} failed")
                messagebox.showwarning("Partial Export Success", f"Exported {len(exported_files)} files\nFailed:\n" + "\n".join(errors))
            elif errors:
                self.progress_label.config(text=f"Export failed")
                messagebox.showerror("Export Failed", "\n".join(errors))
            else:
                self.progress_label.config(text="Please select export format")
                
        except Exception as e:
            self.progress_label.config(text=f"Export failed: {e}")
            messagebox.showerror("Export Error", f"Export failed: {e}")
    
    def _export_with_dialog(self):
        """Export results with dialog to select export options."""
        if not self.search_results:
            messagebox.showwarning("Warning", "No results to export, please search first")
            return
        
        # Get current search query
        search_term = self.query_entry.get().strip()
        
        # Execute export
        self._export_results(search_term, self.search_results)
    
    def _handle_search_error(self, error_msg):
        """Handle search errors."""
        self.progress_label.config(text="Search failed")
        self.search_button.config(state='normal')
        messagebox.showerror("Search Error", f"An error occurred during search:\n{error_msg}")


def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = PaperSearchGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
