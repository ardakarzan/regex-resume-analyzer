# gui/main_window.py
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, Listbox, Text
from tkinter import ttk # Themed widgets
import logging
import os
import threading

# Import project modules
import constants
import config
from utils.pdf_parser import extract_text_from_pdf
from utils.resume_analyzer import (
    extract_years_experience,
    find_user_skills_in_text,
    calculate_skill_symbol,
    extract_basic_info
)
# Keep Camunda client import - we are using the engine implementation
from camunda.camunda_client import get_next_state_from_camunda


class DynamicDFASimulatorApp:
    def __init__(self, master):
        self.master = master
        self.style = ttk.Style()
        try:
            self.style.theme_use('vista')
        except tk.TclError:
            logging.warning("Could not apply 'vista' theme. Using default.")

        master.title(f"Resume DFA Analyzer (Engine Target: {config.CAMUNDA_BASE_URL})")
        master.geometry("850x750")

        self.pdf_path = None
        self.folder_path = None
        self.required_skills_set = set() # Holds lowercase skills for logic

        # Define helper methods needed during UI build or early init
        # (Methods like clear_summary, reset_results are defined further down)

        # Build the UI - this creates the widgets
        self._build_ui()

        # Set initial state for results area *after* widgets are created
        self.reset_results()


    # --- Methods Definition Order: Define before first call ---

    def update_status(self, message):
        """Updates the status bar safely from any thread."""
        # Ensure status_label exists before configuring
        if hasattr(self, 'status_label'):
            self.master.after(0, lambda: self.status_label.config(text=message))
        else:
            logging.warning("Attempted to update status_label before it was created.")

    def clear_summary(self):
         """Clears the results summary text area safely."""
         if hasattr(self, 'results_summary_text'):
             def _clear():
                try:
                    self.results_summary_text.config(state=tk.NORMAL)
                    self.results_summary_text.delete("1.0", tk.END)
                    self.results_summary_text.config(state=tk.DISABLED)
                except tk.TclError:
                     logging.warning("Attempted to clear summary text, but widget might not exist or be destroyed.")
             # Use master.after to ensure it runs on the main GUI thread
             self.master.after(0, _clear)
         else:
              logging.warning("Tried to clear summary, but results_summary_text widget not found.")

    def append_summary(self, message):
        """Appends text to the results summary area safely."""
        if hasattr(self, 'results_summary_text'):
            def _append():
                try:
                    self.results_summary_text.config(state=tk.NORMAL)
                    self.results_summary_text.insert(tk.END, message + "\n")
                    self.results_summary_text.see(tk.END) # Scroll to bottom
                    self.results_summary_text.config(state=tk.DISABLED)
                except tk.TclError:
                    logging.warning("Attempted to append summary text, but widget might not exist or be destroyed.")
            # Use master.after for thread safety
            self.master.after(0, _append)
        else:
            logging.warning("Tried to append summary, but results_summary_text widget not found.")

    def reset_results(self):
        """Clears the results summary area and resets result frame background."""
        self.clear_summary()
        # Resetting ttk widget backgrounds is often unnecessary/handled by theme
        # if hasattr(self, 'results_frame'):
        #     self.results_frame.config(style='TFrame') # Reset to default style if needed

    def _build_ui(self):
        # Main frame using ttk
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame: File/Folder Selection ---
        self.file_frame = ttk.LabelFrame(main_frame, text="Input Source", padding="10")
        self.file_frame.pack(pady=5, padx=5, fill=tk.X)
        self.browse_file_button = ttk.Button(self.file_frame, text="Select Single PDF...", command=self.browse_file)
        self.browse_file_button.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.browse_folder_button = ttk.Button(self.file_frame, text="Select Folder...", command=self.browse_folder)
        self.browse_folder_button.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
        self.source_label = ttk.Label(self.file_frame, text="No source selected", style='Status.TLabel', relief="sunken", width=70, anchor='w', padding=(5,2))
        self.source_label.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.file_frame.columnconfigure(2, weight=1)

        # --- Middle Frame: User Requirements ---
        self.req_frame = ttk.LabelFrame(main_frame, text="Requirements", padding="10")
        self.req_frame.pack(pady=10, padx=5, fill=tk.X)
        self.req_frame.columnconfigure(2, weight=1)
        self.req_frame.rowconfigure(4, weight=1)

        ttk.Label(self.req_frame, text="Min Exp (yrs):").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.min_exp_entry = ttk.Entry(self.req_frame, width=5); self.min_exp_entry.grid(row=0, column=1, sticky='w', pady=2); self.min_exp_entry.insert(0, "2")
        ttk.Label(self.req_frame, text="Pref Exp (yrs):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.pref_exp_entry = ttk.Entry(self.req_frame, width=5); self.pref_exp_entry.grid(row=1, column=1, sticky='w', pady=2); self.pref_exp_entry.insert(0, "5")

        skill_input_frame = ttk.Frame(self.req_frame)
        skill_input_frame.grid(row=0, column=2, rowspan=5, sticky='nsew', padx=(20, 5), pady=0)
        ttk.Label(skill_input_frame, text="Required Skills (one per line or comma-separated):").pack(anchor='w', padx=2, pady=(0,2))
        self.skill_text_widget = Text(skill_input_frame, height=4, width=40, relief="solid", borderwidth=1, font=('Segoe UI', 9))
        self.skill_text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 5), padx=2) # Allow text widget to expand more
        skill_input_frame.rowconfigure(1, weight=1) # Make text widget row expand

        skill_button_frame = ttk.Frame(skill_input_frame)
        skill_button_frame.pack(fill=tk.X, pady=(0,5))
        self.update_skills_button = ttk.Button(skill_button_frame, text="Update Skill List", command=self.update_skills_from_input)
        self.update_skills_button.pack(side=tk.LEFT, padx=(2, 10))
        self.remove_skill_button = ttk.Button(skill_button_frame, text="Remove Selected Skill", command=self.remove_skill)
        self.remove_skill_button.pack(side=tk.LEFT, padx=(2, 5))

        listbox_label = ttk.Label(skill_input_frame, text="Current Required Skills:")
        listbox_label.pack(anchor='w', padx=2, pady=(5,0))
        self.skill_listbox_frame = ttk.Frame(skill_input_frame)
        self.skill_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0,5))
        self.skill_listbox_frame.rowconfigure(0, weight=1) # Make listbox row expand
        self.skill_listbox_frame.columnconfigure(0, weight=1) # Make listbox col expand

        self.skill_scrollbar = ttk.Scrollbar(self.skill_listbox_frame, orient=tk.VERTICAL)
        self.skill_listbox = Listbox(self.skill_listbox_frame, height=5, width=40, relief="solid", borderwidth=1, exportselection=False, yscrollcommand=self.skill_scrollbar.set, font=('Segoe UI', 9))
        self.skill_scrollbar.config(command=self.skill_listbox.yview)
        self.skill_scrollbar.grid(row=0, column=1, sticky='ns')
        self.skill_listbox.grid(row=0, column=0, sticky='nsew')

        # --- Bottom Frame: Evaluation & Results ---
        self.eval_frame = ttk.Frame(main_frame, padding="5 10 5 10")
        self.eval_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(2, weight=1)

        self.evaluate_button = ttk.Button(self.eval_frame, text="Run Analysis", command=self.start_analysis_thread, state=tk.DISABLED, style='Accent.TButton')
        self.evaluate_button.pack(pady=10)

        self.results_frame = ttk.LabelFrame(self.eval_frame, text="Results Log", padding="10")
        self.results_frame.pack(pady=5, padx=0, fill=tk.BOTH, expand=True)
        self.eval_frame.rowconfigure(1, weight=1); self.eval_frame.columnconfigure(0, weight=1)

        self.results_summary_text = scrolledtext.ScrolledText(self.results_frame, height=15, width=80, wrap=tk.WORD, state=tk.DISABLED, relief="solid", borderwidth=1, font=('Consolas', 9))
        self.results_summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status Bar
        self.status_label = ttk.Label(self.master, text="Ready", relief=tk.SUNKEN, anchor=tk.W, padding="5 2")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Custom Style
        self.style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), padding=5)
        self.style.configure('Status.TLabel', foreground='#555555')

    # --- Skill Handling ---
    def update_skills_from_input(self):
        raw_text = self.skill_text_widget.get("1.0", tk.END)
        potential_skills = []
        for line in raw_text.split('\n'):
            potential_skills.extend(part.strip() for part in line.split(',') if part.strip())
        new_skills_lower = {s.lower() for s in potential_skills if s}
        display_skills_dict = {s.lower(): s for s in reversed(potential_skills) if s} # Keep last casing entered
        display_skills = display_skills_dict.values()

        if new_skills_lower != self.required_skills_set:
            logging.info(f"Updating required skills. New set: {new_skills_lower}")
            self.required_skills_set = new_skills_lower
            self.skill_listbox.delete(0, tk.END)
            for skill_display in sorted(list(display_skills), key=str.lower):
                self.skill_listbox.insert(tk.END, skill_display)
            self.update_status(f"Updated required skills list ({len(self.required_skills_set)} skills).")
        else:
             self.update_status("Required skills unchanged.")

    def remove_skill(self):
        selected_indices = self.skill_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a skill from the listbox below to remove.")
            return
        skills_removed_count = 0
        skills_to_remove_lower = set()
        selected_listbox_items = []

        for index in selected_indices:
            skill_in_listbox = self.skill_listbox.get(index)
            selected_listbox_items.append(skill_in_listbox) # Store for removing from text widget
            skills_to_remove_lower.add(skill_in_listbox.lower())

        # Update internal set
        original_set_size = len(self.required_skills_set)
        self.required_skills_set.difference_update(skills_to_remove_lower) # Remove items
        skills_removed_count = original_set_size - len(self.required_skills_set)
        if skills_removed_count > 0:
             logging.info(f"Removed {skills_removed_count} skill(s): {skills_to_remove_lower}")

        # Update listbox (rebuild from set for consistency)
        self.skill_listbox.delete(0, tk.END)
        # Re-create display list from potentially modified set
        # This part is tricky - we lost original casing. Let's rebuild text area first.
        current_text_skills = []
        raw_text = self.skill_text_widget.get("1.0", tk.END)
        for line in raw_text.split('\n'):
             current_text_skills.extend(part.strip() for part in line.split(',') if part.strip())

        # Filter out the removed skills (case-insensitive)
        remaining_display_skills = [s for s in current_text_skills if s.lower() not in skills_to_remove_lower]
        # Update text area
        self.skill_text_widget.delete("1.0", tk.END)
        self.skill_text_widget.insert("1.0", "\n".join(remaining_display_skills)) # Use newline separation
        # Update listbox from remaining display skills (unique, sorted)
        display_map = {s.lower(): s for s in reversed(remaining_display_skills) if s}
        for skill_display in sorted(list(display_map.values()), key=str.lower):
            self.skill_listbox.insert(tk.END, skill_display)

        self.update_status(f"Removed {skills_removed_count} skill(s). {len(self.required_skills_set)} skills remain.")


    # --- File/Folder Browsing ---
    def browse_file(self):
        f_path = filedialog.askopenfilename(title="Select Resume PDF", filetypes=[("PDF Files", "*.pdf")])
        if f_path:
            self.pdf_path = f_path; self.folder_path = None
            base_name = os.path.basename(f_path)
            self.source_label.config(text=f"File: {base_name}")
            self.evaluate_button.config(state=tk.NORMAL); self.update_status(f"Selected File: {base_name}")
            logging.info(f"Selected PDF: {self.pdf_path}"); self.clear_summary()

    def browse_folder(self):
        dir_path = filedialog.askdirectory(title="Select Folder Containing Resumes")
        if dir_path:
            self.folder_path = dir_path; self.pdf_path = None
            self.source_label.config(text=f"Folder: ...{os.sep}{os.path.basename(dir_path)}")
            self.evaluate_button.config(state=tk.NORMAL); self.update_status(f"Selected Folder: {os.path.basename(dir_path)}")
            logging.info(f"Selected Folder: {self.folder_path}"); self.clear_summary()

    # --- Requirements Parsing ---
    def get_user_requirements(self):
        """Parses requirements from the GUI inputs. Returns dict or None on error."""
        self.update_skills_from_input() # Ensure internal set is up-to-date

        requirements = {'required_skills': self.required_skills_set.copy()}
        try:
            min_exp_val = int(self.min_exp_entry.get() or 0)
            if min_exp_val < 0: raise ValueError("Min experience cannot be negative")
            requirements['min_experience'] = min_exp_val
        except ValueError as e: messagebox.showerror("Input Error", f"Minimum Exp must be a non-negative integer.\nError: {e}"); return None
        try:
            pref_exp_str = self.pref_exp_entry.get()
            if pref_exp_str:
                pref_exp_val = int(pref_exp_str)
                if pref_exp_val < 0: raise ValueError("Pref experience cannot be negative")
                requirements['pref_experience'] = pref_exp_val
            else: requirements['pref_experience'] = None
        except ValueError as e: messagebox.showerror("Input Error", f"Preferred Exp must be a non-negative integer (or empty).\nError: {e}"); return None
        logging.info(f"User Requirements parsed: {requirements}")
        return requirements

    # --- Analysis Execution ---
    def start_analysis_thread(self):
         """Starts the analysis process in a separate thread."""
         self.evaluate_button.config(state=tk.DISABLED)
         self.update_status("Starting analysis...")
         self.clear_summary()
         user_req = self.get_user_requirements()
         if user_req is None:
             self.update_status("Invalid requirements."); self.evaluate_button.config(state=tk.NORMAL); return
         analysis_thread = threading.Thread(target=self.run_analysis_logic, args=(user_req,), daemon=True)
         analysis_thread.start()

    def run_analysis_logic(self, user_req):
         """Contains the logic for processing PDFs and running DFA via Camunda API."""
         pdf_files_to_process = []; source_desc = "No source selected."
         if self.folder_path and os.path.isdir(self.folder_path):
             source_desc = f"Analyzing PDFs in folder: {os.path.basename(self.folder_path)}"
             try: pdf_files_to_process = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.lower().endswith(".pdf")]
             except OSError as e: logging.error(f"Folder Error {self.folder_path}: {e}"); messagebox.showerror("Folder Error", f"Could not read folder:\n{e}"); self.update_status("Error reading folder."); self.master.after(0, lambda: self.evaluate_button.config(state=tk.NORMAL)); return
         elif self.pdf_path and os.path.isfile(self.pdf_path):
             source_desc = f"Analyzing single PDF: {os.path.basename(self.pdf_path)}"; pdf_files_to_process.append(self.pdf_path)
         else: messagebox.showwarning("No Source", "Please select a PDF file or folder."); self.update_status("No source selected."); self.master.after(0, lambda: self.evaluate_button.config(state=tk.NORMAL)); return

         self.append_summary(source_desc)
         if not pdf_files_to_process: messagebox.showinfo("No PDFs", "No PDF files found."); self.update_status("No PDFs found."); self.master.after(0, lambda: self.evaluate_button.config(state=tk.NORMAL)); return

         all_results = []
         total_files = len(pdf_files_to_process); processed_count = 0

         for pdf_file in pdf_files_to_process:
             processed_count += 1; filename = os.path.basename(pdf_file)
             self.update_status(f"Processing {processed_count}/{total_files}: {filename}...")
             self.append_summary(f"\n--- Analyzing: {filename} ---")
             individual_result = { "filename": filename, "name": "N/A", "email": None, "phone": None, "education": "N/A", "years_experience": "N/A", "required_skills_found": [], "final_state": "Error" }
             try:
                 resume_text = extract_text_from_pdf(pdf_file)
                 basic_info = extract_basic_info(resume_text)
                 years_experience = extract_years_experience(resume_text)
                 required_skills_from_user = user_req['required_skills']
                 found_user_skills = find_user_skills_in_text(resume_text, required_skills_from_user)
                 individual_result.update({ "name": basic_info["name"], "email": basic_info["email"], "phone": basic_info["phone"], "education": basic_info["education"], "years_experience": years_experience, "required_skills_found": sorted(list(found_user_skills)) })
                 self.append_summary(f"  Name: {basic_info['name']} | Exp: {years_experience} yrs | Skills: {', '.join(found_user_skills) or 'None'}")

                 meets_min_exp = years_experience >= user_req['min_experience']
                 pref_exp_req = user_req['pref_experience']
                 meets_pref_exp = (pref_exp_req is not None and years_experience >= pref_exp_req)
                 skill_symbol = calculate_skill_symbol(found_user_skills, required_skills_from_user, constants)
                 pref_exp_symbol = constants.SYM_PREF_EXP_NA if pref_exp_req is None else (constants.SYM_PREF_EXP_MET if meets_pref_exp else constants.SYM_PREF_EXP_NOT_MET)

                 current_state = constants.S_START
                 max_steps = 10; step = 0; trace = []
                 while current_state not in constants.FINAL_STATES and step < max_steps:
                     step += 1; trace.append(f"S={current_state}")
                     input_symbol = None
                     if current_state == constants.S_START: input_symbol = constants.SYM_PROCESS
                     elif current_state == constants.S_EVAL_MIN_EXP: input_symbol = constants.SYM_MIN_EXP_MET if meets_min_exp else constants.SYM_MIN_EXP_NOT_MET
                     elif current_state == constants.S_EVAL_SKILLS: input_symbol = skill_symbol
                     elif current_state == constants.S_EVAL_PREF_EXP: input_symbol = pref_exp_symbol
                     else: raise RuntimeError(f"Unexpected state '{current_state}'")
                     trace.append(f" -> Sym='{input_symbol}'")
                     # *** Call Camunda Engine Client ***
                     next_state = get_next_state_from_camunda(current_state, input_symbol)
                     trace.append(f" -> Next='{next_state}'")
                     current_state = next_state
                 if step >= max_steps: current_state = "ERROR_LOOP"
                 # self.append_summary(f"     Trace: {' | '.join(trace)}") # Optional trace log
                 self.append_summary(f"  ==> Final State: {current_state}")
                 individual_result["final_state"] = current_state
             except (FileNotFoundError, ValueError, ConnectionError, TimeoutError, RuntimeError, Exception) as e:
                 error_message = f"ERROR processing {filename}: {type(e).__name__} - {e}"
                 logging.error(error_message, exc_info=False) # Log less detail for repetitive errors
                 self.append_summary(f"  ERROR: {e}")
                 individual_result["final_state"] = f"Error: {type(e).__name__}"
             finally: all_results.append(individual_result)

         # --- Write Report ---
         self.update_status("Writing report...")
         try:
             output_filename = config.DEFAULT_REPORT_FILENAME
             self.write_report(all_results, output_filename)
             self.append_summary(f"\n--- Analysis complete. Report saved to: {output_filename} ---")
             self.master.after(0, lambda: messagebox.showinfo("Complete", f"Analysis finished.\nReport saved as '{output_filename}'."))
         except Exception as e:
             logging.error(f"Failed to write report: {e}", exc_info=True)
             self.master.after(0, lambda: messagebox.showerror("Report Error", f"Could not write report file:\n{e}"))
             self.append_summary(f"\n--- ERROR: Failed to write report file ---")

         self.update_status("Analysis complete.")
         self.master.after(0, lambda: self.evaluate_button.config(state=tk.NORMAL)) # Re-enable button

    # --- Reporting ---
    def write_report(self, results_list, output_filename):
        """Writes the structured report to a text file."""
        logging.info(f"Writing analysis report to {output_filename}")
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                for result in results_list:
                    f.write(f"Resume File Name: {result.get('filename', 'N/A')}\n")
                    f.write(f"Candidate Name: {result.get('name', 'Not Found')}\n")
                    edu_text = result.get('education', 'Not Found')
                    f.write(f"Candidate Education:\n  {edu_text}\n") # Indent education
                    if result.get('phone'): f.write(f"Candidate Phone Number: {result.get('phone')}\n")
                    if result.get('email'): f.write(f"Candidate Email: {result.get('email')}\n")
                    f.write(f"Candidate Experience: {result.get('years_experience', 'N/A')} years\n")
                    skills_found_str = ", ".join(result.get('required_skills_found', [])) or "None Required/Found"
                    f.write(f"Found Required Skills: {skills_found_str}\n")
                    status = "Error/Unknown"; state = result.get('final_state', 'Error')
                    if state == constants.S_ACCEPT: status = "Accepted"
                    elif state == constants.S_REJECT: status = "Rejected"
                    elif state == constants.S_REVIEW: status = "Pending Review"
                    elif "Error" in state: status = f"Processing Error ({state})"
                    f.write(f"Candidate Status: {status}\n")
                    f.write("-" * 40 + "\n\n")
        except IOError as e:
            logging.error(f"IOError writing report file {output_filename}: {e}")
            raise