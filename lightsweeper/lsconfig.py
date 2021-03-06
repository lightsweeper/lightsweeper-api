""" Contains tools used to create, read, and manage Lightsweeper configurations """

from collections import defaultdict
import os
import json
import numbers

from lightsweeper.lstile import LSOpen
from lightsweeper.lstile import LSRealTile

DEFAULTCONFIGURATION = dict()

lsSysPath = os.path.dirname(os.path.abspath(__file__))

class FileDoesNotExistError(IOError):
    """ Custom exception returned when the config file is non-existant. """
    pass

class FileExistsError(IOError):
    """
        Custom exception returned by writeConfig() when the config file is already present
        and overwrite=False
    """
    pass
    
class CannotParseError(IOError):
    """ Custom exception returned when the config file is present but cannot be parsed. """
    pass

class InvalidConfigError(Exception):
    """ Custom exception returned when the configuration is not valid. """
    pass
    
def getConfigurationPaths(configurationFilePath = None):
    # Returns a list of paths to lightsweeper configuration files
        
    fileName = "lightsweeper.conf"                      # Default configuration file name
                                                        # Configuration search space:
    defaultPaths = ["/LightSweeper",                        # Look for a systemwide /LightSweeper/ folder in root
                    os.path.expanduser("~/.lightsweeper"),  # Look for a hidden .lightsweeper/ folder in user's home directory
                    os.path.expanduser("~/"),               # No dedicated Lightsweeper directory, look in user's home directory
                    os.getcwd()]                            # Look in current working directory
        
        
    if configurationFilePath is not None:
        absPath = os.path.abspath(configurationFilePath)
        if os.path.isfile(absPath):                             # If you provide an absolute path to a valid configuration file it will
            return([absPath])                                   # be the sole configuration used. Otherwise files override individual
                                                                # options according to the heirarchy in defaultPaths
        elif (os.path.exists(absPath) is not True) and (configurationFilePath is not None):
            fileName = configurationFilePath                    # Provided file is not a directory or link, so assume it's an alternate
                                                                # base name
        elif os.path.isdir(absPath):
            defaultPaths.append(configurationFilePath)          # Add provided path directory to end of search space

    outPaths = list()
    for path in [os.path.abspath(p) for p in defaultPaths]:     # No absolute configuration explicitly provided, search in default directories
        if os.path.exists(path) and os.path.isfile(os.path.join(path, fileName)):
            outPaths.append(os.path.join(path, fileName))

    if len(outPaths) > 0:
        return(list(set(outPaths)))     # Passing the list through set removes duplicates that occur when the current working directory is
                                        # also a default search directory
    else:
        cf = configurationFilePath
        if cf is None:
            e = "No {:s} found.".format(fileName)
        else:
            e = "{:s} does not exist.".format(os.path.join(cf, fileName) if os.path.exists(cf) else cf)
        raise(FileDoesNotExistError(e))
    
def readConfiguration (configurationFilePath = None):
    """
        Attempts to load configuration details from lightsweeper conf files.
        configurationFilePath can be either a a valid configuration file name
        or a directory containing a valid configuration named "lightsweeper.conf"
    """
    
    pathList = getConfigurationPaths(configurationFilePath)
    
 #   if not silent:
 #       if len(pathList) is 1:
 #           print("Loading options from {:s}".format(pathList[0]))
 #       else:
 #           print("Loading overrides from {:s}".format(pathList[-1]))

    configuration = DEFAULTCONFIGURATION
    configuration['CONFIGDIR'] = os.path.dirname(pathList[0])
    for path in pathList:
        configuration = parseConfiguration(path, configuration)

    return(configuration)

         # TODO:  Validate configuration

def parseConfiguration (configurationPath, configuration):
    with open(configurationPath, "r") as f:
        lines = [l.rstrip("\n") for l in f]
        i = 0
        for directive in lines:
            i += 1
            if directive.startswith("#"):               # Lines that start with # are comments
                pass
            elif (directive == ""):                     # Ignore blank lines
                pass
            else:
                try:
                    (option, value) = str.split(directive, "=", 1)
                except ValueError:
                    e = "[{:s}: line {:d}] : Invalid directive: {:s}".format(configurationPath, i, directive)
                    raise(InvalidConfigError(e))
                configuration[option.strip()] = value.strip()
        return(configuration)
    
    
class LSFloorConfig:
    """

        This class implements methods to read/write and otherwise
        manipulate Lightsweeper floor configurations.

        Attributes:
            fileName (str):         The name of the config file on disk
            cells (int):            The number of cells in the lightsweeper matrix.
            rows (int):             The number of rows in the lightsweeper matrix.
            cols (int):             The number of columns in the lightsweeper matrix.
            config (list):          A list of 4-tuples of the form (row, col, port, address, calibration)
            board (dict):           A dictionary of dictionaries sorted by row and column, each
                                    containing a tuple of the corresponding tile's port and address
            calibrationMap(dict):   A map keyed by the tuple (address,port) to another tuple containing
                                    low and high observed readings from the tile's touch sensor
    """

    fileName = None
    cells = 0
    rows = 0
    cols = 0
    config = list()
    board = defaultdict(lambda: defaultdict(int))
    calibrationMap = dict()

    def __init__(self, configFile=None, rows=None, cols=None):

        conf = readConfiguration()
        try:
            self.floorDir = conf["FLOORSDIR"]
        except KeyError:
            try:
                self.floorDir = conf["CONFIGDIR"]
            except KeyError:
                self.floorDir = os.path.abspath(os.getcwd())

        if configFile is not None:
            self.fileName = self._formatFileName(configFile)
            try:
                self.loadConfig(self.fileName)
            except FileDoesNotExistError as e:
                if rows is not None and cols is not None:
                    self.config = self._createVirtualConfig(rows, cols)
                else:
                    print(e)
                    raise
            finally:
                self.makeFloor()
        else:
            self.rows = rows
            self.cols = cols
    
    def makeFloor(self):
        """
            This function attempts to parse the data in config and populate the rest of the object
        """
        self.cells = self.rows*self.cols
        self._parseConfig(self.config)
    
    def makeVirtual(self):
        """
            This function turns the current LSFloorConfig object into a virtual floor
        """
        self.cells = self.rows * self.cols
        self.config = self._createVirtualConfig(self.rows, self.cols)

    def loadConfig(self, fileName):
        """
            This function attempts to load the floor configuration at fileName

            Returns:
                True                    if the load was succesful

            Raises:
                IOError                 if fileName is a directory
                FileDoesNotExistError   if fileName is non-existent
                CannotParseError        if the file can not be parsed
        """
        if os.path.exists(fileName) is True:
            if os.path.isfile(fileName) is not True:
                raise IOError(fileName + " is not a valid configuration file!")
        else:
            raise FileDoesNotExistError(fileName + " does not exist!")
        try:
            with open(fileName) as configFile:
                self.config = json.load(configFile)
        except Exception as e:
            print(e)
            raise CannotParseError("Could not parse {:s}!".format(fileName))
        finally:
            print("Board mapping loaded from {:s}".format(fileName))
            self.fileName = fileName
            try:
                self._parseConfig(self.config)
            except Exception as e:
                raise CannotParseError("Parsing of {:s} failed: {s}".format(fileName, e))
            print("Loaded {:d} rows and {:d} columns ({:d} tiles)".format(self.rows, self.cols, self.cells))
            return True

    def containsVirtual(self):
        """
            This function returns true if the configuration contains any
            virtual tiles.
        """
        for cell in self.config:
            if "virtual" in cell[2]:
                return True
        return False

    def containsReal(self):
        """
            This function returns true if the configuration contains any
            real tiles.
        """
        for cell in self.config:
            if "virtual" not in cell[2]:
                return True
        return False

    # prints the list of 4-tuples
    def printConfig(self):
        """
            This function prints the current configuration
        """
      #  self._validate()
        print("The configuration has {:d} entries:".format(len(self.config)))
      #  print(self.cells, self.rows, self.cols) # Debugging
        for cell in self.config:
            print(repr(cell))


    def writeConfig(self, fileName = None, overwrite=False, message=None):
        """
            This function attempts to write the current configuration to disk

            Raises:
                IOError                 if fileName is not set
                FileExistsError         if fileName already exists and overwrite is False
        """
        if fileName is not None:
            self.fileName = self._formatFileName(fileName)
        elif self.fileName is None:
            raise IOError("fileName must be set. Try writeConfig(fileName).")
        if os.path.exists(self.fileName) is True:
            if overwrite is not True:
                raise FileExistsError("Cannot overwrite {:s} (try setting overwrite=True).".format(fileName))
        
        if len(self.calibrationMap) > 0:
            self._storeCalibration()
        with open(self.fileName, 'w') as configFile:
            json.dump(self.config, configFile, sort_keys = True, indent = 4,)
        if message is None:
            if overwrite is True:
                message = "Overwriting {:s}...".format(self.fileName)
            else:
                message = "Your configuration was saved in {:s}".format(self.fileName)
        print(message)

    def listFloorFiles (self):
        return list(filter(lambda ls: ls.endswith(".floor"), os.listdir(self.floorDir)))


    def selectConfig(self):
        """
            This function looks for .floor files in the directory set by the
            directive FLOORSDIR in the general configuration, or, if unset, in
            the current directory and prompts the user to select one, then loads
            it into this instance. 
            
            Raises:
                IOError                 if no .floor files are found
        """

        floorFiles = self.listFloorFiles()
        
        if len(floorFiles) is 0:
            raise IOError("No floor configuration found. Try running LSFloorConfigure.py")
        elif len(floorFiles) is 1:
            fileName = floorFiles[0]
        else:
            print("\nFound multiple configurations: \n")
            fileName = userSelect(floorFiles, "\nWhich floor configuration would you like to use?")
        absFloorConfig = os.path.abspath(os.path.join(self.floorDir, fileName))
        try:
            self.loadConfig(absFloorConfig)
        except CannotParseError as e:
            print("\nCould not parse the configuration at {:s}: {:s}".format(absFloorConfig, e))
            self.selectConfig()

    def _formatFileName(self, fileName):
        if fileName.endswith(".floor") is False:
            fileName += ".floor"
        if os.path.dirname(fileName) != self.floorDir:
            fileName = os.path.join(self.floorDir, fileName)
        return fileName
        
    def _createVirtualConfig(self, rows, cols):
        assert isinstance(rows, numbers.Integral), "Rows must be a whole number."
        assert isinstance(cols, numbers.Integral), "Cols must be a whole number."
        print("Creating virtual configuration with {:d} rows and {:d} columns.".format(rows,cols))
        virtualConfig = list()
        row = 0
        col = 0
        for i in range(1,rows*cols+1):
            virtualConfig.append((row, col, "virtual", i, (127, 127)))
            if col < cols-1:
                col += 1
            else:
                row += 1
                col = 0
        return(virtualConfig)


    def _parseConfig(self, config):
        self.cells = 0
        self.rows = 0
        self.cols = 0
        for (row, col, port, addr, cal) in config:
            self.cells += 1
            if row >= self.rows:
                self.rows = row + 1
            if col >= self.cols:
                self.cols = col + 1
            self.board[row][col] = (port, addr)
            self.calibrationMap[(addr,port)] = cal
        self._validate()

    def _validate(self):
        if self.rows * self.cols is not self.cells:
            raise InvalidConfigError("Configuration is not valid.")
            
    def _storeCalibration(self):
        for i, (row, col, port, address, cal) in enumerate(self.config):
            self.config[i] = (row, col, port, address, self.calibrationMap[address,port])

def userSelect(selectionList, message="Select an option from the list:"):
    def checkInput(selection):
        options = dict(enumerate(selectionList))
        for key, value in options.items():
            if selection.lower() == value.lower():
                return(options[key])
        try:
            selection = int(selection)
        except:
            return False
        if selection in options.keys():
            return options.get(selection)
        return False
        
    def pick(msg):
        x=str()
        while checkInput(x) is False:
            x = input(msg)
        return checkInput(x)
        
    options = enumerate(selectionList)
    print("\r")
    for optNum, optName in options:
        print("  [{:d}] {:s}".format(optNum, optName))
    return pick("{:s} ".format(message))


def validateRowCol(rows, cols, rowsOrCols, isVirtual=True):
    numTiles = rows*cols
    try:
        rowsOrCols = int(rowsOrCols)
    except:
        print("You must enter a whole number!")
        return False
    if numTiles is 0:       # Virtual floor
        return True
    if isVirtual is False:
        if rowsOrCols > numTiles:
            print("There are only " + repr(numTiles) + " tiles!")
            return False
    return True

def validateRow(rows, cols, row, isVirtual=True):
    if not validateRowCol(rows, cols, row, isVirtual):
        return False
    row = int(row)
    if row < 1 or row > rows:
        print("Row must be between 1 and {:d}!".format(rows))
        return False

def validateCol(rows, cols, col, isVirtual=True):
    if not validateRowCol(rows, cols, col, isVirtual):
        return False
    col = int(col)
    if col < 1 or col > cols:
        print("Column must be between 1 and {:d}!".format(cols))
        return False
    

def pickRowCol(rows, cols, message, validationFunc=validateRowCol, isVirtual=True):
    x = input(message)
    while validationFunc(rows, cols, x, isVirtual) is False:
        x = input(message)
    return x

def pickRow(*args, **kwargs):
    return pickRowCol(*args, validationFunc=validateRow, **kwargs)

def pickCol(*args, **kwargs):
    return pickRowCol(*args, validationFunc=validateCol, **kwargs)
    

def YESno(message, default="Y"):
    yesses = ("yes", "Yes", "YES", "y", "Y")
    nos = ("no", "No", "NO", "n", "N")
    if default in yesses:
        answer = input("{:s} [Y/n]: ".format(message))
    elif default in nos:
        answer = input("{:s} [y/N]: ".format(message))
    else:
        raise ValueError("Default must be some form of yes or no")
    if answer is "":
        answer = default
    if answer in yesses:
        return True
    elif answer in nos:
        return False
    else:
        print("Please answer Yes or No.")
        return YESno(message)

def yesNO(message, default="N"):
    return YESno(message, default)

def pickFile(message):
    fileName = input(message)
    if fileName == "" or fileName == "NEW":
        return None
    else:
        if fileName.endswith(".floor") is False:
            fileName += ".floor"
        if os.path.exists(fileName) is False:
            if YESno(fileName + " does not exist, would you like to create it?") is True:
                print("Creating {:s}.".format(fileName))
                floorConfig = LSFloorConfig()
                floorConfig.fileName = fileName
                return floorConfig
            else:
                return pickFile(message)
        try:
            return LSFloorConfig(fileName)
        except Exception as e:
            print(e)
            return pickFile(message)

def configWithKeyboard(floorConfig, tilepile):
    config = list()
    mappedAddrs = list()
    print("Blanking all tiles.")
    for port in tilepile.lsMatrix:
        myTile = LSRealTile(tilepile.sharedSerials[port])
        myTile.assignAddress(0)
    #   myTile.blank()     # Not implemented in LSRealTile
        myTile.setColor(0)  # A TEMPORARY hack

        
    for port in tilepile.lsMatrix:
        for addr in tilepile.lsMatrix[port]:
            rcHash = 0
            while rcHash not in mappedAddrs:
                print("\nPort is: " + repr(port) + " Address is: " + repr(addr))
                myTile = LSRealTile(tilepile.sharedSerials[port])
                myTile.assignAddress(addr)
                myTile.demo(1)
                row=int(pickRow(floorConfig.rows, floorConfig.cols, "Which row?: "))
                col=int(pickCol(floorConfig.rows, floorConfig.cols, "Which col?: "))
                rcHash = int(str(row)+str(col))
                if rcHash not in mappedAddrs:
                    mappedAddrs.append(rcHash)
                    thisTile = (row-1, col-1, port, addr, (127, 127))
                    config.append(thisTile)
                    print("Added this tile: {:s}".format(str(thisTile)))
                else:
                    print("Tile ({:d}, {:d}) has already been configured!".format(row, col))
                    rcHash = 0
                myTile.setColor(0)
        print("")
    floorConfig.config = config
    return floorConfig



def interactiveConfig (config = None):

    if config is None:
        print("\nStarting a new configuration from scratch.")
        config = []
    else:
        print("Configuring {:s}...".format(config.fileName))

    totaltiles = 0

    isLive = True
    try:
        tilepile = LSOpen()
    except IOError as e:
        print("Not using serial because: {:s}".format(str(e)))
        isLive = False

    if isLive is not False:
        # serial ports are COM<N> on windows, /dev/xyzzy on Unixlike systems
        availPorts = list(tilepile.lsMatrix)

        print("Available serial ports: " + str(availPorts))

        for port in tilepile.lsMatrix:
            totaltiles += len(tilepile.lsMatrix[port])

        # It's the little details that count
        question = "Would you like this to be a virtual floor?"
        if totaltiles is 0:
            isVirtual = YESno(question)
        else:
            isVirtual = yesNO(question)
    else:
        isVirtual = True


    if isVirtual is True:
        print("\nConfiguring virtual Lightsweeper floor...")
    else:
        print("\nConfiguring real floor...")

    rows = int(pickRow(totaltiles, totaltiles, "\nHow many rows do you want?: "))
    
    if isVirtual is True or totaltiles is 0:
        cols = int(pickRowCol(rows, totaltiles, "How many columns do you want?: ", isVirtual))
    else:
        cols = int(totaltiles/rows)

    print("OK, you have a floor with " + repr(rows) + " by " + repr(cols)  + " columns")

    if isVirtual is True:
        config = LSFloorConfig(rows=rows, cols=cols)
        config.makeVirtual()
    else:
        if totaltiles is not 0:
            config = LSFloorConfig(rows=rows, cols=cols)
            configWithKeyboard(config, tilepile)

    return config

def main():

    print("TODO: Test lsconfig")


    input("Press return to exit")

if __name__ == '__main__':

    main()

