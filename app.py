import sys, os
from tornado.web import Application, StaticFileHandler
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.options
from tornado.options import define, options, parse_command_line
import tornado.web
import tornado.gen

from jinja2 import Environment, FileSystemLoader

import logging
import re
import time

from tornado.httputil import url_concat
from tornado.concurrent import return_future

import torngithub
from torngithub import json_encode, json_decode

log = logging.getLogger("github.demo")



# From SmartAPI website
src_path = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
if src_path not in sys.path:
    sys.path.append(src_path)
print(src_path)

# Actual Path
actual_path = os.path.dirname(os.path.realpath(__file__))
print(actual_path)


STATIC_PATH = os.path.join(src_path, 'src/static')
print(STATIC_PATH)

TEMPLATE_PATH  = os.path.join(actual_path, 'templates')
print(TEMPLATE_PATH)

define("port", default=8888, help="run on the given port", type=int)
define("address", default="127.0.0.1", help="run on localhost")
define("debug", default=False, type=bool, help="run in debug mode")
define("github_client_id", help="your Github application Client ID",
       default="616faf09617779076aee")
define("github_client_secret", help="your Github application Client Secret",
       default="30ab99b97661d6ee24950b27d7470ae59823b114")
define("github_callback_path", help="your Github application Callback",
       default="/oauth")
define("github_scope", help="github scope", default="")


tornado.options.parse_command_line()
if options.debug:
    import tornado.autoreload
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    options.address = '0.0.0.0'


# Docs: http://docs.python-guide.org/en/latest/scenarios/web/
# Load template file templates/site.html
templateLoader = FileSystemLoader( searchpath="templates/" )
templateEnv = Environment( loader=templateLoader, cache_size=0 )


TEMPLATE_FILE = "site.html"
template = templateEnv.get_template(TEMPLATE_FILE)
# List for famous movie rendering
movie_list = [[1,"The Hitchhiker's Guide to the Galaxy"],[2,"Back to future"],[3,"Matrix"]]
# template.render() returns a string which contains the rendered html
html_output = template.render(list=movie_list,
                        title="Here is my favorite movie list")

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json:
            return None
        return json_decode(user_json)


# LOGIN_FILE = "login.html"
# login_template = templateEnv.get_template(LOGIN_FILE)
# login_output = login_template.render(path="TESTING")

class MainHandler(BaseHandler, torngithub.GithubMixin, tornado.web.RequestHandler):
    # def get(self):
        # self.write("Hello, world")
        # self.write(html_output)
        # template.render(list=movie_list,
        #                 title="Here is my favorite movie list")
    def get(self):
        if self.current_user:
            # self.write('Login User: ' +  self.current_user["name"]
            #            + '<br> Email: ' + self.current_user["email"]
            #            + ' <a href="/logout">Logout</a>')
            REG_FILE = "reg_form.html"
            reg_template = templateEnv.get_template(REG_FILE)
            reg_output = reg_template.render()
            self.write(reg_output)
        else:
            # self.write('<a href="'
            #            + self.settings["github_callback_path"] + '">Login</a>')

            path = self.settings["github_callback_path"]
            print "** PATH: ", path

            xsrf = self.xsrf_token
            print "** XSRF: ", self.xsrf_token

            LOGIN_FILE = "login.html"
            login_template = templateEnv.get_template(LOGIN_FILE)
            login_output = login_template.render(path=path, xsrf=xsrf)
            self.write(login_output)

            # self.render("login.html", path=path)



class GithubLoginHandler(tornado.web.RequestHandler, torngithub.GithubMixin):
    @tornado.gen.coroutine
    def get(self):
        # we can append next to the redirect uri, so the user gets the
        # correct URL on login
        redirect_uri = url_concat(self.request.protocol
                                  + "://" + self.request.host
                                  + self.settings["github_callback_path"],
                                  {"next": self.get_argument('next', '/')})

        # if we have a code, we have been authorized so we can log in
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["github_client_id"],
                client_secret=self.settings["github_client_secret"],
                code=self.get_argument("code"))
            if user:
                log.info('logged in user from github: ' + str(user))
                self.set_secure_cookie("user", json_encode(user))
            else:
                self.clear_cookie("user")
            self.redirect(self.get_argument("next","/"))
            return

        # otherwise we need to request an authorization code
        yield self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.settings["github_client_id"],
            extra_params={"scope": self.settings['github_scope'], "foo":1})

def parse_link(link):
    linkmap = {}
    for s in link.split(","):
        s = s.strip();
        linkmap[s[-5:-1]] = s.split(";")[0].rstrip()[1:-1]
    return linkmap

def get_last_page_num(link):
    if not link:
        return 0
    linkmap = parse_link(link)
    matches = re.search(r"[?&]page=(\d+)", linkmap["last"])
    return int(matches.group(1))

@tornado.gen.coroutine
def get_my_stars(http_client, access_token):
    data = []
    first_page = yield torngithub.github_request(
        http_client, '/user/starred?page=1&per_page=100',
        access_token=access_token)
    log.info(first_page.headers.get('Link', ''))
    data.extend(first_page.body)
    max_pages = get_last_page_num(first_page.headers.get('Link', ''))

    ress = yield [torngithub.github_request(
        http_client, '/user/starred?per_page=100&page=' + str(i),
        access_token=access_token) for i in range(2, max_pages + 1)]

    for res in ress:
        data.extend(res.body)

    raise tornado.gen.Return(data)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


# TEST
INDEX_FILE = "index.html"
index_template = templateEnv.get_template(INDEX_FILE)
index_output = index_template.render()

class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(index_output)



# Registration Form
REG_FILE = "reg_form.html"
reg_template = templateEnv.get_template(REG_FILE)
reg_output = reg_template.render()

class RegistrationHandler(tornado.web.RequestHandler):
    """
    API Metadata URL registration form.
    """
    def get(self):
        self.write(reg_output)

# class RegistrationHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.write(index_output)


#Login
# LOGIN_FILE = "login.html"
# login_template = templateEnv.get_template(LOGIN_FILE)
# login_output = login_template.render()

# class LoginHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.write(login_output)




# https://stackoverflow.com/questions/12031007/disable-static-file-caching-in-tornado
# class MyStaticFileHandler(tornado.web.StaticFileHandler):
#     def set_extra_headers(self, path):
#         # Disable cache
#         self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')




APP_LIST = [
    (r"/", MainHandler),
    (r"/test", TestHandler),
    (r"/registration", RegistrationHandler),
    # (r"/login", LoginHandler),
    (options.github_callback_path, GithubLoginHandler),
    (r"/logout", LogoutHandler)
]

settings = {
    "static_path": STATIC_PATH,
    "template_path": TEMPLATE_PATH,
    "compiled_template_cache": False,
    "cookie_secret": "asdf",
    "login_url": options.github_callback_path,
    "xsrf_cookies": True,
    "github_client_id": options.github_client_id,
    "github_client_secret": options.github_client_secret,
    "github_callback_path": options.github_callback_path,
    "github_scope": options.github_scope,
    "autoescape": None
}


def main():
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

    application = tornado.web.Application(APP_LIST, **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port, address=options.address)
    loop = tornado.ioloop.IOLoop.instance()
    if options.debug:
        tornado.autoreload.start(loop)
        logging.info('Server is running on "%s:%s"...' % (options.address, options.port))
    loop.start()


if __name__ == "__main__":
    main()

