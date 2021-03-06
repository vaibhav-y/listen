import numpy as np
import math
import scipy.ndimage

from IPython import embed
from listen.utils.array_helpers import array_helpers as ahelp
from listen.utils.filters import Filter
from scipy.signal import hanning

class Spectrogram(object):
    def __init__(self, fft_size, step_size, thresh):
        self.fftsize = int(fft_size)
        self.step = int(step_size)
        self.thresh = thresh

    def overlap(self, X):
        """
        Create an overlapped version of X
        Parameters
        ----------
        X : ndarray, shape=(n_samples,)
            Input signal to window and overlap

        Returns
        -------
        X_strided : shape=(n_windows, window_size)
            2D array of overlapped X
        """
        if self.fftsize % 2 != 0:
            raise ValueError("Window size must be even!")
        # Make sure there are an even number of windows before stridetricks
        append = np.zeros((self.fftsize - len(X) % self.fftsize))
        X = np.hstack((X, append))

        ws = self.fftsize
        ss = self.step
        a = X

        valid = len(a) - ws
        nw = valid // ss
        nw = 1 if nw == 0 else nw
        out = np.ndarray((nw, ws), dtype=a.dtype)

        for i in range(nw):
            # "slide" the window along the samples
            start = i * ss
            stop = start + ws
            out[i] = a[start: stop]

        return out

    def stft(self, X, mean_normalize=True, real=False, compute_onesided=True):
        """Computes STFT for 1D real valued input X
        """
        if real:
            local_fft = np.fft.rfft
            cut = -1
        else:
            local_fft = np.fft.fft
            cut = None
        if compute_onesided:
            cut = self.fftsize // 2
        if mean_normalize:
            X -= X.mean()

        X = self.overlap(X)

        size = self.fftsize
        # win = 0.54 - .46 * np.cos(2 * np.pi * np.arange(size) / (size - 1))
        win = hanning(size)
        X = X * win[None]
        X = local_fft(X)[:, :cut]
        return X

    def compute_spectrum(self, data, logscale=False):
        """Creates a spectrogram using data passed
        """
        specgram = np.abs(self.stft(data, real=False, compute_onesided=True))
        # specgram = ahelp.linscale(specgram, left=1e-6, right=1)

        if logscale:
            lt = np.log(self.thresh)
            specgram = np.log10(specgram)
            specgram[specgram < -lt] = -lt

        return specgram

    def compute_mel_cepstrum(self, data, nb_mfcc_bins, frange, compression=1):
        # embed()
        specgram = self.compute_spectrum(data, logscale=True)
        mel_filter, _ = Filter.create_mel_filter(
            self.fftsize, nb_mfcc_bins, *frange)

        mel_cepstrum = specgram.dot(mel_filter).T
        if compression != 1:
            mel_cepstrum = scipy.ndimage.zoom(mel_cepstrum.astype(
                'float32'), [1, 1. / compression]).astype('float32')

        mel_cepstrum = mel_cepstrum[:, 1:-1]
        return mel_cepstrum
