# File with helper functions

# Standard Libraries
import numpy as np
import pandas as pd

# StatsBombPy
from statsbombpy import sb

# Plots
import matplotlib.pyplot as plt

# For Pitch
from mplsoccer.pitch import Pitch

# Networkx
import networkx as nx

# ------------------------------------------------------------------------------------
# Functions

# Function for creating network Graph from passes using Networkx library
def create_graph(passes):
    # Changing df to tupple
    passes = passes[['pass_maker', 'pass_receiver', 'total_passes']]
    passes_tupple = passes.apply(tuple, axis=1).tolist()

    # Creating Graph
    G = nx.DiGraph()

    for i in range(len(passes_tupple)):
        G.add_edge(passes_tupple[i][0], passes_tupple[i][1], weight = passes_tupple[i][2])

    return G


# Function to get and to plot match passes for one team for one match
def get_match_passes_by_team(match_passes, team, players, team2, team_position, show_legend=False, show_pitch=False):
    # Get passes for team
    match_passes_team = match_passes[match_passes['team'] == team]
    match_passes_team = match_passes_team[match_passes_team['type'] == 'Pass']

    # Get pass maker and pass receiver players
    match_passes_team['pass_maker'] = match_passes_team['player']
    match_passes_team['pass_receiver'] = match_passes_team['player'].shift(-1)

    match_passes_team = match_passes_team[match_passes_team['pass_outcome'].isnull() == True].reset_index()

    # Take only passes from the normal game time - First and Second halfs
    match_end_df = match_passes.query('type == "Half End"').sort_values(by=['minute', 'second'])
    last_minute = match_end_df.iloc[2]['minute']
    match_passes_team = match_passes_team[(match_passes_team['minute'] <= last_minute)]

    # Get Location for each pass in separate df
    location = match_passes_team['location']
    location_df = pd.DataFrame(location.to_list(), columns=['location_x', 'location_y'])
    location_end = match_passes_team['pass_end_location']
    location_end_df = pd.DataFrame(location_end.to_list(), columns=['pass_end_location_x', 'pass_end_location_y'])

    # Get separate x and y locations for pass location and end location
    match_passes_team['location_x'] = location_df['location_x']
    match_passes_team['location_y'] = location_df['location_y']
    match_passes_team['pass_end_location_x'] = location_end_df['pass_end_location_x']
    match_passes_team['pass_end_location_y'] = location_end_df['pass_end_location_y']

    # Prepare final passes data for one player
    match_passes_team['pass_outcome'] = match_passes_team['pass_outcome'].fillna('Successful')
    match_passes_team = match_passes_team[['index', 'minute', 'second', 'team', 'type', 'pass_outcome', 'player', 'pass_maker', 'pass_receiver', 'location_x', 'location_y', 'pass_end_location_x', 'pass_end_location_y', 'pass_outcome']]

    # Get average location of players based on documentation
    av_locaction = match_passes_team.groupby('pass_maker').agg({'location_x':['mean'], 'location_y':['mean', 'count']})
    av_locaction.columns = ['location_x', 'location_y', 'count']

    # Number of passes for each player to each player
    passes = match_passes_team.groupby(['pass_maker', 'pass_receiver']).index.count().reset_index()
    passes.rename(columns = {'index':'total_passes'}, inplace = True)

    # Merge average location and number of passes
    passes = passes.merge(av_locaction, left_on = 'pass_maker', right_index = True)
    passes = passes.merge(av_locaction, left_on = 'pass_receiver', right_index = True, suffixes = ['', '_receipt'])
    passes.rename(columns = {'pass_maker_x_receipt':'pass_end_location_x', 'pass_maker_y_receipt':'pass_end_location_y', 'count_receipt':'total_passes_received'}, inplace = True)
    passes = passes[passes['pass_maker'] != passes['pass_receiver']].reset_index()

    # Replace player names
    passes_new = passes.replace({"pass_maker": players, "pass_receiver": players})

    if show_pitch:
        # Plot using Pitch
        pitch = Pitch(pitch_color='grass', goal_type = 'box', line_color='white')
        fig, ax = pitch.draw()

        # Normal team position on the Pitch
        if team_position == 0:
            arrows = pitch.arrows(passes.location_x, passes.location_y,
                                    passes.location_x_receipt, passes.location_y_receipt, lw = 5,
                                    color = 'black', zorder = 1, ax = ax)
            nodes = pitch.scatter(av_locaction.location_x, av_locaction.location_y,
                                    s=300, color = 'white', edgecolors='black', ax = ax)
            # Get start 11 players and plot them:
            players_legend = []
            for index, row in av_locaction.iterrows():
                pitch.annotate(players[row.name], xy=(row.location_x, row.location_y), c ='black', va = 'center', ha = 'center', size = 10, ax = ax)
                players_legend.append(f"{players[row.name]} - {index}")
        else:
            # Reverse team on the Pitch
            arrows = pitch.arrows(120 - passes.location_x, passes.location_y,
                                    120 - passes.location_x_receipt, passes.location_y_receipt, lw = 5,
                                    color = 'black', zorder = 1, ax = ax)
            nodes = pitch.scatter(120 - av_locaction.location_x, av_locaction.location_y,
                                    s=300, color = 'blue', edgecolors='black', ax = ax)

            # Get start 11 players and plot them:
            players_legend = []
            for index, row in av_locaction.iterrows():
                pitch.annotate(players[row.name], xy=(120 - row.location_x, row.location_y), c ='black', va = 'center', ha = 'center', size = 10, ax = ax)
                players_legend.append(f"{players[row.name]} - {index}")

        if show_legend:
            plt.legend(players_legend,
                handlelength=0,
                handleheight=0,
                prop={'size': 6},
                title='Players',
                labels=players_legend,
                loc='upper center', bbox_to_anchor=(0.5, 0),
                ncol=2)

        plt.title(f"Pass network for {team} at match againts {team2}")
        plt.show()

    # Return passes list to use with Networkx
    return passes_new


# Function to get players names and jersey number from one match
def get_players_names(match_id, team):
    lineup_team = sb.lineups(match_id=match_id)[team]

    # Get only informations about player name and jersey number and save it to dict
    players_team = dict(zip(lineup_team['player_name'], lineup_team['jersey_number']))

    return players_team


# Function to show informations and to plot passes for one player on one match
def plot_passes_for_player(match, player):
    # Find passes for one player
    player_passes = match[match['player'] == player]
    player_passes = player_passes[player_passes['type'] == 'Pass'].reset_index()

    print('Passes for player:', player)
    # Different player passes
    print('Different passes:', player_passes.pass_outcome.unique()) # Nan is a successful pass by documentation

    # Get Location for each pass in separate df
    player_location = player_passes['location']
    player_location_df = pd.DataFrame(player_location.to_list(), columns=['location_x', 'location_y'])
    player_location_end = player_passes['pass_end_location']
    player_location_end_df = pd.DataFrame(player_location_end.to_list(), columns=['pass_end_location_x', 'pass_end_location_y'])

    # Get separate x and y locations for pass location and end location
    player_passes['location_x'] = player_location_df['location_x']
    player_passes['location_y'] = player_location_df['location_y']
    player_passes['pass_end_location_x'] = player_location_end_df['pass_end_location_x']
    player_passes['pass_end_location_y'] = player_location_end_df['pass_end_location_y']

    # Prepare final passes data for one player
    player_passes['pass_outcome'] = player_passes['pass_outcome'].fillna('Successful')

    # See percentage of passes for this player
    print(player_passes['pass_outcome'].value_counts(normalize=True).mul(100))

    player_passes = player_passes[['minute', 'location_x', 'location_y', 'pass_end_location_x', 'pass_end_location_y', 'pass_outcome']]

    # Show passes for one player on Pitch
    pitch = Pitch(pitch_color = 'grass', line_color = 'white', goal_type = 'box')
    fig, ax = pitch.draw()

    for i in range(len(player_passes)):
        # White arrows represents successful passes
        if player_passes.pass_outcome[i] == 'Successful':
            pitch.arrows(player_passes.location_x[i], player_passes.location_y[i], player_passes.pass_end_location_x[i], player_passes.pass_end_location_y[i], ax=ax, color='white', width = 3)
            pitch.scatter(player_passes.location_x[i], player_passes.location_y[i], ax = ax, color = 'white')
        # Red arrows are bad passes
        else:
            pitch.arrows(player_passes.location_x[i], player_passes.location_y[i], player_passes.pass_end_location_x[i], player_passes.pass_end_location_y[i], ax=ax, color='red', width=3)
            pitch.scatter(player_passes.location_x[i], player_passes.location_y[i], ax = ax, color='red')

    ax.legend(['Successful passes', 'Unsuccessful passes'],
           handlelength=0,
           title='Legend',
           labels=['Successful passes', 'Unsuccessful passes'],
           labelcolor=["white", "red"])
    plt.title(player)
    plt.show()