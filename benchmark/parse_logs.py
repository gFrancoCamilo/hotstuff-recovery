from datetime import datetime
from glob import glob
from multiprocessing import Pool
from os.path import join
from re import findall, search
from statistics import mean
from collections import Counter
import pandas as pd
import sys
import matplotlib.pyplot as plt

from benchmark.utils import Print

def parse_nodes(log):
    if search(r'panic', log) is not None:
        raise Exception('Node(s) panicked')

    tmp = findall(r'\[(.*Z) .* Created B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    proposals = merge_results([tmp])

    tmp = findall(r'\[(.*Z) .* Committed B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    commits = merge_results([tmp])

    tmp = findall(r'\[(.*Z) .* Sending new sync request to this.', log)
    tmp = [to_posix(t) for t in tmp]
    start_sync = tmp
    print('Start: ' + str(start_sync) + ' in log ' + str(log[:57]))

    tmp = findall(r'\[(.*Z) .* Updated Firewall, which now is.', log)
    tmp = [to_posix(t) for t in tmp]
    end_sync = tmp
    print('End: ' + str(end_sync) + ' in log ' + str(log[:57]))

    tmp = findall(r'Batch ([^ ]+) contains (\d+) B', log)
    sizes = {d: int(s) for d, s in tmp}

    return proposals, commits, sizes, start_sync, end_sync

def consensus_throughput(commits, proposals, sizes, size):
    if not commits:
        return 0, 0, 0
    start, end = min(proposals.values()), max(commits.values())
    duration = end - start
    bytes = sum(sizes.values())
    bps = bytes / duration
    tps = bps / size[0]
    return tps, bps, duration


def to_posix(string):
    x = datetime.fromisoformat(string.replace('Z', '+00:00'))
    return datetime.timestamp(x)

def log_filename(nodes):
    files = ['./logs/node-' + str(i) +'.log' for i in range(nodes)]
    return files

def merge_results(input):
    # Keep the earliest timestamp.
    merged = {}
    for x in input:
        for k, v in x:
            if not k in merged or merged[k] > v:
                merged[k] = v
    return merged

def count_commits_in_intervals(commits):
    if not commits:
        return {}

    interval_length = 5  # seconds
    interval_counts = {}

    for commit_time, _ in commits:
        interval_start = commit_time
        #interval_counts[interval_start] =

    return interval_counts


def main():
    if len(sys.argv) < 2:
        print("Please enter the number of nodes as arguments")
        print("USAGE: python3 parse_nodes.py <nodes>")
        return -1
    files = log_filename(int(sys.argv[1]))
    logs = []
    for file in files:
        with open(file, 'r') as f:
            logs += [f.read()]

    try:
        with Pool() as p:
            results = p.map(parse_nodes, logs)
            results_two = p.map(parse_nodes, logs[:2])
    except (ValueError, IndexError) as e:
        raise Exception(f'Failed to parse node logs: {e}')

    proposals, commit, sizes, start_all, end_all \
        = zip(*results)

    #commits = merge_results([x.items() for x in commit])
    #counter = Counter(commits.values())

    proposals_two, commit_two, sizes_two, start_sync, end_sync \
        = zip(*results_two)
    test_two = merge_results([x.items() for x in commit_two])
    sizes_test = [x.items() for x in sizes]
    sizes_two = merge_results(sizes_test)
    counter_two = Counter(test_two.values())
    commit_two = {k: v for k, v in sorted(test_two.items(), key=lambda item: item[1])}
    execution_time = max(commit_two.values())-min(commit_two.values())
    start = []
    end = []
    for x in start_all:
        for y in x:
            start.append(y)
    for x in end_all:
        for y in x:
            end.append(y)

    print(start)
    print(end)
    start_time = min(start)-min(commit_two.values())
    end_time = max(end)-min(commit_two.values())
    min_time = min(commit_two.values())
    print('Min time is ' + str(min_time))
    print(start_time)
    print(end_time)
    #print(commit_two)

    batches = []
    timestamp = []
    for key in commit_two:
        batches.append(key)
        timestamp.append(commit_two[key]-min_time)

    batch_size = []
    for batch in batches:
        batch_size.append(sizes_two[batch]/512)

    dic = {}
    i = 0
    for time in timestamp:
        if time not in dic:
            dic[time] = []
        dic[time].append(batch_size[i])
        dic[time] = [sum(dic[time])]
        i+=1

    print(dic)
    for batch in batch_size:
        if batch == 1:
            print(batch)
    plt.scatter(timestamp, batch_size)
    plt.grid()
    plt.ylabel('Number of transactions')
    plt.xlabel('Commit Time (s)')
    plt.axvspan(start_time, end_time, color='blue', alpha=0.15, lw=0)
    ax = plt.gca()
    plt.savefig('transactions_time.pdf')
    plt.clf()

    tps = []
    x = []
    for i in range(15,int(execution_time) + 30, 15):
        x.append(i)
        bps_accumulator = 0
        for key in commit_two:
            if commit_two[key] - min_time > i - 15 and commit_two[key] - min_time < i:
                bps_accumulator += sizes_two[key]
        tps.append(bps_accumulator/512)
    
    plt.clf()
    plt.plot(x, tps)
    ax = plt.gca()
    ax.set_xticks([i for i in range(30, 300, 60)])
    ax.set_xticklabels(['[15,30]', '[75,90]', '[135,150]', '[195,210]', '[255,270]'])
    plt.grid()
    plt.ylabel('Number of transactions')
    plt.xlabel('Time Interval (s)')
    plt.axvspan(start_time, end_time, color='blue', alpha=0.15, lw=0)
    plt.savefig('tps_recovery.pdf')
    plt.clf()

    x, y = [], []
    for value in counter_two:
        x += [value]
        y += [counter_two[value]]

    x = [i-x[0] for i in x]
    print('x: ' + str(x))
    print('y: ' + str(y))
    plt.scatter(x,y)
    plt.grid()
    plt.ylabel('Number of commits')
    plt.xlabel('Time (s)')
    plt.axvspan(start_time, end_time, color='blue', alpha=0.15, lw=0)
    plt.savefig('number_commits.pdf')


    return

    test = [x.items() for x in commit]
    commit_two = merge_results([test[0], test[1]])
    sizes_test = [x.items() for x in sizes]
    sizes_two = merge_results(sizes_test)

    counter_two = Counter(commit_two.values())
    commit_two = {k: v for k, v in sorted(commit_two.items(), key=lambda item: item[1])}
    execution_time = max(commit_two.values())-min(commit_two.values())
    min_time = min(commit_two.values())
    print('Min time is ' + str(min_time))
    
    tps = []
    x = []
    for i in range(5,int(execution_time) + 5 + 5, 5):
        x.append(i)
        bps_accumulator = 0
        for key in commit_two:
            if commit_two[key] - min_time > i - 5 and commit_two[key] - min_time < i:
                bps_accumulator += sizes_two[key]
        tps.append(bps_accumulator/512)

    plt.plot(x, tps)
    ax = plt.gca()
    #ax.set_xticklabels(['0', '[0,5]', '[5,10]', '[10,15]', '[15,20]', '[20,25]', '[25,30]', '[30,35]', '[35,40]'])
    plt.grid()
    plt.ylabel('Number of transactions')
    plt.xlabel('Time Interval (s)')
    plt.axvspan(23.5, 30, color='blue', alpha=0.15, lw=0)
    plt.savefig('tps_recovery.pdf')
    plt.clf()


    x, y = [], []
    for value in counter_two:
        x += [value]
        y += [counter_two[value]]

    x = [i-x[0] for i in x]
    print('x: ' + str(x))
    print('y: ' + str(y))
    plt.scatter(x,y)
    plt.grid()
    plt.ylabel('Number of commits')
    plt.xlabel('Time (s)')
    plt.axvspan(23.5, 30, color='blue', alpha=0.15, lw=0)
    plt.savefig('number_commits.pdf')

    return
    proposals = merge_results([x.items() for x in proposals])
    sizes = {
        k: v for x in sizes for k, v in x.items() if k in commits
    }

main()
