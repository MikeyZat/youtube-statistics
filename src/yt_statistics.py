import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import logging

# set logging configuration here
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG
)


def shape_item(item):
    """ Leave out unnecessary info """
    snippet = item['snippet']
    return {
        'publishedAt': snippet.get('publishedAt'),
        'title': snippet.get('title'),
        'channelTitle': snippet.get('channelTitle'),
        'tags': snippet.get('tags'),
        'categoryId': snippet.get('categoryId'),
    }


def response_to_video_list(response):
    """ Shape response from YT API """
    return list(map(shape_item, response['items']))


class Statistics:
    youtube_client = None
    liked_songs = []
    all_categories_map = {}

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.liked_songs = self.get_all_liked_videos()
        self.all_categories_map = self.get_categories_map()

    def get_youtube_client(self):
        """ Log into Youtube """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "OAuth_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        logging.info("Successfully retrieved youtube client")

        return youtube_client

    def get_liked_videos_batch(self, page_token=None):
        """ Get paginated chunk of liked videos
            If no page_token is given, it returns first page """
        request = self.youtube_client.videos().list(
            part="snippet",
            myRating="like",
            maxResults=50,
            pageToken=page_token
        )
        response = request.execute()
        result = response_to_video_list(response)
        logging.info(f"Successfully received {len(result)} youtube liked videos list")
        return result, response.get('nextPageToken')

    def get_all_liked_videos(self):
        """ Get liked videos and shape the results """
        result, page_token = self.get_liked_videos_batch()
        while page_token is not None:
            new_results, page_token = self.get_liked_videos_batch(page_token)
            result = result + new_results

        return result

    def get_categories_map(self):
        """ Get all existing categories in format id -> category name """
        categories_ids = set(map(lambda item: item.get('categoryId'), self.liked_songs))
        request = self.youtube_client.videoCategories().list(
            part="snippet",
            id=','.join(id for id in categories_ids),
        )
        response = request.execute()
        logging.info(f"Successfully received {len(response['items'])} categories")
        categories_map = {}
        for category in response['items']:
            try:
                categories_map[category['id']] = category['snippet']['title']
            except KeyError:
                logging.error("Incorrect category body", exc_info=True)
        return categories_map


if __name__ == '__main__':
    stats = Statistics()
