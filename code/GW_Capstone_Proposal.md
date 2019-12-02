# Capstone

### Topics

- Identifies which of the three proposals you outlined in your lightning talk you have chosen
- Articulates the main goal of your project (your problem statement)
- Outlines your proposed methods and models
- Defines the risks & assumptions of your data
- Revises initial goals & success criteria, as needed
- Documents your data source
- Performs & summarizes preliminary EDA of your data

### Proposal

Create a forecasting model using Monte Carlo simulations to test the effect of polling and political google searches on predicting the winner of an election. 

Polling data will be collected from top polling organizations and weighted with [FiveThirtyEight's Pollster Rankings](https://projects.fivethirtyeight.com/pollster-ratings/). Without a current Democratic nominee for the 2020 Presidential Race, current polling examines "most-likely" candidates against the incumbent. Polls will be collected for each of these instances as well as availbale "typical-Democrat" polls.

Political Google Search data will be collected by using a corpus of Democratic and Republican Party Platforms from 1948 to 2016 retrieved from [Comparative Agendas Project](https://www.comparativeagendas.net/datasets_codebooks). A Natural Language Processing Model will compare the tokenized platforms of each party per election cycle to predict whether a state will vote Democratic or Republican by examining the popularity of each party's platform on a state-by-state basis in Google Trends.

This project seeks to both utilize conventional polling techniques as a measure of prediction for electoral success while acknowledging the common failures of electoral polling that were highlighted in 2016 by including regional/statewide Google search trends as indicators of political leaning.

### Risks and Assumptions

An issue specific to polling data is that there is no electoral fraud and that reported polling perfectly reflects the preferences of voters of the state.

The Google Trend data will assume that searches for political party platforms will be more popular in states that agree with what the party has to say and therefore more likely to vote for the party's nominee. This is used to guage the likelihood that a specific state will break for X party's candidate.

### Data Sources

Political Party Platforms:
[Comparative Agendas Project](https://www.comparativeagendas.net/datasets_codebooks)
- [Topic Codes](https://www.comparativeagendas.net/pages/master-codebook)

Pollster Rankings:
[FiveThirtyEight's Pollster Rankings](https://projects.fivethirtyeight.com/pollster-ratings/)

Presidential Election Polls:
[FiveThirtyEight Polls: Presidential](https://projects.fivethirtyeight.com/polls/president-general/)

Democratic Primary Polls:
[FiveThirtyEight Polls: Democratic Primary](https://projects.fivethirtyeight.com/polls/president-primary-d/)

Google Trends:
[Google Trends Home Page](https://trends.google.com/trends/?geo=US)