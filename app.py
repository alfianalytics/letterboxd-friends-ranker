import streamlit as st
from htbuilder import div, big, h2, styles, p
from htbuilder.units import rem
import altair as alt
import numpy as np
import pandas as pd
import pickle
from deployment import scrape_films_details, scrape_films, scrape_friends, list_friends, recommend_movies, DOMAIN, classify_popularity, classify_likeability
from pathlib import Path
from datetime import date

if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'collapsed'

current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
css_file = current_dir / "styles" / "main.css"
st.set_page_config(page_icon="📽️", page_title="Letterboxd Analysis", layout='wide', initial_sidebar_state=st.session_state.sidebar_state)
with open(css_file) as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


# sections = ['Analyze Profile', 'Compare 2 Profile', 'Friends Ranker + Movie Recommendations']
sections = ['Analyze Profile', 'Friends Ranker + Movie Recommendations']
selected_sect = st.sidebar.selectbox('Choose mode', sections)

if selected_sect == sections[0]:
    st.title('📽️ Letterboxd Profile Analyzer')
    st.write("""See how you rate your movies, what movies you like, the genres, the actors and directors of those movies 🍿.
    Read my **[Medium article](https://medium.com/@alf.19x/letterboxd-profile-analysis-identifying-our-movie-watching-behaviour-281f913a7073)**
    about this.""")
    with st.expander("ℹ️ What will this app do?"):
        st.markdown("""
        - Scrape your rated movies
        - Scrape your rated movies' details
        - Analyze and visualize those movies
        """)
        st.markdown("""
        ⚠️ Note: It takes approximately 1 seconds to scrape details from one movie, so it will take some minutes to process
        especially when you have rated many movies.
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
            df_rating, df_actor, df_director, df_genre = scrape_films_details(df_film, username)

            # export file
            df_film.to_pickle('log/{0}_dff.pickle'.format(filename))
            df_rating.to_pickle('log/{0}_dfr.pickle'.format(filename))
            df_actor.to_pickle('log/{0}_dfa.pickle'.format(filename))
            df_director.to_pickle('log/{0}_dfd.pickle'.format(filename))
            df_genre.to_pickle('log/{0}_dfg.pickle'.format(filename))
            
            # add new log
            new_row = pd.DataFrame({'date':[str(today)], 'username':[username]})
            df_log = pd.concat([df_log, new_row]).reset_index(drop=True)
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
        df_rating['ltw_ratio'] = df_rating['liked_by']/df_rating['watched_by']
        df_rating['popularity'] = df_rating.apply(lambda row: classify_popularity(row['watched_by']), axis=1)
        df_rating['likeability'] = df_rating.apply(lambda row: classify_likeability(row['ltw_ratio']), axis=1)
        df_rating_merged = pd.merge(df_film, df_rating)
        df_rating_merged['rating'] = df_rating_merged['rating'].astype(float)
        df_rating_merged['avg_rating'] = df_rating_merged['avg_rating'].astype(float)
        df_rating_merged['difference'] = df_rating_merged['rating']-df_rating_merged['avg_rating']
        df_rating_merged['difference_abs'] = abs(df_rating_merged['difference'])
        
        st.write("")
        row_year = st.columns(2)

        with row_year[0]:
            st.subheader("When were Your Movies Released?")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("year:O", axis=alt.Axis(labelAngle=90)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), 
            #theme=None,
            use_container_width=True)
            st.markdown("""
            Looks like the average release date is around **{}**, with your oldest movie being **[{}]({})** ({}) and your latest being **[{}]({})** ({}).
            Your movies mostly were released in {}.
            """.format(round(df_rating_merged['year'].astype(float).mean()),
                       df_rating_merged['title'].values[-1], DOMAIN+df_rating_merged['link'].values[-1], df_rating_merged['year'].values[-1],
                       df_rating_merged['title'].values[0], DOMAIN+df_rating_merged['link'].values[0], df_rating_merged['year'].values[0],
                       df_rating_merged['year'].value_counts().index[0]
                       ))

        with row_year[1]:
            st.subheader("Which Decade were Your Movies Released in?")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("decade", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), 
            #theme=None, 
            use_container_width=True)
            liked = ""
            if (df_rating_merged[df_rating_merged['liked'] == True].shape[0] != 0):
                liked = """Your favorite decade is probably **{}** since your liked movies mostly were released in that decade, with
                {} movies.""".format(df_rating_merged[df_rating_merged['liked'] == True]['decade'].value_counts().index[0],
                       df_rating_merged[df_rating_merged['liked'] == True]['decade'].value_counts().values[0])
            st.markdown("""
            You mostly rated movies that were released in the **{}**, you rated {} movies from that decade.
            {}
            """.format(df_rating_merged['decade'].value_counts().index[0], df_rating_merged['decade'].value_counts().values[0], liked))

        st.write("")
        # st.dataframe(df_rating_merged)
        
        
        row_rating = st.columns(2)
        
        with row_rating[0]:
            st.subheader("How Do You Rate Your Movies?")
            st.write("")
            # st.altair_chart(alt.Chart(data_temp).mark_bar(tooltip=True).encode(
            #     x='rating',
            #     y='count',
            #     color=alt.Color(value="#00b020"),
            # ), theme=None, use_container_width=True)
            df_film['rating'] = df_film['rating'].astype(str)
            st.altair_chart(alt.Chart(df_film).mark_bar(tooltip=True).encode(
                alt.X("rating", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), 
            #theme=None,
            use_container_width=True)
            
            if (df_rating_merged['difference'].mean() > 0):
                ave_rat = 'higher'
            else:
                ave_rat = 'lower'

            st.markdown("""
            It looks like on average you rated movies **{}** than the average Letterboxd user, **by about {} points**.
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
            ), 
            #theme=None, 
            use_container_width=True)
            st.markdown("""
            Here is the distribution of average rating by other Letterboxd users for the movies that you've rated. Your movie with the lowest average
            rating is **[{}]({})** ({}) with {}, the highest is **[{}]({})** ({}) with {}.
            """.format(df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].min()]['title'].values[0],
                       DOMAIN+df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].min()]['link'].values[0],
                       df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].min()]['year'].values[0],
                       df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].min()]['avg_rating'].values[0],
                       df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].max()]['title'].values[0],
                       DOMAIN+df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].max()]['link'].values[0],
                       df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].max()]['year'].values[0],
                       df_rating_merged[df_rating_merged['avg_rating'] == df_rating_merged['avg_rating'].max()]['avg_rating'].values[0]))
        st.write("")

        row_popularity = st.columns(2)
        with row_popularity[0]:
            st.subheader("How Popular are Your Movies?")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("popularity", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ), 
            #theme=None,
            use_container_width=True)
            popular = ""
            if (df_rating_merged['popularity'].value_counts().index[0] == '3 - popular'):
                popular = "As expected, you mostly rated movies that are popular among Letterboxd users."
            else:
                popular = "Wow, you have a very unique taste because you mostly don't watch popular movies."
            st.markdown("""
            {} Your most obscure movie is **[{}]({})** with just **{:,} users watched**, your most popular movie is **[{}]({})** with **{:,} users watched**.
            """.format(popular,
                       df_rating_merged[df_rating_merged['watched_by'] == df_rating_merged['watched_by'].min()]['title'].values[0],
                       DOMAIN + df_rating_merged[df_rating_merged['watched_by'] == df_rating_merged['watched_by'].min()]['link'].values[0],
                       df_rating_merged['watched_by'].min(),
                       df_rating_merged[df_rating_merged['watched_by'] == df_rating_merged['watched_by'].max()]['title'].values[0],
                       DOMAIN + df_rating_merged[df_rating_merged['watched_by'] == df_rating_merged['watched_by'].max()]['link'].values[0],
                       df_rating_merged['watched_by'].max()))
            with st.expander("Popularity classification"):
                st.markdown("""
                Popularity is determined by number of watches.
                - <= 10,000 -> very obscure
                - 10,101 - 100,000 -> obscure
                - 100,001 - 1,000,000 -> popular
                - \> 1,000,000 -> very popular
                """)
        with row_popularity[1]:
            st.subheader("How Likeable are Your Movies?")
            st.write("")
            st.altair_chart(alt.Chart(df_rating_merged).mark_bar(tooltip=True).encode(
                alt.X("likeability", axis=alt.Axis(labelAngle=0)),
                y='count()',
                color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            ),
            #theme=None,
            use_container_width=True)
            unlikeable = ""
            if (df_rating_merged[(df_rating_merged['likeability'] == "1 - rarely likeable") & (df_rating_merged['liked'] == True)].shape[0] > 0):
                if (df_rating_merged[(df_rating_merged['likeability'] == "1 - rarely likeable") & (df_rating_merged['liked'] == True)].shape[0] > 1):
                    unlikeable = "Wow, you liked movies that are rarely likeable, you really followed your heart and don't care what others think."
                else:
                    unlikeable = """
                    Wow, you liked a movie that is rarely likeable, it's **[{}]({}) ({}\% users liked)**, you must have a genuine opinion on this movie.
                    """.format(df_rating_merged[(df_rating_merged['likeability'] == "1 - rarely likeable") & (df_rating_merged['liked'] == True)]['title'].values[0],
                               DOMAIN + df_rating_merged[(df_rating_merged['likeability'] == "1 - rarely likeable") & (df_rating_merged['liked'] == True)]['link'].values[0],
                               round(df_rating_merged[(df_rating_merged['likeability'] == "1 - rarely likeable") & (df_rating_merged['liked'] == True)]['ltw_ratio'].values[0]*100,2))
            mostly = ""
            if (df_rating_merged['likeability'].value_counts().index[0] == '3 - often likeable'):
                mostly = "You mostly rated movies that are often likeable, it possibly means that your movies are mostly good movies."
            elif ((df_rating_merged[df_rating_merged['likeability'] == '1 - rarely likeable'].shape[0] +
                  df_rating_merged[df_rating_merged['likeability'] == '2 - sometimes likeable'].shape[0]) >
                  (df_rating_merged[df_rating_merged['likeability'] == '3 - often likeable'].shape[0] +
                  df_rating_merged[df_rating_merged['likeability'] == '4 - usually likeable'].shape[0])):
                mostly = "You mostly rated movies that are less likeable, it possibly means that you've been watching bad movies all this time."
            st.markdown("""
            {} {} Your most likeable movie is **[{}]({})** with **{}\% users liked**, your least likeable movie is **[{}]({})** with just **{}\% users liked**.
            """.format(unlikeable, mostly,
                       df_rating_merged[df_rating_merged['ltw_ratio'] == df_rating_merged['ltw_ratio'].max()]['title'].values[0],
                       DOMAIN + df_rating_merged[df_rating_merged['ltw_ratio'] == df_rating_merged['ltw_ratio'].max()]['link'].values[0],
                       round(df_rating_merged['ltw_ratio'].max()*100,2),
                       df_rating_merged[df_rating_merged['ltw_ratio'] == df_rating_merged['ltw_ratio'].min()]['title'].values[0],
                       DOMAIN + df_rating_merged[df_rating_merged['ltw_ratio'] == df_rating_merged['ltw_ratio'].min()]['link'].values[0],
                       round(df_rating_merged['ltw_ratio'].min()*100,2))
                       )
            with st.expander("Likeability classification"):
                st.markdown("""
                Likeability is determined by number of likes to number of watches ratio.
                - <= 0.1 -> rarely likeable
                - 0.1 - 0.2 -> sometimes likeable
                - 0.2 - 0.4 -> often likeable
                - \> 0.4 -> usually likeable
                """)


        df_director_merged = pd.merge(df_film, df_director)
        df_actor_merged = pd.merge(df_film, df_actor)

        df_temp = df_director['director'].value_counts().reset_index()
        df_temp.rename(columns = {'index':'director', 'director':'count'}, inplace=True)
        df_director_merged['rating'] = df_director_merged['rating'].astype(float)
        df_temp_2 = df_director_merged.groupby(['director', 'director_link']).agg({'liked':'sum', 'rating':'mean'})
        df_temp_2 = df_temp_2.reset_index()
        df_temp = pd.merge(df_temp_2, df_temp)
        df_temp = df_temp.sort_values('count', ascending=False).reset_index(drop=True)
        n_director = df_temp.iloc[14]['count']
        df_temp = df_temp[df_temp['count']>=n_director]
        
        # df_temp = df_temp[df_temp['count']!=1]
        st.write("")
        st.subheader("Your Top Directors")
        row_director = st.columns((2,1))
        with row_director[0]:
            st.write("")
            # st.dataframe(df_temp)
            base = alt.Chart(df_director_merged[df_director_merged['director'].isin(df_temp['director'])]).encode(
                    alt.X("director", sort=df_temp['director'].tolist(), axis=alt.Axis(labelAngle=0))
                )
            
            area = base.mark_bar(tooltip=True).encode(
                alt.Y('count()',
                    axis=alt.Axis(title='Count of Records')),
                    color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            )
            line = alt.Chart(df_temp).mark_line(interpolate='monotone').encode(
                alt.X("director", sort=df_temp['director'].tolist(), axis=alt.Axis(labelAngle=0)),
                alt.Y('rating', axis=alt.Axis(title='Average Rating', titleColor='#40bcf4'), scale=alt.Scale(zero=False)),
                color=alt.Color(value="#40bcf4"),
            )
            # st.altair_chart(alt.Chart(df_director_merged[df_director_merged['director'].isin(df_temp['director'])]).mark_bar(tooltip=True).encode(
            #     y=alt.X("director", sort='-x', axis=alt.Axis(labelAngle=0)),
            #     x='count()',
            #     color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            # ), theme=None, use_container_width=True)
            # st.altair_chart(alt.Chart(df_temp).mark_line().encode(
            #     alt.Y("director", sort=df_temp['director'].tolist(), axis=alt.Axis(labelAngle=0)),
            #     alt.X('rating', scale=alt.Scale(zero=False)),
            #     color=alt.Color(value="#00b020"),
            # ), theme=None, use_container_width=True)
            st.altair_chart(alt.layer(area, line).resolve_scale(
                y = 'independent'
            ), 
            #theme=None,
            use_container_width=True)
        with row_director[1]:
            if (df_temp['liked'].max() != 0):
                if (df_temp[df_temp['rating']==df_temp['rating'].max()]['director'].values[0] != df_temp[df_temp['liked']==df_temp['liked'].max()]['director'].values[0]):
                    st.markdown("""
                    You rated **{}** movies that were directed by **[{}]({})**. Your favorite director is probably **[{}]({})** which you
                    gave average rating of **{}**, or **[{}]({})** which you liked **{}** of his/her movies.
                    """.format(df_temp['count'].values[0], df_temp['director'].values[0], DOMAIN+df_temp['director_link'].values[0],
                            df_temp[df_temp['rating']==df_temp['rating'].max()]['director'].values[0],
                            DOMAIN+df_temp[df_temp['rating']==df_temp['rating'].max()]['director_link'].values[0],
                            round(df_temp['rating'].max(), 2),
                            df_temp[df_temp['liked']==df_temp['liked'].max()]['director'].values[0],
                            DOMAIN+df_temp[df_temp['liked']==df_temp['liked'].max()]['director_link'].values[0],
                            df_temp['liked'].max()))
                else:
                    st.markdown("""
                    You rated **{}** movies that were directed by **[{}]({})**. Your favorite director is probably **[{}]({})** which you
                    gave average rating of **{}** and liked **{}** of his/her movies.
                    """.format(df_temp['count'].values[0], df_temp['director'].values[0], DOMAIN+df_temp['director_link'].values[0],
                            df_temp[df_temp['rating']==df_temp['rating'].max()]['director'].values[0],
                            DOMAIN+df_temp[df_temp['rating']==df_temp['rating'].max()]['director_link'].values[0],
                            round(df_temp['rating'].max(), 2),
                            df_temp['liked'].max()))
            else:
                st.markdown("""
                You rated **{}** movies that were directed by **[{}]({})**. Your favorite director is probably **[{}]({})** which you
                    gave average rating of **{}**.
                """.format(df_temp['count'].values[0], df_temp['director'].values[0], DOMAIN+df_temp['director_link'].values[0],
                            df_temp[df_temp['rating']==df_temp['rating'].max()]['director'].values[0],
                            DOMAIN+df_temp[df_temp['rating']==df_temp['rating'].max()]['director_link'].values[0],
                            round(df_temp['rating'].max(), 2)))
            
        
        df_temp = df_actor['actor'].value_counts().reset_index()
        df_temp.rename(columns = {'index':'actor', 'actor':'count'}, inplace=True)
        df_actor_merged['rating'] = df_actor_merged['rating'].astype(float)
        df_temp_2 = df_actor_merged.groupby(['actor', 'actor_link']).agg({'liked':'sum', 'rating':'mean'})
        df_temp_2 = df_temp_2.reset_index()
        df_temp = pd.merge(df_temp_2, df_temp)
        df_temp = df_temp.sort_values('count', ascending=False).reset_index(drop=True)
        # df_temp = df_temp[df_temp['count']!=1]
        n_actor = df_temp.iloc[19]['count']
        df_temp = df_temp[df_temp['count']>=n_actor]
        # df_temp = df_temp[:10]
        st.write("")
        st.subheader("Your Top Actors")
        row_actor = st.columns((2,1))
        with row_actor[0]:
            st.write("")
            # st.altair_chart(alt.Chart(df_actor_merged[df_actor_merged['actor'].isin(df_temp['actor'])]).mark_bar(tooltip=True).encode(
            #     y=alt.X("actor", sort='-x', axis=alt.Axis(labelAngle=0)),
            #     x='count()',
            #     color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            # ), theme=None, use_container_width=True)
            base = alt.Chart(df_actor_merged[df_actor_merged['actor'].isin(df_temp['actor'])]).encode(
                    alt.X("actor", sort=df_temp['actor'].tolist(), axis=alt.Axis(labelAngle=0))
                )
            
            area = base.mark_bar(tooltip=True).encode(
                alt.Y('count()',
                    axis=alt.Axis(title='Count of Records')),
                    color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            )
            line = alt.Chart(df_temp).mark_line(interpolate='monotone').encode(
                alt.X("actor", sort=df_temp['actor'].tolist(), axis=alt.Axis(labelAngle=0)),
                alt.Y('rating', axis=alt.Axis(title='Average Rating', titleColor='#40bcf4'), scale=alt.Scale(zero=False)),
                color=alt.Color(value="#40bcf4"),
            )
            st.altair_chart(alt.layer(area, line).resolve_scale(
                y = 'independent'
            ),
            #theme=None,
            use_container_width=True)
        with row_actor[1]:
            if (df_temp['liked'].max() != 0):
                st.markdown("""
                You rated **{}** movies starring **[{}]({})**. Your favorite actor is probably **[{}]({})** which you liked **{}** of
                his/her movies.
                """.format(df_temp['count'].values[0], df_temp['actor'].values[0], DOMAIN+df_temp['actor_link'].values[0],
                        df_temp[df_temp['liked']==df_temp['liked'].max()]['actor'].values[0],
                        DOMAIN+df_temp[df_temp['liked']==df_temp['liked'].max()]['actor_link'].values[0],
                        df_temp['liked'].max()))
            else:
                st.markdown("""
                You rated **{}** movies starring **[{}]({})**.
                """.format(df_temp['count'].values[0], df_temp['actor'].values[0], DOMAIN+df_temp['actor_link'].values[0]))
        st.write("")
        st.subheader("Genre Breakdown")
        row_genre = st.columns((2,1))
        df_genre_merged = pd.merge(df_film, df_genre)
        df_temp = df_genre['genre'].value_counts().reset_index()
        df_temp.rename(columns = {'index':'genre', 'genre':'count'}, inplace=True)
        df_temp = df_temp[df_temp['count'] > df_film.shape[0]/100].reset_index(drop=True)
        df_genre_merged['rating'] = df_genre_merged['rating'].astype(float)
        df_temp_2 = df_genre_merged.groupby(['genre']).agg({'liked':'sum', 'rating':'mean'})
        df_temp_2 = df_temp_2.reset_index()
        df_temp = pd.merge(df_temp_2, df_temp)
        df_temp = df_temp.sort_values('count', ascending=False).reset_index(drop=True)
        
        with row_genre[0]:
            
            st.write("")
            # st.altair_chart(alt.Chart(df_genre_merged).mark_bar(tooltip=True).encode(
            #     alt.X("genre", sort='-y', axis=alt.Axis(labelAngle=45)),
            #     y='count()',
            #     color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            # ), theme=None, use_container_width=True)
            # st.altair_chart(alt.Chart(df_genre_merged).mark_line(tooltip=True).encode(
            #     alt.X("genre", sort='-y', axis=alt.Axis(labelAngle=45)),
            #     alt.Y('mean(rating):Q', scale=alt.Scale(zero=False)),
            #     color=alt.Color(value="#00b020"),
            # ), theme=None, use_container_width=True)
            base = alt.Chart(df_genre_merged[df_genre_merged['genre'].isin(df_temp['genre'])]).encode(
                    alt.X("genre", sort=df_temp['genre'].tolist(), axis=alt.Axis(labelAngle=90))
                )
            # st.altair_chart(base)
            area = base.mark_bar(tooltip=True).encode(
                alt.Y('count()',
                    axis=alt.Axis(title='Count of Records')),
                    color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            )
            line = alt.Chart(df_temp).mark_line(interpolate='monotone').encode(
                    alt.X('genre', sort=df_temp['genre'].tolist()),
                    alt.Y('rating',
                        axis=alt.Axis(title='Average Rating', titleColor='#40bcf4'), scale=alt.Scale(zero=False)),
                        color=alt.Color(value="#40bcf4")
                )
            # line = base.mark_line(tooltip=True).encode(
            #         alt.Y('mean(rating):Q',
            #             axis=alt.Axis(title='Average Rating'), scale=alt.Scale(zero=False)),
            #             color=alt.Color(value="#ff8000")
            #     )
            st.altair_chart(alt.layer(area, line).resolve_scale(
                y = 'independent'
            ), 
            #theme=None,
            use_container_width=True)
        with row_genre[1]:
            liked = ""
            if (df_temp['liked'].max() != 0):
                liked = "You mostly liked **{}** movies with {} movies.".format(df_temp[df_temp['liked']==df_temp['liked'].max()]['genre'].values[0],
                       df_temp[df_temp['liked']==df_temp['liked'].max()]['liked'].values[0])
            st.markdown("""
            Seems like you're not a great fan of **{}** movies, you gave average rating of {} on that genre.
            You really gave good ratings on **{}** movies, with average rating of {}.
            You mostly rated **{}** movies with {} movies. {}
            """.format(df_temp[df_temp['rating']==df_temp['rating'].min()]['genre'].values[0],
                       round(df_temp[df_temp['rating']==df_temp['rating'].min()]['rating'].values[0], 2),
                       df_temp[df_temp['rating']==df_temp['rating'].max()]['genre'].values[0],
                       round(df_temp[df_temp['rating']==df_temp['rating'].max()]['rating'].values[0], 2),
                       df_temp[df_temp['count']==df_temp['count'].max()]['genre'].values[0],
                       df_temp[df_temp['liked']==df_temp['liked'].max()]['count'].values[0],
                       liked))
        
        
        df_genre_combination = pd.DataFrame(columns=df_genre_merged.columns)
        for i in range(len(df_temp['genre'].tolist())):
            for j in range(i+1, len(df_temp['genre'].tolist())):
                df_ha = df_genre_merged[(df_genre_merged['genre'] == df_temp['genre'].tolist()[i]) | (df_genre_merged['genre'] == df_temp['genre'].tolist()[j])]
                if len(df_ha) != 0:
                    df_ha['genre'] = df_temp['genre'].tolist()[i] + " & " + df_temp['genre'].tolist()[j]
                    df_ha = df_ha[df_ha.duplicated('id')]
                    df_genre_combination = pd.concat([df_genre_combination, df_ha]).reset_index(drop=True)
        
        df_temp_comb = df_genre_combination['genre'].value_counts().reset_index()
        df_temp_comb.rename(columns = {'index':'genre', 'genre':'count'}, inplace=True)
        df_genre_combination['rating'] = df_genre_combination['rating'].astype(float)
        df_genre_combination['liked'] = df_genre_combination['liked'].astype(int)
        df_temp_comb_2 = df_genre_combination.groupby(['genre']).agg({'liked':'sum', 'rating':'mean'})
        df_genre_combination['liked'] = df_genre_combination['liked'].astype(bool)
        df_temp_comb_2 = df_temp_comb_2.reset_index()
        df_temp_comb = pd.merge(df_temp_comb_2, df_temp_comb)
        df_temp_comb = df_temp_comb.sort_values('count', ascending=False).reset_index(drop=True)
        n_genre = df_temp_comb.iloc[19]['count']
        df_temp_comb = df_temp_comb[df_temp_comb['count']>=n_genre]

        st.subheader("Top Genre Combinations Breakdown")
        row_genre_comb = st.columns((2,1))
        with row_genre_comb[0]:
            st.write("")
            base = alt.Chart(df_genre_combination[df_genre_combination['genre'].isin(df_temp_comb['genre'])]).encode(
                        alt.X("genre", sort=df_temp_comb['genre'].tolist(), axis=alt.Axis(labelAngle=90))
                    )
            area = base.mark_bar(tooltip=True).encode(
                alt.Y('count()',
                    axis=alt.Axis(title='Count of Records')),
                    color=alt.Color('liked', scale=alt.Scale(domain=[True, False], range=["#ff8000", "#00b020"]))
            )
            line = alt.Chart(df_temp_comb).mark_line(interpolate='monotone').encode(
                    alt.X('genre', axis=alt.Axis(title='genre combination'), sort=df_temp_comb['genre'].tolist()),
                    alt.Y('rating',
                        axis=alt.Axis(title='Average Rating', titleColor='#40bcf4'), scale=alt.Scale(zero=False)),
                        color=alt.Color(value="#40bcf4")
                )
            st.altair_chart(alt.layer(area, line).resolve_scale(
                y = 'independent'
            ), 
            #theme=None, 
            use_container_width=True)
        with row_genre_comb[1]:
            top_2 = ""
            if (pd.DataFrame(df_temp_comb['genre'][0].split(" & ")).isin(df_temp.iloc[:2]['genre'].tolist()).sum()[0] == 0):
                top_2 = """
                It's a little bit surprising that your mostly rated genre combination (**{}**) is not your top 2 genres (**{} & {}**).
                """.format(df_temp_comb['genre'][0], df_temp['genre'][0], df_temp['genre'][1])
            elif ((pd.DataFrame(df_temp_comb['genre'][0].split(" & ")).isin(df_temp.iloc[:2]['genre'].tolist()).sum()[0] == 1)):
                top_2 = "Well, it's no surprise that your mostly rated genre combination (**{}**) consists of one of your top 2 genres (**{}**).".format(df_temp_comb['genre'][0],
                                                                                                                                                         df_temp.iloc[:2][df_temp.iloc[:2]['genre'].isin(df_temp_comb['genre'][0].split(" & "))]['genre'].values[0])
            elif ((pd.DataFrame(df_temp_comb['genre'][0].split(" & ")).isin(df_temp.iloc[:2]['genre'].tolist()).sum()[0] == 2)):
                top_2 = "Well, it's no surprise that your mostly rated genre combination consists of your top 2 genres (**{}**).".format(df_temp_comb['genre'][0])
            st.markdown("""It's a common thing that a movie is categorized into more than 1 genre, so we'll look deeper into the genre combinations
            to get a better understanding of your movies.
            """)

            low = ""
            if (pd.DataFrame(df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].min()]['genre'].values[0].split(" & ")).isin(df_temp[df_temp['rating'] == df_temp['rating'].min()]['genre'].values.tolist()).sum()[0] != 0):
                low = """Once again, **{}** movies are definitely not your cup of tea, even when it's combined with other genre, the combination of **{}**
                has the lowest average rating ({}) compared to your other top genre combinations.
                """.format(df_temp[df_temp['rating'] == df_temp['rating'].min()]['genre'].values[0],
                           df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].min()]['genre'].values[0],
                           round(df_temp_comb['rating'].min(),2))
            else:
                low = """Genre combination with the lowest average rating you gave among your other top genre combinations is **{}** with {}.
                """.format(df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].min()]['genre'].values[0],
                           round(df_temp_comb['rating'].min(),2))
            
            high = ""
            if (pd.DataFrame(df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].max()]['genre'].values[0].split(" & ")).isin(df_temp[df_temp['rating'] == df_temp['rating'].max()]['genre'].values.tolist()).sum()[0] != 0):
                high = """You seem to have a lot appreciation for **{}** movies, the combination of **{}**
                has the highest average rating ({}) compared to your other top genre combinations.
                """.format(df_temp[df_temp['rating'] == df_temp['rating'].max()]['genre'].values[0],
                           df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].max()]['genre'].values[0],
                           round(df_temp_comb['rating'].max(),2))
            else:
                high = """You gave the highest average rating to **{}** movies with {}.
                """.format(df_temp_comb[df_temp_comb['rating'] == df_temp_comb['rating'].max()]['genre'].values[0],
                            round(df_temp_comb['rating'].max(),2))
            
            st.markdown("{} {} {}".format(top_2, low, high))
            
# elif selected_sect == sections[1]:
#     st.write("Still not ready hehe")
elif selected_sect == sections[1]:
    st.title('📽️ Letterboxd Friends Ranker (+ Movie Recommendations)')
    st.write("""See which friend has the most similar taste in movies to yours based on the ratings and likes of the movies you
    both have watched 🍿. Read my **[Medium article](https://medium.com/@alf.19x/letterboxd-friends-ranker-simple-movie-recommendation-system-80a38dcfb0da)**
    about this.""")
    with st.expander("ℹ️ What will this app do?"):
        st.markdown("""
        - Scrape your rated movies
        - Scrape your friends
        - Scrape your friends' rated movies
        - Compute similarity between you and each of your friend
        - Rank the similarity score
        - Make movie recommendations based on your friends' movies
        """)
        st.markdown("""
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
            df_recom = recommend_movies(df_friends, friends_data, df_a)
            df_recom = df_recom.sort_values('index', ascending=False).reset_index(drop=True)
            df_recom = df_recom[df_recom['no_of_rate'] > 1].reset_index(drop=True)
            df_recom = df_recom.iloc[:100]
            
            df_rating_recom, df_actor_recom, df_director_recom, df_genre_recom = scrape_films_details(df_recom, username)
            df_recom = pd.merge(pd.merge(df_recom, df_rating_recom), df_genre_recom)
            df_recom['genre'] = df_recom.groupby(['id'])['genre'].transform(lambda x: '|'.join(x))
            df_recom = df_recom.drop_duplicates().reset_index(drop=True)
            df_recom['ltw_ratio'] = df_recom['liked_by']/df_recom['watched_by']
            df_recom.to_pickle('log/{0}_dfr.pickle'.format(filename))
            with open('log/{0}_fdd.pickle'.format(filename), 'wb') as f:
                pickle.dump(friends_data, f)
            with open('log/{0}_fl.pickle'.format(filename), 'wb') as f:
                pickle.dump(friends_list, f)
            
            # add new log
            new_row = pd.DataFrame({'date':[str(today)], 'username':[username], 'ftype':[ftype], 'limit':[limit]})
            df_log = pd.concat([df_log, new_row]).reset_index(drop=True)
            df_log.to_csv('log.csv', index=False)
        else:
            st.write("We already have scraped your data today")
            with open('log/{0}_fl.pickle'.format(filename), 'rb') as f:
                friends_list = pickle.load(f)
            df_a = pd.read_pickle('log/{0}_dfa.pickle'.format(filename))
            df_friends = pd.read_pickle('log/{0}_dff.pickle'.format(filename))
            df_friends = df_friends.sort_values('total_index', ascending=False).reset_index(drop=True)
            df_recom = pd.read_pickle('log/{0}_dfr.pickle'.format(filename))
            df_recom['ltw_ratio'] = df_recom['liked_by']/df_recom['watched_by']
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
        
        st.write("")
        st.write("")
        st.subheader("Your Recommended Movies by Popularity and Likeability")
        st.write("")

        @st.experimental_memo
        def convert_df(df_recom):
            return df_recom.to_csv(index=False).encode('utf-8')
        csv = convert_df(df_recom)
        st.altair_chart(alt.Chart(df_recom).mark_circle(size=60).encode(
                alt.X('ltw_ratio:Q', axis=alt.Axis(title='Likeability Ratio'), scale=alt.Scale(zero=False)),
                alt.Y('watched_by:Q', axis=alt.Axis(title='Number of Watches'), scale=alt.Scale(zero=False)),
                color=alt.Color('index', scale=alt.Scale(range=["#00b020", "#ff8000"])),
                tooltip=['title', 'year', 'genre', 'index', 'rating', 'avg_rating', 'no_of_rate'],
            ).interactive(), use_container_width=True)
        with st.expander("Full Data"):
            st.dataframe(df_recom)

            st.download_button(
                "Download Movie Recommenations",
                csv,
                "{}_Movie Recommendations.csv".format(filename),
                "text/csv",
                key='download-csv'
            )
            
            


    
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