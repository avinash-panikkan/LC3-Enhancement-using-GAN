import os
import librosa
import numpy as np

window_size = 2 ** 14  # about 1 second of samples
sample_rate = 16000
stride = 0.5





def slice_signal(file, window_size, stride, sample_rate):
    """
    Helper function for slicing the audio file
    by window size and sample rate with [1-stride] percent overlap (default 50%).
    """
    wav, sr = librosa.load(file, sr=sample_rate)
    hop = int(window_size * stride)
    slices = []
    for end_idx in range(window_size, len(wav), hop):
        start_idx = end_idx - window_size
        slice_sig = wav[start_idx:end_idx]
        slices.append(slice_sig)
    return slices

file = "D:\Main Project\Project\\test\output\output1\p232_001.wav"

wav, sr = librosa.load(file,sr=None)

print(wav)

clean_sliced = slice_signal(file, window_size, stride, sample_rate)
print("shape",len(clean_sliced))

for idx, segment in enumerate(clean_sliced):
    print("Shape of segment {}: {}".format(idx+1, segment.shape))
