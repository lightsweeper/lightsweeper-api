""" The lowest level of the LightSweeper API, responsible for modelling and talking to LightSweeper tiles """

import os
import threading
import time
import types

from lightsweeper import Colors
from lightsweeper import Shapes

### Definition of the Lightsweeper low level API

# Todo: Add exceptions for e.g. TileNotFound, etc

class LSTile():
    def __init__(self, row=0, col=0):
        self.row = row
        self.col = col
        self.color = None
        self.shape = None
        self.segments = dict.fromkeys(list(map(chr, range(97, 97+7))))
        for segKey in self.segments.keys():
            self.segments[segKey] = None
        
    def set(self, shape=None, color=None, transition=0):
        if color is not None:
            self.setColor(color)
        if shape is not None:
            self.setShape(shape)
        if(transition != 0):
            self.setTransition(transition)


    def setColor(self, color):
       self.color = color
       for segKey in self.segments.keys():
           segment = self.segments[segKey]
           if segment is not None:
               self.segments[segKey] = color
               

    def setShape(self, shape):
        self.shape = shape
        if shape & Shapes.SEG_A:
            if self.segments["a"] is None:
                self.segments["a"] = self.color
        else:
            self.segments["a"] = None
        if shape & Shapes.SEG_B:
            if self.segments["b"] is None:
                self.segments["b"] = self.color
        else:
            self.segments["b"] = None
        if shape & Shapes.SEG_C:
            if self.segments["c"] is None:
                self.segments["c"] = self.color
        else:
            self.segments["c"] = None
        if shape & Shapes.SEG_D:
            if self.segments["d"] is None:
                self.segments["d"] = self.color
        else:
            self.segments["d"] = None
        if shape & Shapes.SEG_E:
            if self.segments["e"] is None:
                self.segments["e"] = self.color
        else:
            self.segments["e"] = None
        if shape & Shapes.SEG_F:
            if self.segments["f"] is None:
                self.segments["f"] = self.color
        else:
            self.segments["f"] = None
        if shape & Shapes.SEG_G:
            if self.segments["g"] is None:
                self.segments["g"] = self.color
        else:
            self.segments["g"] = None
        
        
    def setSegments(self, rgb):
        c = Colors.rgbToSegments(rgb)
        self.segments["a"] = c[0]
        self.segments["b"] = c[1]
        self.segments["c"] = c[2]
        self.segments["d"] = c[3]
        self.segments["e"] = c[4]
        self.segments["f"] = c[5]
        self.segments["g"] = c[6]
        self.shape = rgb[0]|rgb[1]|rgb[2]
        

    def setTransition(self, transition):
        raise NotImplementedError()
        
    def getShape(self):
        return self.shape
        
    def getColor(self):
        return self.color
        
    def getCol (self):
        return self.col

    def getRow (self):
        return self.row

    def destroy(self):
        raise NotImplementedError()

    def version(self):
        raise NotImplementedError()

    def blank(self):
        self.setColor(None)

    def locate(self):
        raise NotImplementedError()

    def demo (self, seconds):
        raise NotImplementedError()

    def setAnimation(self):
        raise NotImplementedError()

    def flip(self):
        raise NotImplementedError()

    def status(self):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()

    # write any queued colors or segments to the display
    def latch(self):
        raise NotImplementedError()

    def unregister(self):
        raise NotImplementedError()

    # addresses may be HW specific, but can support here
    def assignAddress(self, address):
        self.address = address

    def getAddress(self):
        return self.address

    def calibrate(self):
        raise NotImplementedError()

    def read(self):
        raise NotImplementedError()
        
    def update(self,type):
#        if (type == 'NOW'):
#            return
#        elif (type == 'CLOCK'):
#            return
#        elif (type == 'TRIGGER'):
#            return
#        else:
#            return
        raise NotImplementedError()

    # TODO - how is this different from latch?
    def flushQueue(self):
        raise NotImplementedError()

###################################

    # REMOVEME - old stuff for reference only


    # set immediately or queue this digit in addressed tiles
    # this is a convenience function that calls setSegments
    def setDigit(self, row, column, digit, setItNow = True):
        raise NotImplementedError()


# TODO - perhaps better to use hexlify and unhexlify
#from HexByteConversion import *

# This is a buffer against serial corruption, bigger numbers are slower but more stable
# .005 = Fastst speed before observed corruption (on 24 tiles split between two com ports)
LSWAIT = .005

# these constants copied from LSTileAPI.h

# one byte commands for special test modes
# some of these can be used to visually locate the addressed tile
NOP_MODE        = 0     # this command changes nothing
SENSOR_TEST     = 1     # single digit ADC voltage, color changes at threshold
SENSOR_STATS    = 2 
SEGMENT_TEST    = 3     # walks through all colors of all digits
FASTEST_TEST    = 4     # walks through all colors of all digits fast, looks white
ROLLING_FADE_TEST = 5   # fades in and out from inside to out
ROLLING_FADE_TEST2 = 6  # fades in and out from inside to out
SHOW_ADDRESS    = 7     # display serial address for floor setup
STOP_MODE       = 0xF   # tile stops updating display

LS_LATCH = 0x10       # refresh display from queue - usually address 0
LS_CLEAR = LS_LATCH+1 # blanks the tile
LS_RESET = LS_LATCH+2 # reboot
LS_DEBUG = LS_LATCH+7 # control tile debug output

LS_RESET_ADC = (LS_LATCH+3)    # reset ADC statistics
LS_CALIBRATE_ON = (LS_LATCH+4) # reset ADC statistics and starts calibration
LS_CALIBRATE_OFF =(LS_LATCH+5) # ends calibration, writes ADC stats to EEPROM

# one byte commands defining whether tile is rightside up or not
# the installation may be configured upside down at EEPROM address EE_CONFIG
FLIP_ON  =    (LS_LATCH+8)   # temporary command to flip display upside down
FLIP_OFF =    (LS_LATCH+9)   # restore display rightside up

# last ditch command to set random, but valid address, if all else fails
# for robustness - two byte command and checksum
LS_RANDOM_ADDRESS  = (LS_LATCH+0xF)
LS_RANDOM_ADDRESS2 = (0xD4)

# seven segment display commands with one data byte
SET_COLOR      = 0x20          # set the tile color - format TBD
SET_SHAPE      = (SET_COLOR+1) # set which segments are "on" - abcdefg-
SET_TRANSITION = (SET_COLOR+2) # set transition at the next refresh - format TBD
# seven segment display commands with three data bytes
SET_TILE       = (SET_COLOR+3) #/ set the color, segments, and transition

# one byte query commands returning one byte
ADC_NOW    = 0x40          # unsigned 8 bits representing current ADC
ADC_MIN    = (ADC_NOW + 1) # unsigned 8 bits representing minimum ADC
ADC_MAX    = (ADC_NOW + 2) # unsigned 8 bits representing maximum ADC
ADC_THRESH = (ADC_NOW + 3) # unsigned 8 bits representing sensor threshold
SENSOR_NOW = (ADC_NOW + 4) # unsigned 8 bits representing sensor tripped with history

TILE_STATUS = (ADC_NOW + 8) # returns bit mapped status
# defined bit masks
STATUS_FLIP_MASK =   0x80 # set if segments flipped
STATUS_ERR_MASK  =   0x40 # set if error, and read by RETURN_ERRORS
STATUS_CAL_MASK  =   0x20 # set if currently calibrating

TILE_VERSION = (ADC_NOW + 9) # format TBD - prefer one byte
# The Hardware version may be read and set at the EE_HW address in EEPROM

# EEPROM read is command and one byte of address
EEPROM_READ  =   0x60
# EEPROM write is two byte command, one address byte, one data byte, and checksum
EEPROM_WRITE =   (EEPROM_READ+1)
EEPROM_WRITE2 =  (0x53)

# Defined EEPROM addresses:
EE_ADDR   =  0 # 0 - tile address in top five bytes
EE_CONFIG =  1 # 1 - tile configuration
#       0x80 - AKA STATUS_FLIP_MASK - installed upside-down
#       TBD - color mapping
EE_HW      = 2  # 2 - tile hardware version
#       0 - dev board
#       1 - 3 proto boards
#       2 - 48 tile boards
EE_ADC_MAX  = 3 # High ADC value from calibration - 8 bits of 10 - not sensitive enough?
EE_ADC_MIN  = 4 # Low ADC value from calibration - 8 bits of 10 - not sensitive enough?
EE_PUP_MODE = 5 # Powerup/Reset mode - command from 0 to 0X0F
#          commands that do not work result in the NOP_MODE

# one byte error system commands
MAX_ERRORS    =  4    # number of command errors remembered in error queue
ERROR_CMD     =  0x78 # error test command
RETURN_ERRORS =  (ERROR_CMD+1) # returns the last MAX_ERRORS errors in queue
        # Most recent errors are returned first
        # Clears error queue and STATUS_ERR_MASK
CLEAR_ERRORS  = (ERROR_CMD+2)  # not really needed, but nearly free

# Segment display commands from 0x80 to 0xBF
SEGMENT_CMD =   0x80
SEGMENT_CMD_END = (SEGMENT_CMD+0x3F)
# Depending on the command, up to 4 byte fields will follow (R,G,B and transition)
# Three bits in command declare that R, G, and/or B segment fields will follow
# Two bits define the update condition
# One bit declares that the transition field will follow
#
# One segment byte field will be provided for each of the RGB color bits declared
# Three segment fields allow for arbitrary colors for each segment
# Segment fields are defined in the -abcdefg order, to match LedControl library
SEGMENT_FIELD_MASK  = 0x38
SEGMENT_FIELD_RED   = 0x20
SEGMENT_FIELD_GREEN = 0x10
SEGMENT_FIELD_BLUE  = 0x08
# Segment fields that are not given clear the associated target color segments
# unless the LSB is set in one of the provided segment fields
SEGMENT_KEEP_MASK  = 0x80 # if MSB set, do not clear any segment data

# The update condition bits define when these segments are applied to the display
# There are three update events: immediate, LATCH commands or a sensor detection
# Only four combinations make sense since immediate trumps the other two
# 00 - segment information is immediately applied to the active display
# 01 - segment information is applied after an LATCH command
# 10 - segment information is applied when the sensor detects weight
# 11 - segment information is applied when the sensor detects weight or LATCH
CONDX_MASK       = 0x06
CONDX_IMMED      = 0x00
CONDX_LATCH      = 0x02
CONDX_TRIG       = 0x04
CONDX_LATCH_TRIG = 0x06
#
# The transition bit means a final byte will be used as the transition effect
# These transitions are TBD.
TRANSITION_FIELD_MASK = 0x01
#
# These examples do not include the tile addressing byte -
#
# Set the segments to transition to a blue 4 on the next LATCH:
# B Segments at LATCH  B=bcfg
# 10 001 01 0          00110011
# 0x8A                 0x33
#
# Set the segments to a red white and blue 8 at a sensor trigger:
# RGB Segments at trigger  R=acdfg   G=adg     B=abdeg
# 10 111 10 0              01011011  01001001  01101101
# 0xBC                     0x5B      0x49      0x6D
#
# Immediately set a yellow 6 with transition effect #7:
# Immediate RGB Segments   R=abcdeg  G=abcdeg Transition #7
# 10 110 00 1              01111101  01111101 00000111 (TBD)
# 0xB1                     0x7D      0x7D     0x07 (TBD)
#
# Clear the active display immediately - alternative way to using LS_CLEAR:
# Immediately clear RGB by giving no segment field data
# 10 000 00 0
# 0x80


### Implementation of the Lightsweeper low level API to a ATTiny tile
class LSRealTile(LSTile):
    def __init__(self, sharedSerial, row=0, col=0):
        self.row = row
        self.col = col
        self.mySerial = sharedSerial
        self.serial = self.mySerial
        # cmdNargs is address + command + N optional bytes
        self.Debug = False
        self.shape = None
        self.color = None
        if sharedSerial is None:
            print("Shared serial is None")
        super().__init__(row, col)
            
    def destroy(self):
        return

    def getRowCol(self):
        return (self.row, self.col)
        
    # set immediately or queue this color in addressed tiles
    def setColor(self, color):
        if self.color is color:
            return
        cmd = SET_COLOR
        self.__tileWrite([cmd, color])
        self.color = color

    def setShape(self, shape):
        if self.shape is shape:
            return
        cmd = SET_SHAPE
        self.__tileWrite([cmd, shape])
        self.shape = shape

    def getShape(self):
        return self.shape

    def getColor(self):
        return self.color

    def setTransition(self, transition):
        cmd = SET_TRANSITION
        self.__tileWrite([cmd, self.shape])

    # rgb is a three element list of numbers from 0 (no segments of this color) to 127 (all 7 segments lit)
    # If any element is None, the colors of unspecified fields is preserved
    # Segment fields are defined in the -abcdefg order, to match LedControl library
    def setSegments(self, rgb, conditionLatch = False, conditionTrig = False ):
        cmd = SEGMENT_CMD
        args = []
        clear = True # default to clearing ungiven colors
        # determine if clear non stated colors or keeps them
        if rgb[0] == None:
            clear = False
        elif rgb[1] == None:
            clear = False
        elif rgb[2] == None:
            clear = False

        # One segment byte field will be provided for each of the RGB color bits declared
        # Three segment fields allow for arbitrary colors for each segment
        if rgb[0] != None and rgb[0] >= 1:
            field = rgb[0]
            if not(clear):
                field |= SEGMENT_KEEP_MASK
            cmd += SEGMENT_FIELD_RED
            args.append(field)
        if rgb[1] != None and rgb[1] >= 1:
            field = rgb[1]
            if not(clear):
                field |= SEGMENT_KEEP_MASK
            cmd += SEGMENT_FIELD_GREEN
            args.append(field)
        if rgb[2] != None and rgb[2] >= 1:
            field = rgb[2]
            if not(clear):
                field |= SEGMENT_KEEP_MASK
            cmd += SEGMENT_FIELD_BLUE
            args.append(field)

        # TODO - not tested in tile, probably broken
        if conditionLatch:
            cmd += CONDX_LATCH
        if conditionTrig:
            cmd += CONDX_TRIG

        # TODO - effects transitions

        args.insert(0, cmd) # couldn't insert cmd until all fields are added
        self.__tileWrite(args)
        self.shape = rgb[0]|rgb[1]|rgb[2]


    # expecting a 7-tuple of Color constants
    def setSegmentsCustom(self, segments, setItNow = True):
        pass

    def setDigit(self, digit):
        if ((digit < 0) | (digit > 9)):
            return  # some kind of error - see Noah example
        digitMaps=[0x7E,0x30,0x6D,0x79,0x33,0x5B,0x7D,0x70,0x7F,0x7B]
        self.shape = digitMaps[digit]
        cmd = SET_SHAPE
        self.__tileWrite([cmd, self.shape])

    def update(self,type):
        raise NotImplementedError()
        if (type == 'NOW'):
            return
        elif (type == 'CLOCK'):
            return
        elif (type == 'TRIGGER'):
            return
        else:
            return

    def version(self):
        # send version command
        cmd = TILE_VERSION
        self.__tileWrite([cmd], True)  # do not eat output
        # return response
        val = self.__tileRead()
        return val
    
    # eeAddr and datum from 0 to 255
    def eepromWrite(self,eeAddr,datum):
        # EEPROM write is two byte command, one address byte, one data byte, and checksum
        sum = EEPROM_WRITE + EEPROM_WRITE2 + eeAddr + datum
        chk = (65536 - sum) % 256;
        #chk = chk + 1 # TEST REMOVEME - this breaks checksum
        print("eepromWrite computed sum = %d, checksum = %d" % (sum, chk))
        self.__tileWrite([EEPROM_WRITE, EEPROM_WRITE2, eeAddr, datum, chk])

    # eeAddr and datum from 0 to 255
    def eepromWriteObsolete(self,eeAddr,datum):
        # old EEPROM write is command byte, address byte, data byte, and is horrible dangerous
        self.__tileWrite([EEPROM_WRITE, eeAddr, datum])

    # eeAddr from 0 to 255
    def eepromRead(self,eeAddr):
        # send read command
        cmd = EEPROM_READ
        self.__tileWrite([cmd, eeAddr], True)  # do not eat output
        # return response
        val = self.__tileRead()
        return val

    # read any saved errors
    def errorRead(self):
        # send read command
        cmd = RETURN_ERRORS
        self.__tileWrite([cmd], True)  # do not eat output
        # return response
        val = self.__tileRead()
        return val


    def blank(self):
        self.setColor(0)  # Silly hack, tile should implement blank
        return

    # send mode command that displays stuff
    def locate(self):
        cmd = SHOW_ADDRESS
        self.__tileWrite([cmd])

    def sensorTest(self):
        cmd = 1
        self.__tileWrite([cmd])

    def demo (self, seconds):
        cmd = SEGMENT_TEST
        self.__tileWrite([cmd])

    def setAnimation(self):
        raise NotImplementedError()

# These should be implemented as animations
 #   def flip(self):
 #       cmd = FLIP_ON  # wire API also has FLIP_OFF
 #       self.__tileWrite([cmd])

 #   def unflip(self):
 #       cmd = FLIP_OFF
 #       self.__tileWrite([cmd])

    # TODO: Move this functionality to the "FLIP-ON" command in firmware
    def flip(self):
        tile_config = self.eepromRead(EE_CONFIG)
        try:
            flip_config = ord(tile_config) ^ STATUS_FLIP_MASK
        except TypeError as e:
            if str(e).startswith("ord() expected a character, but string of length"):
                print("Cannot flip tile, try resetting the eeprom with tilediag")
                return False
        self.eepromWrite(EE_CONFIG,flip_config)
        self.reset()

    def status(self):
        raise NotImplementedError()
        return
        
    def sensorStatus(self):
        #self.__tileWrite([SENSOR_NOW], True)  # do not eat output
        #self.__tileWrite([EEPROM_READ, 0], True)  # REMOVEME - may use for testing with no sensor
        self.__tileWrite([ADC_NOW], True)  # do not eat output
        # return response
        thisRead = self.__tileRead(1) # request more than 1 byte means waiting for timeout
        #print ("Sensor status = " + ' '.join(format(x, '#02x') for x in thisRead))
        #if thisRead != None:
        if thisRead:
            for x in thisRead:
                intVal = int(x)
                return intVal #x # val
        # yikes - no return on read from tile?
        return 234
        
    def reset(self):
        versionCmd = LS_RESET
        self.__tileWrite([versionCmd], True)  # do not eat output
        # return response in case tile spits stuff at reset
        time.sleep(1.0)
        val = self.__tileRead()

    # resynchronize communications
    # this uses the global address, so it needs to be done only once per interface port
    def syncComm(self):
        # TODO - __tileWrite could handle global address, simpler to just copy code
        if self.mySerial == None:
            return

        # sync command is two adjacent NOP_MODE commands
        args = [0, NOP_MODE]  # use global address
        count = self.mySerial.safeWrite(args)
        count = self.mySerial.safeWrite(args)
        if self.Debug:
            print("sync command wrote two NOP_MODE commands")

        # read to flush tile debug output
        thisRead = self.mySerial.read(8)
        if len(thisRead) > 0:
            # Debug or not, if tile sends something, we want to see it
            print ("Debug response: " + ' '.join(format(x, '#02x') for x in thisRead))

    def setDebug(self, debugFlag):
        cmd = LS_DEBUG
        self.Debug = debugFlag
        self.__tileWrite([cmd, debugFlag])

    # write any queued colors or segments to the display
    def latch(self, wholePort = False):
        if wholePort:
            keepAddress = self.address
            self.address = 0
        latchCmd = LS_LATCH
        self.__tileWrite([latchCmd])
        if wholePort:
            self.address = keepAddress


    def unregister(self):
        raise NotImplementedError()
        return

    # assignAddress and getAddress are in LSTileAPI base class

    def calibrate(self):
        raise NotImplementedError()
        return

    def read(self):
        raise NotImplementedError()

    def flushQueue(self):
        raise NotImplementedError()

    def setRandomAddress(self):
        # random address set is two byte command and checksum
        sum = LS_RANDOM_ADDRESS + LS_RANDOM_ADDRESS2
        chk = (65536 - sum) % 256;
        #chk = chk + 1 # TEST REMOVEME - this breaks checksum
        print("setRandomAddress computed sum = %d, checksum = %d" % (sum, chk))
        self.__tileWrite([LS_RANDOM_ADDRESS, LS_RANDOM_ADDRESS2, chk])

    # write a command to the tile
    # minimum args is command by itself
    def __tileWrite(self, args, expectResponse=False):
        if self.mySerial == None:
            return

        # flush stale read data if response is expected
        if (expectResponse):
            thisRead = self.mySerial.read(8)
            if len(thisRead) > 0:
                # debug or not, if tile sends something, we want to see it
                if self.Debug:
                    print ("Stale response (" + self.mySerial.port + "->" + repr(self.getAddress()) + "): " + ' '.join(format(x, '#02x') for x in thisRead))

        # insert address byte plus optional arg count
        addr = self.address + len(args) - 1  # command is not counted
        args.insert(0, addr)
        count = self.mySerial.safeWrite(args)
  #      if self.Debug:         # This debug clause breaks "Full test suite" in tilediag.py
 #           writeStr = (' '.join(format(x, '#02x') for x in args))
#            print("0x%x command wrote %d bytes: %s " % (args[1], count, writeStr))

        # if no response is expected, read anyway to flush tile debug output
        # do not slow down to flush if not in debug mode
        if(self.Debug and not(expectResponse)):
            thisRead = self.mySerial.read(8)
            if len(thisRead) > 0:
                #if self.Debug:
                # debug or not, if tile sends something, we want to see it
                if True or self.Debug:
                    print ("Debug response: " + ' '.join(format(x, '#02x') for x in thisRead))
        time.sleep(LSWAIT)

    # read from the tile
    def __tileRead(self, count=8):
        if self.mySerial == None:
            return
        thisRead = self.mySerial.read(count)
        if len(thisRead) > 0:
            if self.Debug:
                print ("Received: " + ' '.join(format(x, '#02x') for x in thisRead))
        #else:
        #    print("Received nothing")
        return thisRead



    ############################################
    # Serial code

def _threadSafeWrite (self, *args, **kwargs):
    # A thread safe write method to be monkey-patched by LSOpen.lsSerial()
    with self.writeLock:
        self.write(*args, **kwargs)


class LSOpen:

    """
        This class probes the LS address space and provides methods for
        for discovering and making use of valid lightsweeper serial objects
    """

    def __init__(self):
        try:
            import serial
        except ImportError as e:
            raise IOError("Could not import serial functions. Make sure pyserial is installed.")
        from serial.tools import list_ports

        self._pyserial = serial
        self._list_ports = list_ports

        self.sharedSerials = dict()

        try:
            self.lsMatrix = self.portmap()
        except Exception as e:
            self.lsMatrix = dict()

        self.numPorts = len(self.lsMatrix)

        if self.numPorts is 0:
            print("Cannot find any lightsweeper tiles")


    def lsSerial(self, port, baud=19200, timeout=0.01):
        """
            Attempts to open the specified com port, returning a pySerial object
            if succesful.
        """
            
        if port in self.sharedSerials.keys():
            return self.sharedSerials[port]
        try:
            self.sharedSerials[port] = self._pyserial.Serial(port, baud, timeout=timeout)
        except self._pyserial.SerialException as e:
            # TODO: Check Exception...
            #       5 = I/O Error (No lightsweeper tiles)
            #       13 = Permissions error (Linux: add user to dialout group)
            raise(e)
        finally:
            # Monkey patch a thread safe writing method onto the pyserial object
            self.sharedSerials[port].writeLock = threading.Lock()
            self.sharedSerials[port].safeWrite = types.MethodType(_threadSafeWrite, self.sharedSerials[port])
            return self.sharedSerials[port]
            
       # return serialObject


    def testport(self, port):
        """
            Returns true if port has any lightsweeper objects listening
        """
        try:
            testTile = LSRealTile(self.lsSerial(port))
        except self._pyserial.SerialException:
            return False
        except KeyError as e:
            return False


        testTile.assignAddress(0)
        if testTile.version():
            return True
        return False


    def availPorts(self):
        """
            Returns a generator for all available serial ports
        """

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


    def validPorts(self):
        """
            Returns a generator for all serial ports with lightsweeper tiles attached
        """
        for validPort in list(filter(self.testport,self.availPorts())):
            yield validPort


    def validAddrs(self, port):
        """
            Returns a generator for valid lightsweeper addresses on provided port
        """
        testTile = LSRealTile(self.lsSerial(port))
        for address in range(1,32):
            tileAddr = address * 8
            testTile.assignAddress(tileAddr)
            if testTile.version():
                yield tileAddr


    def portmap(self):
        """
            Returns a map of responding lightsweeper tiles and serial ports.
            
        """
        return({port:set(self.validAddrs(port)) for port in self.validPorts()})


    def selectPort(self, portList = None):
        """
            Prompts the user to select a valid com port then returns it.
            If you provide this function with a list of serial ports it
            will limit the prompt to those ports.
        """

        posPorts = dict(enumerate(sorted(self.lsMatrix.keys())))

        # TODO: Sanity check that portList consists of valid ports
        if portList is not None:
            posPorts = dict(enumerate(sorted(portList)))

        def checkinput(userSelection):
            if userSelection in posPorts.values():
                return userSelection
            try:
                numericSelection = int(userSelection)
            except ValueError as e:
                if str(e).startswith("invalid literal for int() with base 10:"):
                    return False
                else:
                    raise(e)
            if numericSelection in posPorts.keys():
                return posPorts.get(numericSelection)
            return False

        # Prompts the user to select a valid serial port then returns it
        print("\nThe following serial ports are available:\n")
        for key,val in posPorts.items():
            print("     [" + repr(key) + "]    " + repr(val) + "  (" + repr(len(self.lsMatrix.get(val))) + " attached tiles)")
        userPort = input("\nWhich one do you want? ")
        while checkinput(userPort) is False:
            print("Invalid selection.")
            userPort = input("Which one do you want? ")
        return checkinput(userPort)


