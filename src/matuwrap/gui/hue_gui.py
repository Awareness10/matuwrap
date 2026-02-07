import sys
import os
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QSlider,
    QColorDialog,
    QSpinBox,
    QLineEdit,
    QCheckBox,
    QAbstractItemView,
    QSizePolicy,
    QFrame,
    QGraphicsDropShadowEffect,
)

from matuwrap.commands.hue import HueController, _check_config
from matuwrap.core.colors import get_colors, WALLPAPER_PATH

# Glaze imports
from glaze import (
    generate_theme,
    get_base_stylesheet,
    get_dialog_stylesheet,
    get_table_container_style,
)
from glaze.widgets import RoundedHeaderView, ThemedComboBox


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def bri_to_pct(bri: int) -> int:
    return int(round((bri / 254) * 100))


def pct_to_bri(pct: int) -> int:
    return int(round((pct / 100) * 254))


def hue_sat_to_qcolor(hue: int, sat: int, bri: int = 254) -> QColor:
    qt_h = int(round((hue / 65535) * 359))
    qt_s = clamp(sat, 0, 254)
    qt_v = clamp(bri, 1, 254)
    c = QColor()
    c.setHsv(qt_h, qt_s, qt_v)
    return c


def contrast_text(bg: QColor) -> QColor:
    # simple luminance heuristic
    r, g, b, _ = bg.getRgb() # type: ignore
    lum = (0.299 * r + 0.587 * g + 0.114 * b)
    return QColor("#111111") if lum > 160 else QColor("#f2f2f2")


class NumericTableItem(QTableWidgetItem):
    """Table item that sorts numerically instead of alphabetically."""

    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return int(self.text()) < int(other.text())
        except ValueError:
            return super().__lt__(other)


@dataclass
class LightRow:
    light_id: int
    name: str
    is_on: bool
    bri: int
    hue: int | None
    sat: int | None
    ct: int | None


class HueDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MatuWrap • Hue Dashboard")
        self.setMinimumSize(1100, 680)

        if not _check_config():
            QMessageBox.critical(self, "Hue not configured", "Missing HUE_BRIDGE_IP or HUE_USERNAME.")
            raise SystemExit(1)

        bridge_ip = os.environ.get("HUE_BRIDGE_IP")
        username = os.environ.get("HUE_USERNAME")
        self.hue = HueController(bridge_ip, username)  # type: ignore[arg-type]

        self.selected_light_id: int | None = None
        self._updating_ui = False
        self._rows_cache: list[LightRow] = []

        # debounce timers (prevents slider spam)
        self.bri_apply_timer = QTimer(self)
        self.bri_apply_timer.setSingleShot(True)
        self.bri_apply_timer.timeout.connect(self._apply_brightness_debounced)

        self.temp_apply_timer = QTimer(self)
        self.temp_apply_timer.setSingleShot(True)
        self.temp_apply_timer.timeout.connect(self._apply_temp_debounced)

        # Generate theme from wallpaper
        self._load_theme()
        self._build_ui()
        self._apply_theme()
        self._setup_refresh()

        self.refresh_now()

    # ---------------- Theme ----------------

    def _load_theme(self):
        """Load theme from wallpaper using Glaze."""
        wallpaper = str(WALLPAPER_PATH) if WALLPAPER_PATH.exists() else None
        self.theme, self._backend = generate_theme(image_path=wallpaper)

    def _set_status_text(self, text: str, dot_color: str):
        """Set status pill text with properly aligned colored dot."""
        self.status_pill.setText(
            f'<table cellpadding="0" cellspacing="0" align="center">'
            f'<tr>'
            f'<td style="vertical-align: middle; color: {dot_color}; font-size: 9px; padding-right: 4px; padding-left: 4x;">●</td>'
            f'<td style="vertical-align: middle;">{text}</td>'
            f'</tr></table>'
        )

    # ---------------- UI ----------------

    def _build_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # LEFT PANEL (Lights)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("Hue Lights")
        title.setFont(QFont("", 16, QFont.Weight.Bold))

        self.status_pill = QLabel()
        self.status_pill.setObjectName("statusPill")
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setFixedHeight(28)
        self.status_pill.setFixedWidth(101)
        self._set_status_text("Connected", "#4ade80")  # green

        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.status_pill)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_now)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search lights…")
        self.search.textChanged.connect(self._apply_filters)

        self.only_on = QCheckBox("Only ON")
        self.only_on.stateChanged.connect(self._apply_filters)

        self.auto_refresh_combo = ThemedComboBox()
        self.auto_refresh_combo.addItems(["Off", "1s", "2s", "5s", "10s"])
        self.auto_refresh_combo.setCurrentText("2s")
        self.auto_refresh_combo.currentTextChanged.connect(self._update_refresh_timer)

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.only_on)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("Auto:"))
        toolbar.addWidget(self.auto_refresh_combo)

        # Table container with shadow effect
        self.table_container = QFrame()
        self.table_container.setObjectName("tableContainer")
        table_container_layout = QVBoxLayout(self.table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0)
        table_container_layout.setSpacing(0)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.table_container.setGraphicsEffect(shadow)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "State", "Bri", "Color", "CT"])
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)

        # Use RoundedHeaderView for styled headers
        self.header = RoundedHeaderView(Qt.Orientation.Horizontal, self.table)
        self.header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalHeader(self.header)

        # Column sizing: ID fixed small, others stretch
        self.header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)      # ID
        self.header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)    # Name
        self.header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)      # State
        self.header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)      # Bri
        self.header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)    # Color
        self.header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)      # CT
        self.table.setColumnWidth(0, 50)   # ID - narrower
        self.table.setColumnWidth(2, 70)   # State
        self.table.setColumnWidth(3, 60)   # Bri
        self.table.setColumnWidth(5, 60)   # CT

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)

        if (v_header := self.table.verticalHeader()) is not None:
            v_header.setVisible(False)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)  # Default sort by ID
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setWordWrap(False)
        self.table.setMouseTracking(True)
        self.table.setRowHeight(0, 42)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        self.table.itemDoubleClicked.connect(self._on_double_click)

        table_container_layout.addWidget(self.table)

        left_layout.addLayout(title_row)
        left_layout.addLayout(toolbar)
        left_layout.addWidget(self.table_container)

        # RIGHT PANEL (Controls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        right_title = QLabel("Controls")
        right_title.setFont(QFont("", 16, QFont.Weight.Bold))

        self.selected_label = QLabel("No light selected")
        self.selected_label.setObjectName("selectedTitle")

        # Quick actions card
        quick_card = QGroupBox("Quick Actions")
        quick_layout = QHBoxLayout(quick_card)
        quick_layout.setSpacing(10)

        self.on_btn = QPushButton("On")
        self.off_btn = QPushButton("Off")
        self.toggle_btn = QPushButton("Toggle")

        self.on_btn.clicked.connect(lambda: self._with_selected(self._turn_on))
        self.off_btn.clicked.connect(lambda: self._with_selected(self._turn_off))
        self.toggle_btn.clicked.connect(lambda: self._with_selected(self._toggle))

        quick_layout.addWidget(self.on_btn)
        quick_layout.addWidget(self.off_btn)
        quick_layout.addWidget(self.toggle_btn)

        # Brightness card
        bri_card = QGroupBox("Brightness")
        bri_layout = QHBoxLayout(bri_card)
        bri_layout.setSpacing(10)

        self.bri_slider = QSlider(Qt.Orientation.Horizontal)
        self.bri_slider.setRange(0, 100)
        self.bri_slider.setValue(100)
        self.bri_slider.valueChanged.connect(self._brightness_changed)

        self.bri_spin = QSpinBox()
        self.bri_spin.setRange(0, 100)
        self.bri_spin.setValue(100)
        self.bri_spin.valueChanged.connect(self._brightness_spin_changed)

        bri_layout.addWidget(self.bri_slider, 1)
        bri_layout.addWidget(self.bri_spin)

        # Color card
        color_card = QGroupBox("Color")
        color_layout = QHBoxLayout(color_card)
        color_layout.setSpacing(10)

        self.pick_color_btn = QPushButton("Pick…")
        self.pick_color_btn.clicked.connect(lambda: self._with_selected(self._pick_color))

        self.theme_combo = ThemedComboBox()
        self.theme_combo.addItems(
            ["primary", "secondary", "tertiary", "primary_container", "secondary_container"]
        )

        self.theme_btn = QPushButton("Apply Theme")
        self.theme_btn.clicked.connect(lambda: self._with_selected(self._apply_theme_color))

        color_layout.addWidget(self.pick_color_btn)
        color_layout.addWidget(self.theme_combo, 1)
        color_layout.addWidget(self.theme_btn)

        # Temperature card
        temp_card = QGroupBox("Temperature")
        temp_layout = QHBoxLayout(temp_card)
        temp_layout.setSpacing(10)

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(153, 500)
        self.temp_slider.setValue(350)
        self.temp_slider.valueChanged.connect(self._temp_changed)

        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(153, 500)
        self.temp_spin.setValue(350)
        self.temp_spin.valueChanged.connect(self._temp_spin_changed)

        temp_layout.addWidget(self.temp_slider, 1)
        temp_layout.addWidget(self.temp_spin)

        right_layout.addWidget(right_title)
        right_layout.addWidget(self.selected_label)
        right_layout.addWidget(quick_card)
        right_layout.addWidget(bri_card)
        right_layout.addWidget(color_card)
        right_layout.addWidget(temp_card)
        right_layout.addStretch(1)

        root_layout.addWidget(left_panel, 3)
        root_layout.addWidget(right_panel, 2)
        self.setCentralWidget(root)

        self._set_controls_enabled(False)

    def _apply_theme(self):
        t = self.theme

        # Get base stylesheet from Glaze
        base_styles = get_base_stylesheet(t)
        dialog_styles = get_dialog_stylesheet(t)
        table_container_styles = get_table_container_style(t)

        # Additional custom styles for this app
        custom_styles = f"""
            QMainWindow {{
                font-size: 13px;
            }}

            QLabel#selectedTitle {{
                font-size: 14px;
                font-weight: 600;
                padding: 8px 10px;
                border-radius: 10px;
                background: {t.bg_secondary};
                border: 1px solid {t.border};
            }}

            QLabel#statusPill {{
                border-radius: 14px;
                padding: 0 10px 0 6px;
                background: {t.bg_secondary};
                border: 1px solid {t.border};
                font-weight: 600;
            }}

            QGroupBox {{
                background: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 14px;
                margin-top: 10px;
                padding: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                font-weight: 700;
                color: {t.text_primary};
            }}

            QCheckBox {{
                color: {t.text_primary};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {t.border};
                border-radius: 4px;
                background-color: {t.bg_primary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {t.accent};
                border-color: {t.accent};
            }}

            QTableWidget::item {{
                padding: 4px 8px;
            }}
        """

        self.setStyleSheet(base_styles + dialog_styles + table_container_styles + custom_styles)

        # Apply table container style directly
        if hasattr(self, 'table_container'):
            self.table_container.setStyleSheet(get_table_container_style(t))

        # Update header colors
        if hasattr(self, 'header'):
            self.header.refresh_theme()

    def _set_controls_enabled(self, enabled: bool):
        self.on_btn.setEnabled(enabled)
        self.off_btn.setEnabled(enabled)
        self.toggle_btn.setEnabled(enabled)
        self.bri_slider.setEnabled(enabled)
        self.bri_spin.setEnabled(enabled)
        self.pick_color_btn.setEnabled(enabled)
        self.theme_combo.setEnabled(enabled)
        self.theme_btn.setEnabled(enabled)
        self.temp_slider.setEnabled(enabled)
        self.temp_spin.setEnabled(enabled)

    # ---------------- Refresh / Filtering ----------------

    def _setup_refresh(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_now)
        self._update_refresh_timer(self.auto_refresh_combo.currentText())

    def _update_refresh_timer(self, txt: str):
        if txt == "Off":
            self.timer.stop()
            return
        sec = int(txt.replace("s", ""))
        self.timer.start(sec * 1000)

    def refresh_now(self):
        try:
            lights = self.hue.get_lights()
            rows: list[LightRow] = []
            for lid_str, light in sorted(lights.items(), key=lambda x: int(x[0])):
                lid = int(lid_str)
                state = light.get("state", {})
                rows.append(
                    LightRow(
                        light_id=lid,
                        name=light.get("name", f"Light {lid}"),
                        is_on=bool(state.get("on", False)),
                        bri=int(state.get("bri", 0) or 0),
                        hue=state.get("hue"),
                        sat=state.get("sat"),
                        ct=state.get("ct"),
                    )
                )

            self._rows_cache = rows
            self._apply_filters()
            self._set_status_text("Connected", "#4ade80")
        except Exception as e:
            self._set_status_text("Error", "#f87171")
            QMessageBox.critical(self, "Hue Error", str(e))

    def _apply_filters(self):
        text = self.search.text().strip().lower()
        only_on = self.only_on.isChecked()

        rows = self._rows_cache
        if text:
            rows = [r for r in rows if text in r.name.lower() or text in str(r.light_id)]
        if only_on:
            rows = [r for r in rows if r.is_on]

        self._render_table(rows)

    def _render_table(self, rows: list[LightRow]):
        self._updating_ui = True
        # Disable sorting while populating to prevent duplicate/reorder bugs
        self.table.setSortingEnabled(False)
        try:
            self.table.setRowCount(len(rows))

            t = self.theme
            text_secondary = QColor(t.text_secondary)
            success_color = QColor(t.success)
            disabled_color = QColor(t.text_disabled)

            for r, row in enumerate(rows):
                self.table.setRowHeight(r, 44)

                # ID (numeric sorting)
                id_item = NumericTableItem(str(row.light_id))
                id_item.setForeground(QBrush(text_secondary))

                # Name
                name_item = QTableWidgetItem(row.name)
                name_item.setFont(QFont("", 11, QFont.Weight.Medium))

                # State (badge-ish)
                state_item = QTableWidgetItem("  ON" if row.is_on else "  OFF")
                state_item.setFont(QFont("", 10, QFont.Weight.Bold))
                state_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)

                if row.is_on:
                    state_item.setForeground(QBrush(success_color))
                else:
                    state_item.setForeground(QBrush(disabled_color))

                # Brightness
                bri_pct = bri_to_pct(row.bri) if row.is_on else 0
                bri_item = QTableWidgetItem(f"{bri_pct}%")
                bri_item.setForeground(QBrush(text_secondary))

                # Color pill - use widget to override stylesheet background
                color_label = QLabel("-")
                color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if row.is_on and row.hue is not None and row.sat is not None:
                    qc = hue_sat_to_qcolor(int(row.hue), int(row.sat), max(row.bri, 30))
                    text_color = contrast_text(qc)
                    color_label.setText(qc.name())
                    color_label.setStyleSheet(f"""
                        background-color: {qc.name()};
                        color: {text_color.name()};
                        font-size: 10px;
                        font-weight: bold;
                        border-radius: 4px;
                        padding: 2px 4px;
                    """)

                # Temp
                ct_item = QTableWidgetItem(str(row.ct) if row.ct is not None else "-")
                ct_item.setForeground(QBrush(text_secondary))

                self.table.setItem(r, 0, id_item)
                self.table.setItem(r, 1, name_item)
                self.table.setItem(r, 2, state_item)
                self.table.setItem(r, 3, bri_item)
                self.table.setCellWidget(r, 4, color_label)
                self.table.setItem(r, 5, ct_item)

            # restore selection
            if self.selected_light_id is not None:
                for r in range(self.table.rowCount()):
                    item = self.table.item(r, 0)
                    if item is None:
                        continue
                    if int(item.text()) == self.selected_light_id:
                        self.table.selectRow(r)
                        break

        finally:
            self._updating_ui = False
            self.table.setSortingEnabled(True)

    def _on_double_click(self, item: QTableWidgetItem):
        # double click any row toggles
        self._with_selected(self._toggle)

    # ---------------- Selection ----------------

    def _on_table_selection(self):
        if self._updating_ui:
            return

        row = self.table.currentRow()
        if row < 0:
            self.selected_light_id = None
            self.selected_label.setText("No light selected")
            self._set_controls_enabled(False)
            return

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 1)
        if id_item is None or name_item is None:
            return

        light_id = int(id_item.text())
        self.selected_light_id = light_id
        self.selected_label.setText(f"Selected: Light {light_id} • {name_item.text()}")
        self._set_controls_enabled(True)

        # sync controls from bridge
        try:
            light = self.hue.get_light(light_id)
            state = light.get("state", {})
            bri = int(state.get("bri", 254) or 254)
            ct = int(state.get("ct", 350) or 350)
            bri_pct = bri_to_pct(bri)

            self._updating_ui = True
            self.bri_slider.setValue(clamp(bri_pct, 0, 100))
            self.bri_spin.setValue(clamp(bri_pct, 0, 100))
            self.temp_slider.setValue(clamp(ct, 153, 500))
            self.temp_spin.setValue(clamp(ct, 153, 500))
        except Exception:
            pass
        finally:
            self._updating_ui = False

    # ---------------- Actions ----------------

    def _with_selected(self, fn):
        if self.selected_light_id is None:
            return
        try:
            fn(self.selected_light_id)
            self.refresh_now()
        except Exception as e:
            QMessageBox.critical(self, "Hue Error", str(e))

    def _turn_on(self, light_id: int):
        self.hue.turn_on(light_id)

    def _turn_off(self, light_id: int):
        self.hue.turn_off(light_id)

    def _toggle(self, light_id: int):
        self.hue.toggle(light_id)

    # ---------------- Debounced sliders ----------------

    def _brightness_changed(self, pct: int):
        if self._updating_ui:
            return
        self.bri_spin.blockSignals(True)
        self.bri_spin.setValue(pct)
        self.bri_spin.blockSignals(False)

        # debounce apply (feels MUCH nicer)
        self.bri_apply_timer.start(120)

    def _brightness_spin_changed(self, pct: int):
        if self._updating_ui:
            return
        self.bri_slider.blockSignals(True)
        self.bri_slider.setValue(pct)
        self.bri_slider.blockSignals(False)

        self.bri_apply_timer.start(120)

    def _apply_brightness_debounced(self):
        if self.selected_light_id is None:
            return
        pct = self.bri_spin.value()
        self.hue.set_brightness(self.selected_light_id, pct_to_bri(pct))
        self.refresh_now()

    def _temp_changed(self, ct: int):
        if self._updating_ui:
            return
        self.temp_spin.blockSignals(True)
        self.temp_spin.setValue(ct)
        self.temp_spin.blockSignals(False)

        self.temp_apply_timer.start(120)

    def _temp_spin_changed(self, ct: int):
        if self._updating_ui:
            return
        self.temp_slider.blockSignals(True)
        self.temp_slider.setValue(ct)
        self.temp_slider.blockSignals(False)

        self.temp_apply_timer.start(120)

    def _apply_temp_debounced(self):
        if self.selected_light_id is None:
            return
        ct = self.temp_spin.value()
        self.hue.set_temperature(self.selected_light_id, ct)
        self.refresh_now()

    # ---------------- Color ----------------

    def _pick_color(self, light_id: int):
        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)

        if dlg.exec():
            c = dlg.selectedColor()

            h = c.hsvHue()          # 0..359 or -1
            s = c.hsvSaturation()   # 0..255

            hue_val = int(round((h / 359) * 65535)) if h >= 0 else 0
            sat_val = int(round((s / 255) * 254))

            self.hue.set_color(light_id, hue_val, sat_val)

    def _apply_theme_color(self, light_id: int):
        colors = get_colors()
        name = self.theme_combo.currentText()
        hex_color = getattr(colors, name)
        qc = QColor(hex_color)

        h = qc.hsvHue()
        s = qc.hsvSaturation()

        hue_val = int(round((h / 359) * 65535)) if h >= 0 else 0
        sat_val = int(round((s / 255) * 254))

        self.hue.set_color(light_id, hue_val, sat_val)

def main():
    app = QApplication(sys.argv)
    win = HueDashboard()
    win.show()
    #sys.exit(app.exec())
    return app.exec()

if __name__ == "__main__":
    main()