from PyQt5 import QtCore, QtGui, QtWidgets, uic
from tkinter import filedialog
import sys, cv2, datetime
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import *
import numpy as np
from lib import add_missing_data, visualize
from ultralytics import YOLO
from lib.sort.sort import *
from lib.util import get_car, read_license_plate, write_csv

class VideoProcessor(QtCore.QThread):
    finished = QtCore.pyqtSignal()

    def __init__(self, input_path, output_path):
        super(VideoProcessor, self).__init__()
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        window.lb_process.setText("İşlem: Araç Tespiti")
        startDetection(self.input_path, "test", )
        
        window.lb_process.setText("İşlem: Verilerin İşlenişi")
        add_missing_data.func("test", "test_interpolated")
        
        window.lb_process.setText("İşlem: Sonuç Videosunun Oluşturumu")
        visualize.func(self.input_path, "test_interpolated", self.output_path)
        
        window.lb_process.setText("İşlem: Tamamlandı!")
        self.finished.emit()
        
class ShowResult(QtCore.QThread):
    finished = QtCore.pyqtSignal()

    def __init__(self):
        super(ShowResult, self).__init__()

    def run(self):
        while(True):
            cap = cv2.VideoCapture("./output/output.mp4")
            ret = True
            while ret:
                ret, frame = cap.read()
                if ret:
                    setFrame(frame)
                    
                while not self.window.isVideoPlaying:
                    pass
            if(self.window.isRepeat==False):
                break
            #cap.release()
        self.finished.emit()
        #if(self.window.isRepeat):
         #   self.videoProcessor = ShowResult()
          #  self.videoProcessor.window = self
           # self.videoProcessor.start()

class Ui(QtWidgets.QMainWindow):
    isVideoPlaying = True
    isRepeat = False
    
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('form.ui', self)
        
        self.find_button.setIcon(QIcon('Icons/m_glass.png'))
        self.find_button.setIconSize(QtCore.QSize(35,35))
        self.save_button.setIcon(QIcon('Icons/m_glass.png'))
        self.save_button.setIconSize(QtCore.QSize(35,35))
        self.pause_button.setIcon(QIcon('Icons/pause.png'))
        self.pause_button.setIconSize(QtCore.QSize(40,40))
        self.repeat_button.setIcon(QIcon('Icons/no-repeat.png'))
        self.pause_button.setIconSize(QtCore.QSize(60,60))
        self.frame_counter.setVisible(False)
        
        self.find_button.clicked.connect(self.findFile)
        self.save_button.clicked.connect(self.saveFile)
        self.start_button.clicked.connect(self.startRecognition)
        self.pause_button.clicked.connect(self.pause)
        self.result_button.clicked.connect(self.showResult)
        self.repeat_button.clicked.connect(self.repeat)
        self.frame_counter.textChanged.connect(self.updateProgressBar)
        self.searchbar.textChanged.connect(self.search)
        self.table_car.cellDoubleClicked.connect(self.getFrame)

        self.show()

    def findFile(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.lbl_path.setText(filename)
            
    def saveFile(self):
        filename = filedialog.askdirectory()
        if filename:
            self.lbl_path_2.setText(filename)

    def startRecognition(self):
        self.videoProcessor = VideoProcessor(self.lbl_path.text(), self.lbl_path_2.text())
        self.videoProcessor.window = self
        self.videoProcessor.start()
        
    
    def pause(self):
        if(self.isVideoPlaying):
            self.pause_button.setIcon(QIcon('Icons/play.png'))
            self.isVideoPlaying = False
        else:
            self.pause_button.setIcon(QIcon('Icons/pause.png'))
            self.isVideoPlaying = True
            
    def repeat(self):
        if(self.isRepeat):
            self.repeat_button.setIcon(QIcon('Icons/no-repeat.png'))
            self.isRepeat = False
        else:
            self.repeat_button.setIcon(QIcon('Icons/repeat.png'))
            self.isRepeat = True
            
    def showResult(self):
        self.videoProcessor = ShowResult()
        self.videoProcessor.window = self
        self.videoProcessor.start()
            
    def updateProgressBar(self):
        window.pb_detection.setValue(int(window.frame_counter.text()))
        
    def getFrame(self, row, column):
        frame_nmr = int(window.table_car.item(row, 2).text())
        cap = cv2.VideoCapture("./output/output.mp4")
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_nmr)
        ret, frame = cap.read()
        setFrame(frame)
        
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_seconds = round(total_frames / fps)
        video_time = datetime.timedelta(seconds=total_seconds)
        window.lb_time.setText(str(datetime.timedelta(seconds=round(frame_nmr/fps))) + "/" + str(video_time))
        
        cap.release()
        
    def search(self):
        name = self.searchbar.text().lower()
        for row in range(self.table_car.rowCount()):
            item = self.table_car.item(row, 3)
            self.table_car.setRowHidden(row, name not in item.text().lower())
        
            
def startDetection(video_path, output_name):
    results = {}
    
    mot_tracker = Sort()
    
    # load models
    model = YOLO("../model/yolo11n.pt")
    license_plate_detector = YOLO('../model/best_20.pt')
    
    # load video
    cap = cv2.VideoCapture(video_path)
    
    #For tracking the progress
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_seconds = round(total_frames / fps)
    video_time = datetime.timedelta(seconds=total_seconds)
    
    window.pb_detection.setMaximum(int(total_frames))
    
    vehicles = [2, 3, 5, 7]
    
    # read frames
    frame_nmr = -1
    ret = True
    while ret:
        frame_nmr += 1
        current_time = datetime.timedelta(seconds=round(frame_nmr/fps))
        ret, frame = cap.read()
        if ret:
            setFrame(frame)
            
            window.lb_frame.setText(str(frame_nmr + 1) + "/" + str(int(total_frames)))
            window.frame_counter.setText(str(frame_nmr+1))
            window.lb_time.setText(str(current_time) + "/" + str(video_time))
            
            
            results[frame_nmr] = {}
            # detect vehicles
            detections = model(frame)[0]
            detections_ = []
            for detection in detections.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = detection
                if int(class_id) in vehicles:
                    detections_.append([x1, y1, x2, y2, score])
    
            # track vehicles
            track_ids = mot_tracker.update(np.asarray(detections_))
    
            # detect license plates
            license_plates = license_plate_detector(frame)[0]
            for license_plate in license_plates.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = license_plate
    
                # assign license plate to car
                xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)
                car_id = int(car_id)
    
                if car_id != -1:
    
                    # crop license plate
                    license_plate_crop = frame[int(y1):int(y2), int(x1): int(x2), :]
    
                    # process license plate
                    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                    _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)
    
                    # read license plate number
                    license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)
    
                    if license_plate_text is not None:
                        results[frame_nmr][car_id] = {'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                                                      'license_plate': {'bbox': [x1, y1, x2, y2],
                                                                        'text': license_plate_text,
                                                                        'bbox_score': score,
                                                                        'text_score': license_plate_text_score}}
                        isUnique = True
                        row_count = window.table_car.rowCount()
                        for i in range(row_count):
                            table_item = window.table_car.item(i,0)
                            if(table_item.text() == str(car_id)):
                                isUnique = False
                                break
                        if(isUnique):
                            window.table_car.setRowCount(row_count+1)
                            window.table_car.setItem(row_count,0,QTableWidgetItem(str(car_id)))
                            window.table_car.setItem(row_count,1,QTableWidgetItem(str(current_time)))
                            window.table_car.setItem(row_count,2,QTableWidgetItem(str(frame_nmr)))
                            window.table_car.setItem(row_count,3,QTableWidgetItem(license_plate_text))
    
    # write results
    write_csv(results, './output/'+ output_name +'.csv')
    cap.release() 
    
def setFrame(frame):
    height, width, channel = frame.shape
    bytesPerLine = 3 * width
    qImg = QtGui.QImage(frame.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888).rgbSwapped()
    pixmap = QtGui.QPixmap.fromImage(qImg)
    window.frame.setPixmap(pixmap)
    

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()