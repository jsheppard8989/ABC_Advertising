#!/bin/bash

# Create desktop shortcut for ABC Roster Processor

DESKTOP_PATH="$HOME/Desktop"
PROJECT_PATH="/Users/jaredsheppard/no_more_typing/ABC_Advertising"

echo "Creating desktop shortcut..."

# Create a symbolic link to the app on the desktop
ln -sf "$PROJECT_PATH/ABC Roster Processor.app" "$DESKTOP_PATH/ABC Roster Processor.app"

echo "Desktop shortcut created!"
echo "You can now double-click 'ABC Roster Processor' on your desktop to run the program."
echo ""
echo "Instructions:"
echo "1. Drop PDF roster or schedule files into the 'import' folder"
echo "2. Double-click the desktop icon"
echo "3. Click 'Process' when prompted"
echo "4. Find your InDesign files in the 'in_design_output' folder"



