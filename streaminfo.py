#!/usr/bin/python
import sys, requests, json
from bs4 import BeautifulSoup


class Stream():
    def __init__(self):
        self.url = ''
        self.name = ''
        self.software = None
        self.kbps = None
        self.checked = False
        self.current_listeners = None
        self.max_listeners = None
        self.avg_listen_time = None
        self.listener_peak = None
        self.current_song = None
        self.samplerate = None


class Io():
    def read_db(self):
        f = open('streams', 'r')
        a = f.readlines()
        objects = []
        streams = [z.replace('\n', '').split(':', 2) for z in a if z.count(':') >= 3 and not z.startswith('#')]

        for stream in streams:
            obj = Stream()
            obj.software = stream[1]
            obj.url = stream[2]
            obj.name = stream[0]
            objects.append(obj)

        return objects

    def fetch_page(self, stream):
        try:
            r = requests.get(stream.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            if r.status_code == 200:
                return r.content
            else:
                raise Exception('')
        except Exception as e:
            pass


class StreamInfo():
    def __init__(self):
        self.streams = Io().read_db()
        self.bar = '-------------------'

    def fetch_all(self):
        for stream in self.streams:
            page = Io().fetch_page(stream)

            if not page:
                continue

            if stream.software == 'shoutcast':
                stream = Parse(stream).shoutcast(page)
            elif stream.software == 'icecast':
                stream = Parse(stream).icecast(page)

    def sanitize(self):
        sanitized_streams = []

        for stream in self.streams:
            s = Stream()

            for attr in [a for a in dir(stream) if not a.startswith('__') and not a.startswith('_')]:
                get_attr = getattr(stream, attr)

                if get_attr:
                    try:
                        get_attr = int(get_attr)
                    except:
                        pass

                    setattr(s, attr, get_attr)
                else:
                    delattr(s, attr)

            sanitized_streams.append(s)

        return sanitized_streams

    def display_json(self):
        data = {}
        stream_list = self.sanitize()
        stream_list.sort(key=lambda x: x.name, reverse=True)

        for stream in stream_list:
            data[stream.name] = stream.__dict__

        print json.dumps(data, sort_keys=True, indent=4)

    def display_raw(self):
        stream_list = self.sanitize()
        stream_list.sort(key=lambda x: x.name, reverse=True)

        for stream in stream_list:
            print '%s\n%s' % (stream.name.title(), self.bar)

            for attr in [a for a in dir(stream) if not a.startswith('__') and not a.startswith('_')]:
                get_attr = getattr(stream, attr)

                print '%s: %s' % (attr, get_attr)
            print ''

    def display_totals(self):
        stream_list = self.sanitize()

        totals = {
            'icecast': 0,
            'shoutcast': 0,
            'totals': 0
        }

        for software in ['icecast', 'shoutcast']:
            print '%s\n%s' % (software.upper(), self.bar)
            for stream in [z for z in stream_list if z.software == software]:
                totals['totals'] += stream.current_listeners
                totals[software] += stream.current_listeners

                print '%s:\t%s' % (stream.name, str(stream.current_listeners))

            print '%s\n%s: %s\n' % (self.bar, 'Amount', str(totals[software]))

        print '\nTOTALS: %s' % str(totals['totals'])


class Parse():
    def __init__(self, stream):
        self.stream = stream

    def icecast(self, page):
        try:
            data = json.loads(page)['icestats']['source']

            self.stream.current_listeners = data['listeners']
            self.stream.samplerate = data['samplerate']
            self.stream.current_song = data['title']
            self.stream.checked = True

            return self.stream
        except:
            pass

    def shoutcast(self, page):
        try:
            soup = BeautifulSoup(page)

            for tr in soup.findAll('tr'):
                if 'Server Status:' in tr.text:
                    if not 'Server is currently up' in tr.text:
                        return
                elif 'Stream Status:' in tr.text:
                    status = tr.text[tr.text.find('at ')+3:]
                    self.stream.kbps = ' '.join(status.split(' ')[:2])
                    self.stream.current_listeners = status[status.find('with ')+5:].split(' ')[0]
                    self.stream.max_listeners = status[status.find('of ')+3:].split(' ')[0]
                elif 'Listener Peak:' in tr.text:
                    self.stream.listener_peak = tr.text[tr.text.find(': ')+2:]
                elif 'Average Listen Time:' in tr.text:
                    self.stream.avg_listen_time = tr.text[tr.text.find(': ')+2:]
                elif 'Current Song' in tr.text:
                    self.stream.current_song = tr.text[tr.text.find(': ')+2:]

            self.stream.checked = True
            return self.stream
        except:
            pass

if __name__ == '__main__':
    s = StreamInfo()
    s.fetch_all()

    if len(sys.argv) >=2:
        if sys.argv[1] == 'json':
            s.display_json()
        elif sys.argv[1] == 'totals':
            s.display_totals()
        elif sys.argv[1] == 'raw':
            s.display_raw()
    else:
        print 'Usage:\n  streaminfo.py [json/totals/raw]'
