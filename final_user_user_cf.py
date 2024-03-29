# -*- coding: utf-8 -*-
"""Final User-User CF.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XSamS-mlx0PbkElhKkQXeXyJnLwqqeJE
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import pairwise_distances
from sklearn.metrics import precision_score, recall_score, f1_score, mean_squared_error, mean_absolute_error
from math import sqrt

from google.colab import drive
drive.mount('/content/drive')

movies_df = pd.read_csv('/content/drive/MyDrive/4-2project/movies.csv')
ratings_df = pd.read_csv('/content/drive/MyDrive/4-2project/ratings.csv')

movies_df.head()

ratings_df.head()

ratings_df = ratings_df.drop('timestamp', 1)
ratings_df.head()

def get_input_user_ratings_table(user_id):

    # Filter the dataframe to get ratings for the specified user ID
    user_ratings_df = ratings_df[ratings_df['userId'] == user_id]

    # Create a table of movies and their ratings for the user
    user_ratings_table = user_ratings_df[['movieId', 'rating']]

    return user_ratings_table

inputMovies = get_input_user_ratings_table(1)
inputMovies

#Filtering out users that have watched movies that the input active user has watched
userSubset = ratings_df[ratings_df['movieId'].isin(inputMovies['movieId'].tolist())]
userSubset.head()

user_id = 1
userSubset = userSubset[userSubset['userId'] != user_id]
userSubset

#Groupby creates several sub dataframes grouped by userid
userSubsetGroup = userSubset.groupby(['userId'])

userSubsetGroup.get_group(10)

#Sorting it so users with movie most in common with the input will have priority
#Sort these groups so the users that share the most movies in common with the input active user have higher priority
userSubsetGroup = sorted(userSubsetGroup,  key=lambda x: len(x[1]), reverse=True)

userSubsetGroup

#Top most user
userSubsetGroup[0]

#name of top user group
userSubsetGroup[0][0]

#dataframe of top user group
userSubsetGroup[0][1]

#Store the Pearson Correlation in a dictionary, where the key is the user Id and the value is the coefficient
pearsonCorrelationDict = {}

#For every user group in our subset
for name, group in userSubsetGroup:

    # Sort the user's movie ratings by movie ID
    group = group.sort_values(by='movieId')

    # Get the input active user's ratings for the movies that the current user has also rated
    inputMovies = inputMovies.sort_values(by='movieId')

    # N = Total similar movies watched
    nRatings = len(group)

    # The movies that they both have in common with active user ratings
    temp_df = inputMovies[inputMovies['movieId'].isin(group['movieId'].tolist())]

    #Store the ratings in temp_df in a list
    tempRatingList = temp_df['rating'].tolist()

    #Store the ratings of current user
    tempGroupList = group['rating'].tolist()

    #Now let's calculate the pearson correlation between two users, so called, x and y

    Sxx = sum([i**2 for i in tempRatingList]) - pow(sum(tempRatingList),2)/float(nRatings)
    Syy = sum([i**2 for i in tempGroupList]) - pow(sum(tempGroupList),2)/float(nRatings)
    Sxy = sum( i*j for i, j in zip(tempRatingList, tempGroupList)) - sum(tempRatingList)*sum(tempGroupList)/float(nRatings)

    if Sxx != 0 and Syy != 0:
        pearsonCorrelationDict[name] = Sxy/np.sqrt(Sxx*Syy)
    else:
        pearsonCorrelationDict[name] = 0

pearsonCorrelationDict.items()

pearsonDF = pd.DataFrame.from_dict(pearsonCorrelationDict, orient='index')
pearsonDF.head()

pearsonDF.columns = ['similarityIndex']
pearsonDF['userId'] = pearsonDF.index
pearsonDF.index = range(len(pearsonDF))
pearsonDF.head()

topUsers = pearsonDF.sort_values(by='similarityIndex', ascending=False)[0:50]
topUsers.head()

topUsersRating = topUsers.merge(ratings_df, left_on='userId', right_on='userId', how='inner')
topUsersRating.head()

#Multiplies the similarity by the user's ratings
topUsersRating['weightedRating'] = topUsersRating['similarityIndex']*topUsersRating['rating']
topUsersRating.head()

#Calculate sum similarity index and sum weighted rating
tempTopUsersRating = topUsersRating.groupby('movieId').sum()[['similarityIndex','weightedRating']]
tempTopUsersRating.columns = ['sum_similarityIndex','sum_weightedRating']
tempTopUsersRating.head()

recommendation_df = pd.DataFrame()
#Now we take the weighted average
recommendation_df['weighted average recommendation score'] = tempTopUsersRating['sum_weightedRating']/tempTopUsersRating['sum_similarityIndex']
recommendation_df['movieId'] = tempTopUsersRating.index
recommendation_df.head()

#Sort the values based on weighted average recommendation score
recommendation_df = recommendation_df.sort_values(by='weighted average recommendation score', ascending=False)
recommendation_df.head()

final_recommendations = movies_df.loc[movies_df['movieId'].isin(recommendation_df.head(10)['movieId'].tolist())]
final_recommendations

RecommendedMovies = final_recommendations['title'].tolist()
RecommendedMovies

import numpy as np
from sklearn.model_selection import KFold
from sklearn.metrics import average_precision_score, accuracy_score


# Split data into training and testing sets using KFold cross-validation
def split_data(data, n_splits=5):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    for train_indices, test_indices in kf.split(data):
        train_data = data[train_indices]
        test_data = data[test_indices]
        yield train_data, test_data


# Define the evaluation function
def evaluate(model, data):
    """
    Evaluate a model on hit rate, coverage, diversity, novelty, and user satisfaction.
    """
    # Calculate hit rate
    hits = 0
    for user, actual_items in data.items():
        predicted_items = model.predict(user)
        for item in predicted_items:
            if item in actual_items:
                hits += 1
    hit_rate = hits / len(data)

    # Calculate coverage
    all_items = set()
    for user, items in data.items():
        all_items.update(items)
    recommended_items = set(model.recommend_all())
    coverage = len(recommended_items) / len(all_items)

    # Calculate diversity
    similarities = []
    for item1 in recommended_items:
        for item2 in recommended_items:
            if item1 != item2:
                similarity = model.similarity(item1, item2)
                similarities.append(similarity)
    diversity = 1 - np.mean(similarities)

    # Calculate novelty
    item_popularity = model.item_popularity()
    novelty = 0
    for user, recommended_items in model.recommendations.items():
        for item in recommended_items:
            novelty += -np.log(item_popularity[item])
    novelty /= len(model.recommendations)

    # Calculate mean average precision
    y_true = []
    y_scores = []
    for user, actual_items in data.items():
        predicted_items = model.predict(user)
        y_true.append([1 if item in actual_items else 0 for item in predicted_items])
        y_scores.append([model.predict_score(user, item) for item in predicted_items])
    map_score = average_precision_score(np.array(y_true), np.array(y_scores), average='macro')

    # Calculate accuracy
    y_true = []
    y_pred = []
    for user, actual_items in data.items():
        predicted_items = model.predict(user)
        y_true += [1 if item in actual_items else 0 for item in predicted_items]
        y_pred += [1 if item in predicted_items else 0 for item in actual_items]
    accuracy = accuracy_score(y_true, y_pred)

    # Calculate user satisfaction
    user_satisfaction = model.user_satisfaction()

    return {
        'hit_rate': hit_rate,
        'coverage': coverage,
        'diversity': diversity,
        'novelty': novelty,
        'map': map_score,
        'accuracy': accuracy,
        'user_satisfaction': user_satisfaction,
    }