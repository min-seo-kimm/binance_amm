from classes import Bot
from threading import Thread

# Initialize two instances of the Bot for BTCUSDT and ETHUSDT
bot1 = Bot('BTCUSDT', 1, 0.01, 0.04, 5, 10)
bot2 = Bot('ETHUSDT', 2, 0.01, 0.04, 5, 10)

# Function to run bot1
def b1():
    print('Starting bot1 for BTCUSDT...')
    bot1.run()

# Function to run bot2
def b2():
    print('Starting bot2 for ETHUSDT...')
    bot2.run()

# Create threads for each bot
t1 = Thread(target=b1)
t2 = Thread(target=b2)

# Start the threads
print('Starting both bots...')
t1.start()
t2.start()
