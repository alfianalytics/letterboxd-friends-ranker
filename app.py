import streamlit as st
from htbuilder import div, big, h2, styles, p
from htbuilder.units import rem
import altair as alt
import plotly.express as px
import numpy as np
import pandas as pd
import pickle
from deployment import scrape_films_details, scrape_films, scrape_friends, list_friends, recommend_movies, DOMAIN
from pathlib import Path
from datetime import date

current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
css_file = current_dir / "styles" / "main.css"
st.set_page_config(page_icon="📽️", page_title="Letterboxd Analysis", layout='wide')
with open(css_file) as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

sections = ['Analyze Profile', 'Compare 2 Profile', 'Friends Ranker + Movie Recommendations']
selected_sect = st.sidebar.selectbox('Choose mode', sections)

if selected_sect == sections[0]:
    st.title('📽️ Letterboxd Profile Analyzer')
    st.write("See how you rate your movies, what movies you like, the genres, the actors and directors of those movies 🍿")
    with st.expander("ℹ️ What will this app do?"):
        st.markdown("""
        - Scrape your rated movies
        - Scrape your rated movies' details (year, average ratings, genre, actor, director)
        - Analyze and visualize those movies
        ⚠️ Note: It takes approximately 10 seconds to scrape 400 movies from one Letterboxd profile,
        so if you have many friends and they have watched many movies, it will take some minutes to process.
        """)
    username = st.text_input('Letterboxd Username')
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
        filename = "{0}_{1}".format(str(today), username)
        df_log = pd.read_csv("log_detail.csv")
        df_found = df_log[(df_log['date'] == str(today)) & (df_log['username'] == username)].reset_index(drop=True)
        if len(df_found) != 1:
            # scraping process
            df_film = scrape_films(username)
            df_film = df_film[df_film['rating']!=-1].reset_index(drop=True)
            st.write("You have {0} movies to scrape".format(len(df_film)))
            df_rating, df_actor, df_director, df_genre = scrape_films_details(df_film)

            # export file
            df_film.to_pickle('log/{0}_dff.pickle'.format(filename))
            df_rating.to_pickle('log/{0}_dfr.pickle'.format(filename))
            df_actor.to_pickle('log/{0}_dfa.pickle'.format(filename))
            df_director.to_pickle('log/{0}_dfd.pickle'.format(filename))
            df_genre.to_pickle('log/{0}_dfg.pickle'.format(filename))
            
            # add new log
            new_row = {'date':str(today), 'username':username}
            df_log = df_log.append(new_row, ignore_index=True)
            df_log.to_csv('log_detail.csv', index=False)
        else:
            st.write("We already have scraped your data today")
            df_film = pd.read_pickle('log/{0}_dff.pickle'.format(filename))
            df_rating = pd.read_pickle('log/{0}_dfr.pickle'.format(filename))
            df_actor = pd.read_pickle('log/{0}_dfa.pickle'.format(filename))
            df_director = pd.read_pickle('log/{0}_dfd.pickle'.format(filename))
            df_genre = pd.read_pickle('log/{0}_dfg.pickle'.format(filename))
        
        st.write("---")
        st.markdown("<h1 style='text-align:center;'>👤 {0}'s Profile Analysis</h1>".format(username), unsafe_allow_html=True)
        st.write('')
        row_df = st.columns(3)
        with row_df[0]:
            st.markdown(
                div(
                    style=styles(
                        text_align="center",
                        padding=(rem(1), 0, rem(2), 0),
                    )
                )(
                    h2(style=styles(font_size=rem(2), padding=0))('👁️ Rated Movies'),
                    big(style=styles(font_size=rem(5), font_weight=600, line_height=1))(
                        len(df_film)
                    )
                ),
                unsafe_allow_html=True,
            )
            # st.header("⭐ Your Rated Movies")
            # st.dataframe(pd.merge(df_film, df_rating)[['title', 'rating', 'avg_rating', 'year']])
        with row_df[1]:
            st.markdown(
                div(
                    style=styles(
                        text_align="center",
                        padding=(rem(1), 0, rem(2), 0),
                    )
                )(
                    h2(style=styles(font_size=rem(2), padding=0))('❤️ Liked Movies'),
                    big(style=styles(font_size=rem(5), font_weight=600, line_height=1))(
                        len(df_film[df_film['liked']==True])
                    )
                ),
                unsafe_allow_html=True,
            )
            # st.header("❤️ Your Liked Movies")
            # st.dataframe(pd.merge(df_film[df_film['liked']==True], df_rating)[['title', 'rating', 'avg_rating', 'year']])
        with row_df[2]:
            st.markdown(
                div(
                    style=styles(
                        text_align="center",
                        padding=(rem(1), 0, rem(2), 0),
                    )
                )(
                    h2(style=styles(font_size=rem(2), padding=0))('⭐ Average Ratings'),
                    big(style=styles(font_size=rem(5), font_weight=600, line_height=1))(
                        round(df_film['rating'].mean(),2)
                    )
                ),
                unsafe_allow_html=True,
            )
        # data_temp = df_film['rating'].astype(str).value_counts().reset_index()
        # data_temp.rename(columns = {'index':'rating', 'rating':'count'}, inplace=True)
        df_rating_merged = pd.merge(df_film, df_rating)
        df_rating_merged['rating'] = df_rating_merged['rating'].astype(float)
        df_rating_merged['avg_rating'] = df_rating_merged['avg_rating'].astype(float)
        df_rating_merged['difference'] = df_rating_merged['rating']-df_rating_merged['avg_rating']
        df_rating_merged['difference_abs'] = abs(df_rating_merged['difference'])
        st.write("")
        row_year = st.columns(2)

        with row_year[0]:
            st.subheader("Rated Movies by Release Year")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("year:O", axis=alt.Axis(labelAngle=-45)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)
            st.markdown("""
            Looks like the average release date is around **{}**, with your oldest movie being **[{}]({})** ({}) and your latest being **[{}]({})** ({}).
            Your movies mostly were released in {}.
            """.format(round(df_rating_merged['year'].astype(float).mean()),
                       df_rating_merged['title'].values[-1], DOMAIN+df_rating_merged['link'].values[-1], df_rating_merged['year'].values[-1],
                       df_rating_merged['title'].values[0], DOMAIN+df_rating_merged['link'].values[0], df_rating_merged['year'].values[0],
                       df_rating_merged['year'].value_counts().index[0]
                       ))

        with row_year[1]:
            st.subheader("Rated Movies by Decade")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("decade", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)
            st.markdown("""
            You mostly watched movies that were released in the **{}**, you rated {} movies from that decade.
            """.format(df_rating_merged['decade'].value_counts().index[0], df_rating_merged['decade'].value_counts().values[0]))

        st.write("")
        row_rating = st.columns(2)
        
        with row_rating[0]:
            st.subheader("How Do You Rate Your Movies?")
            st.write("")
            # st.altair_chart(alt.Chart(data_temp).mark_bar(tooltip=True).encode(
            #     x='rating',
            #     y='count',
            #     color=alt.Color(value="#00b020"),
            # ), use_container_width=True)
            df_film['rating'] = df_film['rating'].astype(str)
            st.altair_chart(alt.Chart(df_film).mark_bar(tooltip=True).encode(
                alt.X("rating", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)
            
            if (df_rating_merged['difference'].mean() > 0):
                ave_rat = 'higher'
            else:
                ave_rat = 'lower'

            st.markdown("""
            It looks like on average you rate movies **{}** than the average Letterboxd user, **by about {} points**.
            You differed from the crowd most on the movie **[{}]({})** where you rated the movie {} stars while the general users rated the movie {}.
            """.format(ave_rat, abs(round(df_rating_merged['difference'].mean(),2)),
                       df_rating_merged[df_rating_merged['difference_abs'] == df_rating_merged['difference_abs'].max()]['title'].values[0],
                       DOMAIN+df_rating_merged[df_rating_merged['difference_abs'] == df_rating_merged['difference_abs'].max()]['link'].values[0],
                       df_rating_merged[df_rating_merged['difference_abs'] == df_rating_merged['difference_abs'].max()]['rating'].values[0],
                       df_rating_merged[df_rating_merged['difference_abs'] == df_rating_merged['difference_abs'].max()]['avg_rating'].values[0]))
        with row_rating[1]:
            st.subheader("How Do Letterboxd Users Rate Your Movies?")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("avg_rating", bin=True, axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)
            st.markdown("""
            Here is the distribution of average rating by other Letterboxd users for the movies that you've rated. Note that this is a distribution of
            averages, which explains the lack of extreme values!
            """)
        st.write("")

        df_director_merged = pd.merge(df_film, df_director)
        df_actor_merged = pd.merge(df_film, df_actor)
        df_temp = df_director['director'].value_counts().reset_index()
        df_temp.rename(columns = {'index':'director', 'director':'count'}, inplace=True)
        df_temp_2 = df_director_merged.groupby(['director', 'director_link']).agg({'liked':'sum'})
        df_temp_2 = df_temp_2.reset_index()
        df_temp = pd.merge(df_temp_2, df_temp)
        df_temp = df_temp.sort_values('count', ascending=False).reset_index(drop=True)
        n_director = df_temp.iloc[10]['count']
        df_temp = df_temp[df_temp['count']>=n_director]
        
        # df_temp = df_temp[df_temp['count']!=1]
        
        row_director = st.columns(2)
        with row_director[0]:
            st.subheader("Movies Rated by Director")
            st.write("")
            st.altair_chart(alt.Chart(df_director_merged[df_director_merged['director'].isin(df_temp['director'])]).mark_bar(tooltip=True).encode(
                y=alt.X("director", sort='-x', axis=alt.Axis(labelAngle=0)),
                x='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)
            st.markdown("""
            You rated **{}** movies that were directed by **[{}]({})**. Your favorite director is probably **[{}]({})** which you liked **{}** of
            his/her movies.
            """.format(df_temp['count'].values[0], df_temp['director'].values[0], DOMAIN+df_temp['director_link'].values[0],
                       df_temp[df_temp['liked']==df_temp['liked'].max()]['director'].values[0],
                       DOMAIN+df_temp[df_temp['liked']==df_temp['liked'].max()]['director_link'].values[0],
                       df_temp['liked'].max()))

        df_temp_actor = df_actor['actor'].value_counts().reset_index()
        df_temp_actor.rename(columns = {'index':'actor', 'actor':'count'}, inplace=True)
        df_temp_actor = df_temp_actor.sort_values('count', ascending=False).reset_index(drop=True)
        # df_temp_actor = df_temp_actor[df_temp_actor['count']!=1]
        n_actor = df_temp_actor.iloc[10]['count']
        df_temp_actor = df_temp_actor[df_temp_actor['count']>=n_actor]
        # df_temp_actor = df_temp_actor[:10]
        with row_director[1]:
            st.subheader("Movies Rated by Actor")
            st.write("")
            st.altair_chart(alt.Chart(df_actor_merged[df_actor_merged['actor'].isin(df_temp_actor['actor'])]).mark_bar(tooltip=True).encode(
                y=alt.X("actor", sort='-x', axis=alt.Axis(labelAngle=0)),
                x='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), use_container_width=True)



            
        


elif selected_sect == sections[1]:
    print('b')
elif selected_sect == sections[2]:
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