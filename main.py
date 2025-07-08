
import sys
import random
import string
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QLabel, QMessageBox,
    QInputDialog, QListWidget, QListWidgetItem, QHeaderView, QMenu, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QTimer
import storage

try:
    import colorama
    colorama.init()
    from colorama import Fore, Style
except ImportError:
    # fallback: define dummy Fore/Style
    class Dummy:
        RESET_ALL = ''
    class DummyFore(Dummy):
        GREEN = YELLOW = RED = CYAN = MAGENTA = GREY = ''
    Fore = DummyFore()
    Style = Dummy()

import re

def cprint(*args, **kwargs):
    text = ' '.join(str(a) for a in args)
    # List of (pattern, color) tuples, multi-character patterns first
    patterns = [
        (r'[><]', Fore.LIGHTYELLOW_EX),
        (r'\+', Fore.YELLOW),
        (r'=', Fore.YELLOW),
        (r'-', Fore.YELLOW),
        (r'!', Fore.RED),
        (r'\|', Fore.YELLOW),
        (r'DEBUG', Fore.GREEN),
    ]
    for pat, color in patterns:
        text = re.sub(pat, lambda m: color + m.group(0) + Style.RESET_ALL, text)
    print(text, **kwargs)

# Word wrap delegate for Task/Note column
class WordWrapDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
    def paint(self, painter, option, index):
        option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter
        option.textElideMode = Qt.ElideNone
        option.wrapMode = True
        super().paint(painter, option, index)
    def sizeHint(self, option, index):
        option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter
        option.textElideMode = Qt.ElideNone
        option.wrapMode = True
        return super().sizeHint(option, index)

class ChecklistApp(QMainWindow):
    def _wrap_with_marker(self, text, marker='↪ '):
        """
        Wrap text for display in the Task/Note column, adding a marker to wrapped lines.
        Uses the actual column width and font metrics for accurate wrapping.
        Accounts for cell padding and marker width.
        """
        from PyQt5.QtGui import QFontMetrics
        col = 2
        if not hasattr(self, 'task_list'):
            return text
        col_width = self.task_list.columnWidth(col)
        # Subtract a margin for padding, scrollbar, etc.
        margin = 30  # pixels, adjust as needed
        avail_width = max(10, col_width - margin)
        font = self.task_list.font()
        metrics = QFontMetrics(font)
        marker_width = metrics.width(marker)
        lines = text.splitlines() if '\n' in text else [text]
        wrapped = []
        for line in lines:
            if not line:
                wrapped.append("")
                continue
            current = ""
            first_line = True
            for word in line.split(' '):
                if not current:
                    current = word
                else:
                    # Use less width for wrapped lines (marker included)
                    width_limit = avail_width if first_line else avail_width - marker_width
                    if metrics.width(current + ' ' + word) > width_limit:
                        wrapped.append(current)
                        current = marker + word
                        first_line = False
                    else:
                        current += ' ' + word
            wrapped.append(current)
        return '\n'.join(wrapped)
    def get_contrasting_font_color(self, bg_hex):
        """
        Given a background hex color, return '#000000' or '#ffffff' for best contrast.
        """
        if not bg_hex or not isinstance(bg_hex, str):
            return '#000000'
        hex_color = bg_hex.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except Exception:
            return '#000000'
        # Per W3C luminance formula
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return '#000000' if luminance > 0.5 else '#ffffff'
    def refreshProjectTab(self, selected_project_id=None):
        """
        Refreshes the project list UI and updates the project label and task list to match the current selection.
        If selected_project_id is provided, selects and loads that project. Otherwise, keeps the current selection.
        """
        cprint("[DEBUG] refreshProjectTab called. selected_project_id:", selected_project_id)
        self.refresh_project_list(selected_project_id=selected_project_id)
        QApplication.processEvents()
        idx = self.project_list.currentRow()
        cprint(f"[DEBUG] After refresh, currentRow is {idx}, project count is {self.project_list.count()}")
        if idx >= 0 and idx < self.project_list.count():
            cprint(f"[DEBUG] Loading project at row {idx}")
            self.load_project(idx)
        else:
            cprint("[DEBUG] No project selected after refresh.")
            self.current_project = None
            self.project_label.setText("No project selected")
            self.task_list.setRowCount(0)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist")
        # Set window icon (top left)
        import os
        from PyQt5.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'checklist_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 850)
        self.current_project = None
        self.init_ui()

    def load_all_projects(self):
        import os, json
        projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
        projects = []
        cprint(f"[DEBUG] Looking for projects in: {projects_dir}")
        if os.path.exists(projects_dir):
            for fname in os.listdir(projects_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(projects_dir, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            proj = json.load(f)
                            if isinstance(proj, dict) and 'id' in proj and 'name' in proj:
                                if 'favourite' not in proj:
                                    proj['favourite'] = False
                                projects.append({'id': proj['id'], 'name': proj['name'], 'favourite': proj['favourite']})
                                cprint(f"[DEBUG] Loaded project: {proj['name']} (ID: {proj['id']})")
                    except Exception as e:
                        cprint(f"[DEBUG] Failed to load {fpath}: {e}")
        cprint(f"[DEBUG] Total projects loaded: {len(projects)}")
        return projects



    def init_ui(self):
        import os, json
        from PyQt5.QtWidgets import QTextEdit
        # --- Main widget and layout ---
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # --- Theme selection bar ---
        theme_bar = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_bar.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.themes = {}
        self.last_theme = None
        self._themes_path = os.path.join(os.path.dirname(__file__), 'themes.json')
        if os.path.exists(self._themes_path):
            try:
                with open(self._themes_path, 'r', encoding='utf-8') as f:
                    all_themes = json.load(f)
                if isinstance(all_themes, dict) and 'last_theme' in all_themes:
                    self.last_theme = all_themes.pop('last_theme')
                self.themes = all_themes
                self.theme_combo.addItems(list(self.themes.keys()))
            except Exception:
                self.themes = {}
        else:
            self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.currentIndexChanged.connect(self.apply_theme)
        theme_bar.addWidget(self.theme_combo)
        custom_theme_btn = QPushButton("Custom Theme")
        custom_theme_btn.setToolTip("Create or edit a custom theme")
        custom_theme_btn.clicked.connect(self.open_custom_theme_dialog)
        theme_bar.addWidget(custom_theme_btn)
        theme_bar.addStretch(1)
        main_layout.addLayout(theme_bar)

        # Set theme combo to last used theme if available
        if self.last_theme and self.last_theme in self.themes:
            idx = list(self.themes.keys()).index(self.last_theme)
            self.theme_combo.setCurrentIndex(idx)

        # --- Main content area (horizontal split) ---
        content_layout = QHBoxLayout()

        # --- Project area (sidebar) ---
        project_area = QVBoxLayout()
        self.project_label_widget = QLabel("Projects")
        project_area.addWidget(self.project_label_widget)
        new_project_btn = QPushButton("New Project")
        new_project_btn.clicked.connect(self.new_project)
        project_area.addWidget(new_project_btn)
        self.project_list = QListWidget()
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self.open_project_context_menu)
        self.project_list.currentRowChanged.connect(self.load_project)
        project_area.addWidget(self.project_list)
        project_widget = QWidget()
        project_widget.setLayout(project_area)
        content_layout.addWidget(project_widget, 1)

        # --- Right area (tasks/notes) ---
        right_layout = QVBoxLayout()
        self.project_label = QLabel("No project selected")
        right_layout.addWidget(self.project_label)

        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sort by:")
        sort_layout.addWidget(sort_label)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Status", "Alphanumeric", "Oldest"])
        self.sort_combo.currentIndexChanged.connect(self.sort_tasks_by_mode)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch(1)
        right_layout.addLayout(sort_layout)

        self.task_list = QTableWidget(0, 4)
        self.task_list.setHorizontalHeaderLabels(["", "", "Task/Note", "Status"])
        self.task_list.setColumnWidth(0, 32)
        self.task_list.setColumnWidth(1, 32)
        self.task_list.setColumnWidth(3, 100)
        self.task_list.verticalHeader().setVisible(False)
        self.task_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_list.setSelectionMode(QTableWidget.SingleSelection)
        self.task_list.cellClicked.connect(self.handle_table_click)
        self.task_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.open_context_menu)
        self.task_list.setWordWrap(True)
        header = self.task_list.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.task_list.setItemDelegateForColumn(2, WordWrapDelegate(self.task_list))
        right_layout.addWidget(self.task_list, 4)

        task_input_layout = QHBoxLayout()
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("Add a new task or note... (multi-line supported)")
        self.task_input.setFixedHeight(100)
        task_input_layout.addWidget(self.task_input)
        add_task_btn = QPushButton("Add")
        add_task_btn.clicked.connect(self.add_task)
        task_input_layout.addWidget(add_task_btn)
        right_layout.addLayout(task_input_layout)

        content_layout.addLayout(right_layout, 3)
        main_layout.addLayout(content_layout)
        self.setCentralWidget(main_widget)

        # --- Populate project list and select first project if available ---
        self._startup_refreshed = False
        self.refresh_project_list()
        self._startup_refreshed = True

        from PyQt5.QtCore import QTimer
        if self.project_list.count() > 0 and self.project_list.currentRow() == -1:
            def select_and_load():
                self.project_list.setCurrentRow(0)
                self.load_project(0)
            QTimer.singleShot(0, select_and_load)

        # --- Apply theme after all widgets are created ---
        self.apply_theme()

    def open_custom_theme_dialog(self):
        import os, json
        from custom_theme_dialog import CustomThemeDialog
        theme_params = [
            ("UIBackground", "Main background"),
            ("FontColor", "Main font color"),
            ("TabBackground", "Sidebar/tab background"),
            ("TabFontColor", "Sidebar/tab font color"),
            ("ButtonBackground", "Button background"),
            ("ButtonFontColor", "Button font color"),
            ("PendingBackground", "Pending status background"),
            ("WIPBackground", "WIP status background"),
            ("DoneBackground", "Done status background"),
        ]
        current_theme = self.themes.get(self.theme_combo.currentText(), {})
        param_values = {k: current_theme.get(k, "#ffffff") for k, _ in theme_params}
        dlg = CustomThemeDialog(self, theme_params, param_values, self.get_contrasting_font_color, self._themes_path)
        dlg.exec_()
        # After dialog closes, reload themes and update dropdown
        if os.path.exists(self._themes_path):
            try:
                with open(self._themes_path, 'r', encoding='utf-8') as f:
                    all_themes = json.load(f)
                if isinstance(all_themes, dict) and 'last_theme' in all_themes:
                    self.last_theme = all_themes['last_theme']
                self.themes = {k: v for k, v in all_themes.items() if k != 'last_theme'}
                self.theme_combo.blockSignals(True)
                self.theme_combo.clear()
                self.theme_combo.addItems(list(self.themes.keys()))
                # Restore last theme selection if possible
                if self.last_theme and self.last_theme in self.themes:
                    idx = list(self.themes.keys()).index(self.last_theme)
                    self.theme_combo.setCurrentIndex(idx)
                self.theme_combo.blockSignals(False)
            except Exception:
                pass
        self.apply_theme()

    def apply_theme(self):
        """
        Apply the selected theme to the main UI elements and persist the choice.
        """
        import os, json
        theme_name = self.theme_combo.currentText() if hasattr(self, 'theme_combo') else 'Light'
        theme = self.themes.get(theme_name, self.themes.get('Light', {}))
        # Set main window background
        if 'UIBackground' in theme:
            self.setStyleSheet(f"background-color: {theme['UIBackground']};")
        # Set font color for main window
        if 'FontColor' in theme:
            self.setStyleSheet(self.styleSheet() + f" color: {theme['FontColor']};")
        # Set project list background and font
        if hasattr(self, 'project_list') and self.project_list is not None:
            if 'TabBackground' in theme:
                self.project_list.setStyleSheet(f"background-color: {theme['TabBackground']}; color: {theme.get('TabFontColor', '#222')};")
        # Set button colors
        if hasattr(self, 'findChildren'):
            for btn in self.findChildren(QPushButton):
                if 'ButtonBackground' in theme:
                    btn.setStyleSheet(f"background-color: {theme['ButtonBackground']}; color: {theme.get('ButtonFontColor', '#222')};")

        # Set QComboBox (dropdown) colors for sort and theme selectors
        combo_bg = theme.get('TabBackground', '#e0e0e0')
        combo_fg = theme.get('TabFontColor', '#222222')
        combo_style = f"QComboBox {{ background-color: {combo_bg}; color: {combo_fg}; }} QComboBox QAbstractItemView {{ background-color: {combo_bg}; color: {combo_fg}; }}"
        if hasattr(self, 'sort_combo'):
            self.sort_combo.setStyleSheet(combo_style)
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setStyleSheet(combo_style)
        # Set project label font color
        if hasattr(self, 'project_label') and 'FontColor' in theme:
            self.project_label.setStyleSheet(f"color: {theme['FontColor']};")
        # Set task input background and font
        if hasattr(self, 'task_input'):
            if 'UIBackground' in theme:
                self.task_input.setStyleSheet(f"background-color: {theme['UIBackground']}; color: {theme.get('FontColor', '#222')};")
        # Set task list header color
        if hasattr(self, 'task_list'):
            if 'TabBackground' in theme:
                self.task_list.setStyleSheet(f"background-color: {theme['TabBackground']}; color: {theme.get('TabFontColor', '#222')};")
            # Set QHeaderView (table header) background and font color
            header = self.task_list.horizontalHeader()
            tab_bg = theme.get('TabBackground', '#e0e0e0')
            tab_fg = theme.get('TabFontColor', '#222222')
            header.setStyleSheet(f"QHeaderView::section {{ background-color: {tab_bg}; color: {tab_fg}; }}")
        # Update the project list to refresh favourite highlighting
        if hasattr(self, 'project_list') and self.project_list is not None and hasattr(self, 'refresh_project_list'):
            self.refresh_project_list(selected_project_id=getattr(self.current_project, 'id', None))

        # --- Persist last selected theme in themes.json ---
        if hasattr(self, '_themes_path') and os.path.exists(self._themes_path):
            try:
                with open(self._themes_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                data['last_theme'] = theme_name
                with open(self._themes_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # --- Update all task rows to use new theme colors ---
        if hasattr(self, 'task_list') and self.task_list.rowCount() > 0:
            theme = self.themes.get(theme_name, self.themes.get('Light', {}))
            for row in range(self.task_list.rowCount()):
                # Update Task/Note cell
                item = self.task_list.item(row, 2)
                if item:
                    # Try to get status from the status dropdown
                    status_combo = self.task_list.cellWidget(row, 3)
                    if status_combo:
                        idx = status_combo.currentIndex()
                        status = ["Done", "WIP", "Pending"][idx] if idx in [0,1,2] else "Pending"
                    else:
                        status = "Pending"
                    bg_map = {
                        "Pending": theme.get("PendingBackground", "#ffeaea"),
                        "WIP": theme.get("WIPBackground", "#fff9e0"),
                        "Done": theme.get("DoneBackground", "#eaffea")
                    }
                    bg_hex = bg_map.get(status, "#ffeaea")
                    font_color = self.get_contrasting_font_color(bg_hex)
                    from PyQt5.QtGui import QColor, QBrush
                    item.setBackground(QBrush(QColor(bg_hex)))
                    item.setForeground(QBrush(QColor(font_color)))
                # Update status dropdown
                status_combo = self.task_list.cellWidget(row, 3)
                if status_combo:
                    idx = status_combo.currentIndex()
                    status = ["Done", "WIP", "Pending"][idx] if idx in [0,1,2] else "Pending"
                    status_bg_map = {
                        "Pending": theme.get("PendingBackground", "#e53935"),
                        "WIP": theme.get("WIPBackground", "#fbc02d"),
                        "Done": theme.get("DoneBackground", "#43a047")
                    }
                    status_bg = status_bg_map.get(status, "#e53935")
                    status_font = self.get_contrasting_font_color(status_bg)
                    # Style both the main box and the popup
                    status_combo.setStyleSheet(
                        f"QComboBox {{ background-color: {status_bg}; color: {status_font}; }} "
                        f"QComboBox QAbstractItemView {{ background-color: {status_bg}; color: {status_font}; }}"
                    )
            self.task_list.viewport().update()
            self.task_list.repaint()
    def refresh_project_list(self, selected_project_id=None):
        # Only allow one refresh at startup
        if hasattr(self, '_startup_refreshed') and self._startup_refreshed and selected_project_id is None:
            return
        # Always reload projects from disk
        self.projects = self.load_all_projects()

        # --- FULLY REBUILD THE PROJECT LIST WIDGET ---
        # Remove old widget from layout and delete it
        parent_layout = self.project_list.parentWidget().layout() if self.project_list.parentWidget() else None
        old_widget = self.project_list
        if parent_layout:
            parent_layout.removeWidget(old_widget)
        old_widget.deleteLater()

        # Create new QListWidget and reattach signals
        from PyQt5.QtWidgets import QListWidget
        self.project_list = QListWidget()
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self.open_project_context_menu)
        self.project_list.currentRowChanged.connect(self.load_project)
        if parent_layout:
            parent_layout.insertWidget(1, self.project_list)  # index 1: after label

        # Favourites first, then others, both sorted by name
        favs = [p for p in self.projects if p.get('favourite', False)]
        nonfavs = [p for p in self.projects if not p.get('favourite', False)]
        favs.sort(key=lambda x: x['name'].lower())
        nonfavs.sort(key=lambda x: x['name'].lower())
        for proj in favs + nonfavs:
            name = f"⭐ {proj['name']}" if proj.get('favourite', False) else proj['name']
            item = QListWidgetItem(name)
            item.setToolTip(proj['id'])
            if proj.get('favourite', False):
                from PyQt5.QtGui import QBrush, QColor
                item.setBackground(QBrush(QColor(204, 153, 0)))  # dark yellow
                item.setForeground(QBrush(QColor(255, 255, 255)))  # white font
            self.project_list.addItem(item)
        cprint(f"[DEBUG] Project list widget count after refresh: {self.project_list.count()}")
        # Do not set selection or load project here; handled in delete_project

    def load_project_by_id(self, project_id):
        import os, json
        import datetime
        # Always reload project metadata from disk
        projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
        project_path = os.path.join(projects_dir, f"{project_id}.json")
        if os.path.exists(project_path):
            try:
                with open(project_path, 'r', encoding='utf-8') as f:
                    proj = json.load(f)
                self.current_project = proj
                self.project_label.setText(f"Project: {proj['name']}")
                self.task_list.setRowCount(0)
                # Load tasks from tasks/<project_id>/
                tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
                tasks = []
                if os.path.exists(tasks_dir):
                    for fname in sorted(os.listdir(tasks_dir)):
                        if fname.endswith('.json'):
                            fpath = os.path.join(tasks_dir, fname)
                            try:
                                with open(fpath, 'r', encoding='utf-8') as f:
                                    task = json.load(f)
                                    if 'order' not in task:
                                        task['order'] = 0
                                    # Add created field if missing (use file creation time)
                                    if 'created' not in task:
                                        try:
                                            stat = os.stat(fpath)
                                            task['created'] = stat.st_ctime
                                        except Exception:
                                            task['created'] = 0
                                    tasks.append(task)
                            except Exception:
                                pass
                self.current_project['tasks'] = tasks
                self.display_tasks()
                return
            except Exception:
                pass
        # If not found
        self.current_project = None
        self.project_label.setText("No project selected")
        self.task_list.setRowCount(0)

    def display_tasks(self):
        # Display tasks in the order selected by the sort combo
        if not self.current_project or 'tasks' not in self.current_project:
            self.task_list.setRowCount(0)
            return
        tasks = self.current_project['tasks']
        mode = self.sort_combo.currentText() if hasattr(self, 'sort_combo') else 'Status'
        if mode == 'Status':
            # Sort by status: Pending, WIP, Done (then by order field)
            status_order = {'Pending': 0, 'WIP': 1, 'Done': 2}
            tasks = sorted(tasks, key=lambda t: (status_order.get(t.get('status', 'Pending'), 3), t.get('order', 0)))
        elif mode == 'Alphanumeric':
            tasks = sorted(tasks, key=lambda t: t.get('text', '').lower())
        elif mode == 'Oldest':
            # Sort by creation timestamp (true chronological order)
            tasks = sorted(tasks, key=lambda t: t.get('created', 0))
        self.task_list.setRowCount(0)
        for task in tasks:
            self.add_task_row(task)

    def sort_tasks_by_mode(self):
        self.display_tasks()

    def load_project_by_name(self, project_name):
        import os, json
        # Find project in self.projects
        for idx, proj in enumerate(self.projects):
            if proj['name'] == project_name:
                self.current_project = self.projects[idx]
                self.project_label.setText(f"Project: {self.current_project['name']}")
                self.task_list.setRowCount(0)
                # Load tasks from tasks/<project_name>/
                tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_name)
                tasks = []
                if os.path.exists(tasks_dir):
                    for fname in sorted(os.listdir(tasks_dir)):
                        if fname.endswith('.json'):
                            fpath = os.path.join(tasks_dir, fname)
                            try:
                                with open(fpath, 'r', encoding='utf-8') as f:
                                    task = json.load(f)
                                    tasks.append(task)
                            except Exception:
                                pass
                self.current_project['tasks'] = tasks
                for task in tasks:
                    self.add_task_row(task)
                return
        # If not found
        self.current_project = None
        self.project_label.setText("No project selected")
        self.task_list.setRowCount(0)

    def load_project(self, idx):
        if idx < 0 or idx >= self.project_list.count():
            self.current_project = None
            self.project_label.setText("No project selected")
            self.task_list.setRowCount(0)
            return
        item = self.project_list.item(idx)
        if not item:
            return
        project_id = item.toolTip()
        self.load_project_by_id(project_id)





    # Duplicate init_ui removed. Only the first definition remains.

    def load_project_by_name(self, project_name):
        import os, json
        # Find project in self.projects
        for idx, proj in enumerate(self.projects):
            if proj['name'] == project_name:
                self.current_project = self.projects[idx]
                self.project_label.setText(f"Project: {self.current_project['name']}")
                self.task_list.setRowCount(0)
                # Load tasks from tasks/<project_name>/
                tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_name)
                tasks = []
                if os.path.exists(tasks_dir):
                    for fname in sorted(os.listdir(tasks_dir)):
                        if fname.endswith('.json'):
                            fpath = os.path.join(tasks_dir, fname)
                            try:
                                with open(fpath, 'r', encoding='utf-8') as f:
                                    task = json.load(f)
                                    tasks.append(task)
                            except Exception:
                                pass
                self.current_project['tasks'] = tasks
                for task in tasks:
                    self.add_task_row(task)
                return
        # If not found
        self.current_project = None
        self.project_label.setText("No project selected")
        self.task_list.setRowCount(0)

    def add_task(self):
        import os, json, uuid, time
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please select or create a project first.")
            return
        text = self.task_input.toPlainText().strip()
        if text:
            task_id = str(uuid.uuid4())
            tasks = self.current_project.get('tasks', [])
            next_order = max([t.get('order', i) for i, t in enumerate(tasks)], default=-1) + 1
            created_ts = time.time()
            task = {"id": task_id, "text": text, "status": "Pending", "order": next_order, "created": created_ts}
            self.current_project['tasks'].append(task)
            self.add_task_row(task)
            # Save task as file
            project_id = self.current_project['id']
            tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
            os.makedirs(tasks_dir, exist_ok=True)
            fpath = os.path.join(tasks_dir, f"{task_id}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(task, f, indent=2, ensure_ascii=False)
            self.task_input.clear()

    def add_task_row(self, task):
        from PyQt5.QtGui import QColor, QBrush
        row = self.task_list.rowCount()
        self.task_list.insertRow(row)
        # Delete button
        del_btn = QPushButton()
        del_btn.setText("❌")
        del_btn.setToolTip("Delete task")
        del_btn.clicked.connect(lambda _, r=row: self.delete_task(r))
        self.task_list.setCellWidget(row, 0, del_btn)
        # Edit button
        edit_btn = QPushButton()
        edit_btn.setText("✏️")
        edit_btn.setToolTip("Edit task")
        edit_btn.clicked.connect(lambda _, r=row: self.edit_task(r))
        self.task_list.setCellWidget(row, 1, edit_btn)
        # Task text with visual wrap marker
        raw_text = task["text"] if isinstance(task, dict) else task
        display_text = self._wrap_with_marker(raw_text, marker='↪ ')
        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        # Enable word wrap for the Task/Note cell
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setData(Qt.TextWordWrap, True)
        # Store task ID in the item for robust status update
        if isinstance(task, dict) and "id" in task:
            item.setData(Qt.UserRole, task["id"])
        # Set background color and font color based on status and theme
        status = task["status"] if isinstance(task, dict) and "status" in task else "Pending"
        theme = self.themes.get(self.theme_combo.currentText(), self.themes.get('Light', {}))
        bg_map = {
            "Pending": theme.get("PendingBackground", "#ffeaea"),
            "WIP": theme.get("WIPBackground", "#fff9e0"),
            "Done": theme.get("DoneBackground", "#eaffea")
        }
        bg_hex = bg_map.get(status, "#ffeaea")
        font_color = self.get_contrasting_font_color(bg_hex)
        item.setBackground(QBrush(QColor(bg_hex)))
        item.setForeground(QBrush(QColor(font_color)))
        self.task_list.setItem(row, 2, item)
        # Force row height to fit contents (word wrap)
        self.task_list.resizeRowToContents(row)
        # For very long lines, ensure a minimum height for visibility
        min_height = 40
        if self.task_list.rowHeight(row) < min_height:
            self.task_list.setRowHeight(row, min_height)
        # Status dropdown
        status_combo = QComboBox()
        status_combo.addItem("Done")
        status_combo.addItem("WIP")
        status_combo.addItem("Pending")
        status_map = {"Done": 0, "WIP": 1, "Pending": 2}
        status_combo.setCurrentIndex(status_map.get(status, 2))
        # Set color for status button (background and font), including popup
        status_bg_map = {
            "Pending": theme.get("PendingBackground", "#e53935"),
            "WIP": theme.get("WIPBackground", "#fbc02d"),
            "Done": theme.get("DoneBackground", "#43a047")
        }
        status_bg = status_bg_map.get(status, "#e53935")
        status_font = self.get_contrasting_font_color(status_bg)
        status_combo.setStyleSheet(
            f"QComboBox {{ background-color: {status_bg}; color: {status_font}; }} "
            f"QComboBox QAbstractItemView {{ background-color: {status_bg}; color: {status_font}; }}"
        )
        status_combo.currentIndexChanged.connect(lambda idx, r=row: self.update_status(r, idx))
        self.task_list.setCellWidget(row, 3, status_combo)
    def handle_table_click(self, row, col):
        if col == 0:
            self.delete_task(row)
        elif col == 1:
            self.edit_task(row)

    def open_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        idx = self.task_list.indexAt(pos)
        row = idx.row()
        if row < 0:
            return
        menu = QMenu()
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.task_list.viewport().mapToGlobal(pos))
        if action == edit_action:
            self.edit_task(row)
        elif action == delete_action:
            self.delete_task(row)

    def edit_task(self, row):
        import os, json
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
        if not self.current_project:
            return
        # Get the task ID from the table row
        item = self.task_list.item(row, 2)
        task_id = item.data(Qt.UserRole) if item else None
        # Find the correct task in self.current_project['tasks'] by ID
        task = None
        for t in self.current_project['tasks']:
            if t.get('id') == task_id:
                task = t
                break
        if not task:
            return
        # Multi-line edit dialog
        class EditDialog(QDialog):
            def __init__(self, text, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Edit Task")
                self.setFixedWidth(800)
                layout = QVBoxLayout()
                layout.addWidget(QLabel("Edit task:"))
                self.text_edit = QTextEdit()
                self.text_edit.setPlainText(text)
                layout.addWidget(self.text_edit)
                btns = QHBoxLayout()
                ok_btn = QPushButton("OK")
                cancel_btn = QPushButton("Cancel")
                btns.addWidget(ok_btn)
                btns.addWidget(cancel_btn)
                layout.addLayout(btns)
                self.setLayout(layout)
                ok_btn.clicked.connect(self.accept)
                cancel_btn.clicked.connect(self.reject)
            def getText(self):
                return self.text_edit.toPlainText()
        dlg = EditDialog(task["text"], self)
        if dlg.exec_() == QDialog.Accepted:
            new_text = dlg.getText().strip()
            if new_text:
                task["text"] = new_text
                # Update the table cell with wrap marker
                display_text = self._wrap_with_marker(new_text, marker='↪ ')
                self.task_list.item(row, 2).setText(display_text)
                # Re-adjust row height to fit new content
                self.task_list.resizeRowToContents(row)
                # Save updated task file
                project_id = self.current_project['id']
                tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
                fpath = os.path.join(tasks_dir, f"{task['id']}.json")
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(task, f, indent=2, ensure_ascii=False)

    def delete_task(self, row):
        import os
        if not self.current_project:
            return
        task = self.current_project['tasks'].pop(row)
        self.task_list.removeRow(row)
        # Delete task file
        project_id = self.current_project['id']
        tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
        fpath = os.path.join(tasks_dir, f"{task['id']}.json")
        if os.path.exists(fpath):
            os.remove(fpath)

    def update_status(self, row, idx):
        import os, json
        from PyQt5.QtGui import QColor, QBrush
        if not self.current_project:
            return
        status = ["Done", "WIP", "Pending"][idx]
        # Get the task ID from the table row
        item = self.task_list.item(row, 2)
        task_id = item.data(Qt.UserRole) if item else None
        # Find the correct task in self.current_project['tasks'] by ID
        task = None
        for t in self.current_project['tasks']:
            if t.get('id') == task_id:
                task = t
                break
        if not task:
            return
        task["status"] = status
        # Save updated status to file
        project_id = self.current_project['id']
        tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
        fpath = os.path.join(tasks_dir, f"{task['id']}.json")
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2, ensure_ascii=False)

        # Update Task/Note cell background and font color
        if item:
            theme = self.themes.get(self.theme_combo.currentText(), self.themes.get('Light', {}))
            bg_map = {
                "Pending": theme.get("PendingBackground", "#ffeaea"),
                "WIP": theme.get("WIPBackground", "#fff9e0"),
                "Done": theme.get("DoneBackground", "#eaffea")
            }
            bg_hex = bg_map.get(status, "#ffeaea")
            font_color = self.get_contrasting_font_color(bg_hex)
            item.setBackground(QBrush(QColor(bg_hex)))
            item.setForeground(QBrush(QColor(font_color)))

        # Update status dropdown color and font
        status_combo = self.task_list.cellWidget(row, 3)
        if status_combo:
            status_bg_map = {
                "Pending": theme.get("PendingBackground", "#e53935"),
                "WIP": theme.get("WIPBackground", "#fbc02d"),
                "Done": theme.get("DoneBackground", "#43a047")
            }
            status_bg = status_bg_map.get(status, "#e53935")
            status_font = self.get_contrasting_font_color(status_bg)
            status_combo.setStyleSheet(f"QComboBox {{ background-color: {status_bg}; color: {status_font}; }} QAbstractItemView {{ background-color: #fff; color: black; }}")

        # Force repaint
        self.task_list.viewport().update()
        self.task_list.repaint()

    def new_project(self):
        from PyQt5.QtWidgets import QInputDialog
        import os, json
        # Ensure 'projects' folder exists
        projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
        os.makedirs(projects_dir, exist_ok=True)
        # Ask for project name
        project_name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if ok and project_name.strip():
            project_name = project_name.strip()
            # Generate unique 12-char alphanumeric ID
            def gen_id():
                return ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            project_id = gen_id()
            # Save project file as <id>.json
            project_path = os.path.join(projects_dir, f"{project_id}.json")
            # Ensure ID is unique (very unlikely to collide, but check)
            while os.path.exists(project_path):
                project_id = gen_id()
                project_path = os.path.join(projects_dir, f"{project_id}.json")
            # Create tasks/<project_id>/ folder
            tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
            os.makedirs(tasks_dir, exist_ok=True)
            # Add default 'Project Created' task
            import uuid
            task_id = str(uuid.uuid4())
            default_task = {"id": task_id, "text": "Project Created", "status": "Done"}
            fpath = os.path.join(tasks_dir, f"{task_id}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(default_task, f, indent=2, ensure_ascii=False)
            # Save project metadata (with favourite False)
            project_meta = {'id': project_id, 'name': project_name, 'favourite': False}
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(project_meta, f, indent=2, ensure_ascii=False)
            new_proj = {'id': project_id, 'name': project_name, 'favourite': False, 'tasks': [default_task]}
            self.projects.append(new_proj)
            # Add to project list widget (not favourites)
            item = QListWidgetItem(project_name)
            item.setToolTip(project_id)
            self.project_list.addItem(item)
            # Select the new project and load its (empty) task/note area
            row = self.project_list.count() - 1
            self.project_list.setCurrentRow(row)
            self.load_project_by_id(project_id)

    def open_project_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        idx = self.project_list.indexAt(pos)
        row = idx.row()
        if row < 0:
            return
        menu = QMenu()
        item = self.project_list.item(row)
        project_id = item.toolTip()
        proj = next((p for p in self.projects if p['id'] == project_id), None)
        if proj and proj.get('favourite', False):
            fav_action = menu.addAction("Un-favourite")
        else:
            fav_action = menu.addAction("Favourite")
        del_action = menu.addAction("Delete")
        action = menu.exec_(self.project_list.viewport().mapToGlobal(pos))
        if action == fav_action:
            if proj.get('favourite', False):
                self.remove_from_favourites(project_id)
            else:
                self.add_to_favourites(project_id)
        elif action == del_action:
            self.confirm_delete_project(project_id, favourite=proj.get('favourite', False))

    def open_fav_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        idx = self.fav_list.indexAt(pos)
        row = idx.row()
        if row < 0:
            return
        menu = QMenu()
        unfav_action = menu.addAction("Un-favourite")
        del_action = menu.addAction("Delete")
        action = menu.exec_(self.fav_list.viewport().mapToGlobal(pos))
        item = self.fav_list.item(row)
        project_id = item.toolTip()
        if action == unfav_action:
            self.remove_from_favourites(project_id)
        elif action == del_action:
            self.confirm_delete_project(project_id, favourite=True)

    def add_to_favourites(self, project_id):
        import os, json
        proj = next((p for p in self.projects if p['id'] == project_id), None)
        if proj and not proj.get('favourite', False):
            proj['favourite'] = True
            # Update project file
            projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
            project_path = os.path.join(projects_dir, f"{project_id}.json")
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['favourite'] = True
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.refresh_project_list(selected_project_id=project_id)

    def remove_from_favourites(self, project_id):
        import os, json
        proj = next((p for p in self.projects if p['id'] == project_id), None)
        if proj and proj.get('favourite', False):
            proj['favourite'] = False
            # Update project file
            projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
            project_path = os.path.join(projects_dir, f"{project_id}.json")
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['favourite'] = False
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.refresh_project_list(selected_project_id=project_id)

    def confirm_delete_project(self, project_id, favourite=False):
        proj = next((p for p in self.projects if p['id'] == project_id), None)
        pname = proj['name'] if proj else project_id
        reply = QMessageBox.question(self, "Delete Project", f"Are you sure you want to delete project '{pname}'? This cannot be undone.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_project(project_id, favourite)

    def delete_project(self, project_id, favourite):
        import os, shutil
        # Find the row of the project to be deleted
        row_to_delete = None
        next_project_id = None
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item and item.toolTip() == project_id:
                row_to_delete = i
                # Try to select the next project after deletion
                if self.project_list.count() > 1:
                    # Prefer next project, else previous
                    if i + 1 < self.project_list.count():
                        next_item = self.project_list.item(i + 1)
                    else:
                        next_item = self.project_list.item(i - 1)
                    if next_item:
                        next_project_id = next_item.toolTip()
                break
        cprint(f"[DEBUG] delete_project called for project_id: {project_id}")
        # Remove from self.projects
        self.projects = [p for p in self.projects if p['id'] != project_id]
        # Remove project file
        import time
        projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
        project_path = os.path.join(projects_dir, f"{project_id}.json")
        if os.path.exists(project_path):
            os.remove(project_path)
            cprint(f"[DEBUG] Deleted project file: {project_path}")
        # Remove tasks folder
        tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
        if os.path.exists(tasks_dir):
            shutil.rmtree(tasks_dir)
            cprint(f"[DEBUG] Deleted tasks folder: {tasks_dir}")
        # Force disk sync and short delay
        if hasattr(os, 'sync'):
            os.sync()
        time.sleep(0.1)
        # Print directory contents for debug
        cprint("[DEBUG] Projects dir after deletion:", os.listdir(projects_dir))
        # Robust UI update: block signals, clear selection, refresh, and force repaint
        self.project_list.blockSignals(True)
        self.project_list.clearSelection()
        self.project_list.clearFocus()
        # Use the same pattern as favourite: pass selected_project_id
        self.refresh_project_list(selected_project_id=next_project_id)
        QApplication.processEvents()
        # Set selection to the next project if any
        count = self.project_list.count()
        if count > 0 and next_project_id:
            for i in range(count):
                item = self.project_list.item(i)
                if item and item.toolTip() == next_project_id:
                    self.project_list.setCurrentRow(i)
                    QApplication.processEvents()
                    self.load_project(i)
                    break
        elif count > 0:
            self.project_list.setCurrentRow(0)
            QApplication.processEvents()
            self.load_project(0)
        else:
            self.project_list.setCurrentRow(-1)
            self.project_list.clearFocus()
            self.current_project = None
            self.project_label.setText("No project selected")
            self.task_list.setRowCount(0)
        self.project_list.blockSignals(False)
        self.project_list.repaint()
        self.repaint()

    def sort_tasks_by_text(self):
        import os, json
        # Sort tasks alphabetically by text
        if not self.current_project or not self.current_project.get('tasks'):
            return
        tasks = self.current_project['tasks']
        tasks.sort(key=lambda t: t.get('text', '').lower())
        # Update order field and save
        project_id = self.current_project['id']
        tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks', project_id)
        for idx, task in enumerate(tasks):
            task['order'] = idx
            fpath = os.path.join(tasks_dir, f"{task['id']}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(task, f, indent=2, ensure_ascii=False)
        # Refresh UI
        self.task_list.setRowCount(0)
        for task in tasks:
            self.add_task_row(task)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ChecklistApp()
    win.show()
    sys.exit(app.exec_())
