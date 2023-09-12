import networkx as nx
from collections import Counter
import pandas as pd
import statsbombpy as sb

#these numbers should not be in the range between 0 and 99 as those 
#are valid jersy numbers for the football players
SHOT = 100
GOAL = 101
BAD_PASS = -1

def get_players_names(match_id, team):
    lineup_team = sb.lineups(match_id=match_id)[team]
    
    players_team = dict(zip(lineup_team['player_name'], (lineup_team['jersey_number'])))

    return players_team

def create_graph(passes,player_jersy):
    '''Creats the Multidigraph from the given pd.Dataframe
    if the reciveing player is not found the pass receiver is 
    set to be -1'''
    
    nodes = []
    for player in passes.player.unique():
        nodes.append(player_jersy[player])
        
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(nodes)
    
    temp_edges = []
    for ind in passes.index:
        sender = player_jersy[passes.loc[ind]['player']]
        
        if passes.loc[ind]['pass_recipient'] in player_jersy.keys():
            reciver = player_jersy[passes.loc[ind]['pass_recipient']]
        else:
            reciver = -1
        temp_edges.append((sender,reciver))
    
    graph.add_edges_from(temp_edges)
    
    return graph
    
def graphs_g_b(match_events, player_jersy, team):
    '''Returns multidigraph for successful passes, and for unsuccessful passes
    The nodes are set to the jersy number of a given player'''
    
    all_passes = match_events.query(f'type == "Pass" and team == "{team.capitalize()}"')[['minute',
                                                                                            'second',
                                                                                            'player', 
                                                                                            'pass_recipient',  
                                                                                            'pass_outcome']]
    
    all_passes = all_passes.sort_values(by=['minute', 'second']).reset_index().drop('index', axis = 1)
    
    successful_passes = all_passes[all_passes.pass_outcome.isnull()]
    unsuccessful_passes = all_passes[~all_passes.pass_outcome.isnull()]
    
    successful_graph = create_graph(successful_passes, player_jersy)
    unsuccessful_graph = create_graph(unsuccessful_passes, player_jersy)
    
    return successful_graph, unsuccessful_graph

def timestamp_to_int(timestamp):
    '''Turns a string of format hh:mm:ss.sss to a int that represents seconds'''
    timestamp = timestamp.split(':')
    return int(timestamp[0])*60*60 + int(timestamp[1])*60 + int(timestamp[2].split('.')[0])

def seconds_played(match_events, team):
    '''For each player calculates how many saconds he has spent on the pitch'''
    
    half_time = match_events[(match_events.team == team.capitalize())
                                 & (match_events.type == 'Half End')]
    
    halfs_duration = []
    for ind in half_time.index:
        timestamp = half_time.loc[ind]['timestamp']
        halfs_duration.append(timestamp_to_int(timestamp))
        
        
    substitutions = match_events[(match_events.team == team.capitalize())
                                 & (match_events.type == 'Substitution')]
    
    players = match_events[(match_events.team == team.capitalize()) &
                          (~match_events.player.isnull()) &
                          (match_events.type == 'Pass')].player.unique()
    
    player_time = dict()
    for player in players:
        player_time[player] = halfs_duration[0] + halfs_duration[1]
        
    for ind in substitutions.index:
        relative_time_of_sub = timestamp_to_int(substitutions.loc[ind]['timestamp'])
        coming_out = substitutions.loc[ind]['player']
        coming_in = substitutions.loc[ind]['substitution_replacement']
        
        if abs(substitutions.loc[ind]['minute'] - relative_time_of_sub/60) > 2:
            player_time[coming_out] = player_time[coming_out] - halfs_duration[1] + relative_time_of_sub
            player_time[coming_in] = halfs_duration[1] - relative_time_of_sub
        else:
            player_time[coming_out] = relative_time_of_sub
            player_time[coming_in] = player_time[coming_in] - relative_time_of_sub
    
    return player_time

def pass_lengths(match_events, team):
    '''For each player finds the lengths of passes he has made and puts it in a list'''

    all_successful_passes = match_events[(match_events.team == team.capitalize()) &
                                         (match_events.type == 'Pass') &
                                         (match_events.pass_outcome.isnull())]
    
    passes = dict()
    players = all_successful_passes.player.unique()
    for player in players:
        passes[player] = []

    for ind in all_successful_passes.index:
        player = all_successful_passes.loc[ind]['player']
        passes[player].append(all_successful_passes.loc[ind]['pass_length'])
        
    return passes
    
def pass_seq(match_events, team, player_jersy):
    '''For the whole match finds the sequence of passes and shots 
    the passes that are not successful are marked with BAD_PASS
    shots are marked with #SHOT and goals with #GOAL'''

    relevant = match_events[(match_events.type =='Pass') | (match_events.type =='Shot')].sort_values(by=['minute','second'])
    relevant = relevant[relevant.team == team.capitalize()].reset_index().drop('index',axis = 1)
    
    good_passes = relevant.pass_outcome.isnull()

    seq = []
    
    for ind in relevant.index:
        if relevant.loc[ind].type == 'Shot':
            if relevant.loc[ind].shot_outcome == 'Goal':
                seq.append(GOAL)
            else:
                seq.append(SHOT)
        elif good_passes[ind]:
            seq.append(player_jersy[relevant.loc[ind]['player']])
        else:
            seq.append(BAD_PASS)
    return seq

def seq2str(seq):
    '''the list of intigers turn into the strin of
    format |int|int|int...'''

    temp_str = str()
    for i in seq:
        temp_str += f'|{i}'

    return temp_str

def find_pattern(seq, min_len = 3, max_len = 10):
    '''Finds how many time a subsequence of a given length repeats itself
    in the whole sequence. It stops once it reach the max_length that is given
    or the maximum repetition of a subsequences of given length is 1 '''

    result = dict()
    
    for length in range(min_len,max_len + 1):
        n_grams = []
        for start in range(len(seq) - length):
            current_seq = seq[start:start+length]
            if BAD_PASS in current_seq:
                if current_seq.count(BAD_PASS) == 1 and current_seq[-1] == BAD_PASS:
                    n_grams.append(seq2str(current_seq))
            else:
                n_grams.append(seq2str(current_seq))
        n_grams = dict(Counter(n_grams))
        
        if max(n_grams.values()) == 1:
            break
        
        temp = []
        for s, f in n_grams.items():
            if f == 1:
                continue
            if len(temp) > 5:
                break
            temp.append(([int(i) for i in s.split('|')[1:]],f))
            
        result[length] = sorted(temp, key = lambda x: -x[1])
        
    return result

def shot_seq(seq, min_length = 3):
    '''Finds the subsequence between BAD_PASS and SHOT/GOAL
    with the min_lenght of a subsequence given by min_length '''
    shot_seq = []
    start = 0
    for i in range(len(seq)):
        if seq[i] == BAD_PASS:
            start = i
        elif (seq[i] == SHOT or seq[i] == GOAL) and start:
            if len(seq[start+1:i+1]) > min_length:
                shot_seq.append(seq[start+1:i+1])
            start = None
    return shot_seq