#!/bin/bash

# ABC Advertising Roster & Schedule Processor
# Desktop launcher script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        osascript -e 'display dialog "Python not found. Please install Python to run this application." buttons {"OK"} default button "OK"'
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Check if import folder exists and has PDF files
if [ ! -d "import" ]; then
    mkdir -p import
fi

PDF_COUNT=$(find import -name "*.pdf" -type f | wc -l)

if [ $PDF_COUNT -eq 0 ]; then
    osascript -e 'display dialog "No PDF files found in the import folder. Please add roster or schedule PDF files to the import folder and try again." buttons {"OK"} default button "OK"'
    exit 1
fi

# Show processing dialog
osascript -e 'display dialog "Found '$PDF_COUNT' PDF file(s) to process. Click OK to start processing rosters and schedules." buttons {"Cancel", "Process"} default button "Process"'

if [ $? -ne 0 ]; then
    exit 0
fi

# Run the Python script
echo "Starting ABC Advertising Roster & Schedule Processor..."
echo "Processing $PDF_COUNT PDF file(s)..."

# Run the main script
$PYTHON_CMD main.py

# Check if processing was successful
if [ $? -eq 0 ]; then
    # Count output files
    OUTPUT_COUNT=$(find in_design_output -name "*.txt" -type f | wc -l)
    osascript -e 'display dialog "Processing complete! Created '$OUTPUT_COUNT' InDesign file(s) in the in_design_output folder." buttons {"OK"} default button "OK"'
    
    # Open the output folder
    open in_design_output
else
    osascript -e 'display dialog "Processing failed. Please check the terminal for error details." buttons {"OK"} default button "OK"'
fi



