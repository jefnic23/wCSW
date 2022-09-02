from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from tqdm import tqdm
import pandas as pd
import numpy as np
import warnings
import os


def createEngine():
    load_dotenv()
    USER = os.getenv('USER')
    PSWD = os.getenv('PSWD')
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    NAME = os.getenv('NAME')
    return create_engine(f'postgresql://{USER}:{PSWD}@{HOST}:{PORT}/{NAME}')


def getCountWeights(df):
    '''group ball-strike counts and find csw z-scores for each'''

    csw_mean = df['csw'].mean()
    csw_std = df['csw'].std()
    count_weights = df.groupby('count').agg(csw_score=('csw', lambda x: (csw_mean - (sum(x) / len(x))) / csw_std))
    count_weights['weight'] = round(1+count_weights['csw_score'], 2)
    return count_weights


def main():
    warnings.filterwarnings('ignore')

    # initialize overall progress bar
    pbar = tqdm(total=3, position=0, desc="Overall")

    # make directory to house savant data
    if not os.path.exists('data'):
        os.mkdir('data')

    # select necessary columns from database only
    columns = [
        'game_year',
        'player_name',
        'description',
        'balls',
        'strikes',
        'at_bat_number'
    ]

    # get savant data from postgres and read into pandas dataframe
    engine = createEngine()
    df = pd.read_sql('baseball_savant', engine, columns=columns)
    pbar.update(1)

    # data cleanup
    df['csw'] = np.where(df['description'].isin([
        'swinging_strike', 
        'swinging_strike_blocked', 
        'called_strike', 
        'foul_tip', 
        'missed_bunt', 
        'bunt_foul_tip', 
        'swinging_pitchout'
    ]), 1, 0)
    df['count'] = df['balls'].astype(str) + '-' + df['strikes'].astype(str)
    df = df.loc[df['count'] != '4-2']     # for some reason there's a 4-2 count
    pbar.update(1)

    # map count to weighted value
    def weightCount(count):
        return weights.loc[count]['weight']

    # create .xlsx file
    with pd.ExcelWriter('data/wES_leaderboards.xlsx') as writer:
        for year in tqdm(range(df['game_year'].min(), df['game_year'].max()+1), position=1, desc='Leaderboards'):
            # filter df by season
            df_year = df[df['game_year'] == year]

            # get csw weights by count
            weights = getCountWeights(df_year)

            # group pitchers by count and get total wES
            df_year = df_year.groupby(['player_name', 'count']).agg(total_pitches=('at_bat_number', 'count'), total_csw=('csw', 'sum')).reset_index()
            df_year['wES'] = df_year['count'].map(weightCount) * df_year['total_csw']
            
            # group pitchers again to get wES rate
            df_year = df_year.groupby(['player_name']).agg({'total_pitches': 'sum', 'wES': 'sum'})
            df_year['wES'] = df_year['wES'] / df_year['total_pitches']

            df_year.to_excel(writer, sheet_name=str(year))
    pbar.update(1)

    return print("Leaderboards saved to data directory.")


if __name__ == '__main__':
    main()
