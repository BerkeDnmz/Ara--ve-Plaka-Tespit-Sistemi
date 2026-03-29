from PyQt5 import QtCore, QtGui, QtWidgets, uic
from tkinter import filedialog
import sys, os, cv2, datetime, torch
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import *

from lib import database

#Ui widgets are setup and connected to functions here
class Ui(QtWidgets.QMainWindow):
    lastClickedRow = -1
    
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('form2.ui', self)
        self.table_car.cellDoubleClicked.connect(self.getRow)
        self.edit_button.clicked.connect(self.updateRow)
        self.delete_button.clicked.connect(self.deleteRow)
        self.fillTable()
        
        self.show()
        
    def fillTable(self):
        car_list = database.getRecords()
        self.table_car.setRowCount(len(car_list))
        i = 0
        for car in car_list:
            self.table_car.setItem(i,0,QTableWidgetItem(str(car[0])))
            self.table_car.setItem(i,1,QTableWidgetItem(car[1]))
            self.table_car.setItem(i,2,QTableWidgetItem(car[3]))
            self.table_car.setItem(i,3,QTableWidgetItem(car[4]))
            i = i + 1
            
    def getRow(self, row, column):
        self.lastClickedRow = row
        plate = self.table_car.item(row, 1).text()
        color = self.table_car.item(row, 2).text()
        frame = database.getImage(plate)
        setFrame(frame)
        self.line_plate.setText(plate)
        self.line_color.setText(color)
        
    def updateRow(self):
        if(self.lastClickedRow != -1):
            car_id = int(self.table_car.item(self.lastClickedRow, 0).text())
            plate = self.table_car.item(self.lastClickedRow, 1).text()
            color = self.table_car.item(self.lastClickedRow, 2).text()
            database.updateRecord(car_id, plate, color)
        
    def deleteRow(self):
        if(self.lastClickedRow != -1):
            car_id = int(self.table_car.item(self.lastClickedRow, 0).text())
            database.deleteRecord(car_id)
    
def setFrame(frame):
    height, width, channel = frame.shape
    bytesPerLine = 3 * width
    qImg = QtGui.QImage(frame.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888).rgbSwapped()
    pixmap = QtGui.QPixmap.fromImage(qImg)
    window.frame.setPixmap(pixmap)
    

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()