"""Property dialog for Expression elements — with syntax highlighting."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import (
    QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument,
)
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog
from hydrosim.gui.styles.theme import (
    FONT_MONO, FONT_UI, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY,
    CAT_COLOURS,
)
from hydrosim.model.elements.expression import Expression
from hydrosim.engine.parser import ExpressionParser, SAFE_FUNCTIONS

# ── Syntax highlighter ────────────────────────────────────────────────────────

_FN_NAMES = "|".join(re.escape(k) for k in SAFE_FUNCTIONS) if False else \
    "abs|sqrt|exp|log|log10|sin|cos|tan|min|max|round|floor|ceil|if_"

import re as _re

class _FormulaHighlighter(QSyntaxHighlighter):
    def __init__(self, doc: QTextDocument, element_names: list[str]):
        super().__init__(doc)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._element_names = set(n.lower() for n in element_names)

        def fmt(colour: str, bold: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(colour))
            if bold:
                f.setFontWeight(700)
            return f

        # Numbers
        self._rules.append((
            QRegularExpression(r'\b\d+\.?\d*([eE][+-]?\d+)?\b'),
            fmt("#7B68C8", bold=True),
        ))
        # Built-in functions
        self._rules.append((
            QRegularExpression(r'\b(' + _FN_NAMES + r')\b'),
            fmt("#00897B", bold=True),
        ))
        # Operators
        self._rules.append((
            QRegularExpression(r'[\+\-\*\/\>\<\=\!\^\(\)]'),
            fmt("#8A93A0"),
        ))

        # Element names — built from known names
        if element_names:
            pattern = r'\b(' + '|'.join(_re.escape(n) for n in element_names) + r')\b'
            self._rules.append((
                QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption),
                fmt("#4CAF82", bold=True),
            ))

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self._rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ── Expression Dialog ─────────────────────────────────────────────────────────

class ExpressionDialog(BaseElementDialog):
    def __init__(self, element: Expression, graph, parent=None):
        self._name_field  = None
        self._name_err    = None
        self._formula_edit = None
        self._known_names = [
            el.name for el in graph.elements.values()
            if el.id != element.id
        ]
        super().__init__(element, graph, parent, min_width=580)
        self.setWindowTitle(f"Expression — {element.name}")
        self.resize(580, 520)

    def _build_body(self) -> QWidget:
        w, lay = self._body_layout()

        # Name + Output Units (2-col)
        row = QHBoxLayout(); row.setSpacing(12)
        nc = QVBoxLayout(); nc.addWidget(self._field_label("Name"))
        self._name_field = QLineEdit(self.element.name)
        nc.addWidget(self._name_field); row.addLayout(nc)
        uc = QVBoxLayout(); uc.addWidget(self._field_label("Output Units"))
        self._units_field = QLineEdit(self.element.output_units)
        uc.addWidget(self._units_field); row.addLayout(uc)
        lay.addLayout(row)
        self._name_err = self._error_label()
        lay.addWidget(self._name_err)

        # Description
        lay.addWidget(self._field_label("Description"))
        self._desc_field = QLineEdit(self.element.description)
        lay.addWidget(self._desc_field)

        # Formula editor
        lay.addWidget(self._field_label("Formula"))
        editor_wrap = QWidget()
        editor_wrap.setStyleSheet(
            "border: 1px solid #E5E7EB; border-radius: 8px; background: #FBFBFD;"
        )
        ewl = QVBoxLayout(editor_wrap); ewl.setContentsMargins(0,0,0,0); ewl.setSpacing(0)

        # Gutter bar
        gutter = QLabel("ƒ(x)  ·  expression")
        gutter.setFont(QFont(FONT_MONO, 10))
        gutter.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: #F5F6FA; "
            "border-bottom: 1px solid #EEF0F4; padding: 6px 12px; border-radius: 8px 8px 0 0;"
        )
        ewl.addWidget(gutter)

        self._formula_edit = QTextEdit()
        self._formula_edit.setPlainText(self.element.formula)
        self._formula_edit.setFont(QFont(FONT_MONO, 13))
        self._formula_edit.setMinimumHeight(90)
        self._formula_edit.setMaximumHeight(150)
        self._formula_edit.setStyleSheet(
            "border: none; background: #FBFBFD; padding: 10px 14px; border-radius: 0 0 8px 8px;"
        )
        ewl.addWidget(self._formula_edit)
        lay.addWidget(editor_wrap)

        # Apply syntax highlighting
        self._highlighter = _FormulaHighlighter(
            self._formula_edit.document(), self._known_names
        )

        # Validation error label
        self._formula_err = self._error_label()
        lay.addWidget(self._formula_err)

        # Available elements chips
        lay.addWidget(self._field_label("Available Elements  (click to insert)"))
        chips_w = QWidget()
        self._chips_layout = _FlowLayout(chips_w)
        self._chips_layout.setSpacing(6)
        self._build_chips()
        lay.addWidget(chips_w)

        # Test button + result
        test_row = QHBoxLayout(); test_row.setSpacing(10)
        self._test_btn = QPushButton("Test at t=0")
        self._test_btn.setFixedHeight(30)
        self._test_btn.setFont(QFont(FONT_UI, 11))
        self._test_btn.clicked.connect(self._run_test)
        test_row.addWidget(self._test_btn)
        self._test_result = QLabel()
        self._test_result.setFont(QFont(FONT_MONO, 11))
        test_row.addWidget(self._test_result)
        test_row.addStretch()
        lay.addLayout(test_row)
        lay.addStretch()

        # Wiring
        self._name_field.textChanged.connect(self._run_validation)
        self._formula_edit.textChanged.connect(self._run_validation)
        return w

    def _build_chips(self) -> None:
        for el in self.graph.elements.values():
            if el.id == self.element.id:
                continue
            for port_name in el.output_ports:
                ref = f"{el.name}.{port_name}" if len(el.output_ports) > 1 else el.name
                self._add_chip(ref)

    def _add_chip(self, ref: str) -> None:
        btn = QPushButton(ref)
        btn.setFont(QFont(FONT_MONO, 11))
        btn.setStyleSheet(
            "QPushButton { background: #F2F8F4; border: 1px solid #D9EBE0; "
            "border-radius: 12px; padding: 4px 10px; color: #1A1A2E; }"
            "QPushButton:hover { background: #E7F3EB; border-color: #BFE0CB; }"
        )
        btn.clicked.connect(lambda _, r=ref: self._insert_ref(r))
        self._chips_layout.addWidget(btn)

    def _insert_ref(self, ref: str) -> None:
        cursor = self._formula_edit.textCursor()
        cursor.insertText(ref)
        self._formula_edit.setFocus()

    def _run_test(self) -> None:
        formula = self._formula_edit.toPlainText().strip()
        if not formula:
            return
        try:
            result = ExpressionParser("", {}).evaluate.__func__ if False else None
            # Simple evaluation with 0 for all inputs
            inputs = {ref: 0.0 for ref in ExpressionParser.extract_references(formula)}
            parser = ExpressionParser(formula, {k.lower(): k for k in inputs})
            val = parser.evaluate(inputs, t=0.0, dt=1.0)
            self._test_result.setStyleSheet(
                "background: #E8F5E9; color: #2f7d33; border-radius: 12px; "
                "padding: 4px 12px; font-weight: 600;"
            )
            self._test_result.setText(f"= {val:.6g}  {self._units_field.text()}")
        except Exception as exc:
            self._test_result.setStyleSheet(
                "background: #FEF2F2; color: #E53935; border-radius: 12px; padding: 4px 12px;"
            )
            self._test_result.setText(f"Error: {exc}")

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors
        e = self._validate_name(self._name_field.text().strip())
        if e:
            errors.append(e); self._show_error(self._name_err, e)
        else:
            self._show_error(self._name_err, "")

        formula = self._formula_edit.toPlainText().strip() if self._formula_edit else ""
        syntax_errs = ExpressionParser.validate_syntax(formula)
        if syntax_errs:
            msg = "; ".join(syntax_errs[:2])
            errors.append(msg); self._show_error(self._formula_err, msg)
        else:
            # Check references exist
            refs = ExpressionParser.extract_references(formula)
            unknown = [
                r.split(".")[0] for r in refs
                if self.graph.get_element_by_name(r.split(".")[0]) is None
            ]
            if unknown:
                msg = f"Unknown element(s): {', '.join(unknown)}"
                errors.append(msg); self._show_error(self._formula_err, msg)
            else:
                self._show_error(self._formula_err, "")
        return errors

    def apply_changes(self) -> None:
        self.element.name         = self._name_field.text().strip()
        self.element.description  = self._desc_field.text().strip()
        self.element.output_units = self._units_field.text().strip() or "-"
        self.element.set_formula(self._formula_edit.toPlainText().strip())
        self.element._prepared    = False


# ── Minimal flow layout (no Qt5Compat dependency) ─────────────────────────────

class _FlowLayout:
    """Wraps widgets in a flow — simple implementation using QHBoxLayout rows."""
    def __init__(self, parent: QWidget):
        self._parent = parent
        self._outer  = QVBoxLayout(parent)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(4)
        self._current_row: QHBoxLayout | None = None
        self._row_count = 0
        self._per_row   = 3

    def setSpacing(self, s: int) -> None:
        self._outer.setSpacing(s)

    def addWidget(self, w: QWidget) -> None:
        if self._current_row is None or self._row_count >= self._per_row:
            self._current_row = QHBoxLayout()
            self._current_row.setSpacing(6)
            self._current_row.setContentsMargins(0,0,0,0)
            self._outer.addLayout(self._current_row)
            self._row_count = 0
        self._current_row.addWidget(w)
        self._row_count += 1
