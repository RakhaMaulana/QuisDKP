#!/bin/python3
# Global Variables - Byte me
N = 20
# Communication with the app
from requests import post, get
def buy(id):
  return get("http://localhost:1002/buy/"+id)
def sell(id):
  return get("http://localhost:1002/sell/"+id)
# Threads Classes
import threading
import time
class Buyer(threading.Thread):
    def run(self):
        while True:
            print("Buying milk...")
            buy("1")
            time.sleep(20)
class Seller(threading.Thread):
    def run(self):
        while True:
        # Some code that find the id
            try:
                print("Selling Milk..")
                sell("1")
            except:
                pass
if __name__ == "__main__":
  b = Buyer()
  b.start()
  sellers = []
  for _ in range(N):
    sellers.append(Seller())
    sellers[-1].start()
