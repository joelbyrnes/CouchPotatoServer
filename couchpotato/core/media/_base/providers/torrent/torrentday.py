import re
import traceback
import time
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://torrentday.eu/',
        'login': 'https://torrentday.eu/torrents/',
        'login_check': 'https://torrentday.eu/userdetails.php',
        'detail': 'https://torrentday.eu/details.php?id=%s',
        'search': 'https://torrentday.eu/V3/API/API.php',
        'download': 'https://torrentday.eu/download.php/%s/%s',
    }

    http_time_between_calls = 1  # Seconds

    def __headers(self):
        if self.conf('cookie', default=None):
            return dict(cookie=self.conf('cookie'))
        return {}

    def _searchOnTitle(self, title, media, quality, results):

        query = '"%s" %s' % (title, media['info']['year'])

        data = {
            '/browse.php?': None,
            'cata': 'yes',
            'jxt': 8,
            'jxw': 'b',
            'search': query,
        }

        data = self.getJsonData(self.urls['search'], data = data, headers=self.__headers())
        try: torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except: return

        for torrent in torrents:
            results.append({
                'id': torrent['id'],
                'name': torrent['name'],
                'url': self.urls['download'] % (torrent['id'], torrent['fname']),
                'detail_url': self.urls['detail'] % torrent['id'],
                'size': self.parseSize(torrent.get('size')),
                'seeders': tryInt(torrent.get('seed')),
                'leechers': tryInt(torrent.get('leech')),
            })

    def login(self):
        # login not required when using cookie header
        if not self.__headers():
            return super(Base, self).login()

        # Check if the cookie is still valid every hour; keep it alive
        now = time.time()
        if not self.last_login_check or (self.last_login_check and self.last_login_check < (now - 3600)):
            try:
                output = self.urlopen(self.urls['login_check'], headers=self.__headers())
                if self.loginCheckSuccess(output):
                    self.last_login_check = now
                    return True
            except: pass
            self.last_login_check = None
            self.login_failures += 1
            if self.login_failures >= 3:
                self.disableAccount()

        if self.last_login_check:
            return True

        # no point trying to login if using cookie

        log.error('Failed to use cookie to access %s', (self.getName()))
        return False

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit.x': 18,
            'submit.y': 11,
            'submit': 'submit',
        }

    def loginSuccess(self, output):
        notfound = re.search('User not found', output)
        if notfound:
            raise Exception(notfound.group(0).strip())

        often = re.search('You tried too often, please wait .*</div>', output)
        if often:
            raise Exception(often.group(0)[:-6].strip())

        return 'Password not correct' not in output

    def loginCheckSuccess(self, output):
        return 'logout.php' in output.lower()

    def loginDownload(self, url = '', nzb_id = ''):
        # login not required when using cookie header
        if not self.__headers():
            return super(Base, self).loginDownload(url, nzb_id)
        else:
            try:
                return self.urlopen(url, headers=self.__headers())
            except:
                log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

config = [{
    'name': 'torrentday',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentDay',
            'description': '<a href="https://torrentday.eu/" target="_blank">TorrentDay</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC5ElEQVQ4y12TXUgUURTH//fO7Di7foeQJH6gEEEIZZllVohfSG/6UA+RSFAQQj74VA8+Bj30lmAlRVSEvZRfhNhaka5ZUG1paKaW39tq5O6Ou+PM3M4o6m6X+XPPzD3zm/+dcy574r515WfIW8CZBM4YAA5Gc/aQC3yd7oXYEONcsISE5dTDh91HS0t7FEWhBUAeN9ynV/d9qJAgE4AECURAcVsGlCCnly26LMA0IQwTa52dje3d3e3hcPi8qqrrMjcVYI3EHCQZlkFOHBwR2QHh2ASAAIJxWGAQEDxjePhs3527XjJwnb37OHBq0T+Tyyjh+9KnEzNJ7nouc1Q/3A3HGsOvnJy+PSUlj81w2Lny9WuJ6+3AmTjD4HOcrdR2dWXLRQePvyaSLfQOPMPC8mC9iHCsOxSyzJCelzdSXlNzD5ujpb25Wbfc/XXJemTXF4+nnCNq+AMLe50uFfEJTiw4GXSFtiHL0SnIq66+p0kSArqO+eH3RdsAv9+f5vW7L7GICq6rmM8XBCAXlBw90rOyxibn5yzfkg/L09M52/jxqdESaIrBXHYZZbB1GX8cEpySxKIB8S5XcOnvqpli1zuwmrTtoLjw5LOK/eeuWsE4JH5IRPaPZKiKigmPp+5pa+u1aEjIMhEgrRkmi9mgxGUhM7LNJSzOzsE3+cOeExovXOjdytE0LV4zqNZUtV0uZzAGoGkhDH/2YHZiErmv4uyWQnZZWc+hoqL3WzlTExN5hhA8IEwkZWZOxwB++30YG/9GkYCPvqAaHAW5uWPROW86OmqCprUR7z1yZDAGQNuCvkoB/baIKUBWMTYymv+gra3eJNvjXu+B562tFyXqTJ6YuHK8rKwvBmC3vR7cOCPQLWFz8LnfXWUrJo9U19BwMyUlJRjTSMJ2ENxUiGxq9KXQfwqYlnWstvbR5aamG9g0uzM8Q4OFt++3NNixQ2NgYmeN03FOTUv7XVpV9aKisvLl1vN/WVhNc/Fi1NEAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'cookie',
                    'default': '',
                    'description': 'Until TorrentDay fixes its captcha. Should look like "uid=1012345; pass=286755fad04869ca523320acce0dc6a4". Ignores username and password if this is set.',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
