# Judicator Match Crawler

This is a person match crawler from my Judicator project. The goal of this crawler is similar to something like a web crawler, which is to methodically visit web pages for various reasons.

This crawler specifically is built to start a seed player or from a queue of matches and build a dataset of match data for the Judicator Project.

The basic pattern is as follows.

* If a seed player is given
	* Download match history into queue
---
* Grab a random match from the queue
	* Download match info and extract all players from the game
	* For each player in the game
		* Download match history into queue
* Repeat until some condition

## Warning

This project is not meant to be run by individuals. This project is meant for personal use and is subject to breaking changes if cloned and used by anyone but it public for learning purposes, display, and convenience.

## Usage

Current usage is quite basic and not production ready.

Suggested usage is to create a bash script to run the crawler.

```
# If you have a environment, activate here
eval "$(conda shell.bash hook)"
conda activate my-env

crawler_location='crawler location'
log_storage='location'
TIME_OF_DAY=$(date)

# python "$crawler_location/judicator_match_crawler.py" &> "$log_storage/CRAWLER $TIME_OF_DAY.log"
```

This basic script captures our output and stores it in a log by the date. Its suggested to run this on a cron schedule.

The crawler should be modified in the `if __name__ == '__main__':` to run for a specific during. Currently this is only modifiable by the amount of matches crawled.

Additionally, a `config.py` needs to be created as well. In this config file the following must be added.

```
MONGODB_CONFIG = {
	'host' : 'replace with connection address',
	'port' : replace with port integer
}
```