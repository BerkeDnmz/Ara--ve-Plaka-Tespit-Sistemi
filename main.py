from PyQt5 import QtCore, QtGui, QtWidgets, uic
from tkinter import filedialog
import sys, os, cv2, datetime, torch, csv
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import *

#from PyQt5 import QtCore, QtGui, QtWidgets

import numpy as np
from lib import add_missing_data, visualize, database, get_color
from ultralytics import YOLO
from lib.sort.sort import *
from lib.util import get_car, read_license_plate, write_csv
from lib.model import resolve_single
from lib.model import edsr, espcn_func

#This thread class does the object tracking
class VideoProcessor(QtCore.QThread):
    finished = QtCore.pyqtSignal()

    def __init__(self, input_path, output_path, input_sql, new_name):
        super(VideoProcessor, self).__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.input_sql = input_sql
        self.new_name = new_name

    def run(self):
        window.lb_process.setText(window.lang["process_detection"])
        startDetection(self.input_path, "test", self.input_sql)
        
        window.lb_process.setText(window.lang["process_data"])
        add_missing_data.func("test", "test_interpolated")
        
        window.lb_process.setText(window.lang["process_video"])
        visualize.func(self.input_path, "test_interpolated", self.output_path, self.new_name)
        
        window.lb_process.setText(window.lang["process_completed"])
        self.finished.emit()

#Shows the end result video
class ShowVideo(QtCore.QThread):
    finished = QtCore.pyqtSignal()

    def __init__(self, video_origin):
        super(ShowVideo, self).__init__()
        self.video_origin = video_origin

    def run(self):
        while(True):
            cap = cv2.VideoCapture(self.window.lbl_path.text())
            if(self.video_origin == "output"):
                cap = cv2.VideoCapture(self.window.lbl_path_2.text() + "/output.mp4")
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_seconds = round(total_frames / fps)
            video_time = datetime.timedelta(seconds=total_seconds)
            frame_nmr = 0
            ret = True
            while ret and self.window.video_settings["willStop"]==False:
                
                if(self.window.video_settings["goBackward"]==True):
                    frame_nmr = max(frame_nmr - fps*10, 0)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_nmr)
                    self.window.video_settings["goBackward"] = False
                
                if(self.window.video_settings["goForward"]==True):
                    frame_nmr = min(frame_nmr + fps*10, total_frames)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_nmr)
                    self.window.video_settings["goForward"] = False
                
                ret, frame = cap.read()
                if ret:
                    frame_nmr += 1
                    window.lb_time.setText(str(datetime.timedelta(seconds=round(frame_nmr/fps))) + "/" + str(video_time))
                    setFrame(frame)
                    
                while not self.window.video_settings["isVideoPlaying"]:
                    pass
                
            if(self.window.video_settings["isRepeat"]==False):
                break
            cap.release()
        self.finished.emit()

#Ui widgets are setup and connected to functions here
class Ui(QtWidgets.QMainWindow):
    video_settings = {}
    video_settings["isVideoPlaying"] = True
    video_settings["isRepeat"] = False
    video_settings["goForward"] = False
    video_settings["goBackward"] = False
    video_settings["willStop"] = False
    video_origin = "output"
    lang_id = 2 #1=Turkish 2=English
    lang={}
    
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
        
        self.lang_turkish.clicked.connect(lambda: self.changeLang(1))
        self.lang_english.clicked.connect(lambda: self.changeLang(2))
        
        self.find_button.clicked.connect(self.findFile)
        self.save_button.clicked.connect(self.saveFile)
        self.gpu_button.clicked.connect(self.gpuHelp)
        self.hs_threshold.valueChanged.connect(lambda: self.thresholdValueChanged(1))
        self.hs_threshold_2.valueChanged.connect(lambda: self.thresholdValueChanged(2))
        self.start_button.clicked.connect(self.sqlCheck)
        self.pause_button.clicked.connect(self.pause)
        self.input_button.clicked.connect(self.showInput)
        self.result_button.clicked.connect(self.showResult)
        self.repeat_button.clicked.connect(self.repeat)
        self.forward_button.clicked.connect(lambda: self.videoSetting("goForward"))
        self.backward_button.clicked.connect(lambda: self.videoSetting("goBackward"))
        self.stop_button.clicked.connect(lambda: self.videoSetting("willStop"))
        self.frame_counter.textChanged.connect(self.updateProgressBar)
        self.searchbar.textChanged.connect(self.search)
        self.table_car.cellDoubleClicked.connect(self.getFrame)
        
        if torch.cuda.is_available():
            self.lb_gpu_result.setText(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.lb_gpu_result.setText(self.lang["gpu"])
        
        self.changeLang(self.lang_id)

        self.show()
        
    def readLangFile(self):
        with open('lib/lang.csv', mode='r')as file:
            csvFile = csv.reader(file)
            for lines in csvFile:
                self.lang[lines[0]] = lines[self.lang_id]
                
    def changeLang(self, new_id):
        self.lang_id = new_id
        self.readLangFile()
        
        self.lbl_path.setText(self.lang["video_select"])
        self.lbl_path_2.setText(self.lang["video_save_path"])
        self.backward_button.setText(self.lang["video_backward"])
        self.forward_button.setText(self.lang["video_forward"])
        self.stop_button.setText(self.lang["video_stop"])
        self.input_button.setText(self.lang["show_input"])
        self.result_button.setText(self.lang["show_output"])
        self.start_button.setText(self.lang["video_start"])
        self.lb_gpu_text.setText(self.lang["gpu_title"])
        self.gpu_button.setText(self.lang["gpu_button"])
        self.lb_process.setText(self.lang["process"])
        self.lb_frame_2.setText(self.lang["frame_counter"])
        self.lb_frame_3.setText(self.lang["search"])
        self.lb_frame_4.setText(self.lang["video_length"])
        self.lb_frame_5.setText(self.lang["model"])
        self.lb_frame_6.setText(self.lang["plate_threshold"])
        self.lb_frame_7.setText(self.lang["resolution"])
        self.cb_plate.setText(self.lang["plate_read"])
        self.cb_plate_version.setText(self.lang["plate"])
        self.cb_sql.setText(self.lang["sql"])
        self.lb_frame_8.setText(self.lang["plate_distance"])
        self.lb_frame_9.setText(self.lang["resize"])
        self.lb_frame_10.setText(self.lang["skip"])
        self.cb_video.setText(self.lang["video"])

    def findFile(self):
        filename = None
        if(self.cb_video.isChecked()):
            filename = filedialog.askdirectory()
        else:
            filename = filedialog.askopenfilename()
        if filename:
            self.lbl_path.setText(filename)
            
    def saveFile(self):
        filename = filedialog.askdirectory()
        if filename:
            self.lbl_path_2.setText(filename)
            
    def gpuHelp(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.lang["gpu_help1"])
        layout = QVBoxLayout()
        message = QLabel(self.lang["gpu_help2"] + "\n" + self.lang["gpu_help3"] + "\n" + self.lang["gpu_help4"])
        layout.addWidget(message)
        dlg.setLayout(layout)
        dlg.exec()
        
    def thresholdValueChanged(self, slider_id):
        if(slider_id==1):
            self.lb_threshold.setText(str(self.hs_threshold.value()))
        else:
            self.lb_threshold_2.setText(str(self.hs_threshold_2.value()))
            
    def sqlCheck(self):
        input_sql = {}
        if(self.cb_sql.isChecked()):
            dialog = InputDialog()
            if dialog.exec():
                input_host, input_user, input_password, input_database = dialog.getInputs()
                input_sql = {}
                input_sql["host"] = input_host
                input_sql["user"] = input_user
                input_sql["password"] = input_password
                input_sql["database"] = input_database
                
                if(database.checkTable(input_sql) == False):
                    database.createTable(input_sql)
                
                self.videoCheck(lambda: input_sql)
        else:
            self.videoCheck(lambda: input_sql)
                    
    def videoCheck(self, input_sql):
        if(self.cb_video.isChecked()):
            i = 1
            files = os.listdir()
            for f in files:
                if(f.endswith(".mp4")):
                    video_path = os.path.abspath(f)
                    self.startRecognition(lambda: video_path, input_sql, "output" + i)
                    i = i + 1
        else:
            self.startRecognition(lambda: self.lbl_path.text(), input_sql, "output")

    def startRecognition(self, video_path, input_sql, output_name):
        self.videoProcessor = VideoProcessor(self.lbl_path.text(), self.lbl_path_2.text(), input_sql, output_name)
        self.videoProcessor.window = self
        self.videoProcessor.start()
        
    
    def pause(self):
        if(self.video_settings["isVideoPlaying"]):
            self.pause_button.setIcon(QIcon('Icons/play.png'))
            self.video_settings["isVideoPlaying"] = False
        else:
            self.pause_button.setIcon(QIcon('Icons/pause.png'))
            self.video_settings["isVideoPlaying"] = True
            
    def repeat(self):
        if(self.video_settings["isRepeat"]):
            self.repeat_button.setIcon(QIcon('Icons/no-repeat.png'))
            self.video_settings["isRepeat"] = False
        else:
            self.repeat_button.setIcon(QIcon('Icons/repeat.png'))
            self.video_settings["isRepeat"] = True
        
    def videoSetting(self, video_command):
        self.video_settings[video_command] = True
        
    def showInput(self):
        self.video_origin = "input"
        self.showVideo = ShowVideo(self.video_origin)
        self.showVideo.window = self
        self.showVideo.start()
            
    def showResult(self):
        self.video_origin = "output"
        self.showVideo = ShowVideo(self.video_origin)
        self.showVideo.window = self
        self.showVideo.start()
            
    def updateProgressBar(self):
        window.pb_detection.setValue(int(window.frame_counter.text())+1)
        
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
        
class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.input_host = QLineEdit(self)
        self.input_user = QLineEdit(self)
        self.input_password = QLineEdit(self)
        self.input_database = QLineEdit(self)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.input_password.setEchoMode(QtWidgets.QLineEdit.Password)
        
        layout = QFormLayout(self)
        #layout.setWindowTitle("MySQL")
        layout.addRow("Host:", self.input_host)
        layout.addRow("User:", self.input_user)
        layout.addRow("Password:", self.input_password)
        layout.addRow("Database:", self.input_database)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
    def getInputs(self):
        return (self.input_host.text(), self.input_user.text(), self.input_password.text(), self.input_database.text())

#Functions below are run inside threads. They are here to not clutter the thread classes.

def startDetection(video_path, output_name, input_sql):
    results = {}
    
    mot_tracker = Sort()
    
    # load models
    model_name = window.cb_model.currentText()
    model = YOLO("./model/yolo/" + model_name)
    model.to('cuda')
    license_plate_detector = YOLO('../model/license/best_50.pt')
    license_plate_detector.to('cuda')
    
    resolution = window.cb_super.currentText()
    res_model = None
    if(resolution=="EDSR"):
        res_model = edsr.edsr(scale=4, num_res_blocks=16)
        res_model.load_weights('model/weights/weights-edsr-16-x4-fine-tuned.h5')
        
    resize_method = {}
    resize_method["Cubic"] = cv2.INTER_CUBIC
    resize_method["Linear"] = cv2.INTER_LINEAR
    resize_method["Nearest"] = cv2.INTER_NEAREST
    
    window.table_car.setRowCount(0)
    
    # load video
    cap = cv2.VideoCapture(video_path)
    
    #For tracking the progress
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_seconds = round(total_frames / fps)
    video_time = datetime.timedelta(seconds=total_seconds)
    
    window.pb_detection.setMaximum(int(total_frames))
    plate_thres = window.hs_threshold.value()
    thres_dist = window.hs_threshold_2.value()
    
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
            window.frame_counter.setText(str(frame_nmr))
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
                    
                    ratio = window.sb_resize.value()
                    if(ratio>1):
                        # resize the image
                        H, W, C = license_plate_crop.shape
                        license_plate_crop = cv2.resize(license_plate_crop, (ratio*H,ratio*W), interpolation=resize_method[window.cb_method.currentText()])
                    
                    # process license plate
                    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                    
                    if(resolution=="EDSR"):
                        image_rgb = np.array(cv2.cvtColor(license_plate_crop_gray, cv2.COLOR_BGR2RGB))
                        license_plate_crop_gray = resolve_single(res_model, image_rgb)
                        license_plate_crop_gray = np.array(license_plate_crop_gray)
                        
                    elif(resolution=="ESPCN"):
                        cv2.imwrite("lib/temp.png", license_plate_crop_gray)
                        espcn_func.Espcn("lib/temp.png")
                        license_plate_crop_gray = cv2.imread("lib/temp.png")
                        
                    elif(resolution=="Keskinleştirme"):
                        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                        license_plate_crop_gray = cv2.filter2D(license_plate_crop_gray, -1, kernel)
                        
                    elif(resolution=="Histogram Eşitlemesi"):
                        license_plate_crop_gray = cv2.equalizeHist(license_plate_crop_gray)
                        
                    elif(resolution=="Gaussian Filtresi"):
                        license_plate_crop_gray = cv2.GaussianBlur(license_plate_crop_gray, (5,5), 1)
                    
                    
                    best_text = None
                    best_score = 0
                    
                    min_range = max(plate_thres-thres_dist, 0)
                    max_range = min(plate_thres+thres_dist+1, 255)
                    
                    step_skip = window.sb_skip.value()
                    
                    i = min_range
                    while(i<max_range):
                        _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, i, 255, cv2.THRESH_BINARY_INV)
    
                        # read license plate number
                        license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh, window.cb_plate_version.isChecked(), window.line_plate.text().upper())
                        
                        if(best_score <= license_plate_text_score):
                            best_text = license_plate_text
                            best_score = license_plate_text_score
                            
                        i = i + step_skip
                        
                    license_plate_text = best_text
                    license_plate_text_score = best_score
                        
                    if license_plate_text is not None and license_plate_text != "None":
                        results[frame_nmr][car_id] = {'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                                                      'license_plate': {'bbox': [x1, y1, x2, y2],
                                                                        'text': license_plate_text,
                                                                        'bbox_score': score,
                                                                        'text_score': license_plate_text_score}}
                        
                    elif(window.cb_plate.isChecked() == False):
                        #license_plate_text = "????"
                        license_plate_text_score = 0
                        results[frame_nmr][car_id] = {'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                                                      'license_plate': {'bbox': [x1, y1, x2, y2],
                                                                        'text': "????",
                                                                        'bbox_score': score,
                                                                        'text_score': license_plate_text_score}}
                        
                    #Showing results in the table widget
                    if(license_plate_text is not None or window.cb_plate.isChecked() == False):     
                        isUnique = True
                        row_count = window.table_car.rowCount()
                        for i in range(row_count):
                            table_item = window.table_car.item(i,0)
                            if(table_item.text() == str(car_id)):
                                isUnique = False
                                
                                #Replacing results with better ones
                                if(window.cb_plate.isChecked() == False and window.table_car.item(i,3).text() == "????"):
                                    window.table_car.setItem(i,3,QTableWidgetItem(license_plate_text))
                                    window.table_car.setItem(i,4,QTableWidgetItem(str(license_plate_text_score)))
                                elif(float(license_plate_text_score) > float(window.table_car.item(i,4).text())):
                                    window.table_car.setItem(i,3,QTableWidgetItem(license_plate_text))
                                    window.table_car.setItem(i,4,QTableWidgetItem(str(license_plate_text_score)))
                                break
                        if(isUnique):
                            window.table_car.setRowCount(row_count+1)
                            window.table_car.setItem(row_count,0,QTableWidgetItem(str(car_id)))
                            window.table_car.setItem(row_count,1,QTableWidgetItem(str(current_time)))
                            window.table_car.setItem(row_count,2,QTableWidgetItem(str(frame_nmr)))
                            window.table_car.setItem(row_count,3,QTableWidgetItem(license_plate_text))
                            window.table_car.setItem(row_count,4,QTableWidgetItem(str(license_plate_text_score)))
                            
                            if(window.cb_sql.isChecked()):
                                if(database.checkRecord(license_plate_text, input_sql)):
                                    #Cropping a picture of the car
                                    print("Kaydediliyor!")
                                    car_image_crop = frame[int(ycar1):int(ycar2), int(xcar1): int(xcar2), :]
                                    color_name = get_color.func(car_image_crop)
                                    database.addRecord(license_plate_text, car_image_crop, color_name, video_path, input_sql)
    
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