from bs4 import BeautifulSoup
# import requests
import cloudscraper
import pandas as pd
import numpy as np
import streamlit as st

DOMAIN = "https://letterboxd.com"
scraper = cloudscraper.create_scraper()

@st.cache_data
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

@st.cache_data
def scrape_films(username):
    print("==== SCRAPING FOR USERNAME {} ====".format(username))
    movies_dict = {}
    movies_dict['id'] = []
    movies_dict['title'] = []
    movies_dict['rating'] = []
    movies_dict['liked'] = []
    movies_dict['link'] = []
    url = DOMAIN + "/" + username + "/films/"
    url_page = scraper.get(url)
    if url_page.status_code != 200:
        st.error("Error")
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
        for i in range(int(li_pagination[-1].find('a').get_text().strip())):
            url = DOMAIN + "/" + username + "/films/page/" + str(i+1)
            url_page = scraper.get(url)
            if url_page.status_code != 200:
                st.error("Error")
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

@st.cache_data
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

@st.cache_data
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

@st.cache_data
def list_friends(username, ftype='following'):
    friends_list = []
    with st.spinner("scraping your friends list"):
        if ((ftype == 'following') | (ftype == 'followers')):
            url = DOMAIN + "/" + username + "/{0}/".format(ftype)
            while True:
                url_page = scraper.get(url)
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
                url_page = scraper.get(url)
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
                url_page = scraper.get(url)
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
                url_page = scraper.get(url)
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
                url_page = scraper.get(url)
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

@st.cache_data
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
        print('scraping for '+username_b + ', ({})'.format(username))
        with st.spinner('scraping movies for '+username_b):
            df_b = scrape_films(username_b)
            df_b = df_b[df_b['rating']!=-1].reset_index(drop=True)
        bar.progress(progress/len(friends_list))
        no_of_movies = len(pd.merge(df_a[['id']], df_b[['id']]))
        if no_of_movies >= limit:
            friends_dict['username'].append(username_b)
            print('comparing {} with {}'.format(username, username_b))
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

@st.cache_data
def recommend_movies(df_friends, friends_data, df_a):
    df_movies = pd.DataFrame()
    for i in friends_data.keys():
        df_friend_movies = friends_data[i]['df_b'].copy()
        df_friend_movies['friends_score'] = df_friends[df_friends['username'] == i]['total_index'].values[0]
        df_movies = pd.concat([df_movies, df_friend_movies])
        
    df_no_of_rate = pd.DataFrame(df_movies.id.value_counts()).reset_index()
    # df_no_of_rate.rename({'index':'id', 'id':'no_of_rate'}, axis='columns', inplace=True)
    df_no_of_rate.rename({'count':'no_of_rate'}, axis='columns', inplace=True)
    
    df_recom = df_movies.groupby(['id', 'title', 'link']).agg({'rating':'mean', 'liked':'sum', 'friends_score':'mean'})
    df_recom = df_recom.reset_index()
    df_recom = pd.merge(df_recom, df_no_of_rate, left_on='id', right_on='id')
    
    df_recom = pd.merge(df_recom, df_a[['id']], how="outer", left_on='id', right_on='id', indicator=True)
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

@st.cache_data
def decade_year(year):
    return str(int(year/10)*10)+"s"

@st.cache_data
def classify_popularity(watched_by):
    if (watched_by <= 10000):
        return "1 - very obscure"
    elif (watched_by <= 100000):
        return "2 - obscure"
    elif (watched_by <= 1000000):
        return "3 - popular"
    else:
        return "4 - very popular"

@st.cache_data
def classify_likeability(ltw_ratio):
    if (ltw_ratio <= 0.1):
        return "1 - rarely likeable"
    elif (ltw_ratio <= 0.2):
        return "2 - sometimes likeable"
    elif (ltw_ratio <= 0.4):
        return "3 - often likeable"
    else:
        return "4 - usually likeable"

@st.cache_data
def classify_runtime(runtime):
    if (pd.isnull(runtime)!=True):
        if (runtime < 30):
            return "less than 30m"
        elif (runtime < 60):
            return "30m-1h"
        elif (runtime < 90):
            return "1h-1h 30m"
        elif (runtime < 120):
            return "1h 30m-2h"
        elif (runtime < 150):
            return "2h-2h 30m"
        elif (runtime < 180):
            return "2h 30m-3h"
        else:
            return "at least 3h"
    else:
        return np.nan

@st.cache_data
def scrape_films_details(df_film, username):
    df_film = df_film[df_film['rating']!=-1].reset_index(drop=True)
    movies_rating = {}
    movies_rating['id'] = []
    movies_rating['avg_rating'] = []
    movies_rating['year'] = []
    movies_rating['watched_by'] = []
    movies_rating['liked_by'] = []
    movies_rating['runtime'] = []
    
    movies_actor = {}
    movies_actor['id'] = []
    movies_actor['actor'] = []
    movies_actor['actor_link'] = []
    
    movies_director = {}
    movies_director['id'] = []
    movies_director['director'] = []
    movies_director['director_link'] = []
    
    movies_genre = {}
    movies_genre['id'] = []
    movies_genre['genre'] = []

    movies_theme = {}
    movies_theme['id'] = []
    movies_theme['theme'] = []
    progress = 0
    bar = st.progress(progress)
    for link in df_film['link']:
        progress = progress+1
        print('scraping details of {} [{}]'.format(df_film[df_film['link'] == link]['title'].values[0], username))
        
        with st.spinner('scraping details of '+df_film[df_film['link'] == link]['title'].values[0]):
            id_movie = df_film[df_film['link'] == link]['id'].values[0]
            url_movie = DOMAIN + link
            url_movie_page = scraper.get(url_movie)
            if url_movie_page.status_code != 200:
                st.error("Error")
            soup_movie = BeautifulSoup(url_movie_page.content, 'html.parser')
            for sc in soup_movie.findAll("script"):
                if sc.string != None:
                    if "ratingValue" in sc.string:
                        rating = sc.string.split("ratingValue")[1].split(",")[0][2:]
                    # if "releaseYear" in sc.string:
                    #     year = sc.string.split("releaseYear")[1].split(",")[0][2:].replace('"','')
                    if "startDate" in sc.string:
                        year = sc.string.split("startDate")[1].split(",")[0][3:7]
            url_stats = DOMAIN + "/csi" + link + "stats"
            url_stats_page = scraper.get(url_stats)
            soup_stats = BeautifulSoup(url_stats_page.content, 'html.parser')
            watched_by = int(soup_stats.findAll('a')[0]['title'].replace(u'\xa0', u' ').split(" ")[2].replace(u',', u''))
            liked_by = int(soup_stats.findAll('a')[2]['title'].replace(u'\xa0', u' ').split(" ")[2].replace(u',', u''))
            try:
                runtime = int(soup_movie.find('p',{'class':'text-link text-footer'}).get_text().strip().split('\xa0')[0])
            except:
                runtime = np.nan
            movies_rating['id'].append(id_movie)
            movies_rating['avg_rating'].append(rating)
            movies_rating['year'].append(year)
            movies_rating['watched_by'].append(watched_by)
            movies_rating['liked_by'].append(liked_by)
            movies_rating['runtime'].append(runtime)

            # finding the actors
            if (soup_movie.find('div', {'class':'cast-list'}) != None):
                for actor in soup_movie.find('div', {'class':'cast-list'}).findAll('a'):
                    if actor.get_text().strip() != 'Show All…':
                        movies_actor['id'].append(id_movie)
                        movies_actor['actor'].append(actor.get_text().strip())
                        movies_actor['actor_link'].append(actor['href'])

            # finding the directors
            if (soup_movie.find('div', {'id':'tab-crew'}) != None):
                for director in soup_movie.find('div', {'id':'tab-crew'}).find('div').findAll('a'):
                    movies_director['id'].append(id_movie)
                    movies_director['director'].append(director.get_text().strip())
                    movies_director['director_link'].append(director['href'])

            # finding the genres
            if (soup_movie.find('div', {'id':'tab-genres'}) != None):
                for genre in soup_movie.find('div', {'id':'tab-genres'}).find('div').findAll('a'):
                    movies_genre['id'].append(id_movie)
                    movies_genre['genre'].append(genre.get_text().strip())
            
            # finding the themes
            if (soup_movie.find('div', {'id':'tab-genres'}) != None):
                if ('Themes' in str(soup_movie.find('div', {'id':'tab-genres'}))):
                    for theme in soup_movie.find('div', {'id':'tab-genres'}).findAll('div')[1].findAll('a'):
                        if theme.get_text().strip() != 'Show All…':
                            movies_theme['id'].append(id_movie)
                            movies_theme['theme'].append(theme.get_text().strip())

        bar.progress(progress/len(df_film))
    df_rating = pd.DataFrame(movies_rating)
    df_rating['decade'] = df_rating.apply(lambda row: decade_year(int(row['year'])), axis=1)
    df_actor = pd.DataFrame(movies_actor)
    df_director = pd.DataFrame(movies_director)
    df_genre = pd.DataFrame(movies_genre)
    df_theme = pd.DataFrame(movies_theme)
    return df_rating, df_actor, df_director, df_genre, df_theme
