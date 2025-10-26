# ABC Advertising - Roster Processing Tool

This tool processes high school sports roster PDFs and converts them to InDesign tagged text format using AI-powered data extraction.

## Features

- Extracts player and coach information from PDF rosters
- Uses OpenAI GPT to intelligently parse roster data
- Converts player years (Freshman=9, Sophomore=10, etc.)
- Sorts players by jersey number
- Outputs InDesign tagged text format for easy import

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key as an environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Batch Processing (Recommended)

1. Place PDF roster files in the `import` folder
2. Run the script without arguments:
```bash
python main.py
```

The script will:
- Process all PDF files in the `import` folder
- Save InDesign files to `in_design_output` folder
- Move processed PDFs to `complete` folder

### Single File Processing

```bash
python main.py <input_pdf> <output_txt>
```

### Example

```bash
python main.py roster.pdf output.txt
```

## Folder Structure

```
ABC_Advertising/
├── import/              # Place PDF files here
├── complete/            # Processed PDFs moved here
├── in_design_output/    # Generated .txt files for InDesign import
├── main.py
└── requirements.txt
```

## Requirements

- Python 3.7+
- OpenAI API key
- PDF file containing sports roster data

## Output

The script generates `.txt` files that can be imported into InDesign with proper formatting for:
- Player information (number, name, position, height, weight, year)
- Coach information (title, name)
- Proper table formatting for InDesign

### How to Import into InDesign

1. **Open InDesign** and create a new document or open an existing one
2. **Go to File → Place** (or press Ctrl+D / Cmd+D)
3. **Select the .txt file** from the `in_design_output` folder
4. **Click to place** the content in your document
5. **The content will import** with proper paragraph styles and table formatting

**Note**: The .txt files contain InDesign's tagged text format - they cannot be opened directly in InDesign, only imported.

## Cost Tracking

The script displays real-time API usage and cost information:
- Token usage (prompt + completion = total)
- Estimated cost per file processed
- Uses GPT-3.5-turbo pricing: $0.50/1M input tokens, $1.50/1M output tokens

Example output:
```
🤖 Calling OpenAI API...
📊 API Usage - Tokens: 594 prompt + 848 completion = 1442 total
💰 Estimated Cost: $0.0016 ($0.0003 prompt + $0.0013 completion)
```
