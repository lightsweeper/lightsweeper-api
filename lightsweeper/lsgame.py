""" Contains methods responsible for running and interacting with LightSweeper games """

import copy
import json
import os
import random
import shelve
import threading
import time

from _thread import start_new_thread
from datetime import timedelta
from collections import defaultdict
from collections import OrderedDict

from lightsweeper.lsdisplay import LSDisplay
from lightsweeper.lsaudio import LSAudio
from lightsweeper.lsconfig import LSFloorConfig
from lightsweeper.lsconfig import userSelect
import lightsweeper.lsconfig as lsconfig

from lightsweeper import Colors
from lightsweeper import Shapes

FPS = 30

class LSGame():
    def __init__(game, display, audio, rows, cols, reader):

        # Standard game setup
        game.display = display
        game.audio = audio
        game.rows = rows
        game.cols = cols
        game.ended = False
        game.duration = 0
        game.frameRate = FPS
        game.display.clearAll()
        game._reader = reader

    def over (game, score=None):
        start_new_thread(game._keepScore, (score,))

    def _keepScore(game, score):
        name = "???"
        if score is not None:
            try:
                scores = game.scoreKeeper.getScores()
            except AttributeError:
                print("Warning: No scoring scheme set, using the default of HighScoreWins")
                game.HighScoreWins()
                scores = game.scoreKeeper.getScores()
            if game.scoreKeeper.isHighScore(score, scoreFill=10):
                keyboard = EnterName(game.display, game.audio, game.rows, game.cols, game._reader)
                keyboard.init()
                game.heartbeat = keyboard.heartbeat
                game.stepOn = keyboard.stepOn
                game.stepOff = keyboard.stepOff
                while not keyboard.output:
                    pass
                name = keyboard.output
            game.__addScore__(score, name)
            game.scoreKeeper.showScores()
        print("[Game Over]")
        game.ended = True

    def HighScoreWins(game):
        game.scoreKeeper = LSScores(game.__class__.__name__, cartridgeReader=game._reader)
        game.__addScore__ = game.scoreKeeper.addHighScore

    def LowScoreWins(game):
        game.scoreKeeper = LSScores(game.__class__.__name__, cartridgeReader=game._reader, reverseScores = True)
        game.__addScore__ = game.scoreKeeper.addLowScore

    def HighTimeWins(game):
        game.scoreKeeper = LSScores(game.__class__.__name__, cartridgeReader=game._reader, timeScores = True)
        game.__addScore__ = game.scoreKeeper.addHighTime

    def LowTimeWins(game):
        game.scoreKeeper = LSScores(game.__class__.__name__, cartridgeReader=game._reader, reverseScores = True, timeScores = True)
        game.__addScore__ = game.scoreKeeper.addLowTime
        
class LSScreenSaver(LSGame):
    def __init__(game, *args, **kwargs):
        super().__init__(*args, **kwargs)
        game.duration = 5
        game.frameRate = 15


from lightsweeper import lsscreensavers

SAVERS = lsscreensavers.screensaverList


#enforces the framerate, pushes sensor data to games, and selects games
class LSGameEngine():
    initLock = threading.Event()
    SIMULATED_FLOOR = True
    CONSOLE = False
    numPlays = 0
    _warnings = []

    def __init__(self, GAME, floorConfig=None, loop=True, cartridgeReader=False):
        self.cartridgeReader = cartridgeReader
        self.loop = loop
        self.wait = time.sleep
        if floorConfig is None:
            conf = LSFloorConfig()
            conf.selectConfig()
        else:
            conf = LSFloorConfig(floorConfig)
        if conf.containsVirtual() is True:
            self.REAL_FLOOR = False
        else:
            self.REAL_FLOOR = True

        self.ROWS = conf.rows
        self.COLUMNS = conf.cols
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Board size is {:d}x{:d}".format(self.ROWS, self.COLUMNS))
            
        self.GAME = GAME
        self.audio = LSAudio(initSound=True)
        self.display = LSDisplay(conf=conf, eventCallback = self.handleTileStepEvent, initScreen=True)
        self.moves = []
        self.sensorMatrix = defaultdict(lambda: defaultdict(int))
        self.newGame(self.GAME)

        #these are for bookkeeping
        self.frames = 0
        self.frameRenderTime = 0
        
        # This lock prevents handleTileStepEvent() from being run by polling loops before init is complete
        self.initLock.set()

    def newGame(self, Game):
        try: # Game is a list of game classes, pick one at random
            GAME = random.choice(Game)
        except: # Game was specified
            GAME = Game
        self.currentGame = GAME.__name__

        print("LSGameEngine: Starting {:s}...".format(self.currentGame))
        self.game = GAME(self.display, self.audio, self.ROWS, self.COLUMNS, self.cartridgeReader)
        self.startGame = time.time()
        self.game.sensors = self.sensorMatrix
        if not isinstance(self.game, LSScreenSaver):
            self.numPlays += 1
        try:
            self.game.init()
        except AttributeError as e:
        #    raise(e)    # Debugging
            self._warnOnce("{:s} has no init() method.".format(self.currentGame))
        
    def beginLoop(self, plays = 0):
        while True:
            if plays is not 0 and self.numPlays <= plays:
                self.enterFrame()
            elif plays is 0:
                self.enterFrame()
            else:
                self.insertCoin()

    def insertCoin(self):
        self.gameOver()
        # TODO: Instead of quitting, go to game/demo screen and wait for someone to reset

    def gameOver(self):
        print(" G A M E  O V E R ")
        self.display.clearAll()
        self.display.setMessage(int(self.display.rows/2)-1,"GAME", start=int(self.display.cols/2)-2)
        self.display.setMessage(int(self.display.rows/2), "OVER", start=int(self.display.cols/2)-2)
        self.display.heartbeat()
        input("--Press any key to exit--\n")
#        self.display.floor.saveAndExit(0)

    def handleTileStepEvent(self, row, col, sensorPcnt):
        self.initLock.wait()
        if int(sensorPcnt) is 0:
            try:
                self.game.stepOff(row, col)
            except AttributeError as e:   # Game has no stepOff() method
                if "object has no attribute 'stepOff'" in str(e):
                    self._warnOnce("{:s} has no stepOff() method.".format(self.currentGame))
                else:
                    raise(e)
         #   print("stepOff: ({:d},{:d})".format(row, col)) # Debugging
            self.moves = [x for x in self.moves if x[0] is not row and x[1] is not col]
        else:
            if self.sensorMatrix[row][col] is 0:
         #       if sensorPcnt > 20:                 # Only trigger > 20%, hack to guard against phantom sensors
         #                                           # TODO: This but better
                if sensorPcnt > 0:
                    try:
                        self.game.stepOn(row, col)
                    except AttributeError as e:   # Game has no stepOn() method
                        if "object has no attribute 'stepOn'" in str(e):
                            self._warnOnce("{:s} has no stepOn() method.".format(self.currentGame))
                        else:
                            raise(e)
                 #   print("stepOn: ({:d},{:d})".format(row, col)) # Debugging
                    m = (row, col)
                    self.moves.append(m)
        self.sensorMatrix[row][col] = int(sensorPcnt)

    def pauseGame (self):
        print("Game is paused.")
        while self.game.frameRate < 1:
            pass
        print("Game resuming...")

    def enterFrame(self):
        if self.game.duration is not 0:
            playTime = (time.time() - self.startGame)
            if playTime > self.game.duration:
            #    self.game.ended = True
                self.newGame(self.GAME)
        startEnterFrame = time.time()
        if not self.game.ended:
            self.game.heartbeat(self.moves)
            self.display.heartbeat()
            self.audio.heartbeat()
        else:
            self.newGame(SAVERS)    # Super hacky, should be in gameOver
         #   self.newGame(self.GAME)
        frameRenderTime = (time.time() - startEnterFrame)
        self.wait(self.padFrame(frameRenderTime))

    def padFrame(self, renderTime):
        if self.game.frameRate is 0:
            self.pauseGame()
        spaces = " " * (52)
        fps = 1.0/renderTime
        if fps < self.game.frameRate or self.game.frameRate < 0:
            print("{1:s}{0:.4f} FPS".format(1.0/renderTime, spaces), end="\r")
            return(0)
        else:
            print("{1:s}{0:.4f} FPS".format(self.game.frameRate, spaces), end="\r")
            return((1.0/self.game.frameRate)-renderTime)
        print(spaces * 2, end="\r")

    def _warnOnce(self, warning):
        if warning not in self._warnings:
            print("WARNING: {:s}".format(warning))
            self._warnings.append(warning)


class LSScores:
    def __init__(self, gameName, cartridgeReader=False, reverseScores = False, timeScores = False):
        self._cartReader = cartridgeReader
        self.gameName = gameName
        self._reverseScores = reverseScores
        self._timeScore = timeScores

    def _validateRawScore(self, rawScore, warning):
        try:
            if rawScore < 0 or rawScore > 999999999:
                print(warning)
                return False
        except TypeError:
            print(warning)
            return False          
        return True

    def _validateScore(self, score):
        warning = "Warning: Score must be an integer from 0 to 999,999,999"
        return self._validateRawScore(score, warning)

    def _validateTime(self, time):
        warning = "Warning: Time must be a number of seconds from 0 to 999,999,999"
        return self._validateRawScore(time, warning)
        
    def _addRawScore(self, score, name):
        if self._cartReader:
            self._cartReader.addScore(name, score)

        self.diskScores[score].append(name)
        self.scoresFile[self.gameName] = self.diskScores
        self.scoresFile.close()     # Write to disk

    def _loadScores(self):
        if self._cartReader:
            while not self._cartReader.loaded:
                pass

        self.diskScores = self._loadScoresFromDisk()

        if self._cartReader:
            return(self._cartReader.scores)
        else:
            return(self.diskScores)

    def _loadScoresFromDisk(self, fileName=None):

        if fileName is None:
            conf = lsconfig.readConfiguration()
            
            try:
                scoresFile = conf['SCORESFILE']
            except KeyError:
                scoresFile = os.path.join(conf['CONFIGDIR'], ".scores")
        else:
            scoresFile = fileName

        self.scoresFile = shelve.open(scoresFile)   # Shelve is faster than json
                                                    # Important since this single
                                                    # db stores all scores for
                                                    # all games


        try:
            return(defaultdict(list, self.scoresFile[self.gameName]))
        except KeyError:
            return defaultdict(list)


    def getScores(self, limit=10):
        scoreList = list()
        i = 0
        for score, names in OrderedDict(sorted(self._loadScores().items(), reverse = True)).items():
            if self._reverseScores:
                score *= -1
            for name in names:
                if i < limit:
                    scoreList.append((name, score))
                    i += 1
        return scoreList

    def isHighScore(self, score, scoreFill = 1):
        if scoreFill < 1:
            raise Exception("scoreFill must be greater than 0")
        scores = self.getScores(scoreFill)
        if len(scores) < scoreFill:
            return True
            print("No scores!") # Debugging
        if self._reverseScores:
            if score < scores.pop()[1]:
                return True
        else:
            if score > scores.pop()[1]:
                return True
        return False


    def showScores(self, limit=10):
        print("    T O P  S C O R E S\n")
        for (name, score) in self.getScores(limit):
            print("         {:s}    {:s}   ".format(name, str(score) if not self._timeScore else timedelta(seconds=score)))
        print("")

    def addHighScore(self, score, name="???"):
        if self._validateScore(score):
            self._addRawScore(score, name)
            print("High score recorded: {:d}".format(score)) # Debugging
        else:
            print("Invalid score: {:s}".format(repr(score)))

    def addLowScore(self, score, name="???"):
        if self._validateScore(score):
            self._addRawScore(score * -1, name)
            print("Low score recorded: {:d}".format(score))    # Debugging
        else:
            print("Invalid score: {:s}".format(repr(score)))

    def addHighTime(self, timeScore, name="???"):
        if self._validateTime(timeScore):
            self._addRawScore(timeScore, name)
            print("High time recorded: {:s}".format(timedelta(seconds=timeScore))) # Debugging
        else:
            print("Invalid time score: {:s}".format(repr(timeScore)))

    def addLowTime(self, timeScore, name="???"):
        if self._validateTime(timeScore):
            self._addRawScore(timeScore * -1, name)
            print("Low time recorded: {:s}".format(timedelta(seconds=timeScore))) # Debugging
        else:
            print("Invalid time score: {:s}".format(repr(timeScore)))

#HI_SCORE_CUTOFF = 5
#class HighScores():
#    def __init__(self, filename="scores"):
#        conf = lsconfig.readConfiguration()
#        fname = os.path.join(conf["CONFIGDIR"], filename)
#        self.fname = fname
#        self.writeToSerial = False
#        self.highScoreThreshold = 0
#        self.scores = [0]
#        #load scores from the card
#        if self.writeToSerial:
#            import serial
#        #load in scores from a file
#        self._parseScores(fname)
#
#    def _parseScores(self, fname):
#        if not os.path.isfile(fname):
#            self.namesAndScores = [["000", 0]]
#            return()
#        with open(fname) as f:
#            self.namesAndScores = json.load(f)
#        for entry in self.namesAndScores:
#            self.scores.append(int(entry[1]))
#        if len(self.scores) < HI_SCORE_CUTOFF:
#            self.highScoreThreshold = 0
#        else:
#            self.highScoreThreshold = self.scores[HI_SCORE_CUTOFF-1]
#
#    def isHighScore(self, score):
#        #TODO: modify somehow to enable lower scores to be better depending on the game
#        return score > self.highScoreThreshold
#
#
#    def saveHighScore(self, name, score):
#        if self.cartridgeReader:
#            self.cartridgeReader.addScore(name, score)
#        if score < self.scores[len(self.scores) - 1]:
#            self.scores.append(score)
#            self.namesAndScores.append((name, str(score)))
#            with open(self.fname, 'w') as f:
#                f.dump(self.namesAndScores)
#            return
#        for i in range(len(self.scores)):
#            if self.scores[i] < score:
#                self.scores.insert(i, score)
#                self.namesAndScores.insert(i, (name, str(score)))
#                with open(self.fname, 'w') as f:
#                    json.dump(self.namesAndScores, f)
#                return
#
#    def getHighScores(self, limit=10, start=0):
#        if self.writeToSerial:
#            pass
#        else:
#            result = []
#            i = start
#            while len(result) < limit and i < len(self.namesAndScores):
#                result.append((self.namesAndScores[i][0], str(self.namesAndScores[i][1])))
#                i += 1
#            return result

class EnterName(LSGame):


    def init(self):
        self.output = False
        if self.rows < 3 or self.cols < 3:
            raise Exception("Board must be at least 3 x 3!")
        self.initials = ["A", "A", "A"]
        self.locks = [False, False, False]
        self.offset = (self.rows/2, self.cols/2)

        r = self.offset[0]
        c = self.offset[1]

        self.display.set(r-1, c-1, Shapes.UP_ARROW, Colors.WHITE)
        self.display.set(r-1, c, Shapes.UP_ARROW, Colors.WHITE)
        self.display.set(r-1, c+1, Shapes.UP_ARROW, Colors.WHITE)

        self.display.set(r+1, c-1, Shapes.DOWN_ARROW, Colors.WHITE)
        self.display.set(r+1, c, Shapes.DOWN_ARROW, Colors.WHITE)
        self.display.set(r+1, c+1, Shapes.DOWN_ARROW, Colors.WHITE)


    def heartbeat(self, activeSensors):
        if self.output:
            return
        if self.locks[0] and self.locks[1] and self.locks[2]:
            self.output = self.initials[0] + self.initials[1] + self.initials[2]

        r = self.offset[0]
        c = self.offset[1]

        self.display.set(r, c-1, Shapes.charToShape(self.initials[0]), Colors.YELLOW if self.locks[0] else Colors.CYAN)
        self.display.set(r, c, Shapes.charToShape(self.initials[1]), Colors.YELLOW if self.locks[1] else Colors.CYAN)
        self.display.set(r, c+1, Shapes.charToShape(self.initials[2]), Colors.YELLOW if self.locks[2] else Colors.CYAN)


    def stepOn(self, row, col):
        if self.output:
            return
        r = self.offset[0]
        c = self.offset[1]

        # Animate buttons
        if (col > c-2 and col < c+2):
            if row == r-1:
                if self.locks[int(col-c+1)]:
                    return
                self.display.setShape(row, col, Shapes.SEG_C+Shapes.SEG_E+Shapes.SEG_G)
                self.audio.playSound("Blop.wav")
            elif row == r+1:
                if self.locks[int(col-c+1)]:
                    return
                self.display.setShape(row, col, Shapes.SEG_B+Shapes.SEG_F+Shapes.SEG_G)
                self.audio.playSound("Blop.wav")
        

        if row == r-1:
            if col == c-1:
                self.charUp(0)
            elif col == c:
                self.charUp(1)
            elif col == c+1:
                self.charUp(2)
        if row == r+1:
            if col == c-1:
                self.charDown(0)
            elif col == c:
                self.charDown(1)
            elif col == c+1:
                self.charDown(2)
        if row == r:
            if col == c-1:
                self.toggleLocks(0)
            elif col == c:
                self.toggleLocks(1)
            elif col == c+1:
                self.toggleLocks(2)

                                

    def stepOff(self, row, col):
        if self.output:
            return
        r = self.offset[0]
        c = self.offset[1]

        if (col > c-2 and col < c+2):
            if row == r-1:
                self.display.setShape(row, col, Shapes.UP_ARROW)
            elif row == r+1:
                self.display.setShape(row, col, Shapes.DOWN_ARROW)


    def charUp (self, index):
        if self.locks[index]:
            return
        char = ord(self.initials[index])
        if char == ord("A"):
            self.initials[index] = "Z"
        else:
            self.initials[index] = chr(char-1)
            

    def charDown (self, index):
        if self.locks[index]:
            return
        char = ord(self.initials[index])
        if char == ord("Z"):
            self.initials[index] = "A"
        else:
            self.initials[index] = chr(char+1)

    def toggleLocks (self, index):
        self.locks[index] = not self.locks[index]
        if self.locks[index] is True:
            if self.locks[0] and self.locks[1] and self.locks[2]:
                self.audio.playSound("NewLevel.wav")
            else:
                self.audio.playSound("ding_1.wav")
        else:
            self.audio.playSound("ZipBlop.wav")





#    def __init__(self, display, rows, cols, seconds=30, highScore = None):
#        print("EnterName init()")
#        self.rows = rows
#        self.cols = cols
#        self.timer = CountdownTimer(seconds, self.timesUp, self.secondTick)
#        self.display = display
#        self.display.clearAll()
#        self.seconds = seconds
#        self.currentText = "_" * cols
#        self.timestamp = time.time()
#        self.enteringName = False
#        self.rainbow = [Colors.RED, Colors.YELLOW, Colors.GREEN,Colors.CYAN,Colors.BLUE,Colors.MAGENTA]
#        self.color = self.rainbow.pop(0)
#        self.ended = False
#        self.letterMap = []
#        self.highScore = highScore
#        alphabet = "abcdefghijklnopqrstuUyz"
#        i = 0
#        for r in range(rows):
#            currentRow = []
#            if r == 0:
#                pass
#            else:
#                for c in range(cols):
#                    currentRow.append(alphabet[i:i+1])
#                    i += 1
#            self.letterMap.append(currentRow)
#
#    def heartbeat(self, sensorsChanged):
#        if not self.enteringName:
#            self.display.setMessage(1, "HIGH", self.color)
#            self.display.setMessage(2, "SCORE", self.color)
#            if self.highScore is not None:
#                self.display.setMessage(3, str(self.highScore), Colors.WHITE)
#
#            if len(self.rainbow) > 0:
#                if time.time() - self.timestamp > 0.5:
#                    self.color = self.rainbow.pop(0)
#                    self.timestamp = time.time()
#                return
#            elif len(self.rainbow) == 0:
#                self.enteringName = True
#                #self.ended = True
#
#       #display letters
#       self.display.setMessage(0, self.currentText, color = Colors.CYAN)
#        for i in range(len(self.letterMap)):
#            self.display.setMessage(i, self.letterMap[i])
#
#        #check for letter pressed
#        for move in sensorsChanged:
#            try:
#                self.currentText = self.currentText.replace('_', self.letterMap[move.row][move.col], 1)
#                print("stepped on", self.letterMap[move.row][move.col], "text", self.currentText)
#            except:
#                pass
#            if '_' not in self.currentText:
#                self.ended = True
#        self.timer.heartbeat()

#        #time left
#        self.display.set(self.rows - 1, self.cols - 2, Shapes.digitToHex(int(self.timer.seconds / 10)), Colors.YELLOW)
#        self.display.set(self.rows - 1, self.cols - 1, Shapes.digitToHex(int(self.timer.seconds % 10)), Colors.YELLOW)
#
#    def timesUp(self):
#        self.ended = True
#
#    def secondTick(self):
#        pass

class CountdownTimer():
    def __init__(self, countdownFrom, finishCallback, secondCallback=None, minuteCallback=None):
        self.countdownFrom = countdownFrom
        self.seconds = countdownFrom
        self.secondCallback = secondCallback
        self.minuteCallback = minuteCallback
        self.finishCallback = finishCallback
        self.timestamp = time.time()
        self.done = False

    def heartbeat(self):
        if self.done:
            return
        ts = time.time()
        if ts - self.timestamp > 1:
            self.timestamp = ts
            self.seconds -= 1
            if self.seconds == 0:
                self.finishCallback()
                self.done = True
                return
            elif self.secondCallback is not None:
                self.secondCallback()
            elif self.seconds % 60 == 0:
                self.minuteCallback()

def main():
    print("TODO: testing lsgame")

if __name__ == '__main__':
    main()
