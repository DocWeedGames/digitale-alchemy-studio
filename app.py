# app.py (bereinigt, konsistente 4 Leerzeichen, QDialog.Accepted)
import os
import sys
import ctypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QGraphicsDropShadowEffect,
    QSplashScreen,
    QMessageBox,
    QDialog,
)

from login_dialog import LoginDialog
from auth import (
    app_data_dir,
    load_config,
    save_config,
    load_users,
    ensure_default_admin,
    verify_token,
)

APP_NAME = "Digitale Alchemy Studio"
APP_DIR = Path(__file__).resolve().parent
ASSETS = APP_DIR / "assets"

ACCENT = "#A8FF00"
ACCENT2 = "#21C7F7"
BG_DARK = "#0E1116"


def set_windows_appid(appid: str):
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
    except Exception:
        pass


def load_app_icon() -> QIcon:
    ico = ASSETS / "app_icon.ico"
    if ico.exists():
        return QIcon(str(ico))
    icon = QIcon()
    for size in (256, 128, 64, 32):
        p = ASSETS / f"logo_app_{size}.png"
        if p.exists():
            icon.addFile(str(p), size=(size, size))
    return icon


def stylesheet() -> str:
    return f"""
    QWidget {{
        background: {BG_DARK};
        color: #E8F0F2;
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
        font-size: 13px;
    }}
    QTabBar::tab {{ padding: 8px 14px; border-bottom: 2px solid transparent; color: #CFE6D4; }}
    QTabBar::tab:selected {{ color: white; border-color: {ACCENT}; }}
    QPushButton {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2});
        border: none; color: #081015; padding: 10px 14px; border-radius: 8px; font-weight: 600;
    }}
    QPushButton:hover {{ filter: brightness(1.06); }}
    QLineEdit, QComboBox, QTextEdit {{ background: #141923; border: 1px solid #243041; border-radius: 6px; padding: 8px 10px; }}
    """


class MainWindow(QMainWindow):
    def __init__(self, username: str = "unbekannt"):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"{APP_NAME} – {self.username}")
        self.setWindowIcon(load_app_icon())

        # Header mit Banner/Logo
        header = QWidget()
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(18, 14, 18, 8)

        banner_label = QLabel()
        banner_path = ASSETS / "logo_header_160.png"
        fallback_glow = ASSETS / "logo_glow.png"
        fallback_plain = ASSETS / "logo_transparent.png"

        if banner_path.exists():
            banner = QPixmap(str(banner_path))
        elif fallback_glow.exists():
            banner = QPixmap(str(fallback_glow)).scaledToHeight(140, Qt.SmoothTransformation)
        else:
            banner = QPixmap(str(fallback_plain)).scaledToHeight(120, Qt.SmoothTransformation)

        banner_label.setPixmap(banner)
        banner_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        shadow = QGraphicsDropShadowEffect(blurRadius=32, xOffset=0, yOffset=0)
        shadow.setColor(Qt.black)
        banner_label.setGraphicsEffect(shadow)

        actions = QHBoxLayout()
        user_lbl = QLabel(f"Angemeldet: <b>{self.username}</b>")
        btn_logout = QPushButton("Logout")
        actions.addWidget(user_lbl)
        actions.addWidget(btn_logout)
        wrap = QWidget()
        wrap.setLayout(actions)

        hbox.addWidget(banner_label, 1)
        hbox.addWidget(wrap, 0, Qt.AlignRight | Qt.AlignVCenter)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(QWidget(), "Dashboard")
        tabs.addTab(QWidget(), "Kunden")
        tabs.addTab(QWidget(), "Rechnungen")
        tabs.addTab(QWidget(), "Domains")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header)
        layout.addWidget(tabs)
        self.setCentralWidget(root)
        self.resize(1240, 780)

        btn_logout.clicked.connect(self.logout)

    def logout(self):
        cfg = load_config()
        cfg.pop("remember_user", None)
        cfg.pop("remember_token", None)
        save_config(cfg)
        QMessageBox.information(self, "Logout", "Du wurdest abgemeldet. Die App wird neu gestartet.")
        python = sys.executable
        os.execl(python, python, *sys.argv)


def show_splash():
    splash_img = ASSETS / "logo_glow.png"
    if not splash_img.exists():
        return None
    pix = QPixmap(str(splash_img)).scaledToHeight(260, Qt.SmoothTransformation)
    splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint)
    splash.setMask(pix.mask())
    splash.showMessage("Lade Module …", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)
    splash.show()
    return splash


def try_auto_login() -> str | None:
    if os.getenv("DA_DEV") == "1":
        return "dev"
    cfg = load_config()
    u = cfg.get("remember_user")
    t = cfg.get("remember_token")
    if not u or not t:
        return None
    users = ensure_default_admin(load_users())
    return u if verify_token(users, u, t) else None


def main():
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    set_windows_appid("de.digitalealchemie.studio")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(stylesheet())

    splash = show_splash()

    # --- Login-Flow ---
    username = try_auto_login()
    if not username:
        dlg = LoginDialog()
        # Splash sichtbar lassen, aber darunter
        if dlg.exec() != QDialog.Accepted:
            # Abbruch -> App beenden
            sys.exit(0)
        username = getattr(dlg, "username", "unbekannt")

    win = MainWindow(username=username)

    def _show():
        if splash:
            splash.finish(win)
        win.show()

    QTimer.singleShot(300, _show)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
