# apipipeline
A package for assisting large looping api requests.

## Api Request Pipeline
The pipeline class that facilitates chained API calls.

By passing a list of callback functions and the limit rates, this
class will automatically run through complicated api chaining to obtain
large collections of specific data. This method is best suited for when
a portion of the return value of a specific api request is used to make
the next request.

### Getting Started
Install the apipipeline through pip and then import the api_request_pipeline
object

```python
!pip install apipipeline==0.0.2
from apipipeline import api_request_pipeline as arp
```

Then create your list of callback functions. Details for how to structure callback
functions can be found [here](#callback-list).

```python
def get_summoner_ids():
    return f"https://na1.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/BRONZE/III?page=1&api_key={credentials["key"]}"
def get_summoners(resp):
    urls = []
    for summoner in resp.json():
        urls.append(f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/{summoner["summonerId"]}?api_key={credentials["key"]}")
    return urls
def get_matches(resp_list):
    urls = []
    for resp in resp_list:
        urls.append(f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{resp.json()["puuid"]}/ids?start=0&count=10&api_key={credentials["key"]}")
    return urls

callback_list = [get_summoner_ids, get_summoners, get_matches]
```

Then you initialize the class object *ApiRequestPipeline* with the
callback function list, the rate limits, and the rate control type.

```python
pipe = arp.ApiRequestPipeline(callback_list=callback_list, rate_limit_1=(20, 1), rate_limit_2=(100, 120), rate_control_type="sprint")
match_responses = pipe.make_requests()
```

The [rate limits](#rate-limit-control) come in tuples specifying the amount in what time period
(in seconds) and the rate control can either be [*sprint*](#rate-control-sprint) or [*walk*](#rate-control-walk)
which specifies how the request loop sleeps to account for the limits.

### <a id="callback-list"></a>Callback List
A series of callback functions defined in a list.
Each callback function should return the API request url/s,
either as a single string or list of strings
and accept the response of an API request as its parameter
using the previous callback function's returned url/s.

### <a id="rate-limit-control"></a>Rate Limit Control
Two api rate limits can be added as tuples in the form (request_count, time).
The way the loop controls the rate limit can be set two different ways

#### <a id="rate-control-sprint"></a>rate_control_type == "sprint"

Increments the short request
and long request counts and then checks if those counts are
greater than the allotted counts within the specific time period.
If so, then it sleeps. If not, then it checks if it passed the
time period without going over the max api limit. If so, then it
resets the count. Therefore, it assumes that the rate at which it
will be calling the api is constant, and resets completely instead
of adhering to a rolling count within the time period.

#### <a id="rate-control-walk"></a>rate_control_type == "walk"

Sleeps enough after every request
to always stay under the most restricting of the two rate limits.