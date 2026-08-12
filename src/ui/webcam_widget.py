"""On-demand local webcam preview for the Bundle Test dialog."""

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtMultimedia import QCamera, QCameraInfo, QCameraViewfinderSettings
from PyQt5.QtMultimediaWidgets import QCameraViewfinder
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WebcamWidget(QWidget):
    """Preview a selected local camera without starting it automatically."""

    RESOLUTIONS = (
        ("640 x 480 (Standard)", 640, 480),
        ("1280 x 720 (HD - Recommended)", 1280, 720),
        ("1920 x 1080 (Full HD)", 1920, 1080),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera = None
        self.camera_infos = []

        title = QLabel("Webcam Preview")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        description = QLabel(
            "Preview the DUT and instrument setup locally. The camera remains "
            "off until Start Preview is selected and stops when this tab is hidden. "
            "Do not start this preview while FFmpeg/Blynk is using the same camera."
        )
        description.setWordWrap(True)

        self.camera_selector = QComboBox()
        self.resolution_selector = QComboBox()
        for label, width, height in self.RESOLUTIONS:
            self.resolution_selector.addItem(label, (width, height))
        self.resolution_selector.setCurrentIndex(1)
        self.refresh_button = QPushButton("Refresh Cameras")
        self.start_button = QPushButton("Start Preview")
        self.stop_button = QPushButton("Stop Preview")
        self.stop_button.setEnabled(False)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Camera:"))
        controls.addWidget(self.camera_selector, stretch=1)
        controls.addWidget(QLabel("Resolution:"))
        controls.addWidget(self.resolution_selector)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)

        self.viewfinder = QCameraViewfinder()
        self.viewfinder.setMinimumSize(640, 360)
        self.viewfinder.setStyleSheet("background-color: black;")
        self.viewfinder.setAspectRatioMode(Qt.KeepAspectRatio)

        self.status_label = QLabel("Camera is off.")
        self.status_label.setStyleSheet("color: #555555;")

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(controls)
        layout.addWidget(self.viewfinder, stretch=1)
        layout.addWidget(self.status_label)

        self.refresh_button.clicked.connect(self.refresh_cameras)
        self.start_button.clicked.connect(self.start_preview)
        self.stop_button.clicked.connect(self.stop_preview)
        self.camera_selector.currentIndexChanged.connect(self._camera_changed)
        self.refresh_cameras()

    @property
    def preview_active(self):
        return self.camera is not None

    def refresh_cameras(self):
        self.stop_preview()
        self.camera_infos = list(QCameraInfo.availableCameras())
        self.camera_selector.clear()
        self.camera_selector.addItems(
            camera.description() for camera in self.camera_infos
        )
        available = bool(self.camera_infos)
        self.camera_selector.setEnabled(available)
        self.start_button.setEnabled(available)
        self.status_label.setText(
            f"Found {len(self.camera_infos)} camera(s). Camera is off."
            if available
            else "No local webcam was detected."
        )

    def start_preview(self):
        index = self.camera_selector.currentIndex()
        if index < 0 or index >= len(self.camera_infos):
            self.status_label.setText("Select an available webcam first.")
            return

        self.stop_preview()
        self.camera = QCamera(self.camera_infos[index], self)
        self.camera.load()
        selected_resolution = self._selected_supported_resolution()
        settings = QCameraViewfinderSettings()
        settings.setResolution(selected_resolution)
        self.camera.setViewfinderSettings(settings)
        self.camera.setViewfinder(self.viewfinder)
        self.camera.error.connect(self._camera_error)
        self.camera.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.camera_selector.setEnabled(False)
        self.resolution_selector.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.status_label.setText(
            f"Previewing {self.camera_infos[index].description()} at "
            f"{selected_resolution.width()} x {selected_resolution.height()}."
        )

    def stop_preview(self):
        if self.camera is not None:
            self.camera.stop()
            self.camera.deleteLater()
            self.camera = None
        available = bool(self.camera_infos)
        self.start_button.setEnabled(available)
        self.stop_button.setEnabled(False)
        self.camera_selector.setEnabled(available)
        self.resolution_selector.setEnabled(True)
        self.refresh_button.setEnabled(True)
        if available:
            self.status_label.setText("Camera is off.")

    def _camera_changed(self, _index):
        if self.preview_active:
            self.stop_preview()

    def _selected_supported_resolution(self):
        width, height = self.resolution_selector.currentData()
        requested = QSize(width, height)
        supported = self.camera.supportedViewfinderResolutions()
        if not supported or requested in supported:
            return requested
        requested_pixels = width * height
        return min(
            supported,
            key=lambda resolution: abs(
                resolution.width() * resolution.height() - requested_pixels
            ),
        )

    def _camera_error(self, _error):
        message = self.camera.errorString() if self.camera is not None else ""
        self.stop_preview()
        self.status_label.setText(
            "Camera unavailable"
            + (f": {message}" if message else ".")
            + " Stop FFmpeg/Blynk if it is using the same webcam."
        )

    def hideEvent(self, event):
        self.stop_preview()
        super().hideEvent(event)
