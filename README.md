# Checklist App

This is a Python Qt-based standalone app for managing project-linked notes, to-do lists, and task logs. It allows you to create, edit, and save checklists for different projects locally.

## Features
- Create and manage projects
- Add, edit, and delete tasks/notes for each project
- Save all data locally (JSON files)
- Simple, user-friendly Qt interface

## Setup

1. Ensure you have Python 3.8+ installed.
2. (Recommended) Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install PyQt5
   ```
4. Run the app:
   ```powershell
   python main.py
   ```

## File Structure
- `main.py` - Main application entry point
- `models.py` - Data models for projects and tasks
- `storage.py` - Handles saving/loading data
- `ui_main.py` - Qt UI code

---

Feel free to extend the app as needed!
