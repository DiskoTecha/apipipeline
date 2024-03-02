"""
apipipeline: Api Request Pipeline
Copyright (C) 2024 Dylan Wadsworth
dylanwadsworth@gmail.com

This program is free software: you can redistribute it and / or modify
it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY;  without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see https://www.gnu.org/licenses/.
"""

import requests
import time


class ApiRequestPipeline:
    """A pipeline class that facilitates chained API calls.

    Uses a series of callback functions defined in a list.
    Each callback function should return the API request url/s,
    either as a single string or list of strings
    and accept the response of an API request as its parameter
    using the previous callback function's returned url/s.
    Two api rate limits can be added as tuples in the form (request_count, time).
    """

    def __init__(self, callback_list, rate_limit_1=None, rate_limit_2=None, rate_control_type="sprint"):
        self.callback_list = callback_list
        self.short_request_start_time = time.perf_counter()
        self.long_request_start_time = time.perf_counter()
        self.short_request_count = 0
        self.long_request_count = 0
        self.rate_control_type = rate_control_type
        if self.rate_control_type != "sprint" and self.rate_control_type != "walk":
            raise Exception("rate_control_type can only either be 'sprint' or 'walk'")

        rate_limit_1 = rate_limit_1 if rate_limit_1 is not None else (0, 0)
        rate_limit_2 = rate_limit_2 if rate_limit_2 is not None else (0, 0)

        if rate_limit_1[1] >= rate_limit_2[1]:
            self.long_request_max = rate_limit_1[0]
            self.long_request_cooldown = rate_limit_1[1]
            self.short_request_max = rate_limit_2[0]
            self.short_request_cooldown = rate_limit_2[1]
        else:
            self.long_request_max = rate_limit_2[0]
            self.long_request_cooldown = rate_limit_2[1]
            self.short_request_max = rate_limit_1[0]
            self.short_request_cooldown = rate_limit_1[1]

    def __check_requests(self):
        """A helper function that sleeps if it hits the api rate.

        rate_control_type == "sprint": Increments the short request
        and long request counts and then checks if those counts are
        greater than the allotted counts within the specific time period.
        If so, then it sleeps. If not, then it checks if it passed the
        time period without going over the max api limit. If so, then it
        resets the count. Therefore, it assumes that the rate at which it
        will be calling the api is constant, and resets completely instead
        of adhering to a rolling count within the time period.

        rate_control_type == "walk": Sleeps enough after every request
        to always stay under the most restricting of the two rate limits.
        """

        # Check for no api limits initialized
        if self.short_request_max == 0 and self.long_request_max == 0:
            return
        if self.rate_control_type == "sprint":
            self.short_request_count += 1
            self.long_request_count += 1
            # If not past long request rate time, and request count is greater than the rate limit max, sleep
            if (time.perf_counter() - self.long_request_start_time < self.long_request_cooldown and
                    self.long_request_count >= self.long_request_max):
                print(
                    f"Sleeping for: {self.long_request_cooldown - (time.perf_counter() - self.long_request_start_time):.2f} seconds")
                time.sleep(self.long_request_cooldown - (time.perf_counter() - self.long_request_start_time))
                self.long_request_start_time = time.perf_counter()
                self.short_request_start_time = time.perf_counter()
                self.long_request_count = 1
                self.short_request_count = 1

            # If long request was initialized and is past the rate time without going past the rate limit, then reset
            elif 0 < self.long_request_cooldown < time.perf_counter() - self.long_request_start_time:
                self.long_request_start_time = time.perf_counter()
                self.long_request_count = 1

            # If not past short request rate time, and request count is greater than the rate limit max, sleep
            elif time.perf_counter() - self.short_request_start_time < self.short_request_cooldown and self.short_request_count >= self.short_request_max:
                print(
                    f"Sleeping for: {self.short_request_cooldown - (time.perf_counter() - self.short_request_start_time):.2f} seconds")
                time.sleep(self.short_request_cooldown - (time.perf_counter() - self.short_request_start_time))
                self.short_request_start_time = time.perf_counter()
                self.short_request_count = 1

            # If short request was initialized and is past the rate time without going past the rate limit, then reset
            elif 0 < self.short_request_cooldown < time.perf_counter() - self.short_request_start_time:
                self.short_request_start_time = time.perf_counter()
                self.short_request_count = 1
        else:
            max_requests_per_second = (self.long_request_max / self.long_request_cooldown) if (
                (self.long_request_max / self.long_request_cooldown) <
                (self.short_request_max / self.short_request_cooldown))\
                else (self.short_request_max / self.short_request_cooldown)
            time.sleep(1 / max_requests_per_second)
        return

    def make_requests(self, initial_request_url=None):
        """Function to call to start the request loop through the callback function list.

        Can specify the initial url to request and then start the callback function
        loop. Or you can simply have the first callback function in the list to not
        take any arguments and simply generates the initial request and returns it. Every
        callback function then takes the response from the last url returned, or a list of
        responses if the last function returned a list of urls. Function ultimately returns
        the last response or list of responses obtained from the last callback function
        """
        resp = None
        url = initial_request_url
        if url is not None:
            resp = requests.get(initial_request_url)
        # For each callback function
        for index, f in enumerate(self.callback_list):
            print(f"Running requests, callback_list index = {index}")
            # Get the callback return
            if resp is not None:
                callback_return = f(resp)
            else:
                callback_return = f()
            # If callback return is a string, then get response treating string as the request url
            if type(callback_return) is str:
                resp = requests.get(callback_return)
                self.__check_requests()
            # If callback return is a list, then create a list of responses
            elif type(callback_return) is list:
                resp = []
                # Loop through list
                for r in callback_return:
                    resp.append(requests.get(r))
                    self.__check_requests()
        return resp
