#!/usr/bin/env python

'''
This scripts monitors a specific process and ensures that its child processes are terminated correctly.
'''

from __future__ import print_function

import argparse
import os
import psutil
import signal
import sys
import time


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Monitor all subprocesses of a given process id and ensure that all are terminated when the parent process dies.')
    parser.add_argument('pid', type=int, nargs='?', default=os.getppid(), help='The process ID to monitor (default: id of parent process)')
    args = parser.parse_args(argv)

    mypid = os.getpid()

    # check if PID is valid
    try:
        proc = psutil.Process(args.pid)
    except psutil.NoSuchProcess:
        print('No process with ID %i found' % args.pid, file=sys.stderr)
        return 1

    # wait until monitored process has died
    print('Monitoring PID %i...' % args.pid)
    children = []
    while proc.is_running():
        children = get_recursive_children(proc)
        time.sleep(10)

    # remove myself from list of children
    children = [c for c in children if c.pid != mypid]

    if not children:
        print('No child processes to terminate.')
        return 0

    if children:
        print('Sending TERM signal to %i child processes:' % len(children))
        for c in children:
            try:
                c.terminate()
                print('- %i: %s' % (c.pid, c.name))
            except psutil.NoSuchProcess:
                print('- %i (already terminated)' % c.pid)

        # wait until all processes are no longer running or until timeout has elapsed
        # giving the processes time to handle the TERM signal
        children = wait_for_processes(children, 30.0)

    if children:
        print('Sending KILL signal to %i remaining child processes:' % len(children))
        for c in children:
            try:
                c.kill()
                print('- %i: %s' % (c.pid, c.name))
            except psutil.NoSuchProcess:
                print('- %i (already terminated)' % c.pid)

        # wait again to check if all process are no longer running
        # giving some time so that the KILL signals have been handled (e.g. should not be 0.1s)
        children = wait_for_processes(children, 1.0)

    if children:
        print('%i processes could not be killed:' % len(children), file=sys.stderr)
        for c in children:
            try:
                print('- %i: %s' % (c.pid, c.name), file=sys.stderr)
            except psutil.NoSuchProcess:
                print('- %i (terminated by now)' % c.pid)
        return 1

    print('All processes have been terminated.')
    return 0


def get_recursive_children(proc):
    children = []
    recurse = [proc]
    while recurse:
        parent = recurse.pop()
        try:
            # recursive=True is only supported with psutil 0.5
            # which is not available on Ubuntu Precise
            direct_children = parent.get_children()
        except psutil.NoSuchProcess:
            continue
        children.extend(direct_children)
        recurse.extend(direct_children)
    return children


def wait_for_processes(processes, timeout=1):
    # wait until all process are no longer running or until timeout has elapsed
    print('Waiting %is for processes to end:' % timeout)
    endtime = time.time() + timeout
    while time.time() < endtime and processes:
        time.sleep(0.1)
        not_running = [p for p in processes if not p.is_running()]
        for p in not_running:
            print('- %i' % p.pid)
        processes = [p for p in processes if p not in not_running]
    return processes


if __name__ == '__main__':
    # ignore SIGTERM so that if the parent process is killed
    # and forwards the signal, this script does not die
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    sys.exit(main())
