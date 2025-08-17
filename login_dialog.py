# login_dialog.py
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QMessageBox
)
from auth import (
    authenticate, change_password, load_users, ensure_default_admin,
    new_remember_token, attach_token, load_config, save_config
)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anmelden")
        self.setModal(True)
        self.resize(420, 220)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 14)
        v.setSpacing(10)

        title = QLabel("<b>Digitale Alchemy Studio</b><br><span style='color:#8f9fb2'>Bitte anmelden</span>")
        v.addWidget(title)

        self.user = QLineEdit(self); self.user.setPlaceholderText("Benutzername")
        self.pw = QLineEdit(self); self.pw.setPlaceholderText("Passwort"); self.pw.setEchoMode(QLineEdit.Password)
        self.remember = QCheckBox("Angemeldet bleiben", self)

        v.addWidget(self.user)
        v.addWidget(self.pw)
        v.addWidget(self.remember)

        h = QHBoxLayout()
        h.addStretch(1)
        self.btn_login = QPushButton("Login", self)
        self.btn_cancel = QPushButton("Abbrechen", self)
        h.addWidget(self.btn_cancel); h.addWidget(self.btn_login)
        v.addLayout(h)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_login.clicked.connect(self.try_login)

        # Default-Admin sicherstellen (falls erste Ausführung)
        users = ensure_default_admin(load_users())
        if "admin" in users and users["admin"].must_change_pw:
            self.user.setText("admin")

    def try_login(self):
        u = self.user.text().strip()
        p = self.pw.text()

        ok, msg = authenticate(u, p)
        if not ok:
            if msg:
                QMessageBox.warning(self, "Login fehlgeschlagen", msg)
            return

        # Passwortwechsel erforderlich?
        users = ensure_default_admin(load_users())
        if users[u].must_change_pw:
            dlg = ChangePasswordDialog(u, parent=self)
            if dlg.exec() != QDialog.Accepted:
                return  # Abbruch -> zurück zu Login

        # Remember me Token
        if self.remember.isChecked():
            cfg = load_config()
            token = new_remember_token()
            attach_token(users, u, token)
            cfg["remember_user"] = u
            cfg["remember_token"] = token
            save_config(cfg)

        self.accept()
        self.username = u  # verfügbar für Aufrufer

class ChangePasswordDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Passwort ändern (erforderlich)")
        self.setModal(True)
        self.resize(440, 240)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 14)
        v.setSpacing(10)

        v.addWidget(QLabel(f"<b>Hallo {username}</b><br>Bitte ein neues Passwort setzen."))

        self.old = QLineEdit(self); self.old.setPlaceholderText("Altes Passwort"); self.old.setEchoMode(QLineEdit.Password)
        self.new1 = QLineEdit(self); self.new1.setPlaceholderText("Neues Passwort"); self.new1.setEchoMode(QLineEdit.Password)
        self.new2 = QLineEdit(self); self.new2.setPlaceholderText("Neues Passwort wiederholen"); self.new2.setEchoMode(QLineEdit.Password)

        v.addWidget(self.old); v.addWidget(self.new1); v.addWidget(self.new2)

        h = QHBoxLayout(); h.addStretch(1)
        ok = QPushButton("Speichern", self)
        cancel = QPushButton("Abbrechen", self)
        h.addWidget(cancel); h.addWidget(ok)
        v.addLayout(h)

        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.save_pw)

    def save_pw(self):
        if self.new1.text() != self.new2.text():
            QMessageBox.warning(self, "Fehler", "Die neuen Passwörter stimmen nicht überein.")
            return
        ok, msg = change_password(self.username, self.old.text(), self.new1.text())
        if not ok:
            QMessageBox.warning(self, "Fehler", msg or "Unbekannter Fehler.")
            return
        QMessageBox.information(self, "Erfolg", "Passwort geändert.")
        self.accept()
