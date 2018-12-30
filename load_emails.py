import os
import re
import sys
import email.parser
import json

from tqdm import tqdm
import pandas as pd

from pugnlp import futil


def iter_emails(emaildir='enron_email_files', verbose=True):
    if verbose:
        print('Indexing files and folders in {emaildir}'.format(emaildir=emaildir))
    filestats = list(tqdm(futil.generate_files(emaildir)))
    parser = email.parser.Parser()

    emails = []
    for filestat in tqdm(filestats):
        try:
            with open(filestat['path'], 'r') as f:
                e = parser.parse(f)
        except UnicodeDecodeError:
            with open(filestat['path'], 'rb') as f:
                e = parser.parse(f)
        ed = {}
        for k in vars(e).keys():
            if k == '_headers':
                ed.update(dict(e._headers))
            else:
                ed[k.strip('_')] = getattr(e, k)
        ed['folder'] = os.path.basename(os.path.dirname(f['path']))
        ed['user'] = os.path.basename(os.path.dirname(os.path.dirname(f['path'])))
        yield ed


def normalize_colname(name):
    r""" Normalize string column name with .lower(), .strip(), and .replace() on all r'\W' chars

    >>> normalize_colname('Email  Message-ID::')
    email_message_id_
    """
    try:
        return int(float(name))
    except (ValueError, TypeError):
        return re.sub(r'[\W]+', '_', str(name).strip().lower())


def DataFrame(table, *args, **kwargs):
    """ set index or index_col to False to skip automagically guessing the Index column """
    index = kwargs.pop('index', None)
    index_col = kwargs.pop('index_col', None)
    if isinstance(index, str):
        index_col = index
        index = None
    df = pd.DataFrame(table, *args, index=(index or None), **kwargs)
    df.columns = [normalize_colname(c) for c in df.columns]
    if index_col:
        df = df.set_index(normalize_colname(index_col))
    elif index_col is not False and index is not False and len(df) == len(df[df.columns[0]].dropna().unique()):
        df = df.set_index(df.columns[0])
    if df.index.name == 'message_id':
        df.index = df.index.str.lstrip('<').str.rstrip('>').str.split('.')
        df.index = pd.MultiIndex.from_tuples(pd.Series(df.index).apply(tuple), names=['i', 'j', 'server', 'name'])
    return df


def parse_emails(emaildir='/Users/hobsonlane/code/springboard/tannistha/enron_email_files'):
    df = DataFrame(iter_emails(emaildir), index_col='Message-ID')
    df = df.fillna('')
    df['defects'] = df['defects'].apply(str)  # otherwise these will be lists and NaNs
    email_users = []  # many-to-many table connecting emails to user email_addresses in the CC, TO, BCC, and FROM fields
    all_users = set()
    for i, e in tqdm(df.iterrows()):
        for c in 'cc bcc from to'.split():
            v = e[c]
            users = set(re.split(r'[\s,]+', v))
            all_users.update(set(users))
            for u in users:
                if not c:
                    continue
                email_users.append(dict(emailid=i, address=u, kind=c.lower()))
    return df, DataFrame(email_users), DataFrame(sorted(all_users))


if __name__ == '__main__':
    emaildir = 'enron_email_files'
    if len(sys.argv) > 1:
        emaildir = sys.argv[1]
    emails, email_users, users = parse_emails(emaildir=emaildir)
    print(emails.head())
    print(emails.shape)
    print(df.describe())
