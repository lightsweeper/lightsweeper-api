""" Contains wrappers for various audio backends """

import atexit
import os
import random
import sys
import time

from _thread import start_new_thread

from collections import OrderedDict

from lightsweeper.lsconfig import userSelect
from lightsweeper import lsconfig

class _lsAudio:


    def __init__(self, initSound=False, useMidi=False, debug=True):
        self.soundVolume = 1.0
        self.musicVolume = 1.0
        self.conf = lsconfig.readConfiguration()
        self.sounds = dict()
        self.useMidi = useMidi
        self.playlist = self.Playlist(self)

        self.musicIsPlaying = False

        self._init()
        if initSound:
            self.playSound('StartUp.wav')

        self.setSoundVolume(0.75)
        self.setMusicVolume(0.75)

######  Music control

    def playMusic(self):
        self.playlist.play()

    def stopMusic(self):
        self.playlist.stop()

    def setMusicVolume(self, vol):
        self.musicVolume = vol
        self._setMusicVolume(vol)


######  Sound effect control

    def loadSound(self, filename, name=None):
        soundFile = self._locateSound(filename)
        if name is None:
            name = os.path.basename(soundFile).split(".")[0]
        print("Loading sound {:s} as {:s}".format(soundFile, name))
        self._loadSound(soundFile, name)

    def playSound(self, name, custom_relative_volume=1.0):
        try:
            sound = self.sounds[name]
        except KeyError:
            self.loadSound(name, name)
        self._playSound(name, custom_relative_volume)

    def stopSounds(self):
        self._stopSounds()

    def setSoundVolume(self, vol):
        self.soundVolume = vol

    def _locateSound(self, filename):
        relativeSounds = os.path.abspath(sys.path[0])
        gameSounds = os.path.join(self.conf["GAMESDIR"], "sounds")
        systemSounds = os.path.join(lsconfig.lsSysPath, "sounds")
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
                print("WARNING: Cannot find sound {:s}.".format(filename))
                return False
        return(filename)

    class Playlist():

        def __init__(self, audioTarget):
            self.audioTarget = audioTarget
            self.autoStart = False
            self.fadeTime = 5000 # Time to fade in milliseconds
            self.queue = self.PlaylistQueue(self.audioTarget._loadMusic)

        def add(self, filename, name=None, autoStart=False):
            songFile = self.audioTarget._locateSound(filename)
            if name is None:
                name = os.path.basename(songFile).split(".")[0]
            print("Adding {:s} to music queue".format(name))
            self.queue.update({name:songFile})
            if autoStart is True:
                if not self.audioTarget._musicIsPlaying():
                    self.play()

        def play(self, fadeIn=False):
            if fadeIn is True:
                self.audioTarget._playMusic(fadeIn=self.fadeInTime if fadeIn else 0)
            else:
                self.audioTarget._playMusic()
            self.audioTarget.musicIsPlaying = True

        def stop(self, fadeOut=False):
            self.audioTarget._stopMusic(fadeOut=self.fadeOutTime if fadeOut else 0)
            self.audioTarget.musicIsPlaying = False

        def __setattr__(self, name, value):
            super().__setattr__(name, value)
            if name == "fadeTime":
                self.fadeInTime = value
                self.fadeOutTime = value

        class PlaylistQueue(OrderedDict):

            def __init__(self, loader):
                self.loader = loader
                super().__init__()

            def __setitem__(self, key, value):
                super().__setitem__(key, value)
                for song in self.values():
                    self.loader(song)
                    


class _pygameAudio(_lsAudio):

    try:
        import pygame.midi
    except ImportError:
        print("No midi :(")

    def _init(self):
        print("Using pygame for Audio...")
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        if self.useMidi is True:
            self._initMidi()
        atexit.register(self._cleanup)


    def _cleanup(self):
        print("\nCleaning up...")
        if self.useMidi is True:
            pygame.midi.quit()

        # Ugly, but pygame.mixer.quit() hangs debian due to an SDL bug:
        # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=708760
        os._exit(1)


    def _loadMusic(self, filename):
        if len(self.playlist.queue) == 1:
            pygame.mixer.music.load(filename)
        else:
            pygame.mixer.music.queue(filename)

    def _playMusic(self, loops=-1, fadeIn=False):
        if pygame.mixer.music.get_busy():
            if self.musicIsPlaying:
                print("The music is already playing!")
                return
            else:
                pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.play(loops=loops)
        if fadeIn:
            start_new_thread(self._fadeInMusic, (fadeIn,))

    def _fadeInMusic (self, fadeInTime):
        targetVolume = self.musicVolume
        volumeIncrement = targetVolume/fadeInTime
        for i in range(fadeInTime):
            self.setMusicVolume(volumeIncrement * i)
            time.sleep(.001)

    def _fadeOutMusic (self, fadeOutTime):
        volumeDecrement = self.musicVolume/fadeOutTime
        for i in reversed(range(fadeOutTime)):
            self.setMusicVolume(volumeDecrement * i)
            time.sleep(.001)
        pygame.mixer.music.pause()

    def _stopMusic(self, fadeOut):
        if fadeOut > 0:
            start_new_thread(self._fadeOutMusic, (fadeOut,))
        else:
            pygame.mixer.music.pause()

    def _setMusicVolume(self, vol):
        pygame.mixer.music.set_volume(vol)


    def _loadSound(self, filename, name):
        sound = pygame.mixer.Sound(filename)
        self.sounds[name] = sound

    def _playSound(self, name, custom_relative_volume=-1):
        print("Playing sound", name)
        sound = self.sounds[name]
        if custom_relative_volume >= 0:
            sound.set_volume(custom_relative_volume * self.soundVolume)
        else:
            sound.set_volume(self.soundVolume)
        pygame.mixer.Sound.play(sound)

    def _stopSounds(self):
        for name in self.sounds.keys():
            pygame.mixer.Sound.stop(self.sounds[name])

    def _setSoundVolume(self, vol):
        #print("setting sound vol:" + str(vol))
        #self.soundVolume = vol
        pass

  # Midi support is very experimental

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

    def midiSoundOn(self, instrument=19, note=72):
        self.midi_out.set_instrument(instrument)
        self.midi_out.note_on(note,int(self.soundVolume * 127))


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
