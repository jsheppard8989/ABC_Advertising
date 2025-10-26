# ABC Roster Processor - Desktop Launcher

## 🖥️ Desktop Icon Created!

You now have a desktop shortcut called **"ABC Roster Processor"** that you can double-click to run your roster and schedule processing program.

## 📋 How to Use

### **Step 1: Add PDF Files**
- Drop your PDF roster or schedule files into the `import/` folder
- The program supports both rosters and schedules automatically

### **Step 2: Run the Program**
- Double-click the **"ABC Roster Processor"** icon on your desktop
- Click **"Process"** when prompted
- The program will automatically detect and process all PDFs

### **Step 3: Get Your Files**
- Processed files will be saved to the `in_design_output/` folder
- Files are named: `SchoolName_sport_roster_MM_DD_YYYY.txt` or `SchoolName_sport_schedule_MM_DD_YYYY.txt`
- The output folder will open automatically when processing is complete

## 🎯 What It Does

- **Automatically detects** if PDFs contain rosters or schedules
- **Processes multiple sports** in one PDF (creates separate files for each)
- **Formats data perfectly** for InDesign import
- **Handles all variations** of grade levels, team names, and formatting
- **Shows progress** and completion status

## 📁 File Structure

```
ABC_Advertising/
├── import/              # Drop PDF files here
├── complete/            # Processed PDFs moved here
├── in_design_output/    # Generated InDesign files
├── ABC Roster Processor.app  # Desktop launcher
└── main.py             # Main processing script
```

## 🔧 Troubleshooting

- **"Python not found"**: Install Python from python.org
- **"No PDF files found"**: Make sure PDFs are in the `import/` folder
- **Processing fails**: Check that PDFs contain readable text (not scanned images)

## 🚀 Ready to Use!

Just drop your PDFs in the `import/` folder and double-click the desktop icon!



