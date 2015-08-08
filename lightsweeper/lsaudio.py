""" Contains wrappers for various audio backends """

import atexit
import os
import random
import sys

from lightsweeper.lsconfig import userSelect
from lightsweeper import lsconfig

class _lsAudio:
    def __init__(self, initSound=True, useMidi=False):
        self.soundVolume = 1.0
        self.loadedSongs = []
        self.soundDictionary = {}
        self.playSound('StartUp.wav')

    def heartbeat(self):
        pass

    def loadSong(self, filename, name):
        pass

    def playSong(self, filename, loops=0):
        pass

    def stopSong(self, fadeOut = 0.1):
        pass

    def setSongVolume(self, vol):
        pass

    #plays loaded songs in a random order
    def shuffleSongs(self):
        pass

    def loadSound(self, filename, name):
        pass

    def playSound(self, filename, custom_relative_volume=-1):
        conf = lsconfig.readConfiguration()
        relativeSounds = os.path.abspath(sys.path[0])
        gameSounds = os.path.join(conf["GAMESDIR"], "sounds")
        systemSounds = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
        if (filename == os.path.abspath(filename)):     # filename is absolute
            pass
        else:
            if os.path.isfile(os.path.join(systemSounds, filename)):
                filename = os.path.join(systemSounds, filename)
            elif os.path.isfile(os.path.join(gameSounds, filename)):
                filename = os.path.join(gameSounds, filename)
            elif os.path.isfile(os.path.join(relativeSounds, filename)):
                filename = os.path.join(relativeSounds, filename)
            else:
                print("WARNING: Cannot find {:s}.".format(filename))
                return
        self._playSound(filename)

    def _playSound(self, filename, custom_relative_volume=-1):
        pass

    def playLoadedSound(self, name):
        pass

    def stopSounds(self):
        pass

    def setSoundVolume(self, vol):
        self.soundVolume = vol


class _pygameAudio(_lsAudio):
  #  import pygame.midi
    def __init__(self, initSound=True, useMidi = False):
        self.useMidi = useMidi
        print("Using pygame for Audio...")
        self.SONG_END = pygame.USEREVENT + 1
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        if useMidi is True:
            self._initMidi()
        atexit.register(self._cleanup)
        _lsAudio.__init__(self)

    def _initMidi(self):
        print("Initializing MIDI subsystem...")
        pygame.midi.init()
        
        midiOpts = dict()
        for i in range( pygame.midi.get_count() ):
            r = pygame.midi.get_device_info(i)
            (interface, name, inp, outp, opened) = r
            if outp:
                midiPortString = "{:s} ({:s})".format(name.decode("utf-8"), interface.decode("utf-8"))
                midiOpts[midiPortString] = i
        if len(midiOpts) == 0:
            print("Cannot play midi, WEEPWEEPWEEPWEP")
            sys.exit()
        elif len(midiOpts) == 1:
            midiPort = 0
        else:
            print("Multiple targets found:")
            midiSelect = userSelect(list(midiOpts.keys()), "\nSelect a midi port:")
            midiPort = midiOpts[midiSelect]
        self.midi_out = pygame.midi.Output(midiPort, 0)

    def _cleanup(self):
        print("\nCleaning up...")
        if self.useMidi is True:
         #   del self.midi_out       # Prevents "Bad pointer" error on exit
            pygame.midi.quit()
     #   pygame.mixer.quit()
        os._exit(1)                 # Ugly, but pygame.mixer.quit() hangs debian (due to an SDL bug: https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=708760)
        mypid = os.getpid()
        print(mypid)
        

    def heartbeat(self):
        #for event in pygame.event.get():
        #    if event.type == self.SONG_END:
        #        self.shuffleSongs()
        pass

    def _loadSong(self, filename, name):
        try:
            pygame.mixer.music.load("sounds/" + filename)
        except Exception:
            pass                # TODO: Handle this properly
        self.loadedSongs.append(filename)
        pass

    def _playSong(self, filename, loops=0):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=256)
        pygame.mixer.music.load("sounds/" + filename)
        pygame.mixer.music.play(loops)
        pass

    def stopSong(self, fadeOut = 0.1):
        pass

    def setSongVolume(self, vol):
        pygame.mixer.music.set_volume(vol)
        pass

    #plays loaded songs in a random order
    def _shuffleSongs(self):
        songCount = len(self.loadedSongs)
        song = random.randint(0, songCount - 1)
        print("songs", songCount)
        print("playing song", self.loadedSongs[song])
        self.playSong(self.loadedSongs[song], 1)
        pygame.mixer.music.set_endevent(self.SONG_END)

    def _loadSound(self, filename, name):
        print("loading sound " + filename + " into " + name)
        sound = pygame.mixer.Sound("sounds/" + filename)
        self.soundDictionary[name] = sound

    def _playSound(self, filename, custom_relative_volume=-1):
        print("playing sound", filename)
        sound = pygame.mixer.Sound(filename)
        if custom_relative_volume >= 0:
            sound.set_volume(custom_relative_volume * self.soundVolume)
        else:
            sound.set_volume(self.soundVolume)
        self.soundDictionary[filename] = sound
        pygame.mixer.Sound.play(sound)
        #do we need this code?        
        #try:
        #    pygame.mixer.music.load("sounds/" + filename)
        #    pygame.mixer.music.play(1)
        #except:
        #    print("Could not load file " + filename)

    def _playLoadedSound(self, name):
        sound = self.soundDictionary[name]
        pygame.mixer.Sound.play(sound)

    def stopSounds(self):
        for name in self.soundDictionary.keys():
            pygame.mixer.Sound.stop(self.soundDictionary[name])

    def midiSoundOn(self, instrument=19, note=72):
        self.midi_out.set_instrument(instrument)
        self.midi_out.note_on(note,int(self.soundVolume * 127))

    def setSoundVolume(self, vol):
        #print("setting sound vol:" + str(vol))
        #self.soundVolume = vol
        pass

try:
    import pygame
    import pygame.mixer
    lsAudioBackend = _pygameAudio
except:
    lsAudioBackend = _lsAudio
    print("No sound platform installed. Make sure pygame is installed with sdl mixer support.")

#this class serves as a common controller for audio
class LSAudio(lsAudioBackend):
    pass
