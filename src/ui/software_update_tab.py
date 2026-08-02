"""Software update controls for the main GUI."""

import traceback

from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from updater.update_service import (
    ApplicationUpdateService,
    UpdateStatus,
)


class UpdateCheckWorker(QThread):
    completed = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, manifest_source):
        super().__init__()
        self.manifest_source = manifest_source

    def run(self):
        try:
            service = ApplicationUpdateService(self.manifest_source)
            self.completed.emit(service.check())
        except Exception as exception:
            self.error.emit(f"{exception}\n\n{traceback.format_exc()}")


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, service, status):
        super().__init__()
        self.service = service
        self.status = status

    def run(self):
        try:
            package = self.service.stage(
                self.status,
                self._report_progress,
            )
            self.completed.emit(package)
        except Exception as exception:
            self.error.emit(f"{exception}\n\n{traceback.format_exc()}")

    def _report_progress(self, downloaded, total):
        if total > 0:
            self.progress.emit(min(100, int(downloaded * 100 / total)))


class SoftwareUpdateTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = ApplicationUpdateService()
        self.status = None
        self.worker = None
        self._automatic_check_completed = False
        self._silent_operation = False

        self.current_version = QLabel(self.service.current_version)
        self.available_version = QLabel("Not checked")
        self.manifest_source = QLineEdit(self.service.manifest_source)
        self.manifest_source.setPlaceholderText(
            r"\\server\share\update_manifest.json or https://..."
        )
        self.auto_check = QCheckBox("Check automatically after startup")
        self.auto_check.setChecked(True)

        settings_group = QGroupBox("Update Source")
        settings_layout = QFormLayout(settings_group)
        settings_layout.addRow("Installed Version:", self.current_version)
        settings_layout.addRow("Available Version:", self.available_version)
        settings_layout.addRow("Manifest Path / URL:", self.manifest_source)
        settings_layout.addRow(self.auto_check)

        self.save_button = QPushButton("Save Source")
        self.check_button = QPushButton("Check for Updates")
        self.install_button = QPushButton("Download and Install")
        self.install_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_source)
        self.check_button.clicked.connect(self.check_for_updates)
        self.install_button.clicked.connect(self.download_and_install)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.install_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status_label = QLabel("Configure an update manifest source.")
        self.status_label.setWordWrap(True)
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setPlaceholderText("Release notes appear here.")

        layout = QVBoxLayout(self)
        layout.addWidget(settings_group)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("Release Notes:"))
        layout.addWidget(self.release_notes, stretch=1)

    def check_automatically(self):
        if (
            self._automatic_check_completed
            or not self.auto_check.isChecked()
            or not self.manifest_source.text().strip()
        ):
            return
        self._automatic_check_completed = True
        QTimer.singleShot(
            0,
            lambda: self.check_for_updates(silent=True),
        )

    def _set_busy(self, busy):
        self.save_button.setEnabled(not busy)
        self.check_button.setEnabled(not busy)
        self.install_button.setEnabled(
            not busy
            and self.status is not None
            and self.status.update_available
        )

    def _save_source(self):
        source = self.manifest_source.text().strip()
        path = ApplicationUpdateService.save_manifest_source(source)
        self.service = ApplicationUpdateService(source)
        self.status_label.setText(f"Update source saved: {path}")

    def check_for_updates(self, _checked=False, silent=False):
        source = self.manifest_source.text().strip()
        if not source:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Update Source Required",
                    "Enter a network manifest path or HTTPS URL.",
                )
            return
        self._silent_operation = bool(silent)
        self.status = None
        self._save_source()
        self.progress.setValue(0)
        self.status_label.setText("Checking for updates...")
        self._set_busy(True)
        self.worker = UpdateCheckWorker(source)
        self.worker.completed.connect(self._check_completed)
        self.worker.error.connect(self._operation_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _check_completed(self, status):
        self.status = status
        self.available_version.setText(status.manifest.version)
        self.release_notes.setPlainText(status.manifest.release_notes)
        if status.update_available:
            self.status_label.setText(
                f"Version {status.manifest.version} is available."
            )
        else:
            self.status_label.setText(
                f"Version {status.current_version} is up to date."
            )

    def download_and_install(self):
        if self.status is None or not self.status.update_available:
            return
        answer = QMessageBox.question(
            self,
            "Install Update",
            "The application will close after the verified update is "
            "downloaded. Continue?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        self._silent_operation = False
        self.progress.setValue(0)
        self.status_label.setText("Downloading and verifying update...")
        self._set_busy(True)
        self.worker = UpdateDownloadWorker(self.service, self.status)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.completed.connect(self._download_completed)
        self.worker.error.connect(self._operation_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _download_completed(self, package_path):
        try:
            self.service.launch_installer(package_path, self.status)
        except Exception as exception:
            self._operation_failed(
                f"{exception}\n\n{traceback.format_exc()}"
            )
            return
        self.progress.setValue(100)
        self.status_label.setText(
            "Update verified. Closing application for installation..."
        )
        QTimer.singleShot(300, QApplication.instance().quit)

    def _operation_failed(self, details):
        message = str(details).split("\n", 1)[0]
        self.status_label.setText(f"Update failed: {message}")
        if not self._silent_operation:
            QMessageBox.critical(self, "Software Update Error", details)

    def _worker_finished(self):
        self.worker = None
        self._silent_operation = False
        self._set_busy(False)
