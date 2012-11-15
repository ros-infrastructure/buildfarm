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

Typically the wet yaml file is at

    https://raw.github.com/ros/rosdistro/master/releases/groovy.yaml

and the dry yaml file is at

    https://code.ros.org/svn/release/trunk/distros/groovy.rosdistro
\
'''
    p = argparse.ArgumentParser(description=desc)
    p.add_argument('wet_url', help='Location of yaml file about wet packages')
    p.add_argument('dry_url', help='Location of yaml file about dry packages')
    p.add_argument('db', help='Path to SQLite db file that will contain the results')
    p.add_argument('--wet_table',
                   default='wet_packages', 
                   help='Name of table for wet packages')
    p.add_argument('--dry_table',
                   default='dry_packages',
                   help='Name of table for dry packages')
    args = p.parse_args()


    db = sqlite3.connect(args.db)

    # Wet
    logging.info('Downloading %s', args.wet_url)
    wet_data = yaml.load(urllib2.urlopen(args.wet_url).read())
    logging.info('Updating %s table in %s', args.wet_table, args.db)
    create_table_with_rows(db, args.wet_table,
                           header='name url version packages'.split(),
                           rows=yield_wet_repo_rows(wet_data['repositories']))

    # Dry
    logging.info('Downloading %s', args.dry_url)
    dry_data = yaml.load(urllib2.urlopen(args.dry_url).read())
    logging.info('Updating %s table in %s', args.dry_table, args.db)
    create_table_with_rows(db, args.dry_table,
                           header='name version'.split(),
                           rows=yield_dry_repo_rows(dry_data['stacks']))

    db.commit()
    logging.info('Done')

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

def yield_wet_repo_rows(repos_dict):
    """
    Yields rows representing source repositories, given a dict from the wet
    release yaml file. Each row is of the form:

        name, url, version, packages

    """
    for repo_name, d in repos_dict.items():
        yield repo_name, d['url'], d['version'], ','.join(d.get('packages', {}).keys())

def yield_dry_repo_rows(stacks_dict):
    """
    Yields rows representing source repositories, given the stacks dict from the
    dry yaml file. Each row is of the form:

        name, version

    """
    for name, d in stacks_dict.items():
        if name == '_rules':
            continue
        yield name, d.get('version')

if __name__ == '__main__':
    main()

