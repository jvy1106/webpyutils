'''Example of using the APIServer to create a quick and dirty RESTful API service'''
import web
import random
from webpyutils import api
from webpyutils import APIServer

QUOTES = [
    {'author':'Bill Gates', 'quote':'640K ought to be enough for anybody.'},
    {'author':'Linus Torvald', 'quote':'Software is like sex; it\'s better when it\'s free.'},
    {'author':'Steve Jobs', 'quote':'We made the buttons on the screen look so good you\'ll want to lick them.'},
]
class Quotes(object):
    '''get a quote and add a quote'''
    @api
    def GET(self):
        '''get a quote'''
        ret = {'quote' : random.choice(QUOTES)}
        return ret

    @api
    def POST(self):
        '''store a quote'''
        ret = {'code' : 200}
        author = web.input().get('author', None)
        quote = web.input().get('quote', None)
        if not author or not quote:
            ret['message'] = 'author and quotes is required'
            ret['code'] = 400
            return ret

        QUOTES.append({'author':author, 'quote':quote})
        ret['message'] = 'Quote has been added'
        return ret

URLS = (
    '/v1/quote/?', Quotes
)

application = web.application(URLS, globals())

if __name__ == '__main__':
    #create and start an instance of APIServer
    server = APIServer(application, server_name='quoteserver', log_path='./quoteserver.log')
    server.run(ip='0.0.0.0', port=8080, threads=5)
