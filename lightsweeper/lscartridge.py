import io
import os
import re
import threading
import time

from collections import defaultdict, OrderedDict

# Todo: exceptions
# Todo: fix multiple instances

class LSRFID:

    """
        This class provides methods for interacting with LightSweeper
        RFID based cartridges.
    """

    def __init__(self):

        self.gameRunning = False

        try:
            import serial
        except ImportError as e:
            raise IOError("Could not import serial functions: {:s}".format(e))
        from serial.tools import list_ports

        self._pyserial = serial
        self._list_ports = list_ports
        self.serial = self.findReader()
        d = threading.Thread(name='cartParserd', target=self.cartParser)
        d.setDaemon(True)
        d.start()

    def findReader (self):        
        for port in self.availPorts():
            try:
                s = self._pyserial.Serial(port,
                                          9600,
                                          bytesize  = self._pyserial.EIGHTBITS,
                                          parity    = self._pyserial.PARITY_NONE,
                                          stopbits  = self._pyserial.STOPBITS_ONE,
                                          timeout   = None)
            except self._pyserial.SerialException as e:
                s = False
            if s:
                if (s.read(5) == b'READY'):
                    print("Cartridge reader detected at: {:s}".format(port)) # Debugging
                    getLine(s)  # Purges the following blank line from the buffer
                    return(s)
        print("No cartridge reader found!")
        raise Exception     # Todo: actual exception

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
        self.sendScoresRequest()

    def sendScoresRequest(self):
        if not self.gameRunning:
            print("No cartridge inserted!")
            return
        for char in "SCORES\n":
            self.serial.write(char.encode())
        

    def cartParser(self):
        while True:
            response = getLine(self.serial).split(" ")
      #      print(" ".join(response)) # Debugging
            if response[0] == "CART":
                if response[1] == "INSERTED":
                    self.gameRunning = True
                    self.gameID = hex(int("".join(response[2:]), 16))
                    self.sendScoresRequest()
                elif response[1] == "PULLED":
                    self.gameRunning = False
                    self.gameID = 0
                    self.loadHint = ""
                    self.scores = dict()
                else:
                    print("Response not recognized" + " ".join(response))
            elif response[0] == "LOAD":
                self.loadHint = " ".join(response[1:])
            elif bool(re.search('\d/\d', response[0])):
                numScores, totalScores = response[0].split("/")
                scores = defaultdict(list)
                for i in range(int(numScores)):
                    name, score = getLine(self.serial).split()
                    scores[int(score)].append(name)
                self.scores = OrderedDict(sorted(scores.items(), reverse = True))
            elif response[0] == "OK":
                print("Score added.") # Debugging
            elif response[0] == "INVALID" and response[1] == "NAME":
                print("Score not added, name must be <= 3 characters.")
            elif response[0] == "NO" and response[1] == "CART":
                print("Cartridge removed during response write!")
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
        if char != b'\n':
            dataBuffer += char.decode("ASCII")
        else:
            return(dataBuffer[:-1])

def main():

    print("TODO: Test lscartridge")
    
    rfidcart = LSRFID()
    print("Insert a cartridge to test.")
    while not rfidcart.gameRunning:
        pass
    time.sleep(1)
    for score, names in rfidcart.scores.items():
        for name in names:
            print("{:s}    {:d}".format(name, score))
    while rfidcart.gameRunning:
        pass
    input("Press return to exit")

if __name__ == '__main__':

    main()
