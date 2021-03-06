""" Bundles various floors together """

from lightsweeper.lsfloor import LSFloor
from lightsweeper.lsemulate import LSPygameFloor
from lightsweeper.lsemulate import LSASCIIFloor
from lightsweeper.lsemulate import BadEmulator
from lightsweeper.lsconfig import LSFloorConfig

from lightsweeper import Shapes
from lightsweeper import Colors
import time

wait = time.sleep

class LSDisplay():
    """
        LSDisplay acts as the main interface for LightSweeper games, it wraps the
        LSFloor object and provides support for animations, text, and higher-level
        logic.

            Example:
                >>> import lsdisplay

                >>> d = lsdisplay.LSDisplay()

                >>> d.setMessage(0,"Hello World")
                >>> d.heartbeat()

    """

    def __init__(self, rows=None, cols=None, conf=None, eventCallback=None, initScreen=True):
        if conf is None:
            if rows is None or cols is None:
                conf = LSFloorConfig()
                conf.selectConfig()
            else:
                conf = LSFloorConfig(rows=rows, cols=cols)
                conf.makeVirtual()

        self.floor = LSFloor(conf, eventCallback = eventCallback)

        try:
            self.floor.register(LSPygameFloor)      # For now it's the only emulator we have
        except BadEmulator:
            self.floor.register(LSASCIIFloor)

        self.rows = conf.rows
        self.cols = conf.cols
        self.lastTileSetTimestamp = time.time()

        if initScreen is True:
            self.splash()
            wait(3)
            self.clearAll()



    def splash(self):
        if self.rows > 1 and self.cols > 7:
            r = int(self.rows/2)-1 # Row offset
            c = int(self.cols/2)-4
            #LIGHTSWEEPER
            self.set(r+0, c+1, Shapes.L, Colors.RED)
            self.set(r+0, c+2, Shapes.I, Colors.YELLOW)
            self.set(r+0, c+3, Shapes.G, Colors.GREEN)
            self.set(r+0, c+4, Shapes.h, Colors.BLUE)
            self.set(r+0, c+5, Shapes.T, Colors.MAGENTA)
            self.set(r+1, c+0, Shapes.S, Colors.RED)
            self.set(r+1, c+1, Shapes.u, Colors.YELLOW)
            self.set(r+1, c+2, Shapes.V, Colors.YELLOW)
            self.set(r+1, c+3, Shapes.E, Colors.GREEN)
            self.set(r+1, c+4, Shapes.E, Colors.CYAN)
            self.set(r+1, c+5, Shapes.P, Colors.BLUE)
            self.set(r+1, c+6, Shapes.E, Colors.MAGENTA)
            self.set(r+1, c+7, Shapes.R, Colors.WHITE)
        else:
            self.setAll(Shapes.EIGHT, Colors.RANDOM())
        self.heartbeat()

    def heartbeat(self):
        self.floor.heartbeat()


    def set(self, row, col, shape, color):
        self.floor.set(row, col, shape, color)


    def setAll(self, shape, color):
        self.floor.setAll(shape, color)

    def setDigit(self, row, col, digit, color=None):
        self.floor.setDigit(row, col, digit, color)
        
    def setAllDigit(self, digit, color=None):
        self.floor.setAllDigit(digit, color)

    def setRow(self, row, shape, color):
        self.floor.setRow(row, shape, color)

    def setColumn(self, column, shape, color):
        self.floor.setColumn(column, shape, color)

    #segColors is a list of seven colors in A,...,G order of segments
    def setCustom(self, row, col, segColors):
        self.floor.setSegments(row, col, Colors.segmentsToRgb(segColors))

    def setAllCustom(self, segColors):
        self.floor.setAllSegments(Colors.segmentsToRgb(segColors))

    def setColor(self, row, col, color):
        self.floor.setColor(row, col, color)


    def setAllColor(self, color):
        self.floor.setAllColor(color)

    def setShape(self, row, col, shape):
        self.floor.setShape(row, col, shape)

    def setAllShape(self, shape):
        self.floor.setAllShape(shape)


    def setMessage(self, row, message, color = Colors.WHITE, start = 0, cutoff = -1):
        #TODO: ability to right-justify
        if cutoff is -1:
            cutoff = self.cols
        shapes = Shapes.stringToShapes(message)
        col = start
        while col < cutoff and len(shapes) > 0:
            self.set(row, col, shapes.pop(0), color)
            col += 1

    def setMessageSplit(self, row, message1, message2, color1 = Colors.WHITE, color2 = Colors.YELLOW, middle=-1):
        #first determine which tile is the middle--this one must be left blank
        if middle == -1:
            middle = int(self.cols / 2)
        self.setMessage(row, message1, color1, cutoff=middle)
        self.setMessage(row, message2, color2, start=middle)
        #fill left side of middle with message1, right side with message2
        #TODO: ability to favor one message or the other, preferentially cutting off the less-favored one



    # Deprecated
#    def showHighScores(self, highScores, label=True):
#        self.setAll(Shapes.ZERO, Colors.BLACK)
#        if label:
#            self.setMessage(0,"HIGH", color=Colors.BLUE)
#            self.setMessage(1,"SCORES", color=Colors.GREEN)
#            row = 2
#        else:
#            row = 0
#        while row < self.rows and len(highScores) > 0:
#            score = highScores.pop(0)
#            self.setMessageSplit(row, score[0], score[1], middle=4)
#            # self.setMessage(row, score[0])
#            # self.setMessage(row + 1, score[1], color=Colors.YELLOW, start=self.cols - 3)
#            row += 1

    def clear(self, row, col):
        try:
            self.floor.blank(row, col)
        except AttributeError as e:     # Tile is out of bounds
            pass                        # Just keep on rolling

    def clearAll(self):
        self.floor.clearAll()
        self.heartbeat()

    # Deprecated
 #   def hasShapeChangesFor(self, row, col):
 #       val = True
 #       try:
 #           self.shapes[(row, col)]
 #       except:
 #          val = False
 #       return val

 #   def hasColorChangesFor(self, row, col):
 #       val = True
 #       try:
 #           self.colors[(row, col)]
 #       except:
 #           val = False
 #       return val
 #
 #   def setFrame(self):
 #       self.heartbeat()
 #       self.colors = dict()
 #       self.shapes = dict()

    def getShape(self, row, col):
        return self.shapes[(row, col)]

    def getColor(self, row, col):
        return self.colors[(row, col)]

    def getAllShapes(self, shape):
        for row in range(self.rows):
            for col in range(self.cols):
                self.shapes[(row, col)] = shape

    def getAllColors(self, color):
        for row in range(self.rows):
            for col in range(self.cols):
                self.colors[(row, col)] = color

    # ?
  #  def add(self, row, col, shape, color):
  #      pass

   # def addCustom(self, row, col, colors):
   #     pass

   # def addAnimation(self, row, col, animation, loops):
   #     pass


def main():
    print("Testing LSDisplay with virtual floor")
    display = LSDisplay(3,8)

    for j in range(8):
        display.setColor(0, j, Colors.RED)
        display.setShape(0, j, Shapes.ZERO)
    wait(0.2)
    for j in range(8):
        display.setColor(1, j, Colors.YELLOW)
        display.setShape(1, j, Shapes.ZERO)
    wait(0.2)
    for j in range(8):
        display.setColor(2, j, Colors.GREEN)
        display.setShape(2, j, Shapes.ZERO)
    wait(0.2)
    for i in range(3):
        for j in range(8):
            display.setShape(i, j, Shapes.digitToHex(i))
            wait(0.01)
    wait(0.2)
    for i in range(0, 100):
        display.heartbeat()
        #display.setColor(random.randint(0, display.row-1), random.randint(0, display.cols-1), Colors.RANDOM())
        #display.setShape(random.randint(0, display.row-1), random.randint(0, display.cols-1), Shapes.randomDigitInHex())


if __name__ == '__main__':
    main()
