#!/usr/bin/python
#
# XRandomClicker.py

# logs
# - click position relative to the viewpoint (at the center of the window)
# - mouse click position relative to center of the target button
# targets moves randomly after been hit
# output
# global x and y position of the click and the relative error to the target (button)
#   |
#  -|-----> x
#   |
#   |
# y v
#  
# (0,0) at upper left

import sys, random
from PyQt4 import QtGui, QtCore
import wiiLogger

class RandomButton(QtGui.QPushButton):
	def __init__(self, title, parent):
		QtGui.QPushButton.__init__(self, title, parent)
		self.parent = parent

	# on click handler if button hit
	def mousePressEvent(self, event):
		QtGui.QPushButton.mousePressEvent(self, event)
		if event.button() == QtCore.Qt.LeftButton:
			self.move(random.random() * (self.parent.width()-self.width()),
					random.random() * (self.parent.height()-self.height()))

			print event.globalPos().x()-self.parent.viewpoint().x() ,",", \
				event.globalPos().y()-self.parent.viewpoint().y(), ",",\
				event.x()-self.geometry().width()/2, ",",\
				event.y()-self.geometry().height()/2
	

class MainWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self, parent)

		self.setWindowTitle('XRandomClicker')

		self.button = RandomButton('Hit me!', self)
		self.button.setGeometry(self.width()/2,self.height()/2,60,35)


		#self.showMaximized()
		screen = QtGui.QDesktopWidget().screenGeometry()

		print "# button size (60,35)"
		print '# screen size ',screen.width(), 'x', screen.height()
		print '#log format dx to VP ,dy to VP,dx to target ,dy to target'

		self.setGeometry((screen.width()-1500)/2,(screen.height()-700)/2,1500, 700)

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)
		paint.setPen(QtCore.Qt.blue)
		size = self.size()
		paint.setBrush(QtGui.QColor(255, 0, 0, 200))
        	paint.drawRect(size.width()/2-5, size.height()/2-5, 10, 10)
		paint.end()	

	# on click handler if button missed
	def mousePressEvent(self, event):
		print event.globalPos().x()-self.viewpoint().x(), ",",\
			event.globalPos().y()-self.viewpoint().y(),",",\
			event.globalPos().x() - self.button.geometry().center().x(), ",",\
			event.globalPos().y() - self.button.geometry().center().y() 

	# returns viewpoint as center of the widget (painted in paintEvent)
	def viewpoint(self):
		return QtCore.QPoint(self.x()+self.size().width()/2, self.y()+self.size().height()/2)

if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	mw = MainWidget()
	mw.show()
	sys.exit(app.exec_())


