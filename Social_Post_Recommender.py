
import itertools
import praw
import spacy
from nltk.corpus import wordnet
import tweepy

# Initiate all our libraries and APIs here
reddit = praw.Reddit(client_id="",
                     client_secret="",
                     password="",
                     user_agent="Post Recommender",
                     username="")

tauth = tweepy.OAuthHandler(consumer_key="",
                            consumer_secret="")
tauth.set_access_token("",
                       "")
tweep = tweepy.API(tauth)

nlp = spacy.load('en_core_web_sm')
UNWANTED_ENTITIES = ['DATE', 'TIME', 'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 'CARDINAL']
GRABBED_POSTS = 10
RECOMMENDED_AMOUNT = 3


class SocialGenerator:
    def __init__(self, site_api):
        self.site = site_api
        self.fetched_posts = {}
        self.recommended_posts = {}
        self.recommended_tweets = []

    # Unfortunately, no twitter APIs have a random tweet generator, so we opt for searching for key words on Twitter
    # We then return those tweets to the user
    def search_twitter(self, p_queries, s_queries):
        for search_term in p_queries:
            recommended_posts = tweep.search(q=search_term, result='mixed', count=5)
            for post in recommended_posts:
                if not self.recommended_tweets or post.text not in self.recommended_tweets:
                    self.recommended_tweets.append(post.text)
            if len(self.recommended_tweets) >= 20:
                break
        for search_term in s_queries:
            recommended_posts = tweep.search(q=search_term, result='mixed', count=5)
            for post in recommended_posts:
                if not self.recommended_tweets or post.text not in self.recommended_tweets:
                    self.recommended_tweets.append(post.text)

            if len(self.recommended_tweets) >= 20:
                return self.recommended_tweets

        return self.recommended_tweets

    # Search through random posts on reddit, number of posts can be inc/dec as well as recommended posts
    def search_reddit(self):
        for i in range(GRABBED_POSTS):
            submission = self.site.subreddit('all').random()
            if submission is not None:
                self.fetched_posts[submission.title] = submission

        self.compare_to_history(self.fetched_posts)

        if len(self.recommended_posts) <= RECOMMENDED_AMOUNT:
            self.search_reddit()

        return self.recommended_posts

    def compare_to_history(self, fetched_posts):
        # Check each word in post until a high match is found in user's interests
        for i in range(len(self.fetched_posts)):
            for word in list(self.fetched_posts)[i].split():
                doc = nlp(word)
                token = doc[0]
                if token.is_stop:
                    continue
                else:
                    fetched_syns = wordnet.synsets(token.text)
                    if fetched_syns:
                        for interest in user.prioritized:
                            interest_syns = wordnet.synsets(interest)
                            if interest_syns:
                                fetched_syns = wordnet.synsets(token.text)[0]
                                interest_syns = wordnet.synsets(interest)[0]
                                if fetched_syns.wup_similarity(interest_syns) is not None:
                                    if fetched_syns.wup_similarity(interest_syns) > 0.8:
                                        url = fetched_posts[list(self.fetched_posts)[i]].url
                                        submission_title = fetched_posts[list(self.fetched_posts)[i]].title
                                        if url not in self.recommended_posts.values():
                                            self.recommended_posts[submission_title] = url

                        for secondary in user.interest_dict:
                            secondary_syns = wordnet.synsets(secondary[0])
                            if secondary_syns:
                                secondary_syns = wordnet.synsets(secondary[0])[0]
                                if fetched_syns.wup_similarity(secondary_syns) is not None:
                                    if fetched_syns.wup_similarity(secondary_syns) > 0.8:
                                        url = fetched_posts[list(self.fetched_posts)[i]].url
                                        submission_title = fetched_posts[list(self.fetched_posts)[i]].title
                                        if url not in self.recommended_posts.values():
                                            self.recommended_posts[submission_title] = url


# Here, we set up a class for any given user and methods to scrape post/comment history
class User:
    # Initialization for username, dict of prioritized interests to search for, list of general interests
    def __init__(self, user_name):
        self.user_name = user_name
        self.prioritized = []
        self.interest_dict = {}

    def scrape_comments_submissions(self):
        # Iterate over each comment
        comments = reddit.redditor(name=self.user_name).comments.new()
        submission_titles = reddit.redditor(name=self.user_name).submissions.new()

        for comment, submission in itertools.zip_longest(comments, submission_titles):
            # Check to ensure a comment or submission is not None type from being "zipped"
            if comment is None and submission is not None:
                doc = nlp(submission.title)
            if submission is None and comment is not None:
                doc = nlp(comment.body)
            elif submission and comment is not None:
                doc = nlp(comment.body + submission.title)

            # Check for entities that are not a date, time, money, etc. Add to priority list
            for ent in doc.ents:
                if type(ent.label_) is str and ent.label_ not in UNWANTED_ENTITIES and ent.text not in self.prioritized:
                    self.prioritized.append(ent.text)

            # Check for any remaining tokens that may represent things a user is interested in; save like "bag of words"
            for token in doc:
                if (token.pos_ == 'NOUN' or token.pos_ == 'PROPN') and token.text not in self.interest_dict:
                    self.interest_dict[token.text] = 1
                elif token.text in self.interest_dict:
                    self.interest_dict[token.text] += 1

        # Sort bag of words in descending order
        self.interest_dict = sorted(self.interest_dict.items(), key=lambda x: x[1], reverse=True)
        print(self.interest_dict)
        print(self.prioritized)

    def scrape_tweets(self):
        # Since a user can have a lot more tweets vs posts on Reddit, to keep things optimal, we'll just grab the user's
        # Latest 200 tweets, this way it's also accurate to their recent interests
        tweets = tweep.user_timeline(screen_name=user.user_name, count=200, include_rts=False)

        for tweet in tweets:
            doc = nlp(tweet.text)

            for ent in doc.ents:
                if type(ent.label_) is str and ent.label_ not in UNWANTED_ENTITIES and ent.text not in self.prioritized:
                    self.prioritized.append(ent.text)

            for token in doc:
                if (token.pos_ == 'NOUN' or token.pos_ == 'PROPN') and token.text not in self.interest_dict:
                    self.interest_dict[token.text] = 1
                elif token.text in self.interest_dict:
                    self.interest_dict[token.text] += 1


# The main part of our program, where we ask the user which social media site they prefer to analyze
if __name__ == '__main__':
    response = (input('What would you like to do? \n 1. Check username for recommended posts \n 2. Quit \n'))

    while response == '1':
        choice = input('Which site would you like to search posts for? \n 1. Reddit \n 2. Twitter \n')
        if choice == '1':
            uName = input('Please enter the Reddit username you would like to check recommended posts for.\n')
            user = User(uName)

            print('Scraping user history now.')
            user.scrape_comments_submissions()
            print('User history scraped successfully.')
            social = SocialGenerator(reddit)
            print('Fetching reddit posts now, please wait.')
            posts = social.search_reddit()
            for key, value in posts.items():
                print(key, ' : ', value)

        if choice == '2':
            uName = input('Please enter the Twitter username you would like to check recommended posts for.\n')
            user = User(uName)

            print('Scraping user tweets now.')
            user.scrape_tweets()
            priority_queries = user.prioritized
            secondary_queries = user.interest_dict
            print('User tweets scraped successfully.')
            social = SocialGenerator(tweep)
            print('Fetching recommended tweets now, please wait.')
            posts = social.search_twitter(priority_queries, secondary_queries)
            for key, value in posts.items():
                print(key, ' : ', value)

        response = input('Would you like to check another user? \n 1. Yes \n 2. No \n')
