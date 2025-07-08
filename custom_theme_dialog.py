from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog, QLineEdit, QWidget, QScrollArea, QMessageBox, QInputDialog
from PyQt5.QtGui import QColor

class PreviewWidget(QWidget):
    def __init__(self, get_values_func, get_contrasting_func, parent=None):
        super().__init__(parent)
        self.get_values = get_values_func
        self.get_contrasting = get_contrasting_func
        self.setMinimumHeight(120)
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter
        painter = QPainter(self)
        vals = self.get_values()
        painter.fillRect(self.rect(), QColor(vals["UIBackground"]))
        painter.fillRect(10, 10, 120, 100, QColor(vals["TabBackground"]))
        painter.setPen(QColor(vals["TabFontColor"]))
        painter.drawText(20, 40, "Sidebar")
        painter.fillRect(150, 20, 100, 30, QColor(vals["ButtonBackground"]))
        painter.setPen(QColor(vals["ButtonFontColor"]))
        painter.drawText(160, 40, "Button")
        painter.fillRect(270, 20, 200, 30, QColor(vals["PendingBackground"]))
        painter.setPen(QColor(self.get_contrasting(vals["PendingBackground"])))
        painter.drawText(280, 40, "Pending task")
        painter.fillRect(270, 55, 200, 30, QColor(vals["WIPBackground"]))
        painter.setPen(QColor(self.get_contrasting(vals["WIPBackground"])))
        painter.drawText(280, 75, "WIP task")
        painter.fillRect(270, 90, 200, 30, QColor(vals["DoneBackground"]))
        painter.setPen(QColor(self.get_contrasting(vals["DoneBackground"])))
        painter.drawText(280, 110, "Done task")
        painter.setPen(QColor(vals["FontColor"]))
        painter.drawText(20, 110, "Main font sample")

class CustomThemeDialog(QDialog):
    def __init__(self, parent, theme_params, param_values, get_contrasting_func, themes_path):
        super().__init__(parent)
        self.setWindowTitle("Custom Theme Editor")
        self.setMinimumWidth(600)
        self.theme_params = theme_params
        self.get_contrasting = get_contrasting_func
        self.themes_path = themes_path
        layout = QVBoxLayout()
        self.param_inputs = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QVBoxLayout()
        self.rgb_labels = {}
        for key, label in theme_params:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            # RGB preview label
            rgb_label = QLabel()
            rgb_label.setFixedWidth(28)
            rgb_label.setFixedHeight(20)
            rgb_label.setStyleSheet(f"background-color: {param_values[key]}; border: 1px solid #888;")
            row.addWidget(rgb_label)
            self.rgb_labels[key] = rgb_label
            color_input = QLineEdit(param_values[key])
            color_input.setMaxLength(7)
            color_input.setFixedWidth(80)
            def make_picker_func(k=key, inp=color_input):
                def pick():
                    col = QColorDialog.getColor(QColor(inp.text()), self, f"Pick color for {k}")
                    if col.isValid():
                        inp.setText(col.name())
                        self.update_preview()
                return pick
            pick_btn = QPushButton("Pick")
            pick_btn.setFixedWidth(50)
            pick_btn.clicked.connect(make_picker_func())
            color_input.textChanged.connect(self.update_preview)
            # Also update RGB preview on hex change
            def make_rgb_updater(k=key, inp=color_input, lbl=rgb_label):
                def update_rgb():
                    val = inp.text()
                    if not val.startswith('#'):
                        val = '#' + val
                    if len(val) == 7:
                        lbl.setStyleSheet(f"background-color: {val}; border: 1px solid #888;")
                return update_rgb
            color_input.textChanged.connect(make_rgb_updater())
            row.addWidget(color_input)
            row.addWidget(pick_btn)
            self.param_inputs[key] = color_input
            form.addLayout(row)
        inner.setLayout(form)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        self.preview = PreviewWidget(self.get_param_values, self.get_contrasting, self)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview)
        save_btn = QPushButton("Save Custom Theme")
        save_btn.clicked.connect(self.save_theme)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def get_param_values(self):
        return {k: self.param_inputs[k].text() for k, _ in self.theme_params}

    def update_preview(self):
        self.preview.update()

    def save_theme(self):
        vals = self.get_param_values()
        for v in vals.values():
            if not (v.startswith('#') and (len(v) == 7 or len(v) == 4)):
                QMessageBox.warning(self, "Invalid Color", f"Invalid color value: {v}")
                return
        name, ok = QInputDialog.getText(self, "Theme Name", "Enter a name for your custom theme:")
        if not ok or not name.strip():
            return
        name = name.strip()
        import json
        try:
            with open(self.themes_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        data[name] = vals
        with open(self.themes_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Update theme combo in main window
        self.parent().themes = data
        self.parent().theme_combo.clear()
        self.parent().theme_combo.addItems(list(data.keys()))
        idx = list(data.keys()).index(name)
        self.parent().theme_combo.setCurrentIndex(idx)
        self.parent().apply_theme()
        self.accept()
