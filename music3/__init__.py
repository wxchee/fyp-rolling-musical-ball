import sounddevice as sd
import soundfile as sf
import numpy as np
from musicgen import tools
from shared import goal_amplitude, goal_speed
import sys
# import librosa
from time import time
from math import ceil, floor
min_sample_chunk = 8820

AUDIO_FILES = [
    'audios/track_drum.wav',
    'audios/track_piano.wav',
    'audios/track_mag_string.wav'
]

class MusicGen:
    def __init__(self):
        self.freq = 0

        self.amplitude = 0
        self.volume_fade_duration = 0.3

        self.speed = 1

        self.f_1 = 0
        self.f_2 = 0
        self.f_3 = 0

        self.tracks = {0: None, 1: None, 2: None}

        for i, file in enumerate(AUDIO_FILES):
            wav, sr = sf.read(file)
            self.tracks[i] = { 'd': wav[:682760], 'l': 682760 if len(wav) > 682760 else len(wav), 'f': 0, 'sync': 99}
            print(i, sr, self.tracks[i])
        # # data, self.samplerate = librosa.load(wav_file, sr=None, mono=True)
        
        # goal_amplitude.value = 1

        self.outstream = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 0))
        self.outstream2 = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 1))
        self.outstream3 = sd.OutputStream(samplerate=sr,channels=1,blocksize=min_sample_chunk,callback= lambda *args: self._callback(*args, 2))
        
        self.init_t = time()
        self.outstream.start()
        self.outstream2.start()
        self.outstream3.start()
        

    def _callback(self, outdata, frames, paT, status, i):
        if (status):
            print('STATUS: ', status, sys.stderr)

        cur_t = paT.currentTime - self.init_t
        # print(cur_t % 5)
        if (cur_t % 2) < self.tracks[i]['sync']: # sync each track every 5 seconds
            self.tracks[i]['f'] = floor(cur_t * 44100.0) % self.tracks[i]['l']
            print(i, 'repos', floor(cur_t * 44100.0) % self.tracks[i]['l'])
        
        self.tracks[i]['sync'] = cur_t % 2
        
        if self.tracks[i]['f'] + frames > self.tracks[i]['l']:
            remain_frames = frames - (self.tracks[i]['l'] - self.tracks[i]['f'])
            new_wav = np.concatenate((self.tracks[i]['d'][self.tracks[i]['f']:], self.tracks[i]['d'][:remain_frames]))
            self.tracks[i]['f'] = remain_frames
        else:
            new_wav = self.tracks[i]['d'][self.tracks[i]['f']:self.tracks[i]['f']+frames]
            self.tracks[i]['f'] += frames
        
        outdata[:,0] = new_wav



    def get_amp_env(self, start_amp, frames):
        dir = 1 if start_amp < goal_amplitude.value else -1
        diff = goal_amplitude.value - start_amp
        
        end_amp = start_amp + diff * min(1, frames / (tools.fs * self.volume_fade_duration))
        
        amp_wave = np.linspace(start_amp, end_amp, frames)
        if dir == 1:
            if (end_amp < goal_amplitude.value):
                return amp_wave
        else:
            if (end_amp > goal_amplitude.value):
                return amp_wave

        diff_frames = int(abs(diff * tools.fs * self.volume_fade_duration))

        return np.linspace(start_amp, goal_amplitude.value, diff_frames)
    
