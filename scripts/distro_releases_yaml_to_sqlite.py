#!/usr/bin/env python

import argparse
import logging
import sqlite3
import urllib2
import yaml

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    
    desc = '''\
Imports a subset of a ROS distro release yaml file to a SQLite file.

Typically the yaml file is
https://raw.github.com/ros/rosdistro/master/releases/groovy.yaml
'''
    p = argparse.ArgumentParser(description=desc)
    p.add_argument('url', help='Location of yaml file')
    p.add_argument('db', help='Path to SQLite db file that will contain the results')
    p.add_argument('--repos_table',
                   default='repositories', 
                   help='Name of table with info on repositories')
    args = p.parse_args()

    yfile = yaml.load(urllib2.urlopen(args.url).read())

    db = sqlite3.connect(args.db)
    create_table_with_rows(db, args.repos_table,
                           header='name url version packages'.split(),
                           rows=yield_repo_rows(yfile['repositories']))
    db.commit()

    logging.info('Updated %s table in %s', args.repos_table, args.db)

def create_table_with_rows(db, table_name, header, rows):
    """
    Creates a table in an SQLite db with the given name, header and rows.
    If the table already exists, it will be overwritten.

    >>> db = sqlite3.connect(':memory:')
    >>> create_table_with_rows(db, 'tbl', header=['a', 'b'], rows=[(1, 2), (2, 3)])
    >>> db.commit()
    >>> c = db.cursor()
    >>> c.execute('select * from tbl').fetchall()
    [(1, 2), (2, 3)]
    """
    columns_str = ', '.join(header)
    db.execute('drop table if exists %s' % table_name)
    db.execute('create table %s(%s)' % (table_name, columns_str))
    slots_str = ', '.join(len(header)*['?'])
    sql = 'insert into %s(%s) values (%s)' % (table_name, columns_str, slots_str)
    db.executemany(sql, rows)

def yield_repo_rows(repos_dict):
    """
    Yields rows representing repositories, given a dict from the release yaml
    file. Each row is of the form:

        name, url, version, packages

    """
    for repo_name, d in repos_dict.items():
        yield repo_name, d['url'], d['version'], ','.join(d.get('packages', {}).keys())

if __name__ == '__main__':
    main()

