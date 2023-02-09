import streamlit as st
import numpy as np
import pandas as pd
import pickle
from deployment import scrape_friends, list_friends, recommend_movies, DOMAIN
from pathlib import Path
from datetime import date

current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
css_file = current_dir / "styles" / "main.css"
st.set_page_config(page_icon="📽️", page_title="Letterboxd Analysis", layout='wide')
with open(css_file) as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

# sections = ['Prediksi MBTI', 'Eksplorasi Data', 'Performa Model']
# selected_sect = st.sidebar.selectbox('Silakan pilih', sections)

st.title('📽️ Letterboxd Friends Ranker (+ Movie Recommendations)')
st.write("See which friend has the most similar taste in movies to yours based on the ratings and likes of the movies you both have watched 🍿")
with st.expander("ℹ️ What will this app do?"):
    st.markdown("""
    - Scrape your rated movies
    - Scrape your friends
    - Scrape your friends' rated movies
    - Compute similarity between you and each of your friend
    - Rank the similarity score
    - Make movie recommendations based on your friends' movies
    ⚠️ Note: It takes approximately 10 seconds to scrape 400 movies from one Letterboxd profile,
    so if you have many friends and they have watched many movies, it will take some minutes to process.
    """)

row0 = st.columns(3)
with row0[0]:
    username = st.text_input('Letterboxd Username')
with row0[1]:
    ftype = st.selectbox('Friends Category', options=['following', 'followers', 'both', 'mutual'])
with row0[2]:
    limit = st.slider('Minimum Movies You Both Have Rated', 1, 100, 20)

row_button = st.columns((6,1,1,6))
submit = row_button[1].button('Submit')
reset = row_button[2].button('Reset')
result = False

if submit:
    result = True

if reset:
    result = False

if result:
    today = date.today()
    filename = "{0}_{1}_{2}_{3}".format(str(today), username, ftype, str(limit))
    df_log = pd.read_csv("log.csv")
    df_found = df_log[(df_log['date'] == str(today)) & (df_log['username'] == username) & (df_log['ftype'] == ftype) & (df_log['limit'] == limit)].reset_index(drop=True)
    if len(df_found) != 1:
        # scraping process
        friends_list = list_friends(username, ftype)
        st.write("You have {0} friends to scrape".format(len(friends_list)))
        df_friends, friends_data, df_a = scrape_friends(username, friends_list, limit)
        df_friends = df_friends.sort_values('total_index', ascending=False).reset_index(drop=True)

        # export file
        df_friends.to_pickle('log/{0}_dff.pickle'.format(filename))
        df_a.to_pickle('log/{0}_dfa.pickle'.format(filename))
        with open('log/{0}_fdd.pickle'.format(filename), 'wb') as f:
            pickle.dump(friends_data, f)
        with open('log/{0}_fl.pickle'.format(filename), 'wb') as f:
            pickle.dump(friends_list, f)
        
        # add new log
        new_row = {'date':str(today), 'username':username, 'ftype':ftype, 'limit':limit}
        df_log = df_log.append(new_row, ignore_index=True)
        df_log.to_csv('log.csv', index=False)
    else:
        st.write("We already have scraped your data today")
        with open('log/{0}_fl.pickle'.format(filename), 'rb') as f:
            friends_list = pickle.load(f)
        df_a = pd.read_pickle('log/{0}_dfa.pickle'.format(filename))
        df_friends = pd.read_pickle('log/{0}_dff.pickle'.format(filename))
        df_friends = df_friends.sort_values('total_index', ascending=False).reset_index(drop=True)
        with open('log/{0}_fdd.pickle'.format(filename), 'rb') as f:
            friends_data = pickle.load(f)

    st.write("---")
    if (len(df_friends) <= 5):
        st.header("🤝 Your Top {0} Friends".format(len(df_friends)))
        row_friends = st.columns(len(df_friends))
        for i, friend in enumerate(df_friends['username']):
            url = DOMAIN + '/{0}/'.format(friend)
            row_friends[i].subheader("{0}. [{1}]({2})".format(i+1, friend, url))
            row_friends[i].write("✅ {0} movies you both have rated".format(df_friends[df_friends['username'] == friend]['no_of_movies'].values[0]))
            row_friends[i].write("❤️ {0} movies you both like".format(len(friends_data[friend]['df_liked'])))
            if len(friends_data[friend]['df_liked']) > 0:
                liked = row_friends[i].expander(label='Common Liked Movies')
                with liked:
                    for j, movie in enumerate(friends_data[friend]['df_liked']['title']):
                        url = DOMAIN + friends_data[friend]['df_liked']['link'].values[j]
                        st.write("{0}. [{1}]({2})".format(j+1, movie, url))
            row_friends[i].write("⭐ {0} points ratings difference on average".format(round(friends_data[friend]['df_different']['difference_abs'].mean(), 2)))
    else:
        row_friends = {}
        n_top = 10
        if (len(df_friends) < 10):
            st.header("🤝 Your Top {0} Friends".format(len(df_friends)))
        else:
            st.header("🤝 Your Top {0} Friends".format(n_top))
        for n_row in range(int(n_top/5)):
            row_friends[n_row] = st.columns(5)
        for i, friend in enumerate(df_friends['username']):
            if (i>=n_top):
                break
            url = DOMAIN + '/{0}/'.format(friend)
            row = int(i/5)
            col = i%5
            row_friends[row][col].subheader("{0}. [{1}]({2})".format(i+1, friend, url))
            row_friends[row][col].write("✅ {0} movies you both have rated".format(df_friends[df_friends['username'] == friend]['no_of_movies'].values[0]))
            row_friends[row][col].write("❤️ {0} movies you both like".format(len(friends_data[friend]['df_liked'])))
            if len(friends_data[friend]['df_liked']) > 0:
                liked = row_friends[row][col].expander(label='Common Liked Movies')
                with liked:
                    for j, movie in enumerate(friends_data[friend]['df_liked']['title']):
                        url = DOMAIN + friends_data[friend]['df_liked']['link'].values[j]
                        st.write("{0}. [{1}]({2})".format(j+1, movie, url))
            row_friends[row][col].write("⭐ {0} points ratings difference on average".format(round(friends_data[friend]['df_different']['difference_abs'].mean(), 2)))

    with st.expander("Full List"):
        for i, friend in enumerate(df_friends['username']):
            url = DOMAIN + '/{0}/'.format(friend)
            st.markdown("{0}. [{1}]({2}) - ✏️ Score: **{3}** with **{4}\%** 🎯 Similarity".format(i+1,
                                                                                    friend,
                                                                                    url,
                                                                                    round(df_friends[df_friends['username']==friend]['total_index'].values[0],2),
                                                                                    round(df_friends[df_friends['username']==friend]['index_score'].values[0]*100, 1)))
        st.markdown("""🎯 **Similarity** is percentage of how similar your ratings and likes between you both,
        while ✏️ **Score** is 🎯 Similarity times 🎞️ Number of Movies You Both Have Rated""")
    
    st.write("---")
    # Recommendation
    df_recom = recommend_movies(df_friends, friends_data, df_a)
    df_recom = df_recom.sort_values('index', ascending=False).reset_index(drop=True)
    st.header("🗒️ Your Top 10 Movies to Watch")
    row_movies = {}
    for i, movie in enumerate(df_recom['title']):
        if (i>=10):
            break
        row = int(i/2)
        if (i%2!=1):
            row_movies[row] = st.columns(2)
        col = i%2
        url = DOMAIN + df_recom['link'].values[i]
        row_movies[row][col].subheader("[{0}]({1})".format(movie, url))
        row_movies[row][col].markdown("""
        ✅ Rated by: {0} | ❤️ Liked by: {1} | ⭐ Friends' ratings: {2}
        """.format(int(df_recom['no_of_rate'].values[i]),
                   int(df_recom['liked'].values[i]),
                   round(df_recom['rating'].values[i], 2)))
    with st.expander("Full Data"):
        st.dataframe(df_recom) 


   
    # for i, friend in enumerate(df_friends['username']):
    #     if (i>=10):
    #         break
    #     url = DOMAIN + '/{0}/'.format(friend)
    #     st.subheader("{0}. [{1}]({2})".format(i+1, friend, url))
    #     st.write("{0} movies you both have rated".format(df_friends[df_friends['username'] == friend]['no_of_movies'].values[0]))
    #     st.write("{0} movies you both liked".format(len(friends_data[friend]['df_liked'])))
    #     if len(friends_data[friend]['df_liked']) > 0:
    #         liked = st.expander(label='Common Liked Movies')
    #         with liked:
    #             for i, movie in enumerate(friends_data[friend]['df_liked']['title']):
    #                 url = DOMAIN + friends_data[friend]['df_liked']['link'].values[i]
    #                 st.write("{0}. [{1}]({2})".format(i+1, movie, url))
    #     st.write("{0} points ratings difference on average".format(round(friends_data[friend]['df_different']['difference_abs'].mean(), 2)))
    
    # st.dataframe(df_friends.sort_values('total_index', ascending=False).reset_index(drop=True))