import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, accuracy_score
from sklearn.preprocessing import LabelEncoder

def load_data():
    pickle_filename = 'df_music.pkl'
    pickle_path = os.path.join('/data/music', pickle_filename)
    df = pd.read_pickle(pickle_path)
    return df

def filter_genres(df, genres):
    return df[df['genre'].isin(genres)]

def run_model(Model, X_train, X_test, y_train, y_test):
    name = Model.__name__
    print('###########################################')
    print('fitting {}...'.format(name))
    clf = Model()
    clf.fit(X_train, y_train)
    print('...finished fitting {}'.format(name))
    y_predict = clf.predict(X_test)
    print(1, "accuracy score:", clf.score(X_test, y_test))

    print("confusion matrix:")
    print(confusion_matrix(y_test, y_predict))

    le = LabelEncoder()
    le.fit(y_train)
    le_y_test = le.transform(y_test)
    le_y_predict = le.transform(y_predict)

    print("accuracy score:", accuracy_score(le_y_test, le_y_predict))

    print("precision:", precision_score(le_y_test, le_y_predict, average=None))

    print("recall:", recall_score(le_y_test, le_y_predict, average=None))

    if name == 'RandomForestClassifier':
        print('RandomForestClassifier feature importance', clf.feature_importances_)

def cross_validate(Model, X, y, cv=5):
    name = Model.__name__
    print('starting cross validation for {}, k=5...'.format(name))
    clf = Model()
    scores = cross_val_score(clf, X, y, cv=cv, n_jobs=-1)
    print('...finished cross validation for {}, k=5'.format(name))
    print('cross validation scores:', scores)
    print('average of cross validation scores:', scores.mean())

def EnsembleVote(clf, songs):
    predictions = clf.predict(songs)
    predictions_counter = Counter(predictions)
    most_common = predictions_counter.most_common()
    results = []
    highest_count = 0
    for value, count in most_common:
        if highest_count >= count:
            highest_count = count
            results.append(value)
    return results

#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################

if __name__ == '__main__':
    genres = ['family', 'horror']
    df = load_data()
    df = filter_genres(df, genres)

    # shuffle rows for cross-validation
    df = df.sample(frac=1)

    y = df.pop('genre').values
    del df['movie']
    X = df.values

    # np.stack([a,b,c], axis=1)

    # split into train and test set
    X_train, X_test, y_train, y_test = train_test_split(X, y)

    models = [RandomForestClassifier, GaussianNB]

    for Model in models:
        run_model(Model, X_train, X_test, y_train, y_test)
        cross_validate(Model, X, y, cv=5)
