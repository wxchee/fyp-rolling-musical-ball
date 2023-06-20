import sounddevice as sd
import soundfile as sf
import numpy as np
from musicgen import tools
from shared import get_vol, volX, volY, volZ
import sys
# import librosa
from time import time
from math import ceil, floor
min_sample_chunk = 1000

AUDIO_FILES = [
    'audios/track_drum.wav',
    'audios/track_piano.wav',
    'audios/track_mag_string.wav'
]

SYNC_INTERVAL = 2

class MusicGen:
    def __init__(self):
        self.freq = 0

        self.amplitude = 0
        self.volume_fade_duration = 0.3

        self.speed = 1

        self.tracks = {0: None, 1: None, 2: None}

        for i, file in enumerate(AUDIO_FILES):
            wav, sr = sf.read(file)
            self.tracks[i] = { 'd': wav[:682760], 'l': 682760 if len(wav) > 682760 else len(wav), 'f': 0, 'amp': 0}
            # print(i, sr, self.tracks[i])
        # # data, self.samplerate = librosa.load(wav_file, sr=None, mono=True)

        self.outstream = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 0))
        self.outstream2 = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 1))
        self.outstream3 = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 2))
        
        self.init_t = time()
        self.cur_t = 0
        self.last_sync = 99

        self.outstream.start()
        self.outstream2.start()
        self.outstream3.start()
        

    def _callback(self, outdata, frames, paT, status, i):
        if (status):
            print('STATUS: ', status, sys.stderr)
        
        # if i == 0:
        self.cur_t = paT.currentTime - self.init_t
        
        
        if (self.cur_t % SYNC_INTERVAL) < self.last_sync: # sync each track every 5 seconds
            self.tracks[i]['f'] = floor(self.cur_t * 44100.0) % self.tracks[i]['l']
            print(i, 'repos', floor(self.cur_t * 44100.0) % self.tracks[i]['l'])
        
        if i == 0:
            self.last_sync = self.cur_t % SYNC_INTERVAL
        
    
        if self.tracks[i]['f'] + frames > self.tracks[i]['l']:
            remain_frames = frames - (self.tracks[i]['l'] - self.tracks[i]['f'])
            new_wav = np.concatenate((self.tracks[i]['d'][self.tracks[i]['f']:], self.tracks[i]['d'][:remain_frames]))
            self.tracks[i]['f'] = remain_frames
        else:
            new_wav = self.tracks[i]['d'][self.tracks[i]['f']:self.tracks[i]['f']+frames]
            self.tracks[i]['f'] += frames

        

        # handle amplitude change
        amp_env = np.ones(frames)
        goal_amp = get_vol(i)
        if self.tracks[i]['amp'] != goal_amp:
            if abs(self.tracks[i]['amp'] - goal_amp) < 0.01:
                self.tracks[i]['amp'] = goal_amp
            else:
                amp_env = self.get_amp_env(self.tracks[i]['amp'], frames, goal_amp)
                self.tracks[i]['amp'] = amp_env[-1]


        target_amp = amp_env if self.tracks[i]['amp'] != goal_amp else self.tracks[i]['amp']

        outdata[:,0] = new_wav * target_amp


    def get_amp_env(self, start_amp, frames, goal):
        dir = 1 if start_amp < goal else -1
        diff = goal - start_amp
        
        end_amp = start_amp + diff * min(1, frames / (tools.fs * self.volume_fade_duration))
        
        amp_wave = np.linspace(start_amp, end_amp, frames)
        if dir == 1:
            if (end_amp < goal):
                return amp_wave
        else:
            if (end_amp > goal):
                return amp_wave

        diff_frames = int(abs(diff * tools.fs * self.volume_fade_duration))

        return np.linspace(start_amp, goal, diff_frames)
    
