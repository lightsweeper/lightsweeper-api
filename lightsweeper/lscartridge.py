import io
import os
import re
import threading
import time

from collections import defaultdict, OrderedDict

class NoCartReader(Exception):
    """ Custom exception returned when no cartridge readers are found. """
    pass

class ReaderNotSupported(Exception):
    """ Custom exception returned when the host system does not have the requisite
        support for a physical cartridge reader. """
    pass

# Todo: exceptions
# Todo: fix multiple instances

class LSRFID:

    """
        This class provides methods for interacting with LightSweeper
        RFID based cartridges.
    """

    def __init__(self):

        self.resetState()

        try:
            import serial
        except ImportError as e:
            raise ReaderNotSupported("Could not import serial functions: {:s}".format(str(e)))
        from serial.tools import list_ports

        self._pyserial = serial
        self._list_ports = list_ports
        self.serial = self.findReader()
        d = threading.Thread(name='cartParserd', target=self.cartParser)
        d.setDaemon(True)
        d.start()


    def resetState(self):
        self.gameRunning = False
        self.loaded = False
        self.gameID = 0
        self.loadHint = False
        self.scores = defaultdict(list)

    def findReader (self):     
        print("Looking for cartridge reader...")   
        for port in self.availPorts():
            try:
                s = self._pyserial.Serial(port,
                                          9600,
                                          bytesize  = self._pyserial.EIGHTBITS,
                                          parity    = self._pyserial.PARITY_NONE,
                                          stopbits  = self._pyserial.STOPBITS_ONE,
                                          timeout   = 3) # Experimentally dictated
            except self._pyserial.SerialException as e:
                s = False
            if s:
                if (s.read(5) == b'READY'):
                    print("Cartridge reader detected at: {:s}".format(port)) # Debugging
                    getLine(s)  # Purges the following blank line from the buffer
                    return(s)
        raise NoCartReader("No cartridge reader found!")

    def addScore(self, name, score):
        if not self.gameRunning:
            print("No cartridge inserted!")
            return
        if len(name) > 3:
            print("Name must be less than 3 characters!")
            return
        cmd = "ADDSCORE {:s} {:d}\n".format(name, score)
        for char in cmd:
            self.serial.write(char.encode())
        scores = self.scores
        try:
            scores[score].append(name)
        except KeyError:
            scores[score] = [name]
        self.scores = scores
      #  self.scores = OrderedDict(sorted(scores.items(), reverse = True))

    def sendScoresRequest(self):
        if not self.gameRunning:
            print("No cartridge inserted!")
            return
        for char in "SCORES\n":
            self.serial.write(char.encode())

    def setHint(self, hint):
        if not self.gameRunning:
            print("No cartridge inserted!")
            return
        for char in "SETLOADTARGET {:s}\n".format(hint):
            self.serial.write(char.encode())

    def cartParser(self):
        while True:
            response = getLine(self.serial).split(" ")
      #      print(" ".join(response)) # Debugging
            if response[0] == "CART":
                if response[1] == "INSERTED":
                    self.gameID = int("".join(response[2:]), 16)
                    self.gameRunning = True
                    time.sleep(1) # Give the reader a chance to initialize its internals
                    self.sendScoresRequest()
                elif response[1] == "PULLED":
                    self.resetState()
                else:
                    print("Response not recognized" + " ".join(response))
            elif response[0] == "LOAD":
                self.loadHint = " ".join(response[1:])
            elif bool(re.search('\d\/\d', response[0])):
                numScores, totalScores = response[0].split("/")
                scores = defaultdict(list)
                for i in range(int(numScores)):
                    name, score = getLine(self.serial).split()
                    scores[int(score)].append(name)
            #    self.scores = OrderedDict(sorted(scores.items(), reverse = True))
                self.scores = scores
                self.loaded = True
            elif response[0] == "OK":
                print("LSRFID: OK") # Debugging
            elif response[0] == "INVALID" and response[1] == "NAME":
                print("Score not added, name must be <= 3 characters.")
            elif response[0] == "NO" and response[1] == "CART":
                print("Cartridge removed during response write!")
            elif response[0] == "READY":        # Cartridge reader reset
                self.resetState()
            elif response[0] == "DEADBEEF":
            # Rather than trying to properly manage our serial resources
            # across processes in a portable way let's just reset everything
            # whenever anything goes wrong
                self.serial.close()
                self.serial.open()
                self.resetState()
            elif response[0] == "?":
                # We sent garbage to the reader, let's just reset everything,
                # slow down, and try again
                self.serial.close()
                self.serial.open()
                self.resetState()
            else:
                print("Response not recognized: " + " ".join(response))

    def availPorts(self):
        """
            Returns a generator for all available serial ports
        """

        # This function is identical to lstile.LSOpen.availPorts()
        if os.name == 'nt': # windows
            for i in range(256):
                try:
                    s = self._pyserial.Serial(i)
                    s.close()
                    yield 'COM' + str(i + 1)
                except self._pyserial.SerialException:
                    pass
        else:               # unix
            for port in self._list_ports.comports():
                yield port[0]

def getLine(pySerialObject):
    dataBuffer = str()
    while True:
        char = pySerialObject.read(1)
    #    print(char.decode("ASCII"), end=" ") #Debugging
        if char != b'\n':
            try:
                dataBuffer += char.decode("ASCII")
            except UnicodeDecodeError as e:
                print("MooOOoo!")
                return ("DEADBEEF")          # A wild hack has appeared! (See line 132)
        else:
            return(dataBuffer[:-1])

def main():

    print("TODO: Test lscartridge")
    
    rfidcart = LSRFID()
    print("Insert a cartridge to test.")
    while not rfidcart.gameRunning:
        pass
    for score, names in rfidcart.scores.items():
        for name in names:
            print("{:s}    {:d}".format(name, score))
    while rfidcart.gameRunning:
        pass
    input("Press return to exit")

if __name__ == '__main__':

    main()
