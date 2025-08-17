# main.py
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QLabel, QStackedWidget, QSizePolicy, QGraphicsOpacityEffect,
    QDialog, QLineEdit, QDialogButtonBox, QGridLayout, QMessageBox, QRadioButton, QButtonGroup
)

import auth  # Sicherheits-Backend

# ======= Theme / Farben =======
ACCENT   = "#8B5CF6"
BG_DARK  = "#0F172A"
BG_PANEL = "#111827"
FG_TEXT  = "#E5E7EB"
FG_MUTED = "#9CA3AF"
SUCCESS  = "#10B981"
WARN     = "#F59E0B"
ERROR    = "#EF4444"

# ----------------------------- Erststart/Setup Dialog -----------------------------
class FirstRunDialog(QDialog):
    """Wird angezeigt, wenn noch kein Passwort im gewählten Backend existiert.
       Erlaubt die Auswahl des Backends + Setzen des Startpassworts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Erstkonfiguration")
        self.setModal(True)
        self.setFixedWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Zugang einrichten")
        title.setStyleSheet(f"color: {FG_TEXT}; font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        info = QLabel("Wähle, wo dein Passwort-Hash gespeichert wird, und setze ein Startpasswort.")
        info.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        info.setWordWrap(True)
        root.addWidget(info)

        # Backend Auswahl
        backendFrame = QFrame()
        bLay = QVBoxLayout(backendFrame)
        bLay.setContentsMargins(12, 12, 12, 12)
        bLay.setSpacing(8)

        self.rbCredman = QRadioButton("Windows Credential Manager (empfohlen)")
        self.rbFile = QRadioButton("Lokale, verschlüsselte Datei (DPAPI in %APPDATA%)")
        group = QButtonGroup(self)
        group.addButton(self.rbCredman)
        group.addButton(self.rbFile)

        # Vorbelegen mit aktuellem Backend
        current_backend = auth.get_backend()
        if current_backend == "credman":
            self.rbCredman.setChecked(True)
        else:
            self.rbFile.setChecked(True)

        for rb in (self.rbCredman, self.rbFile):
            rb.setStyleSheet(f"color: {FG_TEXT}; font-size: 13px;")
            bLay.addWidget(rb)

        root.addWidget(backendFrame)

        # Passwort Felder
        form = QFrame()
        grid = QGridLayout(form)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)

        lblUser = QLabel("Benutzername")
        lblUser.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        self.txtUser = QLineEdit()
        self.txtUser.setText(auth.DEFAULT_USER)
        self.txtUser.setReadOnly(True)
        self.txtUser.setMinimumWidth(280)

        lblPw1 = QLabel("Passwort")
        lblPw1.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        self.txtPw1 = QLineEdit()
        self.txtPw1.setEchoMode(QLineEdit.Password)

        lblPw2 = QLabel("Passwort wiederholen")
        lblPw2.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        self.txtPw2 = QLineEdit()
        self.txtPw2.setEchoMode(QLineEdit.Password)

        grid.addWidget(lblUser, 0, 0)
        grid.addWidget(self.txtUser, 1, 0, 1, 2)
        grid.addWidget(lblPw1, 2, 0)
        grid.addWidget(self.txtPw1, 3, 0, 1, 2)
        grid.addWidget(lblPw2, 4, 0)
        grid.addWidget(self.txtPw2, 5, 0, 1, 2)

        root.addWidget(form)

        self.errorLabel = QLabel("")
        self.errorLabel.setStyleSheet("color: #FCA5A5; font-size: 12px;")
        root.addWidget(self.errorLabel)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Speichern")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.save_creds)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_DARK}; }}
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 8px 10px;
                color: {FG_TEXT};
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(139, 92, 246, 0.65);
                background: rgba(255,255,255,0.09);
            }}
            QPushButton {{
                background-color: rgba(139, 92, 246, 0.85);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{ background-color: rgba(139, 92, 246, 1.0); }}
        """)

    def save_creds(self):
        pw1 = self.txtPw1.text()
        pw2 = self.txtPw2.text()
        if pw1 != pw2:
            self.errorLabel.setText("Die Passwörter stimmen nicht überein.")
            return
        if len(pw1) < 8:
            self.errorLabel.setText("Bitte ein Passwort mit mindestens 8 Zeichen wählen.")
            return
        backend = "credman" if self.rbCredman.isChecked() else "file"
        ok = auth.set_credentials(pw1, username=auth.DEFAULT_USER, backend=backend)  # speichert auch Backend
        if not ok:
            self.errorLabel.setText("Speichern fehlgeschlagen. Prüfe Berechtigungen.")
            return
        self.accept()

# ----------------------------- Login Dialog -----------------------------
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anmeldung")
        self.setModal(True)
        self.setFixedWidth(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Bitte anmelden")
        title.setStyleSheet(f"color: {FG_TEXT}; font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        form = QFrame()
        grid = QGridLayout(form)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)

        lblUser = QLabel("Benutzername")
        lblUser.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        self.txtUser = QLineEdit()
        self.txtUser.setPlaceholderText("z. B. Timo.Hertling")
        self.txtUser.setText(auth.DEFAULT_USER)
        self.txtUser.setMinimumWidth(260)
        self.txtUser.returnPressed.connect(lambda: self.txtPwd.setFocus())

        lblPwd = QLabel("Passwort")
        lblPwd.setStyleSheet(f"color: {FG_MUTED}; font-size: 12px;")
        self.txtPwd = QLineEdit()
        self.txtPwd.setPlaceholderText("Passwort")
        self.txtPwd.setEchoMode(QLineEdit.Password)
        self.txtPwd.returnPressed.connect(self.try_login)

        grid.addWidget(lblUser, 0, 0)
        grid.addWidget(self.txtUser, 1, 0, 1, 2)
        grid.addWidget(lblPwd, 2, 0)
        grid.addWidget(self.txtPwd, 3, 0, 1, 2)

        root.addWidget(form)

        self.errorLabel = QLabel("")
        self.errorLabel.setStyleSheet("color: #FCA5A5; font-size: 12px;")
        root.addWidget(self.errorLabel)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Anmelden")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_DARK}; }}
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 8px 10px;
                color: {FG_TEXT};
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(139, 92, 246, 0.65);
                background: rgba(255,255,255,0.09);
            }}
            QPushButton {{
                background-color: rgba(139, 92, 246, 0.85);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{ background-color: rgba(139, 92, 246, 1.0); }}
        """)

    def try_login(self):
        user = self.txtUser.text().strip()
        pwd  = self.txtPwd.text()
        if auth.verify(user, pwd):
            self.accept()
            return
        self.errorLabel.setText("Ungültige Anmeldedaten. Bitte erneut versuchen.")
        self.shake()

    def shake(self):
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        start = self.pos()
        anim.setKeyValueAt(0.0, start)
        anim.setKeyValueAt(0.25, start + QPoint(8, 0))
        anim.setKeyValueAt(0.50, start + QPoint(-8, 0))
        anim.setKeyValueAt(0.75, start + QPoint(6, 0))
        anim.setKeyValueAt(1.0, start)
        anim.start()

# ----------------------------- UI Komponenten (Dashboard etc.) -----------------------------
class StatsCard(QFrame):
    def __init__(self, title: str, value: int|str = "—", color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsCard")
        self.titleLabel = QLabel(title); self.titleLabel.setObjectName("CardTitle")
        self.valueLabel = QLabel(str(value)); self.valueLabel.setObjectName("CardValue")
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(6)
        lay.addWidget(self.titleLabel); lay.addWidget(self.valueLabel, 0, Qt.AlignLeft|Qt.AlignVCenter)
        self.setStyleSheet(f"""
            QFrame#StatsCard {{ background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; }}
            QLabel#CardTitle {{ color: {FG_MUTED}; font-size: 12px; letter-spacing: 0.5px; }}
            QLabel#CardValue {{ color: {FG_TEXT}; font-size: 28px; font-weight: 600; }}
        """)

    def animate_to(self, target_value: int, duration_ms: int = 700):
        try: current = int(self.valueLabel.text())
        except ValueError: current = 0
        steps = max(1, int(duration_ms / 16))
        delta = (target_value - current) / steps
        i = 0
        def tick():
            nonlocal i, current
            i += 1; current += delta
            if i >= steps:
                self.valueLabel.setText(str(target_value)); timer.stop()
            else:
                self.valueLabel.setText(str(int(current)))
        timer = QTimer(self); timer.timeout.connect(tick); timer.start(16)

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        wrapper = QVBoxLayout(self); wrapper.setContentsMargins(0, 0, 0, 0); wrapper.setSpacing(12)
        header = QLabel("Dashboard"); header.setObjectName("PageHeader")
        row = QHBoxLayout(); row.setSpacing(12)
        self.cardClients = StatsCard("KUNDEN", 0, ACCENT)
        self.cardInvoicesOpen = StatsCard("OFFENE KUNDENRECHNUNGEN", 0, WARN)
        self.cardOwnOpen = StatsCard("EIGENE OFFENE RECHNUNGEN", 0, ERROR)
        self.cardDomains = StatsCard("VERFÜGBARE DOMAINS", "—", SUCCESS)
        for c in (self.cardClients, self.cardInvoicesOpen, self.cardOwnOpen, self.cardDomains): c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.cardClients); row.addWidget(self.cardInvoicesOpen); row.addWidget(self.cardOwnOpen); row.addWidget(self.cardDomains)
        wrapper.addWidget(header); rowWidget = QWidget(); rowWidget.setLayout(row); wrapper.addWidget(rowWidget)
        placeholder = QFrame(); placeholder.setObjectName("Placeholder"); placeholder.setMinimumHeight(280)
        placeholder.setStyleSheet(f"QFrame#Placeholder {{ background-color: {BG_PANEL}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; }}")
        phLay = QVBoxLayout(placeholder); phLay.setContentsMargins(16, 16, 16, 16)
        phTitle = QLabel("Kürzlich aktualisiert (Platzhalter)"); phTitle.setStyleSheet(f"color: {FG_MUTED}; font-size: 13px;")
        phLay.addWidget(phTitle); wrapper.addWidget(placeholder)
        self.setStyleSheet(f"QLabel#PageHeader {{ color: {FG_TEXT}; font-size: 20px; font-weight: 600; padding: 4px 8px; }}")
        QTimer.singleShot(300, lambda: self.cardClients.animate_to(12))
        QTimer.singleShot(400, lambda: self.cardInvoicesOpen.animate_to(3))
        QTimer.singleShot(500, lambda: self.cardOwnOpen.animate_to(1))

class PlaceholderPage(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        header = QLabel(title); header.setStyleSheet(f"color: {FG_TEXT}; font-size: 20px; font-weight: 600; padding: 4px 8px;")
        lay.addWidget(header); body = QLabel("Inhalt folgt …"); body.setStyleSheet(f"color: {FG_MUTED}; font-size: 14px; padding: 8px;"); lay.addWidget(body)

class SideButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True); self.setCursor(Qt.PointingHandCursor); self.setMinimumHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{ color: {FG_TEXT}; background-color: transparent; border: none; text-align: left; padding: 8px 12px; border-radius: 8px; font-size: 14px; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.06); }}
            QPushButton:checked {{ background-color: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.45); }}
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digitale Alchemy Studio"); self.resize(1180, 740)
        self._fadeAnims = []
        central = QFrame(); central.setObjectName("Central"); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(220)
        sideLay = QVBoxLayout(sidebar); sideLay.setContentsMargins(12, 16, 12, 16); sideLay.setSpacing(6)
        appTitle = QLabel("Digitale\nAlchemy Studio"); appTitle.setStyleSheet(f"color: {FG_TEXT}; font-size: 18px; font-weight: 700;"); appTitle.setWordWrap(True)
        sideLay.addWidget(appTitle); sideLay.addSpacing(8)
        self.btnDashboard = SideButton("Dashboard"); self.btnClients = SideButton("Kunden"); self.btnInvoices = SideButton("Rechnungen")
        self.btnDomains = SideButton("Domains"); self.btnContracts = SideButton("Verträge"); self.btnSettings = SideButton("Einstellungen")
        for b in (self.btnDashboard, self.btnClients, self.btnInvoices, self.btnDomains, self.btnContracts, self.btnSettings): sideLay.addWidget(b)
        sideLay.addStretch(1)
        mainArea = QFrame(); mainArea.setObjectName("MainArea"); mainLay = QVBoxLayout(mainArea); mainLay.setContentsMargins(16, 16, 16, 16); mainLay.setSpacing(12)
        header = QFrame(); header.setObjectName("Header"); headerLay = QHBoxLayout(header); headerLay.setContentsMargins(12, 12, 12, 12); headerLay.setSpacing(8)
        hdrTitle = QLabel("Übersicht"); hdrTitle.setStyleSheet(f"color: {FG_TEXT}; font-size: 16px; font-weight: 600;"); headerLay.addWidget(hdrTitle); headerLay.addStretch(1)
        self.stack = QStackedWidget()
        self.pageDashboard = DashboardPage(); self.pageClients = PlaceholderPage("Kunden"); self.pageInvoices = PlaceholderPage("Rechnungen")
        self.pageDomains = PlaceholderPage("Domains"); self.pageContracts = PlaceholderPage("Verträge"); self.pageSettings = PlaceholderPage("Einstellungen")
        for p in (self.pageDashboard, self.pageClients, self.pageInvoices, self.pageDomains, self.pageContracts, self.pageSettings): self.stack.addWidget(p)
        mainLay.addWidget(header); mainLay.addWidget(self.stack)
        root.addWidget(sidebar); root.addWidget(mainArea, 1)
        self.btnDashboard.clicked.connect(lambda: self.switch_page(0, self.btnDashboard))
        self.btnClients.clicked.connect(lambda: self.switch_page(1, self.btnClients))
        self.btnInvoices.clicked.connect(lambda: self.switch_page(2, self.btnInvoices))
        self.btnDomains.clicked.connect(lambda: self.switch_page(3, self.btnDomains))
        self.btnContracts.clicked.connect(lambda: self.switch_page(4, self.btnContracts))
        self.btnSettings.clicked.connect(lambda: self.switch_page(5, self.btnSettings))
        self.btnDashboard.setChecked(True)
        self.apply_theme()
        viewMenu = self.menuBar().addMenu("Ansicht")
        toggleAct = QAction("Dunkles Theme (Standard)", self, checkable=True, checked=True); toggleAct.triggered.connect(self.toggle_theme)
        viewMenu.addAction(toggleAct)

    def apply_theme(self, dark: bool = True):
        base_bg = BG_DARK if dark else "#F5F7FB"; base_text = FG_TEXT if dark else "#111827"; panel = BG_PANEL if dark else "#FFFFFF"
        border = "rgba(0,0,0,0.08)" if not dark else "rgba(255,255,255,0.06)"
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {base_bg}; }}
            QFrame#Sidebar {{ background-color: {panel}; border-right: 1px solid {border}; }}
            QFrame#MainArea {{ background-color: {base_bg}; }}
            QFrame#Header {{ background-color: {panel}; border: 1px solid {border}; border-radius: 12px; }}
            QMenuBar, QMenu {{ background-color: {panel}; color: {base_text}; }}
            QMenu::item:selected {{ background: rgba(139, 92, 246, 0.15); }}
        """)
        font = QFont(); font.setPointSize(10); QApplication.instance().setFont(font)

    def toggle_theme(self, checked: bool):
        self.apply_theme(dark=checked)

    def switch_page(self, index: int, btn: QPushButton):
        for b in (self.btnDashboard, self.btnClients, self.btnInvoices, self.btnDomains, self.btnContracts, self.btnSettings):
            b.setChecked(b is btn)
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        eff = QGraphicsOpacityEffect(page); page.setGraphicsEffect(eff); eff.setOpacity(0.0)
        anim = QPropertyAnimation(eff, b"opacity", self); anim.setDuration(200); anim.setStartValue(0.0); anim.setEndValue(1.0); anim.setEasingCurve(QEasingCurve.InOutCubic); anim.start()

# ----------------------------- App Start -----------------------------
def main():
    app = QApplication([])

    # Erststart? -> Setup Dialog (Passwort setzen + Backend wählen)
    if not auth.credentials_exist(auth.DEFAULT_USER):
        setup = FirstRunDialog()
        if setup.exec() != QDialog.Accepted:
            return 0  # Abbruch
        # Wenn Setup ok war, sind jetzt Backend+Hash gesetzt

    # Login
    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        return 0

    win = MainWindow(); win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
