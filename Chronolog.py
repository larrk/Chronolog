''' A script for logging worker statistics to be used in calculating
    manual ether payout amounts to ethermine.org pool peers. '''
''' Intended to be run hourly via CRON job. '''

import requests
import time
import os
import json

#### Configuration ####

## API endpoint and request parameters
API = 'https://api.ethermine.org/miner/'
timeout = 10

## Miner address
MINER = 'BC1ADb062Fe69fe08f4722809C7B64198f831097'

## Peers
PEERS = ["Ryan", "Matthew", "Sam"]
PEERWORKERS = {PEERS[0]: ['kleiner', '43465a'],
               PEERS[1]: ['pc'],
               PEERS[2]: ['sam']}



## The current date and time
t = time.localtime()
logDateTime = time.strftime("%y-%m-%d : %H", t)

## Create payout summary directory
try:
    os.mkdir("payouts")
except(FileExistsError):
    pass

## Create log file directory
try:
    os.mkdir("logs")
except(FileExistsError):
    pass

#### Script begins here ####

if __name__ == '__main__':

    # Get statistics from API (3 requests).

    # Get miner history.
    # https://api.ethermine.org/docs/#api-Miner
    historicalMinerStats = requests.get(API+MINER+'/history', timeout=timeout)
    # Get worker history.
    # https://api.ethermine.org/docs/#api-Worker
    historicalWorkerStats = requests.get(API+MINER+'/workers', timeout=timeout)
    # Get payout history.
    # https://api.ethermine.org/docs/#api-Miner-miner_payouts
    historicalPayoutStats = requests.get(API+MINER+'/payouts', timeout=timeout)

    # Open db.json and refresh values in memory.
    with open("db.json", "r") as db:
        dbjson = json.load(db)
        recordedLastPayout = dbjson['lastPayout']
        # If ethermine.org paid out to our wallet in the last hour, reset nonce, megahash-hours and average hashrate. 
        if historicalPayoutStats.json()['data'][0]['paidOn'] != recordedLastPayout:
            dbjson['lastPayout'] = historicalPayoutStats.json()['data'][0]['paidOn']
            dbjson['nonce'] = 0
            for peer in PEERS:
                dbjson['peers'][peer]['cumulativeMegaHashHours'] = 0
                dbjson['peers'][peer]['averageHashRateThisPayoutPeriod'] = 0
        # Otherwise, update averages normally and increment nonce.
        # TODO: Abbreviate next 11 lines
        else:
            dbjson['nonce'] = dbjson['nonce'] + 1
            nonce = dbjson['nonce']
            for peer in PEERS:
                thisPeerWorkers = PEERWORKERS[peer]
                thisPeerMegaHashHours = 0
                for worker in thisPeerWorkers:
                    # 4 requests.
                    thisWorkerHistory = requests.get(API+MINER+'/worker/'+worker+'/history')
                    thisWorkerMegaHashHours = thisWorkerHistory.json()['data'][0]['averageHashrate']
                    print(worker, "averaged", thisPeerMegaHashHours / pow(10, 6), "Mh/s this hour")
                    thisPeerMegaHashHours = thisPeerMegaHashHours + thisWorkerMegaHashHours
                    #print(peer, "contributed", thisPeerMegaHashHours / pow(10, 6), "MegaHashHours this hour.")
                dbjson['peers'][peer]['cumulativeMegaHashHours'] = dbjson['peers'][peer]['cumulativeMegaHashHours'] + thisPeerMegaHashHours / pow(10, 6)
                dbjson['peers'][peer]['averageHashRateThisPayoutPeriod'] = dbjson['peers'][peer]['cumulativeMegaHashHours'] / nonce
        
    with open("db.json", "w") as db:
        # Write modified json object to file db.json
        print(str(json.dumps(dbjson, indent=4)))
        db.write(str(json.dumps(dbjson, indent=4)))




        
    ## Move CWD to ./logs
    os.chdir("logs")

    # Open log file in append mode
    with open(logDateTime + '.log', "a") as logFile:
        prettyHistMinerStats =  str(json.dumps(historicalMinerStats.json(), sort_keys=False, indent=4))
        prettyHistWorkerStats = str(json.dumps(historicalWorkerStats.json(), sort_keys=False, indent=4))

        logOut = logDateTime + "\nMINER STATS\n\n" + prettyHistMinerStats + "\n\nWORKER STATS" + prettyHistWorkerStats 
        logFile.write(logOut)
    
    # 7 requests total.