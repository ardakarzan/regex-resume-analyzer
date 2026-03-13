# utils/resume_analyzer.py
import re
import logging
import string 

# Regex Patterns

# Email
RE_EMAIL = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'

# Phone
RE_PHONE = r'(\+?\d{1,3}[-.\s]?)?\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?:\s*(?:ext|x|extension)\.?\s*\d+)?\b'

# Experience Years
RE_YEARS_EXP = r'\b(\d{1,2})\+?\s+years?\'?\s+(?:of\s+)?(?:professional\s+|work\s+|hands-on\s+)?(experience|programming|development|engineering|management)\b'
RE_YEARS_EXP_RANGE = r'\b(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s+years?' # 5-7 years, 10–12 years

# Education Keywords
RE_EDUCATION_KEYWORDS = r'^\s*(EDUCATION|ACADEMIC BACKGROUND|QUALIFICATIONS|EDUCATIONAL QUALIFICATIONS|PROFESSIONAL EDUCATION)\b\s*[:\n]?'

# Section End Markers
RE_SECTION_END_MARKERS = r'^\s*(EXPERIENCE|EMPLOYMENT|WORK HISTORY|PROFESSIONAL EXPERIENCE|PROJECTS|SKILLS|TECHNICAL SKILLS|PUBLICATIONS|REFERENCES|AWARDS|CERTIFICATIONS)\b\s*[:\n]?|(?:\n\s*){3,}'

# Name 
# 1.  "Name:" label
RE_NAME_EXPLICIT = r'^\s*(?:name|applicant)\s*[:\-\s]\s*([A-Z][a-zA-Z\s\.\'-]+)\s*$'
# 2. Likely name pattern (Capitalized words, allows '.', '-', ''') - often near top
RE_NAME_PATTERN = r'^\s*([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+|\s+[A-Z]\.?){1,3})\s*$' # 2 to 4 capitalized words


# Education Details Patterns 
# Degree variations 
RE_DEGREE = r'\b(?:(?:Bachelor|Master|Doctor(?:ate)?|Associate)\s+of\s+(?:Science|Arts|Engineering|Business Administration)|B\.?S\.?|M\.?S\.?|Ph\.?D\.?|B\.?A\.?|M\.?B\.?A\.?|A\.?A\.?|A\.?S\.?|B\.?Eng\.?)\b'
# University/College names (multi-word capitalized phrases ending in Uni/College/Inst)
RE_INSTITUTION = r'\b([A-Z][a-zA-Z\s,&]+(?:University|College|Institute|Polytechnic|School))\b'
# Graduation Year/Date 
RE_GRAD_DATE = r'\b(?:(?:Graduat(?:ed|ion)|Expected|Completion)\s*(?:in|date)?\s*:?\s*)?(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+)?(\b(?:19|20)\d{2})\b'

# Filtering 
# Common words unlikely to be a primary name
COMMON_NON_NAMES = {
    'resume', 'curriculum vitae', 'cv', 'profile', 'summary', 'objective', 'contact',
    'experience', 'education', 'skills', 'projects', 'portfolio', 'references',
    'email', 'phone', 'address', 'linkedin', 'github', 'website',
    'engineer', 'developer', 'manager', 'analyst', 'specialist', 'consultant', 'architect',
    'inc', 'llc', 'ltd', 'corp', 'associates',
    'ccna', 'pmp', 'mba', 'cpa', 'phd', 'msc', 'bsc', 
}

# --- Extraction Functions ---

def extract_years_experience(resume_text):
    """Extracts the maximum years of experience mentioned in the text."""
    max_experience = 0
    if not isinstance(resume_text, str): return 0

    # Prioritize specific patterns 
    try:
        matches = re.findall(RE_YEARS_EXP, resume_text, re.IGNORECASE)
        for match_tuple in matches:
            years = int(match_tuple[0])
            if years > max_experience: max_experience = years
    except Exception as e: logging.warning(f"Error in RE_YEARS_EXP matching: {e}")

    # Check ranges take the higher number if no specific value found yet or range is higher
    try:
        range_matches = re.findall(RE_YEARS_EXP_RANGE, resume_text, re.IGNORECASE | re.UNICODE) 
        for match_tuple in range_matches:
            # (start_year, end_year)
            start_years = int(match_tuple[0])
            end_years = int(match_tuple[1])
            if end_years > max_experience: max_experience = end_years
            elif start_years > max_experience: max_experience = start_years # Less likely but possible
    except Exception as e: logging.warning(f"Error in RE_YEARS_EXP_RANGE matching: {e}")

    # Fallback: "years experience" if patterns fail
    if max_experience == 0:
        try:
            generic_matches = re.findall(r'\b(\d{1,2})\s+years?.*?experience\b', resume_text, re.IGNORECASE)
            for year_str in generic_matches:
                 years = int(year_str)
                 if years > max_experience: max_experience = years
        except Exception as e: logging.warning(f"Error in generic year matching: {e}")


    logging.info(f"Extracted years experience: {max_experience}")
    return max_experience

def find_user_skills_in_text(resume_text, required_skills_set):
    found_skills = set()
    if not required_skills_set or not isinstance(resume_text, str): return found_skills
    logging.info(f"Searching for {len(required_skills_set)} skills: {required_skills_set}")
    for skill_to_find in required_skills_set:
        try:
            if not skill_to_find or not isinstance(skill_to_find, str): continue
            pattern = r'\b' + re.escape(skill_to_find) + r'\b'
            # Search in the entire text, case-insensitive
            if re.search(pattern, resume_text, re.IGNORECASE):
                found_skills.add(skill_to_find)
                logging.debug(f"Found required skill: '{skill_to_find}'")
        except re.error as e: logging.warning(f"Regex error searching for skill '{skill_to_find}': {e}")
        except Exception as e: logging.error(f"Unexpected error searching for skill '{skill_to_find}': {e}")
    logging.info(f"Search complete. Found required skills: {found_skills}")
    return found_skills

def extract_basic_info(resume_text):
    info = { "name": "Not Found", "email": None, "phone": None, "education": "Not Found" }
    if not isinstance(resume_text, str) or not resume_text: return info

    # Extract Email 
    try:
        email_match = re.search(RE_EMAIL, resume_text)
        if email_match: info["email"] = email_match.group(0); logging.info(f"Found Email: {info['email']}")
    except Exception as e: logging.warning(f"Error during email extraction: {e}")

    # Extract Phone 
    try:
        phone_match = re.search(RE_PHONE, resume_text)
        if phone_match: info["phone"] = phone_match.group(0); logging.info(f"Found Phone: {info['phone']}")
    except Exception as e: logging.warning(f"Error during phone extraction: {e}")

    # Extract Name 
    potential_names = []
    try:
        # 1. Look for explicit "Name:" 
        name_explicit_match = re.search(RE_NAME_EXPLICIT, resume_text[:300], re.MULTILINE) # Search first few lines
        if name_explicit_match:
            potential_names.append(name_explicit_match.group(1).strip())
            logging.debug(f"Potential name (explicit label): {potential_names[-1]}")

        # 2. Look for pattern matches 
        lines = resume_text.strip().split('\n')
        for line in lines[:5]: # Check first 5 lines
             name_pattern_match = re.match(RE_NAME_PATTERN, line.strip())
             if name_pattern_match:
                 potential_names.append(name_pattern_match.group(1).strip())
                 logging.debug(f"Potential name (top lines pattern): {potential_names[-1]}")

        # 3. Look near email/phone if found
        contact_index = -1
        search_radius = 150 # Characters around contact info
        if info["email"]: contact_index = resume_text.find(info["email"])
        elif info["phone"]: contact_index = resume_text.find(info["phone"])

        if contact_index != -1:
             search_area_contact = resume_text[max(0, contact_index - search_radius):contact_index + search_radius]
             # Find all potential name patterns in this area
             contact_name_matches = re.findall(RE_NAME_PATTERN, search_area_contact, re.MULTILINE)
             for pname in contact_name_matches:
                  potential_names.append(pname.strip())
                  logging.debug(f"Potential name (near contact pattern): {potential_names[-1]}")

        # Filter potential names
        best_name = "Not Found"
        processed_names = set() # Avoid duplicates
        for name in potential_names:
            name_lower = name.lower()
            # Basic checks: not empty, not already processed, not just punctuation/numbers
            if not name or name_lower in processed_names or name.isnumeric() or all(c in string.punctuation for c in name):
                continue
            processed_names.add(name_lower)

            # Filter against common non-names list
            is_common_non_name = False
            for non_name in COMMON_NON_NAMES:
                # Check if potential name contains a common nonname word 
                if re.search(r'\b' + re.escape(non_name) + r'\b', name, re.IGNORECASE):
                    is_common_non_name = True
                    logging.debug(f"Filtering out '{name}' because it contains non-name term '{non_name}'")
                    break
            if is_common_non_name:
                continue

            best_name = name
            logging.info(f"Selected Name: {best_name}")
            break 
        info["name"] = best_name

    except Exception as e: logging.warning(f"Error during name extraction: {e}")

    # Extract Education 
    education_text = "Not Found"
    extracted_details = [] # tuples of (degree, institution, year)
    try:
        # Find start of education section using keywords
        edu_keyword_match = re.search(RE_EDUCATION_KEYWORDS, resume_text, re.IGNORECASE | re.MULTILINE)
        if edu_keyword_match:
            start_index = edu_keyword_match.start()
            logging.debug(f"Found education keyword '{edu_keyword_match.group(0)}' at index {start_index}")

            # Find end of education section ,search after the found keyword
            search_start_for_end = edu_keyword_match.end()
            end_match = re.search(RE_SECTION_END_MARKERS, resume_text[search_start_for_end:], re.IGNORECASE | re.MULTILINE)
            end_index = len(resume_text) # Default to EOF
            if end_match:
                end_index = end_match.start() + search_start_for_end
                logging.debug(f"Found end marker '{end_match.group(0).strip()}' for education at index {end_index}")

            education_chunk = resume_text[start_index:end_index]
            logging.debug(f"Education chunk identified (length {len(education_chunk)}).")

            # Attempt to extract structured details 
            lines_in_chunk = education_chunk.split('\n')
            current_degree = None
            current_institution = None
            current_year = None
            for line in lines_in_chunk:
                line_stripped = line.strip()
                if not line_stripped: continue # Skip empty line

                # Try to find details on this line
                degree_match = re.search(RE_DEGREE, line_stripped, re.IGNORECASE)
                institution_match = re.search(RE_INSTITUTION, line_stripped) 
                year_match = re.search(RE_GRAD_DATE, line_stripped)

                # Combine info
                degree = degree_match.group(0) if degree_match else None
                institution = institution_match.group(1) if institution_match else None # Group 1 captures name
                year = year_match.group(1) if year_match else None # Group 1 captures YYYY

                # If we find a degree, start a new potential entry
                if degree:
                    # If we had a previous entry nearly complete, save it
                    if current_institution or current_year:
                         extracted_details.append((current_degree or "Degree?", current_institution or "Institution?", current_year))
                    # Start new entry
                    current_degree = degree
                    current_institution = institution # Might be on same line
                    current_year = year
                # If no degree on this line, but maybe institution or year, add to current entry
                elif institution and not current_institution:
                     current_institution = institution
                elif year and not current_year:
                     current_year = year

            # Add the last collected entry if any parts were found
            if current_degree or current_institution or current_year:
                 extracted_details.append((current_degree or "Degree?", current_institution or "Institution?", current_year))

            # Format the extracted details for the report
            if extracted_details:
                formatted_edu = []
                for deg, inst, yr in extracted_details:
                    entry = f"- {deg}"
                    if inst and inst != "Institution?": entry += f" from {inst}"
                    if yr: entry += f" ({yr})"
                    formatted_edu.append(entry)
                education_text = "\n  ".join(formatted_edu) # Indent each entry
                logging.info(f"Formatted Education Details: {education_text}")
            else:
                 # Fallback: If no structured details found, provide raw chunk (limited)
                 education_lines = [line.strip() for line in education_chunk.split('\n') if line.strip()]
                 education_text = "\n  ".join(education_lines[:6]) # Limit lines
                 if len(education_lines) > 6: education_text += "\n  ..."
                 if not education_text: education_text = "Section keyword found, but no content extracted."
                 logging.info("Could not extract structured education details, using chunk.")
        else:
            logging.info("Education keyword not found.")

    except Exception as e:
        logging.warning(f"Could not reliably extract education section: {e}", exc_info=True)
        education_text = "Error during extraction."

    info["education"] = education_text
    return info


def calculate_skill_symbol(found_user_skills_set, required_user_skills_set, constants):
    if not required_user_skills_set: return constants.SYM_SKILLS_NA
    required_lower = {s.lower() for s in required_user_skills_set}
    found_lower = {s.lower() for s in found_user_skills_set}
    found_count = len(required_lower.intersection(found_lower))
    total_required = len(required_lower)
    if total_required == 0: return constants.SYM_SKILLS_NA
    if found_count == total_required: return constants.SYM_SKILLS_ALL
    elif found_count > 0: return constants.SYM_SKILLS_PARTIAL
    else: return constants.SYM_SKILLS_NONE