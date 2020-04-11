"""
General logic for this file.

Take a summoner name seed and pull match list.
If no seed check summoner queue

Judicator match crawler is used to start at one player and pull their entire match history

From this match history we download each game and pull every user from each game and their match histories if we haven't seen the user before.

Match history games get moved into a queue of match ids where we randomly pull a new match id to download and repeat the above procedure.

The goal of this file is to slowly crawl over all players and collect massive amounts of game data. To then build applications on top of it.
"""

from judicator.api.matchAPI import MatchAPI
from judicator.api.leagueAPI import LeagueAPI 
from judicator.api.summonerAPI import SummonerAPI

from pymongo import MongoClient

import random
from datetime import datetime

from requests.exceptions import HTTPError

import config

class BaseCrawler:

	def __init__(self):
		"""

		"""
		self.match_conn = MatchAPI()
		self.league_conn = LeagueAPI()
		self.summoner_conn = SummonerAPI()

		# Initialize connection information
		self.client = MongoClient(**config.MONGODB_CONFIG)
		self.judicator_db = self.client['judicator']

		self.judicator_summoner = self.judicator_db['summoner']
		self.judicator_summoner_league = self.judicator_db['summoner_league']
		self.judicator_match_queue = self.judicator_db['match_queue']
		self.judicator_match = self.judicator_db['match']

		# Initialize empty set information
		self.registered_matches = set()
		self.registered_summoners = set()
		self.summoner_accounts = set()
		self.queued_matches = set()

		self.queues = set([420])
		self.seasons = set([13])
		self.beginning_time = datetime(2020, 3, 19)
		self.ending_time = datetime(2020, 3, 26)

	def crawl(self, match_count: int=1, seed: str=None):
		"""

		Args:
			match_count: Will crawl this amount of matches, if None is supplied the crawler will crawl until the program is forcefully stopped
			seed: string of a player name to seed
		"""
		print('Initialize: Pulling from database', flush=True)
		self.pull_registered_matches()
		self.pull_registered_summoners()

		if len(self.queued_matches) == 0 and seed is None:
			print('No matches in queue', flush=True)
			raise Exception
		
		if seed is not None:
			print('Seeding', flush=True)
			summoner = self.summoner_conn.get_summoner_by_name(seed)

			if summoner.puuid() not in self.registered_summoners:
				self.process_account_id(summoner.accountId())
		

		counter = 0
		while len(self.queued_matches) != 0:
			print('Crawling', flush=True)
			match_id = random.sample(self.queued_matches, 1)[0]
			try:
				self.process_match_id(match_id)
			except Exception as e:
				print(f'ERROR: {e}')
				continue
			counter += 1
			if match_count is not None and counter >= match_count:
				break

	def pull_registered_matches(self) -> None:
		"""
			Pull all registered game ids (believe to be unique)
			# TODO consider moving to comprehension or reworking entirely
			Registered matches is needed to not insert duplicate games while crawling match histories
			Multiple players play in a same game so a match will be in multiple users match histories 
			# TODO Look into match more extra sets for crawling certain things, like patch versions
		"""
		result = self.judicator_match.find({}, {'_id' : 0})
		for doc in result:
			self.registered_matches.add(doc['gameId'])
		
		result = self.judicator_match_queue.find({}, {'_id' : 0})
		for doc in result:
			assert doc['gameId'] not in self.registered_matches, f"Match queue contains pulled match id: {doc['gameId']}"
			self.queued_matches.add(doc['gameId'])

	def pull_registered_summoners(self) -> None:
		"""
			Pull all registered summoner puuids (completely unique)
			# TODO consider moving to comprehension or reworking entirely 
			Registered summoners is needed to not insert duplicate summoners while crawling league histories
		"""
		result = self.judicator_summoner.find({}, {'_id' : 0})
		for doc in result:
			self.registered_summoners.add(doc['puuid'])
			self.summoner_accounts.add(doc['accountId'])

	def process_account_id(self, account_id: str) -> None:
		"""
			Takes an account id and requests the entire match history for the account.
			Once the entire match history is returned matches that haven't been queued or registered are inserted into the queue.
			The correct mongo tables are updated accordingly

			Args:
				account_id: string representing a summoners account id
		"""
		# get entire match history
		match_list_obj = self.match_conn.get_matchlist_by_accountid(account_id, end_time=self.ending_time, begin_time=self.beginning_time, queues=self.queues, seasons=self.seasons)
		match_list = match_list_obj.matches()

		# add matches to queue that are unencountered
		for match in match_list:
			if match.game_id() not in self.queued_matches and match.game_id() not in self.registered_matches:
				self.judicator_match_queue.insert_one(match.raw_data())
				self.queued_matches.add(match.game_id())

	def process_match_id(self, match_id: int) -> None:
		"""
			Takes a match id and requests the full match data that is then registered and inserted into the database. The game id is removed from the queue
			Then we collect all participants in the games. For the participants we register their puuid and process their account.
		"""
		match = self.match_conn.get_match_by_matchid(match_id)
		participants = match.participant_account_ids()

		if match.game_id() not in self.registered_matches:
			# add to local registered match set and database
			self.judicator_match.insert_one(match.raw_data())
			self.registered_matches.add(match.game_id())
			# remove from local registered match set and database
			self.queued_matches.remove(match.game_id())
			self.judicator_match_queue.delete_one({'gameId' : match.game_id()})

		for account_id in participants:
			# skip accounts already encountered, waste of calls
			if account_id in self.summoner_accounts:
				continue
			try:
				summoner = self.summoner_conn.get_summoner_by_account_id(account_id)
			except HTTPError as e:
				if int(e.response.status_code) == 404:
					print(f'Account ID Not Found: {account_id}')
					continue

			# Don't register summoners already registered
			if summoner.puuid() not in self.registered_summoners:
				self.judicator_summoner.insert_one(summoner.raw_data())
				self.registered_summoners.add(summoner.puuid())
			
			self.process_account_id(account_id)

if __name__ == '__main__':
	crawler = BaseCrawler()
	crawler.crawl(match_count=None, seed='A Legendary Crab')
