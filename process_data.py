from __future__ import print_function

import os
# os.environ['LIBROSA_CACHE_DIR'] = '/data/tmp/librosa_cache'
# os.environ['LIBROSA_CACHE_LEVEL'] = '50'
import time
import math
import glob
from multiprocessing import Pool
import ipdb
from functools import partial
from datetime import datetime
from hashlib import md5
from collections import Counter

import numpy as np
import pandas as pd
import librosa


pool = Pool(processes=16)

def current_time():
    print("current time: {}".format(str(datetime.now().time())))


def time_elapsed(start_time):
    elapsed_time = float(time.time()) - float(start_time)
    minutes = math.floor(elapsed_time / 60)
    seconds = elapsed_time % 60
    current_time()
    print("{} minutes and {} seconds".format(minutes, seconds))

def load_data(genres_list, music_path):
    time_elapsed(start_time)
    """Load audio buffer (data) for all songs for the specified genres

    Keyword arguments:
    genres_list -- list of genre names(str)
    music_path -- the path to the music(str)

    Notes:
    The file structure follows this form:
    music_path
    ----genre
    --------song

    Dictionary returned looks like:
    {
        'genre1': [[], []], # first list is X, second is y
        'genre2': [[], []] # first list is X, second is y
    }
    """
    # dictionary whose keys are genres and values are  a tuple, 0th index is array of songs, 1st index is array of labels
    genres_dict = {}
    # add the data for each genre to the dictionary
    for genre in genres_list:
        print('loading songs for:', genre, '...')

        audio_buffer_array_for_genre_list_of_lists = []
        all_movie_names_for_genre = []

        genres_path = os.path.join(music_path, genre, '*')
        # print('genres_path', genres_path)
        for movie_path in glob.glob(genres_path):
            movie_name = movie_path.split('/')[4]
            print('loading songs for:', movie_name, '...')
            movies_path = os.path.join(music_path, genre, movie_path, '*')
            # print('movie_path', movie_path)
            # print('movies_path', movies_path)

            hashed_movie_title = md5(movie_name).hexdigest()

            pickle_filename = '{}.npy'.format(hashed_movie_title)
            pickle_path = os.path.join(music_path, 'songs_pkl', pickle_filename)
            # print('pickled pickle_path:', pickle_path)
            if (os.path.isfile(pickle_path)):
                audio_buffer_array_for_movie, movie_names = np.load(pickle_path)
            else:
                all_songs_for_movie = glob.glob(movies_path)
                loaded_audio_for_movie = pool.map(librosa.load, all_songs_for_movie)
                audio_buffer_array_for_movie = np.array([loaded_audio[0] for loaded_audio in loaded_audio_for_movie])
                print ('movie_name', movie_name)
                print ('all_songs_for_movie', all_songs_for_movie)
                print ('len(all_songs_for_movie)', len(all_songs_for_movie))
                movie_names = [movie_name] * len(all_songs_for_movie)
                print ('movie_names', movie_names)
                all_movie_names_for_genre += movie_names
                print ('all_movie_names_for_genre', movie_names)
                print('pickling {} audio buffer data...'.format(movie_name))
                np.save(pickle_path, [audio_buffer_array_for_movie, movie_names])
                print('...finished pickling {} audio buffer data'.format(movie_name))

            audio_buffer_array_for_genre_list_of_lists.append(audio_buffer_array_for_movie)
            print('... finished loading songs for:', movie_name)

        audio_buffer_array_for_genre = np.concatenate(audio_buffer_array_for_genre_list_of_lists)

        genres_dict[genre] = [audio_buffer_array_for_genre]
        genres_dict[genre].append(np.array([genre] * len(audio_buffer_array_for_genre)))
        genres_dict[genre].append(all_movie_names_for_genre)
        print('... finished loading songs for:', genre)

    return genres_dict



if __name__ == '__main__':
    start_time = time.time()
    current_time()

    # user provided list of genres they want to load
    genres_list = ['family', 'horror', 'sci-fi']
    # genres_list = ['family', 'horror']
    # genres_list = ['family', 'sci-fi']
    print('genres of interest:')
    for genre in genres_list:
        print('    -', genre)


    # load dictionary whose keys are genres and values are a list, 0th index is array of songs, 1st index is array of labels
    print('loading audio files...')

    genres_dict = load_data(genres_list, '/data/music')
    time_elapsed(start_time)

    print('...finished loading audio files')

    # get X and y
    Xs = []
    ys = []
    all_movie_names_list_of_lists = []
    for genre_data in genres_dict.values():
        Xs.append(genre_data[0])
        ys.append(genre_data[1])
        all_movie_names_list_of_lists.append(genre_data[2])

    X = np.concatenate(Xs)
    y = np.concatenate(ys)
    all_movie_names = np.concatenate(all_movie_names_list_of_lists)

    print('X', X)
    print('y', y)
    print('all_movie_names', all_movie_names)

###############################
##### CALCULATE FEATURES #####
###############################

    df = pd.DataFrame(data={'genre': y, 'movie': all_movie_names})

    print('calculating spectral rolloff...')
    time_elapsed(start_time)
    pickle_filename = 'spectral_rolloffs_{}.npy'
    pickle_path_mean = os.path.join('/data/music/features_pkl', pickle_filename.format('mean'))
    pickle_path_std = os.path.join('/data/music/features_pkl', pickle_filename.format('std'))
    if (os.path.isfile(pickle_path_mean) and os.path.isfile(pickle_path_std) ):
        print('loading pickled data...')
        df['spectral_rolloffs_mean'] = np.load(pickle_path_mean)
        df['spectral_rolloffs_std'] = np.load(pickle_path_std)
        print('finished loading pickled data')
    else:
        spectral_rolloffs = pool.imap(librosa.feature.spectral_rolloff, X)
        spectral_rolloffs = list(spectral_rolloffs)
        df['spectral_rolloffs_mean'] = [spectral_rolloff.mean() for spectral_rolloff in spectral_rolloffs]
        df['spectral_rolloffs_std'] = [spectral_rolloff.std() for spectral_rolloff in spectral_rolloffs]
        np.save(pickle_path_mean, df['spectral_rolloffs_mean'])
        np.save(pickle_path_std, df['spectral_rolloffs_std'])
    # spectral_rolloffs = [librosa.feature.spectral_rolloff(x) for x in X]
    print('...finished calculating spectral rolloff')
    time_elapsed(start_time)

    print('calculating spectral centroids...')
    time_elapsed(start_time)
    pickle_filename = 'spectral_centroids_{}.npy'
    pickle_path_mean = os.path.join('/data/music/features_pkl', pickle_filename.format('mean'))
    pickle_path_std = os.path.join('/data/music/features_pkl', pickle_filename.format('std'))
    if (os.path.isfile(pickle_path_mean) and os.path.isfile(pickle_path_std) ):
        print('loading pickled data...')
        df['spectral_centroids_mean'] = np.load(pickle_path_mean)
        df['spectral_centroids_std'] = np.load(pickle_path_std)
        print('finished loading pickled data')
    else:
        spectral_centroids = pool.imap(librosa.feature.spectral_centroid, X)
        spectral_centroids = list(spectral_centroids)
        df['spectral_centroids_mean'] = [spectral_centroid.mean() for spectral_centroid in spectral_centroids]
        df['spectral_centroids_std'] = [spectral_centroid.std() for spectral_centroid in spectral_centroids]
        np.save(pickle_path_mean, df['spectral_centroids_mean'])
        np.save(pickle_path_std, df['spectral_centroids_std'])
    # spectral_centroids = [librosa.feature.spectral_centroid(x) for x in X]
    print('...finished calculating spectral centroids')
    time_elapsed(start_time)

    print('calculating zero-crossing rate...')
    time_elapsed(start_time)
    pickle_filename = 'zero_crossing_rates_{}.npy'
    pickle_path_mean = os.path.join('/data/music/features_pkl', pickle_filename.format('mean'))
    pickle_path_std = os.path.join('/data/music/features_pkl', pickle_filename.format('std'))
    if (os.path.isfile(pickle_path_mean) and os.path.isfile(pickle_path_std) ):
        print('loading pickled data...')
        df['zero_crossing_rates_mean'] = np.load(pickle_path_mean)
        df['zero_crossing_rates_std'] = np.load(pickle_path_std)
        print('finished loading pickled data')
    else:
        zero_crossing_rates = pool.imap(librosa.feature.zero_crossing_rate, X)
        zero_crossing_rates = list(zero_crossing_rates)
        df['zero_crossing_rates_mean'] = [zero_crossing_rate.mean() for zero_crossing_rate in zero_crossing_rates]
        df['zero_crossing_rates_std'] = [zero_crossing_rate.std() for zero_crossing_rate in zero_crossing_rates]
        np.save(pickle_path_mean, df['zero_crossing_rates_mean'])
        np.save(pickle_path_std, df['zero_crossing_rates_std'])
    # zero_crossing_rates = [librosa.feature.zero_crossing_rate(x) for x in X]
    print('...finished calculating zero-crossing rate')
    time_elapsed(start_time)

    print('calculating mfccs...')
    time_elapsed(start_time)

    pickle_filename = 'mfccs_{number}_{metric}.npy'
    pickle_path_mean_1 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=1, metric='mean'))
    pickle_path_std_1 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=1, metric='std'))
    pickle_path_mean_2 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=2, metric='mean'))
    pickle_path_std_2 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=2, metric='std'))
    pickle_path_mean_3 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=3, metric='mean'))
    pickle_path_std_3 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=3, metric='std'))
    pickle_path_mean_4 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=4, metric='mean'))
    pickle_path_std_4 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=4, metric='std'))
    pickle_path_mean_5 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=5, metric='mean'))
    pickle_path_std_5 = os.path.join('/data/music/features_pkl', pickle_filename.format(number=5, metric='std'))

    if (os.path.isfile(pickle_path_mean_1) and os.path.isfile(pickle_path_std_1) ):
        print('loading pickled data...')
        df['mfcc1_mean'] = np.load(pickle_path_mean_1)
        df['mfcc1_std'] = np.load(pickle_path_mean_1)
        df['mfcc2_mean'] = np.load(pickle_path_mean_2)
        df['mfcc2_std'] = np.load(pickle_path_mean_2)
        df['mfcc3_mean'] = np.load(pickle_path_mean_3)
        df['mfcc3_std'] = np.load(pickle_path_mean_3)
        df['mfcc4_mean'] = np.load(pickle_path_mean_4)
        df['mfcc4_std'] = np.load(pickle_path_mean_4)
        df['mfcc5_mean'] = np.load(pickle_path_mean_5)
        df['mfcc5_std'] = np.load(pickle_path_mean_5)
        print('finished loading pickled data')
    else:
        partial_mfcc = partial(librosa.feature.mfcc, n_mfcc=5)
        mfccs = pool.imap(partial_mfcc, X)
        mfccs = list(mfccs)
        # mfccs = [librosa.feature.mfcc(x, n_mfcc=5) for x in X]
        print('...finished calculating mfccs')
        print('calculating mfcc1...')
        mfcc1s = [mfcc[0] for mfcc in mfccs]
        df['mfcc1_mean'] = [mfcc1.mean() for mfcc1 in mfcc1s]
        df['mfcc1_std'] = [mfcc1.std() for mfcc1 in mfcc1s]
        print('...finished calculating mfcc1')
        print('calculating mfcc2...')
        mfcc2s = [mfcc[1] for mfcc in mfccs]
        df['mfcc2_mean'] = [mfcc2.mean() for mfcc2 in mfcc2s]
        df['mfcc2_std'] = [mfcc2.std() for mfcc2 in mfcc2s]
        print('...finished calculating mfcc2')
        print('calculating mfcc3...')
        mfcc3s = [mfcc[2] for mfcc in mfccs]
        df['mfcc3_mean'] = [mfcc3.mean() for mfcc3 in mfcc3s]
        df['mfcc3_std'] = [mfcc3.std() for mfcc3 in mfcc3s]
        print('...finished calculating mfcc3')
        print('calculating mfcc4...')
        mfcc4s = [mfcc[3] for mfcc in mfccs]
        df['mfcc4_mean'] = [mfcc4.mean() for mfcc4 in mfcc4s]
        df['mfcc4_std'] = [mfcc4.std() for mfcc4 in mfcc4s]
        print('...finished calculating mfcc4')
        print('calculating mfcc5...')
        mfcc5s = [mfcc[4] for mfcc in mfccs]
        df['mfcc5_mean'] = [mfcc5.mean() for mfcc5 in mfcc5s]
        df['mfcc5_std'] = [mfcc5.std() for mfcc5 in mfcc5s]
        print('...finished calculating mfcc5')

        np.save(pickle_path_mean_1, df['mfcc1_mean'])
        np.save(pickle_path_std_1, df['mfcc1_std'])
        np.save(pickle_path_mean_2, df['mfcc2_mean'])
        np.save(pickle_path_std_2, df['mfcc2_std'])
        np.save(pickle_path_mean_3, df['mfcc3_mean'])
        np.save(pickle_path_std_3, df['mfcc3_std'])
        np.save(pickle_path_mean_4, df['mfcc4_mean'])
        np.save(pickle_path_std_4, df['mfcc4_std'])
        np.save(pickle_path_mean_5, df['mfcc5_mean'])
        np.save(pickle_path_std_5, df['mfcc5_std'])

    print('...finished calculating mfccs')
    time_elapsed(start_time)


    print('PICKLING DATAFRAME...')
    time_elapsed(start_time)
    pickle_filename = 'df_music.pkl'
    pickle_path = os.path.join('/data/music', pickle_filename)
    df.to_pickle(pickle_path)
    print('...finished PICKLING DATAFRAME')


# Silla's feature vector

# TIMBRAL FEATURES

# RHYTHMIC FEATURES

# PITCH FEATU
