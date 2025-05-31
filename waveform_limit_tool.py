import sys
import csv
import math
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QWidget, QPushButton, QLabel, QLineEdit, QFileDialog, 
                              QMessageBox, QGroupBox, QGridLayout, QTextEdit, QSplitter,
                              QGraphicsView, QGraphicsScene, QComboBox, QCheckBox,
                              QDialog, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
                              QHeaderView, QDialogButtonBox)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPolygonF, QCursor


class LimitDesignerDialog(QDialog):
    def __init__(self, parent=None, time_data=None, waveform_data=None, existing_limits=None):
        super().__init__(parent)
        self.setWindowTitle("Limit Array Designer")
        self.setGeometry(200, 200, 900, 700)
        
        # Data storage
        self.num_points = 10
        self.time_points = []
        self.high_limits = []
        self.low_limits = []
        
        # Use actual waveform data if provided, otherwise generate sample data
        if time_data is not None and waveform_data is not None:
            self.sample_time = time_data.copy()
            self.sample_data = waveform_data.copy()
            self.has_real_data = True
        else:
            self.sample_data = []
            self.sample_time = []
            self.has_real_data = False
        
        # Store existing limits to reload them
        self.existing_limits = existing_limits
        
        # Plot settings
        self.drawing_mode = None  # 'high', 'low', or None
        self.plot_rect = QRectF()
        self.margin = 50
        
        self.setup_ui()
        
        if not self.has_real_data:
            self.generate_sample_data()
        else:
            self.load_existing_or_initialize_limits()
            self.update_plot()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls section
        controls_group = QGroupBox("Limit Array Settings")
        controls_layout = QGridLayout(controls_group)
        
        controls_layout.addWidget(QLabel("Number of Points:"), 0, 0)
        self.points_spinbox = QSpinBox()
        self.points_spinbox.setRange(2, 100)
        self.points_spinbox.setValue(10)
        self.points_spinbox.valueChanged.connect(self.on_points_changed)
        controls_layout.addWidget(self.points_spinbox, 0, 1)
        
        self.generate_sample_btn = QPushButton("Generate New Sample Data")
        self.generate_sample_btn.clicked.connect(self.generate_sample_data)
        self.generate_sample_btn.setEnabled(not self.has_real_data)  # Disable if using real data
        controls_layout.addWidget(self.generate_sample_btn, 0, 2)
        
        controls_layout.addWidget(QLabel("Drawing Mode:"), 1, 0)
        self.high_limit_btn = QPushButton("Draw High Limits")
        self.high_limit_btn.setCheckable(True)
        self.high_limit_btn.clicked.connect(lambda: self.set_drawing_mode('high'))
        controls_layout.addWidget(self.high_limit_btn, 1, 1)
        
        self.low_limit_btn = QPushButton("Draw Low Limits")
        self.low_limit_btn.setCheckable(True)
        self.low_limit_btn.clicked.connect(lambda: self.set_drawing_mode('low'))
        controls_layout.addWidget(self.low_limit_btn, 1, 2)
        
        self.clear_btn = QPushButton("Clear All Limits")
        self.clear_btn.clicked.connect(self.clear_limits)
        controls_layout.addWidget(self.clear_btn, 2, 0)
        
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_to_default)
        controls_layout.addWidget(self.reset_btn, 2, 1)
        
        layout.addWidget(controls_group)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()
        
        # Plot tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        
        self.plot_widget = LimitPlotWidget()
        self.plot_widget.point_clicked.connect(self.on_plot_clicked)
        plot_layout.addWidget(self.plot_widget)
        
        if self.has_real_data:
            instructions_text = "Instructions: Designing limits for your loaded waveform data. Select drawing mode above, then click on the plot to set limit points. Red line = High limits, Blue line = Low limits"
        else:
            instructions_text = "Instructions: Select drawing mode above, then click on the plot to set limit points. Red line = High limits, Blue line = Low limits"
            
        instructions = QLabel(instructions_text)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        plot_layout.addWidget(instructions)
        
        self.tab_widget.addTab(plot_tab, "Interactive Plot")
        
        # Table tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Time", "High Limit", "Low Limit"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellChanged.connect(self.on_table_changed)
        table_layout.addWidget(self.table)
        
        table_buttons = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.clicked.connect(self.add_table_row)
        table_buttons.addWidget(self.add_row_btn)
        
        self.remove_row_btn = QPushButton("Remove Row")
        self.remove_row_btn.clicked.connect(self.remove_table_row)
        table_buttons.addWidget(self.remove_row_btn)
        
        table_buttons.addStretch()
        table_layout.addLayout(table_buttons)
        
        self.tab_widget.addTab(table_tab, "Manual Entry")
        
        layout.addWidget(self.tab_widget)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initialize data
        self.on_points_changed()
        
    def set_drawing_mode(self, mode):
        """Set the current drawing mode"""
        self.drawing_mode = mode
        self.high_limit_btn.setChecked(mode == 'high')
        self.low_limit_btn.setChecked(mode == 'low')
        
        if mode == 'high':
            self.setCursor(QCursor(Qt.CrossCursor))
        elif mode == 'low':
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            
    def on_points_changed(self):
        """Handle change in number of points"""
        self.num_points = self.points_spinbox.value()
        
        # Only reinitialize if the number of points has actually changed from existing data
        if self.existing_limits and len(self.existing_limits['time_points']) == self.num_points:
            # Keep existing limits if the point count matches
            return
        
        if self.has_real_data:
            self.initialize_limits_from_data()
        else:
            self.initialize_limits()
        self.update_plot()
        self.update_table()
        
    def initialize_limits(self):
        """Initialize limit arrays with default values"""
        if self.has_real_data and self.sample_time:
            # Use actual data time range
            time_min, time_max = min(self.sample_time), max(self.sample_time)
            self.time_points = [time_min + i * (time_max - time_min) / (self.num_points - 1) for i in range(self.num_points)]
        else:
            # Use default time range
            self.time_points = [i * 10.0 / (self.num_points - 1) for i in range(self.num_points)]
        self.high_limits = [2.0] * self.num_points
        self.low_limits = [-2.0] * self.num_points
        
    def load_existing_or_initialize_limits(self):
        """Load existing limits if available, otherwise initialize new ones"""
        if self.existing_limits:
            # Load existing limit arrays
            self.time_points = self.existing_limits['time_points'].copy()
            self.high_limits = self.existing_limits['high_limits'].copy()
            self.low_limits = self.existing_limits['low_limits'].copy()
            self.num_points = len(self.time_points)
            self.points_spinbox.blockSignals(True)  # Prevent triggering on_points_changed
            self.points_spinbox.setValue(self.num_points)
            self.points_spinbox.blockSignals(False)
            self.update_table()  # Update table with loaded values
        else:
            # Initialize new limits from data
            self.initialize_limits_from_data()
        
    def initialize_limits_from_data(self):
        """Initialize limits based on actual waveform data"""
        if not self.sample_data or not self.sample_time:
            self.initialize_limits()
            return
            
        time_min, time_max = min(self.sample_time), max(self.sample_time)
        amp_min, amp_max = min(self.sample_data), max(self.sample_data)
        amp_range = amp_max - amp_min
        
        # Create time points across the data range
        self.time_points = [time_min + i * (time_max - time_min) / (self.num_points - 1) for i in range(self.num_points)]
        
        # Set initial limits with some margin above/below the data
        margin = amp_range * 0.2 if amp_range > 0 else 1.0
        self.high_limits = [amp_max + margin] * self.num_points
        self.low_limits = [amp_min - margin] * self.num_points
        
    def generate_sample_data(self):
        """Generate sample waveform data"""
        self.sample_time = [i * 0.1 for i in range(101)]  # 0 to 10 seconds
        self.sample_data = []
        
        for t in self.sample_time:
            # Create a complex waveform with multiple frequency components
            value = (math.sin(t * 2) * 1.5 + 
                    math.sin(t * 5) * 0.8 + 
                    math.sin(t * 0.5) * 0.5 +
                    random.uniform(-0.2, 0.2))  # Add some noise
            self.sample_data.append(value)
            
        self.update_plot()
        
    def clear_limits(self):
        """Clear all limit points"""
        self.high_limits = [0.0] * self.num_points
        self.low_limits = [0.0] * self.num_points
        self.update_plot()
        self.update_table()
        
    def reset_to_default(self):
        """Reset to default limit values"""
        if self.has_real_data:
            self.initialize_limits_from_data()
        else:
            self.initialize_limits()
        self.update_plot()
        self.update_table()
        
    def on_plot_clicked(self, time_val, amp_val):
        """Handle plot click events"""
        if self.drawing_mode is None:
            return
            
        # Find the closest time point
        closest_idx = 0
        min_distance = abs(self.time_points[0] - time_val)
        
        for i, t in enumerate(self.time_points):
            distance = abs(t - time_val)
            if distance < min_distance:
                min_distance = distance
                closest_idx = i
                
        # Update the appropriate limit
        if self.drawing_mode == 'high':
            self.high_limits[closest_idx] = amp_val
        elif self.drawing_mode == 'low':
            self.low_limits[closest_idx] = amp_val
            
        self.update_plot()
        self.update_table()
        
    def update_plot(self):
        """Update the plot display"""
        self.plot_widget.set_data(
            self.sample_time, self.sample_data,
            self.time_points, self.high_limits, self.low_limits
        )
        
    def update_table(self):
        """Update the table with current limit values"""
        self.table.blockSignals(True)  # Prevent infinite recursion
        
        self.table.setRowCount(len(self.time_points))
        
        for i, (t, h, l) in enumerate(zip(self.time_points, self.high_limits, self.low_limits)):
            self.table.setItem(i, 0, QTableWidgetItem(f"{t:.2f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{h:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{l:.2f}"))
            
        self.table.blockSignals(False)
        
    def on_table_changed(self, row, col):
        """Handle table cell changes"""
        try:
            value = float(self.table.item(row, col).text())
            
            if col == 0:  # Time
                self.time_points[row] = value
            elif col == 1:  # High limit
                self.high_limits[row] = value
            elif col == 2:  # Low limit
                self.low_limits[row] = value
                
            self.update_plot()
            
        except (ValueError, AttributeError):
            # Restore previous value if invalid
            self.update_table()
            
    def add_table_row(self):
        """Add a new row to the table"""
        self.time_points.append(max(self.time_points) + 1.0 if self.time_points else 0.0)
        self.high_limits.append(2.0)
        self.low_limits.append(-2.0)
        self.num_points = len(self.time_points)
        self.points_spinbox.setValue(self.num_points)
        self.update_table()
        self.update_plot()
        
    def remove_table_row(self):
        """Remove the last row from the table"""
        if len(self.time_points) > 2:
            self.time_points.pop()
            self.high_limits.pop()
            self.low_limits.pop()
            self.num_points = len(self.time_points)
            self.points_spinbox.setValue(self.num_points)
            self.update_table()
            self.update_plot()
            
    def get_limit_arrays(self):
        """Return the current limit arrays"""
        return {
            'time_points': self.time_points.copy(),
            'high_limits': self.high_limits.copy(),
            'low_limits': self.low_limits.copy()
        }


class LimitPlotWidget(QGraphicsView):
    point_clicked = Signal(float, float)  # time, amplitude
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Data storage
        self.sample_time = []
        self.sample_data = []
        self.time_points = []
        self.high_limits = []
        self.low_limits = []
        
        # Plot settings
        self.margin = 50
        self.plot_rect = QRectF()
        
        # Setup view
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing)
        
    def set_data(self, sample_time, sample_data, time_points, high_limits, low_limits):
        """Set the data to be plotted"""
        self.sample_time = sample_time
        self.sample_data = sample_data
        self.time_points = time_points
        self.high_limits = high_limits
        self.low_limits = low_limits
        self.update_plot()
        
    def update_plot(self):
        """Update the plot with current data"""
        self.scene.clear()
        
        if not self.sample_data:
            return
            
        self.calculate_plot_rect()
        self.draw_grid()
        self.draw_axes()
        self.draw_sample_data()
        self.draw_limit_lines()
        self.draw_limit_points()
        self.draw_labels()
        
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
    def calculate_plot_rect(self):
        """Calculate the plotting rectangle"""
        if not self.sample_data:
            return
            
        time_min, time_max = min(self.sample_time), max(self.sample_time)
        amp_min, amp_max = min(self.sample_data), max(self.sample_data)
        
        # Include limit points in range
        if self.high_limits:
            amp_max = max(amp_max, max(self.high_limits))
        if self.low_limits:
            amp_min = min(amp_min, min(self.low_limits))
            
        # Add padding
        time_range = time_max - time_min if time_max != time_min else 1
        amp_range = amp_max - amp_min if amp_max != amp_min else 1
        
        self.time_min = time_min - time_range * 0.05
        self.time_max = time_max + time_range * 0.05
        self.amp_min = amp_min - amp_range * 0.1
        self.amp_max = amp_max + amp_range * 0.1
        
        self.plot_rect = QRectF(self.margin, self.margin, 700 - 2 * self.margin, 400 - 2 * self.margin)
        
    def data_to_scene(self, time_val, amp_val):
        """Convert data coordinates to scene coordinates"""
        if self.time_max == self.time_min or self.amp_max == self.amp_min:
            return QPointF(self.plot_rect.left(), self.plot_rect.bottom())
            
        x = self.plot_rect.left() + (time_val - self.time_min) / (self.time_max - self.time_min) * self.plot_rect.width()
        y = self.plot_rect.bottom() - (amp_val - self.amp_min) / (self.amp_max - self.amp_min) * self.plot_rect.height()
        return QPointF(x, y)
        
    def scene_to_data(self, scene_point):
        """Convert scene coordinates to data coordinates"""
        if self.time_max == self.time_min or self.amp_max == self.amp_min:
            return 0, 0
            
        time_val = self.time_min + (scene_point.x() - self.plot_rect.left()) / self.plot_rect.width() * (self.time_max - self.time_min)
        amp_val = self.amp_min + (self.plot_rect.bottom() - scene_point.y()) / self.plot_rect.height() * (self.amp_max - self.amp_min)
        return time_val, amp_val
        
    def draw_grid(self):
        """Draw grid lines"""
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        
        for i in range(6):
            x = self.plot_rect.left() + i * self.plot_rect.width() / 5
            self.scene.addLine(x, self.plot_rect.top(), x, self.plot_rect.bottom(), pen)
            
        for i in range(6):
            y = self.plot_rect.top() + i * self.plot_rect.height() / 5
            self.scene.addLine(self.plot_rect.left(), y, self.plot_rect.right(), y, pen)
            
    def draw_axes(self):
        """Draw axes"""
        pen = QPen(QColor(0, 0, 0), 2)
        self.scene.addLine(self.plot_rect.left(), self.plot_rect.bottom(), 
                          self.plot_rect.right(), self.plot_rect.bottom(), pen)
        self.scene.addLine(self.plot_rect.left(), self.plot_rect.top(), 
                          self.plot_rect.left(), self.plot_rect.bottom(), pen)
                          
    def draw_sample_data(self):
        """Draw the sample waveform"""
        if len(self.sample_time) < 2:
            return
            
        pen = QPen(QColor(100, 100, 100), 2)
        
        # Draw line segments instead of polygon to avoid connecting last to first
        for i in range(len(self.sample_time) - 1):
            p1 = self.data_to_scene(self.sample_time[i], self.sample_data[i])
            p2 = self.data_to_scene(self.sample_time[i + 1], self.sample_data[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            
    def draw_limit_lines(self):
        """Draw interpolated limit lines"""
        if len(self.time_points) < 2:
            return
            
        # High limit line - draw as connected line segments
        high_pen = QPen(QColor(200, 0, 0), 2, Qt.DashLine)
        for i in range(len(self.time_points) - 1):
            p1 = self.data_to_scene(self.time_points[i], self.high_limits[i])
            p2 = self.data_to_scene(self.time_points[i + 1], self.high_limits[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), high_pen)
            
        # Low limit line - draw as connected line segments
        low_pen = QPen(QColor(0, 0, 200), 2, Qt.DashLine)
        for i in range(len(self.time_points) - 1):
            p1 = self.data_to_scene(self.time_points[i], self.low_limits[i])
            p2 = self.data_to_scene(self.time_points[i + 1], self.low_limits[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), low_pen)
            
    def draw_limit_points(self):
        """Draw individual limit points"""
        # High limit points
        for t, h in zip(self.time_points, self.high_limits):
            point = self.data_to_scene(t, h)
            self.scene.addEllipse(point.x() - 4, point.y() - 4, 8, 8, 
                                 QPen(QColor(200, 0, 0), 2), QBrush(QColor(255, 200, 200)))
            
        # Low limit points
        for t, l in zip(self.time_points, self.low_limits):
            point = self.data_to_scene(t, l)
            self.scene.addEllipse(point.x() - 4, point.y() - 4, 8, 8, 
                                 QPen(QColor(0, 0, 200), 2), QBrush(QColor(200, 200, 255)))
            
    def draw_labels(self):
        """Draw axis labels"""
        # Title - different for real vs sample data
        parent_dialog = self.parent()
        if hasattr(parent_dialog, 'has_real_data') and parent_dialog.has_real_data:
            title_text = "Limit Designer - Your Waveform Data"
        else:
            title_text = "Limit Designer - Sample Data"
            
        title = self.scene.addText(title_text, QFont("Arial", 12, QFont.Bold))
        title_rect = title.boundingRect()
        title.setPos((700 - title_rect.width()) / 2, 5)
        
    def mousePressEvent(self, event):
        """Handle mouse press events for setting limit points"""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            # Check if click is within plot area
            if self.plot_rect.contains(scene_pos):
                time_val, amp_val = self.scene_to_data(scene_pos)
                self.point_clicked.emit(time_val, amp_val)
        
        super().mousePressEvent(event)


class WaveformPlotWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Data storage
        self.time_data = None
        self.waveform_data = None
        self.limit_arrays = None
        self.crossing_points = []
        
        # Plot settings
        self.margin = 60  # Increased margin for better label spacing
        self.plot_rect = QRectF()
        
        # Setup view
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
    def set_data(self, time_data, waveform_data, limit_arrays=None, crossing_points=None):
        """Set the data to be plotted"""
        self.time_data = time_data
        self.waveform_data = waveform_data
        self.limit_arrays = limit_arrays
        self.crossing_points = crossing_points or []
        self.update_plot()
        
    def update_plot(self):
        """Update the plot with current data"""
        self.scene.clear()
        
        if self.time_data is None or self.waveform_data is None:
            self.draw_empty_plot()
            return
            
        # Calculate plot boundaries
        self.calculate_plot_rect()
        
        # Draw plot elements
        self.draw_grid()
        self.draw_axes()
        self.draw_waveform()
        self.draw_limit_arrays()
        self.draw_violations()
        self.draw_crossing_points()
        self.draw_labels()
        
        # Fit view to content
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
    def calculate_plot_rect(self):
        """Calculate the plotting rectangle based on data bounds"""
        if len(self.time_data) == 0 or len(self.waveform_data) == 0:
            return
            
        time_min, time_max = min(self.time_data), max(self.time_data)
        amp_min, amp_max = min(self.waveform_data), max(self.waveform_data)
        
        # Extend amplitude range to include limit values if they exist
        if self.limit_arrays:
            if self.limit_arrays['high_limits']:
                amp_max = max(amp_max, max(self.limit_arrays['high_limits']))
            if self.limit_arrays['low_limits']:
                amp_min = min(amp_min, min(self.limit_arrays['low_limits']))
        
        # Add padding
        time_range = time_max - time_min if time_max != time_min else 1
        amp_range = amp_max - amp_min if amp_max != amp_min else 1
        
        time_padding = time_range * 0.05
        amp_padding = amp_range * 0.1
        
        self.time_min = time_min - time_padding
        self.time_max = time_max + time_padding
        self.amp_min = amp_min - amp_padding
        self.amp_max = amp_max + amp_padding
        
        # Define plot rectangle (in scene coordinates)
        self.plot_rect = QRectF(
            self.margin, 
            self.margin, 
            600 - 2 * self.margin, 
            400 - 2 * self.margin
        )
        
    def data_to_scene(self, time_val, amp_val):
        """Convert data coordinates to scene coordinates"""
        if self.time_max == self.time_min or self.amp_max == self.amp_min:
            return QPointF(self.plot_rect.left(), self.plot_rect.bottom())
            
        x = self.plot_rect.left() + (time_val - self.time_min) / (self.time_max - self.time_min) * self.plot_rect.width()
        y = self.plot_rect.bottom() - (amp_val - self.amp_min) / (self.amp_max - self.amp_min) * self.plot_rect.height()
        return QPointF(x, y)
        
    def interpolate_limit(self, time_val, time_points, limit_values):
        """Interpolate limit value at given time"""
        if not time_points or not limit_values:
            return None
            
        # Handle edge cases
        if time_val <= time_points[0]:
            return limit_values[0]
        if time_val >= time_points[-1]:
            return limit_values[-1]
            
        # Find interpolation points
        for i in range(len(time_points) - 1):
            if time_points[i] <= time_val <= time_points[i + 1]:
                # Linear interpolation
                t1, t2 = time_points[i], time_points[i + 1]
                v1, v2 = limit_values[i], limit_values[i + 1]
                ratio = (time_val - t1) / (t2 - t1) if t2 != t1 else 0
                return v1 + ratio * (v2 - v1)
                
        return limit_values[0]  # Fallback
        
    def draw_empty_plot(self):
        """Draw empty plot with message"""
        text = self.scene.addText("Load CSV file and select columns to display waveform", QFont("Arial", 12))
        text.setPos(150, 150)
        
    def draw_grid(self):
        """Draw grid lines"""
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        
        # Vertical grid lines
        for i in range(6):
            x = self.plot_rect.left() + i * self.plot_rect.width() / 5
            line = self.scene.addLine(x, self.plot_rect.top(), x, self.plot_rect.bottom(), pen)
            
        # Horizontal grid lines
        for i in range(6):
            y = self.plot_rect.top() + i * self.plot_rect.height() / 5
            line = self.scene.addLine(self.plot_rect.left(), y, self.plot_rect.right(), y, pen)
            
    def draw_axes(self):
        """Draw axes"""
        pen = QPen(QColor(0, 0, 0), 2)
        
        # X-axis
        self.scene.addLine(
            self.plot_rect.left(), 
            self.plot_rect.bottom(), 
            self.plot_rect.right(), 
            self.plot_rect.bottom(), 
            pen
        )
        
        # Y-axis
        self.scene.addLine(
            self.plot_rect.left(), 
            self.plot_rect.top(), 
            self.plot_rect.left(), 
            self.plot_rect.bottom(), 
            pen
        )
        
    def draw_waveform(self):
        """Draw the main waveform"""
        if len(self.time_data) < 2:
            return
            
        pen = QPen(QColor(0, 100, 200), 2)
        
        # Draw line segments instead of polygon to avoid connecting last to first
        for i in range(len(self.time_data) - 1):
            p1 = self.data_to_scene(self.time_data[i], self.waveform_data[i])
            p2 = self.data_to_scene(self.time_data[i + 1], self.waveform_data[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            
    def draw_limit_arrays(self):
        """Draw limit arrays if they exist"""
        if not self.limit_arrays:
            return
            
        time_points = self.limit_arrays['time_points']
        high_limits = self.limit_arrays['high_limits']
        low_limits = self.limit_arrays['low_limits']
        
        if len(time_points) < 2:
            return
            
        # Draw high limit line as connected line segments
        high_pen = QPen(QColor(200, 0, 0), 2, Qt.DashLine)
        for i in range(len(time_points) - 1):
            p1 = self.data_to_scene(time_points[i], high_limits[i])
            p2 = self.data_to_scene(time_points[i + 1], high_limits[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), high_pen)
            
        # Draw low limit line as connected line segments
        low_pen = QPen(QColor(200, 0, 0), 2, Qt.DashLine)
        for i in range(len(time_points) - 1):
            p1 = self.data_to_scene(time_points[i], low_limits[i])
            p2 = self.data_to_scene(time_points[i + 1], low_limits[i + 1])
            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), low_pen)
            
        # Draw limit points
        for t, h in zip(time_points, high_limits):
            point = self.data_to_scene(t, h)
            self.scene.addEllipse(point.x() - 3, point.y() - 3, 6, 6, 
                                 QPen(QColor(200, 0, 0), 1), QBrush(QColor(255, 200, 200)))
            
        for t, l in zip(time_points, low_limits):
            point = self.data_to_scene(t, l)
            self.scene.addEllipse(point.x() - 3, point.y() - 3, 6, 6, 
                                 QPen(QColor(200, 0, 0), 1), QBrush(QColor(255, 200, 200)))
            
    def draw_violations(self):
        """Draw violation points"""
        if not self.limit_arrays:
            return
            
        pen = QPen(QColor(255, 0, 0), 1)
        brush = QBrush(QColor(255, 0, 0, 100))
        
        time_points = self.limit_arrays['time_points']
        high_limits = self.limit_arrays['high_limits']
        low_limits = self.limit_arrays['low_limits']
        
        for time_val, amp_val in zip(self.time_data, self.waveform_data):
            high_limit = self.interpolate_limit(time_val, time_points, high_limits)
            low_limit = self.interpolate_limit(time_val, time_points, low_limits)
            
            if high_limit is not None and low_limit is not None:
                if amp_val > high_limit or amp_val < low_limit:
                    point = self.data_to_scene(time_val, amp_val)
                    circle = self.scene.addEllipse(
                        point.x() - 2, point.y() - 2, 4, 4, 
                        pen, brush
                    )
                
    def draw_crossing_points(self):
        """Draw crossing points"""
        if not self.crossing_points:
            return
            
        pen = QPen(QColor(0, 150, 0), 2)
        brush = QBrush(QColor(0, 255, 0, 150))
        
        for cp in self.crossing_points:
            point = self.data_to_scene(cp['time'], cp['value'])
            circle = self.scene.addEllipse(
                point.x() - 5, point.y() - 5, 10, 10, 
                pen, brush
            )
            
    def draw_labels(self):
        """Draw axis labels and title"""
        # Title
        title = self.scene.addText("Waveform Limit Analysis", QFont("Arial", 14, QFont.Bold))
        title_rect = title.boundingRect()
        title.setPos(
            (600 - title_rect.width()) / 2, 
            10
        )
        
        # X-axis label
        x_label = self.scene.addText("Time", QFont("Arial", 12))
        x_label_rect = x_label.boundingRect()
        x_label.setPos(
            (600 - x_label_rect.width()) / 2, 
            self.plot_rect.bottom() + 30
        )
        
        # Y-axis label (rotated) - positioned further left to avoid overlap
        y_label = self.scene.addText("Amplitude", QFont("Arial", 12))
        y_label.setRotation(-90)
        y_label_rect = y_label.boundingRect()
        y_label.setPos(
            -10, 
            (self.plot_rect.height() + y_label_rect.width()) / 2 + self.plot_rect.top()
        )
        
        # Draw tick labels
        self.draw_tick_labels()
        
    def draw_tick_labels(self):
        """Draw tick labels on axes"""
        if self.time_data is None or self.waveform_data is None:
            return
            
        font = QFont("Arial", 9)
        
        # X-axis ticks
        for i in range(6):
            x_pos = self.plot_rect.left() + i * self.plot_rect.width() / 5
            time_val = self.time_min + i * (self.time_max - self.time_min) / 5
            text = self.scene.addText(f"{time_val:.2f}", font)
            text_rect = text.boundingRect()
            text.setPos(x_pos - text_rect.width() / 2, self.plot_rect.bottom() + 5)
            
        # Y-axis ticks - positioned with more spacing from y-axis
        for i in range(6):
            y_pos = self.plot_rect.bottom() - i * self.plot_rect.height() / 5
            amp_val = self.amp_min + i * (self.amp_max - self.amp_min) / 5
            text = self.scene.addText(f"{amp_val:.2f}", font)
            text_rect = text.boundingRect()
            text.setPos(self.plot_rect.left() - text_rect.width() - 15, y_pos - text_rect.height() / 2)
            
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)


class WaveformLimitTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform Limit Analysis")
        self.setGeometry(100, 100, 1400, 800)
        
        # Data storage
        self.csv_data = []
        self.csv_headers = []
        self.waveform_data = None
        self.time_data = None
        self.limit_arrays = None
        self.crossing_points = []
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel for controls
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # Right panel for plot
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)
        
        # Set initial splitter sizes (25% controls, 75% plot)
        splitter.setSizes([300, 900])
        
    def create_control_panel(self):
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # File loading section
        file_group = QGroupBox("File Loading")
        file_layout = QVBoxLayout(file_group)
        
        self.load_button = QPushButton("Load CSV File")
        self.load_button.clicked.connect(self.load_csv_file)
        file_layout.addWidget(self.load_button)
        
        self.load_sample_button = QPushButton("Load Sample Data")
        self.load_sample_button.clicked.connect(self.load_sample_data)
        file_layout.addWidget(self.load_sample_button)
        
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)
        
        control_layout.addWidget(file_group)
        
        # Column selection section
        column_group = QGroupBox("Column Selection")
        column_layout = QGridLayout(column_group)
        
        column_layout.addWidget(QLabel("Time Column:"), 0, 0)
        self.time_column_combo = QComboBox()
        self.time_column_combo.currentTextChanged.connect(self.update_plot_data)
        column_layout.addWidget(self.time_column_combo, 0, 1)
        
        self.auto_time_checkbox = QCheckBox("Auto-generate time")
        self.auto_time_checkbox.toggled.connect(self.on_auto_time_changed)
        column_layout.addWidget(self.auto_time_checkbox, 0, 2)
        
        column_layout.addWidget(QLabel("Amplitude Column:"), 1, 0)
        self.amplitude_column_combo = QComboBox()
        self.amplitude_column_combo.currentTextChanged.connect(self.update_plot_data)
        column_layout.addWidget(self.amplitude_column_combo, 1, 1)
        
        control_layout.addWidget(column_group)
        
        # Limit setting section
        limit_group = QGroupBox("Limit Settings")
        limit_layout = QVBoxLayout(limit_group)
        
        self.design_limits_button = QPushButton("Design Limit Arrays")
        self.design_limits_button.clicked.connect(self.open_limit_designer)
        limit_layout.addWidget(self.design_limits_button)
        
        self.limits_status_label = QLabel("No limits defined")
        self.limits_status_label.setWordWrap(True)
        limit_layout.addWidget(self.limits_status_label)
        
        self.apply_limits_button = QPushButton("Apply Limits & Test")
        self.apply_limits_button.clicked.connect(self.apply_limits)
        limit_layout.addWidget(self.apply_limits_button)
        
        self.clear_limits_button = QPushButton("Clear Limits")
        self.clear_limits_button.clicked.connect(self.clear_limits)
        limit_layout.addWidget(self.clear_limits_button)
        
        control_layout.addWidget(limit_group)
        
        # Results section
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(250)
        self.results_text.setFont(QFont("Courier", 9))
        results_layout.addWidget(self.results_text)
        
        control_layout.addWidget(results_group)
        
        # Add stretch to push everything to top
        control_layout.addStretch()
        
        return control_widget
        
    def create_plot_panel(self):
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        
        # Create custom plot widget
        self.plot_widget = WaveformPlotWidget()
        plot_layout.addWidget(self.plot_widget)
        
        # Add zoom controls
        controls_layout = QHBoxLayout()
        
        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.clicked.connect(lambda: self.plot_widget.scale(1.2, 1.2))
        controls_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.clicked.connect(lambda: self.plot_widget.scale(0.8, 0.8))
        controls_layout.addWidget(zoom_out_btn)
        
        fit_btn = QPushButton("Fit to View")
        fit_btn.clicked.connect(lambda: self.plot_widget.fitInView(
            self.plot_widget.scene.itemsBoundingRect(), Qt.KeepAspectRatio))
        controls_layout.addWidget(fit_btn)
        
        controls_layout.addStretch()
        plot_layout.addLayout(controls_layout)
        
        return plot_widget
        
    def load_sample_data(self):
        """Load built-in sample data"""
        try:
            # Generate sample data
            self.csv_data = []
            self.csv_headers = ["Time", "Voltage", "Current"]
            
            for i in range(100):
                time = i * 0.1
                voltage = 3.3 + math.sin(time * 2) * 1.2 + math.sin(time * 5) * 0.3 + random.uniform(-0.1, 0.1)
                current = 1.5 + math.cos(time * 1.5) * 0.8 + random.uniform(-0.05, 0.05)
                self.csv_data.append([f"{time:.2f}", f"{voltage:.3f}", f"{current:.3f}"])
            
            # Update column selection
            self.update_column_combos()
            
            self.file_label.setText(f"Sample Data Loaded\n"
                                  f"Rows: {len(self.csv_data)}\n"
                                  f"Columns: {self.csv_headers}")
            
            self.results_text.setText("Sample data loaded successfully. Select columns and design limits for testing.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate sample data:\n{str(e)}")
        
    def load_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Load CSV data
                self.csv_data = []
                self.csv_headers = []
                
                with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                    # Try to detect delimiter
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.reader(csvfile, delimiter=delimiter)
                    
                    # Read headers
                    self.csv_headers = next(reader)
                    
                    # Read data
                    for row in reader:
                        if row:  # Skip empty rows
                            self.csv_data.append(row)
                
                # Update column selection dropdowns
                self.update_column_combos()
                
                self.file_label.setText(f"Loaded: {file_path.split('/')[-1]}\n"
                                      f"Rows: {len(self.csv_data)}\n"
                                      f"Columns: {self.csv_headers}")
                
                self.results_text.setText("File loaded successfully. Select columns and design limits for testing.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file:\n{str(e)}")
                
    def update_column_combos(self):
        """Update the column selection combo boxes"""
        self.time_column_combo.clear()
        self.amplitude_column_combo.clear()
        
        if self.csv_headers:
            self.time_column_combo.addItems(self.csv_headers)
            self.amplitude_column_combo.addItems(self.csv_headers)
            
            # Set default selections
            if len(self.csv_headers) >= 2:
                self.time_column_combo.setCurrentIndex(0)
                self.amplitude_column_combo.setCurrentIndex(1)
            elif len(self.csv_headers) == 1:
                self.amplitude_column_combo.setCurrentIndex(0)
                self.auto_time_checkbox.setChecked(True)
                
    def on_auto_time_changed(self):
        """Handle auto-generate time checkbox change"""
        self.time_column_combo.setEnabled(not self.auto_time_checkbox.isChecked())
        self.update_plot_data()
        
    def update_plot_data(self):
        """Update plot data based on selected columns"""
        if not self.csv_data or not self.csv_headers:
            return
            
        try:
            # Get amplitude data
            amp_column = self.amplitude_column_combo.currentText()
            if not amp_column:
                return
                
            amp_index = self.csv_headers.index(amp_column)
            self.waveform_data = []
            
            for row in self.csv_data:
                try:
                    value = float(row[amp_index])
                    self.waveform_data.append(value)
                except (ValueError, IndexError):
                    # Skip invalid data points
                    continue
                    
            # Get time data
            if self.auto_time_checkbox.isChecked():
                # Auto-generate time data
                self.time_data = list(range(len(self.waveform_data)))
            else:
                time_column = self.time_column_combo.currentText()
                if not time_column:
                    return
                    
                time_index = self.csv_headers.index(time_column)
                self.time_data = []
                
                for i, row in enumerate(self.csv_data):
                    if i < len(self.waveform_data):  # Match length with amplitude data
                        try:
                            value = float(row[time_index])
                            self.time_data.append(value)
                        except (ValueError, IndexError):
                            # Use index if conversion fails
                            self.time_data.append(i)
                            
            # Ensure both lists have same length
            min_length = min(len(self.time_data), len(self.waveform_data))
            self.time_data = self.time_data[:min_length]
            self.waveform_data = self.waveform_data[:min_length]
            
            # Update plot
            self.plot_widget.set_data(self.time_data, self.waveform_data, self.limit_arrays)
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error processing column data: {str(e)}")
            
    def open_limit_designer(self):
        """Open the limit designer dialog"""
        # Check if data is loaded
        if self.time_data is None or self.waveform_data is None:
            reply = QMessageBox.question(self, "No Data Loaded", 
                                       "No waveform data is currently loaded. Would you like to:\n\n"
                                       "• Load sample data first, or\n"
                                       "• Design limits with sample data?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.load_sample_data()
            else:
                return
        
        # Pass the actual waveform data and existing limits to the designer
        dialog = LimitDesignerDialog(self, self.time_data, self.waveform_data, self.limit_arrays)
        if dialog.exec() == QDialog.Accepted:
            self.limit_arrays = dialog.get_limit_arrays()
            
            # Update status
            num_points = len(self.limit_arrays['time_points'])
            self.limits_status_label.setText(f"Limit arrays defined with {num_points} points\n"
                                            f"Time range: {min(self.limit_arrays['time_points']):.2f} to {max(self.limit_arrays['time_points']):.2f}")
            
            # Update plot
            if self.time_data and self.waveform_data:
                self.plot_widget.set_data(self.time_data, self.waveform_data, self.limit_arrays)
                
    def clear_limits(self):
        """Clear all limit arrays"""
        self.limit_arrays = None
        self.crossing_points = []
        self.limits_status_label.setText("No limits defined")
        
        if self.time_data and self.waveform_data:
            self.plot_widget.set_data(self.time_data, self.waveform_data)
            
        self.results_text.clear()
                
    def apply_limits(self):
        if self.waveform_data is None or len(self.waveform_data) == 0:
            QMessageBox.warning(self, "Warning", "Please load data and select columns first")
            return
            
        if not self.limit_arrays:
            QMessageBox.warning(self, "Warning", "Please design limit arrays first")
            return
                
        # Perform limit testing
        self.perform_limit_test()
        
        # Update plot
        self.plot_widget.set_data(
            self.time_data, 
            self.waveform_data, 
            self.limit_arrays,
            self.crossing_points
        )
            
    def perform_limit_test(self):
        """Detect crossing points where waveform exceeds interpolated limits"""
        self.crossing_points = []
        
        if len(self.waveform_data) < 2 or not self.limit_arrays:
            return
        
        time_points = self.limit_arrays['time_points']
        high_limits = self.limit_arrays['high_limits']
        low_limits = self.limit_arrays['low_limits']
        
        # Check each data point against interpolated limits
        violations = []
        for i, (time_val, amp_val) in enumerate(zip(self.time_data, self.waveform_data)):
            high_limit = self.plot_widget.interpolate_limit(time_val, time_points, high_limits)
            low_limit = self.plot_widget.interpolate_limit(time_val, time_points, low_limits)
            
            if high_limit is not None and low_limit is not None:
                high_violation = amp_val > high_limit
                low_violation = amp_val < low_limit
                violations.append((high_violation, low_violation))
            else:
                violations.append((False, False))
        
        # Detect crossing points (transitions)
        for i in range(1, len(violations)):
            prev_high, prev_low = violations[i-1]
            curr_high, curr_low = violations[i]
            
            # High limit crossings
            if prev_high != curr_high:
                self.crossing_points.append({
                    'index': i,
                    'time': self.time_data[i],
                    'value': self.waveform_data[i],
                    'type': 'high',
                    'direction': 'up' if curr_high else 'down'
                })
                
            # Low limit crossings
            if prev_low != curr_low:
                self.crossing_points.append({
                    'index': i,
                    'time': self.time_data[i],
                    'value': self.waveform_data[i],
                    'type': 'low',
                    'direction': 'down' if curr_low else 'up'
                })
        
        # Sort by time
        self.crossing_points.sort(key=lambda x: x['time'])
        
        # Generate results summary
        self.update_results_display(violations)
        
    def update_results_display(self, violations):
        """Update the results text area with crossing point information"""
        results = []
        results.append("=== LIMIT ARRAY TEST RESULTS ===\n")
        results.append(f"Limit Points: {len(self.limit_arrays['time_points'])}")
        results.append(f"Total Data Points: {len(self.waveform_data)}")
        results.append(f"Crossing Points Found: {len(self.crossing_points)}\n")
        
        if self.crossing_points:
            results.append("CROSSING POINTS:")
            results.append("-" * 50)
            results.append(f"{'Index':<8} {'Time':<12} {'Value':<12} {'Limit':<6} {'Dir':<6}")
            results.append("-" * 50)
            
            for cp in self.crossing_points:
                results.append(f"{cp['index']:<8} {cp['time']:<12.4f} {cp['value']:<12.4f} "
                             f"{cp['type']:<6} {cp['direction']:<6}")
        else:
            results.append("No limit violations detected!")
            
        # Count violations
        high_violations = sum(1 for h, l in violations if h)
        low_violations = sum(1 for h, l in violations if l)
        
        results.append(f"\nVIOLATION SUMMARY:")
        results.append(f"Points above high limits: {high_violations}")
        results.append(f"Points below low limits: {low_violations}")
        results.append(f"Total violations: {high_violations + low_violations}")
        results.append(f"Violation rate: {((high_violations + low_violations) / len(self.waveform_data) * 100):.2f}%")
        
        self.results_text.setText("\n".join(results))


def main():
    app = QApplication(sys.argv)
    window = WaveformLimitTester()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()