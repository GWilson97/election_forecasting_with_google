import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import io
import time
import tqdm


# Get electoral vote distribution for 2010-2020
url = "https://raw.githubusercontent.com/chris-taylor/USElection/master/data/electoral-college-votes.csv"
res = requests.get(url).content
electoral = pd.read_csv(io.StringIO(res.decode('utf-8')), header = None, names = ["state", "elec_votes"])

# Get polling data
polls = pd.read_csv("datasets/president_polls.csv")

# Create Pollster Ratings DataFrame from 538
url = "https://raw.githubusercontent.com/fivethirtyeight/data/master/pollster-ratings/pollster-ratings.csv"
res = requests.get(url).content
pollster_rating = pd.read_csv(io.StringIO(res.decode('utf-8')))

# Get historic voting trends for each state
votes_by_year = pd.read_csv("datasets/historic_voting.csv", index_col = "Unnamed: 0")

# Create a DataFrame denoting a win or loss in the state
url = "https://raw.githubusercontent.com/chris-taylor/USElection/master/data/electoral-college-votes.csv"
res = requests.get(url).content
electoral = pd.read_csv(io.StringIO(res.decode('utf-8')), header = None, names = ["state", "elec_votes"])

# Get Google Trends prediction data, weighted for recency
weighted_preds = pd.read_csv("datasets/weighted_preds.csv")


def weight_polls(polls):
    """
    Weight the polls on their recency and pollster rating
    given by FiveThirtyEight.
    
    Parameters:
    ===========
    polls : pandas dataframe, polls collected from FiveThirtyEight and
            split by the defined state_matchup function
    """
    # Create columns with the month and year of the polls
    month_array = []
    for i in range(len(polls["end_date"])):
        month_array.append(int(str(polls["end_date"][i])[5:7]))

    year_array = []
    for i in range(len(polls["end_date"])):
        year_array.append(int(str(polls["end_date"][i])[:4]))

    polls["month"] = pd.Series(month_array)
    polls["year"] = pd.Series(year_array)

    # Get the month and year of the most recent poll
    latest_poll = [polls["month"][0], polls["year"][0]]

    # Convert months and year into distance in months from most recent poll
    month_diff = []
    for i in range(polls.shape[0]):
        months_back = latest_poll[0] - polls["month"][i]
        years_back = latest_poll[1] - polls["year"][i]
        month_diff.append(months_back + (12 * years_back))

    polls["month_diff"] = pd.Series(month_diff)

    # Create a weighting column for recency of polling data
    polls["recency_weight"] = 1 / (polls["month_diff"] + 1)

    # Create a weighting column for quality of pollster: from FiveThirtyEight
    polls["pollster_weight"] = 1 / (polls["Predictive Plus-Minus"] + 2.0)

    # Create cumulative weighting column
    polls["poll_weight"] = polls["pollster_weight"] * polls["recency_weight"]

    # Create weighted polls columns
    polls["weighted_votes_dem"] = polls["poll_weight"] * polls["votes_dem"]
    polls["weighted_votes_rep"] = polls["poll_weight"] * polls["votes_rep"]
    
    return polls

# Create function to do all combos
def get_matchup(df,
                pollster_rating,
                candidate_x, candidate_y,
                cand_x_party, cand_y_party,
                level = "national",
                state = None):
    """
    Takes in a Pandas DataFrame of polls from FiveThirtyEight
    and candidate names and returns a combined DataFrame of
    the Candidate-1 vs. Candidate-2 poll results.
    
    Parameters:
    -----------
    df : pandas dataframe, polls from FiveThirtyEight
    pollster_rating : pandas dataframe, pollster organization weights
    candidate_x : str, Name of candidate
    candidate_y : str, Name of candidate
    cand_x_party : str, Party of candidate
    cand_y_party : str, Party of candidate
    level : str, "national", "state", or "all" state level polls
    state : str, default None, if "state" level is specified, which state to return
    """
    
    # Get relevant columns from the DataFrame
    cols = ["question_id",
            "poll_id",
            "stage",
            "office_type",
            "pollster",
            "state",
            "end_date",
            "candidate_name",
            "candidate_party",
            "sample_size",
            "pct"]
    df = df[cols]
    
    
    # Combine polling data with pollster ratings
    cols = ["Pollster",
            "Predictive Plus-Minus",
            "538 Grade"]
    df = df.merge(pollster_rating[cols],
                         how = "left",
                         left_on = "pollster",
                         right_on = "Pollster")
    # Find and keep only polls with Pollster Ratings
    df = df.loc[df["pollster"] == df["Pollster"], ]
    
    
    
    # Get polls where there is no specified state (i.e. National Polls)
    if level == "national": 
        df = df.loc[df["state"].isna()]
    # Get polls for a specific state
    elif level == "state":
        df = df.loc[df["state"] == state]
    elif level == "all":
        df = df.loc[df["state"].notna()]
        
    # Create separate DataFrames for each candidate
    dict_of_candidate_dfs = {}
    for candidate in df['candidate_name'].unique():
        c_df = df.loc[df['candidate_name'] == candidate, :]
        dict_of_candidate_dfs[candidate] = c_df
    
    # Get each DataFrame for each candidate, if they exist
    if candidate_x in df["candidate_name"].unique():
        cand_1 = dict_of_candidate_dfs[candidate_x]
    else:
        print("No polls have been collected for the specified race.")
        return
    
    if candidate_y in df["candidate_name"].unique():
        cand_2 = dict_of_candidate_dfs[candidate_y]
    else:
        print("No polls have been collected for the specified race.")
        return
    
    # Combine DataFrames
    pair = pd.merge(cand_1,
                    cand_2[["question_id", "candidate_name", "candidate_party", "pct"]],
                    on = "question_id",
                    suffixes = (f"_{cand_x_party}", f"_{cand_y_party}")).drop(["Pollster"], axis = 1)
    
    # Create column for votes for each candidate
    pair[f"votes_{cand_x_party}"] = (pair["sample_size"] * (pair[f"pct_{cand_x_party}"] / 100)).astype(int)
    pair[f"votes_{cand_y_party}"] = (pair["sample_size"] * (pair[f"pct_{cand_y_party}"] / 100)).astype(int)
    
    pair["total_decided"] = pair[f"votes_{cand_x_party}"] + pair[f"votes_{cand_y_party}"]
    
    # Convert End Date column to Datetime
    pair["end_date"] = pd.to_datetime(pair["end_date"])
    
    return pair


# Given a DataFrame of state poll results between two candidates, return a win/loss ratio for n simulations
def state_sim(state_df, weighted_preds, cand_x_party, cand_y_party, state, n = 100):
    """
    Takes in a dataframe of polling results for each state and
    weighted predictions from Google Search Trends by state.
    Returns the candidate ("x" or "y") that won n simulations
    of an election in the state.
    
    Parameters:
    -----------
    state_df : pandas dataframe, polls from FiveThirtyEight
    weighted_preds : pandas dataframe, predictions from Google Trends of state leaning
    n : int, number of Monte Carlo simulations run
    """
    c_x = sum(state_df[f"votes_{cand_x_party}"])
    c_y = sum(state_df[f"votes_{cand_y_party}"])
    total = c_x + c_y

    win_c_x = 0
    loss_c_x = 0
    
    gt_weight = weighted_preds.loc[weighted_preds["geoName"] == state, cand_x_party].values[0]

    for i in range(n):
        p = (0.95 * (c_x * np.random.normal(1, .20)) / total) + (0.05 * gt_weight)
        if p >= .50:
            win_c_x += 1
        else:
            loss_c_x += 1
            
    if win_c_x > loss_c_x:
        return cand_x_party
    else:
        return cand_y_party
    
    
def party_vote(df, party):
    """
    Account for party-faithful states and add the electoral votes
    to the total, given the stated party.
    
    Parameters:
    -----------
    df : pandas dataframe, electoral results for the simulated election
    party : str, "dem" or "rep" for Democratic or Republican candidate
    """
    if party == "dem":
        df["result"] = df["win"].map({"dem": 1, "rep": 0, 0: 0})
        df.loc[df["win_dem"] == 1, ["result"]] = 1
    elif party == "rep":
        df["result"] = df["win"].map({"dem": 0, "rep": 1, 0: 0})
        df.loc[df["win_rep"] == 1, ["result"]] = 1
    else:
        print("Invalid Party")
    
    return (df.loc[df["result"] == 1]["elec_votes"].sum(), df)


def election_sim(polls, pollster_rating, electoral, weighted_preds, cand_x, cand_y, cand_x_party, cand_y_party):
    """
    Simulate an election between candidates x and y.
    100 iterations and a standard deviation of .15 have been prespecified.
    
    Parameters:
    -----------
    polls : pandas dataframe, Polling data from FiveThirtyEight
    pollster_rating : pandas dataframe, pollster organization weights
    candidate_x : str, Name of candidate
    candidate_y : str, Name of candidate
    cand_x_party : str, Party of candidate
    cand_y_party : str, Party of candidate
    """
    
    # Get DataFrame of polling matchups
    match = get_matchup(polls, pollster_rating, cand_x, cand_y, cand_x_party, cand_y_party, "all")
    
    # Set empty columns for elecotral wins
    electoral["win"] = 0
    electoral["win_dem"] = 0
    electoral["win_rep"] = 0
    
    
    
    # States that consistently vote one party last 7 cycles: "predetermined"
    rep_states = []
    dem_states = []
    for i in votes_by_year:
        if sum(votes_by_year[i]) == 0:
            rep_states.append(i)
        elif sum(votes_by_year[i]) == 7:
            dem_states.append(i)
    
    
    
    # States that have been "predetermined"
    predet_states = dem_states + rep_states
    
    
    
    # Prepopulate columns with consistent states
    electoral.loc[electoral["state"].isin(rep_states), ["win_rep"]] = 1
    electoral.loc[electoral["state"].isin(dem_states), ["win_dem"]] = 1
    
    
    
    # States not "predetermined" that don't have polls
    missing_states = []
    for i in electoral["state"]:
        if i not in predet_states:
            if i not in match["state"].unique():
                missing_states.append(i)
                
                
                
    # Categorize states with missing polls as either Democrat or Republican leaning
    dem_lean = []
    rep_lean = []

    for i in missing_states:
        if votes_by_year[i].mean() > .500:
            dem_lean.append(i)
        else:
            rep_lean.append(i)
    
    
    
    # Classify leans as wins
    electoral.loc[electoral["state"].isin(dem_lean), ["win_dem"]] = 1
    electoral.loc[electoral["state"].isin(rep_lean), ["win_rep"]] = 1
    
    
    """
    Gets all states without predetermined values
    and assesses the polls to return whether the state 
    was won or lost. Adds the result to a dataframe.
    """
    for i in electoral.loc[(electoral["win_dem"] + electoral["win_rep"]) == 0]["state"].values:
        match_df = get_matchup(polls,
                               pollster_rating,
                               cand_x,
                               cand_y,
                               cand_x_party,
                               cand_y_party,
                               "state",
                               state = i)
        
        match_df = weight_polls(match_df)
        
        pred_result = state_sim(match_df, weighted_preds, cand_x_party, cand_y_party, state = i)
        electoral.loc[electoral["state"] == i, ["win"]] = pred_result
        
    
    tot_x, df_x = party_vote(electoral, cand_x_party)
    tot_y, df_y = party_vote(electoral, cand_y_party)
    
    
    return (tot_x, tot_y, df_x[["state", "result"]])


def mult_sim_election(polls, pollster_rating, electoral, weighted_preds, cand_x, cand_y, cand_x_party, cand_y_party, n = 1000):
    """
    Simulate n elections and return a choropleth with the
    state-by-state election results and labels with
    number of state wins for n elections.
    
    Parameters:
    -----------
    polls : pandas dataframe, Polling data from FiveThirtyEight
    pollster_rating : pandas dataframe, pollster organization weights
    cand_x : str, Name of candidate
    cand_y : str, Name of candidate
    cand_x_party : str, Party of candidate
    cand_y_party : str, Party of candidate
    n : int, number of iterations of the national election
    """
    tot_df = pd.DataFrame(index = range(0, 51), columns = ["state", "wins_y"])
    tot_df["wins_y"] = 0
    tot_df["state"] = votes_by_year.drop(columns = "year").columns
    
    national_win_x = 0
    national_win_y = 0
    national_draw = 0
    for i in tqdm.tqdm_notebook(range(0, n)):
        x, y, res_df = election_sim(polls,
                                    pollster_rating,
                                    electoral,
                                    weighted_preds,
                                    cand_x,
                                    cand_y,
                                    cand_x_party,
                                    cand_y_party)
        if x > y:
            national_win_x += 1
        elif y > x:
            national_win_y += 1
        elif x == y:
            national_draw += 1
        else:
            print("Invalid case.")

        for i, state in enumerate(res_df["state"]):
            state_res = res_df["result"][i]
            tot_df.loc[tot_df["state"] == state, "wins_y"] += state_res
            

    print("")
    print("==============================================")
    cand_x_prob = round(float(national_win_x / n), 4)
    cand_y_prob = round(float(national_win_y / n), 4)
    draw_prob = round(float(national_draw / n), 4)
    
    print(f"Of {n} simulations, {cand_x} wins {round((cand_x_prob * 100), 4)}% of cases.")
    print(f"Of {n} simulations, {cand_y} wins {round((cand_y_prob * 100), 4)}% of cases.")
    print(f"Of {n} simulations, draws occur in {round((draw_prob * 100), 4)}% of cases.")
    
    
    
    # Create columns for candidate Y
    tot_df["wins_x"] = abs(tot_df["wins_y"] - 1000)
    tot_df["perc_x"] = tot_df["wins_x"] / 1000
    tot_df["perc_y"] = tot_df["wins_y"] / 1000

    # State abbreviations retrieved from: http://worldpopulationreview.com/states/state-abbreviations/
    shorts = pd.read_csv("datasets/state_shorts.csv")
    tot_df = pd.merge(tot_df, shorts, left_on = "state", right_on = "State")
    
    
    # Adapted from code found at: https://plot.ly/python/choropleth-maps/
    for col in tot_df.columns:
        tot_df[col] = tot_df[col].astype(str)
    
    if cand_x_party == "rep":
        party = True
    else:
        party = False
    
    tot_df["popup"] = tot_df["state"] + "<br>" + \
        cand_x + " " + tot_df["wins_x"] + "<br>" + \
        cand_y + " " + tot_df["wins_y"]

    fig = go.Figure(data=go.Choropleth(
        locations = tot_df["Code"],
        text = tot_df["popup"],
        z = tot_df["perc_x"].astype(float),
        locationmode = "USA-states",
        autocolorscale = False,
        colorscale = [[0, "rgb(200, 10, 30)"], [0.5, "rgb(255, 255, 255)"], [1, "rgb(1, 51, 100)"]],
        reversescale = party,
        marker_line_color = "white",
        colorbar_title = "Wins Distribution",
        hoverinfo = "text"
    ))

    fig.update_layout(
        title_text = f"2020 {cand_x} vs. {cand_y} Simulation Results<br>(Hover for breakdown)",
        geo = dict(
            scope = "usa",
            projection = go.layout.geo.Projection(type = "albers usa"),
            showlakes = False,
            bgcolor = "lightslategray"
        ),
    )

    fig.show()
    
    
    return tot_df

