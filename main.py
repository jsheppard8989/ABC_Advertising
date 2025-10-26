import pdfplumber, openai, re, os, shutil, json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Optional image support
try:
    import pytesseract
    from PIL import Image
    HAS_IMAGE_SUPPORT = True
except ImportError:
    HAS_IMAGE_SUPPORT = False

# Setup
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Constants for efficiency
SUPPORTED_IMAGE_EXTS = {}  # Images not directly supported - convert to PDF first
AI_PROMPT_TEMPLATE = (
    "CRITICAL: Transfer data accurately from the source text. Do not modify opponent names, dates, or times unless specifically instructed. "
    "Analyze this text and determine if it contains roster data or schedule data. Return JSON with 'type' field ('roster' or 'schedule') and appropriate data structure. "
    "\n\nFor ROSTERS: Return 'teams' array where each team has: {{sport, players, coaches}}. "
    "IMPORTANT: If a document contains both VARSITY and JV (Junior Varsity) teams, create SEPARATE team entries for each. "
    "For example: 'Varsity Volleyball' and 'JV Volleyball' should be two different teams in the array. "
    "The sport name should clearly distinguish the team level: 'Varsity Volleyball', 'JV Volleyball', 'Freshman Volleyball', etc. "
    "Players: {{number, name, position, height, weight, year}}. Convert years: Freshman/F/FR/fresh=09, Sophomore/SO/soph=10, Junior/JR/junior=11, Senior/SR/senior=12. "
    "The heading for the final output file need to be abbreviated, for example Number = No.  Name = Name, Height = Ht., Weight = Wt., Position = Pos., Year = Yr."
    "All grades should be converted to two digits (e.g. '9' should be '09').  If players name is followed by 'freshman' then the year should be '09'. If the players name is followed by 'sophomore' then the year should be 10. If the players name is followed by 'junior' then the year should be 11. If the players name is followed by 'senior' then the year should be 12. " 
    "Use first number if player has two (e.g. '45/80'). Sort players by jersey number (lowest to highest). "
        "CRITICAL FOR EXCEL PDFs: The source text may contain headers and contact info mixed with player data (e.g. 'Name Email Phone' or addresses in the middle of player rows). "
        "IGNORE these extraneous lines. Focus on extracting complete player rows that have: name, number, height, weight, position, and grade/year. "
        "Skip any lines that are clearly headers, footers, contact info, or administrative text. Only extract valid player entries. "
        "Coaches: {{title, name}}. "
        "\n\nFor SCHEDULES: Return 'schedules' array where each schedule has: {{sport, games}}. "
    "Games: {{date, opponent (Level), and time}}. "
    "ACCURACY REQUIREMENT: Use the exact opponent names from the source text. Do not substitute or change opponent names. "
    "EXAMPLE: If the source shows 'Home vs Forreston' then output 'FORRESTON' (not Stockton or any other name). "
    "EXAMPLE: If the source shows 'Away @ Milledgeville' then output 'at Milledgeville'. "
    "For dates, 11/28/2025 should be displayed as 'Nov 28'. If a tournament covers multiple days use 'Nov 29-31'. "
    "If the Location is 'Home' then make the opponent name ALL CAPITAL LETTERS. For example 'Home vs Stockton' should be 'STOCKTON'. "
    "If the location is 'Away' then return 'at Opponent'. The opponent could be a city, school, team name or tournament name. "
    "Following the opponent name, pdfs may describe the level such as F, FS, JV, Var, and sometimes B/G for boys or girls. Keep this information in abbreviated form. "
    "Also sometimes following opponent names may be H for Homecoming or S for Senior Night. Keep this information in abbreviated form. "
    "Time format should be HH:MM AM/PM. If there are multiple times on the same day use the earliest time. "
    "Sort games by date (earliest first). "
    "MANDATORY ABBREVIATIONS: Always abbreviate 'Tournament' as 'Tourney'. Always abbreviate 'Varsity' as 'V'. Always abbreviate 'Junior Varsity' as 'JV'. "
    "If the pdf specifies the game is JV and Varsity, the InDesign document should show (JV/V). "
    "CRITICAL: Replace ALL instances of 'Varsity' with 'V' in the output. Never leave 'Varsity' unchanged. "
    "For home games, opponent names must be in ALL CAPITAL LETTERS."
    "\n\nSport names should be descriptive if the information is provide in the pdf (e.g. 'Football', 'Varisity Boys Basketball', 'JV Girls Volleyball'). "
    "If multiple sports/teams, return separate entries for each.\n\n{}"
)

def call_ai_agent(text):
    """Extract roster or schedule data using OpenAI"""
    prompt = AI_PROMPT_TEMPLATE.format(text)
    
    print("🤖 Calling OpenAI API...")
    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Extract structured roster data. Return valid JSON only."}, {"role": "user", "content": prompt}],
        temperature=0.1, max_tokens=3000
    )
    
    # Print usage and trace info
    usage = response.usage
    print(f"📊 API Usage - Tokens: {usage.prompt_tokens} prompt + {usage.completion_tokens} completion = {usage.total_tokens} total")
    prompt_cost = usage.prompt_tokens * 0.0005 / 1000
    completion_cost = usage.completion_tokens * 0.0015 / 1000
    total_cost = prompt_cost + completion_cost
    print(f"💰 Estimated Cost: ${total_cost:.4f} (${prompt_cost:.4f} prompt + ${completion_cost:.4f} completion)")
    
    if hasattr(response, 'id'):
        print(f"🔗 Trace Link: https://platform.openai.com/playground?assistant={response.id}")
        print(f"📋 Request ID: {response.id}")
    else:
        print("🔗 Trace Link: https://platform.openai.com/usage (check your OpenAI dashboard)")
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Raw AI response: {response.choices[0].message.content[:500]}...")
        
        # Try to fix common JSON issues
        content = response.choices[0].message.content
        
        # Remove any trailing commas before closing braces/brackets
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Try to complete truncated JSON by adding missing closing braces
        if content.count('{') > content.count('}'):
            missing_braces = content.count('{') - content.count('}')
            content += '}' * missing_braces
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If still failing, try to extract partial data
            print("⚠️  Attempting to extract partial data from malformed JSON...")
            try:
                # Look for the first complete team object
                team_match = re.search(r'\{[^{}]*"sport"[^{}]*"players"[^{}]*\}[^{}]*\}', content, re.DOTALL)
                if team_match:
                    partial_json = team_match.group(0)
                    return json.loads(partial_json)
            except Exception:
                pass
            print("❌ Could not parse AI response as JSON")
            raise

# Player sorting now handled by AI

# Field name mappings for display (abbreviated headers)
FIELD_DISPLAY_NAMES = {
    'number': 'No.',
    'name': 'Name',
    'position': 'Pos.',
    'height': 'Ht.',
    'weight': 'Wt.',
    'year': 'Yr.'
}

def get_field_display_name(field):
    """Get the abbreviated display name for a field"""
    return FIELD_DISPLAY_NAMES.get(field, field.title())

def make_indesign_tagged_roster(players, coaches, fields):
    """Generate InDesign tagged text format for rosters"""
    result = ["<ASCII-MAC>\n"]
    # Use abbreviated field names for headers
    display_headers = [get_field_display_name(f) for f in fields]
    result.append("<ParaStyle:Table Header>" + "\t".join(display_headers) + "\n")
    
    for p in players:
        row = [str(p.get(f, "")) for f in fields]
        result.append("<ParaStyle:Table Row>" + "\t".join(row) + "\n")
    
    if coaches:
        result.append("\n<ParaStyle:Coach Header>Coaches\n")
        for c in coaches:
            title, name = c.get("title", ""), c.get("name", "")
            if title or name:
                result.append(f"<ParaStyle:Coach Row>{title} {name}\n")
    
    return ''.join(result)

def make_indesign_tagged_schedule(games, fields):
    """Generate InDesign tagged text format for schedules with aligned columns"""
    result = ["<ASCII-MAC>\n"]
    
    # Find the longest opponent name to determine tab spacing
    max_opponent_length = 0
    for game in games:
        opponent = str(game.get("opponent", ""))
        max_opponent_length = max(max_opponent_length, len(opponent))
    
    # Add some padding for better alignment
    tab_width = max_opponent_length + 3
    
    # Header row with proper spacing - align Time header with times column
    # The structure is: Date \t Opponent \t Time
    # We need to pad the "Time" header to align with where times start
    result.append("<ParaStyle:Table Header>Date\tOpponent\t" + "Time".ljust(tab_width) + "\n")
    
    # Game rows with aligned columns
    for game in games:
        row_parts = []
        for field in fields:
            value = str(game.get(field, ""))
            if field == "opponent":
                # Pad opponent name to align times
                padded_opponent = value.ljust(tab_width)
                row_parts.append(padded_opponent)
            else:
                row_parts.append(value)
        
        result.append("<ParaStyle:Table Row>" + "\t".join(row_parts) + "\n")
    
    return ''.join(result)


def extract_text_from_image(image_path):
    """Extract text from an image file using OCR"""
    if not HAS_IMAGE_SUPPORT:
        print(f"❌ Image processing not available. Install pytesseract and Pillow:")
        print(f"   pip3 install pytesseract Pillow")
        print(f"   macOS: brew install tesseract")
        return ""
    
    try:
        with Image.open(image_path) as image:
            return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        print(f"❌ Tesseract OCR not found. Please install it:")
        print(f"   macOS: brew install tesseract")
        print(f"   Linux: sudo apt-get install tesseract-ocr")
        print(f"   Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        return ""
    except Exception as e:
        print(f"❌ Error extracting text from image: {str(e)}")
        return ""

def process_single_file(file_path, output_folder):
    """Process one PDF or image file and create InDesign output files for each team/schedule"""
    try:
        file_ext = Path(file_path).suffix.lower()
        
        # Extract text based on file type
        if file_ext == '.pdf':
            print(f"📄 Processing PDF: {file_path.name}")
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif file_ext in SUPPORTED_IMAGE_EXTS:
            print(f"⚠️  Image files (PNG, JPG, etc.) are not directly supported.")
            print(f"   Please convert the image to PDF first using:")
            print(f"   - Preview (macOS): Open image → File → Export as PDF")
            print(f"   - Online converter")
            print(f"   Then process the PDF file.")
            return [], False
        else:
            print(f"⚠️  Unsupported file type: {file_ext}")
            return [], False
        
        # Parse data with AI
        data = call_ai_agent(text)
        
        # Debug: Check data type
        if not isinstance(data, dict):
            print(f"⚠️  AI returned non-dict data: {type(data)} - {str(data)[:200]}")
            return [], False
        
        doc_type = data.get("type", "unknown")
        
        if doc_type == "roster":
            return process_roster_data(data, file_path, output_folder)
        elif doc_type == "schedule":
            return process_schedule_data(data, file_path, output_folder)
        else:
            print(f"⚠️  Unknown document type in {file_path}")
            return [], False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return [], False

def normalize_player_data(player):
    """Normalize player data keys to lowercase standard format"""
    # Map common variations to standard keys
    key_mapping = {
        'No.': 'number', 'no.': 'number', 'number': 'number',
        'Name': 'name', 'name': 'name', 'player': 'name',
        'Pos.': 'position', 'pos.': 'position', 'position': 'position',
        'Ht.': 'height', 'ht.': 'height', 'height': 'height',
        'Wt.': 'weight', 'wt.': 'weight', 'weight': 'weight',
        'Yr.': 'year', 'yr.': 'year', 'year': 'year', 'grade': 'year'
    }
    
    normalized = {}
    for key, value in player.items():
        # Convert key to standard lowercase
        standard_key = key_mapping.get(key, key.lower())
        normalized[standard_key] = value
    return normalized

def process_roster_data(data, pdf_path, output_folder):
    """Process roster data and create InDesign files"""
    teams = data.get("teams", [])
    
    print(f"🔍 Debug: Found {len(teams)} team(s) in AI response")
    for i, team in enumerate(teams):
        if not isinstance(team, dict):
            print(f"⚠️  Team {i+1} is not a dict: {type(team)} - {str(team)[:100]}")
            continue
        sport = team.get("sport", "unknown")
        player_count = len(team.get("players", []))
        print(f"   Team {i+1}: '{sport}' with {player_count} players")
    
    if not teams:
        print(f"⚠️  No teams found in {pdf_path}")
        return [], False
    
    date_str = datetime.now().strftime("%m_%d_%Y")
    pdf_stem = Path(pdf_path).stem
    created_files = []
    
    for team in teams:
        sport = team.get("sport", "unknown").lower().replace(" ", "_")
        players = team.get("players", [])
        coaches = team.get("coaches", [])
        
        if not players:
            print(f"⚠️  No players found for {sport} team")
            continue
        
        # Normalize player data keys
        players = [normalize_player_data(p) for p in players]
        
        # AI already sorted players by jersey number
        all_fields = ["number", "name", "position", "height", "weight", "year"]
        fields_present = [f for f in all_fields if any(p.get(f) for p in players)] or ["name"]
        tagged = make_indesign_tagged_roster(players, coaches, fields_present)
        
        output_filename = f"{pdf_stem}_{sport}_roster_{date_str}.txt"
        output_path = output_folder / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tagged)
        
        print(f"✅ Exported {sport} roster to {output_filename}")
        created_files.append(output_filename)
    
    if created_files:
        print(f"📄 Created {len(created_files)} roster file(s): {', '.join(created_files)}")
        return created_files, True
    else:
        print(f"⚠️  No valid rosters found in {pdf_path}")
        return [], False

def process_schedule_data(data, pdf_path, output_folder):
    """Process schedule data and create InDesign files"""
    schedules = data.get("schedules", [])
    
    if not schedules:
        print(f"⚠️  No schedules found in {pdf_path}")
        return [], False
    
    date_str = datetime.now().strftime("%m_%d_%Y")
    pdf_stem = Path(pdf_path).stem
    created_files = []
    
    for schedule in schedules:
        sport = schedule.get("sport", "unknown").lower().replace(" ", "_")
        games = schedule.get("games", [])
        
        if not games:
            print(f"⚠️  No games found for {sport} schedule")
            continue
        
        # AI already sorted games by date
        all_fields = ["date", "opponent", "location", "time", "home_away"]
        fields_present = [f for f in all_fields if any(g.get(f) for g in games)] or ["date", "opponent"]
        tagged = make_indesign_tagged_schedule(games, fields_present)
        
        output_filename = f"{pdf_stem}_{sport}_schedule_{date_str}.txt"
        output_path = output_folder / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tagged)
        
        print(f"✅ Exported {sport} schedule to {output_filename}")
        created_files.append(output_filename)
    
    if created_files:
        print(f"📄 Created {len(created_files)} schedule file(s): {', '.join(created_files)}")
        return created_files, True
    else:
        print(f"⚠️  No valid schedules found in {pdf_path}")
        return [], False

def process_pdfs(files=None, output_folder="in_design_output"):
    """Process PDF and image files - batch mode if no files specified, single file mode if files provided"""
    folders = [Path("import"), Path("complete"), Path(output_folder)]
    for folder in folders:
        folder.mkdir(exist_ok=True)
    
    # If no files specified, process all PDFs and images in import folder
    if files is None:
        import_dir = Path("import")
        pdf_files = list(import_dir.glob("*.pdf"))
        image_files = [f for f in import_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTS]
        files = pdf_files + image_files
        
        if not files:
            print("📁 No PDF or image files found in the 'import' folder.")
            return
        print(f"🔍 Found {len(files)} file(s) to process...")
    else:
        # Single file mode - ensure it exists
        if not os.path.exists(files[0]):
            print(f"Error: Input file '{files[0]}' not found.")
            return False
        print(f"🔄 Processing single file: {files[0]}")
    
    processed_count = 0
    all_created_files = []
    
    for file in files:
        print(f"\n📄 Processing: {file.name}")
        
        created_files, success = process_single_file(file, Path(output_folder))
        if success:
            all_created_files.extend(created_files)
            # Move to complete folder after successful processing
            shutil.move(str(file), str(Path("complete") / file.name))
            print(f"📁 Moved {file.name} to 'complete' folder")
            processed_count += 1
        else:
            print(f"⚠️  Skipped {file.name} due to processing error")
    
    print(f"\n🎉 Processing complete! {processed_count}/{len(files)} files processed successfully.")
    if files is None or len(files) > 1:
        print(f"📁 Processed files moved to: complete")
    print(f"📄 InDesign files saved to: {output_folder}")
    print(f"🔢 TOTAL FILES CREATED IN THIS RUN: {len(all_created_files)}")
    
    # Write the count to a file that the launcher can read
    with open(".file_count", "w") as f:
        f.write(str(len(all_created_files)))
    
    return len(all_created_files)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # Batch processing mode
        print("🔄 Starting batch processing mode...")
        process_pdfs()
    elif len(sys.argv) == 3:
        # Single file processing mode
        input_pdf, output_folder = sys.argv[1], sys.argv[2]
        process_pdfs([Path(input_pdf)], output_folder)
    else:
        print("Usage:")
        print("  Batch mode:     python main.py")
        print("  Single file:    python main.py <input_file> <output_folder>")
        print("")
        print("Batch mode processes all PDF and image files in the 'import' folder")
        print("and saves InDesign files to 'in_design_output' folder.")
        print("Supports both ROSTERS and SCHEDULES:")
        print("  - Rosters: Creates separate files for each sport")
        print("  - Schedules: Creates separate files for each sport")
        print("  - Multiple sports in one file will create separate files for each sport.")
        print("Supported file formats: PDF, PNG, JPG, JPEG, BMP, TIFF, GIF")
        sys.exit(1)