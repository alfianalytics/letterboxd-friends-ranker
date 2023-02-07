from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import streamlit as st

DOMAIN = "https://letterboxd.com"

def transform_ratings(some_str):
    """
    transforms raw star rating into float value
    :param: some_str: actual star rating
    :rtype: returns the float representation of the given star(s)
    """
    stars = {
        "★": 1,
        "★★": 2,
        "★★★": 3,
        "★★★★": 4,
        "★★★★★": 5,
        "½": 0.5,
        "★½": 1.5,
        "★★½": 2.5,
        "★★★½": 3.5,
        "★★★★½": 4.5
    }
    try:
        return stars[some_str]
    except:
        return -1

def scrape_films(username):
    movies_dict = {}
    movies_dict['id'] = []
    movies_dict['title'] = []
    movies_dict['rating'] = []
    movies_dict['liked'] = []
    movies_dict['link'] = []
    url = DOMAIN + "/" + username + "/films/"
    url_page = requests.get(url)
    if url_page.status_code != 200:
        encounter_error("")
    soup = BeautifulSoup(url_page.content, 'html.parser')
    
    # check number of pages
    li_pagination = soup.findAll("li", {"class": "paginate-page"})
    if len(li_pagination) == 0:
        ul = soup.find("ul", {"class": "poster-list"})
        if (ul != None):
            movies = ul.find_all("li")
            for movie in movies:
                movies_dict['id'].append(movie.find('div')['data-film-id'])
                movies_dict['title'].append(movie.find('img')['alt'])
                movies_dict['rating'].append(transform_ratings(movie.find('p', {"class": "poster-viewingdata"}).get_text().strip()))
                movies_dict['liked'].append(movie.find('span', {'class': 'like'})!=None)
                movies_dict['link'].append(movie.find('div')['data-target-link'])
    else:
        for i in range(len(li_pagination)):
            url = DOMAIN + "/" + username + "/films/page/" + str(i+1)
            url_page = requests.get(url)
            if url_page.status_code != 200:
                encounter_error("")
            soup = BeautifulSoup(url_page.content, 'html.parser')
            ul = soup.find("ul", {"class": "poster-list"})
            if (ul != None):
                movies = ul.find_all("li")
                for movie in movies:
                    movies_dict['id'].append(movie.find('div')['data-film-id'])
                    movies_dict['title'].append(movie.find('img')['alt'])
                    movies_dict['rating'].append(transform_ratings(movie.find('p', {"class": "poster-viewingdata"}).get_text().strip()))
                    movies_dict['liked'].append(movie.find('span', {'class': 'like'})!=None)
                    movies_dict['link'].append(movie.find('div')['data-target-link'])
    
    df_film = pd.DataFrame(movies_dict)    
    return df_film

def score_index(rating_x, liked_x, rating_y, liked_y):
    score = 0.0
    if ((rating_x == rating_y) & (liked_x == liked_y)):
        score = 2.0
    # both like but different ratings
    elif ((liked_x == True) & (liked_x == liked_y)):
        score = 2.0-(abs(rating_x-rating_y)/5)
    else:
        score = 1.0-(abs(rating_x-rating_y)/5)
    return score

def compare_ratings_friends(username_a, df_a, username_b, df_b):
    
    # movies they both liked
    df_liked = pd.merge(df_a[['id', 'title', 'link', 'liked']], df_b[['id', 'liked']])
    df_liked = df_liked[df_liked['liked']==True].reset_index(drop=True)
    
    # movies they gave same rate
    df_same = pd.merge(df_a[['id', 'title', 'rating']], df_b[['id', 'rating']])
    
    # movies they gave different rate
    df_different = pd.merge(df_a[['id', 'title', 'rating']], df_b[['id', 'rating']], how='inner', on='id')
    df_different = df_different[df_different['rating_x']!=df_different['rating_y']].reset_index(drop=True)
    df_different['difference'] = df_different['rating_x']-df_different['rating_y']
    df_different['difference_abs'] = abs(df_different['rating_x']-df_different['rating_y'])
    df_different = df_different.rename(columns={'rating_x': 'rating_{0}'.format(username_a), 'rating_y': 'rating_{0}'.format(username_b)})
    
    # calculate index
    df_merge = pd.merge(df_a, df_b, on = ['id', 'title'])
    if len(df_merge) > 0:
        df_merge['score'] = df_merge.apply(lambda row: score_index(row['rating_x'], row['liked_x'],
                                                                   row['rating_y'], row['liked_y']),
                                           axis = 1)
        index = df_merge['score'].sum()/(2*len(df_merge))
    else:
        index = 0
    return df_liked, df_same, df_different, index

def list_friends(username, ftype='following'):
    friends_list = []
    with st.spinner("scraping your friends list"):
        if ((ftype == 'following') | (ftype == 'followers')):
            url = DOMAIN + "/" + username + "/{0}/".format(ftype)
            while True:
                url_page = requests.get(url)
                soup = BeautifulSoup(url_page.content, 'html.parser')
                friends = soup.findAll('div', {'class':'person-summary'})

                for friend in friends:
                    username_b = friend.find('a', {'class':'avatar'})['href'].replace('/','')
                    friends_list.append(username_b)

                # check if there's next page
                if soup.find('a', {'class':'next'}) is None:
                    break
                else:
                    url = DOMAIN + soup.find('a', {'class':'next'})['href']
        elif (ftype == 'both'):
            url = DOMAIN + "/" + username + "/following/"
            while True:
                url_page = requests.get(url)
                soup = BeautifulSoup(url_page.content, 'html.parser')
                friends = soup.findAll('div', {'class':'person-summary'})

                for friend in friends:
                    username_b = friend.find('a', {'class':'avatar'})['href'].replace('/','')
                    friends_list.append(username_b)

                # check if there's next page
                if soup.find('a', {'class':'next'}) is None:
                    break
                else:
                    url = DOMAIN + soup.find('a', {'class':'next'})['href']
            url = DOMAIN + "/" + username + "/followers/"
            while True:
                url_page = requests.get(url)
                soup = BeautifulSoup(url_page.content, 'html.parser')
                friends = soup.findAll('div', {'class':'person-summary'})

                for friend in friends:
                    username_b = friend.find('a', {'class':'avatar'})['href'].replace('/','')
                    friends_list.append(username_b)

                # check if there's next page
                if soup.find('a', {'class':'next'}) is None:
                    break
                else:
                    url = DOMAIN + soup.find('a', {'class':'next'})['href']
            friends_list = list(dict.fromkeys(friends_list))
        elif (ftype == 'mutual'):
            following_list = []
            url = DOMAIN + "/" + username + "/following/"
            while True:
                url_page = requests.get(url)
                soup = BeautifulSoup(url_page.content, 'html.parser')
                friends = soup.findAll('div', {'class':'person-summary'})

                for friend in friends:
                    username_b = friend.find('a', {'class':'avatar'})['href'].replace('/','')
                    following_list.append(username_b)

                # check if there's next page
                if soup.find('a', {'class':'next'}) is None:
                    break
                else:
                    url = DOMAIN + soup.find('a', {'class':'next'})['href']
            followers_list = []
            url = DOMAIN + "/" + username + "/followers/"
            while True:
                url_page = requests.get(url)
                soup = BeautifulSoup(url_page.content, 'html.parser')
                friends = soup.findAll('div', {'class':'person-summary'})

                for friend in friends:
                    username_b = friend.find('a', {'class':'avatar'})['href'].replace('/','')
                    followers_list.append(username_b)

                # check if there's next page
                if soup.find('a', {'class':'next'}) is None:
                    break
                else:
                    url = DOMAIN + soup.find('a', {'class':'next'})['href']
            for following in following_list:
                if following in followers_list:
                    friends_list.append(following)
    return friends_list

def scrape_friends(username, friends_list, limit=20):
    with st.spinner('scraping your movies'):
        df_a = scrape_films(username)
        df_a = df_a[df_a['rating']!=-1].reset_index(drop=True)
    
    friends_dict = {}
    friends_dict['username'] = []
    friends_dict['index_score'] = []
    friends_dict['no_of_movies'] = []
    
    friends_data = {}
    progress = 0
    bar = st.progress(progress)
    for username_b in friends_list:
        progress = progress+1
        print('scraping for '+username_b)
        with st.spinner('scraping movies for '+username_b):
            df_b = scrape_films(username_b)
            df_b = df_b[df_b['rating']!=-1].reset_index(drop=True)
        bar.progress(progress/len(friends_list))
        no_of_movies = len(pd.merge(df_a[['id']], df_b[['id']]))
        if no_of_movies >= limit:
            friends_dict['username'].append(username_b)
            print('comparing for '+username_b)
            df_liked, df_same, df_different, index = compare_ratings_friends(username, df_a, username_b, df_b)
            friends_dict['index_score'].append(index)
            friends_dict['no_of_movies'].append(no_of_movies)
            friends_data[username_b] = {}
            friends_data[username_b]['df_b'] = df_b
            friends_data[username_b]['df_liked'] = df_liked
            friends_data[username_b]['df_same'] = df_same
            friends_data[username_b]['df_different'] = df_different

    df_friends = pd.DataFrame(friends_dict)
    df_friends['total_index'] = df_friends['index_score']*df_friends['no_of_movies']
    return df_friends, friends_data, df_a

def recommend_movies(df_friends, friends_data, df_a):
    df_movies = pd.DataFrame()
    for i in friends_data.keys():
        df_friend_movies = friends_data[i]['df_b'].copy()
        df_friend_movies['friends_score'] = df_friends[df_friends['username'] == i]['total_index'].values[0]
        df_movies = pd.concat([df_movies, df_friend_movies])
        
    df_no_of_rate = pd.DataFrame(df_movies.id.value_counts()).reset_index()
    df_no_of_rate.rename({'index':'id', 'id':'no_of_rate'}, axis='columns', inplace=True)
    
    df_recom = df_movies.groupby(['id', 'title', 'link']).agg({'rating':'mean', 'liked':'sum', 'friends_score':'mean'})
    df_recom = df_recom.reset_index()
    df_recom = pd.merge(df_recom, df_no_of_rate)
    
    df_recom = pd.merge(df_recom, df_a[['id']], how="outer", indicator=True)
    df_recom = df_recom[df_recom['_merge'] == 'left_only']
    del df_recom['_merge']
    
    #df_recom['index'] = df_recom['rating']*3/5+df_recom['liked']/df_recom['no_of_rate']*6.5+4*df_recom['friends_score']/df_recom['friends_score'].max()+6.5*df_recom['no_of_rate']/df_recom['no_of_rate'].max()
#     df_recom['index'] = df_recom['rating']*df_recom['friends_score']+df_recom['liked']*df_recom['no_of_rate']
    r_w = 6
    l_w = 3
    fs_w = 2
    nor_w = 0
    df_recom['index'] = r_w/5*df_recom['rating']+l_w*df_recom['liked']/df_recom['liked'].max()+fs_w*df_recom['friends_score']/df_recom['friends_score'].max()+nor_w*df_recom['no_of_rate']/df_recom['no_of_rate'].max()
    return df_recom