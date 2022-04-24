from datetime import datetime
from tqdm import tqdm
import pandas as pd
import numpy as np
import warnings
import os


def name(mlbam):
    '''
    map mlb ids to name
    '''
    try:
        return lookup.loc[mlbam]['name']
    except:
        return mlbam

def getCountWeights(df):
    '''
    group ball-strike counts and find csw z-scores for each
    '''
    csw_mean = df['csw'].mean()
    csw_std = df['csw'].std()
    
    count_weights = df.groupby('count').agg(csw_score=('csw', lambda x: (csw_mean - (sum(x) / len(x))) / csw_std))
    count_weights['weight'] = round(1+count_weights['csw_score'], 2)
    return count_weights

def weightCount(count):
    '''
    map count to weighted value
    '''
    return weights.loc[count]['weight']


if __name__ == '__main__':
    warnings.filterwarnings('ignore')

    while True:
        year = input("Enter a year from 2015 to present: ")
        try:
            year = int(year)
        except ValueError:
            print('Not a valid year')
            continue
        if 2015 <= year <= datetime.now().year:
            break
        else:
            print('Not a valid year')

    # initialize progress bar
    pbar = tqdm(total=70)

    while True:
        # get player id data and read into a pandas dataframe
        url = "https://raw.githubusercontent.com/chadwickbureau/register/master/data/people.csv"
        lookup = pd.read_csv(url, index_col="key_mlbam")
        lookup['name'] = lookup['name_first'] + ' ' + lookup['name_last']
        pbar.update(10)

        # locate savant data and read into pandas dataframe
        dir = os.path.abspath(f'../baseball_savant/data/savant_{year}.csv')
        df = pd.read_csv(dir)
        pbar.update(10)

        # data cleanup
        df['csw'] = np.where(df['description'].isin(['swinging_strike', 'swinging_strike_blocked', 'called_strike', 'foul_tip']), 1, 0)
        df['count'] = df['balls'].astype(str) + '-' + df['strikes'].astype(str)
        df = df.loc[df['count'] != '4-2']     # for some reason there's a 4-2 count
        pbar.update(10)

        # get csw weights by count
        weights = getCountWeights(df)
        pbar.update(10)

        # group batters by count and get total wcsw
        df = df.groupby(['pitcher', 'count']).agg(total_pitches=('at_bat_number', 'count'), total_csw=('csw', 'sum')).reset_index()
        df['wCSW'] = df['count'].map(weightCount) * df['total_csw']
        pbar.update(10)
        
        # group batters again to get wcsw rate
        df = df.groupby('pitcher').agg({'total_pitches': 'sum', 'wCSW': 'sum'})
        df['wCSW'] = df['wCSW'] / df['total_pitches']
        df.index = df.index.map(name)
        pbar.update(10)

        # make directory to house savant data
        if not os.path.exists('data'):
            os.mkdir('data')

        df.to_csv(f"data/wCSW_{year}.csv")
        pbar.update(10)

        break